from flask import Flask, render_template, Response
import cv2

app = Flask(__name__)


#cap = cv2.VideoCapture("rtsp://admin:Spring01!@192.168.1.28/cam/realmonitor?channel=4&subtype=0")
cap = cv2.VideoCapture("rtsp://admin:Spring01!@192.168.1.19/cam/realmonitor?channel=4&subtype=0")


def gen_frames():
    while True:
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
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')