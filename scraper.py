#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   Stalker MAC Portal → M3U Multi-Portal Auto-Updater            ║
║   Soporta múltiples portales MAC en paralelo                    ║
║   TV en Vivo / Películas / Series con episodios completos       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import time
import os
import hashlib
import re
import sys
import math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ════════════════════════════════════════════════════════════════
PORTALS_FILE      = "portals.json"
PORTAL_PATH       = "/portal.php"
PORTAL_C          = "/stalker_portal/c/"
REQUEST_TIMEOUT   = 10
MAX_RETRIES       = 2
RETRY_DELAY       = 3
PAGE_SIZES_TO_TRY = [500, 250, 100, 50, 14]
PARALLEL_WORKERS  = 1   # 1 hilo para evitar bloqueos (Rate-Limit) de seguridad del portal

# ════════════════════════════════════════════════════════════════
#  DETECCIÓN DE IDIOMA
# ════════════════════════════════════════════════════════════════
LANGUAGE_KEYWORDS = {
    "ES": ["ES","ESP","ESPAÑOL","SPANISH","SPAIN","ESPANA","ESPAÑA","CASTELLANO","LATINO","LAT","SPA","DAZN"],
    "FR": ["FR","FRE","FRENCH","FRANCE","FRANÇAIS","FRANCAIS","FRA"],
    "EN": ["EN","ENG","ENGLISH","UK","US","USA","GB","GBR","UHD UK","UNITED KINGDOM"],
    "DE": ["DE","DEU","GERMAN","GERMANY","DEUTSCH","GER"],
    "IT": ["IT","ITA","ITALIAN","ITALY","ITALIANO"],
    "PT": ["PT","POR","PORTUGUESE","PORTUGAL","BRASIL","BR","PORTUGUES"],
    "AR": ["AR","ARA","ARABIC","ARAB","ARABE"],
    "NL": ["NL","NED","DUTCH","NETHERLANDS","HOLLAND"],
    "PL": ["PL","POL","POLISH","POLAND"],
    "RU": ["RU","RUS","RUSSIAN","RUSSIA"],
    "TR": ["TR","TUR","TURKISH","TURKEY","TURQUIE"],
}

