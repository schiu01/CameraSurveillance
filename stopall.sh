#!/bin/sh
echo 'Killing Camera app...'
for x in `ps -aux | grep run_camera_app | grep python  | awk '{print $2}'`; do kill $x; done

echo 'Killing Live Stream...'
for x in `ps -aux | grep ffmpeg | grep surveillance  | awk '{print $2}'`; do kill $x; done
