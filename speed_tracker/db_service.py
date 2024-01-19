import motor


class DBService:
    def __init__(self, mongo_config):
        self.mongo_config = mongo_config
        self.client = None

    async def init_db(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            f"mongodb://{self.mongo_config['username']}:{self.mongo_config['password']}@"
            f"{self.mongo_config['host']}:{self.mongo_config['port']}/admin"
        )

    async def insert_speed_result(self, parent_process_id, process_id, timestamp, result):
        db = self.client[self.mongo_config['database']]
        speed_results = db.speed_results
        await speed_results.insert_one(
            {'parent_process_id': parent_process_id, 'process_id': process_id, 'created_at': timestamp,
             'result': result})
