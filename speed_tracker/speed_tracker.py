import json
import logging

import cv2
import numpy as np
import pandas as pd
from torch import Tensor
from ultralytics import YOLO

from utils import get_rect_center

FRAMES_INTERVAL = 2
PREPROCESSED_VIDEO_WIDTH = 1080
PREPROCESSED_VIDEO_HEIGHT = 720
CROSSING_DETECTION_OFFSET = 20


class CrossingData:
    def __init__(self, lane_id, start, is_up):
        self.lane_id = lane_id
        self.start = start
        self.processed = False
        self.is_up = is_up


class SpeedData:
    def __init__(self, lane_id, speed, start, finish, is_up):
        self.lane_id = lane_id
        self.speed = speed
        self.start = start
        self.finish = finish
        self.is_up = is_up


class SpeedTracker:
    def __init__(self, model_path, class_list, object_tracker, lane_locator, debug=False):
        self.model = YOLO(model_path)
        self.class_list = class_list
        self.object_tracker = object_tracker
        self.lane_locator = lane_locator
        self.object_id_2_crossing_data = {}
        self.lane_id_2_speed_data = {}
        for lane in self.lane_locator.lanes:
            self.lane_id_2_speed_data[lane.id] = []
        self.debug = debug

    def process_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        self.lane_locator.conv_lanes_coordinates(frame_width, frame_height, PREPROCESSED_VIDEO_WIDTH,
                                                 PREPROCESSED_VIDEO_HEIGHT)

        frames_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frames_count += 1
            if frames_count % FRAMES_INTERVAL != 0:
                continue

            frame = cv2.resize(frame, (PREPROCESSED_VIDEO_WIDTH, PREPROCESSED_VIDEO_HEIGHT))

            results = self.model.predict(frame, device="mps", verbose=False)
            bounding_boxes = self.get_bounding_boxes(results)
            bbox_id = self.update_tracker(bounding_boxes)

            for bbox in bbox_id:
                x3, y3, x4, y4, id = bbox
                cx, cy = get_rect_center(x3, y3, x4, y4)

                speed = self.process_speed(id, cx, cy, frames_count, fps)
                if speed is not None:
                    print(json.dumps(vars(speed)))

                draw_elements(frame, bbox, cx, cy, id, x3, y3, x4, y4, speed)

            if self.debug:
                self.draw_lanes_on_video(frame)

                cv2.imshow("RGB", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

        cap.release()
        cv2.destroyAllWindows()

    def get_bounding_boxes(self, yolo_results):
        bounding_boxes = []
        a = yolo_results[0].boxes.data
        px = pd.DataFrame(Tensor.cpu(a)).astype("float")

        for index, row in px.iterrows():
            x1, y1, x2, y2, _, d = map(int, row[:6])
            c = self.class_list[d]

            vehicle_types = ['car', 'bus', 'truck', 'motorcycle']
            if c in vehicle_types:
                bounding_boxes.append([x1, y1, x2, y2])

        return bounding_boxes

    def update_tracker(self, bounding_boxes):
        return self.object_tracker.update(bounding_boxes)

    def process_speed(self, id, cx, cy, frame_number, fps):
        lane = self.lane_locator.get_lane(cx, cy)
        frame_time = frame_number / fps  # time in seconds from start of the video.py
        crossing_data = self.object_id_2_crossing_data.get(id)

        speed_data = None
        if crossing_data is not None and crossing_data.processed:
            return None

        if lane is not None:
            is_near_upper_boundary = lane.point_near_upper_boundary(cx, cy, CROSSING_DETECTION_OFFSET)
            is_near_lower_boundary = lane.point_near_lower_boundary(cx, cy, CROSSING_DETECTION_OFFSET)
            if crossing_data is None:
                if is_near_upper_boundary:
                    self.object_id_2_crossing_data[id] = CrossingData(lane.id, frame_time, False)
                elif is_near_lower_boundary:
                    self.object_id_2_crossing_data[id] = CrossingData(lane.id, frame_time, True)
            elif (crossing_data.is_up and is_near_upper_boundary) or (
                    not crossing_data.is_up and is_near_lower_boundary):
                speed = (lane.length * 3.6) / (frame_time - crossing_data.start)
                speed_data = SpeedData(lane.id, round(speed), round(crossing_data.start, 2), round(frame_time, 2), crossing_data.is_up)
                self.lane_id_2_speed_data[lane.id].append(speed_data)
                crossing_data.processed = False

        return speed_data

    def draw_lanes_on_video(self, frame):
        for lane in self.lane_locator.lanes:
            coords = np.array([lane.coords[0], lane.coords[1], lane.coords[3], lane.coords[2]], np.int32)
            cv2.polylines(frame, [coords], isClosed=True, color=(0, 255, 0), thickness=2)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


def draw_elements(frame, bbox, cx, cy, id, x3, y3, x4, y4, speed_data):
    cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 0, 255), 2)
    cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
    cv2.putText(frame, str(id), (x3, y3), cv2.FONT_HERSHEY_COMPLEX, 0.6, (255, 255, 255), 1)
    if speed_data is not None:
        cv2.putText(frame, str(int(speed_data.speed)) + 'Km/h', (x4, y4), cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 255, 255), 2)
