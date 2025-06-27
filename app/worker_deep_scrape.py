#!/usr/bin/env python3
"""
Worker para processamento assíncrono de deep scraping via Redis Queue
"""
import os
import sys
import time
import logging
import asyncio
import json
from playwright.async_api import async_playwright

# sys.path.append('./app')  # Não necessário quando executado com working_dir correto

from internal import redis_queue, redis_cache, util
from router import deep_scrape
from internal.redis_queue import acquire_lock, release_lock

PROGRESS_CHANNEL = 'deep_scrape_progress'

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

async def process_job(job):
    job_id = job['job_id']
    params = job['params']
    url = params.get("url")
    logging.info(f'Iniciando processamento do job {job_id} para URL: {url}')
    # Distributed Locking
    if not acquire_lock(url):
        logging.warning(f'Lock não adquirido para URL: {url}. Job {job_id} será pulado.')
        redis_queue.set_job_status(job_id, 'skipped', error='Lock não adquirido, processamento concorrente detectado.')
        return
    redis_queue.set_job_status(job_id, 'running')
    try:
        from starlette.datastructures import URL
        class DummyRequest:
            def __init__(self, url_str):
                self.url = URL(url_str)
                self.state = type('obj', (), {'browser': None, 'semaphore': asyncio.Semaphore(1)})
                self.headers = {}
                self.base_url = URL(scheme=self.url.scheme, netloc=self.url.netloc)
        request = DummyRequest(params['url'])

        from router.query_params import URLParam, CommonQueryParams, BrowserQueryParams, ProxyQueryParams, ReadabilityQueryParams
        from router.deep_scrape import DeepScrapeQueryParams

        logging.info(f"DEBUG: params structure: {json.dumps(params, indent=2)}")

        url_param = URLParam(params['url'])
        common_params = CommonQueryParams(**params['params'])
        browser_params = BrowserQueryParams(**params['browser_params'])
        proxy_params = ProxyQueryParams(**params['proxy_params'])
        readability_params = ReadabilityQueryParams(**params['readability_params'])
        deep_scrape_params = DeepScrapeQueryParams(**params['deep_scrape_params'])

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            request.state.browser = browser

            async def progress_callback(progress):
                redis_queue.set_job_progress(job_id, progress)
                publish_progress(job_id, progress)

            result = await deep_scrape.deep_scrape(
                request, url_param, common_params, browser_params, proxy_params,
                readability_params, deep_scrape_params, _=None, progress_callback=progress_callback
            )
            r_id = result['id']
            # Salvar resultado no cache Redis
            redis_cache.store_result(r_id, result)
            redis_queue.set_job_status(job_id, 'done', result_id=r_id)
            logging.info(f'Job {job_id} finalizado com sucesso. Result ID: {r_id}')
            # Publicar progresso final
            final_progress = {
                'current_level': deep_scrape_params.depth,
                'current_page': 0,
                'pages_in_level': 0,
                'total_levels': deep_scrape_params.depth,
                'total_pages': result.get('total_pages', 0) if isinstance(result, dict) else 0,
                'last_url': url,
                'percent': 100,
                'status': 'done',
                'job_id': job_id,
            }
            redis_queue.set_job_progress(job_id, final_progress)
            publish_progress(job_id, final_progress)
            await browser.close()
    except Exception as e:
        logging.error(f'Erro no job {job_id}: {e}')
        redis_queue.set_job_status(job_id, 'error', error=str(e))
        # Publicar progresso final de erro
        error_progress = {
            'current_level': 0,
            'current_page': 0,
            'pages_in_level': 0,
            'total_levels': 0,
            'total_pages': 0,
            'last_url': url,
            'percent': 100,
            'status': 'error',
            'job_id': job_id,
            'error': str(e),
        }
        redis_queue.set_job_progress(job_id, error_progress)
        publish_progress(job_id, error_progress)
    finally:
        release_lock(url)


def publish_progress(job_id, progress):
    try:
        import redis as redislib
        r = redislib.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
        msg = json.dumps({'job_id': job_id, 'progress': progress})
        r.publish(PROGRESS_CHANNEL, msg)
    except Exception as e:
        logging.error(f'Erro ao publicar progresso no Pub/Sub: {e}')


def main():
    logging.info('Worker de deep scraping iniciado. Aguardando jobs...')
    job_count = 0
    while True:
        logging.debug('Verificando por novos jobs na queue...')
        job = redis_queue.dequeue_job(timeout=10)
        if job:
            job_count += 1
            job_id = job.get('job_id', 'unknown')
            url = job.get('params', {}).get('url', 'unknown')
            logging.info(f'🎯 NOVO JOB RECEBIDO! #{job_count} - Job ID: {job_id} - URL: {url}')
            asyncio.run(process_job(job))
            logging.info(f'✅ Job {job_id} finalizado. Total processados: {job_count}')
        else:
            logging.debug('Nenhum job encontrado. Aguardando 2 segundos...')
            time.sleep(2)

if __name__ == '__main__':
    main() 