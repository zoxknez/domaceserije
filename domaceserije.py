# -*- coding: utf-8 -*-
# Python 3 - Modul za xStream / Kodi (domaceserije.net)
# Version: 1.0.0
# Verified: 2026-08-01
# Compatible: xStream 2026.02.11+ / ResolveURL 5.1.173+

import re
from html import unescape
from urllib.parse import quote_plus, urljoin, urlparse

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'domaceserije'
SITE_NAME = 'DomaceSerije'
SITE_ICON = 'domaceserije.png'

# Dinamičko podešavanje domena preko cConfig sa fallback-om na domaceserije.net
DOMAIN = (cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'domaceserije.net') or 'domaceserije.net').strip().strip('/')
if not DOMAIN.startswith(('http://', 'https://')):
    URL_MAIN = 'https://' + DOMAIN
else:
    URL_MAIN = DOMAIN

URL_SERIES = URL_MAIN + '/zanr-tv/svi'
URL_MOVIES = URL_MAIN + '/zanr-film/svi'
URL_DUBBED = URL_MAIN + '/zanr-crtaci/sinhronizovano'
URL_CARTOONS = URL_MAIN + '/zanr-crtaci/crtaci'
URL_SEARCH_PAGE = URL_MAIN + '/search.php?search='

# Konstante keširanja
CACHE_CATALOG = 2 * 60 * 60
CACHE_SERIES = 60 * 60
CACHE_SEARCH = 30 * 60

# Hostere koji zahtevaju Referer za ResolveURL (uključuje i flemoon alias)
REFERER_HOSTERS = ('filemoon', 'flemoon', 'vidhide', 'swiftload')

# Eksplicitno podešavanje globalne pretrage
SITE_GLOBAL_SEARCH = (cConfig().getSetting('global_search_' + SITE_IDENTIFIER) != 'false')

def normalize_hostname(value):
    """Izdvaja i normalizuje domen bez portova i 'www.'"""
    if not value:
        return ""
    hostname = urlparse(value).netloc.lower().split(':', 1)[0]
    if hostname.startswith('www.'):
        hostname = hostname[4:]
    return hostname

def request_page(url, caching=True, ignoreErrors=False, cache_time=None, referer=None, origin=None, bypass_dns=False):
    """Mrežni zahtev sa podrškom za keširanje, Referer/Origin zaglavlja i detekciju grešaka"""
    try:
        req = cRequestHandler(url, caching=caching, ignoreErrors=ignoreErrors, bypass_dns=bypass_dns)
        
        if cache_time is not None:
            req.cacheTime = cache_time

        if referer:
            req.addHeaderEntry('Referer', referer)

        if origin:
            req.addHeaderEntry('Origin', origin)

        content = req.request() or ""
        content_upper = content.upper()
        
        known_errors = (
            "SEITE NICHT ERREICHBAR",
            "URL FEHLER",
            "CLOUDFLARE-SCHUTZ AKTIV",
            "DDOS GUARD SCHUTZ"
        )
        
        # Provera tačnog TIMEOUT odgovora ili fraza grešaka (izbegava setTimeout u JS-u)
        if content.strip().upper() in ("TIMEOUT", "HTTP TIMEOUT", "REQUEST TIMEOUT") or any(error in content_upper for error in known_errors):
            logger.error(f"[{SITE_IDENTIFIER}] Neuspešan odgovor za {url}")
            return ""

        return content
    except Exception as exc:
        logger.error(f"[{SITE_IDENTIFIER}] Greška mreže pri dohvatanju {url}: {exc}")
        return ""

def make_full_url(path, base_url=None):
    """Pouzdan pretvarač relativnih i protokol-relativnih URL-ova u puni URL sa kontekstom roditelja"""
    if not path:
        return ""
    path = unescape(path.strip()).replace('\\/', '/')
    if path.startswith('//'):
        return 'https:' + path
    return urljoin(base_url or (URL_MAIN + '/'), path)

