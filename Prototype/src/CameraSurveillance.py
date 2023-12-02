import json as js
import base64
import cv2
class CameraSurveillance:
    def __init__(self):
        """
            Initialization routine for camera
            1. Read Configuration File
            
        """
        self.config = None
        self.config_file = "../config/camera_surveillance.config"
        self.read_config()

        self.frame_size = {"width": 0, "height": 0, "channels": 3}
        self.frame_resized = {"width": 0, "height": 0, "channels": 3}
        self.frame_small = {"width": 0, "height": 0, "channels": 3}

        self.camera_stop = False
        

        ## Set Previous Frame Value = for Absolute Difference

        pass
    def start(self):
        """
            Starts the Camera Surveillance system
        """
        self.init_capture()
    def read_config(self):
        fd = open(self.config_file,"r")
        self.config = js.load(fd)
        fd.close()
    def decode_password(self, enc_password):
        return  base64.b64decode(str(enc_password).encode('ascii')).decode('ascii')
    def build_rtsp_url(self):
        user = self.config["rtsp_user"]
        password = self.decode_password(self.config["rtsp_password"])
        url = self.config["rtsp_host_url"]
        return f"rtsp://{user}:{password}@{url}"
    def init_capture(self):
        """
            Initialization of cap objects of VideoCapture
            Detects Width/Height/Channels

        """
        self.cap = cv2.VideoCapture(self.build_rtsp_url())

        
        self.frame_size["width"] = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_size["height"] = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size["channels"] = int(self.cap.get(cv2.CAP_PROP_VIDEO_TOTAL_CHANNELS))

        self.frame_resized["width"] = int(self.frame_size["width"] * self.config["resize_ratio"])
        self.frame_resized["height"] = int(self.frame_size["height"] * self.config["resize_ratio"])

        self.frame_small["width"] = int(self.frame_size["width"] * self.config["resize_ratio"] * self.config["small_resize_ratio"])
        self.frame_small["height"] = int(self.frame_size["height"] * self.config["resize_ratio"] * self.config["small_resize_ratio"])

    def retrieve_frame(self):
        ret, frame = self.cap.read()
        if ret:
            return frame
        else:
            return None
        
    def loop_camera_frames(self):
        while(not self.camera_stop):
            frame = self.retrieve_frame()
            if(frame != None):
                self.process_frame(frame)

    def process_frame(self, frame):
        pass



