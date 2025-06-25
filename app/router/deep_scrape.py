import asyncio
import datetime
from typing import Annotated, List, Dict, Set
from collections import deque
from urllib.parse import urljoin, urlparse
import logging
import re
import html

import tldextract

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
                        if current_level < deep_scrape_params.depth - 1:
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