# -*- coding: utf-8 -*-
"""
OFFLINE UNIT TESTS FOR domaceserije.py
Verifies pure helper logic, parser functions, edge cases, and network error handling
without making external HTTP calls.
"""

import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import domaceserije

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def test_normalize_hostname():
    print("Executing test_normalize_hostname...")
    require(domaceserije.normalize_hostname("") == "", "Empty hostname should return empty string")
    require(domaceserije.normalize_hostname("https://www.vidmoly.biz:8080/embed") == "vidmoly.biz", "Port and www should be stripped")
    require(domaceserije.normalize_hostname("http://bysebuho.com/e/123") == "bysebuho.com", "Standard URL hostname extraction failed")

def test_make_full_url():
    print("Executing test_make_full_url...")
    require(domaceserije.make_full_url("") == "", "Empty path should return empty string")
    require(domaceserije.make_full_url("//domain.com/path") == "https://domain.com/path", "Protocol relative URL failed")
    require(domaceserije.make_full_url("/zanr-film/svi") == domaceserije.URL_MAIN + "/zanr-film/svi", "Relative URL join failed")
    require(domaceserije.make_full_url("sub\\/path") == domaceserije.URL_MAIN + "/sub/path", "Escaped slash handling failed")

def test_add_resolver_referer():
    print("Executing test_add_resolver_referer...")
    ref = "https://domaceserije.net/player"
    
    # Non-referer hoster
    url1 = domaceserije.add_resolver_referer("https://vidmoly.biz/embed.html", ref, "VidMoly")
    require(url1 == "https://vidmoly.biz/embed.html", "VidMoly should not append referer")

    # Flemoon (REFERER_HOSTERS) - bysebuho normalized to filemoon.sx
    url2 = domaceserije.add_resolver_referer("https://bysebuho.com/e/123", ref, "Flemoon")
    require(url2 == f"https://filemoon.sx/e/123$${ref}", "Flemoon should append $$referer and normalize domain")

    # Vidhide (REFERER_HOSTERS) - morencius normalized to vidhidepro.com
    url3 = domaceserije.add_resolver_referer("https://morencius.com/embed/123", ref, "VIDHIDE")
    require(url3 == f"https://vidhidepro.com/embed/123$${ref}", "Vidhide should append $$referer and normalize domain")

    # Already contains $$referer -> Idempotent
    already = f"https://filemoon.sx/e/123$${ref}"
    url4 = domaceserije.add_resolver_referer(already, ref, "VIDHIDE")
    require(url4 == already, "Already appended referer should be left intact")


def test_extract_year():
    print("Executing test_extract_year...")
    require(domaceserije.extract_year("Poznati film iz (2024) godine") == 2024, "Year 2024 extraction failed")
    require(domaceserije.extract_year("<p>Serija 1998 opis</p>") == 1998, "Year 1998 extraction failed")
    require(domaceserije.extract_year("Nema godine ovde") is None, "None should be returned when no year is present")

def test_clean_card_title():
    print("Executing test_clean_card_title...")
    raw = "Montevideo, Bog te video! <br/> (2010) <br /> <span>Ceo film</span>"
    title = domaceserije.clean_card_title(raw)
    require(title == "Montevideo, Bog te video!", f"Unexpected title: {title}")

    raw_escaped = "Tom &amp; Jerry <br> Sinhronizovano"
    title_escaped = domaceserije.clean_card_title(raw_escaped)
    require(title_escaped == "Tom & Jerry", f"Unexpected title: {title_escaped}")

def test_detect_media_type():
    print("Executing test_detect_media_type...")
    require(domaceserije.detect_media_type("/test", "Senke nad Balkanom (serija)") == 'tvshow', "Explicit (serija) tag failed")
    require(domaceserije.detect_media_type("/test", "Lauš (film)") == 'movie', "Explicit (film) tag failed")
    require(domaceserije.detect_media_type("https://domaceserije.net/domaci-filmovi/glavonja-2026-ceo-film-online", "Glavonja") == 'movie', "URL movie path detection failed")
    require(domaceserije.detect_media_type("https://domaceserije.net/domaca-serija/vukovar", "Vukovar") == 'tvshow', "Fallback to tvshow failed")

