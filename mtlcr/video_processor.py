from datetime import datetime
import json
import time
from uuid import uuid4

import cv2
import tensorflow

from mtlcr import calc_mtlcr, save_imgs

tensorflow.keras.utils.disable_interactive_logging()


def create_mask(mask):
    pred_mask = tensorflow.argmax(mask, axis=-1)
    pred_mask = pred_mask[..., tensorflow.newaxis]
    return pred_mask[0]


def preprocess_frame(frame):
    return cv2.resize(frame, (256, 256))


class VideoProcessor:

    def __init__(self, model_path, debug=False):
        self.model = tensorflow.keras.models.load_model(model_path)
        self.debug = debug

    # first - vertical
    # second - horizontal
    # 0 - left high corner
    def process_video(self, video_path, lanes, interval=10, simulation=True):
        cap = cv2.VideoCapture(video_path)

        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        frames_interval = round(interval * frame_rate)
        video = {
            'id': uuid4(),
            'path': video_path,
            'frames_interval': frames_interval,
            'interval': interval,
            'width': width,
            'height': height,
            'lanes': [],
        }

        for i, lane in enumerate(lanes):
            lane_obj = {
                'id': lane.id,
                'n': i,
                'coords': {
                    'dl': lane.coords[0],
                    'dr': lane.coords[1],
                    'hl': lane.coords[2],
                    'hr': lane.coords[3],
                }
            }

            video['lanes'].append(lane_obj)

        skip_counter = 0
        while cap.isOpened():
            # to debug on videos
            if simulation:
                time.sleep(1 / frame_rate)

            ret, frame = cap.read()
            if not ret:
                break

            if skip_counter > 0:
                skip_counter -= 1
                continue

            skip_counter = frames_interval

            self.process_frame(frame, video)

        cap.release()

    def process_frame(self, frame, video_metadata):
        preprocessed_frame = preprocess_frame(frame)
        mask = self.model.predict(preprocessed_frame[tensorflow.newaxis, ...])

        # Invert to make everything that is NOT road to be 1
        mask = 1 - create_mask(mask).numpy()

        results = []
        time = datetime.utcnow().isoformat()
        for area in video_metadata['lanes']:
            mtlcr, masks = calc_mtlcr(mask, video_metadata['width'], video_metadata['height'], area['coords'])
            res = {
                'video': video_metadata['path'],
                'lane_id': area['id'],
                'mtlcr': mtlcr,
                'created_at': time,
            }

            if self.debug:
                folder_name = f"video_{video_metadata['id']}"
                timestamp = datetime.utcnow().isoformat()
                image_name = f"lane_{area['id']}_{timestamp}.png"
                save_imgs(masks, f"MTLCR: {mtlcr}", folder_name, image_name)

            print(json.dumps(res))

            results.append(res)

        return results
