import json as js
import base64
import cv2
import numpy as np
from datetime import datetime
from BackgroundSubtraction import BackgroundSubtraction
from time import sleep
from ObjectDection import ObjectDetection
from ObjectTracker import ObjectTracker
from threading import Thread
from multiprocessing.pool import Pool
from queue import Queue
import subprocess as sp
import os
import ffmpeg
import threading
from Notification import ProjectAlert
c =  threading.Condition()
process = None
http_start = False



class CameraSurveillance:
    def __init__(self):
        """
            Purpose: 
                CameraSurveillance Object is the main interface with the camera to retrieve frames
                and provides the frames to Background Subtraction Module to be processed.
                It also interfaces with Object Detection and Tracking Modules.
                The output frames are sent to an rtsp server for further distribution downstream.
            
            Notes:
                Camera Surveillance is driven by configuration file camera_surveillance.config
                The rtsp url to our source camera is an entry within the config file.
            
            Libraries used:
                OpenCV - for Retrieval of Camera frames and processing of the frames such as resizing.
                queue - For Queueing of frames for saving into a file via multi-threading - for smoother experience.
                ffmpeg - to form ffmpeg parameters.
            
            run: 
                The module, after init, is kicked off using "start" function.

            
        """
        self.config = None
        self.config_file = "./config/camera_surveillance.config"
        self.read_config()

        ## Debug flag to show stats
        self.debug = self.config.get("debug")

        ## Initialization of frame sizes
        self.frame_size = {"width": 0, "height": 0, "channels": 3}
        self.frame_resized = {"width": 0, "height": 0, "channels": 3}
        self.frame_small = {"width": 0, "height": 0, "channels": 3}
        
        
        ## Stop the camera loop
        self.camera_stop = False
        
        ## custom background mask class. input is background masking type = mog2 or absdiff
        self.background_mask = BackgroundSubtraction(bs_type=self.config["background_subtraction_method"])
        
        ## Save Video when detection is alerted.
        self.save_video = self.config.get("save_video_on_alert")
        self.object_detected_start = False
        self.object_detected_starttime = None
        self.object_detected_endtime = None
        self.video_comments = {}
        self.video_title = None

        ## Record 3 more seconds AFTER object is no longer detected; so if another object comes to scene it continues recording.
        self.record_extra_frame_count = 0 
        self.total_extra_frames_recorded = (5*15) ## 5 seconds additional.

        ## Date time for filename saved as.
        self.datetime = datetime.now().strftime("%Y%m%d")
        self.output_file = f"raw_capture_{self.datetime}.mp4"

        ## Yolo Object
        self.obj_detection = ObjectDetection()

        # Object Tracker
        show_centroid_trail = self.config["object_tracker_centroid_trail"]
        centroid_max_distance = self.config["centroid_max_distance"]
        self.obj_tracker = ObjectTracker(centroid_max_distance, show_centroid_trail, self.debug)

        # Version Info
        self.version_info = self.config["version_info"]

        ## Multi processing for smoother experience and handling of saving of videos in a separate cpu
        num_cpu = cv2.getNumberOfCPUs()
        self.pool = Pool(processes=num_cpu)
        
        ## queue created for multiprocessing. 
        ## where read from frames and post-processing frame is added to queue
        ## and another cpu to read from frames and save video if required.
        ## the save video also triggers notification
        self.image_queue = Queue()
        self.notify_queue = Queue()
        

        ## Notification Flag
        self.notify_users = self.config.get("send_notifications")
        self.alert = ProjectAlert()
        self.alert_words = self.config["notification_alert_hot_words"]

    def alerting(self):
        while(not self.camera_stop):
            try:
                alert_message = self.notify_queue.get(block=False)
                subject = alert_message.get("subject")
                message = alert_message.get("message")
                message_words = message.split(" ")
                send_alert = False
                for m in message_words:
                    if(m in self.alert_words):
                        send_alert = True
                        break
                if(send_alert):
                    self.alert.send_email(subject, message)
            except Exception as e:
                sleep(10)

    def send_alert_queue(self, object):
        self.notify_queue.put(object, block=False)
    def start(self):
        """
            Starts the Camera Surveillance system
        """
        self.init_capture()
        th1 = Thread(name="read_thread", target=self.loop_camera_frames)
        th1.start()
        th2 = Thread(name="save_frame", target=self.save_video_frames)
        th2.start()
        th3 = Thread(name="http_stream", target=self.http_stream)
        th3.start()
        if(self.notify_users):
            print("Starting Notifications System...")
            th4 = Thread(name="alerting", target=self.alerting )
            th4.start()
        else:
            print("Notification System is not active.")
        th1.join()
        th2.join()