def add_resolver_referer(stream_url, referer, hoster_name=""):
    """Dodaje ResolveURL Referer za hostere kojima je potreban (prepoznaje i domen i ime servera)"""
    if not stream_url or "$$" in stream_url or not referer:
        return stream_url

    hostname = normalize_hostname(stream_url)
    identity = f"{hostname} {hoster_name}".lower()

    if any(hoster in identity for hoster in REFERER_HOSTERS):
        return f"{stream_url}$${referer}"

    return stream_url

def extract_year(raw_desc):
    """Izvlači 4-cifrenu godinu iz opisa radi poboljšanja TMDB metapodataka"""
    text = unescape(re.sub(r'<[^>]+>', ' ', raw_desc))
    match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    return int(match.group(1)) if match else None

def clean_card_title(raw_desc):
    """Izvlači samo čist naslov serije/filma iz img__description bloka"""
    parts = [re.sub(r'<[^>]*>', '', part).strip() for part in re.split(r'<br\s*/?>', raw_desc, flags=re.IGNORECASE)]
    parts = [p for p in parts if p]
    if parts:
        return unescape(parts[0])
    return "Nepoznat naslov"

def detect_media_type(url, raw_desc):
    """Precizno određivanje tipa sadržaja ('movie' ili 'tvshow')"""
    clean_desc = unescape(re.sub(r'<[^>]+>', ' ', raw_desc)).lower()

    if '(serija)' in clean_desc:
        return 'tvshow'
    if '(film)' in clean_desc:
        return 'movie'

    movie_paths = ('/domaci-film/', '/domaci-filmovi/', 'ceo-film-online', '-film-online')
    if any(path in url.lower() for path in movie_paths):
        return 'movie'

    return 'tvshow'

def determine_view_mode(cards):
    """Određuje validan xStream view mode (movies, tvshows, files) na osnovu kartica"""
    if not cards:
        return 'files'
    media_types = {card['media_type'] for card in cards}
    if media_types == {'movie'}:
        return 'movies'
    elif media_types == {'tvshow'}:
        return 'tvshows'
    return 'files'

def episode_sort_key(episode):
    """Numeričko sortiranje sezona i epizoda radi sprečavanja leksikografskih grešaka (1, 10, 100, 11)"""
    title = episode[0]
    match = re.search(r'(?:Sezona|S)\s*(\d+).*?Epizoda\s*(\d+)', title, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))

    match = re.search(r'Epizoda\s*(\d+)', title, re.IGNORECASE)
    if match:
        return 1, int(match.group(1))

    return 9999, 9999

def isolate_catalog_html(html_content):
    """Odseca sidebar 'najgl' i izoluje glavno telo kataloga ili pretrage sa fallback-om"""
    if not html_content:
        return ""
    
    album_match = re.search(r'id=["\']latestalbum["\']', html_content, re.IGNORECASE)
    if album_match:
        return html_content[album_match.start():]
        
    search_match = re.search(r'(?:Pretraga\s*:|Poslednja\s+Pretraga\s*:)', html_content, re.IGNORECASE)
    if search_match:
        return html_content[search_match.start():]

    return html_content

def parse_catalog_cards(html_content):
    """Jedinstveni i otporni parser kartica (katalog i pretraga)"""
    cards = []
    clean_html = isolate_catalog_html(html_content)

    wrap_pattern = (
        r'<div[^>]*class=["\'][^"\']*\bimg__wrap\b[^"\']*["\'][^>]*>'
        r'(.*?)'
        r'(?=<div[^>]*class=["\'][^"\']*\bimg__wrap\b[^"\']*["\']|</section>|<footer>|$)'
    )
    wrap_blocks = re.findall(wrap_pattern, clean_html, re.DOTALL)

    seen_links = set()

    for block in wrap_blocks:
        link_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\']', block)
        if not link_match:
            continue
        link = make_full_url(link_match.group(1))

        if link in seen_links:
            continue

        # Prioritet ima data-src nad src radi sprečavanja placeholder slika
        img_match = (
            re.search(r'<img[^>]+data-src=["\']([^"\']+)["\']', block, re.IGNORECASE) or
            re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.IGNORECASE)
        )
        thumb = make_full_url(img_match.group(1)) if img_match else ""

        desc_match = re.search(r'<p[^>]*class=["\'][^"\']*\bimg__description\b[^"\']*["\'][^>]*>(.*?)</p>', block, re.DOTALL)
        raw_desc = desc_match.group(1) if desc_match else block

        title = clean_card_title(raw_desc)
        media_type = detect_media_type(link, raw_desc)
        year = extract_year(raw_desc)

        seen_links.add(link)
        cards.append({
            'title': title,
            'url': link,
            'thumb': thumb,
            'media_type': media_type,
            'year': year
        })
    return cards