# ════════════════════════════════════════════════════════════════
#  DETECCIÓN DE PAÍSES
# ════════════════════════════════════════════════════════════════
COUNTRY_KEYWORDS = {
    "ES": {"flag":"🇪🇸","name":"España","keywords":["ESPAÑA","SPAIN","ESPANA","TVE","ANTENA 3","CUATRO","LA SEXTA","TELECINCO","CANAL SUR","TV3","TELEMADRID","ARAGONTV","IB3","ETB","TVG","LA 1","LA 2","MOVISTAR+","GOL TV","REAL MADRID TV","BARCA TV","SPAIN HD"]},
    "FR": {"flag":"🇫🇷","name":"Francia","keywords":["FRANCE","FRANÇAIS","FRANCAIS","TF1","FRANCE 2","FRANCE 3","FRANCE 4","FRANCE 5","M6","W9","TMC","TFX","C8","CSTAR","BFMTV","LCI","CNEWS","ARTE","GULLI","RMC","NRJ12","FRANCE HD","OCS"]},
    "GB": {"flag":"🇬🇧","name":"Reino Unido","keywords":["UK","UNITED KINGDOM","BRITAIN","BRITISH","ENGLAND","BBC","ITV","CHANNEL 4","CHANNEL 5","SKY","BT SPORT","DAVE","E4","MORE4","5USA","5STAR","GOLD","ALIBI","UHD UK","SKY ONE","SKY ATLANTIC","SKY CINEMA","SKY SPORTS","TNT SPORTS"]},
    "DE": {"flag":"🇩🇪","name":"Alemania","keywords":["GERMANY","GERMAN","DEUTSCHLAND","DEUTSCH","ARD","ZDF","RTL","SAT.1","SAT1","PRO7","PROSIEBEN","VOX","KABEL1","DMAX DE","SPORT1","3SAT","PHOENIX","MÜNCHEN","BERLIN"]},
    "IT": {"flag":"🇮🇹","name":"Italia","keywords":["ITALY","ITALIAN","ITALIA","ITA","RAI","RAI 1","RAI 2","RAI 3","CANALE 5","ITALIA 1","RETE 4","LA7","TV8","NOVE","MEDIASET","SKY IT","ROMA","MILAN","NAPOLI"]},
    "PT": {"flag":"🇵🇹","name":"Portugal","keywords":["PORTUGAL","PORTUGUESE","PORTUGUES","RTP","RTP1","RTP2","SIC","TVI","CMTV","RECORD","SPORT TV","LISBOA","PORTO"]},
    "NL": {"flag":"🇳🇱","name":"Países Bajos","keywords":["NETHERLANDS","DUTCH","HOLLAND","NED","NPO","RTL NL","SBS6","NET5","VERONICA","NPO 1","NPO 2","NPO 3","RTL 4","AMSTERDAM"]},
    "BE": {"flag":"🇧🇪","name":"Bélgica","keywords":["BELGIUM","BELGIQUE","BELGIË","VRT","RTBF","VTM","CANVAS","EEN","LA UNE","LA DEUX","BRUSSELS"]},
    "CH": {"flag":"🇨🇭","name":"Suiza","keywords":["SWITZERLAND","SWISS","SUISSE","SCHWEIZ","SRF","RTS","RSI","ZURICH","GENEVA"]},
    "PL": {"flag":"🇵🇱","name":"Polonia","keywords":["POLAND","POLISH","POLSKA","TVP","TVN","POLSAT","TVP1","TVP2","TVN 24","WARSAW"]},
    "RU": {"flag":"🇷🇺","name":"Rusia","keywords":["RUSSIA","RUSSIAN","RUSSIE","CHANNEL ONE RU","RUSSIA 1","NTV","MATCH TV","MOSCOW","RT "]},
    "UA": {"flag":"🇺🇦","name":"Ucrania","keywords":["UKRAINE","UKRAINIAN","UKRAINA","1+1","INTER UA","KYIV","STB"]},
    "RO": {"flag":"🇷🇴","name":"Rumanía","keywords":["ROMANIA","ROMANIAN","PRO TV","ANTENA 1 RO","TVR","DIGI24","BUCHAREST"]},
    "TR": {"flag":"🇹🇷","name":"Turquía","keywords":["TURKEY","TURKISH","TÜRKIYE","TRT","TRT 1","ATV","SHOW TV","KANAL D TR","FOX TR","ISTANBUL"]},
    "GR": {"flag":"🇬🇷","name":"Grecia","keywords":["GREECE","GREEK","GRECIA","ERT","ANT1","MEGA GR","STAR GR","ATHENS"]},
    "SE": {"flag":"🇸🇪","name":"Suecia","keywords":["SWEDEN","SWEDISH","SVERIGE","SVT","TV4 SE","KANAL 5","STOCKHOLM"]},
    "NO": {"flag":"🇳🇴","name":"Noruega","keywords":["NORWAY","NORWEGIAN","NORGE","NRK","TV 2 NO","OSLO"]},
    "DK": {"flag":"🇩🇰","name":"Dinamarca","keywords":["DENMARK","DANISH","DANMARK","DR","TV2 DK","COPENHAGEN"]},
    "FI": {"flag":"🇫🇮","name":"Finlandia","keywords":["FINLAND","FINNISH","SUOMI","YLE","MTV3 FI","HELSINKI"]},
    "CZ": {"flag":"🇨🇿","name":"Rep. Checa","keywords":["CZECH","CZECHIA","CESKA","CT","PRIMA","NOVA CZ","PRAGUE"]},
    "HU": {"flag":"🇭🇺","name":"Hungría","keywords":["HUNGARY","HUNGARIAN","MAGYARORSZÁG","DUNA","RTL HU","TV2 HU","BUDAPEST"]},
    "HR": {"flag":"🇭🇷","name":"Croacia","keywords":["CROATIA","CROATIAN","HRVATSKA","HRT","NOVA HR","ZAGREB"]},
    "RS": {"flag":"🇷🇸","name":"Serbia","keywords":["SERBIA","SERBIAN","SRBIJA","RTS","BEOGRAD","PINK TV","B92"]},
    "US": {"flag":"🇺🇸","name":"USA","keywords":["USA","UNITED STATES","AMERICAN","NBC","CBS","ABC US","FOX US","CNN","MSNBC","ESPN","HBO","SHOWTIME","STARZ","AMC","TNT","COMEDY CENTRAL","SYFY","NEW YORK","LOS ANGELES"]},
    "MX": {"flag":"🇲🇽","name":"México","keywords":["MEXICO","MÉXICO","MEXICANO","TELEVISA","TV AZTECA","AZTECA 7","AZTECA UNO","GUADALAJARA","MONTERREY"]},
    "AR": {"flag":"🇦🇷","name":"Argentina","keywords":["ARGENTINA","ARGENTINO","EL TRECE","TELEFE","CANAL 9 AR","AMERICA TV AR","TN","BUENOS AIRES"]},
    "CO": {"flag":"🇨🇴","name":"Colombia","keywords":["COLOMBIA","COLOMBIANO","RCN","CARACOL","CANAL 1 CO","BOGOTA","MEDELLIN"]},
    "CL": {"flag":"🇨🇱","name":"Chile","keywords":["CHILE","CHILENO","TVN","CANAL 13 CL","CHV","MEGA CL","SANTIAGO DE CHILE"]},
    "PE": {"flag":"🇵🇪","name":"Perú","keywords":["PERU","PERÚ","PERUANO","LATINA TV","AMERICA TV PE","ATV","LIMA"]},
    "VE": {"flag":"🇻🇪","name":"Venezuela","keywords":["VENEZUELA","VENEZOLANO","VENEVISION","TELEVEN","GLOBOVISION","CARACAS"]},
    "BR": {"flag":"🇧🇷","name":"Brasil","keywords":["BRAZIL","BRASIL","BRASILEIRO","GLOBO","SBT","RECORD BR","BAND","SAO PAULO","RIO DE JANEIRO"]},
    "CA": {"flag":"🇨🇦","name":"Canadá","keywords":["CANADA","CANADIAN","CBC","CTV","TORONTO","MONTREAL","TSN","SPORTSNET"]},
    "MA": {"flag":"🇲🇦","name":"Marruecos","keywords":["MAROC","MOROCCO","MARRUECOS","2M","SNRT","AL AOULA","CASABLANCA","RABAT","MARRAKECH"]},
    "DZ": {"flag":"🇩🇿","name":"Argelia","keywords":["ALGERIA","ALGERIE","ARGELIA","ENTV","DZAIR TV","ALGER","ORAN"]},
    "TN": {"flag":"🇹🇳","name":"Túnez","keywords":["TUNISIA","TUNISIE","TUNEZ","WATANIYA","HANNIBAL TV","NESSMA","TUNIS"]},
    "EG": {"flag":"🇪🇬","name":"Egipto","keywords":["EGYPT","EGYPTE","EGIPTO","NILE TV","CBC EG","MBC MASR","CAIRO"]},
    "SA": {"flag":"🇸🇦","name":"Arabia Saudí","keywords":["SAUDI","ARABIA SAUDI","KSA","MBC","ROTANA","AL ARABIYA","RIYADH","MBC 1","MBC 2","MBC 3","MBC 4"]},
    "AE": {"flag":"🇦🇪","name":"Emiratos","keywords":["UAE","EMIRATOS","EMIRATES","DUBAI","ABU DHABI","SHARJAH"]},
    "QA": {"flag":"🇶🇦","name":"Qatar","keywords":["QATAR","AL JAZEERA","BEIN SPORTS","DOHA","BEINSPORTS"]},
    "LB": {"flag":"🇱🇧","name":"Líbano","keywords":["LEBANON","LIBAN","LIBANO","LBC","MTV LIBAN","AL JADEED","BEIRUT"]},
    "IQ": {"flag":"🇮🇶","name":"Irak","keywords":["IRAQ","IRAK","IRAQIA","AL IRAQIA","BAGHDAD","KURDISTAN"]},
    "IR": {"flag":"🇮🇷","name":"Irán","keywords":["IRAN","IRANIEN","IRANI","IRIB","TEHRAN"]},
    "IN": {"flag":"🇮🇳","name":"India","keywords":["INDIA","INDIAN","HINDI","STAR PLUS","ZEE TV","COLORS","SAB TV","BOLLYWOOD","MUMBAI","DELHI"]},
    "PK": {"flag":"🇵🇰","name":"Pakistán","keywords":["PAKISTAN","PAKISTANI","URDU","GEO TV","ARY DIGITAL","HUM TV","KARACHI","LAHORE"]},
    "CN": {"flag":"🇨🇳","name":"China","keywords":["CHINA","CHINESE","CCTV","CCTV 1","CCTV 4","PHOENIX TV","BEIJING","SHANGHAI","MANDARIN"]},
    "JP": {"flag":"🇯🇵","name":"Japón","keywords":["JAPAN","JAPANESE","JAPON","NHK","TV TOKYO","FUJI TV","ANIME","TOKYO JP"]},
    "KR": {"flag":"🇰🇷","name":"Corea del Sur","keywords":["KOREA","KOREAN","COREA","KBS","MBC KR","SBS KR","SEOUL","KDRAMA","K-DRAMA"]},
    "NG": {"flag":"🇳🇬","name":"Nigeria","keywords":["NIGERIA","NIGERIAN","CHANNELS TV","NTA","LAGOS","NOLLYWOOD"]},
    "ZA": {"flag":"🇿🇦","name":"Sudáfrica","keywords":["SOUTH AFRICA","SUDAFRICA","SABC","DSTV","JOHANNESBURG"]},
    "INTL": {"flag":"🌍","name":"Internacional","keywords":["INTERNATIONAL","INTERNACIONAL","EUROSPORT","EURONEWS","AL JAZEERA ENGLISH","BBC WORLD","CNN INTERNATIONAL","BLOOMBERG","NATIONAL GEOGRAPHIC","HISTORY CHANNEL"]},
}