#        th3.join()
        #self.loop_camera_frames()

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
        

        # if(self.save_video):
        #     four_cc = cv2.VideoWriter_fourcc(*'mp4v')
        #     self.record_out = cv2.VideoWriter(self.output_file, four_cc, 15.0, (self.frame_resized["width"],self.frame_resized["height"]))
            
        # else:
        #     self.record_out = None
        self.record_out = None
        self.ffmpeg = 'ffmpeg'
        self.dimension = '{}x{}'.format(self.frame_resized["width"],self.frame_resized["height"])

    def retrieve_frame(self):
        """
            Image Retrieval from Camera.
        """
        return self.cap.read()
        
    def queue_frame(self, frame):
        self.image_queue.put_nowait(frame)
    def save_video_frames(self):
        
            while(not self.camera_stop or self.image_queue.qsize() > 0):
                
                if(self.image_queue.qsize() == 0 or not self.save_video):
                    sleep(0.1)
                    continue
                frame = None
                try:
                    frame = self.image_queue.get_nowait()
                except Exception as e:
                    pass
                if(isinstance(frame, np.ndarray)):  
                    #print("Recording....")         
                    try:       
                        #self.record_out.write(frame)
                        self.record_out.stdin.write(frame.tostring())
                    except Exception as e:
                        print(f"There was an error capturing frame {e}")
    def http_stream(self):
        while(not self.camera_stop):
            global http_start
            global process
            
            if(process == None):
                print("Starting Process...")
                http_start = False
                process = (
                    ffmpeg
                    .input('pipe:', hwaccel_output_format="cuda", format='rawvideo',codec="rawvideo", pix_fmt='bgr24', s='{}x{}'.format(self.frame_resized["width"], self.frame_resized["height"]))
                    .output(
                        "rtsp://0.0.0.0:8554/surveillance",
                        codec="h264",
                        pix_fmt="yuv420p",
                        rtsp_transport="udp",
                        maxrate="1200k",
                        bufsize="5000k",
                        g="64",
                        probesize="64",
                        f="rtsp"
                        )
                    .overwrite_output()
                    .run_async("ffmpeg_g",  pipe_stdin=True, quiet=True)
                )
                http_start = True
                
            else:
                if(process.poll() is not None):
                    http_start = False
                    process = (
                        ffmpeg
                        .input('pipe:', hwaccel_output_format="cuda", format='rawvideo',codec="rawvideo", pix_fmt='bgr24', s='{}x{}'.format(self.frame_resized["width"], self.frame_resized["height"]))
                        .output(
                            "rtsp://0.0.0.0:8554/surveillance",
                            codec="h264",
                            pix_fmt="yuv420p",
                            rtsp_transport="udp",
                            maxrate="2400k",
                            bufsize="5000k",
                            g="64",
                            probesize="64",
                            f="rtsp")
                        .overwrite_output()
                        .run_async("ffmpeg_g", pipe_stdin=True, quiet=True)
                    )
                            
                    # command = [
                    #     "ffmpeg_g","hwaccel_output_format=cuda", 
                    #     "-i","-",
                    #     "-c:v","h264",
                    #     "-g","64",
                    #     "-f","rtsp",
                    #     "-rtsp_transport","udp",
                    #     "rtsp://0.0.0.0:8554/surveillance"
                    # ]
                    # process = sp.Popen(command,  stdin=sp.PIPE, stderr=sp.PIPE)
                    http_start = True
                else: 
                    sleep(1)

            

        
    def loop_camera_frames(self):
        """
            Continuously Capture Frames from Camera.
            
        """
        while(not self.camera_stop):
            ret, frame = self.retrieve_frame()
            if(ret):
                if(frame.size == 0):
                    break
                pframe = self.process_frame(frame)
                if(self.save_video):
                    self.queue_frame(pframe)

                if(http_start):
                    try:
                        process.stdin.write(pframe.tobytes())
                    except Exception as e:
                        pass
                

        self.pool.close()
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
                    #print(f"CTR Area: {ctr_area} | height: {h}")
                    #cv2.imwrite("images/detected.jpg", self.frame_resized)
                    ## Get the Regions of Interests
                    ## Apppy bitwise and with fgmask, and retrieve the ROIs.
        if(total_blobs > 0):
            roi_frame = cv2.bitwise_and(resized_frame,resized_frame, mask=fgmask_new)

            obj_detection_results = self.obj_detection.detect(roi_frame)
            resized_frame, total_objects, detected_objects = self.obj_detection.boundBox(inp_frame=resized_frame,
                                                           results=obj_detection_results,
                                                           img_ratio=1,
                                                           confidence_level=0.6)
            # Send detected objects to tracker.
            resized_frame, new_objects_count, total_obj_tracked, str_object_detected, comments = self.obj_tracker.track(resized_frame, detected_objects, total_objects)
            for str_comment in comments:
                self.video_comments[str_comment] = 1
            if(total_obj_tracked > 0 and not self.save_video): ## Notify if new objects found.
                
                self.datetime = datetime.now().strftime("%Y%m%d%H%M%S")
                self.output_file = f"recorded_videos/vidtmp_raw_capture_{self.datetime}.mp4"

                #print(f"Start Recording... {self.output_file}")

                # four_cc = cv2.VideoWriter_fourcc(*'mp4v')
                # self.record_out = cv2.VideoWriter(self.output_file, four_cc, 15.0, (self.frame_resized["width"],self.frame_resized["height"]))
                self.save_video = True
                command = [self.ffmpeg,
                        '-y',
                        '-f', 'rawvideo',
                        '-vcodec','rawvideo',
                        '-s', self.dimension,
                        '-pix_fmt', 'bgr24',
                        '-r', '15',
                        '-i', '-',
                        "-metadata",f"title={str_object_detected}",
                        '-vcodec','h264',
                        #'-vcodec','mpeg4',
                        '-pix_fmt',"yuv420p",
                        '-crf','23',
                        '-b:v', '5000k',
                        self.output_file ]
                self.record_out = sp.Popen(command, stdin=sp.PIPE, stderr=sp.PIPE)
                self.video_title = str_object_detected
                # print(resized_frame.shape)
                # print(f"==> ({self.frame_resized['width']},{self.frame_resized['height']})")
