from flask import Flask, render_template, Response, request, stream_with_context, session
from flask_session import Session
import sys
import cv2
import json as js
import subprocess
from datetime import datetime, timedelta
import os
import hashlib

## Initialise Flask and attach to session object.
app = Flask(__name__, static_folder='static')

## Sessions: https://www.geeksforgeeks.org/how-to-use-flask-session-in-python-flask/
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



## Set cap variavble for cv2 video capture from our RTSP Server
## The rtsp server gets feed from our standalone app running on our server.
#
cap = cv2.VideoCapture("rtsp://192.168.1.23:8554/surveillance")
connected = True


## Gen frames goes through frame by frame and sends it back as realtime
## this is a "backup method" versus HLS - Http Live Streaming option.
## this method does not support audio.
def gen_frames():
    try:
        while True:
            if(not connected):
                break 
            ret, frame = cap.read()
            if(ret):
            
                frame = cv2.resize(frame, (960,540), interpolation=cv2.INTER_AREA)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                ret, buffer = cv2.imencode(".png", frame, encode_param)
                frame = buffer.tobytes()
                yield(b'--frame\r\n'
                    b'Content-Type: image/png\r\n\r\n' + frame + b'\r\n')
    except GeneratorExit:
        pass
    
## main page.
@app.route("/")
def index():
    return render_template("recorded_videos.html")

@app.route("/cam")
def cam():
    connected = True
    return Response(stream_with_context(gen_frames()), mimetype="multipart/x-mixed-replace; boundary=frame")
@app.route("/static/recorded_videos/<path:path>")
def static_file(path):
    return app.send_static_file(f"/opt/surveillance/www/static/recorded_videos/{path}")

@app.route("/recorded_videos")
def recorded_videos():
    return render_template("recorded_videos.html")
