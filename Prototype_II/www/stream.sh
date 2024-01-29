#!/bin/sh
ffmpeg -fflags +genpts \
 -loglevel info \
 -rtsp_transport tcp \
 -i rtsp://192.168.1.23:8554/surveillance \
 -metadata title=LIVE \
 -copyts \
 -vcodec copy \
 -movflags frag_keyframe+empty_moov \
 -crf 5 \
 -an \
 -hls_flags delete_segments+append_list \
 -f hls \
 -hls_time 1 \
 -hls_list_size 3 \
 -hls_segment_type mpegts \
 -hls_segment_filename './static/stream/%d.ts' \
./static/stream/playlist.m3u8
