import argparse

from aiohttp import web

from app.config import MONGO_CONFIG
from app.service.video_service import VideoService
from app.service.db_service import DBService
from app.service.processing_service import ProcessingService


async def health_check(_request):
    return web.json_response({"ok": True})


async def init_app(debug=False, log_levels=None):
    if log_levels is None:
        log_levels = {}

    app = web.Application()
    db_service = DBService(MONGO_CONFIG)
    await db_service.init_db()
    processing_service = ProcessingService(db_service, debug, log_levels=log_levels)
    video_service = VideoService(db_service)

    app.router.add_get('/health', health_check)

    app.router.add_get('/videos', video_service.list_videos)
    app.router.add_post('/videos', video_service.add_video)
    app.router.add_get('/videos/{video_id}', video_service.get_video)
    app.router.add_delete('/videos/{video_id}', video_service.delete_video)

    app.router.add_post('/videos/{video_id}/lanes', video_service.add_lane)
    app.router.add_delete('/videos/{video_id}/lanes/{lane_id}', video_service.remove_lane)

    app.router.add_post('/videos/{video_id}/process', processing_service.start_processing)
    app.router.add_get('/processes', processing_service.list_processes)
    app.router.add_post('/processes/{process_id}', processing_service.stop_processing)

    app.router.add_get('/processes/{process_id}/speed_results', processing_service.list_speed_results_by_process_id)
    app.router.add_get('/processes/{process_id}/lanes/{lane_id}/speed_results', processing_service.list_speed_results_by_process_and_lane_id)

    app.router.add_get('/processes/{process_id}/mtlcr_results', processing_service.list_mtlcr_results_by_process_id)
    app.router.add_get('/processes/{process_id}/lanes/{lane_id}/mtlcr_results', processing_service.list_mtlcr_results_by_process_and_lane_id)

    app.router.add_get('/processes/{process_id}/composed_results', processing_service.list_composed_results_by_process_id)
    # app.router.add_get('/processes/{process_id}/lanes/{lane_id}/tlir_results', processing_service.list_speed_results_by_process_and_lane_id)

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--log', nargs='+', choices=['mtlcr', 'tlir', 'speed'], default=['tlir'], help='Log levels (choose from: mtlcr, tlir, speed)')

    args = parser.parse_args()
    is_debug = args.debug
    log_levels = {level: level in args.log for level in ['mtlcr', 'tlir', 'speed']}

    web.run_app(init_app(debug=is_debug, log_levels=log_levels))
