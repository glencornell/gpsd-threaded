# GPSD Threaded Client

This is a simple python library that connects to a
[GPSD](https://gpsd.io/) server and prints out
[TPV](https://gpsd.gitlab.io/gpsd/gpsd_json.html#_tpv),
[SKY](https://gpsd.gitlab.io/gpsd/gpsd_json.html#_sky) and
[ATT](https://gpsd.gitlab.io/gpsd/gpsd_json.html#_att) reports.

If the GPS device has an INS and gpsd is able to interpret messages,
then the `ATT` report will contain vehicle attitude (heading, pitch, &
roll).

## License

Copyright, 2023.  Glen Cornell.  See the [LICENSE](LICENSE) file for details.
