#!/bin/sh

workdir=/home/pi/bin/stationcontrol/radio
cd $workdir
/usr/bin/python $workdir/flex6k_monitor.py >/dev/null 2>&1 &
echo "Monitor started."
exit 0
