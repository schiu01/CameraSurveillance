import math
import cv2

from ultralytics import YOLO ## Version 8

class ObjectDetection:
    def __init__(self):

        ## We are using pre-built version of Yolo Version 8 - Latest version as of today.
        self.yolo_model = YOLO("yolo-weights/yolov8n.pt")

        ## Pushing the model inference to use GPU
        self.yolo_model.to('cuda')

        ## Pre built classnames for Yolo.

        self.yolo_classNames = ["person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat",
                "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
                "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
                "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat",
                "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
                "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
                "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", "pottedplant", "bed",
                "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote", "keyboard", "cell phone",
                "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
                "teddy bear", "hair drier", "toothbrush"
                ]
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.fontScale = 0.7
        self.color = (0, 255, 0)
        self.thickness = 1
        pass

    def detect(self, inp_frame):
        results = self.yolo_model(inp_frame, stream=True, verbose=False)
        return results
    def boundBox(self, inp_frame, results, img_ratio, confidence_level=0.55):
        yolo_obj_found = False
        for r in results:
            boxes = r.boxes
            if(len(boxes) > 0):
                yolo_obj_found = True
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1 * img_ratio),int(y1 * img_ratio),int(x2 * img_ratio), int(y2 * img_ratio ) # convert to int values
                    confidence = math.ceil((box.conf[0]))
                    cls = int(box.cls[0])
                    if(box.conf[0] > confidence_level):
                        cv2.rectangle(inp_frame,(x1,y1),(x2,y2), (0,255,0),3)
                        text_title = f"{self.yolo_classNames[cls]},{box.conf[0]:0.2f}"
                        org = [int(x1), int(y1)]
            
                        (labelWidth, labelHeight), baseline = cv2.getTextSize(text_title, fontFace=self.font, fontScale=self.fontScale, thickness=self.thickness)
                        cv2.rectangle(inp_frame, (int(x1),int(y1-labelHeight)), (int(x1)+labelWidth+3, int(y1)),(0,0,255),-1)
                        cv2.putText(inp_frame, text_title, org, self.font, self.fontScale, self.color, self.thickness)
        return inp_frame, yolo_obj_found

        