# ════════════════════════════════════════════════════════════════
#  CLASE PORTAL
# ════════════════════════════════════════════════════════════════
class StalkerPortal:
    def __init__(self, portal_cfg: dict):
        self.id          = portal_cfg.get("id", "portal_unknown")
        self.name        = portal_cfg.get("name", "Portal sin nombre")
        raw_url          = portal_cfg.get("url", "").rstrip("/")
        # Limpiar rutas típicas de Stalker que el usuario puede haber incluido por error
        for _suffix in ["/stalker_portal/c", "/stalker_portal", "/c", "/portal.php"]:
            if raw_url.endswith(_suffix):
                raw_url = raw_url[:-len(_suffix)].rstrip("/")
        self.url         = raw_url
        self.mac         = portal_cfg.get("mac", "")
        self.color       = portal_cfg.get("color", "#e94560")
        self.enabled     = portal_cfg.get("enabled", True)
        self.api_url     = self.url + PORTAL_PATH
        self.token       = ""
        self.page_size   = 14
        self.session     = requests.Session()
        self.session.verify = False
        self.device_id   = hashlib.md5(self.mac.encode()).hexdigest()[:13].upper()
        self.device_id2  = hashlib.sha256(self.mac.encode()).hexdigest()[:13].upper()
        self.serial_num  = self.device_id
        self.signature   = hashlib.md5((self.mac + self.device_id).encode()).hexdigest()

    def build_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "X-User-Agent": "Model: MAG250; Link: WiFi",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": f"{self.url}{PORTAL_C}",
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Cookie": f"mac={self.mac}; stb_lang=en; timezone=Europe/Madrid; device_id={self.device_id}; sn={self.serial_num};",
        }

    def safe_get(self, params: dict):
        headers = self.build_headers()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(
                    self.api_url, params=params, headers=headers,
                    timeout=REQUEST_TIMEOUT, allow_redirects=True
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("js", data)
            except requests.exceptions.Timeout:
                print(f"    [{self.name}] ⚠ Timeout intento {attempt}/{MAX_RETRIES}")
            except requests.exceptions.HTTPError as e:
                print(f"    [{self.name}] ⚠ HTTP {e.response.status_code} intento {attempt}/{MAX_RETRIES}")
            except json.JSONDecodeError:
                print(f"    [{self.name}] ⚠ Respuesta no JSON intento {attempt}/{MAX_RETRIES}")
            except Exception as e:
                print(f"    [{self.name}] ⚠ Error [{e}] intento {attempt}/{MAX_RETRIES}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        return None

    def authenticate(self) -> bool:
        print(f"\n  🔐 [{self.name}] Autenticando... (MAC: {self.mac})")
        result = self.safe_get({
            "action": "handshake", "type": "stb",
            "token": "", "JsHttpRequest": "1-xml",
        })
        if not result:
            print(f"  ❌ [{self.name}] Handshake fallido")
            return False
        self.token = result.get("token", "")
        if not self.token:
            print(f"  ❌ [{self.name}] Sin token en respuesta")
            return False
        print(f"  ✅ [{self.name}] Token: {self.token[:20]}...")
        profile = self.safe_get({
            "action": "get_profile", "type": "stb",
            "id": self.mac, "JsHttpRequest": "1-xml",
            "hw_version": "2.0.0", "sn": self.serial_num,
            "device_id": self.device_id, "device_id2": self.device_id2,
            "signature": self.signature, "auth_second_step_token": "",
        })
        if profile:
            print(f"  ✅ [{self.name}] Perfil: estado={profile.get('status','?')} expira={profile.get('end_date','?')}")
        return True

    def detect_page_size(self) -> int:
        print(f"\n  🔍 [{self.name}] Detectando PAGE_SIZE óptimo...")
        for size in PAGE_SIZES_TO_TRY:
            result = self.safe_get({
                "action": "get_ordered_list", "type": "itv",
                "genre": "*", "p": "1", "perpage": str(size),
                "fav": "0", "sortby": "name", "JsHttpRequest": "1-xml",
            })
            if not result:
                continue
            items = result.get("data", []) if isinstance(result, dict) else result
            total = int(result.get("total_items", 0)) if isinstance(result, dict) else len(items)
            received = len(items)
            if received == 0:
                continue
            if received >= size or received == total:
                print(f"  ✅ [{self.name}] PAGE_SIZE = {size}")
                return size
        return 14

    def _fetch_page_threadsafe(self, params: dict):
        """Abre su propia sesión HTTP — seguro para uso en threads."""
        session = requests.Session()
        session.verify = False
        headers = self.build_headers()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = session.get(
                    self.api_url, params=params, headers=headers,
                    timeout=REQUEST_TIMEOUT, allow_redirects=True
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("js", data)
            except Exception:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
        return None

    def paginated_fetch(self, params_base: dict, max_items: int = None) -> list:
        # ── Página 1: descubrir total ──────────────────────────────
        result1 = self.safe_get({**params_base, "p": "1", "perpage": str(self.page_size)})
        if not result1:
            return []
        items1 = result1.get("data", []) if isinstance(result1, dict) else result1
        total  = int(result1.get("total_items", 0)) if isinstance(result1, dict) else len(items1)
        if not items1:
            return []

        # Si especificamos max_items, limitamos el total a procesar
        if max_items is not None and total > max_items:
            total = max_items

        total_pages = math.ceil(total / self.page_size) if total > 0 else 1
        pct = len(items1) / total * 100 if total > 0 else 100
        print(f"      [{self.name}] 📄 Pág   1: +{len(items1):>4} │ {len(items1):>5}/{total:<6} │ {pct:.0f}% [total páginas requeridas: {total_pages}]")

        if total_pages == 1:
            return items1[:total]

        # ── Páginas 2…N en paralelo ────────────────────────────────
        pages_data: dict = {1: items1}

        def fetch_one(page_num):
            if PARALLEL_WORKERS == 1:
                time.sleep(0.3) # Retraso cortesía para no saturar al portal
            params = {**params_base, "p": str(page_num), "perpage": str(self.page_size)}
            result = self._fetch_page_threadsafe(params)
            if not result:
                return page_num, []
            items = result.get("data", []) if isinstance(result, dict) else result
            return page_num, items

        with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
            futures = {executor.submit(fetch_one, p): p for p in range(2, total_pages + 1)}
            for future in as_completed(futures):
                page_num, items = future.result()
                pages_data[page_num] = items
                so_far = sum(len(v) for v in pages_data.values())
                pct2   = so_far / total * 100 if total > 0 else 0
                print(f"      [{self.name}] 📄 Pág {page_num:>3}: +{len(items):>4} │ {so_far:>5}/{total:<6} │ {pct2:.0f}%")

        # ── Combinar en orden ──────────────────────────────────────
        all_items = []
        for p in range(1, total_pages + 1):
            all_items.extend(pages_data.get(p, []))
        return all_items[:total]

    def resolve_stream_url(self, cmd: str, content_type: str, item_id: str) -> str:
        if not cmd:
            return ""
        # Si el comando ya es una URL directa, devolverla limpia
        if cmd.startswith("http://") or cmd.startswith("https://"):
            return cmd.strip()
        # Si el comando contiene una URL precedida de "ffmpeg " o "ffplay "
        # (formato habitual de los portales Stalker para TV en vivo)
        # extraemos la URL directamente sin llamar a la API
        if cmd.startswith("ffmpeg ") or cmd.startswith("ffplay "):
            url_match = re.search(r'(https?://\S+)', cmd)
            if url_match:
                extracted = url_match.group(1).strip()
                # Verificamos que el stream no sea vacío antes de devolver la URL directa
                if "stream=" in extracted and not extracted.endswith("stream="):
                    return extracted
        result = self.safe_get({
            "action": "create_link", "type": content_type,
            "cmd": cmd, "series": "0",
            "forced_storage": "undefined", "disable_ad": "0",
            "JsHttpRequest": "1-xml",
        })
        if not result:
            return f"{self.url}{cmd}" if cmd.startswith("/") else cmd
        if isinstance(result, dict):
            resolved = result.get("cmd", result.get("url", ""))
            if resolved:
                # Buscar un patrón HTTP/S que pueda estar dentro de comillas o seguido de espacios
                url_match = re.search(r'(https?://[^\s\'"\n]+)', resolved)
                if url_match:
                    return url_match.group(1).strip()
                return resolved.strip()
        return ""


    def fetch_live_tv(self) -> list:
        print(f"\n  📺 [{self.name}] Extrayendo TV en Vivo...")
        genres_result = self.safe_get({"action":"get_genres","type":"itv","JsHttpRequest":"1-xml"})
        genres = []
        if isinstance(genres_result, list): genres = genres_result
        elif isinstance(genres_result, dict): genres = genres_result.get("data", [])

        # Filtramos el género '*' (All) — siempre iteramos géneros individuales
        # para que cada canal herede el genre_title con el prefijo de idioma (ES|, FR|, etc.)
        individual_genres = [g for g in genres if g.get("id") != "*"]
        if not individual_genres:
            # Si no hay géneros individuales, usamos el '*' como fallback
            individual_genres = [{"id": "*", "title": "All"}]

        channels  = []
        seen_ids  = set()
        max_channels = 2000  # Límite para evitar atascos

        for genre in individual_genres:
            if len(channels) >= max_channels:
                break

            genre_id    = genre.get("id", "*")
            genre_title = genre.get("title", "General")
            items = self.paginated_fetch({
                "action": "get_ordered_list", "type": "itv",
                "genre": genre_id, "force_ch_link_check": "",
                "fav": "0", "sortby": "name", "JsHttpRequest": "1-xml",
            }, max_items=max_channels)
            for ch in items:
                if len(channels) >= max_channels:
                    break
                ch_id = ch.get("id", "")
                if ch_id in seen_ids: continue
                seen_ids.add(ch_id)
                name = clean_name(ch.get("name", ch.get("title", "Canal")))
                channels.append({
                    "type":        "live",
                    "id":          f"{self.id}_{ch_id}",
                    "name":        name,
                    "logo":        ch.get("logo", ch.get("tv_logo", "")),
                    "url":         extract_cmd_url(ch.get("cmd","")),
                    "group":       genre_title,
                    "lang":        detect_language(f"{name} {genre_title}"),
                    "country":     detect_country(name, genre_title, ch.get("country","")),
                    "epg_id":      ch.get("xmltv_id", ch.get("epg_id", "")),
                    "portal_id":   self.id,
                    "portal_name": self.name,
                    "portal_color":self.color,
                })
        print(f"  ✅ [{self.name}] Canales en vivo: {len(channels)}")
        return channels



    def fetch_movies(self) -> list:
        print(f"\n  🎬 [{self.name}] Extrayendo Películas...")
        cats_result = self.safe_get({"action":"get_categories","type":"vod","JsHttpRequest":"1-xml"})
        cats = []
        if isinstance(cats_result, list): cats = cats_result
        elif isinstance(cats_result, dict): cats = cats_result.get("data", [])
        if not cats: cats = [{"id": "*", "title": "Películas"}]

        movies   = []
        seen_ids = set()
        max_movies = 1000 # Límite estricto para evitar atascos de películas
        
        for cat in cats:
            if len(movies) >= max_movies:
                break
                
            cat_id    = cat.get("id", "*")
            cat_title = cat.get("title", cat.get("name", "Películas"))
            items = self.paginated_fetch({
                "action": "get_ordered_list", "type": "vod",
                "category": cat_id, "sortby": "added",
                "fav": "0", "JsHttpRequest": "1-xml",
            }, max_items=max_movies)
            new_count = 0
            for movie in items:
                if len(movies) >= max_movies:
                    break
                mid = movie.get("id", "")
                if mid in seen_ids: continue
                seen_ids.add(mid)
                new_count += 1
                name = clean_name(movie.get("name", movie.get("o_name", "Película")))
                movies.append({
                    "type":         "movie",
                    "id":           f"{self.id}_{mid}",
                    "name":         name,
                    "logo":         movie.get("screenshot_uri", movie.get("logo", movie.get("poster",""))),
                    "url":          extract_cmd_url(movie.get("cmd","")),
                    "group":        cat_title,
                    "lang":         detect_language(f"{name} {cat_title}"),
                    "country":      detect_country(name, cat_title, movie.get("country","")),
                    "description":  movie.get("description", movie.get("desc","")),
                    "year":         movie.get("year",""),
                    "director":     movie.get("director",""),
                    "actors":       movie.get("actors", movie.get("cast","")),
                    "rating":       movie.get("rating_imdb", movie.get("rating","")),
                    "duration":     movie.get("time", movie.get("duration","")),
                    "genres":       movie.get("genres_str", movie.get("genre","")),
                    "portal_id":    self.id,
                    "portal_name":  self.name,
                    "portal_color": self.color,
                })
            # Si la categoría '*' ya trajo todas las películas, no iteramos el resto
            if cat_id == "*" and new_count == len(movies) and len(movies) == len(items):
                print(f"  ⚡ [{self.name}] Categoría '*' devuelve todas las películas — omitiendo categorías individuales")
                break
        print(f"  ✅ [{self.name}] Películas: {len(movies)}")

        return movies

    def fetch_series(self) -> list:
        import base64
        print(f"\n  📺 [{self.name}] Extrayendo Series (rastreo profundo)...")
        cats_result = self.safe_get({"action":"get_categories","type":"series","JsHttpRequest":"1-xml"})
        cats = []
        if isinstance(cats_result, list): cats = cats_result
        elif isinstance(cats_result, dict): cats = cats_result.get("data", [])
        if not cats: cats = [{"id": "*", "title": "Series"}]

        episodes_list = []
        for cat in cats:
            cat_id    = cat.get("id", "*")
            if cat_id == "*": continue
            cat_title = cat.get("title", cat.get("name", "Series"))

            series_items = self.paginated_fetch({
                "action": "get_ordered_list", "type": "series",
                "genre": cat_id, "sortby": "added",
                "fav": "0", "JsHttpRequest": "1-xml",
            })
            for serie in series_items:
                raw_id   = serie.get("id", "")
                # Algunos portales devuelven "id:extra" — tomamos solo la parte numérica
                serie_id = str(raw_id).split(":")[0] if raw_id else ""
                if not serie_id: continue

                serie_name = clean_name(serie.get("name", serie.get("title", "Serie")))
                serie_logo = serie.get("screenshot_uri", serie.get("logo", serie.get("poster","")))
                lang       = detect_language(f"{serie_name} {cat_title}")
                country    = detect_country(serie_name, cat_title, serie.get("country",""))

                # Obtener temporadas usando el mismo método del código de referencia
                seasons_result = self.safe_get({
                    "action": "get_ordered_list", "type": "series",
                    "movie_id": serie_id, "JsHttpRequest": "1-xml",
                })
                seasons = []
                if isinstance(seasons_result, list): seasons = seasons_result
                elif isinstance(seasons_result, dict):
                    seasons = seasons_result.get("data", [])
                if not seasons: continue

                for season in seasons:
                    season_name = season.get("name", season.get("title", "Temporada 1"))
                    # Extraer número de temporada del nombre
                    season_num = 1
                    sn_match = re.search(r'\d+', season_name)
                    if sn_match:
                        season_num = int(sn_match.group())

                    # Lista de números de episodio en esta temporada
                    episode_nums = season.get("series", [])
                    if not episode_nums:
                        episode_nums = [1]

                    for ep_num in episode_nums:
                        ep_name = f"{serie_name} - S{season_num:02d}E{ep_num:02d}"

                        # Crear el cmd base64 exactamente como en el código de referencia
                        cmd_data = {
                            "series_id": int(serie_id),
                            "season_num": season_num,
                            "episode_num": ep_num,
                            "type": "series"
                        }
                        cmd_str = base64.b64encode(
                            json.dumps(cmd_data).encode("utf-8")
                        ).decode("utf-8")

                        # Resolver URL del episodio via create_link
                        link_result = self.safe_get({
                            "action": "create_link", "type": "vod",
                            "cmd": cmd_str, "series": "",
                            "forced_storage": "0", "disable_ad": "0",
                            "JsHttpRequest": "1-xml",
                        })
                        ep_url = ""
                        if isinstance(link_result, dict):
                            raw_url = link_result.get("cmd", link_result.get("url", ""))
                            if raw_url:
                                m = re.search(r'(https?://\S+)', raw_url)
                                ep_url = m.group(1).strip() if m else raw_url.strip()
                                # Añadir parámetros de serie al URL
                                sep = "&" if "?" in ep_url else "?"
                                if "dummy=" not in ep_url:
                                    ep_url += f"{sep}dummy=/series/&type=movie"
                        if not ep_url:
                            continue

                        episodes_list.append({
                            "type":         "series",
                            "id":           f"{self.id}_{serie_id}_s{season_num}e{ep_num}",
                            "serie_id":     f"{self.id}_{serie_id}",
                            "serie_name":   serie_name,
                            "name":         ep_name,
                            "logo":         serie_logo,
                            "url":          ep_url,
                            "group":        f"SERIES · {cat_title}",
                            "lang":         lang,
                            "country":      country,
                            "description":  serie.get("description", serie.get("desc","")),
                            "year":         serie.get("year",""),
                            "director":     serie.get("director",""),
                            "actors":       serie.get("actors", serie.get("cast","")),
                            "rating":       serie.get("rating_imdb", serie.get("rating","")),
                            "genres":       serie.get("genres_str", serie.get("genre","")),
                            "season":       str(season_num),
                            "episode":      str(ep_num),
                            "season_name":  season_name,
                            "ep_name":      ep_name,
                            "portal_id":    self.id,
                            "portal_name":  self.name,
                            "portal_color": self.color,
                        })
                time.sleep(0.3)

        print(f"  ✅ [{self.name}] Episodios: {len(episodes_list)}")
        return episodes_list


    def scrape_all(self, include_tv: bool = True, include_movies: bool = True, include_series: bool = False) -> list:
        if not self.enabled:
            print(f"\n⏭  [{self.name}] Portal desactivado, omitiendo.")
            return []

        print(f"\n{'='*60}")
        print(f"  🚀 Iniciando scraping: {self.name}")
        print(f"     URL: {self.url}")
        print(f"     MAC: {self.mac}")
        print(f"{'='*60}")

        if not self.authenticate():
            print(f"  ❌ [{self.name}] Autenticación fallida, omitiendo portal.")
            return []

        self.page_size = self.detect_page_size()
        items = []

        if include_tv:
            try:
                items.extend(self.fetch_live_tv())
            except Exception as e:
                print(f"  ⚠ [{self.name}] Error TV en Vivo: {e}")

        if include_movies:
            try:
                items.extend(self.fetch_movies())
            except Exception as e:
                print(f"  ⚠ [{self.name}] Error Películas: {e}")

        if include_series:
            try:
                print(f"\n  📺 [{self.name}] Iniciando rastreo profundo de Series...")
                items.extend(self.fetch_series())
            except Exception as e:
                print(f"  ⚠ [{self.name}] Error Series: {e}")

        print(f"\n  ✅ [{self.name}] Total items: {len(items)}")
        return items



# ════════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
# ════════════════════════════════════════════════════════════════
def clean_name(name: str) -> str:
    if not name: return "Sin nombre"
    return name.strip().replace(",", " -").replace('"', "'")

def extract_cmd_url(cmd: str) -> str:
    """Extrae la URL directamente del campo cmd del portal Stalker.
    Los portales Stalker devuelven el cmd en formatos como:
      - 'ffmpeg http://host/play/live.php?...'
      - 'ffplay http://host/play/movie.php?...'
      - 'http://host/play/live.php?...' (ya resuelto)
    Esta funcion limpia cualquier prefijo y devuelve la URL limpia.
    """
    if not cmd:
        return ""
    cmd = cmd.strip()
    # Si ya es una URL directa
    if cmd.startswith("http://") or cmd.startswith("https://"):
        return cmd
    # Extraer URL de comandos ffmpeg/ffplay/vlc
    m = re.search(r'(https?://\S+)', cmd)
    if m:
        return m.group(1).strip()
    return ""

def detect_language(text: str) -> str:
    upper = text.upper()
    # Primero: detectar el prefijo que el portal ya incluye en el nombre
    # Formato comun: 'FR| Canal Name', 'ES| Canal Name', 'SP - Pelicula'
    prefix_match = re.match(r'^([A-Z]{2,3})[|\-\s]', upper)
    if prefix_match:
        prefix = prefix_match.group(1)
        if prefix in LANGUAGE_KEYWORDS:
            return prefix
    # Segundo: busqueda por keywords
    for lang, keywords in LANGUAGE_KEYWORDS.items():
        for kw in keywords:
            pattern = r'(?:^|[\s|\-_\[\]():,])' + re.escape(kw) + r'(?:$|[\s|\-_\[\]():,])'
            if re.search(pattern, upper):
                return lang
    return "OTHER"

def detect_country(name: str, group: str = "", country_field: str = "") -> str:
    if country_field:
        upper_cf = country_field.upper().strip()
        for code, data in COUNTRY_KEYWORDS.items():
            if upper_cf == code or upper_cf == data["name"].upper():
                return code
    search_text = f"{name} {group}".upper()
    for code, data in COUNTRY_KEYWORDS.items():
        for kw in data["keywords"]:
            if not kw: continue
            pattern = r'(?:^|[\s|\-_\[\]():,./+])' + re.escape(kw) + r'(?:$|[\s|\-_\[\]():,./+])'
            if re.search(pattern, search_text):
                return code
    return "OTHER"

def load_portals() -> list:
    portals = []
    if os.path.exists(PORTALS_FILE):
        try:
            with open(PORTALS_FILE, "r", encoding="utf-8") as f:
                portals = json.load(f)
            print(f"✅ Portales cargados desde {PORTALS_FILE}: {len(portals)}")
        except Exception as e:
            print(f"⚠ Error leyendo {PORTALS_FILE}: {e}")

    env_url = os.environ.get("PORTAL_URL", "")
    env_mac = os.environ.get("MAC_ADDRESS", "")
    if env_url and env_mac:
        existing = next((p for p in portals if p.get("url") == env_url), None)
        if not existing:
            portals.insert(0, {
                "id": "portal_env", "name": "Portal (env)",
                "url": env_url, "mac": env_mac,
                "enabled": True, "color": "#e94560"
            })

    if not portals:
        print("❌ No se encontraron portales configurados.")
        sys.exit(1)

    enabled = [p for p in portals if p.get("enabled", True)]
    print(f"📡 Portales activos: {len(enabled)}/{len(portals)}")
    return portals

def generate_m3u(all_items: list, portals: list) -> str:
    portal_names = {p["id"]: p["name"] for p in portals}
    lines = [
        "#EXTM3U",
        f"# Generado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"# Portales: {', '.join(portal_names.values())}",
        f"# Total items: {len(all_items)}",
        "",
    ]
    for item in all_items:
        if not item.get("url"): continue
        lang        = item.get("lang", "OTHER")
        country     = item.get("country", "OTHER")
        itype       = item.get("type", "live")
        portal_name = item.get("portal_name", "")

        if itype == "live":
            group = f"Live | {item.get('group','General')} ({lang})"
        elif itype == "movie":
            group = f"Movies | {item.get('group','Películas')} ({lang})"
        else:
            group = f"Series | {item.get('group','Series')} ({lang})"

        extinf = (
            f'#EXTINF:-1 tvg-id="{item.get("epg_id","")}" '
            f'tvg-logo="{item.get("logo","")}" '
            f'group-title="{group}"'
        )
        if itype in ("movie","series"):
            if item.get("year"):     extinf += f' tvg-year="{item["year"]}"'
            if item.get("director"): extinf += f' tvg-director="{item["director"]}"'
            if item.get("rating"):   extinf += f' tvg-rating="{item["rating"]}"'

        # Limpiar prefijo ffmpeg o ffplay si estuviera en la URL
        url = item["url"].strip()
        if url.startswith("ffmpeg "):
            url = url[7:].strip()
        elif url.startswith("ffplay "):
            url = url[7:].strip()

        lines.extend([f'{extinf},{item.get("name","Sin nombre")}', url, ""])
    return "\n".join(lines)

def generate_stats(all_items: list, portals: list) -> dict:
    live   = [i for i in all_items if i["type"]=="live"]
    movies = [i for i in all_items if i["type"]=="movie"]
    series = [i for i in all_items if i["type"]=="series"]
    langs, countries, by_portal = {}, {}, {}
    for item in all_items:
        l = item.get("lang","OTHER");    langs[l]     = langs.get(l,0)+1
        c = item.get("country","OTHER"); countries[c] = countries.get(c,0)+1
        p = item.get("portal_name","?"); by_portal[p] = by_portal.get(p,0)+1
    return {
        "live_channels": len(live),
        "movies":        len(movies),
        "series":        len(set(i.get("serie_name","") for i in series)),
        "episodes":      len(series),
        "languages":     langs,
        "countries":     countries,
        "by_portal":     by_portal,
        "portals":       [{"id":p["id"],"name":p["name"],"color":p["color"],"enabled":p["enabled"]} for p in portals],
        "total":         len(all_items),
    }

# ════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════
def main():
    print("="*65)
    print("  🚀 Stalker MAC Multi-Portal → M3U Scraper")
    print(f"  📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*65)

    # ── PARSEO DE ARGUMENTOS ──
    include_tv = True
    include_movies = True
    include_series = True

    mode = "all"
    if "--only-tv" in sys.argv:
        include_tv = True
        include_movies = False
        include_series = False
        mode = "tv"
        print("🔍 Modo: ESCUTAR ÚNICAMENTE CANALES DE TV (Rápido)")
    elif "--only-movies" in sys.argv:
        include_tv = False
        include_movies = True
        include_series = False
        mode = "movies"
        print("🔍 Modo: ESCUTAR ÚNICAMENTE PELÍCULAS (Rápido)")
    elif "--only-series" in sys.argv:
        include_tv = False
        include_movies = False
        include_series = True
        mode = "series"
        print("🔍 Modo: ESCUTAR ÚNICAMENTE SERIES (Workflow lento)")
    elif "--no-series" in sys.argv:
        include_tv = True
        include_movies = True
        include_series = False
        mode = "no-series"
        print("🔍 Modo: ESCUTAR TV Y PELÍCULAS (Sin series)")

    portals_cfg = load_portals()
    enabled     = [p for p in portals_cfg if p.get("enabled", True)]

    if not enabled:
        print("❌ No hay portales activos.")
        sys.exit(1)

    all_items = []
    for portal_cfg in enabled:
        portal = StalkerPortal(portal_cfg)
        items  = portal.scrape_all(include_tv, include_movies, include_series)
        all_items.extend(items)

    # Si estamos corriendo un modo específico (parcial), leemos la metadata actual
    # para conservar los elementos de las otras categorías y no borrarlos.
    metadata_file = "metadata.json"
    existing_items = []
    if mode != "all" and os.path.exists(metadata_file):
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                old_meta = json.load(f)
            
            old_items = old_meta.get("items", [])
            
            # Qué elementos conservamos de la versión anterior
            if mode == "tv":
                # Conservamos películas y series anteriores
                existing_items = [i for i in old_items if i.get("type") in ("movie", "series")]
            elif mode == "movies":
                # Conservamos TV y series anteriores
                existing_items = [i for i in old_items if i.get("type") in ("live", "series")]
            elif mode == "series":
                # Conservamos TV y películas anteriores
                existing_items = [i for i in old_items if i.get("type") in ("live", "movie")]
            elif mode == "no-series":
                # Conservamos series anteriores
                existing_items = [i for i in old_items if i.get("type") == "series"]
                
            print(f"📦 Combinando {len(existing_items)} elementos anteriores con los nuevos de esta ejecución.")
        except Exception as meta_err:
            print(f"⚠️ Error al mezclar la metadata anterior: {meta_err}")

    # Lista total unificada para el metadata del dashboard
    unified_items = all_items + existing_items

    # ── FILTRADO BAJO DEMANDA PARA M3U ──
    filters_file = "user_filters.json"
    filtered_items = unified_items
    if os.path.exists(filters_file):
        try:
            with open(filters_file, "r", encoding="utf-8") as f:
                filter_cfg = json.load(f)
            
            allowed_langs = set(filter_cfg.get("languages", []))
            allowed_ctries = set(filter_cfg.get("countries", []))
            
            if allowed_langs or allowed_ctries:
                print(f"\n📂 Aplicando filtros de exportación desde {filters_file}...")
                
                filtered_items = []
                for item in unified_items:
                    item_lang = item.get("lang", "OTHER")
                    item_ctry = item.get("country", "OTHER")
                    
                    lang_ok = not allowed_langs or item_lang in allowed_langs
                    ctry_ok = not allowed_ctries or item_ctry in allowed_ctries
                    
                    if lang_ok and ctry_ok:
                        filtered_items.append(item)
                
                print(f"🎯 Items filtrados para M3U: {len(filtered_items)} de {len(unified_items)} totales.")
        except Exception as filter_err:
            print(f"⚠️ Error al aplicar filtros de usuario: {filter_err}")

    # Separar en las tres playlists independientes
    tv_items    = [i for i in filtered_items if i.get("type") == "live"]
    movie_items = [i for i in filtered_items if i.get("type") == "movie"]
    series_items = [i for i in filtered_items if i.get("type") == "series"]

    stats = generate_stats(unified_items, portals_cfg)
    print("\n"+"="*65)
    print("  📊 RESUMEN FINAL")
    print("="*65)
    print(f"  📡 Portales procesados : {len(enabled)}")
    print(f"  📺 Canales en vivo     : {len(tv_items)}")
    print(f"  🎬 Películas           : {len(movie_items)}")
    print(f"  📺 Series              : {len(series_items)}")
    print(f"  📁 TOTAL FILTRADO M3U  : {len(filtered_items)}")
    print("="*65)

    # 1. playlist_tv.m3u
    m3u_tv = generate_m3u(tv_items, portals_cfg)
    with open("playlist_tv.m3u", "w", encoding="utf-8") as f: f.write(m3u_tv)
    print(f"✅ playlist_tv.m3u ({len(tv_items)} items)")

    # 2. playlist_movies.m3u
    m3u_movies = generate_m3u(movie_items, portals_cfg)
    with open("playlist_movies.m3u", "w", encoding="utf-8") as f: f.write(m3u_movies)
    print(f"✅ playlist_movies.m3u ({len(movie_items)} items)")

    # 3. playlist_series.m3u
    m3u_series = generate_m3u(series_items, portals_cfg)
    with open("playlist_series.m3u", "w", encoding="utf-8") as f: f.write(m3u_series)
    print(f"✅ playlist_series.m3u ({len(series_items)} items)")

    # Guardar también el playlist.m3u global heredado
    m3u_global = generate_m3u(filtered_items, portals_cfg)
    with open("playlist.m3u", "w", encoding="utf-8") as f: f.write(m3u_global)

    metadata = {
        "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "portals":   [p["name"] for p in enabled],
        "total":     len(unified_items),
        "items":     unified_items
    }
    with open("metadata.json","w",encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"✅ metadata.json ({len(json.dumps(metadata)):,} bytes)")

    stats["generated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    with open("stats.json","w",encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("✅ stats.json")
    print("\n🎉 ¡Proceso completado!")

if __name__ == "__main__":
    main()
