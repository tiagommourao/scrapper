from collections.abc import MutableMapping
from urllib.parse import parse_qs, urlparse, urlunparse, parse_qsl, urlencode

from bs4 import BeautifulSoup
from starlette.datastructures import URL

import re
import html


TITLE_MAX_DISTANCE = 350
ACCEPTABLE_LINK_TEXT_LEN = 40


def improve_content(title: str, content: str) -> str:
    tree = BeautifulSoup(content, 'html.parser')

    # 1. remove all p and div tags that contain one word or less (or only digits),
    # and not contain any images (or headers)
    for el in tree.find_all(['p', 'div']):
        # skip if the element has any images, headers, code blocks, lists, tables, forms, etc.
        if el.find([
            'img',
            'picture',
            'svg',
            'canvas',
            'video',
            'audio',
            'iframe',
            'embed',
            'object',
            'param',
            'source',
            'h1',
            'h2',
            'h3',
            'h4',
            'h5',
            'h6',
            'pre',
            'code',
            'blockquote',
            'dl',
            'ol',
            'ul',
            'table',
            'form',
        ]):
            continue
        text = el.get_text(strip=True)
        # remove the element if it contains one word or less (or only digits)
        words = text.split()
        if len(words) <= 1 or (''.join(words)).isnumeric():
            el.decompose()

    # 2. move the first tag h1 (or h2) to the top of the tree
    title_distance = 0

    for el in tree.find_all(string=True):
        if el.parent.name in ('h1', 'h2', 'h3'):
            text = el.parent.get_text(strip=True)
            # stop if the header is similar to the title
            min_len = min(len(text), len(title))
            # remove all non-alphabetic characters and convert to lowercase
            # noinspection PyTypeChecker
            str1 = ''.join(filter(str.isalpha, text[:min_len])).lower()
            # noinspection PyTypeChecker
            str2 = ''.join(filter(str.isalpha, title[:min_len])).lower()
            if str1 and str2 and levenshtein_similarity(str1, str2) > 0.9:
                title = text
                el.parent.decompose()  # 'real' move will be below, at 3.1 or 3.2
                break

        # stop if distance is too big
        title_distance += len(el.text)
        if title_distance > TITLE_MAX_DISTANCE:
            # will be used article['title'] as title
            break

    # 3.1 check if article tag already exists, and then insert the title into it
    for el in tree.find_all():
        if el.name == 'article':
            el.insert(0, BeautifulSoup(f'<h1>{title}</h1>', 'html.parser'))
            return str(tree)

    # 3.2 if not, create a new article tag and insert the title into it
    content = str(tree)
    return f'<article><h1>{title}</h1>{content}</article>'


def improve_link(link: MutableMapping) -> MutableMapping:
    lines = link['text'].splitlines()
    text = ''
    # find the longest line
    for line in lines:
        if len(line) > len(text):
            text = line
        # stop if the line is long enough
        if len(text) > ACCEPTABLE_LINK_TEXT_LEN:
            break

    link['text'] = text
    return link


def social_meta_tags(full_page_content: str) -> dict:
    og = {}  # open graph
    twitter = {}
    tree = BeautifulSoup(full_page_content, 'html.parser')
    for el in tree.find_all('meta'):
        attrs = el.attrs
        # open Graph protocol
        if 'property' in attrs and attrs['property'].startswith('og:'):
            key = attrs['property'][3:]  # len('og:') == 3
            if key and 'content' in attrs:
                og[key] = attrs['content']

        # twitter protocol
        if 'name' in attrs and attrs['name'].startswith('twitter:'):
            key = attrs['name'][8:]  # len('twitter:') == 8
            if key and 'content' in attrs:
                twitter[key] = attrs['content']

    res = {key: props for key, props in (('og', og), ('twitter', twitter)) if props}
    return res


def levenshtein_similarity(str1: str, str2: str) -> float:
    # create a matrix to hold the distances
    d = [[0] * (len(str2) + 1) for _ in range(len(str1) + 1)]

    # initialize the first row and column of the matrix
    for i in range(len(str1) + 1):
        d[i][0] = i
    for j in range(len(str2) + 1):
        d[0][j] = j

    # fill in the rest of the matrix
    for i in range(1, len(str1) + 1):
        for j in range(1, len(str2) + 1):
            if str1[i - 1] == str2[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1]) + 1

    # return normalized distance
    return 1 - d[-1][-1] / max(len(str1), len(str2))


def improve_text_content(text: str) -> str:
    s = '\n'.join(filter(None, map(str.strip, text.splitlines())))
    return s


