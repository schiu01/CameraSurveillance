import math
import cv2
class ObjectTracker:
    def __init__(self, centroid_max_dist=100, show_centroid_trail=False):
        self.objects = []
        self.last_centroids = []
        self.tracked_centroids = []
        self.show_centroid_trail = show_centroid_trail
        self.total_tracked_objects = 0
        self.centroid_max_dist = centroid_max_dist ## 5 pixels
        self.consecutive_frames_noobject = 0
        self.tracked_counter = []
        self.object_counter = 0
        self.object_direction = []
    def clear_tracker(self):
        self.consecutive_frames_noobject += 1
        if(self.consecutive_frames_noobject > 5):
            self.objects =[]
            self.last_centroids = []
            self.tracked_centroids = []
            self.total_tracked_objects = 0
            self.consecutive_frames_noobject = 0
            self.tracked_counter = []
            self.object_direction = []
    def get_distance(self,p1, p2):
        """
            Assume p1 = {"x": x, "y": y}
            Assume p2 = {"x": x, "y": y}
            Dict format.
        """
        dy = (p1["y"] - p2["y"]) ** 2
        dx = (p1["x"] - p2["x"]) ** 2
        if(dy == 0):
            return 0.0
        euclidean_distance = math.sqrt(dx+dy)
        return euclidean_distance


    def track(self,input_frame, objects, total_objects):
        new_objects_count = 0
        if(total_objects == 0):
            self.clear_tracker()
                
            return input_frame,0
        else:
            self.consecutive_frames_noobject = 0
            for object_no, object in enumerate(objects):
                (x1,y1,x2,y2) = object["loc"]
                object_class = object["label"]
                confidence_level = object["confidence"]
                centroid = {"x": int(x1) + int((x2-x1)/2), "y": int(y1) + int((y2-y1)/2)}
                found_centroid = False
                last_tracked_centroid_index = 0
                shortest_dist = 1000
                #print(f"Total Last Centroids: {len(self.last_centroids)}")
                for i, cp in enumerate(self.last_centroids):
                    dist = self.get_distance(cp, centroid)
                    #print(f"Object: {object_no} | {cp} <=> {centroid} = {dist}")
                    if(dist <= self.centroid_max_dist and dist < shortest_dist):
                        
                        last_tracked_centroid_index = i
                        shortest_dist = dist
                        
                        

                if(shortest_dist != 1000):
                    ## If the car's x is > current centroid x then car is moving West (camera is facing south)
                    ## if x is < current centroid x then its moving east
                    ## if there is a big change in Y, then either car is moving away or towards the camera. (so North / South)
                    self.tracked_centroids[last_tracked_centroid_index].append(centroid)
                    if (self.tracked_centroids[last_tracked_centroid_index][0]["x"] - centroid["x"]) < -100:
                        self.object_direction[last_tracked_centroid_index] = "West"
                    elif (self.tracked_centroids[last_tracked_centroid_index][0]["x"] - centroid["x"]) >  100:    
                        self.object_direction[last_tracked_centroid_index] = "East"
                    if (self.tracked_centroids[last_tracked_centroid_index][0]["y"] - centroid["y"]) < - 100:
                        self.object_direction[last_tracked_centroid_index] = "Into Driveway"
                    elif (self.tracked_centroids[last_tracked_centroid_index][0]["y"] - centroid["y"]) >  100:    
                        self.object_direction[last_tracked_centroid_index] = "Away from Driveway"

                    self.last_centroids[last_tracked_centroid_index] = centroid
                    
                    cv2.rectangle(input_frame, (10,500-(object_no+3)* 30,800,500-(object_no+2)*30) , (20,20,20),-1)
                    
                    cv2.putText(input_frame,f"{object_class} #{self.tracked_counter[last_tracked_centroid_index]} is moving {self.object_direction[last_tracked_centroid_index]}",
                                [15, 500 - (object_no+2)*30],cv2.FONT_HERSHEY_DUPLEX,0.6,(255,255,255),1)


                else:
                    self.tracked_centroids.append([centroid])
                    self.last_centroids.append(centroid)
                    self.object_counter += 1
                    self.tracked_counter.append(self.object_counter)
                    self.object_direction.append("")
                    self.total_tracked_objects += 1
                    new_objects_count += 1
                if(object_class in ["car","truck","vehicle"]):
                    cv2.rectangle(input_frame, (int(x1),int(y1)-15), (int(x2),int(y1)), (89,0,179),-1)
                    cv2.putText(input_frame,f"{object_class} Id: {self.tracked_counter[last_tracked_centroid_index]} | {self.object_direction[last_tracked_centroid_index]}",[int(x1), int(y1)-1],cv2.FONT_HERSHEY_DUPLEX,0.7,(255,255,255),1)
                    cv2.rectangle(input_frame, (int(x1),int(y1)), (int(x2),int(y2)), (89,0,179),2)
                elif(object_class in ["person"]):
                    cv2.rectangle(input_frame, (int(x1),int(y1)-15), (int(x2),int(y1)), (255,0,102),-1)
                    cv2.putText(input_frame,f"{object_class} Id: {self.tracked_counter[last_tracked_centroid_index]}",[int(x1), int(y1)-1],cv2.FONT_HERSHEY_DUPLEX,0.7,(255,255,255),1)
                    cv2.rectangle(input_frame, (int(x1),int(y1)), (int(x2),int(y2)), (255,0,102),2)

                for idx in range(1,len(self.tracked_centroids[last_tracked_centroid_index])):
                
                    prior_point = self.tracked_centroids[last_tracked_centroid_index][idx-1]
                    curr_point = self.tracked_centroids[last_tracked_centroid_index][idx]
                    cv2.line(input_frame,(prior_point["x"], prior_point["y"]), (curr_point["x"], curr_point["y"]), (0,0,255),2)
                    cv2.circle(input_frame, (curr_point["x"],curr_point["y"]), 3, (255,255,255), 3)
                    cv2.circle(input_frame, (prior_point["x"],prior_point["y"]), 3, (255,255,255), 3)
                if(shortest_dist != 1000):
                    if (((self.tracked_centroids[last_tracked_centroid_index][0]["x"] - centroid["x"]) > 100) and (centroid["x"] < 50))\
                        or (((self.tracked_centroids[last_tracked_centroid_index][0]["x"] - centroid["x"]) < -100) and (centroid["x"] > 900)):
                                
                        del self.last_centroids[last_tracked_centroid_index]
                        del self.tracked_centroids[last_tracked_centroid_index]
                        self.total_tracked_objects -= 1
                        del self.tracked_counter[last_tracked_centroid_index]
                        del self.object_direction[last_tracked_centroid_index]                         
#        print(f"Total Objects in tracker: {self.total_tracked_objects} ")



        return input_frame, new_objects_count
        


        

        
        pass