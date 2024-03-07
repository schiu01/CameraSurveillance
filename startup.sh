#!/bin/sh

echo 'Starting Camera App...'
nohup python3 /opt/surveillance/run_camera_app.py >> /dev/null&

