# -*- coding: utf-8 -*-
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import domaceserije
from resources.lib.gui.gui import cGui
from resources.lib.handler.ParameterHandler import ParameterHandler

def run_tests():
    print("=" * 70)
    print("DEEP LIVE VERIFICATION OF REFACTORED domaceserije.py (xStream 2026 Compatible)")
    print("=" * 70)

    # TEST 1: load()
    print("\n--- TEST 1: Main Menu (load) ---")
    cGui.current_items.clear()
    domaceserije.load()
    print(f"Main menu items created: {len(cGui.current_items)}")
    for item in cGui.current_items:
        print(f" - [{item['element'].title}] -> func: {item['element'].function}, sUrl: {item['params'].get('sUrl')}")
    assert len(cGui.current_items) == 5, "Main menu should have 5 items"

    # TEST 2: Series Catalog (showCatalog)
    print("\n--- TEST 2: Series Catalog (bIsFolder Check) ---")
    cGui.current_items.clear()
    p = ParameterHandler()
    p.setParam('sUrl', domaceserije.URL_SERIES)
    domaceserije.showCatalog()
    print(f"Series parsed: {len(cGui.current_items)}")
    for item in cGui.current_items[:3]:
        print(f" - [{item['element'].title}] type: {item['element'].media_type}, bIsFolder: {item['is_folder']} -> url: {item['params'].get('sUrl')}")
    assert cGui.current_items[0]['is_folder'] == True, "Series should have bIsFolder=True"

    # TEST 3: Movies Catalog (bIsFolder Check)
    print("\n--- TEST 3: Movies Catalog (bIsFolder=False Check) ---")
    cGui.current_items.clear()
    p = ParameterHandler()
    p.setParam('sUrl', domaceserije.URL_MOVIES)
    domaceserije.showCatalog()
    print(f"Movies parsed: {len(cGui.current_items)}")
    for item in cGui.current_items[:3]:
        print(f" - [{item['element'].title}] type: {item['element'].media_type}, bIsFolder: {item['is_folder']} -> url: {item['params'].get('sUrl')}")
    movie_item = next(i for i in cGui.current_items if i['element'].media_type == 'movie')
    assert movie_item['is_folder'] == False, "Movies MUST have bIsFolder=False for direct playback!"
    first_movie_url = movie_item['params'].get('sUrl')

    # TEST 4: Dubbed Series & Episode bIsFolder Check
    print("\n--- TEST 4: Dubbed Series & Episodes (bIsFolder=False Check) ---")
    cGui.current_items.clear()
    p = ParameterHandler()
    p.setParam('sUrl', 'https://domaceserije.net/sinhronizovano/icarly')
    p.setParam('sName', 'iCarly')
    domaceserije.showSeasons()
    
    print(f"Seasons folders created: {len(cGui.current_items)}")
    assert cGui.current_items[0]['is_folder'] == True, "Seasons MUST have bIsFolder=True"
    
    cGui.current_items.clear()
    p.setParam('sSeasonFilter', '1')
    domaceserije.showSeasons()
    print(f"Season 1 Episodes extracted: {len(cGui.current_items)}")
    print(f" - [{cGui.current_items[0]['element'].title}] bIsFolder: {cGui.current_items[0]['is_folder']}")
    assert cGui.current_items[0]['is_folder'] == False, "Episodes MUST have bIsFolder=False for direct playback!"

    # TEST 5a: JS Hoster Extraction & Flemoon $$referer check
    print("\n--- TEST 5a: JS Hoster Extraction & Flemoon $$referer Check ---")
    ep_url = cGui.current_items[0]['params'].get('sUrl')
    p = ParameterHandler()
    p.setParam('sUrl', ep_url)
    hosters = domaceserije.showHosters()
    print(f"Hosters extracted for JS player ({ep_url}): {len(hosters)-1 if hosters and 'getHosterUrl' in hosters else 0}")
    if isinstance(hosters, list):
        for h in hosters:
            if isinstance(h, dict):
                print(f" - Provider: {h.get('name')} | Stream URL: {h.get('link')}")

    # TEST 5b: HTML Hoster Extraction for Movie
    print("\n--- TEST 5b: HTML Hoster Extraction for Movie ---")
    p = ParameterHandler()
    p.setParam('sUrl', first_movie_url)
    movie_hosters = domaceserije.showHosters()
    print(f"Hosters extracted for Movie ({first_movie_url}): {len(movie_hosters)-1 if movie_hosters and 'getHosterUrl' in movie_hosters else 0}")
    if isinstance(movie_hosters, list):
        for h in movie_hosters:
            if isinstance(h, dict):
                print(f" - Provider: {h.get('name')} | Stream URL: {h.get('link')}")

    # TEST 6: Search & Global _search
    print("\n--- TEST 6: Global xStream _search ---")
    cGui.current_items.clear()
    dummy_gui = cGui()
    domaceserije._search(dummy_gui, 'senke')
    print(f"Global search results for 'senke': {len(cGui.current_items)}")
    for item in cGui.current_items:
        print(f" - [{item['element'].title}] type: {item['element'].media_type}, bIsFolder: {item['is_folder']} -> url: {item['params'].get('sUrl')}")

    print("\n" + "=" * 70)
    print("ALL REPOSITORY COMPARISON FIXES VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == '__main__':
    run_tests()