def load():
    """Glavni meni xStream dodatka za domaceserije.net"""
    logger.info('Load %s' % SITE_NAME)
    oGui = cGui()
    
    # Domaće Serije
    params = ParameterHandler()
    params.setParam('sUrl', URL_SERIES)
    oGui.addFolder(cGuiElement("Domaće Serije", SITE_IDENTIFIER, 'showCatalog'), params)

    # Domaći Filmovi
    params = ParameterHandler()
    params.setParam('sUrl', URL_MOVIES)
    oGui.addFolder(cGuiElement("Domaći Filmovi", SITE_IDENTIFIER, 'showCatalog'), params)

    # Sinhronizovano
    params = ParameterHandler()
    params.setParam('sUrl', URL_DUBBED)
    oGui.addFolder(cGuiElement("Sinhronizovano", SITE_IDENTIFIER, 'showCatalog'), params)

    # Crtaći
    params = ParameterHandler()
    params.setParam('sUrl', URL_CARTOONS)
    oGui.addFolder(cGuiElement("Crtaći", SITE_IDENTIFIER, 'showCatalog'), params)

    # Pretraga
    params = ParameterHandler()
    oGui.addFolder(cGuiElement("Pretraga", SITE_IDENTIFIER, 'showSearch'), params)

    oGui.setEndOfDirectory()

def showCatalog():
    """Prikaz kataloga (Serije, Filmovi, Crtaći) sa paginacijom"""
    params = ParameterHandler()
    sUrl = params.getValue('sUrl') or URL_SERIES
    oGui = cGui()
    
    sHtmlContent = request_page(sUrl, caching=True, cache_time=CACHE_CATALOG, referer=URL_MAIN + '/', bypass_dns=True)
    if not sHtmlContent:
        logger.error(f"[{SITE_IDENTIFIER}] Katalog nije otvoren: {sUrl}")
        oGui.showInfo()
        oGui.setEndOfDirectory(False)
        return

    cards = parse_catalog_cards(sHtmlContent)
    
    if not cards:
        logger.error(f"[{SITE_IDENTIFIER}] Nisu pronađene kartice u katalogu: {sUrl}")
        oGui.showInfo()
        oGui.setEndOfDirectory(False)
        return

    logger.info(f"[{SITE_IDENTIFIER}] Katalog {sUrl}: pronadjeno {len(cards)} kartica")
    total = len(cards)

    for card in cards:
        is_movie = card['media_type'] == 'movie'

        if is_movie:
            oGuiElement = cGuiElement(card['title'], SITE_IDENTIFIER, 'showHosters')
            oGuiElement.setMediaType('movie')
        else:
            oGuiElement = cGuiElement(card['title'], SITE_IDENTIFIER, 'showSeasons')
            oGuiElement.setMediaType('tvshow')

        if card.get('year') and hasattr(oGuiElement, 'setYear'):
            oGuiElement.setYear(card['year'])

        if card['thumb']:
            oGuiElement.setThumbnail(card['thumb'])

        p = ParameterHandler()
        p.setParam('sUrl', card['url'])
        p.setParam('sName', card['title'])
        p.setParam('sThumbnail', card['thumb'])
        p.setParam('sReferer', sUrl)

        # Film ima bIsFolder=False, serija ima bIsFolder=True, prosleđuje se total
        oGui.addFolder(oGuiElement, p, not is_movie, total)

    # Logika za sledeću stranicu (paginacija)
    current_page = 1
    page_match = re.search(r'[?&]page=(\d+)', sUrl)
    if page_match:
        current_page = int(page_match.group(1))

    next_page_num = current_page + 1
    next_page_pattern = f'href=["\'](?:[^"\']*page=)?{next_page_num}["\']'
    
    if re.search(next_page_pattern, sHtmlContent):
        base_url = sUrl.split('?page=')[0].split('&page=')[0]
        sep = '&' if '?' in base_url else '?'
        next_url = f"{base_url}{sep}page={next_page_num}"

        p_next = ParameterHandler()
        p_next.setParam('sUrl', next_url)

        if hasattr(oGui, 'addNextPage'):
            oGui.addNextPage(SITE_IDENTIFIER, 'showCatalog', p_next)
        else:
            oGui.addFolder(cGuiElement(">>> Sledeća stranica (%d)" % next_page_num, SITE_IDENTIFIER, 'showCatalog'), p_next, True, total)

    oGui.setView(determine_view_mode(cards))
    oGui.setEndOfDirectory()

