import argparse
import json

from lane import Lane
from video_processor import VideoProcessor
import sys

DEFAULT_LANE_1 = Lane(0, 'left', [(1250, 1525), (1950, 1525), (2150, 743), (2400, 743)], 70, 7, 120)
DEFAULT_LANE_2 = Lane(1, 'right', [(2800, 1525), (3400, 1525), (2800, 743), (3050, 743)], 70, 7, 120)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--video_path', type=str, default='videos/2_poland.mp4', help='Path to the video ')
    parser.add_argument('--lanes', type=str, default=None, help='Lanes config')

    args = parser.parse_args()

    is_debug = args.debug
    video_path = args.video_path
    lanes = args.lanes

    if lanes is None:
        lanes = [DEFAULT_LANE_1, DEFAULT_LANE_2]
    else:
        lanes = [Lane(**lane) for lane in json.loads(lanes)]

    model_path = "mtlcr/models/road_segmentation.h5"

    # local debug
    # video_path = "../videos/2_poland.mp4"
    # model_path = "models/road_segmentation.h5"

    video_processor = VideoProcessor(model_path, debug=is_debug)
    print(video_path)
    video_processor.process_video(video_path, lanes, 2)
