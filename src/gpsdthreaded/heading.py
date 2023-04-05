#!/usr/bin/env python3
"""
Connect to a running gpsd instance and show human readable output.
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from .threadedclient import ThreadedClient
import time
import json

def print_gps(gps):
    # TODO: print more human-readable form of the gspResponse object.
    # Maybe using curses?  For now, just dump it in json.
    print(json.dumps(gps.__dict__, default=lambda o: o.__dict__))

def stream_readable(gpsd):
    # Get gps position.  It's a dictionary of the last received
    while True:
        x = gpsd.get_current()
        print_gps(x)
        # to prevent excessive CPU utilization:
        time.sleep(1)

def stream_json(gpsd):
    while True:
        x = gpsd.get_current()
        print(json.dumps(x.__dict__, default=lambda o: o.__dict__))
        # to prevent excessive CPU utilization:
        time.sleep(1)

def main():
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter,
        description=__doc__,
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="The host running GPSD",
    )
    parser.add_argument(
        "--port",
        default="2947",
        help="GPSD port",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON strings",
    )
    args = parser.parse_args()

    try:
        gpsd = ThreadedClient()
        gpsd.connect(host=args.host, port=args.port, convert_datetime=True)
        if args.json:
            stream_json(gpsd)
        else:
            stream_readable(gpsd)
    except (ConnectionError, EnvironmentError) as e:
        print(e)
    except KeyboardInterrupt:
        gpsd.terminate()
        print()
        return 0