def parse_episodes(sHtmlContent):
    """Izvlači sve epizode iz HTML-a serije (kombinuje HTML i JS epizode sa striktnim proverama domena)"""
    episodes = []
    seen_episode_urls = set()

    # 1. Izolacija <li> elemenata u tabelama epizoda uz \b match za klasu
    li_pattern = r'<li[^>]*class=["\'][^"\']*\bplaylist-number\b[^"\']*["\'][^>]*>(.*?)</li>'
    li_blocks = re.findall(li_pattern, sHtmlContent, re.DOTALL)
    
    for block in li_blocks:
        title_match = re.search(r'<h4>\s*(.*?)\s*</h4>', block, re.DOTALL)
        link_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\']', block)
        if title_match and link_match:
            ep_title = unescape(re.sub(r'<[^>]*>', '', title_match.group(1))).strip()
            ep_link = make_full_url(link_match.group(1))
            # Preskačemo naslove zaglavlja sezone koji nisu epizode
            if ep_title.upper().startswith('SEZONA') and 'EPIZODA' not in ep_title.upper():
                continue
            if ep_link and ep_link not in seen_episode_urls:
                seen_episode_urls.add(ep_link)
                episodes.append((ep_title, ep_link))

    # 2. JS nizovi (npr. iCarly) – Normalizacija www. i poddomena pri proveri
    site_host = normalize_hostname(URL_MAIN)
    js_arrays = re.findall(r'(?:const|let|var)?\s*[\w$]+\s*=\s*\[(.*?)\]\s*;', sHtmlContent, re.DOTALL)
    clean_urls = []
    for arr_str in js_arrays:
        raw_urls = re.findall(r'["\']([^"\']+)["\']', arr_str)
        candidate_urls = []
        for u in raw_urls:
            if '/zsrv/' not in u and 'search=rs-' not in u:
                continue
            full_u = make_full_url(u)
            u_host = normalize_hostname(full_u)
            if u_host == site_host or u_host.endswith('.' + site_host):
                candidate_urls.append(full_u)
        if candidate_urls:
            clean_urls = candidate_urls
            break

    if clean_urls:
        logger.info(f"[{SITE_IDENTIFIER}] JS epizode: pronađeno {len(clean_urls)} URL-ova")
        btn_matches = re.findall(r'<a[^>]+id=["\'](\d+)["\'][^>]*>\s*<strong>([^<]+)</strong>\s*-\s*([^<]+)\s*</a>', sHtmlContent)
        for ep_id_str, s_part, ep_part in btn_matches:
            try:
                idx = int(ep_id_str) - 1
                if 0 <= idx < len(clean_urls):
                    ep_link = clean_urls[idx]
                    if ep_link not in seen_episode_urls:
                        seen_episode_urls.add(ep_link)
                        full_ep_title = f"{s_part.strip()} - {ep_part.strip()}"
                        episodes.append((full_ep_title, ep_link))
            except (ValueError, IndexError):
                continue

    # 3. Opšti fallback pretraga ako ništa nije nađeno
    if not episodes:
        general_matches = re.findall(r'<a[^>]+href=["\']([^"\']*(?:sezona|epizoda)[^"\']*)["\'][^>]*>\s*(.*?)\s*</a>', sHtmlContent, re.IGNORECASE | re.DOTALL)
        for ep_link, ep_title in general_matches:
            clean_t = unescape(re.sub(r'<[^>]*>', '', ep_title)).strip()
            clean_l = make_full_url(ep_link)
            if clean_t and clean_l not in seen_episode_urls:
                seen_episode_urls.add(clean_l)
                episodes.append((clean_t, clean_l))

    return episodes

