# DomaceSerije.net - xStream / Kodi Plugin Modul

[![xStream Compatible](https://img.shields.io/badge/xStream-2026.02.11%2B-blue.svg)](https://github.com/michaz1988/michaz1988.github.io)
[![ResolveURL Compatible](https://img.shields.io/badge/ResolveURL-5.1.173%2B-green.svg)](https://github.com/michaz1988/michaz1988.github.io)
[![Python 3](https://img.shields.io/badge/Python-3.x-yellow.svg)](https://www.python.org/)

Zvanični xStream modul za podršku sajta [domaceserije.net](https://domaceserije.net) u Kodi okruženju.

## 🚀 Karakteristike

- **Pun katalog**: Podrška za Domaće Serije, Domaće Filmove, Sinhronizovane crtaće i Animirane crtaće.
- **xStream 2026 Arhitektura**:
  - `bIsFolder=False` za reproduktivne filmove i epizode (direktno pokretanje plejera).
  - `bIsFolder=True` za serije i sezonske foldere.
  - `iTotal` optimizacija za brzinu TMDB metapodataka.
- **Potpuni Referer lanac**:
  - `sReferer` praćenje navigacije sa roditeljske stranice do plejera.
  - `$$referer` sintaksa za ResolveURL (Filemoon, Flemoon, Vidhide, Swiftload).
  - Odvajanje `sSrvUrl` referera kod HTML hostera.
- **Pametna ekstrakcija hostera**:
  - Automatsko hvatanje HTML servera i JavaScript switch-case servera (RPMShare, VidMoly, Filemoon, Vidhide, Streamtape).
  - Normalizacija `www.` i poddomena.
  - Filtriranje lokalnih oglasnih iframe-ova.
- **Optimizacija i stabilnost**:
  - `bypass_dns=True` podrška za mrežni fallback.
  - Detekcija Cloudflare, DDoS Guard i exact TIMEOUT odgovora.
  - Numeričko sortiranje sezona i epizoda (sprečavanje 1, 10, 100, 11 problema).
  - TMDB metapodaci (`setYear`, `setSeason`, `setEpisode`, `setTVShowTitle`).
- **Pretraga**: Lokalna tastatura i xStream globalna pretraga (`_search`).

## 📦 Instalacija u Kodi / xStream

Kopirajte fajl `domaceserije.py` u xStream direktorijum sajtova:
`special://home/addons/plugin.video.xstream/resources/lib/sites/domaceserije.py`

## 🧪 Testiranje

Test paket se pokreće komandom:
```bash
python test_domaceserije.py
```

## 📄 Licenca

Distributed under the MIT License.
