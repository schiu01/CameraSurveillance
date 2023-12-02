import json as js
import base64
import cv2
class BackgroundSubtraction:
    def __init__(self, bs_type):
        self.prev_frame = None
        if(bs_type == None):
            self.bs_type = "absdiff"
        else:
            self.bs_type = bs_type
    
    def get_fgmask(self, frame):

        self.update_background(frame)
        pass
    def update_background(self, frame):
        pass

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
        
        self.background_mask = BackgroundSubtraction(bs_type=self.config["background_subtraction_method"])
        
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

        self.frame_resized["width"] = self.config["resized_frame_w"]
        self.frame_resized["height"] = self.config["resized_frame_h"]

        self.frame_small["width"] = self.config["small_frame_w"]
        self.frame_small["height"] = self.config["small_frame_h"]

    def retrieve_frame(self):
        """
            Image Retrieval from Camera.
        """
        ret, frame = self.cap.read()
        if ret:
            return frame
        else:
            return None
        
    def loop_camera_frames(self):
        """
            Continuously Capture Frames from Camera.
        """
        while(not self.camera_stop):
            frame = self.retrieve_frame()
            if(frame != None):
                self.process_frame(frame)


    def process_frame(self, frame):
        resized_frame, small_frame, gray_frame = self.augment_frame(frame)
        fg_mask = self.background_mask.get_fgmask(gray_frame)
        pass
    def augment_frame(self, frame):
        """
            Augment Frame is to resize frame to display frame (smaller than original) 
        """
        resized_frame = cv2.resize(frame, (self.frame_resized["width"], self.frame_resized["height"]), interpolation=cv2.INTER_AREA)
        gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
        small_frame = cv2.resize(gray_frame, (self.frame_small["width"], self.frame_small["height"]), interpolation=cv2.INTER_AREA)

        return resized_frame, small_frame, gray_frame



