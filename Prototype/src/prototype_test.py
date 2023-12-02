import unittest
import cv2
import os
import json as js
import base64
from CameraSurveillance import CameraSurveillance

"""
    Camera surveillance system is built using Test Driven Development (TDD) method.
    Project: 3070 - Final Project
    University of London.
    Author: Steven (Suk Ching) Chiu

    About:
    Camera Surveillance System is a computer vision enabled application for detection of vehicles and persons.

    Keywords:
    opencv, background subtraction, foreground mask, yolo, you only look once, vehicle detection, person detection, centroids

    Python Open CV Install:
    pip install opencv-python

    Prototyping start date: 01-Dec-2023

"""

class TestCameraSurveillance(unittest.TestCase):
    def setUp(self) -> None:
        self.config = None
        self.config_file = "../config/camera_surveillance.config"
        self.camera_surveillance = CameraSurveillance()
        self.camera_surveillance.start()
        return super().setUp()
    
    
    def test_config(self):
        """
            Test Purpose: Check if configuration file exists
            date: 01-dec-2023

        """
        print("Testing Configuration File exists...")
        config_file_exists = os.path.exists(self.config_file)
        self.assertTrue(config_file_exists)
    def test_config_values(self):
        """
            Test Purpose: import configuration values successfully
            date: 01-dec-2023
        """
        print("Testing Configuration File values...")
        fd = open(self.config_file,"r")
        self.config = js.load(fd)
        fd.close()
        self.assertIsNotNone(self.config['rtsp_host_url'])
        self.assertIsNotNone(self.config['rtsp_user'])
        self.assertIsNotNone(self.config['rtsp_password'])                
    def test_opencv_read(self):
        """
            Testing OpenCV Reading.
            date: 01-dec-2023
        """
        print("Testing rtsp url...")
        rtsp_url = self.camera_surveillance.build_rtsp_url()
        self.assertIsNotNone(rtsp_url)
        #
        self.assertIsNotNone(self.camera_surveillance.cap)
    def test_retrieve_frame(self):
        """
            Testing Frame Retrieval from Camera [test_retrieve_frame]
        """
        print("Retrieving Frame")
        frame = self.camera_surveillance.retrieve_frame()
        self.assertIsNotNone(frame)
    def test_augment_frame(self):
        """
            Testing Frame Retrieval from Camera [test_augment_frame]
        """
        print("Retrieving Frame and Augmenting Frames")
        frame = self.camera_surveillance.retrieve_frame()
        resized_frame, small_frame, gray_frame = self.camera_surveillance.augment_frame(frame)
        self.assertIsNotNone(resized_frame)
        self.assertIsNotNone(small_frame)
        self.assertIsNotNone(gray_frame)
        
    def tearDown(self) -> None:
        self.camera_surveillance.cap.release()
        return super().tearDown()



if __name__ == '__main__':
    unittest.main()