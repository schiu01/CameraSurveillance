#!/bin/sh

echo 'Starting Camera App...'
nohup python3 /opt/surveillance/run_camera_app.py >> /dev/null&


echo 'Starting Live Stream...'
echo 'Sleeping for 5 seconds for camera app to start up... '
sleep 5
nohup /opt/surveillance/www/stream.sh >> /dev/null &
