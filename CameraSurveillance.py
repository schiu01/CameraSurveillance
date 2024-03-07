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
import signal
import logging
c =  threading.Condition()
# global process 
# global http_start 
# process = None
# http_start = False



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


        ## Signals - INT, KILL gracefully shutdown
        signal.signal(signal.SIGINT,self.end_all)
        
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
        self.monitoring_stop = False
        
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
        self.alert = ProjectAlert(email_user=self.config.get("notification_from_email"),
                                  smtp_password=self.config.get("notification_pwd"),
                                  notify_user=self.config.get("notification_email")
                                  )
        self.alert_words = self.config["notification_alert_hot_words"]



        ## process variable for external ffmpeg run
        self.process = None
        self.http_start = False


        ## Camera Source Error Flag
        self.camera_source_error_flag = False

        ### thread monitoring - threadname prefix
        self.thread_name_prefix = "camsurvapp_"

        self.thread_list = []

        logging.basicConfig(format='%(asctime)s|%(levelname)s|%(message)s', filename=f"camera_surveillance_{self.datetime}.log",filemode='a', level=logging.INFO)
    def end_all(self, *args):
        print("Signal Caught, Gracefully Shutting Down!")
        logging.warn("Signal Caught, Gracefully Shutting Down!")
        self.camera_stop = True
        self.monitoring_stop = True
    def alerting(self):
        """
            This Thread invoked process is to process Notifcations system.
            if a 'hot' word is found in the comment, then we send a notification.
        
        """
        while(not self.camera_stop):
            try:
                if(self.notify_queue.empty()):
                    sleep(10)
                else:
                    alert_message = self.notify_queue.get(block=False)
                    subject = alert_message.get("subject")
                    message = alert_message.get("message")
                    image_file = alert_message.get("image_file")
                    message_words = f"{message}".split(" ")
                    subject_words = str(subject).split(" ")
                    send_alert = False
                    for sw in subject_words:
                        if(sw in self.alert_words):
                            send_alert = True
                            break
                    if(not send_alert):
                        for m in message_words:
                            if(m in self.alert_words):
                                send_alert = True
                                break
                    if(send_alert):
                        self.alert.send_email(subject, message, image_file)
            except Exception as e:
                print(f"Queue / Alert Processing Error {e}")
                logging.warn(f"Queue / Alert Processing Error {e}")
                sleep(10)

    def send_alert_queue(self, object):
        self.notify_queue.put(object, block=False)
    def self_monitoring(self):
        """
            This module (added late in project) is to monitor the health of the overall application.
            20-Feb-2024: Recent continued breaking of application due to network issues on camera caused the application to simply hang.
            This thread will monitor all threads, 

            Restart all threads if:
                - if one is dead it kills all the other threads and restarts
                - if the source camera fails retries at least 5 times, then it source camera flag is set to True, and this thread will kill all threads and restart
            
        """
        while(not self.monitoring_stop):
            # 1: check self.camera_source_error_flag = True; then kill all process and restart.
            if(self.camera_source_error_flag):
                logging.warn("[self_monitoring] camera source error flag detected false - setting camera stop to true to shutdown threads")
                self.camera_stop = True
                ## Kill process and let the parent process restart.
                sleep(5)
                logging.warn("[self_monitoring] Killing self process!")
                os.kill(threading.current_thread().native_id)
            else:
                sleep(10)
                ## Sleepi
            #     sleep(10)
            # thread_status = {}
            
            # for tname in self.thread_list:
            #     thread_found_alive = False
            #     thread_status[tname] = {}
            #     curr_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            #     for thread in threading.enumerate():
            #         if(thread.name == tname):
            #             if(thread.is_alive()):
            #                 thread_found_alive = True
            #                 thread_status[tname]['status'] = "Alive"
            #                 thread_status[tname]['ident'] = thread.ident
            #                 thread_status[tname]['native_id'] = thread.native_id
            #                 thread_status[tname]['check_timestamp'] = curr_date
                            

            #     if(not thread_found_alive):
            #         th1 = None
            #         thread_status[tname]['status'] = "Not Found Alive!"
            #         if("read_thread" in tname):
            #             if(self.cap.isOpened()):
            #                 self.cap.release()
            #             self.init_capture()
            #             th1 = Thread(name=f"{self.thread_name_prefix}_read_thread", target=self.loop_camera_frames)
            #         elif("save_frame" in tname):
            #             th1 = Thread(name=f"{self.thread_name_prefix}_save_frame", target=self.save_video_frames)
            #         elif("http_stream" in tname):
            #             th1 = Thread(name=f"{self.thread_name_prefix}_http_stream", target=self.http_stream)
            #         elif("alerting" in tname):
            #             th1 = Thread(name=f"{self.thread_name_prefix}_alerting", target=self.alerting )

            #         logging.info(f"Restarting Thread: {tname}")
            #         print(f"Restarting Thread: {tname}")
            #         try:
            #             if(th1 == None):
            #                 logging.error(f"{tname} not found in list of accepted thread names")
            #             else:
            #                 th1.start()
            #                 curr_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            #                 thread_status[tname]['status'] = "Restarted"
            #                 thread_status[tname]['ident'] = th1.ident
            #                 thread_status[tname]['native_id'] = th1.native_id
            #                 thread_status[tname]['check_timestamp'] = curr_date
            #                 logging.info(thread_status[tname])

            #         except Exception as e:
            #             logging.error(f"Error in starting thread {e}")
                    

            # # for t in thread_status:
            # #     logging.info(f"[monitoring] Status of {t}")
            # #     for k in thread_status[t]:
            # #         logging.info(f"[monitoring] {t} : {k} : {thread_status[t][k]}")
            # self.camera_stop = False
            # self.camera_source_error_flag = False
            # sleep(10)


        pass
    def start(self):
        """
            Starts the Camera Surveillance system
            using a multi-threading model - Due to Resource Intensive acitivites by each process.
            Thread #1 - Loop Camera Frames
            Thread #2 - Saving Video Frames - if saving flag is enabled
            Thread #3 - Stream video to RTSP Server.
            Thread #4 - Notification
        """
        self.init_capture()
        th1 = Thread(name=f"{self.thread_name_prefix}_read_thread", target=self.loop_camera_frames)
        th1.start()
        self.thread_list.append(f"{self.thread_name_prefix}_read_thread")
        th2 = Thread(name=f"{self.thread_name_prefix}_save_frame", target=self.save_video_frames)
        th2.start()
        self.thread_list.append(f"{self.thread_name_prefix}_save_frame")
        th3 = Thread(name=f"{self.thread_name_prefix}_http_stream", target=self.http_stream)
        th3.start()
        self.thread_list.append(f"{self.thread_name_prefix}_http_stream")
        if(self.notify_users):
            print("Starting Notifications System...")
            logging.info("Starting Notifications System...")
            th4 = Thread(name=f"{self.thread_name_prefix}_alerting", target=self.alerting )
            th4.start()
            self.thread_list.append(f"{self.thread_name_prefix}_alerting")
        else:
            logging.info("Notification System is not active.")
        
        th4 = Thread(name="camsurv_monitoring", target=self.self_monitoring)
        th4.start()
        
        th4.join()

        ## if loop camera fails - everything fails.
        #th2.join()
