import os
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import redis.asyncio as redis

router = APIRouter(prefix='/ws', tags=['websocket'])

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
PROGRESS_CHANNEL = 'deep_scrape_progress'

async def redis_subscribe(job_id):
    r = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(PROGRESS_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get('job_id') == job_id:
                    yield data['progress']
    finally:
        await pubsub.unsubscribe(PROGRESS_CHANNEL)
        await pubsub.close()
        await r.close()

@router.websocket('/deep-scrape/{job_id}')
async def ws_deep_scrape_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        # Busca inicial do progresso
        r = redis.from_url(REDIS_URL, decode_responses=True)
        progress_key = f"job_progress:{job_id}"
        progress_json = await r.get(progress_key)
        if progress_json:
            progress = json.loads(progress_json)
            await websocket.send_json(progress)
            if progress.get('percent', 0) >= 100 or progress.get('status') in ('done', 'error'):
                await websocket.close()
                await r.close()
                return
        await r.close()
        # Loop de subscribe
        async for progress in redis_subscribe(job_id):
            await websocket.send_json(progress)
            if progress.get('percent', 0) >= 100 or progress.get('status') in ('done', 'error'):
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({'error': str(e)})
    finally:
        await websocket.close() 