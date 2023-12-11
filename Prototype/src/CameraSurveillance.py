import json as js
import base64
import cv2
import numpy as np
from datetime import datetime
class BackgroundSubtraction:
    def __init__(self, bs_type):
        self.prev_frame = None
        self.prev_init_done = False
        self.pixels_changed_pct = 0
        self.pixels_changed = 0

        self.prev_history_frames = []
        self.total_history_frames = 5
        self.prev_history_index = 0 ## Pointer on where the current history is, for update and retrieval.




        if(bs_type == None):
            self.bs_type = "absdiff"
        else:
            self.bs_type = bs_type
        

        ## Mixture of Gradients BS.
        if(self.bs_type == "mog2"):
            self.backsub = cv2.createBackgroundSubtractorMOG2(history=100)
    


    def get_fgmask(self, frame):
        fgmask = None
        if(self.bs_type == "absdiff"):
            fgmask =  self.get_fgmask_absdiff(frame)
        elif(self.bs_type == "mog2"):
            ## https://docs.opencv.org/4.x/d1/dc5/tutorial_background_subtraction.html
            fgmask =  self.get_fgmask_mog2(frame)

        if(fgmask.size != 0):
            self.pixels_changed = np.count_nonzero(fgmask)
            self.pixels_changed_pct = int(100 * self.pixels_changed / np.size(fgmask))
            return fgmask

    def get_history_indexes(self):
        idx = []
        for x in range(self.prev_history_index, self.total_history_frames):
            idx.append(x)
        for x in range(0,self.prev_history_index):
            idx.append(x)
        return idx
    def get_fgmask_mog2(self,frame):
        resized_frame = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
        resized_frame = cv2.GaussianBlur(resized_frame,(3,3),0) 
        fgmask = self.backsub.apply(resized_frame)
        ret, fgmask = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
        fgmask = cv2.dilate(fgmask,None,iterations=2)
        return fgmask

    def get_fgmask_absdiff(self, frame):
        """
            Iteration 1: The framesize was large at 1280 x 720 pixels, reduced to 320 x 180 pixels for more efficiency
            Iteration 2: Added thresholding of pixel values, all pixesl > X are converted to white pixes, others are black.
            first setting of x = 65, some pixels that should be positive are not captured, we will set it to 50
            Iteration 3: Added 5 frame differential with max difference being extracted.
            Iteration 4: added gaussian blur to incoming frames.

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

        # ## Iteraiton 4: Added Gaussian Blur to minimize small movements.
        resized_frame = cv2.GaussianBlur(resized_frame,(3,3),0) 

        if(self.prev_init_done == False):

            # Iteration 3 - multi frame differentials
            for x in range(0, self.total_history_frames):
                self.prev_history_frames.append(resized_frame)
            self.prev_frame = resized_frame
            self.prev_history_index = 0
            self.prev_init_done = True
        diff_frames = []
        for frame_idx in self.get_history_indexes():
            df = cv2.absdiff(self.prev_history_frames[frame_idx], resized_frame)
            diff_frames.append(df)

        diff_frame = np.maximum(diff_frames[0], diff_frames[1])

        ## Get max differential values.
        for idx in range(2,self.total_history_frames):
            diff_frame = np.maximum(diff_frame, diff_frames[idx])
            

        ## Set threshold for any pixels > 50 to 255 and others to 0..
        ret, diff_frame = cv2.threshold(diff_frame, 50, 255, cv2.THRESH_BINARY)
        diff_frame = cv2.dilate(diff_frame,None, iterations=2)
        if(ret):
            self.update_background_absdiff(resized_frame)
            ## Keep count on # pixels changed
            




        ## Test

        # if(self.prev_init_done == False):
        #     self.prev_frame = resized_frame
        #     self.prev_init_done = True
        # diff_frame = cv2.absdiff(self.prev_frame, resized_frame)
        # self.update_background_absdiff(resized_frame)
        return diff_frame
        


    def update_background_absdiff(self, frame):
        self.prev_frame = frame
        # self.prev_history_frames[self.prev_history_index] = frame
        # self.prev_history_index = (self.prev_history_index + 1) % self.total_history_frames

        

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
        self.save_video = self.config.get("save_video")
        self.datetime = datetime.now().strftime("%Y%m%d")
        self.output_file = f"raw_capture_{self.datetime}.mp4"



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
        self.cap = None
        if self.config.get("source") == "rtsp":
            self.cap = cv2.VideoCapture(self.build_rtsp_url())
        elif self.config.get("source") == "video_file":
            self.cap =  cv2.VideoCapture(self.config.get("video_file"))
            print(self.cap.get(cv2.CAP_PROP_FPS))
            self.cap.set(cv2.CAP_PROP_FPS, 5)
            print(self.cap.get(cv2.CAP_PROP_FPS))

        
        self.frame_size["width"] = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_size["height"] = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size["channels"] = int(self.cap.get(cv2.CAP_PROP_VIDEO_TOTAL_CHANNELS))

        self.frame_resized["width"] = self.config["resized_frame_w"]
        self.frame_resized["height"] = self.config["resized_frame_h"]

        self.frame_small["width"] = self.config["small_frame_w"]
        self.frame_small["height"] = self.config["small_frame_h"]
        four_cc = cv2.VideoWriter_fourcc(*'mp4v')

        self.fgmask_ratio = self.frame_resized["width"] / 320 

        if(self.save_video):
            self.record_out = cv2.VideoWriter(self.output_file, four_cc, 17.0, (self.frame_size["width"],self.frame_size["height"]))
        else:
            self.record_out = None

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
                if(frame.size == 0):
                    break
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

        ## After get fgmask, we need to identify all the blobs on the screen.
        ### We will use opencv's contours
        contours, hierarchy = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for i, ctr in enumerate(contours):
            ctr_area = cv2.contourArea(ctr)
            if(ctr_area > 100):
                if(hierarchy[0][i][3] == -1):
                    (cx, cy, cw, ch) = cv2.boundingRect(ctr)
                    cx = int(cx * self.fgmask_ratio)
                    cy = int(cy * self.fgmask_ratio)
                    cw = int(cw * self.fgmask_ratio)
                    ch = int(ch * self.fgmask_ratio)
                    cv2.rectangle(resized_frame, (cx, cy), (cx+cw, cy+ch), (0,0,255), 2 )

                





        ## Use an area at bottom of window to show fgmask and frame stats
        resized_frame[self.frame_resized["height"]-fg_mask.shape[0]:self.frame_resized["height"], 0:fg_mask.shape[1]] = cv2.cvtColor(fg_mask,cv2.COLOR_GRAY2BGR)
        cv2.putText(resized_frame,"FG Mask",[0,self.frame_resized["height"]-fg_mask.shape[0]],cv2.FONT_HERSHEY_COMPLEX,0.7,(0,255,0),1)

        ## Add black box and add text for stats
        cv2.rectangle(resized_frame, (fg_mask.shape[1]+2,self.frame_resized["height"]-fg_mask.shape[0]),(2*fg_mask.shape[1],self.frame_resized["height"]), (0,0,0),-1)

        ## Pixels Changed
        cv2.putText(resized_frame,f"BS Type: {self.background_mask.bs_type}",
                    [fg_mask.shape[1]+3,self.frame_resized["height"]-fg_mask.shape[0]+15],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,0,255),
                    1)

        cv2.putText(resized_frame,f"Pixels Changed %: {self.background_mask.pixels_changed_pct} %",
                    [fg_mask.shape[1]+3,self.frame_resized["height"]-fg_mask.shape[0]+30],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,255,255),
                    1)
        cv2.putText(resized_frame,f"Pixels Changed : {self.background_mask.pixels_changed}",
                    [fg_mask.shape[1]+3,self.frame_resized["height"]-fg_mask.shape[0]+45],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,255,255),
                    1)
        cv2.putText(resized_frame,f"Total Pixels : 57.6k",
                    [fg_mask.shape[1]+3,self.frame_resized["height"]-fg_mask.shape[0]+60],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,255,255),
                    1)
        self.show_window(resized_frame)
        
        if self.save_video:
            self.record_out.write(frame)
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
            if(self.save_video):
                self.record_out.release()