def test_determine_view_mode():
    print("Executing test_determine_view_mode...")
    require(domaceserije.determine_view_mode([]) == 'files', "Empty list should return 'files'")
    require(domaceserije.determine_view_mode([{'media_type': 'movie'}]) == 'movies', "All movies should return 'movies'")
    require(domaceserije.determine_view_mode([{'media_type': 'tvshow'}]) == 'tvshows', "All tvshows should return 'tvshows'")
    require(domaceserije.determine_view_mode([{'media_type': 'movie'}, {'media_type': 'tvshow'}]) == 'files', "Mixed types should return 'files'")

def test_episode_sort_key():
    print("Executing test_episode_sort_key...")
    ep1 = ("Sezona 1 Epizoda 2",)
    ep2 = ("Sezona 1 Epizoda 10",)
    require(domaceserije.episode_sort_key(ep1) < domaceserije.episode_sort_key(ep2), "Episode 2 should come before Episode 10")

    ep_simple = ("Epizoda 5",)
    require(domaceserije.episode_sort_key(ep_simple) == (1, 5), "Simple episode parsing failed")

def test_isolate_catalog_html():
    print("Executing test_isolate_catalog_html...")
    require(domaceserije.isolate_catalog_html("") == "", "Empty HTML should return empty string")
    
    html_sidebar = '<div>Sidebar content</div><div id="latestalbum">Main Content</div>'
    isolated = domaceserije.isolate_catalog_html(html_sidebar)
    require('Main Content' in isolated and 'Sidebar content' not in isolated, "Sidebar isolation failed")

def test_parse_catalog_cards_offline():
    print("Executing test_parse_catalog_cards_offline...")
    sample_html = """
    <div id="latestalbum">
        <div class="img__wrap">
            <a href="/domaci-filmovi/test-film-2025-ceo-film-online">
                <img src="/thumbs/test.jpg" />
                <p class="img__description">Test Film <br> (2025)</p>
            </a>
        </div>
    </div>
    """
    cards = domaceserije.parse_catalog_cards(sample_html)
    require(len(cards) == 1, f"Expected 1 card, got {len(cards)}")
    require(cards[0]['title'] == "Test Film", f"Title error: {cards[0]['title']}")
    require(cards[0]['media_type'] == "movie", f"Media type error: {cards[0]['media_type']}")
    require(cards[0]['year'] == 2025, f"Year error: {cards[0]['year']}")

def test_timeout_string_rejection_vs_javascript_settimeout():
    print("Executing test_timeout_string_rejection_vs_javascript_settimeout...")
    
    # Mock requestHandler for offline test
    class MockReq:
        def __init__(self, content):
            self.content = content
            self.cacheTime = 0
        def addHeaderEntry(self, k, v):
            pass
        def request(self):
            return self.content

    original_cReq = domaceserije.cRequestHandler

    try:
        # Case 1: JavaScript contains setTimeout -> MUST NOT BE REJECTED
        js_html = '<html><head><script>setTimeout(function () {}, 1000);</script></head><body>OK</body></html>'
        domaceserije.cRequestHandler = lambda url, **kwargs: MockReq(js_html)
        res1 = domaceserije.request_page("http://dummy")
        require(res1 == js_html, "JavaScript setTimeout was incorrectly rejected as network TIMEOUT error!")

        # Case 2: Response is exact TIMEOUT string -> MUST BE REJECTED (returns "")
        domaceserije.cRequestHandler = lambda url, **kwargs: MockReq("TIMEOUT")
        res2 = domaceserije.request_page("http://dummy")
        require(res2 == "", "Exact 'TIMEOUT' string response was not rejected!")

        # Case 3: Cloudflare error message -> MUST BE REJECTED (returns "")
        domaceserije.cRequestHandler = lambda url, **kwargs: MockReq("Error: Cloudflare-Schutz aktiv")
        res3 = domaceserije.request_page("http://dummy")
        require(res3 == "", "Cloudflare error page was not rejected!")

    finally:
        domaceserije.cRequestHandler = original_cReq

def run_unit_tests():
    print("=" * 70)
    print("RUNNING OFFLINE UNIT TESTS (domaceserije.py)")
    print("=" * 70)
    
    test_normalize_hostname()
    test_make_full_url()
    test_add_resolver_referer()
    test_extract_year()
    test_clean_card_title()
    test_detect_media_type()
    test_determine_view_mode()
    test_episode_sort_key()
    test_isolate_catalog_html()
    test_parse_catalog_cards_offline()
    test_timeout_string_rejection_vs_javascript_settimeout()
    
    print("=" * 70)
    print("ALL OFFLINE UNIT TESTS PASSED SUCCESSFULLY! (100%)")
    print("=" * 70)

if __name__ == '__main__':
    run_unit_tests()
