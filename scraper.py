#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   Stalker MAC Portal → M3U Auto-Updater + Metadata Scraper      ║
║   Autor: Sistema GitHub Actions (Zero-Device Architecture)       ║
║   Portal: http://mag.greatott.me:80                              ║
║   Soporta: TV en Vivo / Películas / Series (con episodios)       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import time
import os
import hashlib
import re
import sys
from datetime import datetime

# ════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DEL PORTAL (tus datos por defecto)
# ════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DEL PORTAL
# ════════════════════════════════════════════════════════════════
PORTAL_URL   = os.environ.get("PORTAL_URL",   "http://mag.greatott.me:80")
MAC_ADDRESS  = os.environ.get("MAC_ADDRESS",  "00:1A:79:74:B1:B9")

# Tamaños de página a intentar (de mayor a menor)
# El scraper probará cada uno y usará el que el portal acepte
PAGE_SIZES_TO_TRY = [500, 250, 100, 50, 14]

# Se determina automáticamente en detect_page_size()
OPTIMAL_PAGE_SIZE = 14  # valor inicial, se sobreescribe
# Rutas del portal Stalker Middleware (estándar Infomir)
PORTAL_PATH  = "/portal.php"
PORTAL_C     = "/stalker_portal/c/"
API_URL      = PORTAL_URL + PORTAL_PATH

# Dispositivo emulado: MAG250 (el más compatible con Stalker Middleware)
DEVICE_ID    = hashlib.md5(MAC_ADDRESS.encode()).hexdigest()[:13].upper()
DEVICE_ID2   = hashlib.sha256(MAC_ADDRESS.encode()).hexdigest()[:13].upper()
SERIAL_NUM   = DEVICE_ID
SIGNATURE    = hashlib.md5((MAC_ADDRESS + DEVICE_ID).encode()).hexdigest()

