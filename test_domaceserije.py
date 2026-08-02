# -*- coding: utf-8 -*-
"""
ROBUST LIVE INTEGRATION & REGRESSION TEST SUITE FOR domaceserije.py (xStream 2026 Compatible)

Key Architecture & Quality Assurance Enhancements:
- State Isolation: ParameterHandler.reset() and cGui.current_items reset before every invocation.
- Standalone Tests: Tests use independent fixtures without inter-test dependencies.
- Referer Spy: Spy wrapper on request_page() verifies sReferer propagation in HTTP headers.
- Strong Assertions: Strict validation of JS and HTML hosters, Flemoon/Vidhide $$referer links.
- Catalog & Pagination Separation: Distinguishes media content cards from pagination links.
- Safe Access & require(): Safe assertions using require() to prevent python -O stripping.
"""

import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import domaceserije
from resources.lib.gui.gui import cGui
from resources.lib.handler.ParameterHandler import ParameterHandler

def require(condition, message):
    """Assertion helper resilient against python -O flag stripping"""
    if not condition:
        raise AssertionError(f"TEST ASSERTION FAILED: {message}")

def invoke(function, *args, **params):
    """Executes target function with isolated ParameterHandler state and clean cGui items"""
    ParameterHandler.reset()
    cGui.current_items.clear()

    handler = ParameterHandler()
    for key, value in params.items():
        handler.setParam(key, value)

    result = function(*args)
    return result, list(cGui.current_items)


def split_catalog_items(items):
    """Separates content media cards (movies/tvshows) from pagination navigation links"""
    content_items = [
        item for item in items
        if item['element'].function in ('showSeasons', 'showHosters')
    ]
    pagination_items = [
        item for item in items
        if item['element'].function == 'showCatalog'
    ]
    return content_items, pagination_items

# --- INDEPENDENT FIXTURES ---

def get_first_movie():
    """Independent fixture: fetches movie catalog and returns first valid movie item"""
    _, items = invoke(domaceserije.showCatalog, sUrl=domaceserije.URL_MOVIES)
    content_items, _ = split_catalog_items(items)
    movie_item = next(
        (item for item in content_items if item['element'].media_type == 'movie'),
        None
    )
    require(movie_item is not None, "Fixture failed: Movie catalog contains no movie items")
    return movie_item

def get_icarly_episode():
    """Independent fixture: fetches iCarly season 1 episodes and returns first episode item"""
    icarly_url = domaceserije.URL_MAIN + '/sinhronizovano/icarly'
    _, items = invoke(
        domaceserije.showSeasons,
        sUrl=icarly_url,
        sName='iCarly',
        sSeasonFilter='1',
        sReferer=domaceserije.URL_DUBBED
    )
    require(items, "Fixture failed: No episodes returned for iCarly season 1")
    first_ep = items[0]
    require(first_ep['element'].media_type == 'episode', "Fixture failed: First item is not an episode")
    return first_ep


# --- LIVE TEST SUITE ---

def test_1_main_menu():
    print("\n--- TEST 1: Main Menu (load) ---")
    _, items = invoke(domaceserije.load)
    print(f"Main menu items created: {len(items)}")
    for item in items:
        print(f" - [{item['element'].title}] -> func: {item['element'].function}, sUrl: {item['params'].get('sUrl')}")
    require(len(items) == 5, f"Main menu should have exactly 5 items, got {len(items)}")

def test_2_series_catalog():
    print("\n--- TEST 2: Series Catalog (bIsFolder Check & Card/Pagination Separation) ---")
    _, items = invoke(domaceserije.showCatalog, sUrl=domaceserije.URL_SERIES)
    series_items, series_pagination = split_catalog_items(items)
    
    print(f"Series cards parsed: {len(series_items)} | Pagination links: {len(series_pagination)}")
    require(len(series_items) > 0, "Series catalog returned zero media content items")
    
    for item in series_items[:3]:
        print(f" - [{item['element'].title}] type: {item['element'].media_type}, bIsFolder: {item['is_folder']} -> url: {item['params'].get('sUrl')}")
    
    require(
        all(item['element'].media_type == 'tvshow' and item['is_folder'] is True for item in series_items),
        "ALL series catalog items MUST have media_type='tvshow' and bIsFolder=True!"
    )

