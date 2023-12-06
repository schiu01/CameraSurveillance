import json as js
import base64
import cv2
import numpy as np
class BackgroundSubtraction:
    def __init__(self, bs_type):
        self.prev_frame = None
        self.prev_init_done = False
        self.pixels_changed_pct = 0




        if(bs_type == None):
            self.bs_type = "absdiff"
        else:
            self.bs_type = bs_type
    
    def get_fgmask(self, frame):
        if(self.bs_type == "absdiff"):
            return self.get_fgmask_absdiff(frame)
        else:
            return None
    def get_fgmask_absdiff(self, frame):
        """
            Iteration 1: The framesize was large at 1280 x 720 pixels, reduced to 320 x 180 pixels for more efficiency
            Iteration 2: Added thresholding of pixel values, all pixesl > X are converted to white pixes, others are black.
            first setting of x = 65, some pixels that should be positive are not captured, we will set it to 50.

            Issues and Resolutions added to iterations.:
            1. Sudden changes in lighting environment causing most pixels to change - to remediate this, we will set a threshold on % of pixels changed. 
            if it is over 50% changed, we know it may be attributed to the environment
            so we skip that frame and present the previous frame.
            2. on a breezy day, the tree wavers and causing pixels to change - we will add some gaussian blur so the difference betwen pixels of those small changes are not significant.
            3. Pixelated foreground mask - we will dilate the pixels so the blobs come together as larger blob (contours).
            Iteration 3: Use the lower screen on the window to display some stats and add the foreground mask in that area instead of another window.
            Iteration 4: Background update is changed to store x # of frames of history and an average is taken over those frames as background to be subtracted
        
        """
        resized_frame = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
        if(self.prev_init_done == False):
            self.prev_frame = resized_frame
            self.prev_init_done = True
        
        diff_frame = cv2.absdiff(self.prev_frame, resized_frame)


        ret, diff_frame = cv2.threshold(diff_frame, 30, 255, cv2.THRESH_BINARY)
        if(ret):
            self.update_background_absdiff(resized_frame)
            ## Keep count on # pixels changed
            self.pixels_changed_pct = int(100 * np.count_nonzero(diff_frame) / (diff_frame.shape[0] * diff_frame.shape[1]))

        
        return diff_frame
        


    def update_background_absdiff(self, frame):
        self.prev_frame = frame
        

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
        self.loop_camera_frames()
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
        return self.cap.read()
        
    def loop_camera_frames(self):
        """
            Continuously Capture Frames from Camera.
        """
        while(not self.camera_stop):
            ret, frame = self.retrieve_frame()
            if(ret):
                self.process_frame(frame)


    def process_frame(self, frame):
        """
            Subroutine to process frame
            1. Augment the size of the frame to workable one for BG Subtraction and saving.
            2. Retrieve foreground mask via BackGround Subtraction Class.
            3. Retrieve the contours (blobs) from the foreground
            4. Appply the contours on the resized frame to get only the area of the frame that moved
            5. Pass into Yolo Model
        """

        resized_frame, small_frame, gray_frame = self.augment_frame(frame)
        fg_mask = self.background_mask.get_fgmask(gray_frame)
        #print(f"% Pixel Change: {self.background_mask.pixels_changed_pct}%")

        ## Use an area at bottom of window to show fgmask and frame stats
        resized_frame[0:self.frame_resized["height"], self.frame_resized["width"]-fg_mask.shape[1]:self.frame_resized["width"]] = cv2.cvtColor(fg_mask,cv2.COLOR_GRAY2BGR)


        self.show_window(resized_frame)
        
        pass
    def augment_frame(self, frame):
        """
            Augment Frame is to resize frame to display frame (smaller than original) 
        """
        resized_frame = cv2.resize(frame, (self.frame_resized["width"], self.frame_resized["height"]), interpolation=cv2.INTER_AREA)
        gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
        small_frame = cv2.resize(gray_frame, (self.frame_small["width"], self.frame_small["height"]), interpolation=cv2.INTER_AREA)

        return resized_frame, small_frame, gray_frame
    def show_window(self, frame, windowname="cv2"):
        cv2.imshow(windowname, frame)
        x  = cv2.waitKey(1)
        if x == 27:
            cv2.destroyAllWindows()
            self.cap.release()
            self.camera_stop = True



