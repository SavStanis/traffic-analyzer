import json
import uuid

from aiohttp import web

from app.utils import log


class VideoService:
    def __init__(self, db_service):
        self.db_service = db_service

    async def add_video(self, request):
        video = await request.json()
        video['id'] = str(uuid.uuid4())
        video['lanes'] = []
        await self.db_service.insert_video(video)
        log('new video source was loaded: ' + video['link'])

        return web.json_response(status=200)

    async def get_video(self, request):
        video_id = request.match_info.get('video_id')
        video = await self.db_service.get_video(video_id)

        return web.json_response(video)

    async def list_videos(self, _request):
        videos = await self.db_service.list_videos()
        return web.json_response(videos)

    async def delete_video(self, request):
        video_id = request.match_info.get('video_id')
        await self.db_service.delete_video(video_id)

        return web.json_response(status=200)

    async def add_lane(self, request):
        video_id = request.match_info.get('video_id')
        video = await self.db_service.get_video(video_id)
        if video is None:
            return web.json_response(status=404)

        lane = await request.json()
        lane['id'] = str(uuid.uuid4())
        lane_name = lane['name']
        log(f'new lane was added to video {video_id}: ' + lane_name)

        video['lanes'].append(lane)
        await self.db_service.update_video(video_id, video)
        return web.json_response(status=200)

    async def remove_lane(self, request):
        video_id = request.match_info.get('video_id')
        lane_id = request.match_info.get('lane_id')
        video = await self.db_service.get_video(video_id)
        if video is None:
            return web.json_response(status=404)

        lanes = [lane for lane in video['lanes'] if lane['name'] != lane_id]
        video['lanes'] = lanes

        await self.db_service.update_video(video_id, video)
        return web.json_response(status=200)
