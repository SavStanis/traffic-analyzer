import asyncio
import json
import time
import uuid

from aiohttp import web
from datetime import datetime

from app.utils import serialize_date_times, log, proc_type_2_short
from tlir.tlir import calc_tlir


TLIR_CALCULATION = 'TLIR_CALCULATION'
SPEED_EVALUATION = 'SPEED_EVALUATION'
MTLCR_CALCULATION = 'MTLCR_CALCULATION'

class ProcessingService:
    def __init__(self, db_service, debug=False, log_levels=None):
        if log_levels is None:
            log_levels = {}
        self.active_processes = {}
        self.db_service = db_service
        self.debug = debug
        self.log_levels = log_levels

    async def start_processing(self, request):
        video_id = request.match_info.get('video_id')
        video = await self.db_service.get_video(video_id)
        if video is None:
            return web.json_response(status=404)

        parent_process_id = str(uuid.uuid4())
        speed_process_id = str(uuid.uuid4())
        tlir_process_id = str(uuid.uuid4())
        asyncio.create_task(self.start_speed_calc_process(video, parent_process_id, speed_process_id))
        mtlcr_process_id = str(uuid.uuid4())
        asyncio.create_task(self.start_mtlcr_calc_process(video, parent_process_id, mtlcr_process_id))
        asyncio.create_task(self.start_tlir_calc_process(video, parent_process_id, mtlcr_process_id, tlir_process_id))
        self.active_processes[speed_process_id] = {'process_type': SPEED_EVALUATION, 'video_path': video['link']}
        self.active_processes[mtlcr_process_id] = {'process_type': MTLCR_CALCULATION, 'video_path': video['link']}

        message = f"Processing started for {video['link']} with ID {parent_process_id} and subprocess IDs {speed_process_id} (SPEED_EVALUATION) and {mtlcr_process_id} (MTLCR_CALCULATION)"
        log(message)

        return web.Response(text=message)

    async def start_speed_calc_process(self, video, parent_process_id, process_id):
        script_args = ['speed_tracker/tracker.py', '--video_path', video['link'], '--lanes', json.dumps(video['lanes'])]
        await self.start_external_process(parent_process_id, process_id, SPEED_EVALUATION, video['link'], script_args, self.db_service.insert_speed_result)

    async def start_mtlcr_calc_process(self, video, parent_process_id, process_id):
        script_args = ['mtlcr/run_mtlcr.py', '--video_path', video['link'], '--lanes', json.dumps(video['lanes'])]
        await self.start_external_process(parent_process_id, process_id, MTLCR_CALCULATION, video['link'], script_args, self.db_service.insert_mtlcr_result)

    async def start_external_process(self, parent_process_id, process_id, process_type, video_link, script_args, result_saver):  # process_id, timestamp, result
        await self.db_service.insert_active_process(parent_process_id, process_id, video_link, process_type)

        if self.debug:
            script_args.append("--debug")

        process = await asyncio.create_subprocess_exec(
            'python3',
            *script_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        while True:
            line = (await process.stdout.readline()).decode('utf-8')
            if not line:
                break

            if line == '\n' or line[0] != "{":
                continue

            if self.log_levels[proc_type_2_short(process_type)]:
                log(f"New value from process {process_id} ({process_type}): {line}")

            result = json.loads(line)
            await result_saver(parent_process_id, process_id, datetime.utcnow(), result)

            if process_id not in self.active_processes:
                process.terminate()
                await process.communicate()
                break

        await self.db_service.finish_active_process(process_id)
        log(f"Process {process_id} ({process_type}) finished")

        del self.active_processes[process_id]

    async def start_tlir_calc_process(self, video, parent_process_id, mtlcr_process_id, tlir_process_id,
                                      calc_interval=5, speed_calc_timeout=60):    # calc_interval - seconds, speed_calc_timeout - seconds
        while True:
            time.sleep(calc_interval)
            for lane in video['lanes']:
                mtlcr_list = await self.db_service.list_mtlcr_results_by_process_and_lane_id(parent_process_id, lane['id'], limit=1)
                if len(mtlcr_list) == 0:
                    mtlcr = 0
                else:
                    mtlcr = mtlcr_list[0]['result']['mtlcr']

                speed_list = await self.db_service.list_speed_results_by_process_and_lane_id(parent_process_id, lane['id'], newer_than_seconds=speed_calc_timeout, limit=10)
                max_speed = lane['max_speed']

                speed_list = list(map(lambda obj: obj['result']['speed'], speed_list))
                tlir = calc_tlir(mtlcr, speed_list, max_speed)
                result = {'mtlcr': mtlcr, 'tlir': tlir}

                result_log = {'video_id': video['id'], 'lane_id': lane['id'], 'mtlcr': mtlcr, 'tlir': tlir}
                log(f"New value from process {tlir_process_id} ({TLIR_CALCULATION}): {json.dumps(result_log)}")

                await self.db_service.insert_composed_result(video['id'], lane['id'], parent_process_id, datetime.utcnow(), result)

            if mtlcr_process_id not in self.active_processes:
                log(f"Process {tlir_process_id} ({TLIR_CALCULATION}) finished")
                break


    async def stop_processing(self, request):
        process_id = request.match_info.get('process_id')   # id of subprocess

        if process_id in self.active_processes:
            del self.active_processes[process_id]

        return web.Response(text=f"Processing stopped for process ID {process_id}")

    async def list_processes(self, _request):
        processes = await self.db_service.list_processes()
        return web.json_response(processes)

    #  ------------------ Speed ------------------------------

    async def list_speed_results_by_process_id(self, request):
        process_id = request.match_info.get('process_id')
        results = await self.db_service.list_speed_results_by_process_id(process_id)
        results = serialize_date_times(results)
        return web.json_response(results)

    async def list_speed_results_by_process_and_lane_id(self, request):
        process_id = request.match_info.get('process_id')
        lane_id = request.match_info.get('lane_id')

        results = await self.db_service.list_speed_results_by_process_and_lane_id(process_id, lane_id)
        results = serialize_date_times(results)
        return web.json_response(results)

    #  ------------------ MTLCR ------------------------------

    async def list_mtlcr_results_by_process_id(self, request):
        process_id = request.match_info.get('process_id')
        results = await self.db_service.list_mtlcr_results_by_process_id(process_id)
        results = serialize_date_times(results)
        return web.json_response(results)

    async def list_mtlcr_results_by_process_and_lane_id(self, request):
        process_id = request.match_info.get('process_id')
        lane_id = request.match_info.get('lane_id')

        results = await self.db_service.list_mtlcr_results_by_process_and_lane_id(process_id, lane_id)
        results = serialize_date_times(results)
        return web.json_response(results)

    #  ------------------ MTLCR + TLIR ------------------------------

    async def list_composed_results_by_process_id(self, request):
        process_id = request.match_info.get('process_id')
        results = await self.db_service.list_composed_result_by_process_id(process_id)
        results = serialize_date_times(results)
        return web.json_response(results)
