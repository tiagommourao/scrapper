from internal.util import levenshtein_similarity, normalize_url


def test_levenshtein_similarity():
    assert levenshtein_similarity('hello', 'hello') == 1.0
    assert levenshtein_similarity('hello', 'world') == 0.19999999999999996
    assert levenshtein_similarity('hello', 'hell') == 0.8
    assert levenshtein_similarity('hello', 'helo') == 0.8
    assert levenshtein_similarity('hello', 'buy') == 0.0

def test_normalize_url():
    base = 'https://site.com/page'
    # Remove utm_*
    assert normalize_url(base + '?utm_source=google') == base
    # Remove ref
    assert normalize_url(base + '?ref=twitter') == base
    # Remove session
    assert normalize_url(base + '?session=abc123') == base
    # Remove fragment
    assert normalize_url(base + '#section') == base
    # Remove trailing slash
    assert normalize_url(base + '/') == base
    # Lowercase host
    assert normalize_url('https://SITE.com/page') == base
    # Parâmetros relevantes permanecem
    assert normalize_url(base + '?id=1') == base + '?id=1'
    # Parâmetros mistos
    assert normalize_url(base + '?id=1&utm_source=google&ref=abc') == base + '?id=1'
    # Ordem dos parâmetros não importa
    assert normalize_url(base + '?utm_source=google&id=1') == base + '?id=1'
