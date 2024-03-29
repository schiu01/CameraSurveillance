import os
import logging
"""
    file_queue_deletion: This program is to remove files that are listed in /opt/surveillance/file_delete_queue/file_delete_queue.list
    The list is sent from delete button action in Web UI.

"""

queue_file = "/opt/surveillance/file_delete_queue/file_delete_queue.list"
tmp_queue_file = "/opt/surveillance/file_delete_queue/file_delete_queue.list.tmp"
# Rename the file to a temp file so it doesnt interfere with Web activity, if a delete is sent in.
try:
    if(os.path.exists(queue_file)):
        os.rename(queue_file, tmp_queue_file)
        fd = open(tmp_queue_file,"r")
        lines = fd.readlines()
        for line in lines:
            line = line.replace("\n","")
            file_attr = line.split("/")
            if(file_attr[-1].endswith(".mp4") and file_attr[-1].startswith("raw_capture_")):
                image_file = line.replace("raw_capture_","img_").replace(".mp4",".jpg")
                

                try:
                    logging.info(f"Removing video file {line}")
                    os.remove(line)
                    logging.info(f"Removing image file {image_file}")
                    os.remove(image_file)
                except Exception as e:
                    logging.warn(f"Error in removing file {line}")
                    logging.warn(f"Error in removing file {image_file}")

        os.remove(tmp_queue_file)
except Exception as e:
    print(f"Failed to rename file to temp file {e}")