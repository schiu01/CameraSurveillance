#!/bin/sh

FILE_DIR=/opt/surveillance/recorded_videos
total_files=`ls ${FILE_DIR}/raw_*.mp4|wc -l`
current_line=0
echo "{\"files\":[" > /tmp/myformat.json
for x in `ls ${FILE_DIR}/raw_*.mp4`
do
	current_line=$(($current_line + 1))
	ffprobe -v quiet -print_format json -show_format $x >> /tmp/myformat.json
	if [ $current_line -ne $total_files ]; then
		echo "," >> /tmp/myformat.json
	fi
done
echo "]}" >> /tmp/myformat.json
cat /tmp/myformat.json
rm /tmp/myformat.json
