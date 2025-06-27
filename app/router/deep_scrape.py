import asyncio
import datetime
from typing import Annotated, List, Dict, Set
from collections import deque
from urllib.parse import urljoin, urlparse
import logging
import re
import html
import subprocess
import os
import tempfile
from pathlib import Path

import tldextract

# WeasyPrint será importado sob demanda para evitar falhas de carregamento do módulo
WEASYPRINT_AVAILABLE = None  # Will be determined on first use

from fastapi import APIRouter, Query, Depends
from fastapi.requests import Request
from pydantic import BaseModel
from playwright.async_api import Browser

from internal import util, cache, redis_cache, redis_queue
from internal.browser import (
    new_context,
    page_processing,
    get_screenshot,
)
from internal.errors import ArticleParsingError
from .query_params import (
    URLParam,
    CommonQueryParams,
    BrowserQueryParams,
    ProxyQueryParams,
    ReadabilityQueryParams,
)
from server.auth import AuthRequired
from settings import READABILITY_SCRIPT, PARSER_SCRIPTS_DIR


router = APIRouter(prefix='/api/deep-scrape', tags=['deep-scrape'])


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to Markdown format"""
    if not html_content:
        return ""
    
    # Remove script and style tags
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert HTML tags to Markdown
    conversions = [
        # Headers
        (r'<h1[^>]*>(.*?)</h1>', r'# \1\n'),
        (r'<h2[^>]*>(.*?)</h2>', r'## \1\n'),
        (r'<h3[^>]*>(.*?)</h3>', r'### \1\n'),
        (r'<h4[^>]*>(.*?)</h4>', r'#### \1\n'),
        (r'<h5[^>]*>(.*?)</h5>', r'##### \1\n'),
        (r'<h6[^>]*>(.*?)</h6>', r'###### \1\n'),
        
        # Paragraphs
        (r'<p[^>]*>(.*?)</p>', r'\1\n\n'),
        
        # Line breaks
        (r'<br[^>]*/?>', r'\n'),
        
        # Links
        (r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)'),
        
        # Images
        (r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>', r'![\2](\1)'),
        (r'<img[^>]*alt="([^"]*)"[^>]*src="([^"]*)"[^>]*/?>', r'![\1](\2)'),
        (r'<img[^>]*src="([^"]*)"[^>]*/?>', r'![](\1)'),
        
        # Bold and italic
        (r'<strong[^>]*>(.*?)</strong>', r'**\1**'),
        (r'<b[^>]*>(.*?)</b>', r'**\1**'),
        (r'<em[^>]*>(.*?)</em>', r'*\1*'),
        (r'<i[^>]*>(.*?)</i>', r'*\1*'),
        
        # Code
        (r'<code[^>]*>(.*?)</code>', r'`\1`'),
        (r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```\n'),
        
        # Lists
        (r'<ul[^>]*>(.*?)</ul>', lambda m: _convert_list(m.group(1), ordered=False)),
        (r'<ol[^>]*>(.*?)</ol>', lambda m: _convert_list(m.group(1), ordered=True)),
        
        # Blockquote
        (r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1\n'),
        
        # Divs and spans (just remove tags, keep content)
        (r'<div[^>]*>(.*?)</div>', r'\1\n'),
        (r'<span[^>]*>(.*?)</span>', r'\1'),
        
        # Remove other HTML tags
        (r'<[^>]+>', ''),
    ]
    
    # Apply conversions
    for pattern, replacement in conversions:
        if callable(replacement):
            html_content = re.sub(pattern, replacement, html_content, flags=re.DOTALL | re.IGNORECASE)
        else:
            html_content = re.sub(pattern, replacement, html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Decode HTML entities
    html_content = html.unescape(html_content)
    
    # Clean up extra whitespace
    html_content = re.sub(r'\n\s*\n\s*\n', '\n\n', html_content)
    html_content = re.sub(r'[ \t]+', ' ', html_content)
    html_content = html_content.strip()
    
    return html_content


def _convert_list(list_content: str, ordered: bool = False) -> str:
    """Convert HTML list items to Markdown"""
    items = re.findall(r'<li[^>]*>(.*?)</li>', list_content, flags=re.DOTALL | re.IGNORECASE)
    result = []
    
    for i, item in enumerate(items):
        # Clean the item content
        item = re.sub(r'<[^>]+>', '', item).strip()
        if ordered:
            result.append(f"{i+1}. {item}")
        else:
            result.append(f"- {item}")
    
    return '\n'.join(result) + '\n\n'


def generate_pdf_from_scraped_html(scraped_html_content: str, base_url: str, output_path: str) -> bool:
    """
    Gera um PDF de alta fidelidade a partir de um conteúdo HTML usando WeasyPrint.
    """
    global WEASYPRINT_AVAILABLE
    
    # Forçar import do WeasyPrint - sabemos que está disponível
    try:
        from weasyprint import HTML, CSS
        WEASYPRINT_AVAILABLE = True
        logging.info("WeasyPrint importado com sucesso na função PDF")
    except ImportError as e:
        logging.error(f"WeasyPrint não disponível na função PDF: {e}")
        return False
    
    try:
        logging.info(f"Gerando PDF para: {output_path}")
        
        # Criar diretório de saída se não existir
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar HTML object
        html = HTML(string=scraped_html_content, base_url=base_url)
        
        # CSS customizado para melhor formatação
        stylesheet = CSS(string='''
            @page { 
                size: A4; 
                margin: 2cm; 
                @bottom-center {
                    content: counter(page) " / " counter(pages);
                    font-size: 10px;
                    color: #666;
                }
            }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #2c3e50;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }
            h1 { border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }
            h2 { border-bottom: 1px solid #e1e4e8; padding-bottom: 0.3em; }
            ul, ol { 
                list-style-position: inside;
                margin: 1em 0;
            }
            a { 
                color: #0066cc; 
                text-decoration: none;
            }
            a:hover { text-decoration: underline; }
            img { 
                max-width: 100%; 
                height: auto; 
                margin: 1em 0;
            }
            code {
                background-color: #f6f8fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            pre {
                background-color: #f6f8fa;
                padding: 1em;
                border-radius: 5px;
                overflow-x: auto;
            }
            blockquote {
                border-left: 4px solid #dfe2e5;
                padding-left: 1em;
                color: #6a737d;
                margin: 1em 0;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }
            th, td {
                border: 1px solid #dfe2e5;
                padding: 0.5em;
                text-align: left;
            }
            th {
                background-color: #f6f8fa;
                font-weight: bold;
            }
        ''')
        
        # Gerar PDF
        html.write_pdf(output_path, stylesheets=[stylesheet])
        logging.info(f"✅ PDF gerado com sucesso em: {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao gerar PDF com WeasyPrint: {e}")
        return False


def generate_docx_from_scraped_html(scraped_html_content: str, output_path: str) -> bool:
    """
    Usa o pandoc para converter HTML em um arquivo DOCX bem formatado.
    """
    temp_html_path = None
    try:
        logging.info(f"Gerando DOCX para: {output_path}")
        
        # Criar diretório de saída se não existir
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar arquivo HTML temporário
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".html", delete=False) as f:
            temp_html_path = f.name
            
            # Melhorar o HTML com metadados e CSS inline
            enhanced_html = f"""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Deep Scraping Results</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c3e50;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                    }}
                    h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }}
                    h2 {{ border-bottom: 1px solid #e1e4e8; padding-bottom: 0.3em; }}
                    a {{ color: #0066cc; }}
                    blockquote {{
                        border-left: 4px solid #dfe2e5;
                        padding-left: 1em;
                        color: #6a737d;
                        margin: 1em 0;
                    }}
                    code {{
                        background-color: #f6f8fa;
                        padding: 0.2em 0.4em;
                        border-radius: 3px;
                    }}
                    pre {{
                        background-color: #f6f8fa;
                        padding: 1em;
                        border-radius: 5px;
                    }}
                </style>
            </head>
            <body>
            {scraped_html_content}
            </body>
            </html>
            """
            f.write(enhanced_html)

        # Comando pandoc com opções aprimoradas
        command = [
            "pandoc", 
            temp_html_path, 
            "-o", output_path, 
            "--from", "html", 
            "--to", "docx",
            "--standalone",
            "--reference-doc=" if os.path.exists("reference.docx") else "",  # Template opcional
        ]
        
        # Remover argumento vazio se não houver template
        command = [arg for arg in command if arg]
        
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logging.info(f"✅ DOCX gerado com sucesso em: {output_path}")
        return True
        
    except FileNotFoundError:
        logging.error("❌ ERRO: O comando 'pandoc' não foi encontrado. Verifique se ele está instalado e no PATH do sistema.")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Erro durante a conversão com pandoc: {e}")
        logging.error(f"Saída do erro: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado ao gerar DOCX: {e}")
        return False
    finally:
        # Limpar arquivo temporário
        if temp_html_path and os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
            except Exception as e:
                logging.warning(f"Não foi possível remover arquivo temporário {temp_html_path}: {e}")


def generate_consolidated_html(result_data: dict) -> str:
    """Gerar HTML consolidado bem formatado para conversão em PDF/DOCX"""
    domain = result_data.get('domain', 'unknown')
    base_url = result_data.get('base_url', '')
    date = result_data.get('date', '')
    total_pages = result_data.get('total_pages', 0)
    levels = result_data.get('levels', [])
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Deep Scraping Results: {domain}</title>
    </head>
    <body>
        <header>
            <h1>Deep Scraping Results: {domain}</h1>
            <div class="meta-info">
                <p><strong>Base URL:</strong> <a href="{base_url}">{base_url}</a></p>
                <p><strong>Date:</strong> {date}</p>
                <p><strong>Total Pages:</strong> {total_pages}</p>
                <p><strong>Levels:</strong> {len(levels)}</p>
            </div>
            <hr>
        </header>
        
        <main>
    """
    
    # Adicionar índice
    html_content += "<h2>Table of Contents</h2>\n<ol>\n"
    page_counter = 1
    
    for level in levels:
        for page in level.get('pages', []):
            title = page.get('title', f'Page {page_counter}')
            html_content += f'<li><a href="#page-{page_counter}">{title}</a></li>\n'
            page_counter += 1
    
    html_content += "</ol>\n<hr>\n"
    
    # Adicionar conteúdo por níveis
    page_counter = 1
    for level in levels:
        level_num = level.get('level', 0)
        pages = level.get('pages', [])
        
        if pages:
            html_content += f"<h2>Level {level_num}</h2>\n"
            html_content += f"<p><em>{len(pages)} pages at this level</em></p>\n"
            
            for page in pages:
                title = page.get('title', 'Untitled Page')
                url = page.get('url', '')
                content = page.get('content', '')
                byline = page.get('byline', '')
                excerpt = page.get('excerpt', '')
                
                html_content += f'<article id="page-{page_counter}">\n'
                html_content += f"<h3>{page_counter}. {title}</h3>\n"
                html_content += f'<p class="page-meta"><strong>URL:</strong> <a href="{url}">{url}</a></p>\n'
                
                if byline:
                    html_content += f'<p class="byline"><strong>Author:</strong> {byline}</p>\n'
                
                if excerpt:
                    html_content += f'<p class="excerpt"><em>{excerpt}</em></p>\n'
                
                html_content += '<div class="page-content">\n'
                html_content += content or ''
                html_content += '\n</div>\n'
                html_content += '</article>\n<hr>\n'
                
                page_counter += 1
    
    html_content += """
        </main>
    </body>
    </html>
    """
    
    return html_content


class DeepScrapeQueryParams:
    """Deep scraping specific parameters"""
    
    def __init__(
        self,
        depth: Annotated[
            int,
            Query(
                description='Maximum depth for recursive scraping. Depth 1 means only the base URL, depth 2 includes direct links, etc.',
                ge=1,
                le=10,
            ),
        ] = 3,
        max_urls_per_level: Annotated[
            int,
            Query(
                alias='max-urls-per-level',
                description='Maximum number of URLs to scrape per level to avoid overwhelming.',
                ge=1,
                le=50,
            ),
        ] = 10,
        same_domain_only: Annotated[
            bool,
            Query(
                alias='same-domain-only',
                description='Whether to restrict scraping to the same domain only.',
            ),
        ] = True,
        delay_between_requests: Annotated[
            float,
            Query(
                alias='delay-between-requests',
                description='Delay in seconds between requests to be respectful to the target server.',
                ge=0.1,
                le=10.0,
            ),
        ] = 1.0,
        exclude_patterns: Annotated[
            str | None,
            Query(
                alias='exclude-patterns',
                description='Comma-separated list of URL patterns to exclude (e.g., "/admin,/login,/logout").',
            ),
        ] = None,
    ):
        self.depth = depth
        self.max_urls_per_level = max_urls_per_level
        self.same_domain_only = same_domain_only
        self.delay_between_requests = delay_between_requests
        self.exclude_patterns = []
        if exclude_patterns:
            if isinstance(exclude_patterns, list):
                self.exclude_patterns = [pattern.strip() for pattern in exclude_patterns if pattern.strip()]
            elif isinstance(exclude_patterns, str):
                self.exclude_patterns = [pattern.strip() for pattern in exclude_patterns.split(',') if pattern.strip()]
            else:
                self.exclude_patterns = []


class DeepScrapeResult(BaseModel):
    id: Annotated[str, Query(description='unique result ID')]
    base_url: Annotated[str, Query(description='base URL that was scraped')]
    domain: Annotated[str, Query(description="base domain")]
    date: Annotated[str, Query(description='date of deep scraping in ISO 8601 format')]
    query: Annotated[dict, Query(description='request parameters')]
    total_pages: Annotated[int, Query(description='total number of pages scraped')]
    levels: Annotated[List[Dict], Query(description='hierarchical structure of scraped content')]
    resultUri: Annotated[str, Query(description='URL of the current result')]
    screenshotUri: Annotated[str | None, Query(description='URL of the screenshot of the base page')] = None


@router.get('', summary='Deep scrape a website recursively', response_model=DeepScrapeResult)
async def deep_scrape(
    request: Request,
    url: Annotated[URLParam, Depends()],
    params: Annotated[CommonQueryParams, Depends()],
    browser_params: Annotated[BrowserQueryParams, Depends()],
    proxy_params: Annotated[ProxyQueryParams, Depends()],
    readability_params: Annotated[ReadabilityQueryParams, Depends()],
    deep_scrape_params: Annotated[DeepScrapeQueryParams, Depends()],
    _: AuthRequired = None,
    progress_callback=None,
) -> dict:
    """
    Deep scrape a website recursively with configurable depth.<br><br>
    This endpoint will start from the base URL, extract its content and links, 
    then recursively scrape linked pages up to the specified depth.
    """
    # split URL into parts: host with scheme, path with query, query params as a dict
    host_url, full_path, query_dict = util.split_url(request.url)

    # get cache data if exists
    r_id = redis_cache.make_key(full_path)  # unique result ID
    if params.cache:
        data = redis_cache.load_result(key=r_id)
        if data:
            return data

    browser: Browser = request.state.browser
    semaphore: asyncio.Semaphore = request.state.semaphore

    logger = logging.getLogger(__name__)
    logger.info(f"Starting deep scrape of {url.url} with depth {deep_scrape_params.depth}")

    # Initialize tracking variables
    visited_urls: Set[str] = set()
    all_results = []
    
    # Queue structure: (url, current_depth, parent_index)
    url_queue = deque([(url.url, 0, -1)])
    base_domain = tldextract.extract(url.url).registered_domain
    
    current_level = 0
    level_results = []
    
    base_screenshot = None
    
    async with semaphore:
        while url_queue and current_level < deep_scrape_params.depth:
            level_urls = []
            
            # Collect all URLs for current level
            while url_queue and url_queue[0][1] == current_level:
                current_url, depth, parent_idx = url_queue.popleft()
                if current_url not in visited_urls:
                    level_urls.append((current_url, depth, parent_idx))
                    visited_urls.add(current_url)
            
            if not level_urls:
                break
                
            # Limit URLs per level
            level_urls = level_urls[:deep_scrape_params.max_urls_per_level]
            
            logger.info(f"Processing level {current_level} with {len(level_urls)} URLs")
            
            level_data = {
                'level': current_level,
                'pages': []
            }
            
            for i, (current_url, depth, parent_idx) in enumerate(level_urls):
                try:
                    logger.info(f"Scraping: {current_url}")
                    
                    async with new_context(browser, browser_params, proxy_params) as context:
                        page = await context.new_page()
                        await page_processing(
                            page=page,
                            url=current_url,
                            params=params,
                            browser_params=browser_params,
                            init_scripts=[READABILITY_SCRIPT],
                        )
                        page_content = await page.content()
                        page_url = page.url
                        
                        # Take screenshot only for base URL
                        screenshot = None
                        if current_level == 0 and i == 0 and params.screenshot:
                            screenshot = await get_screenshot(page)
                            base_screenshot = screenshot

                        # Extract article content
                        parser_args = {
                            'maxElemsToParse': readability_params.max_elems_to_parse,
                            'nbTopCandidates': readability_params.nb_top_candidates,
                            'charThreshold': readability_params.char_threshold,
                        }
                        
                        with open(PARSER_SCRIPTS_DIR / 'article.js', encoding='utf-8') as f:
                            article = await page.evaluate(f.read() % parser_args)
                        
                        # Extract links for next level
                        if current_level + 1 < deep_scrape_params.depth:
                            with open(PARSER_SCRIPTS_DIR / 'links.js', encoding='utf-8') as f:
                                links = await page.evaluate(f.read() % {})
                            
                            if links and 'err' not in links:
                                for link in links[:20]:  # Limit links per page
                                    link_url = link.get('url')
                                    if link_url and _is_valid_url(
                                        link_url, current_url, base_domain, 
                                        deep_scrape_params, visited_urls
                                    ):
                                        absolute_url = urljoin(current_url, link_url)
                                        url_queue.append((absolute_url, current_level + 1, len(all_results)))
                        
                        # Process article result
                        if article and 'err' not in article:
                            # Convert HTML content to Markdown
                            content_markdown = html_to_markdown(article.get('content', ''))
                            
                            page_result = {
                                'url': page_url,
                                'title': article.get('title'),
                                'content': article.get('content'),  # Keep original HTML for compatibility
                                'contentMarkdown': content_markdown,  # New Markdown version
                                'textContent': article.get('textContent'),
                                'byline': article.get('byline'),
                                'excerpt': article.get('excerpt'),
                                'length': len(article.get('textContent', '')) if article.get('textContent') else 0,
                                'lang': article.get('lang'),
                                'parent_index': parent_idx,
                                'level': current_level,
                                'meta': util.social_meta_tags(page_content),
                            }
                            
                            if params.full_content:
                                page_result['fullContent'] = page_content
                            
                            level_data['pages'].append(page_result)
                            all_results.append(page_result)

                        # Progresso por página
                        if progress_callback:
                            progress = {
                                'current_level': current_level,
                                'current_page': i + 1,
                                'pages_in_level': len(level_urls),
                                'total_levels': deep_scrape_params.depth,
                                'total_pages': len(all_results),
                                'last_url': current_url,
                                'percent': round(100 * (current_level + (i + 1) / len(level_urls)) / deep_scrape_params.depth, 2) if len(level_urls) > 0 else 0,
                            }
                            await progress_callback(progress)
                        
                        # Respectful delay between requests
                        if deep_scrape_params.delay_between_requests > 0:
                            await asyncio.sleep(deep_scrape_params.delay_between_requests)
                            
                except Exception as e:
                    logger.error(f"Error scraping {current_url}: {str(e)}")
                    continue
            
            if level_data['pages']:
                level_results.append(level_data)
            
            # Progresso por nível
            if progress_callback:
                progress = {
                    'current_level': current_level + 1,
                    'current_page': 0,
                    'pages_in_level': 0,
                    'total_levels': deep_scrape_params.depth,
                    'total_pages': len(all_results),
                    'last_url': None,
                    'percent': round(100 * (current_level + 1) / deep_scrape_params.depth, 2),
                }
                await progress_callback(progress)
            current_level += 1

    # Prepare final result
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    domain = tldextract.extract(url.url).registered_domain
    
    result = {
        'id': r_id,
        'base_url': url.url,
        'domain': domain,
        'date': now,
        'resultUri': f'{host_url}/result/{r_id}',
        'query': query_dict,
        'total_pages': len(all_results),
        'levels': level_results,
    }
    
    if params.screenshot and base_screenshot:
        result['screenshotUri'] = f'{host_url}/screenshot/{r_id}'

    # Save result to cache (Redis with file fallback)
    redis_cache.store_result(key=r_id, data=result)
    
    # Save screenshot separately (still using file system for now)
    if base_screenshot:
        cache.dump_screenshot(key=r_id, screenshot=base_screenshot)
    
    logger.info(f"Deep scrape completed. Total pages: {len(all_results)}")
    return result


def generate_consolidated_markdown(result_data: dict) -> str:
    """Generate a consolidated Markdown document from deep scrape results"""
    markdown_content = []
    
    # Header
    markdown_content.append(f"# Deep Scraping Results: {result_data['domain']}")
    markdown_content.append(f"**Base URL:** {result_data['base_url']}")
    markdown_content.append(f"**Date:** {result_data['date']}")
    markdown_content.append(f"**Total Pages:** {result_data['total_pages']}")
    markdown_content.append(f"**Levels:** {len(result_data['levels'])}")
    markdown_content.append("\n---\n")
    
    # Table of Contents
    markdown_content.append("## Table of Contents")
    toc_items = []
    page_counter = 1
    
    for level in result_data['levels']:
        for page in level['pages']:
            title = page.get('title', f'Page {page_counter}')
            toc_items.append(f"{page_counter}. {title}")
            page_counter += 1
    
    markdown_content.extend(toc_items)
    markdown_content.append("\n---\n")
    
    # Content by levels
    for level in result_data['levels']:
        markdown_content.append(f"## Level {level['level']}")
        markdown_content.append(f"*{len(level['pages'])} pages at this level*\n")
        
        for page in level['pages']:
            title = page.get('title', 'Untitled Page')
            
            markdown_content.append(f"### {title}")
            markdown_content.append(f"**URL:** {page['url']}")
            
            if page.get('byline'):
                markdown_content.append(f"**Author:** {page['byline']}")
            
            if page.get('excerpt'):
                markdown_content.append(f"*{page['excerpt']}*")
            
            markdown_content.append("")  # Empty line
            
            # Add the markdown content
            if page.get('contentMarkdown'):
                markdown_content.append(page['contentMarkdown'])
            
            markdown_content.append("\n---\n")
    
    return '\n'.join(markdown_content)


@router.get('/pdf', summary='Generate high-quality PDF from deep scrape results using WeasyPrint')
async def deep_scrape_pdf(
    request: Request,
    _: AuthRequired = None,
    result_id: Annotated[
        str | None,
        Query(
            alias='result_id',
            description='Result ID from previous deep scrape operation',
        ),
    ] = None,
) -> dict:
    """
    Generate a high-quality PDF document from deep scrape results using WeasyPrint.
    This produces much better results than client-side PDF generation.
    """
    # WeasyPrint está disponível - testamos anteriormente
    # Vamos assumir que está funcionando e prosseguir
    
    # Get existing deep scrape results
    host_url, full_path, query_dict = util.split_url(request.url)
    
    if result_id:
        r_id = result_id
    else:
        # Try to extract from referrer or use query parameters
        r_id = query_dict.get('url')
        if r_id:
            r_id = redis_cache.make_key(f"/api/deep-scrape?url={r_id}")
        else:
            return {"error": "result_id ou url é obrigatório.", "success": False}
    
    result_data = redis_cache.load_result(key=r_id)
    if not result_data:
        return {"error": f"Resultados não encontrados para ID: {r_id}. Execute o deep scraping primeiro.", "success": False}
    
    try:
        # Generate consolidated HTML
        html_content = generate_consolidated_html(result_data)
        
        # Generate filename
        domain = result_data.get('domain', 'unknown')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"deep_scrape_{domain}_{timestamp}.pdf"
        
        # Ensure output directory exists
        output_dir = Path("static/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        # Generate PDF
        base_url = result_data.get('base_url', 'https://example.com')
        success = generate_pdf_from_scraped_html(html_content, base_url, str(output_path))
        
        if success:
            download_url = f"{host_url}/static/output/{filename}"
            return {
                "success": True,
                "download_url": download_url,
                "filename": filename,
                "message": "PDF gerado com sucesso usando WeasyPrint"
            }
        else:
            return {"error": "Falha na geração do PDF", "success": False}
            
    except Exception as e:
        logging.error(f"Erro ao gerar PDF: {e}")
        return {"error": f"Erro interno: {str(e)}", "success": False}


@router.get('/docx', summary='Generate high-quality DOCX from deep scrape results using Pandoc')
async def deep_scrape_docx(
    request: Request,
    _: AuthRequired,
    result_id: Annotated[
        str | None,
        Query(
            alias='result_id',
            description='Result ID from previous deep scrape operation',
        ),
    ] = None,
) -> dict:
    """
    Generate a high-quality DOCX document from deep scrape results using Pandoc.
    This produces much better results than client-side DOCX generation.
    """
    # Get existing deep scrape results
    host_url, full_path, query_dict = util.split_url(request.url)
    
    if result_id:
        r_id = result_id
    else:
        # Try to extract from referrer or use query parameters
        r_id = query_dict.get('url')
        if r_id:
            r_id = redis_cache.make_key(f"/api/deep-scrape?url={r_id}")
        else:
            return {"error": "result_id ou url é obrigatório.", "success": False}
    
    result_data = redis_cache.load_result(key=r_id)
    if not result_data:
        return {"error": f"Resultados não encontrados para ID: {r_id}. Execute o deep scraping primeiro.", "success": False}
    
    try:
        # Generate consolidated HTML
        html_content = generate_consolidated_html(result_data)
        
        # Generate filename
        domain = result_data.get('domain', 'unknown')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"deep_scrape_{domain}_{timestamp}.docx"
        
        # Ensure output directory exists
        output_dir = Path("static/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        # Generate DOCX
        success = generate_docx_from_scraped_html(html_content, str(output_path))
        
        if success:
            download_url = f"{host_url}/static/output/{filename}"
            return {
                "success": True,
                "download_url": download_url,
                "filename": filename,
                "message": "DOCX gerado com sucesso usando Pandoc"
            }
        else:
            return {"error": "Falha na geração do DOCX", "success": False}
            
    except Exception as e:
        logging.error(f"Erro ao gerar DOCX: {e}")
        return {"error": f"Erro interno: {str(e)}", "success": False}


@router.get('/markdown', summary='Get deep scrape results as consolidated Markdown')
async def deep_scrape_markdown(
    request: Request,
    url: Annotated[URLParam, Depends()],
    params: Annotated[CommonQueryParams, Depends()],
    browser_params: Annotated[BrowserQueryParams, Depends()],
    proxy_params: Annotated[ProxyQueryParams, Depends()],
    readability_params: Annotated[ReadabilityQueryParams, Depends()],
    deep_scrape_params: Annotated[DeepScrapeQueryParams, Depends()],
    _: AuthRequired,
) -> dict:
    """
    Deep scrape a website and return consolidated Markdown content.<br><br>
    This endpoint returns a single Markdown document containing all scraped pages
    organized by levels with table of contents and proper formatting.
    """
    # Get the regular deep scrape result
    result = await deep_scrape(
        request, url, params, browser_params, proxy_params, 
        readability_params, deep_scrape_params, _
    )
    
    # Generate consolidated markdown
    markdown_content = generate_consolidated_markdown(result)
    
    return {
        'id': result['id'],
        'base_url': result['base_url'],
        'domain': result['domain'],
        'date': result['date'],
        'total_pages': result['total_pages'],
        'markdown': markdown_content,
        'resultUri': result['resultUri'],
        'screenshotUri': result.get('screenshotUri')
    }


def _is_valid_url(
    link_url: str, 
    current_url: str, 
    base_domain: str, 
    params: DeepScrapeQueryParams,
    visited_urls: Set[str]
) -> bool:
    """Check if a URL should be included in deep scraping"""
    try:
        # Convert to absolute URL
        absolute_url = urljoin(current_url, link_url)
        
        # Skip if already visited
        if absolute_url in visited_urls:
            return False
        
        # Parse URL
        parsed = urlparse(absolute_url)
        
        # Skip non-HTTP URLs
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check domain restriction
        if params.same_domain_only:
            url_domain = tldextract.extract(absolute_url).registered_domain
            if url_domain != base_domain:
                return False
        
        # Check exclude patterns
        for pattern in params.exclude_patterns:
            if pattern in absolute_url:
                return False
        
        # Skip common non-content URLs
        skip_patterns = [
            '/login', '/logout', '/register', '/signup', '/admin',
            '.pdf', '.doc', '.docx', '.zip', '.exe', '.dmg',
            'mailto:', 'tel:', 'javascript:', '#',
            '/feed', '/rss', '/api/', '/ajax/'
        ]
        
        for skip in skip_patterns:
            if skip in absolute_url.lower():
                return False
        
        return True
        
    except Exception:
        return False


class AsyncDeepScrapeRequest(BaseModel):
    url: str
    depth: int = 3
    max_urls_per_level: int = 10
    same_domain_only: bool = True
    delay_between_requests: float = 1.0
    exclude_patterns: List[str] = []
    # Additional optional parameters
    cache: bool = True
    screenshot: bool = False
    proxy: str = None
    user_agent: str = None
    timeout: int = 30
    wait_for: str = None
    wait_for_timeout: int = 10
    block_resources: List[str] = []
    extra_headers: dict = {}
    cookies: dict = {}
    viewport_width: int = 1280
    viewport_height: int = 720
    readability: bool = True
    include_raw_html: bool = False
    include_screenshot: bool = False


@router.post('/async', summary='Enfileira deep scraping assíncrono via Redis Queue')
async def deep_scrape_async(body: AsyncDeepScrapeRequest) -> dict:
    """
    Enfileira um job de deep scraping para processamento assíncrono.
    Retorna um job_id para consulta posterior do status/resultados.
    Se já houver resultado no cache, retorna imediatamente.
    """
    # Gerar chave normalizada para a URL
    r_id = redis_cache.make_key(body.url)
    logging.info(f"[deep_scrape_async] Chave de cache gerada: {r_id}")
    cached = redis_cache.load_result(key=r_id)
    if cached:
        logging.info(f"[deep_scrape_async] Cache HIT para chave: {r_id}")
        return {
            'success': True,
            'from_cache': True,
            'result_id': r_id,
            'resultUri': f'/result/{r_id}',
            'message': 'Resultado servido do cache.'
        }
    logging.info(f"[deep_scrape_async] Cache MISS para chave: {r_id}. Enfileirando novo job.")
    
    # Converter request body para o formato esperado pelo worker
    browser_params = {}
    if body.user_agent:
        browser_params['user_agent'] = body.user_agent
    if body.timeout != 30:
        browser_params['timeout'] = body.timeout * 1000  # Converter para milliseconds
    if body.viewport_width != 1280:
        browser_params['viewport_width'] = body.viewport_width
    if body.viewport_height != 720:
        browser_params['viewport_height'] = body.viewport_height
    
    proxy_params = {}
    if body.proxy:
        proxy_params['proxy_server'] = body.proxy
    
    job_data = {
        'url': body.url,
        'params': {
            'cache': body.cache,
            'screenshot': body.screenshot,
        },
        'browser_params': browser_params,
        'proxy_params': proxy_params,
        'readability_params': {},
        'deep_scrape_params': {
            'depth': body.depth,
            'max_urls_per_level': body.max_urls_per_level,
            'same_domain_only': body.same_domain_only,
            'delay_between_requests': body.delay_between_requests,
            'exclude_patterns': body.exclude_patterns,
        },
        'request_headers': {},
    }
    job_id = redis_queue.enqueue_job(job_data)
    logging.info(f"[deep_scrape_async] Job enfileirado com job_id: {job_id} para chave: {r_id}")
    host_url = "http://localhost:3000"  # Temporary hardcode for testing
    return {
        'success': True,
        'job_id': job_id,
        'status_url': f'{host_url}/api/deep-scrape/status/{job_id}',
        'message': 'Job enfileirado com sucesso. Consulte o status pelo job_id.'
    }


@router.get('/status/{job_id}', summary='Consulta status de job assíncrono de deep scraping')
async def deep_scrape_status(job_id: str, _: AuthRequired) -> dict:
    """
    Consulta o status de um job de deep scraping assíncrono.
    Retorna status, erro, timestamps e result_id (se pronto).
    """
    job = redis_queue.get_job_status(job_id)
    if not job:
        return {'success': False, 'error': f'Job {job_id} não encontrado.'}
    return {
        'success': True,
        'job_id': job_id,
        'status': job['status'],
        'created_at': job.get('created_at'),
        'updated_at': job.get('updated_at'),
        'error': job.get('error'),
        'result_id': job.get('result_id'),
    }


@router.get('/progress/{job_id}', summary='Consulta progresso granular de job assíncrono')
async def deep_scrape_progress(job_id: str, _: AuthRequired) -> dict:
    """
    Consulta o progresso detalhado de um job de deep scraping assíncrono.
    Retorna progresso granular (nível, página, percent, etc).
    """
    progress = redis_queue.get_job_progress(job_id)
    if progress is None:
        return {'success': False, 'error': f'Progresso não encontrado para job {job_id}.'}
    return {'success': True, 'job_id': job_id, 'progress': progress}


# === MANUAL GENERATOR ENDPOINTS ===

class ManualGenerationRequest(BaseModel):
    """Parâmetros para geração de manual"""
    result_id: str
    format_type: str = 'html'  # html, markdown, pdf, docx
    style: str = 'professional'  # professional, technical, minimal
    translate: bool = False
    source_language: str = 'auto'
    target_language: str = 'pt'
    translation_provider: str = 'libre'  # openai, google, deepl, libre
    translation_api_key: str | None = None
    manual_type: str = 'general'  # general, technical, tutorial
    include_toc: bool = True
    include_metadata: bool = True
    prepare_for_rag: bool = False  # Nova flag para preparar conteúdo para RAG


@router.post('/manual', summary='Gera manual estruturado a partir de deep scraping')
async def generate_manual(
    request: Request,
    body: ManualGenerationRequest,
    _: AuthRequired = None
) -> dict:
    """
    Gera manual profissional estruturado a partir de dados de deep scraping.
    
    Este endpoint transforma dados de scraping em um manual organizado com:
    - Análise semântica do conteúdo
    - Estruturação hierárquica inteligente
    - Formatação profissional
    - Opções de tradução contextual
    """
    try:
        logging.info(f"Iniciando geração de manual para result_id: {body.result_id}")
        
        # Recuperar dados do deep scraping
        # Tentar primeiro no Redis cache (usado pelo worker assíncrono)
        scraped_data = redis_cache.load_result(body.result_id)
        if not scraped_data:
            # Fallback para cache de arquivos (scraping síncrono)
            scraped_data = cache.load_result(body.result_id)
            if not scraped_data:
                return {"error": "Dados de scraping não encontrados", "result_id": body.result_id}
        
        # Importar módulos do gerador de manuais
        try:
            from manual_generator import ContentAnalyzer, StructureDetector, ManualFormatter, Translator
            from manual_generator.translator import TranslationConfig, TranslationProvider
            logging.info("Manual generator modules imported successfully")
        except ImportError as e:
            logging.error(f"Failed to import manual generator modules: {e}")
            return {"error": f"Erro na importação dos módulos: {str(e)}"}
        
        # Fase 1: Análise de conteúdo
        try:
            content_analyzer = ContentAnalyzer()
            analyzed_structure = content_analyzer.analyze_scraped_data(scraped_data)
            logging.info("Content analysis completed successfully")
        except Exception as e:
            logging.error(f"Error in content analysis: {e}")
            return {"error": f"Erro na análise de conteúdo: {str(e)}"}
        
        # Fase 2: Análise de estrutura
        try:
            structure_detector = StructureDetector()
            structure_analysis = structure_detector.analyze_structure(analyzed_structure)
            logging.info(f"Structure analysis completed with quality score: {structure_analysis.quality_score}")
        except Exception as e:
            logging.error(f"Error in structure analysis: {e}")
            return {"error": f"Erro na análise de estrutura: {str(e)}"}
        
        # Usar estrutura reorganizada se a qualidade for boa
        if structure_analysis.quality_score > 60:
            # Atualizar estrutura com reorganização sugerida
            analyzed_structure['chapters'] = structure_analysis.suggested_reorganization
            logging.info(f"Aplicando reorganização sugerida (qualidade: {structure_analysis.quality_score:.1f})")
        
        # Fase 3: Tradução (se solicitada)
        if body.translate and body.target_language != body.source_language:
            translator = Translator()
            
            # Configurar tradução
            provider_map = {
                'openai': TranslationProvider.OPENAI,
                'google': TranslationProvider.GOOGLE,
                'deepl': TranslationProvider.DEEPL,
                'libre': TranslationProvider.LIBRE
            }
            
            translation_config = TranslationConfig(
                provider=provider_map.get(body.translation_provider, TranslationProvider.LIBRE),
                source_language=body.source_language,
                target_language=body.target_language,
                api_key=body.translation_api_key,
                technical_context=f"Manual técnico sobre {analyzed_structure['metadata'].get('domain', '')}"
            )
            
            analyzed_structure = translator.translate_manual_structure(analyzed_structure, translation_config)
            logging.info(f"Tradução aplicada: {body.source_language} -> {body.target_language}")
        
        # Fase 4: Formatação final
        formatter = ManualFormatter()
        
        format_options = {
            'include_toc': body.include_toc,
            'include_metadata': body.include_metadata,
            'manual_type': body.manual_type,
            'prepare_for_rag': body.prepare_for_rag
        }
        
        try:
            logging.info(f"Iniciando formatação em {body.format_type} com estilo {body.style}")
            formatted_manual = formatter.format_manual(
                analyzed_structure, 
                body.format_type, 
                body.style, 
                format_options
            )
            logging.info(f"Formatação concluída. Formato: {formatted_manual.get('format', 'N/A')}")
            logging.info(f"Tamanho do conteúdo: {len(str(formatted_manual.get('content', '')))}")
        except RuntimeError as e:
            logging.error(f"RuntimeError na formatação: {e}")
            if "WeasyPrint não está disponível" in str(e):
                return {"error": "PDF não disponível. WeasyPrint não está instalado corretamente no sistema. Tente usar HTML ou Markdown."}
            elif "Erro no Pandoc" in str(e):
                return {"error": "DOCX não disponível. Pandoc não está instalado corretamente no sistema. Tente usar HTML ou Markdown."}
            else:
                raise
        except Exception as e:
            logging.error(f"Erro inesperado na formatação: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return {"error": f"Erro na formatação: {str(e)}"}
        
        # Adicionar informações da análise de estrutura
        formatted_manual['structure_analysis'] = {
            'pattern': structure_analysis.pattern.value,
            'quality_score': structure_analysis.quality_score,
            'recommendations': structure_analysis.recommendations
        }
        
        # Para PDF/DOCX, remover o campo 'content' ANTES de salvar no cache
        if body.format_type in ['pdf', 'docx'] and 'content' in formatted_manual:
            del formatted_manual['content']

        # Salvar resultado no cache
        manual_id = f"manual_{body.result_id}_{body.format_type}"
        redis_cache.store_result(manual_id, formatted_manual)  # Usar Redis cache para consistência
        
        # Preparar resposta
        response = {
            'manual_id': manual_id,
            'title': formatted_manual['title'],
            'format': formatted_manual['format'],
            'style': formatted_manual['style'],
            'generated_at': formatted_manual['generated_at'],
            'structure_analysis': formatted_manual['structure_analysis'],
            'metadata': {
                'total_words': formatted_manual['metadata'].get('total_words', 0),
                'estimated_reading_time': formatted_manual['metadata'].get('estimated_reading_time', 0),
                'content_types_found': formatted_manual['metadata'].get('content_types_found', []),
                'translated': body.translate
            },
            'download_url': f"/api/deep-scrape/manual/{manual_id}/download"
        }
        
        # Para formatos de texto, incluir conteúdo na resposta
        if body.format_type in ['html', 'markdown']:
            response['content'] = formatted_manual['content']
        else:
            # Para PDF/DOCX, não salvar o campo 'content' (bytes) no cache nem retornar no JSON
            if 'content' in formatted_manual:
                del formatted_manual['content']
        
        logging.info(f"Manual gerado com sucesso: {manual_id}")
        return response
        
    except Exception as e:
        logging.error(f"Erro na geração de manual: {e}")
        return {"error": f"Erro na geração do manual: {str(e)}"}


@router.get('/manual/{manual_id}/download', summary='Download de manual gerado')
async def download_manual(
    manual_id: str,
    _: AuthRequired = None
):
    """
    Faz download de manual gerado previamente.
    """
    try:
        # Recuperar manual do cache
        manual_data = redis_cache.load_result(manual_id)
        if not manual_data:
            return {"error": "Manual não encontrado"}
        
        format_type = manual_data.get('format', 'html')
        title = manual_data.get('title', 'Manual').replace(' ', '_')
        
        # Preparar resposta baseada no formato
        if format_type == 'html':
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content=manual_data['content'],
                headers={"Content-Disposition": f"attachment; filename={title}.html"}
            )
        
        elif format_type == 'markdown':
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(
                content=manual_data['content'],
                headers={"Content-Disposition": f"attachment; filename={title}.md"}
            )
        
        elif format_type in ['pdf', 'docx']:
            from fastapi.responses import FileResponse
            file_path = manual_data.get('file_path')
            if file_path and os.path.exists(file_path):
                extension = 'pdf' if format_type == 'pdf' else 'docx'
                return FileResponse(
                    path=file_path,
                    filename=f"{title}.{extension}",
                    media_type=f"application/{extension}"
                )
            else:
                return {"error": "Arquivo não encontrado"}
        
        else:
            return {"error": f"Formato não suportado: {format_type}"}
            
    except Exception as e:
        logging.error(f"Erro no download do manual: {e}")
        return {"error": f"Erro no download: {str(e)}"}


@router.get('/manual/preview/{result_id}', summary='Preview da estrutura do manual')
async def preview_manual_structure(
    result_id: str,
    _: AuthRequired = None
) -> dict:
    """
    Gera preview da estrutura do manual sem formatação completa.
    Útil para mostrar ao usuário como ficará organizado antes da geração final.
    """
    try:
        # Recuperar dados do deep scraping
        # Tentar primeiro no Redis cache (usado pelo worker assíncrono)
        scraped_data = redis_cache.load_result(result_id)
        if not scraped_data:
            # Fallback para cache de arquivos (scraping síncrono)
            scraped_data = cache.load_result(result_id)
            if not scraped_data:
                return {"error": "Dados de scraping não encontrados"}
        
        # Importar módulos necessários
        from manual_generator import ContentAnalyzer, StructureDetector
        
        # Análise rápida
        content_analyzer = ContentAnalyzer()
        analyzed_structure = content_analyzer.analyze_scraped_data(scraped_data)
        
        structure_detector = StructureDetector()
        structure_analysis = structure_detector.analyze_structure(analyzed_structure)
        
        # Preparar preview
        preview = {
            'title': analyzed_structure['title'],
            'structure_pattern': structure_analysis.pattern.value,
            'quality_score': structure_analysis.quality_score,
            'recommendations': structure_analysis.recommendations,
            'estimated_reading_time': analyzed_structure['metadata'].get('estimated_reading_time', 0),
            'total_words': analyzed_structure['metadata'].get('total_words', 0),
            'content_types': analyzed_structure['metadata'].get('content_types_found', []),
            'outline': []
        }
        
        # Gerar sumário do manual
        chapter_num = 1
        
        # Introdução
        if analyzed_structure.get('introduction'):
            preview['outline'].append({
                'type': 'introduction',
                'title': 'Introdução',
                'level': 0,
                'content_type': analyzed_structure['introduction'].content_type.value,
                'word_count': analyzed_structure['introduction'].metadata.get('word_count', 0)
            })
        
        # Capítulos
        for chapter in analyzed_structure.get('chapters', []):
            chapter_info = {
                'type': 'chapter',
                'number': chapter_num,
                'title': chapter.title,
                'level': 1,
                'content_type': chapter.content_type.value,
                'word_count': chapter.metadata.get('word_count', 0),
                'subsections': []
            }
            
            # Subseções
            section_num = 1
            for subsection in chapter.subsections:
                subsection_info = {
                    'type': 'section',
                    'number': f"{chapter_num}.{section_num}",
                    'title': subsection.title,
                    'level': 2,
                    'content_type': subsection.content_type.value,
                    'word_count': subsection.metadata.get('word_count', 0)
                }
                chapter_info['subsections'].append(subsection_info)
                section_num += 1
            
            preview['outline'].append(chapter_info)
            chapter_num += 1
        
        # Apêndices
        appendix_letter = 'A'
        for appendix in analyzed_structure.get('appendices', []):
            preview['outline'].append({
                'type': 'appendix',
                'letter': appendix_letter,
                'title': appendix.title,
                'level': 1,
                'content_type': appendix.content_type.value,
                'word_count': appendix.metadata.get('word_count', 0)
            })
            appendix_letter = chr(ord(appendix_letter) + 1)
        
        return preview
        
    except Exception as e:
        logging.error(f"Erro no preview do manual: {e}")
        return {"error": f"Erro no preview: {str(e)}"} 