"""
Redis Queue para processamento assíncrono de deep scraping
"""
import os
import json
import uuid
import time
from typing import Optional, Dict, Any
from .util import normalize_url

try:
    import redis
except ImportError:
    redis = None

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
QUEUE_NAME = os.getenv('REDIS_QUEUE_NAME', 'deep_scrape_jobs')
JOB_PREFIX = 'deep_scrape_job:'
LOCK_PREFIX = 'lock:'
LOCK_TTL = 600  # segundos (10 minutos)


def get_redis():
    if redis is None:
        raise RuntimeError('redis-py não está instalado')
    return redis.from_url(REDIS_URL, decode_responses=True)


def enqueue_job(job_data: dict) -> str:
    """Enfileira um novo job e retorna o job_id"""
    import logging
    r = get_redis()
    job_id = str(uuid.uuid4())
    job_key = JOB_PREFIX + job_id
    job_record = {
        'job_id': job_id,
        'status': 'pending',
        'created_at': time.time(),
        'updated_at': time.time(),
        'error': None,
        'result_id': None,
        'params': job_data,
    }
    r.set(job_key, json.dumps(job_record))
    r.lpush(QUEUE_NAME, job_id)
    
    url = job_data.get('url', 'unknown')
    queue_length = r.llen(QUEUE_NAME)
    logging.info(f'📥 JOB ENFILEIRADO! Job ID: {job_id} - URL: {url} - Queue length: {queue_length}')
    
    return job_id


def dequeue_job(timeout: int = 5) -> Optional[dict]:
    """Remove e retorna o próximo job da fila (ou None se timeout)"""
    import logging
    r = get_redis()
    queue_length_before = r.llen(QUEUE_NAME)
    
    result = r.brpop(QUEUE_NAME, timeout=timeout)
    if result:
        _, job_id = result
        job_key = JOB_PREFIX + job_id
        job_json = r.get(job_key)
        if job_json:
            job_data = json.loads(job_json)
            url = job_data.get('params', {}).get('url', 'unknown')
            queue_length_after = r.llen(QUEUE_NAME)
            logging.info(f'📤 JOB RETIRADO DA QUEUE! Job ID: {job_id} - URL: {url} - Queue: {queue_length_before} → {queue_length_after}')
            return job_data
    
    return None


def set_job_status(job_id: str, status: str, result_id: Optional[str] = None, error: Optional[str] = None):
    """Atualiza o status do job no Redis"""
    r = get_redis()
    job_key = JOB_PREFIX + job_id
    job_json = r.get(job_key)
    if not job_json:
        return
    job = json.loads(job_json)
    job['status'] = status
    job['updated_at'] = time.time()
    if result_id:
        job['result_id'] = result_id
    if error:
        job['error'] = error
    r.set(job_key, json.dumps(job))


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Obtém o status do job"""
    r = get_redis()
    job_key = JOB_PREFIX + job_id
    job_json = r.get(job_key)
    if not job_json:
        return None
    return json.loads(job_json)


def set_job_progress(job_id: str, progress: dict):
    """Atualiza o progresso do job no Redis"""
    r = get_redis()
    job_key = JOB_PREFIX + job_id
    job_json = r.get(job_key)
    if not job_json:
        return
    job = json.loads(job_json)
    job['progress'] = progress
    job['updated_at'] = time.time()
    r.set(job_key, json.dumps(job))


def get_job_progress(job_id: str) -> Optional[Dict[str, Any]]:
    """Obtém o progresso do job"""
    r = get_redis()
    job_key = JOB_PREFIX + job_id
    job_json = r.get(job_key)
    if not job_json:
        return None
    job = json.loads(job_json)
    return job.get('progress', None)


def acquire_lock(url: str, ttl: int = LOCK_TTL) -> bool:
    """
    Tenta adquirir um lock distribuído para a URL normalizada.
    Retorna True se o lock foi adquirido, False caso contrário.
    """
    r = get_redis()
    key = LOCK_PREFIX + normalize_url(url)
    # SETNX + EXPIRE atômico
    return r.set(key, '1', nx=True, ex=ttl)


def release_lock(url: str):
    """
    Libera o lock distribuído para a URL normalizada.
    """
    r = get_redis()
    key = LOCK_PREFIX + normalize_url(url)
    r.delete(key) 