@app.route("/list_videos_by_hour_mins")
def list_video_by_hour_mins():
    in_year = request.args.get("year")
    in_month = request.args.get("month")
    in_day = request.args.get("day")
    in_hour = request.args.get("hour")
    curr_date = datetime.now()
    
    if(in_year == None):
        in_year = curr_date.strftime("%Y")
        in_month = curr_date.strftime("%m")
        in_day = curr_date.strftime("%d")
        in_hour = curr_date.strftime("%H")
    else:
        in_year = in_year.zfill(2)
        in_month = in_month.zfill(2)
        in_day = in_day.zfill(2)
        in_hour = in_hour.zfill(2)

    files_query = f"raw_capture_{in_year}{in_month}{in_day}{in_hour}*.mp4"
    process = subprocess.Popen([f"/opt/surveillance/www/list_files.sh", files_query],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    metadata = []
    files_j = js.loads(out)
    videos = {}
    for f in files_j["files"]:
        filename = f["format"]["filename"].split("/")[-1]
        filename_first,ext = filename.split(".")
        filename_attr = filename_first.split("_")
        timestamp = filename_attr[-1]
        yy = timestamp[0:4]
        mm = timestamp[4:6]
        dd = timestamp[6:8]
        hh = timestamp[8:10]
        mi = timestamp[10:12]
        ss = timestamp[12:14]
        file_format = f["format"]["format_long_name"]
        duration = "{:.2f}s".format(float(f["format"]["duration"]))
        file_date = f"{yy}-{mm}-{dd} {hh}:{mi}:{ss}"

        bit_rate = f["format"]["bit_rate"]
        file_size = "{:.2f} mb".format(int(f["format"]["size"])/(1024*1024))
        title = f["format"]["tags"]["title"].replace("\\\"","")
        title_attr = title.split(" ")
        title = title_attr[0] + " " + title_attr[1] if len(title_attr) > 1 else ""
        comment = None
        if(f["format"].get("tags")):
            comment = f["format"]["tags"].get("comment")

        idx = (int(int(mi)/5)) * 5 
        if(videos.get(str(idx)) == None):
            videos[str(idx)] = []

        videos[str(idx)].append({"date": file_date, 
                            "filename": f["format"]["filename"].split("/")[-1],
                            "time": f"{hh}:{mi}:{ss}",
                            "title": title,
                            "duration": duration,
                            "bit_rate": bit_rate,
                            "file_size": file_size,
                            "comment": comment,
                            "file_format": file_format
                            })
                
        

    return js.dumps(videos)
    pass
@app.route("/list_videos_by_day_hour")
def list_videos_by_month_by_day_hour():
    in_year = request.args.get("year")
    in_month = request.args.get("month")
    in_day = request.args.get("day")
    curr_date = datetime.now()
    
    if(in_year == None):
        in_year = curr_date.strftime("%Y")
        in_month = curr_date.strftime("%m")
        in_day = curr_date.strftime("%d")
    else:
        in_year = in_year.zfill(2)
        in_month = in_month.zfill(2)
        in_day = in_day.zfill(2)


    videos_month = {}
    for base_dir, dirs, files in os.walk("/opt/surveillance/recorded_videos/"):
        for filename in files:
            if(filename.endswith(".mp4") and filename.startswith("raw_capture_")):
                file_first, ext = filename.split(".")
                file_attr = file_first.split("_")
                file_dated = file_attr[2]
                file_yy = file_dated[:4]
                file_mm = file_dated[4:6]
                file_dd = file_dated[6:8]
                file_hh = file_dated[8:10]
                file_date_str = f"{file_yy}-{file_mm}-{file_dd}"
                if(not (file_yy == in_year and file_mm == in_month and file_dd == in_day)):
                    print(file_first)
                    continue


                if(videos_month.get(file_hh) == None):
                    videos_month[file_hh] = 1
                else:
                    videos_month[file_hh] += 1

    return js.dumps(videos_month)

@app.route("/list_videos_by_day")
def list_videos_by_month_by_day():
    in_year = request.args.get("year")
    in_month = request.args.get("month")
    in_day = request.args.get("day")
    curr_date = datetime.now()
    
    if(in_year == None):
        in_year = curr_date.strftime("%Y")
        in_month = curr_date.strftime("%m")
        in_day = curr_date.strftime("%d")
    else:
        in_year = in_year.zfill(2)
        in_month = in_month.zfill(2)
        in_day = in_day.zfill(2)

    prior_year = "0"
    prior_month = "00"
    curr_month = datetime.strptime(f"{in_year}-{in_month}-01","%Y-%m-%d")
    prior_month_dt = curr_month + timedelta(days=-2)
    prior_month_str = prior_month_dt.strftime("%Y-%m")
    prior_year, prior_month = prior_month_str.split("-")


    videos_month = {}
    for base_dir, dirs, files in os.walk("/opt/surveillance/recorded_videos/"):
        for filename in files:
            if(filename.endswith(".mp4") and filename.startswith("raw_capture_")):
                file_first, ext = filename.split(".")
                file_attr = file_first.split("_")
                file_dated = file_attr[2]
                file_yy = file_dated[:4]
                file_mm = file_dated[4:6]
                file_dd = file_dated[6:8]
                file_date_str = f"{file_yy}-{file_mm}-{file_dd}"
                if(not ((file_yy == in_year and file_mm == in_month) or (file_yy == prior_year and file_mm == prior_month) )):
                    continue


                if(videos_month.get(file_date_str) == None):
                    videos_month[file_date_str] = 1
                else:
                    videos_month[file_date_str] += 1

    return js.dumps(videos_month)

@app.route("/admin_login")
def admin_login():
    return render_template("admin_login.html", data="")

@app.route("/admin_delete", methods=["POST"])
def admin_delete():
    if session.get("name"):
        if(session.get("name") == "admin"):

            files = request.form.getlist("video_file")
            delete_result = []

            ## /opt/surveillance/file_delete_queue is provided access to flask_user.
            fd = open("/opt/surveillance/file_delete_queue/file_delete_queue.list","a")
            for del_file in files:
                if(str(del_file).startswith("raw_capture_") and str(del_file).endswith(".mp4")):
                    try:
                        fd.write(f"/opt/surveillance/www/recorded_videos/{del_file}\n")
                        delete_result.append(f"{del_file} - Queued for deletion")
                    except Exception as e:
                        delete_result.append(f"{del_file} - Unsuccessful Add to queue - {e}")
                else:
                    delete_result.append(f"{del_file} - Unsuccessful")

                    
            return render_template("admin.html", data={"username": session.get('name'), "message": delete_result})
        else:
            return render_template("admin_login.html", data=f"Invalid User")
    else:
        return render_template("admin_login.html", data=f"Please Login {session.get('name')}")


@app.route("/admin", methods=["POST"])
def admin():
    user = request.form.get("username")
    md5_pass = request.form.get("md5_pass")
    md5_value = hashlib.md5(b"admin123").hexdigest()
    if md5_pass == md5_value:
        session["name"] = user
        return render_template("admin.html", data={"username": user, "message": ""})
    else:
        return render_template("admin_login.html", data=f"Failed Login User/Password!")
    
@app.route("/playvideo")
def playvideo():
    video_name = request.args.get("file")
    if(video_name == None):
        return render_template("index.html")
    if(video_name.endswith(".mp4")):
        return render_template("play_video.html",video_name=f"/surveillance/static/recorded_videos/{video_name}")
    else:
        return render_template("index.html")