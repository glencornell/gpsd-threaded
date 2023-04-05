from gpsdclient import GPSDClient
from .gpsresponse import GpsResponse
import threading
import copy
import time

class ThreadedClient(threading.Thread):
    """
    This class is a threaded layer on top of the gpsdclient library.
    It's main purpose is to accumulate the latest TPV, SKY & ATT gpsd
    messages.

    Attributes:
        lock (threading.Lock): semaphore to prevent race conditions.
        gps (dict): The latest TPV, SKY and ATT reports as dictionary entries.
    """
    
    def __init__(self):
        """Class constructor."""
        threading.Thread.__init__(self)
        self._running = False
        self._lock = threading.Lock()
        self._gps = GpsResponse()
        self._gpsd = None
        self._host = None
        self._port = None

    def connect(self, host='127.0.0.1', port=2947):
        """Connect to gpsd and start the thread"""
        self._host = host
        self._port = port
        while True:
            try:
                self._gpsd = GPSDClient(self._host, self._port)
                break
            except ConnectionRefusedError:
                print('connection refused. sleep & try again.')
                time.sleep(1)
        self.start()

    def terminate(self):
        """ Terminate the running task."""
        self._running = False
        self.join()

    def get_current(self):
        """Get the last combined data"""
        with self._lock:
            rval = copy.deepcopy(self._gps)
        return rval

    def run(self):
        """Main loop: read and process gpsd messages."""
        self._running = True
        while self._running:
            try:
                for result in self._gpsd.dict_stream(convert_datetime=False):
                    if self._running == False:
                        break
                    with self._lock:
                        self._gps.parse_packet(result)
            except ConnectionRefusedError:
                print('connection refused. sleep & try again.')
                time.sleep(1)
                self._gpsd = GPSDClient(self._host, self._port)