def showSeasons():
    """Prikaz stranice serije - sezone i epizode sa Kodi metapodacima i sReferer praćenjem"""
    params = ParameterHandler()
    sUrl = params.getValue('sUrl')
    sName = params.getValue('sName') or "Serija"
    sThumbnail = params.getValue('sThumbnail')
    sSeasonFilter = params.getValue('sSeasonFilter')
    sReferer = params.getValue('sReferer') or (URL_MAIN + '/')

    oGui = cGui()

    if not sUrl:
        logger.error(f"[{SITE_IDENTIFIER}] Nedostaje sUrl u showSeasons()")
        oGui.showInfo()
        oGui.setEndOfDirectory(False)
        return

    sHtmlContent = request_page(sUrl, caching=True, cache_time=CACHE_SERIES, referer=sReferer, bypass_dns=True)
    if not sHtmlContent:
        logger.error(f"[{SITE_IDENTIFIER}] Stranica serije nije učitana: {sUrl}")
        oGui.showInfo()
        oGui.setEndOfDirectory(False)
        return

    # Opis serije: Prioritet ima vidljivi sinopsis u telu stranice pre SEO meta tagova
    sDesc = ""
    desc_match = (
        re.search(r'<p><strong>Serija[^:]*:?\s*</strong>\s*<br\s*/?>\s*(.*?)</p>', sHtmlContent, re.DOTALL) or
        re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', sHtmlContent, re.IGNORECASE) or
        re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']', sHtmlContent, re.IGNORECASE) or
        re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', sHtmlContent, re.IGNORECASE) or
        re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', sHtmlContent, re.IGNORECASE)
    )
    if desc_match:
        sDesc = unescape(desc_match.group(1)).strip()
        sDesc = re.sub(r'<[^>]*>', '', sDesc)

    # Poster serije (prihvata oba redosleda property i content atributa)
    if not sThumbnail:
        thumb_match = (
            re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', sHtmlContent, re.IGNORECASE) or
            re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', sHtmlContent, re.IGNORECASE)
        )
        if thumb_match:
            sThumbnail = make_full_url(thumb_match.group(1))

    all_episodes = parse_episodes(sHtmlContent)

    if not all_episodes:
        logger.error(f"[{SITE_IDENTIFIER}] Nisu pronađene epizode za {sName}")
        oGui.showInfo()
        oGui.setEndOfDirectory(False)
        return

    # Grupisati epizode po sezonama
    seasons_dict = {}
    for ep_title, ep_link in all_episodes:
        season_num = "1"
        s_match = re.search(r'(?:Sezona|S)\s*(\d+)', ep_title, re.IGNORECASE)
        if s_match:
            season_num = s_match.group(1)

        if season_num not in seasons_dict:
            seasons_dict[season_num] = []
        seasons_dict[season_num].append((ep_title, ep_link))

    # Numeričko sortiranje epizoda unutar svake sezone (rešava 1, 10, 100, 11 problem)
    for season_key in seasons_dict:
        seasons_dict[season_key].sort(key=episode_sort_key)

    logger.info(f"[{SITE_IDENTIFIER}] Serija {sName}: pronađeno {len(all_episodes)} epizoda, {len(seasons_dict)} sezona")

    # Ako serija ima više sezona i korisnik još nije izabrao sezonu
    if len(seasons_dict) > 1 and not sSeasonFilter:
        seasons_total = len(seasons_dict)
        for s_num in sorted(seasons_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            oGuiElement = cGuiElement(f"Sezona {s_num}", SITE_IDENTIFIER, 'showSeasons')
            oGuiElement.setMediaType('season')
            if hasattr(oGuiElement, 'setTVShowTitle'):
                oGuiElement.setTVShowTitle(sName)
            if hasattr(oGuiElement, 'setSeason'):
                try:
                    oGuiElement.setSeason(int(s_num))
                except (ValueError, TypeError):
                    pass

            if sThumbnail:
                oGuiElement.setThumbnail(sThumbnail)
            if sDesc:
                oGuiElement.setDescription(sDesc)

            p = ParameterHandler()
            p.setParam('sUrl', sUrl)
            p.setParam('sName', sName)
            p.setParam('sThumbnail', sThumbnail)
            p.setParam('sSeasonFilter', s_num)
            p.setParam('sReferer', sUrl)
            
            # Sezona je FOLDER (bIsFolder=True)
            oGui.addFolder(oGuiElement, p, True, seasons_total)

        oGui.setView('seasons')
        oGui.setEndOfDirectory()
        return

    # Prikaz epizoda za izabranu sezonu ili sve epizode
    if sSeasonFilter:
        target_episodes = seasons_dict.get(sSeasonFilter, [])
    else:
        all_episodes.sort(key=episode_sort_key)
        target_episodes = all_episodes

    if not target_episodes:
        logger.error(f"[{SITE_IDENTIFIER}] Nema epizoda za sezonu {sSeasonFilter}")
        oGui.showInfo()
        oGui.setEndOfDirectory(False)
        return

    episodes_total = len(target_episodes)
    for sEpTitle, sCleanEpLink in target_episodes:
        oGuiElement = cGuiElement(sEpTitle, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('episode')
        
        if hasattr(oGuiElement, 'setTVShowTitle'):
            oGuiElement.setTVShowTitle(sName)

        ep_match = re.search(r'(?:Sezona|S)\s*(\d+).*?Epizoda\s*(\d+)', sEpTitle, re.IGNORECASE)
        if ep_match and hasattr(oGuiElement, 'setSeason') and hasattr(oGuiElement, 'setEpisode'):
            try:
                oGuiElement.setSeason(int(ep_match.group(1)))
                oGuiElement.setEpisode(int(ep_match.group(2)))
            except (ValueError, TypeError):
                pass
        else:
            ep_only = re.search(r'Epizoda\s*(\d+)', sEpTitle, re.IGNORECASE)
            if ep_only and hasattr(oGuiElement, 'setSeason') and hasattr(oGuiElement, 'setEpisode'):
                try:
                    oGuiElement.setSeason(1)
                    oGuiElement.setEpisode(int(ep_only.group(1)))
                except (ValueError, TypeError):
                    pass

        if sThumbnail:
            oGuiElement.setThumbnail(sThumbnail)
        if sDesc:
            oGuiElement.setDescription(sDesc)

        p = ParameterHandler()
        p.setParam('sUrl', sCleanEpLink)
        p.setParam('sName', f"{sName} - {sEpTitle}")
        p.setParam('sThumbnail', sThumbnail)
        p.setParam('sReferer', sUrl)

        # Epizoda ima bIsFolder=False, prosleđuje se episodes_total
        oGui.addFolder(oGuiElement, p, False, episodes_total)

    oGui.setView('episodes')
    oGui.setEndOfDirectory()

def showHosters():
    """Dohvatanje ugrađenih video plejera/hostera sa preciznim praćenjem sReferer lanca"""
    hosters = []
    params = ParameterHandler()
    sUrl = params.getValue('sUrl')
    sReferer = params.getValue('sReferer') or (URL_MAIN + '/')
    
    if not sUrl:
        return []

    # Ako je sUrl već direktni zsrv plejer (npr. iz JS niza za crtaće)
    if '/zsrv/' in sUrl or 'search=rs-' in sUrl:
        player_iframe_url = make_full_url(sUrl, URL_MAIN)
        player_referer = sReferer
    else:
        sHtmlContent = request_page(sUrl, caching=False, referer=sReferer, bypass_dns=True)
        if not sHtmlContent:
            return []

        iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']*zsrv/[^"\']+)["\']', sHtmlContent)
        if not iframe_match:
            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']*(?:embed|player|stream|video)[^"\']+)["\']', sHtmlContent)

        if not iframe_match:
            logger.error(f"[{SITE_IDENTIFIER}] Nije pronađen zsrv iframe na {sUrl}")
            return []

        player_iframe_url = make_full_url(iframe_match.group(1), sUrl)
        player_referer = sUrl

    try:
        embed_html = request_page(player_iframe_url, caching=False, referer=player_referer)
        if embed_html:
            seen_hoster_urls = set()
            site_host = normalize_hostname(URL_MAIN)

            # 1. HTML href linkovi (npr. href="filemoon?search=...")
            servers = re.findall(r'<a[^>]+href=["\']([^"#][^"\']*)["\'][^>]*>\s*<span>\s*•?\s*(?:Server\s*-\s*)?([^<]+)\s*</span>', embed_html)
            for sSrvPath, sSrvName in servers:
                sSrvName = sSrvName.strip()

                if cConfig().isBlockedHoster(sSrvName)[0]:
                    continue

                sSrvUrl = make_full_url(sSrvPath, player_iframe_url)
                try:
                    srv_html = request_page(sSrvUrl, caching=False, referer=player_iframe_url)
                    if srv_html:
                        # Pronalaženje svih iframe-ova na sSrvUrl i filtriranje oglasnih iframe-ova sa glavnog sajta
                        iframe_urls = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', srv_html, re.IGNORECASE)
                        logger.info(f"[{SITE_IDENTIFIER}] Server {sSrvName}: pronađeno {len(iframe_urls)} iframe kandidata")
                        
                        real_stream_url = ""
                        for raw_iframe_url in iframe_urls:
                            candidate = make_full_url(raw_iframe_url, sSrvUrl)
                            candidate_host = normalize_hostname(candidate)
                            
                            if not candidate_host or candidate_host == site_host:
                                continue

                            parsed = urlparse(candidate)
                            if parsed.scheme in ("http", "https"):
                                real_stream_url = candidate
                                break

                        if real_stream_url and real_stream_url not in seen_hoster_urls:
                            if not cConfig().isBlockedHoster(real_stream_url)[0]:
                                seen_hoster_urls.add(real_stream_url)
                                # Za HTML hostere Referer je sSrvUrl, i proverava se i ime servera
                                resolver_url = add_resolver_referer(real_stream_url, sSrvUrl, sSrvName)
                                hosters.append({
                                    'link': resolver_url,
                                    'name': sSrvName,
                                    'displayedName': sSrvName
                                })
                except Exception as e:
                    logger.error(f"[{SITE_IDENTIFIER}] Greška pri dohvatanju servera {sSrvName}: {e}")
                    continue

            # 2. JS switch-case linkovi (npr. crtani plejer: case 1: src = "https://glme.rpmvid.site/#...")
            js_cases = dict(re.findall(r'case\s*(\d+):\s*src\s*=\s*["\']([^"\']+)["\']', embed_html))
            btn_matches = re.findall(r'<a[^>]+id=["\'](\d+)["\'][^>]*>\s*<span>\s*•?\s*(?:Server\s*-\s*)?([^<]+)\s*</span>', embed_html)
            for btn_id, sSrvName in btn_matches:
                sSrvName = sSrvName.strip()
                if btn_id in js_cases:
                    stream_url = make_full_url(js_cases[btn_id], player_iframe_url)
                    if stream_url and stream_url not in seen_hoster_urls:
                        if not cConfig().isBlockedHoster(sSrvName)[0] and not cConfig().isBlockedHoster(stream_url)[0]:
                            seen_hoster_urls.add(stream_url)
                            resolver_url = add_resolver_referer(stream_url, player_iframe_url, sSrvName)
                            hosters.append({
                                'link': resolver_url,
                                'name': sSrvName,
                                'displayedName': sSrvName
                            })

            logger.info(f"[{SITE_IDENTIFIER}] Plejer {player_iframe_url}: pronađeno {len(servers)} HTML servera, {len(js_cases)} JS servera -> {len(hosters)} validnih hostera")
    except Exception as e:
        logger.error(f"[{SITE_IDENTIFIER}] Greška pri ekstrakciji hostera: {e}")

    if not hosters:
        logger.error(f"[{SITE_IDENTIFIER}] Nije pronađen nijedan hoster na: {player_iframe_url if 'player_iframe_url' in locals() else sUrl}")

    if hosters:
        hosters.append('getHosterUrl')

    return hosters

