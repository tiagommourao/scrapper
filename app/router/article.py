import asyncio
import datetime
from typing import Annotated

import tldextract

from fastapi import APIRouter, Query, Depends
from fastapi.requests import Request
from pydantic import BaseModel
from playwright.async_api import Browser

from internal import util, cache, redis_cache
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


router = APIRouter(prefix='/api/article', tags=['article'])


class Article(BaseModel):
    byline: Annotated[str | None, Query(description='author metadata')]
    content: Annotated[str | None, Query(description='HTML string of processed article content')]
    dir: Annotated[str | None, Query(description='content direction')]
    excerpt: Annotated[str | None, Query(description='article description, or short excerpt from the content')]
    id: Annotated[str, Query(description='unique result ID')]
    url: Annotated[str, Query(description='page URL after redirects, may not match the query URL')]
    domain: Annotated[str, Query(description="page's registered domain")]
    lang: Annotated[str | None, Query(description='content language')]
    length: Annotated[int | None, Query(description='length of extracted article, in characters')]
    date: Annotated[str, Query(description='date of extracted article in ISO 8601 format')]
    query: Annotated[dict, Query(description='request parameters')]
    meta: Annotated[dict, Query(description='social meta tags (open graph, twitter)')]
    resultUri: Annotated[str, Query(description='URL of the current result, the data here is always taken from cache')]
    fullContent: Annotated[str | None, Query(description='full HTML contents of the page')] = None
    screenshotUri: Annotated[str | None, Query(description='URL of the screenshot of the page')] = None
    siteName: Annotated[str | None, Query(description='name of the site')]
    textContent: Annotated[str | None, Query(description='text content of the article, with all the HTML tags removed')]
    title: Annotated[str | None, Query(description='article title')]
    publishedTime: Annotated[str | None, Query(description='article publication time')]


@router.get('', summary='Parse article from the given URL', response_model=Article)
async def parse_article(
    request: Request,
    url: Annotated[URLParam, Depends()],
    params: Annotated[CommonQueryParams, Depends()],
    browser_params: Annotated[BrowserQueryParams, Depends()],
    proxy_params: Annotated[ProxyQueryParams, Depends()],
    readability_params: Annotated[ReadabilityQueryParams, Depends()],
    _: AuthRequired,
) -> dict:
    """
    Parse article from the given URL.<br><br>
    The page from the URL should contain the text of the article that needs to be extracted.
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

    # create a new browser context
    async with semaphore:
        async with new_context(browser, browser_params, proxy_params) as context:
            page = await context.new_page()
            await page_processing(
                page=page,
                url=url.url,
                params=params,
                browser_params=browser_params,
                init_scripts=[READABILITY_SCRIPT],
            )
            page_content = await page.content()
            screenshot = await get_screenshot(page) if params.screenshot else None
            page_url = page.url

            # evaluating JavaScript: parse DOM and extract article content
            parser_args = {
                # Readability options:
                'maxElemsToParse': readability_params.max_elems_to_parse,
                'nbTopCandidates': readability_params.nb_top_candidates,
                'charThreshold': readability_params.char_threshold,
                # TODO: add linkDensityModifier option
            }
            with open(PARSER_SCRIPTS_DIR / 'article.js', encoding='utf-8') as f:
                article = await page.evaluate(f.read() % parser_args)

    if article is None:
        raise ArticleParsingError(page_url, "The page doesn't contain any articles.")

    # parser error: article is not extracted, result has 'err' field
    if 'err' in article:
        raise ArticleParsingError(page_url, article['err'])

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()  # ISO 8601 format
    domain = tldextract.extract(page_url).registered_domain

    # set common fields
    article['id'] = r_id
    article['url'] = page_url
    article['domain'] = domain
    article['date'] = now
    article['resultUri'] = f'{host_url}/result/{r_id}'
    article['query'] = query_dict
    article['meta'] = util.social_meta_tags(page_content)

    if params.full_content:
        article['fullContent'] = page_content
    if params.screenshot:
        article['screenshotUri'] = f'{host_url}/screenshot/{r_id}'

    if 'title' in article and 'content' in article:
        article['content'] = util.improve_content(
            title=article['title'],
            content=article['content'],
        )

    if 'textContent' in article:
        article['textContent'] = util.improve_text_content(article['textContent'])
        article['length'] = len(article['textContent']) - article['textContent'].count('\n')

    # save result to disk
    # Save result to cache (Redis with file fallback)
    redis_cache.store_result(key=r_id, data=article)
    
    # Save screenshot separately (still using file system for now)
    if screenshot:
        cache.dump_screenshot(key=r_id, screenshot=screenshot)
    return article
