import time
import datetime

class NoFixError(Exception):
    pass

class GpsResponse(object):
    """ Class representing geo information returned by GPSD

    Use the attributes to get the raw gpsd data, use the methods to get parsed and corrected information.

    :type mode: int
    :type sats: int
    :type sats_valid: int
    :type lon: float
    :type lat: float
    :type alt: float
    :type track: float
    :type hspeed: float
    :type climb: float
    :type time: str
    :type error: dict[str, float]
    :type heading: float
    :type pitch: float
    :type roll: float

    :var self.mode: Indicates the status of the GPS reception, 0=No value, 1=No fix, 2=2D fix, 3=3D fix
    :var self.sats: The number of satellites received by the GPS unit
    :var self.sats_valid: The number of satellites with valid information
    :var self.lon: Longitude in degrees
    :var self.lat: Latitude in degrees
    :var self.alt: Altitude in meters
    :var self.track: Course over ground, degrees from true north
    :var self.hspeed: Speed over ground, meters per second
    :var self.climb: Climb (positive) or sink (negative) rate, meters per second
    :var self.time: Time/date stamp in ISO8601 format, UTC. May have a fractional part of up to .001sec precision.
    :var self.error: GPSD error margin information
    :var self.heading: heading, degrees from true north.
    :var self.pitch: pitch in degrees.
    :var self.roll: roll in degrees.

    GPSD error margin information
    -----------------------------

    c: ecp: Climb/sink error estimate in meters/sec, 95% confidence.
    s: eps: Speed error estinmate in meters/sec, 95% confidence.
    t: ept: Estimated timestamp error (%f, seconds, 95% confidence).
    v: epv: Estimated vertical error in meters, 95% confidence. Present if mode is 3 and DOPs can be
            calculated from the satellite view.
    x: epx: Longitude error estimate in meters, 95% confidence. Present if mode is 2 or 3 and DOPs
            can be calculated from the satellite view.
    y: epy: Latitude error estimate in meters, 95% confidence. Present if mode is 2 or 3 and DOPs can
            be calculated from the satellite view.
    """
    gpsTimeFormat = '%Y-%m-%dT%H:%M:%S.%fZ'

    def __init__(self):
        self.mode = 0
        self.sats = 0
        self.sats_valid = 0
        self.lon = 0.0
        self.lat = 0.0
        self.alt = 0.0
        self.track = 0
        self.hspeed = 0
        self.climb = 0
        self.time = ''
        self.error = {}
        self.heading = 0.0
        self.pitch = 0.0
        self.roll = 0.0

    def parse_tpv(self, last_tpv):
        self.mode = last_tpv['mode']

        if last_tpv['mode'] >= 2:
            self.lon = last_tpv['lon'] if 'lon' in last_tpv else 0.0
            self.lat = last_tpv['lat'] if 'lat' in last_tpv else 0.0
            self.track = last_tpv['track'] if 'track' in last_tpv else 0
            self.hspeed = last_tpv['speed'] if 'speed' in last_tpv else 0
            self.time = last_tpv['time'] if 'time' in last_tpv else ''
            self.error = {
                'c': 0,
                's': last_tpv['eps'] if 'eps' in last_tpv else 0,
                't': last_tpv['ept'] if 'ept' in last_tpv else 0,
                'v': 0,
                'x': last_tpv['epx'] if 'epx' in last_tpv else 0,
                'y': last_tpv['epy'] if 'epy' in last_tpv else 0
            }

        if last_tpv['mode'] >= 3:
            self.alt = last_tpv['alt'] if 'alt' in last_tpv else 0.0
            self.climb = last_tpv['climb'] if 'climb' in last_tpv else 0
            self.error['c'] = last_tpv['epc'] if 'epc' in last_tpv else 0
            self.error['v'] = last_tpv['epv'] if 'epv' in last_tpv else 0

    def parse_sky(self, last_sky):
        if 'satellites' in last_sky:
            self.sats = len(last_sky['satellites'])
            self.sats_valid = len(
                [sat for sat in last_sky['satellites'] if sat['used'] == True])
        else:
            self.sats = 0
            self.sats_valid = 0

    def parse_att(self, last_att):
        self.heading = last_att['heading'] if 'heading' in last_att else 0.0
        self.pitch = last_att['pitch'] if 'pitch' in last_att else 0.0
        self.roll = last_att['roll'] if 'roll' in last_att else 0.0

    def parse_poll(self, packet):
        """ parse a gpsd POLL response """
        if not packet['active']:
            raise UserWarning('GPS not active')
        self.parse_tpv(packet['tpv'][-1])
        self.parse_sky(packet['sky'][-1])

    def parse_packet(self, packet):
        """ parse a GPSD packet and override existing values """
        if packet['class'] == 'POLL':
            self.parse_poll(packet)
        elif packet['class'] == 'TPV':
            self.parse_tpv(packet)
        elif packet['class'] == 'SKY':
            self.parse_sky(packet)
        elif packet['class'] == 'ATT':
            self.parse_att(packet)

    @classmethod
    def from_json(cls, packet):
        """ Create GpsResponse instance based on the json data from GPSD
        :type packet: dict
        :param packet: JSON decoded GPSD response
        :return: GpsResponse
        """
        result = cls()
        result.parse_packet(packet)
        return result

    def position(self):
        """ Get the latitude and longtitude as tuple.
        Needs at least 2D fix.

        :return: (float, float)
        """
        if self.mode < 2:
            raise NoFixError("Needs at least 2D fix")
        return self.lat, self.lon

    def altitude(self):
        """ Get the altitude in meters.
        Needs 3D fix

        :return: (float)
        """
        if self.mode < 3:
            raise NoFixError("Needs at least 3D fix")
        return self.alt

    def movement(self):
        """ Get the speed and direction of the current movement as dict

        The speed is the horizontal speed.
        The climb is the vertical speed
        The track is te direction of the motion
        Needs at least 3D fix

        :return: dict[str, float]
        """
        if self.mode < 3:
            raise NoFixError("Needs at least 3D fix")
        return {"speed": self.hspeed, "track": self.track, "climb": self.climb}

    def speed_vertical(self):
        """ Get the vertical speed with the small movements filtered out.
        Needs at least 2D fix

        :return: float
        """
        if self.mode < 2:
            raise NoFixError("Needs at least 2D fix")
        if abs(self.climb) < self.error['c']:
            return 0
        else:
            return self.climb

    def speed(self):
        """ Get the horizontal speed with the small movements filtered out.
        Needs at least 2D fix

        :return: float
        """
        if self.mode < 2:
            raise NoFixError("Needs at least 2D fix")
        if self.hspeed < self.error['s']:
            return 0
        else:
            return self.hspeed

    def position_precision(self):
        """ Get the error margin in meters for the current fix.

        The first value return is the horizontal error, the second
        is the vertical error if a 3D fix is available

        Needs at least 2D fix

        :return: (float, float)
        """
        if self.mode < 2:
            raise NoFixError("Needs at least 2D fix")
        return max(self.error['x'], self.error['y']), self.error['v']

    def map_url(self):
        """ Get a openstreetmap url for the current position
        :return: str
        """
        if self.mode < 2:
            raise NoFixError("Needs at least 2D fix")
        return "http://www.openstreetmap.org/?mlat={}&mlon={}&zoom=15".format(self.lat, self.lon)

    def get_time(self, local_time=False):
        """ Get the GPS time

        :type local_time: bool
        :param local_time: Return date in the local timezone instead of UTC
        :return: datetime.datetime
        """
        if self.mode < 2:
            raise NoFixError("Needs at least 2D fix")
        if self.time == '' or self.time == None:
            rval = datetime.datetime.now().isoformat()
        else:
            rval = datetime.datetime.strptime(self.time, GpsResponse.gpsTimeFormat)

        if local_time:
            rval = time.replace(tzinfo=datetime.timezone.utc).astimezone()

        return rval

    def get_heading(self):
        """ Get the heading in degrees from true north.

        :return: float
        """
        return self.heading

    def get_pitch(self):
        """ Get the pitch in degrees.

        :return: float
        """
        return self.pitch

    def get_roll(self):
        """ Get the roll in degrees.

        :return: float
        """
        return self.roll

    def __repr__(self):
        modes = {
            0: 'No mode',
            1: 'No fix',
            2: '2D fix',
            3: '3D fix'
        }
        if self.mode < 2:
            return "<GpsResponse {}>".format(modes[self.mode])
        if self.mode == 2:
            return "<GpsResponse 2D Fix lat: {}, lon: {}, heading: {}>".format(self.lat, self.lon, self.heading)
        if self.mode == 3:
            return "<GpsResponse 3D Fix lat: {}, lon: {}, alt: {}, heading: {}, pitch: {}, roll: {}>".format(self.lat, self.lon, self.alt, self.heading, self.pitch, self.roll)
        