def test_3_movies_catalog():
    print("\n--- TEST 3: Movies Catalog (bIsFolder=False Check) ---")
    _, items = invoke(domaceserije.showCatalog, sUrl=domaceserije.URL_MOVIES)
    movie_items, movie_pagination = split_catalog_items(items)
    
    print(f"Movie cards parsed: {len(movie_items)} | Pagination links: {len(movie_pagination)}")
    require(len(movie_items) > 0, "Movie catalog returned zero media content items")
    
    for item in movie_items[:3]:
        print(f" - [{item['element'].title}] type: {item['element'].media_type}, bIsFolder: {item['is_folder']} -> url: {item['params'].get('sUrl')}")
    
    require(
        all(item['element'].media_type == 'movie' and item['is_folder'] is False for item in movie_items),
        "ALL movie items MUST have media_type='movie' and bIsFolder=False for direct playback!"
    )

def test_4_dubbed_series_and_episodes():
    print("\n--- TEST 4: Dubbed Series & Episodes (bIsFolder=False Check) ---")
    icarly_url = domaceserije.URL_MAIN + '/sinhronizovano/icarly'
    
    # 4a: Seasons Folders Check
    _, season_items = invoke(
        domaceserije.showSeasons,
        sUrl=icarly_url,
        sName='iCarly',
        sReferer=domaceserije.URL_DUBBED
    )
    require(season_items, "No season folders created for iCarly")
    print(f"Seasons folders created: {len(season_items)}")
    require(season_items[0]['is_folder'] is True, "Seasons MUST have bIsFolder=True")
    
    # 4b: Episode Extraction Check
    _, episode_items = invoke(
        domaceserije.showSeasons,
        sUrl=icarly_url,
        sName='iCarly',
        sSeasonFilter='1',
        sReferer=domaceserije.URL_DUBBED
    )
    require(episode_items, "No episode items extracted for iCarly season 1")
    print(f"Season 1 Episodes extracted: {len(episode_items)}")
    print(f" - [{episode_items[0]['element'].title}] bIsFolder: {episode_items[0]['is_folder']}")
    require(episode_items[0]['is_folder'] is False, "Episodes MUST have bIsFolder=False for direct playback!")

def test_5a_js_hoster_extraction_and_referer_spy():
    print("\n--- TEST 5a: JS Hoster Extraction & Flemoon $$referer & HTTP Header Spy Check ---")
    ep_item = get_icarly_episode()
    ep_params = ep_item['params']
    ep_url = ep_params.get('sUrl')
    ep_referer = ep_params.get('sReferer')

    # Spy request_page to confirm HTTP headers passed to network handler
    request_calls = []
    original_request_page = domaceserije.request_page

    def request_spy(url, **kwargs):
        request_calls.append({'url': url, **kwargs})
        return original_request_page(url, **kwargs)

    domaceserije.request_page = request_spy

    try:
        hosters, _ = invoke(
            domaceserije.showHosters,
            sUrl=ep_url,
            sReferer=ep_referer
        )
    finally:
        domaceserije.request_page = original_request_page

    # Verify HTTP Referer header propagation in spy
    player_call = next(
        (call for call in request_calls if call['url'] == ep_url),
        None
    )
    require(player_call is not None, f"request_page was not called for episode URL {ep_url}")
    require(player_call.get('referer') == ep_referer, f"Expected referer '{ep_referer}', got '{player_call.get('referer')}'")

    # Assert hoster return structure
    require(isinstance(hosters, list), "showHosters must return a list")
    require(hosters, "JS player returned no hosters")
    require(hosters[-1] == 'getHosterUrl', "Missing 'getHosterUrl' resolver callback")

    js_hosters = [h for h in hosters if isinstance(h, dict)]
    require(len(js_hosters) >= 1, "No valid JS hoster dictionaries returned")

    print(f"Extracted JS hosters count: {len(js_hosters)}")
    for h in js_hosters:
        print(f" - Provider: {h.get('name')} | Stream URL: {h.get('link')}")

    # Flemoon Referer Assertion
    flemoon = next(
        (h for h in js_hosters if 'flemoon' in h.get('name', '').lower() or 'filemoon' in h.get('name', '').lower()),
        None
    )
    require(flemoon is not None, "Flemoon hoster was not extracted from JS player")
    require('$$' in flemoon['link'], "Flemoon stream link is missing '$$referer'")

    stream_url, referer = flemoon['link'].rsplit('$$', 1)
    require(stream_url.startswith(('http://', 'https://')), f"Invalid Flemoon stream URL: {stream_url}")
    require(referer == ep_url, f"Wrong Flemoon referer: {referer} (expected {ep_url})")