# Idiomas soportados para filtrado automático
LANGUAGE_KEYWORDS = {
    "ES": ["ES","ESP","ESPAÑOL","SPANISH","SPAIN","ESPANA","CASTELLANO","LATINO","LAT","SPA"],
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

# Timeout y reintentos
REQUEST_TIMEOUT = 30
MAX_RETRIES     = 3
RETRY_DELAY     = 5   # segundos entre reintentos
PAGE_SIZE       = 14  # elementos por página en la API Stalker

# ════════════════════════════════════════════════════════════════
#  CABECERAS HTTP (imitando un MAG250 real)
# ════════════════════════════════════════════════════════════════
def build_headers(token: str = ""):
    """Construye las cabeceras HTTP que imitan un dispositivo MAG250."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (QtEmbedded; U; Linux; C) "
            "AppleWebKit/533.3 (KHTML, like Gecko) "
            "MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
        ),
        "X-User-Agent":   "Model: MAG250; Link: WiFi",
        "Accept":         "*/*",
        "Accept-Language":"en-US,en;q=0.5",
        "Accept-Encoding":"gzip, deflate",
        "Connection":     "keep-alive",
        "Referer":        f"{PORTAL_URL}{PORTAL_C}",
        "Authorization":  f"Bearer {token}" if token else "",
        "Cookie": (
            f"mac={MAC_ADDRESS}; "
            f"stb_lang=en; "
            f"timezone=Europe/Madrid; "
            f"device_id={DEVICE_ID}; "
            f"sn={SERIAL_NUM}; "
        ),
    }

# ════════════════════════════════════════════════════════════════
#  UTILIDADES
# ════════════════════════════════════════════════════════════════
def safe_get(session: requests.Session, url: str, params: dict, token: str) -> dict | None:
    """GET con reintentos y manejo de errores robusto."""
    headers = build_headers(token)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                url, params=params, headers=headers,
                timeout=REQUEST_TIMEOUT, allow_redirects=True
            )
            resp.raise_for_status()
            data = resp.json()
            # Stalker envuelve el resultado en {"js": ...}
            return data.get("js", data)
        except requests.exceptions.Timeout:
            print(f"  ⚠  Timeout en intento {attempt}/{MAX_RETRIES} → {url}")
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠  HTTP {e.response.status_code} en intento {attempt}/{MAX_RETRIES}")
        except json.JSONDecodeError:
            print(f"  ⚠  Respuesta no es JSON en intento {attempt}/{MAX_RETRIES}")
        except Exception as e:
            print(f"  ⚠  Error inesperado [{e}] en intento {attempt}/{MAX_RETRIES}")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
    return None


def detect_language(text: str) -> str:
    """Detecta el idioma de un canal/categoría por palabras clave en el nombre."""
    upper = text.upper()
    for lang, keywords in LANGUAGE_KEYWORDS.items():
        for kw in keywords:
            # Busca la palabra clave como token (no subcadena parcial)
            pattern = r'(?:^|[\s|\-_\[\]():,])' + re.escape(kw) + r'(?:$|[\s|\-_\[\]():,])'
            if re.search(pattern, upper):
                return lang
    return "OTHER"


def clean_name(name: str) -> str:
    """Limpia nombres de canales/contenido para M3U."""
    if not name:
        return "Sin nombre"
    return name.strip().replace(",", " -").replace('"', "'")


def paginated_fetch(session, params_base: dict, token: str) -> list:
    """
    Recorre TODAS las páginas de la API Stalker (paginación automática).
    La API devuelve `data` (lista) y `total_items` (total).
    """
    all_items = []
    page = 1
    while True:
        params = {**params_base, "p": page, "perpage": PAGE_SIZE}
        result = safe_get(session, API_URL, params, token)
        if not result:
            break

        # La respuesta puede ser dict con 'data' o directamente una lista
        if isinstance(result, dict):
            items = result.get("data", [])
            total = int(result.get("total_items", 0))
        elif isinstance(result, list):
            items = result
            total = len(items)
        else:
            break

        if not items:
            break

        all_items.extend(items)
        print(f"      📄 Página {page}: +{len(items)} items (total acumulado: {len(all_items)}/{total})")

        if len(all_items) >= total and total > 0:
            break
        if len(items) < PAGE_SIZE:
            break

        page += 1
        time.sleep(0.3)  # Pausa cortés para no saturar el portal

    return all_items

# ════════════════════════════════════════════════════════════════
#  FASE 1 → AUTENTICACIÓN (Handshake Stalker)
# ════════════════════════════════════════════════════════════════
def authenticate(session: requests.Session) -> str | None:
    """
    Realiza el handshake con el portal Stalker.
    Devuelve el token de sesión o None si falla.
    
    Flujo estándar Stalker Middleware (Infomir):
    1. GET /portal.php?action=handshake → obtiene token
    2. GET /portal.php?action=get_profile → activa la sesión
    """
    print("\n🔐 FASE 1 · Autenticación con el portal...")
    print(f"   Portal  : {PORTAL_URL}")
    print(f"   MAC     : {MAC_ADDRESS}")
    print(f"   DeviceID: {DEVICE_ID}")

    # ── Paso 1: Handshake ──────────────────────────────────────
    handshake_params = {
        "action":          "handshake",
        "type":            "stb",
        "token":           "",
        "JsHttpRequest":   "1-xml",
    }
    result = safe_get(session, API_URL, handshake_params, "")
    if not result:
        print("  ❌ Handshake FALLIDO: no hay respuesta del portal.")
        return None

    token = result.get("token", "")
    if not token:
        print(f"  ❌ Handshake FALLIDO: sin token. Respuesta: {result}")
        return None

    print(f"  ✅ Token obtenido: {token[:20]}...")

    # ── Paso 2: Get Profile (activa la sesión) ─────────────────
    profile_params = {
        "action":        "get_profile",
        "type":          "stb",
        "id":            MAC_ADDRESS,
        "JsHttpRequest": "1-xml",
        "hw_version":    "2.0.0",
        "sn":            SERIAL_NUM,
        "device_id":     DEVICE_ID,
        "device_id2":    DEVICE_ID2,
        "signature":     SIGNATURE,
        "auth_second_step_token": "",
    }
    profile = safe_get(session, API_URL, profile_params, token)
    if not profile:
        print("  ⚠  get_profile no respondió; se continúa con el token obtenido.")
    else:
        expiry = profile.get("end_date", "Desconocida")
        status = profile.get("status", "?")
        print(f"  ✅ Perfil activado · Estado: {status} · Expiración: {expiry}")

    return token

# ════════════════════════════════════════════════════════════════
#  FASE 2 → TV EN VIVO
# ════════════════════════════════════════════════════════════════
def fetch_live_tv(session, token: str) -> list:
    """Extrae todos los canales de TV en vivo con paginación."""
    print("\n📺 FASE 2 · Extrayendo TV en Vivo...")
    channels = []

    # Obtener géneros/categorías
    genres_params = {
        "action":        "get_genres",
        "type":          "itv",
        "JsHttpRequest": "1-xml",
    }
    genres_result = safe_get(session, API_URL, genres_params, token)
    genres = []
    if isinstance(genres_result, list):
        genres = genres_result
    elif isinstance(genres_result, dict):
        genres = genres_result.get("data", [])

    # Añadir género "Todos" para capturar canales sin categoría
    if not any(g.get("id") == "*" for g in genres):
        genres.insert(0, {"id": "*", "title": "All"})

    print(f"  📂 Categorías encontradas: {len(genres)}")

    seen_ids = set()
    for genre in genres:
        genre_id    = genre.get("id", "*")
        genre_title = genre.get("title", "General")
        print(f"  ▸ Categoría [{genre_id}] {genre_title}")

        items = paginated_fetch(session, {
            "action":        "get_ordered_list",
            "type":          "itv",
            "genre":         genre_id,
            "force_ch_link_check": "",
            "fav":           "0",
            "sortby":        "name",
            "JsHttpRequest": "1-xml",
        }, token)

        for ch in items:
            ch_id = ch.get("id", "")
            if ch_id in seen_ids:
                continue
            seen_ids.add(ch_id)

            name    = clean_name(ch.get("name", ch.get("title", "Canal")))
            logo    = ch.get("logo", ch.get("tv_logo", ""))
            cmd     = ch.get("cmd", "")
            lang    = detect_language(f"{name} {genre_title}")

            # Construir la URL del stream
            stream_url = resolve_stream_url(session, token, cmd, "itv", ch_id)

            channels.append({
                "type":       "live",
                "id":         ch_id,
                "name":       name,
                "logo":       logo,
                "url":        stream_url,
                "group":      genre_title,
                "lang":       lang,
                "epg_id":     ch.get("xmltv_id", ch.get("epg_id", "")),
            })

    print(f"  ✅ Total canales en vivo: {len(channels)}")
    return channels

# ════════════════════════════════════════════════════════════════
#  FASE 3 → PELÍCULAS (VOD)
# ════════════════════════════════════════════════════════════════
def fetch_movies(session, token: str) -> list:
    """Extrae todas las películas con metadata completa."""
    print("\n🎬 FASE 3 · Extrayendo Películas (VOD)...")
    movies = []

    # Categorías VOD
    cats_params = {
        "action":        "get_categories",
        "type":          "vod",
        "JsHttpRequest": "1-xml",
    }
    cats_result = safe_get(session, API_URL, cats_params, token)
    cats = []
    if isinstance(cats_result, list):
        cats = cats_result
    elif isinstance(cats_result, dict):
        cats = cats_result.get("data", [])

    if not cats:
        cats = [{"id": "*", "title": "Películas"}]

    print(f"  📂 Categorías VOD: {len(cats)}")

    seen_ids = set()
    for cat in cats:
        cat_id    = cat.get("id", "*")
        cat_title = cat.get("title", cat.get("name", "Películas"))
        print(f"  ▸ Categoría [{cat_id}] {cat_title}")

        items = paginated_fetch(session, {
            "action":        "get_ordered_list",
            "type":          "vod",
            "category":      cat_id,
            "sortby":        "added",
            "fav":           "0",
            "JsHttpRequest": "1-xml",
        }, token)

        for movie in items:
            mid = movie.get("id", "")
            if mid in seen_ids:
                continue
            seen_ids.add(mid)

            name        = clean_name(movie.get("name", movie.get("o_name", "Película")))
            logo        = movie.get("screenshot_uri", movie.get("logo", movie.get("poster", "")))
            description = movie.get("description", movie.get("desc", ""))
            year        = movie.get("year", "")
            director    = movie.get("director", "")
            actors      = movie.get("actors", movie.get("cast", ""))
            rating      = movie.get("rating_imdb", movie.get("rating", ""))
            duration    = movie.get("time", movie.get("duration", ""))
            genres_m    = movie.get("genres_str", movie.get("genre", ""))
            cmd         = movie.get("cmd", "")
            lang        = detect_language(f"{name} {cat_title}")

            stream_url  = resolve_stream_url(session, token, cmd, "vod", mid)

            movies.append({
                "type":        "movie",
                "id":          mid,
                "name":        name,
                "logo":        logo,
                "url":         stream_url,
                "group":       cat_title,
                "lang":        lang,
                "description": description,
                "year":        year,
                "director":    director,
                "actors":      actors,
                "rating":      rating,
                "duration":    duration,
                "genres":      genres_m,
            })

    print(f"  ✅ Total películas: {len(movies)}")
    return movies

# ════════════════════════════════════════════════════════════════
#  FASE 4 → SERIES (Rastreo Profundo: Serie→Temporada→Episodio)
# ════════════════════════════════════════════════════════════════
def fetch_series(session, token: str) -> list:
    """
    Extrae series con RASTREO PROFUNDO (3 niveles):
      Nivel 1: Categorías de series
      Nivel 2: Series dentro de cada categoría
      Nivel 3: Temporadas → Episodios (con URL directa de stream)
    
    Esto resuelve el problema de que los botones de reproducir no aparezcan:
    solo si llegamos al nivel de EPISODIO individual tenemos la URL real del stream.
    """
    print("\n📺 FASE 4 · Extrayendo Series (rastreo profundo 3 niveles)...")
    episodes_list = []

    # ── Nivel 1: Categorías de series ─────────────────────────
    cats_params = {
        "action":        "get_categories",
        "type":          "series",
        "JsHttpRequest": "1-xml",
    }
    cats_result = safe_get(session, API_URL, cats_params, token)
    cats = []
    if isinstance(cats_result, list):
        cats = cats_result
    elif isinstance(cats_result, dict):
        cats = cats_result.get("data", [])

    if not cats:
        cats = [{"id": "*", "title": "Series"}]

    print(f"  📂 Categorías de series: {len(cats)}")

    for cat in cats:
        cat_id    = cat.get("id", "*")
        cat_title = cat.get("title", cat.get("name", "Series"))
        print(f"\n  ▸ Categoría: [{cat_id}] {cat_title}")

        # ── Nivel 2: Series dentro de la categoría ─────────────
        series_items = paginated_fetch(session, {
            "action":        "get_ordered_list",
            "type":          "series",
            "category":      cat_id,
            "sortby":        "added",
            "fav":           "0",
            "JsHttpRequest": "1-xml",
        }, token)

        print(f"     📺 Series encontradas: {len(series_items)}")

        for serie in series_items:
            serie_id    = serie.get("id", "")
            serie_name  = clean_name(serie.get("name", serie.get("title", "Serie")))
            serie_logo  = serie.get("screenshot_uri", serie.get("logo", serie.get("poster", "")))
            description = serie.get("description", serie.get("desc", ""))
            year        = serie.get("year", "")
            director    = serie.get("director", "")
            actors      = serie.get("actors", serie.get("cast", ""))
            rating      = serie.get("rating_imdb", serie.get("rating", ""))
            genres_s    = serie.get("genres_str", serie.get("genre", ""))
            lang        = detect_language(f"{serie_name} {cat_title}")

            print(f"     ▸ Serie: {serie_name} (id={serie_id})")

            # ── Nivel 3a: Temporadas ───────────────────────────
            seasons_params = {
                "action":        "get_seasons",
                "type":          "series",
                "series_id":     serie_id,
                "JsHttpRequest": "1-xml",
            }
            seasons_result = safe_get(session, API_URL, seasons_params, token)
            seasons = []
            if isinstance(seasons_result, list):
                seasons = seasons_result
            elif isinstance(seasons_result, dict):
                seasons = seasons_result.get("data", seasons_result.get("seasons", []))

            if not seasons:
                # Algunos portales devuelven los episodios directamente
                seasons = [{"id": "0", "name": "Temporada 1"}]

            print(f"       🎬 Temporadas: {len(seasons)}")

            for season in seasons:
                season_id   = season.get("id", "0")
                season_name = season.get("name", season.get("title", f"Temporada {season_id}"))
                season_num  = season.get("number", season_id)

                # ── Nivel 3b: Episodios de esta temporada ──────
                episodes = paginated_fetch(session, {
                    "action":        "get_ordered_list",
                    "type":          "series",
                    "series_id":     serie_id,
                    "season_id":     season_id,
                    "episode_id":    "0",
                    "fav":           "0",
                    "sortby":        "added",
                    "JsHttpRequest": "1-xml",
                }, token)

                print(f"         📌 {season_name}: {len(episodes)} episodios")

                for ep in episodes:
                    ep_id     = ep.get("id", "")
                    ep_name   = ep.get("name", ep.get("title", f"Episodio {ep_id}"))
                    ep_num    = ep.get("episode_num", ep.get("number", ""))
                    ep_cmd    = ep.get("cmd", "")

                    # ◀◀ Este es el URL real del stream del episodio ▶▶
                    stream_url = resolve_stream_url(session, token, ep_cmd, "series", ep_id)

                    # Construir nombre descriptivo del episodio para M3U
                    ep_full_name = f"{serie_name} · {season_name} · E{ep_num} - {ep_name}"

                    episodes_list.append({
                        "type":        "series",
                        "id":          ep_id,
                        "serie_id":    serie_id,
                        "serie_name":  serie_name,
                        "name":        ep_full_name,
                        "logo":        serie_logo,
                        "url":         stream_url,
                        "group":       f"SERIES · {cat_title}",
                        "lang":        lang,
                        "description": description,
                        "year":        year,
                        "director":    director,
                        "actors":      actors,
                        "rating":      rating,
                        "genres":      genres_s,
                        "season":      str(season_num),
                        "episode":     str(ep_num),
                        "season_name": season_name,
                        "ep_name":     ep_name,
                    })

                time.sleep(0.2)  # pausa cortés entre temporadas
            time.sleep(0.3)      # pausa cortés entre series

    print(f"\n  ✅ Total episodios extraídos: {len(episodes_list)}")
    return episodes_list

# ════════════════════════════════════════════════════════════════
#  RESOLVEDOR DE URLs DE STREAM
# ════════════════════════════════════════════════════════════════
def resolve_stream_url(session, token: str, cmd: str, content_type: str, item_id: str) -> str:
    """
    Resuelve la URL directa del stream (m3u8 o ts) a partir del comando.
    
    Los portales Stalker no dan la URL directa en el listado;
    hay que llamar a 'create_link' para obtener la URL real.
    """
    if not cmd:
        return ""

    # Si el cmd ya es una URL directa, devolverla
    if cmd.startswith("http://") or cmd.startswith("https://"):
        return cmd.strip()

    # Llamar a create_link para obtener la URL real
    create_params = {
        "action":        "create_link",
        "type":          content_type,
        "cmd":           cmd,
        "series":        "0",
        "forced_storage":"undefined",
        "disable_ad":    "0",
        "JsHttpRequest": "1-xml",
    }
    result = safe_get(session, API_URL, create_params, token)
    if not result:
        # Fallback: construir URL manual desde el cmd
        return f"{PORTAL_URL}{cmd}" if not cmd.startswith("/") else f"{PORTAL_URL}{cmd}"

    # La respuesta de create_link tiene el campo 'cmd' con la URL final
    if isinstance(result, dict):
        resolved = result.get("cmd", result.get("url", ""))
        if resolved:
            # A veces viene como "ffrt http://..." → extraer la URL
            url_match = re.search(r'(https?://\S+)', resolved)
            if url_match:
                return url_match.group(1).strip()
            return resolved.strip()

    return ""

# ════════════════════════════════════════════════════════════════
#  GENERADOR M3U
# ════════════════════════════════════════════════════════════════
def generate_m3u(all_items: list) -> str:
    """
    Genera el contenido del archivo M3U con:
    - Separación por tipo (TV Vivo / Películas / Series)
    - group-title con idioma para facilitar filtrado en reproductores
    - tvg-logo con poster
    - Episodios con nombre descriptivo completo
    """
    lines = [
        "#EXTM3U",
        f"# Generado automáticamente: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"# Portal: {PORTAL_URL}",
        f"# Total items: {len(all_items)}",
        "",
    ]

    for item in all_items:
        if not item.get("url"):
            continue  # Sin URL no podemos reproducir

        name     = item.get("name", "Sin nombre")
        logo     = item.get("logo", "")
        url      = item["url"]
        epg_id   = item.get("epg_id", "")
        lang     = item.get("lang", "OTHER")
        itype    = item.get("type", "live")

        # Prefijo de grupo según tipo
        if itype == "live":
            group = f"TV · {item.get('group', 'General')} · {lang}"
        elif itype == "movie":
            group = f"PELICULAS · {item.get('group', 'Películas')} · {lang}"
        elif itype == "series":
            group = f"SERIES · {item.get('group', 'Series')} · {lang}"
        else:
            group = item.get("group", "General")

        # Línea EXTINF enriquecida
        extinf = (
            f'#EXTINF:-1 '
            f'tvg-id="{epg_id}" '
            f'tvg-logo="{logo}" '
            f'group-title="{group}"'
        )

        # Metadata adicional como comentarios para el dashboard
        if itype in ("movie", "series"):
            year      = item.get("year", "")
            director  = item.get("director", "")
            actors    = item.get("actors", "")
            rating    = item.get("rating", "")
            desc      = item.get("description", "")
            if year:     extinf += f' tvg-year="{year}"'
            if director: extinf += f' tvg-director="{director}"'
            if rating:   extinf += f' tvg-rating="{rating}"'

        lines.append(extinf)
        lines.append(name)
        lines.append(url)
        lines.append("")

    return "\n".join(lines)

# ════════════════════════════════════════════════════════════════
#  GENERADOR JSON (para el Dashboard Web)
# ════════════════════════════════════════════════════════════════
def generate_metadata_json(all_items: list) -> str:
    """
    Genera un JSON con toda la metadata para el Dashboard HTML.
    El dashboard carga este JSON y muestra posters, sinopsis, filtros, etc.
    """
    metadata = {
        "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "portal": PORTAL_URL,
        "total": len(all_items),
        "items": all_items,
    }
    return json.dumps(metadata, ensure_ascii=False, indent=2)

# ════════════════════════════════════════════════════════════════
#  GENERADOR DE ESTADÍSTICAS
# ════════════════════════════════════════════════════════════════
def generate_stats(all_items: list) -> dict:
    live    = [i for i in all_items if i["type"] == "live"]
    movies  = [i for i in all_items if i["type"] == "movie"]
    series  = [i for i in all_items if i["type"] == "series"]

    # Agrupar series por nombre de serie (no por episodio)
    unique_series = set(i.get("serie_name", "") for i in series)

    langs = {}
    for item in all_items:
        lang = item.get("lang", "OTHER")
        langs[lang] = langs.get(lang, 0) + 1

    return {
        "live_channels": len(live),
        "movies":        len(movies),
        "series":        len(unique_series),
        "episodes":      len(series),
        "languages":     langs,
        "total":         len(all_items),
    }

# ════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA PRINCIPAL
# ════════════════════════════════════════════════════════════════
def main():
    print("=" * 65)
    print("  🚀 Stalker MAC Portal → M3U Scraper")
    print(f"  📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 65)

    session = requests.Session()
    session.verify = False  # Algunos portales usan SSL autofirmado

    # ── FASE 1: Autenticación ──────────────────────────────────
    token = authenticate(session)
    if not token:
        print("\n❌ AUTENTICACIÓN FALLIDA · Abortando.")
        print("   Verifica: URL del portal, MAC address y estado del servidor.")
        sys.exit(1)

    all_items = []

    # ── FASE 2: TV en Vivo ─────────────────────────────────────
    try:
        live_channels = fetch_live_tv(session, token)
        all_items.extend(live_channels)
    except Exception as e:
        print(f"\n⚠  Error en TV en Vivo: {e}")

    # ── FASE 3: Películas ─────────────────────────────────────
    try:
        movies = fetch_movies(session, token)
        all_items.extend(movies)
    except Exception as e:
        print(f"\n⚠  Error en Películas: {e}")

    # ── FASE 4: Series (rastreo profundo) ─────────────────────
    try:
        episodes = fetch_series(session, token)
        all_items.extend(episodes)
    except Exception as e:
        print(f"\n⚠  Error en Series: {e}")

    # ── Estadísticas ───────────────────────────────────────────
    stats = generate_stats(all_items)
    print("\n" + "=" * 65)
    print("  📊 RESUMEN FINAL")
    print("=" * 65)
    print(f"  📺 Canales en vivo : {stats['live_channels']}")
    print(f"  🎬 Películas        : {stats['movies']}")
    print(f"  📺 Series únicas    : {stats['series']}")
    print(f"  📌 Episodios        : {stats['episodes']}")
    print(f"  🌍 Idiomas detectados:")
    for lang, count in sorted(stats["languages"].items(), key=lambda x: -x[1]):
        print(f"     {lang:8s}: {count}")
    print(f"  📁 TOTAL ITEMS      : {stats['total']}")
    print("=" * 65)

    if not all_items:
        print("\n⚠  No se extrajeron items. Verifica el portal y el MAC address.")
        sys.exit(1)

    # ── Guardar playlist.m3u ───────────────────────────────────
    m3u_content = generate_m3u(all_items)
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"\n✅ playlist.m3u guardado ({len(m3u_content):,} bytes)")

    # ── Guardar metadata.json (para el dashboard) ──────────────
    json_content = generate_metadata_json(all_items)
    with open("metadata.json", "w", encoding="utf-8") as f:
        f.write(json_content)
    print(f"✅ metadata.json guardado ({len(json_content):,} bytes)")

    # ── Guardar stats.json ─────────────────────────────────────
    stats["generated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    stats["portal"]    = PORTAL_URL
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print("✅ stats.json guardado")

    print("\n🎉 ¡Proceso completado con éxito!")
    print(f"   Tu URL M3U: https://raw.githubusercontent.com/naimmeliana-prog/conversor_metrico/main/playlist.m3u")
    print(f"   Dashboard : https://naimmeliana-prog.github.io/conversor_metrico/")


if __name__ == "__main__":
    main()
