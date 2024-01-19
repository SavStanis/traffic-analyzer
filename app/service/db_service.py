from datetime import timedelta, datetime

import motor.motor_asyncio

from app.utils import serialize_date_times


class DBService:
    def __init__(self, mongo_config):
        self.mongo_config = mongo_config
        self.client = None

    async def init_db(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            f"mongodb://{self.mongo_config['username']}:{self.mongo_config['password']}@"
            f"{self.mongo_config['host']}:{self.mongo_config['port']}/admin"
        )

    async def close_db(self):
        self.client.close()

    # --------------------- Video Management -------------------------- #

    async def insert_video(self, video):
        db = self.client[self.mongo_config['database']]
        videos = db.videos

        await videos.insert_one(video)

    async def get_video(self, video_id):
        db = self.client[self.mongo_config['database']]
        videos = db.videos

        return await videos.find_one({"id": video_id}, {"_id": False})

    async def list_videos(self):
        db = self.client[self.mongo_config['database']]

        videos = []
        for video in await db.videos.find({}, {"_id": False}).to_list(length=1000):
            videos.append(video)

        return videos

    async def update_video(self, video_id, video):
        db = self.client[self.mongo_config['database']]
        return await db.videos.update_one({"id": video_id}, {"$set": video})

    async def delete_video(self, video_id):
        db = self.client[self.mongo_config['database']]
        videos = db.videos

        await videos.delete_one({"id": video_id})

    async def add_lane(self, lane):
        db = self.client[self.mongo_config['database']]
        lanes = db.lanes

        await lanes.insert_one(lane)

    async def list_lanes(self, video_id):
        db = self.client[self.mongo_config['database']]
        lanes = db.lanes

        await lanes.find({'video_id': video_id})

    async def remove_lane(self, video_id, lane_id):
        db = self.client[self.mongo_config['database']]
        lanes = db.lanes

        await lanes.delete_one({'video_id': video_id, 'id': lane_id})

    # --------------------- Processing -------------------------- #

    async def insert_active_process(self, parent_process_id, process_id, video_path, process_type):
        db = self.client[self.mongo_config['database']]
        processes = db.processes

        await processes.insert_one({
            'id': process_id,
            'parent_process_id': parent_process_id,
            'video_source': video_path,
            'type': process_type,
            'status': 'running',
            'created_at': datetime.utcnow(),
        })

    async def finish_active_process(self, process_id):
        db = self.client[self.mongo_config['database']]
        processes = db.processes

        await processes.update_one({"id": process_id}, {"$set": {'status': 'finished'}})

    async def list_processes(self):
        db = self.client[self.mongo_config['database']]

        processes = []
        for process in await (db.processes.find({}, {"_id": False}).sort("created_at", -1).to_list(length=1000)):
            process = serialize_date_times(process)
            processes.append(process)

        return processes

    # --------------------- Speed Measurements -------------------------- #

    async def insert_speed_result(self, parent_process_id, process_id, timestamp, result):
        db = self.client[self.mongo_config['database']]
        speed_results = db.speed_results
        await speed_results.insert_one(
            {'parent_process_id': parent_process_id, 'process_id': process_id, 'created_at': timestamp,
             'result': result})

    async def list_speed_results_by_process_id(self, process_id):
        db = self.client[self.mongo_config['database']]

        speed_results = []
        for result in await (
                db.speed_results.find({'parent_process_id': process_id}, {"_id": False}).sort("created_at", -1).to_list(
                    length=1000)):
            speed_results.append(result)

        return speed_results

    async def list_speed_results_by_process_and_lane_id(self, process_id, lane_id, newer_than_seconds=None, limit=1000):
        db = self.client[self.mongo_config['database']]

        if newer_than_seconds is None:
            res_filter = {'parent_process_id': process_id}
        else:
            threshold_time = datetime.utcnow() - timedelta(seconds=newer_than_seconds)
            res_filter = {'parent_process_id': process_id, "created_at": {"$gt": threshold_time}}

        speed_results = []
        for result in await (
                db.speed_results.find(res_filter, {"_id": False}).sort("created_at", -1).to_list(length=limit)):
            if result['result']['lane_id'] == lane_id:
                speed_results.append(result)

        return speed_results

    # --------------------- MTLCR Measurements -------------------------- #

    async def insert_mtlcr_result(self, parent_process_id, process_id, timestamp, result):
        db = self.client[self.mongo_config['database']]
        mtlcr_results = db.mtlcr_results
        await mtlcr_results.insert_one(
            {'parent_process_id': parent_process_id, 'process_id': process_id, 'created_at': timestamp,
             'result': result})

    async def list_mtlcr_results_by_process_id(self, process_id):
        db = self.client[self.mongo_config['database']]

        mtlcr_results = []
        for result in await (
                db.mtlcr_results.find({'parent_process_id': process_id}, {"_id": False}).sort("created_at", -1).to_list(
                    length=1000)):
            mtlcr_results.append(result)

        return mtlcr_results

    async def list_mtlcr_results_by_process_and_lane_id(self, process_id, lane_id, newer_than_seconds=None, limit=1000):
        db = self.client[self.mongo_config['database']]

        if newer_than_seconds is None:
            res_filter = {'parent_process_id': process_id}
        else:
            threshold_time = datetime.utcnow() - timedelta(seconds=newer_than_seconds)
            res_filter = {'parent_process_id': process_id, "created_at": {"$gt": threshold_time}}

        mtlcr_results = []
        for result in await (
                db.mtlcr_results.find(res_filter, {"_id": False}).sort("created_at", -1).to_list(length=limit)):
            if result['result']['lane_id'] == lane_id:
                mtlcr_results.append(result)

        return mtlcr_results

    # --------------------- TLIR Measurements -------------------------- #

    async def insert_tlir_result(self, parent_process_id, timestamp, result):
        db = self.client[self.mongo_config['database']]
        tlir_results = db.tlir_results
        await tlir_results.insert_one(
            {'parent_process_id': parent_process_id, 'created_at': timestamp, 'result': result})

    async def list_tlir_results_by_process_id(self, process_id):
        db = self.client[self.mongo_config['database']]

        tlir_results = []
        for result in await (
                db.tlir_results.find({'parent_process_id': process_id}, {"_id": False}).sort("created_at", -1).to_list(
                    length=1000)):
            tlir_results.append(result)

        return tlir_results

    async def list_tlir_results_by_process_and_lane_id(self, process_id, lane_id, newer_than_seconds=None):
        db = self.client[self.mongo_config['database']]

        if newer_than_seconds is None:
            res_filter = {'parent_process_id': process_id}
        else:
            threshold_time = datetime.utcnow() - timedelta(seconds=newer_than_seconds)
            res_filter = {'parent_process_id': process_id, "created_at": {"$gt": threshold_time}}

        tlir_results = []
        for result in await (
                db.tlir_results.find(res_filter, {"_id": False}).sort("created_at", -1).to_list(length=1000)):
            if result['result']['lane_id'] == lane_id:
                tlir_results.append(result)

        return tlir_results

    # --------------------- Composed Ratios -------------------------- #

    async def insert_composed_result(self, video_id, lane_id, process_id, timestamp, result):
        db = self.client[self.mongo_config['database']]
        composed_results = db.composed_results
        await composed_results.insert_one(
            {'process_id': process_id, 'video_id': video_id, 'lane_id': lane_id, 'created_at': timestamp,
             'result': result})

    async def list_composed_result_by_process_id(self, process_id):
        db = self.client[self.mongo_config['database']]
        res_filter = {'process_id': process_id}

        composed_results = {'process_id': process_id, 'lanes': {}}
        for result in await (
                db.composed_results.find(res_filter, {"_id": False}).sort("created_at", -1).to_list(length=1000)):
            res = {'created_at': result['created_at'], 'result': result['result']}
            if composed_results['lanes'].get(result['lane_id']) is None:
                composed_results['lanes'][result['lane_id']] = [res]
            else:
                composed_results['lanes'][result['lane_id']].append(res)

        return composed_results
