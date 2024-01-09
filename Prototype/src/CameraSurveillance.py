import json as js
import base64
import cv2
import numpy as np
from datetime import datetime
from BackgroundSubtraction import BackgroundSubtraction
from time import sleep
from ObjectDection import ObjectDetection

      

class CameraSurveillance:
    def __init__(self):
        """
            Initialization routine for camera
            1. Read Configuration File
            
        """
        self.config = None
        self.config_file = "../config/camera_surveillance.config"
        self.read_config()

        ## Initialization of frame sizes
        self.frame_size = {"width": 0, "height": 0, "channels": 3}
        self.frame_resized = {"width": 0, "height": 0, "channels": 3}
        self.frame_small = {"width": 0, "height": 0, "channels": 3}
        
        
        ## Stop the camera loop
        self.camera_stop = False
        
        ## custom background mask class. input is background masking type = mog2 or absdiff
        self.background_mask = BackgroundSubtraction(bs_type=self.config["background_subtraction_method"])
        
        ## Set Previous Frame Value = for Absolute Difference
        self.save_video = self.config.get("save_video")

        ## Date time for filename saved as.
        self.datetime = datetime.now().strftime("%Y%m%d")
        self.output_file = f"raw_capture_{self.datetime}.mp4"

        ## Yolo Object
        self.obj_detection = ObjectDetection()

        # Version Info
        self.version_info = self.config["version_info"]
        

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

        ## Open the source as filehandle
        if self.config.get("source") == "rtsp":
            self.cap = cv2.VideoCapture(self.build_rtsp_url())
        elif self.config.get("source") == "video_file":
            self.cap =  cv2.VideoCapture(self.config.get("video_file"))
            print(self.cap.get(cv2.CAP_PROP_FPS))
            self.cap.set(cv2.CAP_PROP_FPS, 5)
            print(self.cap.get(cv2.CAP_PROP_FPS))

        ## Set the framesizes from source.
        self.frame_size["width"] = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_size["height"] = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size["channels"] = int(self.cap.get(cv2.CAP_PROP_VIDEO_TOTAL_CHANNELS))

        ## Set resized frame values from configuration
        self.frame_resized["width"] = self.config["resized_frame_w"]
        self.frame_resized["height"] = self.config["resized_frame_h"]

        self.frame_small["width"] = self.config["small_frame_w"]
        self.frame_small["height"] = self.config["small_frame_h"]
        
        ## Set and update fgmask width and height.
        self.fgmask_ratio = self.frame_resized["width"] / self.frame_small["width"] 
        

        if(self.save_video):
            four_cc = cv2.VideoWriter_fourcc(*'mp4v')
            self.record_out = cv2.VideoWriter(self.output_file, four_cc, 15.0, (self.frame_resized["width"],self.frame_resized["height"]))
            
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
                #sleep(0.2)


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
        orig_fg_mask, fg_mask = self.background_mask.get_fgmask(small_frame)

        #print(f"% Pixel Change: {self.background_mask.pixels_changed_pct}%")

        ## After get fgmask, we need to identify all the blobs on the screen.
        ### We will use opencv's contours
        contours, hierarchy = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        fgmask_new = np.zeros(( self.frame_resized["height"],self.frame_resized["width"]), dtype="uint8")
        roi_frame = np.zeros(( self.frame_resized["height"],self.frame_resized["width"],3), dtype="uint8")
        total_blobs = 0
        total_objects = 0
        for i, ctr in enumerate(contours):
            ctr_area = cv2.contourArea(ctr)
            (x,y,w,h) = cv2.boundingRect(ctr)
            if(ctr_area > 250 or h > 50):
                
                if(hierarchy[0][i][3] == -1):
                    total_blobs += 1
                    ctr_resized = np.multiply(ctr, self.fgmask_ratio).astype(int)
                    (cx, cy, cw, ch) = cv2.boundingRect(ctr_resized)
                    cv2.rectangle(fgmask_new, (cx, cy), (cx+cw, cy+ch), (1,1), -1 )
                    #cv2.rectangle(resized_frame, (cx, cy), (cx+cw, cy+ch), (0,255,0), 2 )
                    ## Get the Regions of Interests
                    ## Apppy bitwise and with fgmask, and retrieve the ROIs.
        if(total_blobs > 0):
            roi_frame = cv2.bitwise_and(resized_frame,resized_frame, mask=fgmask_new)

            obj_detection_results = self.obj_detection.detect(roi_frame)
            resized_frame, total_objects = self.obj_detection.boundBox(inp_frame=resized_frame,
                                                           results=obj_detection_results,
                                                           img_ratio=1,
                                                           confidence_level=0.6)

                    

                
        #contours, hierarchy = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        # for i, ctr in enumerate(contours):
        #     ctr_area = cv2.contourArea(ctr)
        #     if(ctr_area > 100):
        #         ctr_resized = np.multiply(ctr, self.fgmask_ratio).astype(int)
        #         cv2.polylines(resized_frame,ctr_resized, True, (0,0,255), 2 )




        ## Original FG Mask without any dilation etc..
        resized_frame[self.frame_resized["height"]-fg_mask.shape[0]:self.frame_resized["height"], 0:fg_mask.shape[1]] = cv2.cvtColor(orig_fg_mask,cv2.COLOR_GRAY2BGR)

        ## Use an area at bottom of window to show fgmask and frame stats
        resized_frame[self.frame_resized["height"]-fg_mask.shape[0]:self.frame_resized["height"], 321:321+fg_mask.shape[1]] = cv2.cvtColor(fg_mask,cv2.COLOR_GRAY2BGR)

        ## Add black box and add text for stats
        cv2.rectangle(resized_frame, (3*fg_mask.shape[1]+3,self.frame_resized["height"]-fg_mask.shape[0]),(4*fg_mask.shape[1]+4,self.frame_resized["height"]), (20,20,20),-1)
        
        # Yolo Input
        roi_frame_resized = cv2.resize(roi_frame,(320,180), interpolation=cv2.INTER_AREA)
        resized_frame[self.frame_resized["height"]-roi_frame_resized.shape[0]:self.frame_resized["height"], 
                      2*fg_mask.shape[1]+2:2*fg_mask.shape[1] + roi_frame_resized.shape[1]+2] = roi_frame_resized

        cv2.putText(resized_frame,"Original FG Mask",[0,self.frame_resized["height"]-fg_mask.shape[0]-2],cv2.FONT_HERSHEY_COMPLEX,0.7,(0,255,0),1)
        cv2.putText(resized_frame,"Augmented FG Mask",[321,self.frame_resized["height"]-fg_mask.shape[0]-2],cv2.FONT_HERSHEY_COMPLEX,0.7,(0,255,0),1)
        cv2.putText(resized_frame,"Yolo Model Input",[(321*2),self.frame_resized["height"]-fg_mask.shape[0]-2],cv2.FONT_HERSHEY_COMPLEX,0.7,(0,255,0),1)
        cv2.putText(resized_frame,"Info",[(321*3),self.frame_resized["height"]-fg_mask.shape[0]-2],cv2.FONT_HERSHEY_COMPLEX,0.7,(0,255,0),1)

        ## For debug version info
        cv2.rectangle(resized_frame, (300,0,800,30) , (20,20,20),-1)
        cv2.putText(resized_frame,self.version_info,(310,20), cv2.FONT_HERSHEY_COMPLEX,0.7,(0,0,255),1)


        ## Pixels Changed
        
        text_pos_x = 3*fg_mask.shape[1] + 4
        cv2.putText(resized_frame,f"Video Source: {self.config.get('source')}",
            [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+15],
            cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,0,255),
            1)

        cv2.putText(resized_frame,f"BS Type: {self.background_mask.bs_type}",
                    [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+30],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,0,255),
                    1)

        cv2.putText(resized_frame,f"Pixels Changed %: {self.background_mask.pixels_changed_pct} %",
                    [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+45],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,255,255),
                    1)
        cv2.putText(resized_frame,f"Pixels Changed : {self.background_mask.pixels_changed}",
                    [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+60],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,255,255),
                    1)
        cv2.putText(resized_frame,f"Total Pixels : 57.6k",
                    [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+75],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,255,255),
                    1)
        cv2.putText(resized_frame,f"Detected Objects #(Yolo): " + str(total_objects),
                    [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+90],
                    cv2.FONT_HERSHEY_COMPLEX_SMALL,0.8,(0,255,255),
                    1)        
        self.show_window(resized_frame)
        
        if self.save_video:
            self.record_out.write(resized_frame)
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



