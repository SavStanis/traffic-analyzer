import argparse
import json

from lane_locator import Lane, LaneLocator
from object_tracker import ObjectTracker
from speed_tracker import SpeedTracker


def read_class_list(file_path):
    with open(file_path, "r") as my_file:
        data = my_file.read()
        return data.split("\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--video_path', type=str, default='../videos/2_poland.mp4', help='Path to the video ')
    parser.add_argument('--lanes', type=str, default=None, help='lanes config')

    args = parser.parse_args()

    is_debug = args.debug
    video_path = args.video_path
    lanes = args.lanes

    if lanes is None:
        lanes = [
            Lane(0, 'left', [(1250, 1525), (1950, 1525), (2150, 743), (2400, 743)], 70, 7, 120),
            Lane(1, 'right', [(2800, 1525), (3400, 1525), (2800, 743), (3050, 743)], 70, 7, 120)
        ]
    else:
        lanes = [Lane(**lane) for lane in json.loads(lanes)]

    model_path = "speed_tracker/models/yolov8x.pt"
    classes_path = "speed_tracker/coco.txt"

    #local debug
    # model_path = "./models/yolov8x.pt"
    # classes_path = "./coco.txt"


    class_list = read_class_list(classes_path)
    objectTracker = ObjectTracker()

    lane_locator = LaneLocator(lanes)
    speedTracker = SpeedTracker(model_path, class_list, objectTracker, lane_locator, debug=is_debug)
    speedTracker.process_video(video_path)