def test_5b_html_hoster_extraction_and_vidhide():
    print("\n--- TEST 5b: HTML Hoster Extraction for Movie & VIDHIDE Check ---")
    movie_item = get_first_movie()
    movie_url = movie_item['params'].get('sUrl')
    movie_referer = movie_item['params'].get('sReferer')

    movie_hosters, _ = invoke(
        domaceserije.showHosters,
        sUrl=movie_url,
        sReferer=movie_referer
    )

    require(isinstance(movie_hosters, list), "showHosters for movie must return a list")
    require(movie_hosters, "Movie HTML player returned no hosters")
    require(movie_hosters[-1] == 'getHosterUrl', "Missing 'getHosterUrl' resolver callback")

    html_hosters = [h for h in movie_hosters if isinstance(h, dict)]
    require(len(html_hosters) >= 1, "No valid HTML hoster dictionaries returned")

    print(f"Extracted HTML hosters count: {len(html_hosters)}")
    for h in html_hosters:
        print(f" - Provider: {h.get('name')} | Stream URL: {h.get('link')}")

    vidhide = next(
        (h for h in html_hosters if 'vidhide' in h.get('name', '').lower()),
        None
    )
    require(vidhide is not None, "VIDHIDE hoster was not extracted from HTML player")
    require('$$' in vidhide['link'], "VIDHIDE stream link is missing '$$referer'")

    stream_url, referer = vidhide['link'].rsplit('$$', 1)
    require(
        domaceserije.normalize_hostname(stream_url) != domaceserije.normalize_hostname(domaceserije.URL_MAIN),
        f"Stream URL points to main site hostname: {stream_url}"
    )
    require('/zsrv/' in referer, f"VIDHIDE referer is missing '/zsrv/': {referer}")
    require('vidhide' in referer.lower(), f"VIDHIDE referer is missing 'vidhide': {referer}")

def test_6_global_search():
    print("\n--- TEST 6: Global xStream _search ---")
    dummy_gui = cGui()
    _, items = invoke(domaceserije._search, dummy_gui, 'senke')

    
    require(items, "Global search returned no results for 'senke'")
    print(f"Global search results for 'senke': {len(items)}")
    for item in items:
        print(f" - [{item['element'].title}] type: {item['element'].media_type}, bIsFolder: {item['is_folder']} -> url: {item['params'].get('sUrl')}")

    require(
        all(item['is_folder'] == (item['element'].media_type != 'movie') for item in items),
        "Search result bIsFolder flag does not match media_type (movie MUST be False, tvshow MUST be True)"
    )

    media_types = {item['element'].media_type for item in items}
    print(f"Media types found in search: {media_types}")
    require('tvshow' in media_types or 'movie' in media_types, "Search did not return valid media types")

def run_live_tests():
    print("=" * 70)
    print("LIVE INTEGRATION & REGRESSION SUITE (domaceserije.py)")
    print("=" * 70)

    test_1_main_menu()
    test_2_series_catalog()
    test_3_movies_catalog()
    test_4_dubbed_series_and_episodes()
    test_5a_js_hoster_extraction_and_referer_spy()
    test_5b_html_hoster_extraction_and_vidhide()
    test_6_global_search()

    print("\n" + "=" * 70)
    print("ALL LIVE PARSING AND XSTREAM INTEGRATION CHECKS PASSED. (100%)")
    print("(Note: Actual video playback in Kodi requires a Kodi runtime environment)")
    print("=" * 70)

if __name__ == '__main__':
    run_live_tests()
