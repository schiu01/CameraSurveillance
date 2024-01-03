import json as js
import base64
import cv2
import numpy as np
from datetime import datetime
import time
class BackgroundSubtraction:
    def __init__(self, bs_type, abs_frame_diff_history=5):
        self.prev_frame = None
        self.prev_init_done = False
        self.pixels_changed_pct = 0
        self.pixels_changed = 0

        self.prev_history_frames = []
        self.total_history_frames = abs_frame_diff_history
        self.prev_history_index = 0 ## Pointer on where the current history is, for update and retrieval.




        if(bs_type == None):
            self.bs_type = "absdiff"
        else:
            self.bs_type = bs_type
        

        ## Mixture of Gradients BS.
        if(self.bs_type == "mog2"):
            self.backsub = cv2.createBackgroundSubtractorMOG2(history=100)

        
        ## Vibe
        if(self.bs_type == "vibe"):
            self.width = 0
            self.height = 0
            self.numberOfSamples = 20
            self.matchingThreshold = 20
            self.matchingNumber = 2
            self.updateFactor = 16
            
            # Storage for the history
            self.historyImage = None
            self.historyBuffer = None
            self.lastHistoryImageSwapped = 0
            self.numberOfHistoryImages = 2
            
            # Buffers with random values
            self.jump = None
            self.neighbor = None
            self.position = None
    

    def get_fgmask(self, frame):
        fgmask = None
        if(self.bs_type == "absdiff"):
            orig_fgmask, fgmask =  self.get_fgmask_absdiff(frame)
        elif(self.bs_type == "mog2"):
            ## https://docs.opencv.org/4.x/d1/dc5/tutorial_background_subtraction.html
            orig_fgmask, fgmask =  self.get_fgmask_mog2(frame)
        elif(self.bs_type == "vibe"):
            if not self.prev_init_done:
                self.AllocInit(frame)
                self.prev_init_done = True
            orig_fgmask, fgmask = self.get_fgmask_vibe(frame)


        if(fgmask.size != 0):
            self.pixels_changed = np.count_nonzero(fgmask)
            self.pixels_changed_pct = int(100 * self.pixels_changed / np.size(fgmask))
            return orig_fgmask, fgmask

    def get_history_indexes(self):
        idx = []
        for x in range(self.prev_history_index, self.total_history_frames):
            idx.append(x)
        for x in range(0,self.prev_history_index):
            idx.append(x)
        return idx
    def get_fgmask_mog2(self,frame):
        #resized_frame = cv2.resize(frame, (self.fgmask_width, self.fgmask_height), interpolation=cv2.INTER_AREA)
        resized_frame = cv2.GaussianBlur(frame,(3,3),0) 
        orig_fgmask = self.backsub.apply(resized_frame)
        ret, fgmask = cv2.threshold(orig_fgmask, 200, 255, cv2.THRESH_BINARY)
        fgmask = cv2.dilate(fgmask,None,iterations=2)
        return orig_fgmask, fgmask

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
        #resized_frame = cv2.resize(frame, (self.fgmask_width, self.fgmask_height), interpolation=cv2.INTER_AREA)

        # ## Iteraiton 4: Added Gaussian Blur to minimize small movements.
        resized_frame = cv2.GaussianBlur(frame,(3,3),0) 

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
        orig_diff_frame = diff_frame
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
        return orig_diff_frame, diff_frame
        


    def update_background_absdiff(self, frame):
        self.prev_frame = frame
        # self.prev_history_frames[self.prev_history_index] = frame
        # self.prev_history_index = (self.prev_history_index + 1) % self.total_history_frames

    ## https://github.com/232525/ViBe.python
    def get_fgmask_vibe(self,frame):
        fgmask = self.Segmentation(frame)
        self.Update(frame, fgmask)
        return fgmask, fgmask
    def AllocInit(self, image):
            print('AllocInit!')
            height, width = image.shape[:2]
            # set the parametors
            self.width = width
            self.height = height
            print(self.height, self.width)
            
            # create the historyImage
            self.historyImage = np.zeros((self.height, self.width, self.numberOfHistoryImages), np.uint8)
            for i in range(self.numberOfHistoryImages):
                self.historyImage[:, :, i] = image
                
            # create and fill the historyBuffer
            self.historyBuffer = np.zeros((self.height, self.width, self.numberOfSamples-self.numberOfHistoryImages), np.uint8)
            for i in range(self.numberOfSamples-self.numberOfHistoryImages):
                image_plus_noise = image + np.random.randint(-10, 10, (self.height, self.width))
                image_plus_noise[image_plus_noise > 255] = 255
                image_plus_noise[image_plus_noise < 0] = 0
                self.historyBuffer[:, :, i] = image_plus_noise.astype(np.uint8)
            
            # fill the buffers with random values
            size = 2 * self.width + 1 if (self.width > self.height) else 2 * self.height + 1
            self.jump = np.zeros((size), np.uint32)
            self.neighbor = np.zeros((size), np.int16)
            self.position = np.zeros((size), np.uint32)
            for i in range(size):
                self.jump[i] = np.random.randint(1, 2*self.updateFactor+1)
                self.neighbor[i] = np.random.randint(-1, 3-1) + np.random.randint(-1, 3-1) * self.width
                self.position[i] = np.random.randint(0, self.numberOfSamples)
    def Segmentation(self, image):
            # segmentation_map init
            segmentation_map = np.zeros((self.height, self.width)) + (self.matchingNumber - 1)
            
            # first history image
            mask = np.abs(image - self.historyImage[:, :, 0]) > self.matchingThreshold
            segmentation_map[mask] = self.matchingNumber
            
            # next historyImages
            for i in range(1, self.numberOfHistoryImages):
                mask = np.abs(image - self.historyImage[:, :, i]) <= self.matchingThreshold
                segmentation_map[mask] = segmentation_map[mask] - 1
            
            # for swapping
            self.lastHistoryImageSwapped = (self.lastHistoryImageSwapped + 1) % self.numberOfHistoryImages
            swappingImageBuffer = self.historyImage[:, :, self.lastHistoryImageSwapped]
            
            # now, we move in the buffer and leave the historyImage
            numberOfTests = self.numberOfSamples - self.numberOfHistoryImages
            mask = segmentation_map > 0
            for i in range(numberOfTests):
                mask_ = np.abs(image - self.historyBuffer[:, :, i]) <= self.matchingThreshold
                mask_ = mask * mask_
                segmentation_map[mask_] = segmentation_map[mask_] - 1
                
                # Swapping: Putting found value in history image buffer
                temp = swappingImageBuffer[mask_].copy()
                swappingImageBuffer[mask_] = self.historyBuffer[:, :, i][mask_].copy()
                self.historyBuffer[:, :, i][mask_] = temp
            
            # simulate the exit inner loop
            mask_ = segmentation_map <= 0
            mask_ = mask * mask_
            segmentation_map[mask_] = 0
            
            # Produces the output. Note that this step is application-dependent
            mask = segmentation_map > 0
            segmentation_map[mask] = 255
            return segmentation_map.astype(np.uint8)
    
    def Update(self, image, updating_mask):
        numberOfTests = self.numberOfSamples - self.numberOfHistoryImages
        
        inner_time = 0
        t0 = time.time()
        # updating
        for y in range(1, self.height-1):
            t1 = time.time()
            shift = np.random.randint(0, self.width)
            indX = self.jump[shift]
            t2 = time.time()
            inner_time += (t2 - t1)
            #""" too slow
            while indX < self.width - 1:
                t3 = time.time()
                index = indX + y * self.width
                t4 = time.time()
                inner_time += (t4 - t3)
                if updating_mask[y, indX] == 255:
                    t5 = time.time()
                    value = image[y, indX]
                    index_neighbor = index + self.neighbor[shift]
                    y_, indX_ = int(index_neighbor / self.width), int(index_neighbor % self.width)
                    
                    if self.position[shift] < self.numberOfHistoryImages:
                        self.historyImage[y, indX, self.position[shift]] = value
                        self.historyImage[y_, indX_, self.position[shift]] = value
                    else:
                        pos = self.position[shift] - self.numberOfHistoryImages
                        self.historyBuffer[y, indX, pos] = value
                        self.historyBuffer[y_, indX_, pos] = value
                    t6 = time.time()
                    inner_time += (t6 - t5)
                t7 = time.time()
                shift = shift + 1
                indX = indX + self.jump[shift]
                t8 = time.time()
                inner_time += (t8 - t7)
            #"""
        t9 = time.time()
        # print('update: %.4f, inner time: %.4f' % (t9 - t0, inner_time))
        
        # First row
        y = 0
        shift = np.random.randint(0, self.width)
        indX = self.jump[shift]
        
        while indX <= self.width - 1:
            index = indX + y * self.width
            if updating_mask[y, indX] == 0:
                if self.position[shift] < self.numberOfHistoryImages:
                    self.historyImage[y, indX, self.position[shift]] = image[y, indX]
                else:
                    pos = self.position[shift] - self.numberOfHistoryImages
                    self.historyBuffer[y, indX, pos] = image[y, indX]
            
            shift = shift + 1
            indX = indX + self.jump[shift]
            
        # Last row
        y = self.height - 1
        shift = np.random.randint(0, self.width)
        indX = self.jump[shift]
        
        while indX <= self.width - 1:
            index = indX + y * self.width
            if updating_mask[y, indX] == 0:
                if self.position[shift] < self.numberOfHistoryImages:
                    self.historyImage[y, indX, self.position[shift]] = image[y, indX]
                else:
                    pos = self.position[shift] - self.numberOfHistoryImages
                    self.historyBuffer[y, indX, pos] = image[y, indX]
            
            shift = shift + 1
            indX = indX + self.jump[shift]
        
        # First column
        x = 0
        shift = np.random.randint(0, self.height)
        indY = self.jump[shift]
        
        while indY <= self.height - 1:
            index = x + indY * self.width
            if updating_mask[indY, x] == 0:
                if self.position[shift] < self.numberOfHistoryImages:
                    self.historyImage[indY, x, self.position[shift]] = image[indY, x]
                else:
                    pos = self.position[shift] - self.numberOfHistoryImages
                    self.historyBuffer[indY, x, pos] = image[indY, x]
            
            shift = shift + 1
            indY = indY + self.jump[shift]
            
        # Last column
        x = self.width - 1
        shift = np.random.randint(0, self.height)
        indY = self.jump[shift]
        
        while indY <= self.height - 1:
            index = x + indY * self.width
            if updating_mask[indY, x] == 0:
                if self.position[shift] < self.numberOfHistoryImages:
                    self.historyImage[indY, x, self.position[shift]] = image[indY, x]
                else:
                    pos = self.position[shift] - self.numberOfHistoryImages
                    self.historyBuffer[indY, x, pos] = image[indY, x]
            
            shift = shift + 1
            indY = indY + self.jump[shift]
            
        # The first pixel
        if np.random.randint(0, self.updateFactor) == 0:
            if updating_mask[0, 0] == 0:
                position = np.random.randint(0, self.numberOfSamples)
                
                if position < self.numberOfHistoryImages:
                    self.historyImage[0, 0, position] = image[0, 0]
                else:
                    pos = position - self.numberOfHistoryImages
                    self.historyBuffer[0, 0, pos] = image[0, 0]                