from flask import Flask, render_template, Response
from flask_socketio import SocketIO, disconnect
import sys
import cv2
import json as js
import subprocess

app = Flask(__name__, static_folder='static')


cap = cv2.VideoCapture("rtsp://192.168.1.23:8554/surveillance")
#cap = cv2.VideoCapture("http://192.168.1.23:8080/")
connected = True
socketio = SocketIO(app, async_mode=None)


def gen_frames():
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
    
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cam")
def cam():
    connected = True
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")
@app.route("/static/recorded_videos/<path:path>")
def static_file(path):
    return app.send_static_file(f"/opt/surveillance/www/static/recorded_videos/{path}")

@app.route("/recorded_videos")
def recorded_videos():
    return render_template("recorded_videos.html")
@app.route("/list_videos")
def list_videos():
    process = subprocess.Popen(["/opt/surveillance/www/list_files.sh"],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    metadata = []
    #fd = open("/opt/surveillance/www/myformat.json","r")
    #files_j = js.load(fd)
    #fd.close()
    files_j = js.loads(out)
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
        duration = f["format"]["duration"]
        file_date = f"{yy}-{mm}-{dd} {hh}:{mi}:{ss}"

        bit_rate = f["format"]["bit_rate"]
        file_size = f["format"]["size"]
        title = f["format"]["tags"]["title"].replace("\\\"","")
        comment = None
        if(f["format"].get("tags")):
            comment = f["format"]["tags"].get("comment")
        metadata.append({"filename": filename, "file_date": file_date,
            "file_format": file_format, "duration": duration, "file_size": file_size,"title": title,"comment":comment,
            "bit_rate": bit_rate})

    #return render_template("list_videos.html",files=metadata)   
    return js.dumps(metadata)


@socketio.on("connect")
def connect():
    print("Connect...",file=sys.stderr)
    connected=True

@socketio.on('disconnect')
def disconnect():
    print("Disconnecting...",file=sys.stderr)
    connected = False
#if __name__ == "__main__":
#    app.run(debug=True, port=5000, host='0.0.0.0')