#             else:
#                 if(self.save_video and total_obj_tracked == 0 and self.record_extra_frame_count > self.total_extra_frames_recorded):
#                     self.record_out.stdin.close()
#                     self.record_out.wait()
#                     self.save_video = False
#                     self.notify_users = True
#                     self.record_extra_frame_count = 0
#                     self.addCommentsffmpeg()
#                     self.video_comments = {}

#                 else:
# #                    print(f"Total Objects Tracked: {total_obj_tracked}")
#                     if(total_obj_tracked == 0):
#                         self.record_extra_frame_count += 1
#                     else:
#                         self.record_extra_frame_count = 0
                
        else:

            ## if there is nothing detected and the video is still being recorded
            ## it needs to record only additional 45 frames. then stop recording.
            if(self.save_video):
                if(self.record_extra_frame_count < self.total_extra_frames_recorded):
                    self.record_extra_frame_count += 1
                else:
                    #print(f"Recording Stopped... {self.output_file}")
                    ## Recording Stopped - Update Metadata on comments
                

                    self.save_video = False
                    self.record_extra_frame_count = 0
                    self.notify_users = True
                    #self.record_out.release()
                    self.record_out.stdin.close()
                    self.record_out.stderr.close()
                    self.record_out.wait()

                    self.addCommentsffmpeg()
                    self.video_comments = {}
                    
            
            self.obj_tracker.clear_tracker()
                    

                
        #contours, hierarchy = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        # for i, ctr in enumerate(contours):
        #     ctr_area = cv2.contourArea(ctr)
        #     if(ctr_area > 100):
        #         ctr_resized = np.multiply(ctr, self.fgmask_ratio).astype(int)
        #         cv2.polylines(resized_frame,ctr_resized, True, (0,0,255), 2 )



        if(self.debug):

            
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

            cv2.putText(resized_frame,"Original FG Mask",[0,self.frame_resized["height"]-fg_mask.shape[0]-2],cv2.FONT_HERSHEY_DUPLEX,0.7,(0,255,0),1)
            cv2.putText(resized_frame,"Augmented FG Mask",[321,self.frame_resized["height"]-fg_mask.shape[0]-2],cv2.FONT_HERSHEY_DUPLEX,0.7,(0,255,0),1)
            cv2.putText(resized_frame,"Yolo Model Input",[(321*2),self.frame_resized["height"]-fg_mask.shape[0]-2],cv2.FONT_HERSHEY_DUPLEX,0.7,(0,255,0),1)
            cv2.putText(resized_frame,"Info",[(321*3),self.frame_resized["height"]-fg_mask.shape[0]-2],cv2.FONT_HERSHEY_DUPLEX,0.7,(0,255,0),1)

            ## For debug version info
            cv2.rectangle(resized_frame, (300,0,800,30) , (20,20,20),-1)
            cv2.putText(resized_frame,self.version_info,(310,20), cv2.FONT_HERSHEY_DUPLEX,0.7,(0,0,255),1)


            ## Pixels Changed
            
            text_pos_x = 3*fg_mask.shape[1] + 4
            cv2.putText(resized_frame,f"Video Source: {self.config.get('source')}",
                [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+15],
                cv2.FONT_HERSHEY_DUPLEX,0.5,(0,0,255),
                1)

            cv2.putText(resized_frame,f"BS Type: {self.background_mask.bs_type}",
                        [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+30],
                        cv2.FONT_HERSHEY_DUPLEX,0.5,(0,0,255),
                        1)

            cv2.putText(resized_frame,f"Pixels Changed %: {self.background_mask.pixels_changed_pct} %",
                        [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+45],
                        cv2.FONT_HERSHEY_DUPLEX,0.5,(0,255,255),
                        1)
            cv2.putText(resized_frame,f"Pixels Changed : {self.background_mask.pixels_changed}",
                        [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+60],
                        cv2.FONT_HERSHEY_DUPLEX,0.5,(0,255,255),
                        1)
            cv2.putText(resized_frame,f"Total Pixels : 57.6k",
                        [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+75],
                        cv2.FONT_HERSHEY_DUPLEX,0.5,(0,255,255),
                        1)
            cv2.putText(resized_frame,f"Detected Objects #(Yolo): " + str(total_objects),
                        [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+90],
                        cv2.FONT_HERSHEY_DUPLEX,0.5,(0,255,255),
                        1)     
            if(self.save_video):  
                cv2.putText(resized_frame,f"Recording...",
                    [text_pos_x,self.frame_resized["height"]-fg_mask.shape[0]+105],
                    cv2.FONT_HERSHEY_DUPLEX,0.5,(0,0,255),
                    1)   
        #self.show_window(resized_frame)
        
        # if self.save_video:
        #     self.record_out.write(resized_frame)
        return resized_frame
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
            # if(self.save_video):
            #     self.record_out.release()



    def addCommentsffmpeg(self):
        
        comment = ""
        output_file = self.output_file.replace("vidtmp_","")
        for c in self.video_comments:
            comment += c + "\n"
        print(f"Updating Video with Comments: {comment}")
        command = [self.ffmpeg,
        '-i', self.output_file,
        '-c','copy',
        "-metadata",f"comment={comment}",
        output_file ]
        proc = sp.Popen(command, stdin=sp.PIPE, stderr=sp.PIPE)
        proc.wait()
        os.remove(self.output_file)
        self.send_alert_queue({"subject": self.video_title, "message": {comment}})
