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

# Importações condicionais para WeasyPrint (pode não estar disponível em todos os ambientes)
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("WeasyPrint não disponível. PDFs serão gerados usando método alternativo.")

from fastapi import APIRouter, Query, Depends
from fastapi.requests import Request
from pydantic import BaseModel
from playwright.async_api import Browser

from internal import util, cache
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
    if not WEASYPRINT_AVAILABLE:
        logging.error("WeasyPrint não está disponível. Não é possível gerar PDF.")
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
            self.exclude_patterns = [pattern.strip() for pattern in exclude_patterns.split(',') if pattern.strip()]


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
    _: AuthRequired,
) -> dict:
    """
    Deep scrape a website recursively with configurable depth.<br><br>
    This endpoint will start from the base URL, extract its content and links, 
    then recursively scrape linked pages up to the specified depth.
    """
    # split URL into parts: host with scheme, path with query, query params as a dict
    host_url, full_path, query_dict = util.split_url(request.url)

    # get cache data if exists
    r_id = cache.make_key(full_path)  # unique result ID
    if params.cache:
        data = cache.load_result(key=r_id)
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
                        
                        # Respectful delay between requests
                        if deep_scrape_params.delay_between_requests > 0:
                            await asyncio.sleep(deep_scrape_params.delay_between_requests)
                            
                except Exception as e:
                    logger.error(f"Error scraping {current_url}: {str(e)}")
                    continue
            
            if level_data['pages']:
                level_results.append(level_data)
            
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

    # Save result to disk
    cache.dump_result(result, key=r_id, screenshot=base_screenshot)
    
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
    url: Annotated[URLParam, Depends()],
    params: Annotated[CommonQueryParams, Depends()],
    browser_params: Annotated[BrowserQueryParams, Depends()],
    proxy_params: Annotated[ProxyQueryParams, Depends()],
    readability_params: Annotated[ReadabilityQueryParams, Depends()],
    deep_scrape_params: Annotated[DeepScrapeQueryParams, Depends()],
    _: AuthRequired,
) -> dict:
    """
    Generate a high-quality PDF document from deep scrape results using WeasyPrint.
    This produces much better results than client-side PDF generation.
    """
    if not WEASYPRINT_AVAILABLE:
        return {"error": "WeasyPrint não está disponível neste servidor.", "success": False}
    
    # Get existing deep scrape results
    host_url, full_path, query_dict = util.split_url(request.url)
    r_id = cache.make_key(full_path.replace('/pdf', ''))  # Remove /pdf suffix
    
    result_data = cache.load_result(key=r_id)
    if not result_data:
        return {"error": "Resultados não encontrados. Execute o deep scraping primeiro.", "success": False}
    
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
        base_url = result_data.get('base_url', url.url)
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
    url: Annotated[URLParam, Depends()],
    params: Annotated[CommonQueryParams, Depends()],
    browser_params: Annotated[BrowserQueryParams, Depends()],
    proxy_params: Annotated[ProxyQueryParams, Depends()],
    readability_params: Annotated[ReadabilityQueryParams, Depends()],
    deep_scrape_params: Annotated[DeepScrapeQueryParams, Depends()],
    _: AuthRequired,
) -> dict:
    """
    Generate a high-quality DOCX document from deep scrape results using Pandoc.
    This produces much better results than client-side DOCX generation.
    """
    # Get existing deep scrape results
    host_url, full_path, query_dict = util.split_url(request.url)
    r_id = cache.make_key(full_path.replace('/docx', ''))  # Remove /docx suffix
    
    result_data = cache.load_result(key=r_id)
    if not result_data:
        return {"error": "Resultados não encontrados. Execute o deep scraping primeiro.", "success": False}
    
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