#        th3.join()
        #self.loop_camera_frames()

    def read_config(self):
        """
            Module to read configuration file camera_surveillance.config

        """
        fd = open(self.config_file,"r")
        self.config = js.load(fd)
        fd.close()


    def decode_password(self, enc_password):
        """
            The password in our configuration file is base64 encoded. This module is to decode it prior to sending for authentication

        """
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
        self.str_object_detected = "" 
        self.ffmpeg = 'ffmpeg'
        self.dimension = '{}x{}'.format(self.frame_resized["width"],self.frame_resized["height"])


        ## flag if we have issues with camera source
        self.blank_frame = np.zeros((self.frame_size["height"], self.frame_size["width"],3),dtype="uint8")
         

    def retrieve_frame(self):
        """
            Image Retrieval from Camera.
        """
        if(self.cap.isOpened):
            return self.cap.read()
        else:
            logging.error("[retrieve_frame] self.cap is closed! returning false.")
            return None, self.blank_frame
        
        
    def queue_frame(self, frame):
        self.image_queue.put_nowait(frame)
    def save_video_frames(self):
            
            """
                This module saves video frames.
                1. if there is an initiation of save video flag and record out isnt initalized, it will initialize it
                2. grabs video frames from queue and saves.
            
            """
        
            save_frame_errors = 0
            while(not self.camera_stop):

                if(self.image_queue.qsize() == 0):
                    if(self.save_video):
                        ## if queue size is 0 and save video is still on, just continue loop.
                        ## sleep for a bit, then continue loop
                        sleep(0.01)
                        continue
                    else:
                        ## If save video flag is off
                        if(self.record_out == None):
                            ## if recording is off - do nothing.. just continue loop.
                            sleep(0.1)
                            continue
                        else:
                        ## if recording is still on and the queue is 0 with save video flag off
                        ## Then close the recording.
                            self.record_extra_frame_count = 0
                            self.notify_users = True
                            #self.record_out.release()
                            self.record_out.stdin.close()
                            self.record_out.stderr.close()
                            self.record_out.wait(15)
                            self.record_out.terminate()

                            self.addCommentsffmpeg()
                            self.video_comments = {}
                            self.str_object_detected = ""
                            self.record_out = None
                                    

                # init frame
                frame = None


                                
                try:
                    frame = self.image_queue.get_nowait()
                except Exception as e:
                    pass

                if(isinstance(frame, np.ndarray)):  

                    ## Check if record is open - if not open it, else just save
                    if(self.record_out == None and self.save_video):

                        self.datetime = datetime.now().strftime("%Y%m%d%H%M%S")
                        self.output_file = f"recorded_videos/vidtmp_raw_capture_{self.datetime}.mp4"
                        self.title_image = f"recorded_images/img_{self.datetime}.jpg"
                        print(f"Saving Video to {self.output_file}")
                        logging.info(f"Saving Video to {self.output_file}")
                        cv2.imwrite(self.title_image,frame)
                        
                        command = [self.ffmpeg,
                                '-y',
                                '-f', 'rawvideo',
                                '-vcodec','rawvideo',
                                '-s', self.dimension,
                                '-pix_fmt', 'bgr24',
                                '-r', '15',
                                '-i', '-',
                                "-metadata",f"title={self.str_object_detected}",
                                '-vcodec','h264',
                                #'-vcodec','mpeg4',
                                '-pix_fmt',"yuv420p",
                                '-crf','23',
                                '-b:v', '5000k',
                                self.output_file ]
                        self.record_out = sp.Popen(command, stdin=sp.PIPE, stderr=sp.PIPE)
                        self.video_title = self.str_object_detected

                    #print("Recording....")         
                    try:       
                        #self.record_out.write(frame)
                        self.record_out.stdin.write(frame.tostring())
                        save_frame_errors = 0
                    except Exception as e:
                        print(f"There was an error capturing frame {e}")
                        logging.error(f"[save_video_frames] There was an error saving frame {e}")
                        save_frame_errors += 1
                        if(save_frame_errors > 50):
                            logging.error(f"[save_video_frames] Save Frame Errors exceeded 50. restarting app.")
                            self.camera_stop = True
    def http_stream(self):
        """
            Module to start streaming to RTSP Server.
            if the process isnt started, it invokes ffmpeg
            if the process has stopped, it restarts it
            checks every 1 second, and exits 
        """
        print("Start Stream to RTSP...")
        logging.info("Start Stream to RTSP...")
        # global http_start
        # global process

        while(not self.camera_stop):
            
            if(self.process == None):
                
                self.http_start = False
                self.process = (
                    ffmpeg
                    .input('pipe:', hwaccel_output_format="cuda", format='rawvideo',codec="rawvideo", pix_fmt='bgr24', s='{}x{}'.format(self.frame_resized["width"], self.frame_resized["height"]))
                    .output(
                        "rtsp://0.0.0.0:8554/surveillance",
                        codec="h264",
                        pix_fmt="yuv420p",
                        rtsp_transport="tcp",
                        maxrate="1200k",
                        bufsize="5000k",
                        g="64",
                        probesize="64",
                        f="rtsp"
                        )
                    .overwrite_output()
                    .run_async("ffmpeg_g",  pipe_stdin=True, quiet=True)
                )
                self.http_start = True
                
            else:
                if(self.process.poll() is not None):
                    self.http_start = False
                    process = (
                        ffmpeg
                        .input('pipe:', hwaccel_output_format="cuda", format='rawvideo',codec="rawvideo", pix_fmt='bgr24', s='{}x{}'.format(self.frame_resized["width"], self.frame_resized["height"]))
                        .output(
                            "rtsp://0.0.0.0:8554/surveillance",
                            codec="h264",
                            pix_fmt="yuv420p",
                            rtsp_transport="tcp",
                            maxrate="2400k",
                            bufsize="5000k",
                            g="64",
                            probesize="64",
                            f="rtsp")
                        .overwrite_output()
                        .run_async("ffmpeg_g", pipe_stdin=True, quiet=True)
                    )
                            
                    self.http_start = True
                else: 
                    sleep(1)

            

        
    def loop_camera_frames(self):
        """
            Continuously Capture Frames from Camera.
            
        """
        print("Starting Camera Feed Loop...")
        logging.info("Starting Camera Feed Loop...")
        # global http_start
        # global process
        retries = 0
        while(not self.camera_stop):
            
            try:
                ret, frame = self.retrieve_frame()
                if(not ret):
                    frame = self.blank_frame
                    self.camera_source_error_flag = True
                    retries += 1
                    if(retries > 50):
                        try:
                            self.cap.release()
                            retries = 0
                        except:
                            pass
                        self.init_capture()
                    logging.error(f"[loop_camera_frames] Return Flag from Retrieve Frame has error!.. ret != true - Retrying # {retries}")
                    print(f"[loop_camera_frames] Return Flag from Retrieve Frame has error!.. ret != true - Retrying # {retries}")
                else:
                    if(retries > 0):
                        logging.info(f"[loop_camera_frames] Returned True after {retries} retries!")
                        print(f"[loop_camera_frames] Returned True after {retries} retries!")
                    self.camera_source_error_flag = False
                    retries = 0

                ## Continue processing - even if its blank. 
                   
                if(frame.size == 0):
                    print("Retrieved Frame Size of 0!.")
                    continue

                pframe = self.process_frame(frame)
                
                if(self.save_video):
                    self.queue_frame(pframe)

                if(self.http_start):
                    try:
                        self.process.stdin.write(pframe.tobytes())
                        #outs, errs = process.communicate(input=pframe.tobytes(), timeout=5)
                    except Exception as e:
                        print(e)
                        print("Killing Process...")
                        logging.error(f"[loop_camera_frames] Killing Process, there was an error writing to process's stdin. {e}")
                        try:
                            self.process.kill()
                        except Exception as e:
                            print("Failed to Kill process")
                            print(str(e))
                            pass
                        self.process = None
                        self.http_start = False
                        pass
                

                        
                            
                
            except Exception as e:
                retries += 1
                if(retries > 10):
                    print(str(e))
                    self.camera_stop = True
                    logging.error(f"[loop_camera_frames] Return Flag from Retrieve Frame has error!.. ret != true - Retrying # {retries}")
                    raise(Exception("Error from Frame Loop"))
                

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

                    ## Remap the detected area to the actual image size.
                    ctr_resized = np.multiply(ctr, self.fgmask_ratio).astype(int)
                    (cx, cy, cw, ch) = cv2.boundingRect(ctr_resized)

                    ## Blank the areas where the blob is, so it can be 'bitwise-and' later for region of interest frame.
                    cv2.rectangle(fgmask_new, (cx, cy), (cx+cw, cy+ch), (1,1), -1 )
        if(total_blobs > 0):

            ## Only send the relevant blobs detected to Yolo
            roi_frame = cv2.bitwise_and(resized_frame,resized_frame, mask=fgmask_new)

            ##
            obj_detection_results = self.obj_detection.detect(roi_frame)

            resized_frame, total_objects, detected_objects = self.obj_detection.boundBox(inp_frame=resized_frame,
                                                           results=obj_detection_results,
                                                           img_ratio=1,
                                                           confidence_level=0.6)
            # Send detected objects to tracker.
            resized_frame, new_objects_count, total_obj_tracked, str_object_detected, comments = self.obj_tracker.track(resized_frame, detected_objects, total_objects)
            for str_comment in comments:
                self.video_comments[str_comment] = 1

            ## If new objects are found and save video flag isnt set, then start the stream into a video file.
            ## This is also where some "jerky" images occur, as these processes need to startup.
            
            if(total_obj_tracked > 0 ): ## Notify if new objects found.
                if(not self.save_video):
                    self.save_video = True
                    self.str_object_detected = str_object_detected
                    
                
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
                    
            
            self.obj_tracker.clear_tracker()
                    
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
        logging.info(f"Updating Video with Comments: {comment}")
        command = [self.ffmpeg,
        '-i', self.output_file,
        '-c','copy',
        "-metadata",f"comment={comment}",
        output_file ]
        proc = sp.Popen(command, stdin=sp.PIPE, stderr=sp.PIPE)
        proc.wait()
        os.remove(self.output_file)
        self.send_alert_queue({"subject": self.video_title, "message": {comment}, "image_file": self.title_image})
