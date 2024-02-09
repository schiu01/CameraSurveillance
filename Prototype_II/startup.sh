#!/bin/sh

echo 'Starting Camera App...'
nohup python3 /opt/surveillance/run_camera_app.py &


echo 'Starting Live Stream...'
nohup /opt/surveillance/www/stream.sh &
~