def getHosterUrl(hUrl):
    """Prosleđivanje video URL-a u Kodi ResolveURL"""
    if isinstance(hUrl, list):
        if not hUrl:
            return []
        hUrl = hUrl[0]
    if not hUrl:
        return []
    return [{'streamUrl': hUrl, 'resolved': False}]

def _search(oGui, sSearchText):
    """Integracija sa xStream globalnom pretragom"""
    SSsearch(oGui, sSearchText)

def showSearch():
    """Unos teksta za pretragu preko Kodi tastature"""
    oGui = cGui()
    sSearchText = oGui.showKeyBoard(sHeading="Pretraga filma ili serije")
    if not sSearchText:
        oGui.setEndOfDirectory()
        return
    SSsearch(False, sSearchText)

def SSsearch(sGui=False, sSearchText=False):
    """Pretraga sajta domaceserije.net sa podrškom za globalnu pretragu"""
    oGui = sGui if sGui else cGui()
    
    if not sSearchText:
        return

    is_global_search = sGui is not False
    sUrl = f"{URL_SEARCH_PAGE}{quote_plus(str(sSearchText))}"
    
    sHtmlContent = request_page(sUrl, caching=True, cache_time=CACHE_SEARCH, ignoreErrors=is_global_search, referer=URL_MAIN + '/', bypass_dns=True)
    
    if not sHtmlContent:
        logger.error(f"[{SITE_IDENTIFIER}] Pretraga nije uspela za: {sSearchText}")
        if not sGui:
            oGui.showInfo()
            oGui.setEndOfDirectory(False)
        return

    cards = parse_catalog_cards(sHtmlContent)
    logger.info(f"[{SITE_IDENTIFIER}] Pretraga '{sSearchText}': {len(cards)} rezultata, URL={sUrl}")

    if not cards:
        if not sGui:
            oGui.showInfo()
            oGui.setEndOfDirectory(False)
        return

    total = len(cards)
    for card in cards:
        is_movie = card['media_type'] == 'movie'

        if is_movie:
            oGuiElement = cGuiElement(card['title'], SITE_IDENTIFIER, 'showHosters')
            oGuiElement.setMediaType('movie')
        else:
            oGuiElement = cGuiElement(card['title'], SITE_IDENTIFIER, 'showSeasons')
            oGuiElement.setMediaType('tvshow')

        if card.get('year') and hasattr(oGuiElement, 'setYear'):
            oGuiElement.setYear(card['year'])

        if card['thumb']:
            oGuiElement.setThumbnail(card['thumb'])

        p = ParameterHandler()
        p.setParam('sUrl', card['url'])
        p.setParam('sName', card['title'])
        p.setParam('sThumbnail', card['thumb'])
        p.setParam('sReferer', sUrl)

        # Film ima bIsFolder=False, serija ima bIsFolder=True, prosleđuje se total
        oGui.addFolder(oGuiElement, p, not is_movie, total)

    if not sGui:
        oGui.setView(determine_view_mode(cards))
        oGui.setEndOfDirectory()

_search = SSsearch