def split_url(url: URL) -> tuple[str, str, dict]:
    """
    Split URL into parts. Return host_url, full_path, query_dict.
    :param url: Starlette URL object
    :return:
        host_url - just the host with scheme
        full_path - just the path with query
        query_dict - query params as a dict
    """
    # just the host with scheme
    host_url = URL(scheme=url.scheme, netloc=url.netloc)

    # just the path with query
    full_path = URL(path=url.path, query=url.query)

    # query params as a dict
    query_dict = parse_qs(qs=url.query, keep_blank_values=True)
    return host_url, full_path, query_dict


def normalize_url(url: str, ignore_params=None) -> str:
    """
    Normaliza uma URL para fins de cache inteligente:
    - Remove parâmetros irrelevantes (utm_*, ref, session, etc)
    - Remove anchors/fragments
    - Normaliza trailing slashes
    - Lowercase no host
    """
    if ignore_params is None:
        ignore_params = [
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'ref', 'referrer', 'session', 'fbclid', 'gclid', 'yclid', 'mc_cid', 'mc_eid',
        ]
    try:
        parsed = urlparse(url)
        # Lowercase no host
        netloc = parsed.netloc.lower()
        # Remove fragment
        fragment = ''
        # Remove parâmetros irrelevantes
        query = urlencode([
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k not in ignore_params and not k.startswith('utm_')
        ])
        # Normaliza trailing slash
        path = parsed.path or '/'
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        # Reconstrói a URL
        normalized = urlunparse((
            parsed.scheme,
            netloc,
            path,
            '',  # params
            query,
            fragment
        ))
        return normalized
    except Exception:
        return url  # fallback para a original se falhar


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to Markdown format"""
    if not html_content:
        return ""
    # Remove script and style tags
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    # Convert HTML tags to Markdown
    conversions = [
        (r'<h1[^>]*>(.*?)</h1>', r'# \1\n'),
        (r'<h2[^>]*>(.*?)</h2>', r'## \1\n'),
        (r'<h3[^>]*>(.*?)</h3>', r'### \1\n'),
        (r'<h4[^>]*>(.*?)</h4>', r'#### \1\n'),
        (r'<h5[^>]*>(.*?)</h5>', r'##### \1\n'),
        (r'<h6[^>]*>(.*?)</h6>', r'###### \1\n'),
        (r'<p[^>]*>(.*?)</p>', r'\1\n\n'),
        (r'<br[^>]*/?>', r'\n'),
        (r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)'),
        (r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>', r'![\2](\1)'),
        (r'<img[^>]*alt="([^"]*)"[^>]*src="([^"]*)"[^>]*/?>', r'![\1](\2)'),
        (r'<img[^>]*src="([^"]*)"[^>]*/?>', r'![](\1)'),
        (r'<strong[^>]*>(.*?)</strong>', r'**\1**'),
        (r'<b[^>]*>(.*?)</b>', r'**\1**'),
        (r'<em[^>]*>(.*?)</em>', r'*\1*'),
        (r'<i[^>]*>(.*?)</i>', r'*\1*'),
        (r'<code[^>]*>(.*?)</code>', r'`\1`'),
        (r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```\n'),
        (r'<ul[^>]*>(.*?)</ul>', lambda m: _convert_list(m.group(1), ordered=False)),
        (r'<ol[^>]*>(.*?)</ol>', lambda m: _convert_list(m.group(1), ordered=True)),
        (r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1\n'),
        (r'<div[^>]*>(.*?)</div>', r'\1\n'),
        (r'<span[^>]*>(.*?)</span>', r'\1'),
        (r'<[^>]+>', ''),
    ]
    for pattern, replacement in conversions:
        if callable(replacement):
            html_content = re.sub(pattern, replacement, html_content, flags=re.DOTALL | re.IGNORECASE)
        else:
            html_content = re.sub(pattern, replacement, html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = html.unescape(html_content)
    html_content = re.sub(r'\n\s*\n\s*\n', '\n\n', html_content)
    html_content = re.sub(r'[ \t]+', ' ', html_content)
    html_content = html_content.strip()
    return html_content


def _convert_list(list_content: str, ordered: bool = False) -> str:
    """Convert HTML list items to Markdown"""
    items = re.findall(r'<li[^>]*>(.*?)</li>', list_content, flags=re.DOTALL | re.IGNORECASE)
    result = []
    for i, item in enumerate(items):
        item = re.sub(r'<[^>]+>', '', item).strip()
        if ordered:
            result.append(f"{i+1}. {item}")
        else:
            result.append(f"- {item}")
    return '\n'.join(result) + '\n\n'
