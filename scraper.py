#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   Stalker MAC Portal → M3U Auto-Updater + Metadata Scraper      ║
║   Portal: http://mag.greatott.me:80                              ║
║   Soporta: TV en Vivo / Películas / Series (con episodios)       ║
║   Incluye: Detección de idioma + país, paginación automática     ║
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
#  CONFIGURACIÓN DEL PORTAL
# ════════════════════════════════════════════════════════════════
PORTAL_URL  = os.environ.get("PORTAL_URL",  "http://mag.greatott.me:80")
MAC_ADDRESS = os.environ.get("MAC_ADDRESS", "00:1A:79:74:B1:B9")

PORTAL_PATH = "/portal.php"
PORTAL_C    = "/stalker_portal/c/"
API_URL     = PORTAL_URL + PORTAL_PATH

DEVICE_ID   = hashlib.md5(MAC_ADDRESS.encode()).hexdigest()[:13].upper()
DEVICE_ID2  = hashlib.sha256(MAC_ADDRESS.encode()).hexdigest()[:13].upper()
SERIAL_NUM  = DEVICE_ID
SIGNATURE   = hashlib.md5((MAC_ADDRESS + DEVICE_ID).encode()).hexdigest()

# Tamaños de página a probar (de mayor a menor)
PAGE_SIZES_TO_TRY = [500, 250, 100, 50, 14]
OPTIMAL_PAGE_SIZE = 14   # se sobreescribe en main()

REQUEST_TIMEOUT = 30
MAX_RETRIES     = 3
RETRY_DELAY     = 5

# ════════════════════════════════════════════════════════════════
#  DETECCIÓN DE IDIOMA
# ════════════════════════════════════════════════════════════════
LANGUAGE_KEYWORDS = {
    "ES": ["ES","ESP","ESPAÑOL","SPANISH","SPAIN","ESPANA","CASTELLANO",
           "LATINO","LAT","SPA"],
    "FR": ["FR","FRE","FRENCH","FRANCE","FRANÇAIS","FRANCAIS","FRA"],
    "EN": ["EN","ENG","ENGLISH","UK","US","USA","GB","GBR","UHD UK",
           "UNITED KINGDOM"],
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
    # ── EUROPA ────────────────────────────────────────────────
    "ES": {
        "flag": "🇪🇸", "name": "España",
        "keywords": [
            "ESPAÑA","SPAIN","ESPANA","TVE","ANTENA 3","CUATRO",
            "LA SEXTA","TELECINCO","CANAL SUR","TV3","TELEMADRID",
            "ARAGONTV","IB3","ETB","TVG","RTPA","LA 1","LA 2",
            "MOVISTAR+","DMAX ES","GOL TV","REAL MADRID TV",
            "BARÇA TV","BARCA TV","SPAIN HD","SPAIN SD",
        ]
    },
    "FR": {
        "flag": "🇫🇷", "name": "Francia",
        "keywords": [
            "FRANCE","FRANÇAIS","FRANCAIS","TF1","FRANCE 2","FRANCE 3",
            "FRANCE 4","FRANCE 5","M6","W9","TMC","TFX","TEVA","6TER",
            "C8","CSTAR","BFMTV","LCI","CNEWS","ARTE","GULLI","RMC",
            "NRJ12","CHERIE 25","PARIS PREMIERE","COMEDIE",
            "FRANCE HD","FRANCE SD","OCS",
        ]
    },
    "GB": {
        "flag": "🇬🇧", "name": "Reino Unido",
        "keywords": [
            "UK","UNITED KINGDOM","BRITAIN","BRITISH","ENGLAND","BBC",
            "ITV","CHANNEL 4","CHANNEL 5","SKY","BT SPORT","DAVE","E4",
            "MORE4","5USA","5STAR","GOLD","ALIBI","W CHANNEL","REALLY",
            "QUEST","YESTERDAY","DRAMA","MOVIES24","UHD UK",
            "SKY ONE","SKY ATLANTIC","SKY CINEMA","SKY SPORTS","TNT SPORTS",
        ]
    },
    "DE": {
        "flag": "🇩🇪", "name": "Alemania",
        "keywords": [
            "GERMANY","GERMAN","DEUTSCHLAND","DEUTSCH","GER","DEU",
            "ARD","ZDF","RTL","SAT.1","SAT1","PRO7","PROSIEBEN","VOX",
            "KABEL1","KABEL EINS","SIXX","DMAX DE","SPORT1","SKY DE",
            "3SAT","ARTE DE","PHOENIX","N24","WELT","MÜNCHEN","BERLIN",
        ]
    },
    "IT": {
        "flag": "🇮🇹", "name": "Italia",
        "keywords": [
            "ITALY","ITALIAN","ITALIA","ITA","RAI","RAI 1","RAI 2",
            "RAI 3","CANALE 5","ITALIA 1","RETE 4","LA7","TV8","NOVE",
            "REAL TIME IT","DMAX IT","CIELO","FOCUS IT","IRIS","MEDIASET",
            "SKY IT","SPORTITALIA","ROMA","MILAN","NAPOLI",
        ]
    },
    "PT": {
        "flag": "🇵🇹", "name": "Portugal",
        "keywords": [
            "PORTUGAL","PORTUGUESE","PORTUGUES","POR","RTP","RTP1",
            "RTP2","SIC","TVI","CMTV","RECORD","SPORTING TV","BENFICA TV",
            "PORTO CANAL","SPORT TV","LISBOA","PORTO",
        ]
    },
    "NL": {
        "flag": "🇳🇱", "name": "Países Bajos",
        "keywords": [
            "NETHERLANDS","DUTCH","HOLLAND","NED","NPO","RTL NL",
            "SBS6","NET5","VERONICA","ZIGGO","NPO 1","NPO 2","NPO 3",
            "RTL 4","RTL 5","RTL 7","RTL 8","AMSTERDAM",
        ]
    },
    "BE": {
        "flag": "🇧🇪", "name": "Bélgica",
        "keywords": [
            "BELGIUM","BELGIQUE","BELGIË","BEL","VRT","RTBF","VTM",
            "CANVAS","EEN","LA UNE","LA DEUX","LA TROIS","PLUG RTL",
            "BE 1","BRUXELLES","BRUSSELS","BRUSSEL","ANTWERP",
        ]
    },
    "CH": {
        "flag": "🇨🇭", "name": "Suiza",
        "keywords": [
            "SWITZERLAND","SWISS","SUISSE","SCHWEIZ","SRF","RTS","RSI",
            "SRF 1","SRF 2","RTS 1","RTS 2","ZURICH","GENEVA","BERN",
        ]
    },
    "PL": {
        "flag": "🇵🇱", "name": "Polonia",
        "keywords": [
            "POLAND","POLISH","POLSKA","POL","TVP","TVN","POLSAT",
            "TVP1","TVP2","TVN 24","POLSAT NEWS","TVP INFO","TVP SPORT",
            "WARSAW","KRAKOW","WROCLAW",
        ]
    },
    "RU": {
        "flag": "🇷🇺", "name": "Rusia",
        "keywords": [
            "RUSSIA","RUSSIAN","RUSSIE","RUS","CHANNEL ONE RU",
            "RUSSIA 1","NTV","REN TV","MATCH TV","MOSCOW","RT ",
        ]
    },
    "UA": {
        "flag": "🇺🇦", "name": "Ucrania",
        "keywords": [
            "UKRAINE","UKRAINIAN","UKRAINA","UKR","1+1","INTER UA",
            "UKRAINE 24","KYIV","KIEV","STB","ICTV",
        ]
    },
    "RO": {
        "flag": "🇷🇴", "name": "Rumanía",
        "keywords": [
            "ROMANIA","ROMANIAN","ROM","PRO TV","ANTENA 1 RO",
            "TVR","DIGI24","KANAL D","B1 TV","BUCHAREST","CLUJ",
        ]
    },
    "TR": {
        "flag": "🇹🇷", "name": "Turquía",
        "keywords": [
            "TURKEY","TURKISH","TURQUIE","TÜRKIYE","TUR","TRT","TRT 1",
            "ATV","SHOW TV","KANAL D TR","FOX TR","STAR TV","ISTANBUL",
            "ANKARA","BEIN SPORTS TR",
        ]
    },
    "GR": {
        "flag": "🇬🇷", "name": "Grecia",
        "keywords": [
            "GREECE","GREEK","GRECIA","GRE","ERT","ANT1","MEGA GR",
            "STAR GR","ATHENS","THESSALONIKI","SKAI","ALPHA TV",
        ]
    },
    "SE": {
        "flag": "🇸🇪", "name": "Suecia",
        "keywords": [
            "SWEDEN","SWEDISH","SVERIGE","SWE","SVT","TV4 SE",
            "KANAL 5","STOCKHOLM","MALMÖ","GÖTEBORG",
        ]
    },
    "NO": {
        "flag": "🇳🇴", "name": "Noruega",
        "keywords": [
            "NORWAY","NORWEGIAN","NORGE","NOR","NRK","TV 2 NO",
            "OSLO","BERGEN","NRK1","NRK2",
        ]
    },
    "DK": {
        "flag": "🇩🇰", "name": "Dinamarca",
        "keywords": [
            "DENMARK","DANISH","DANMARK","DEN","DR","TV2 DK",
            "COPENHAGEN","KOBENHAVN","DR1","DR2",
        ]
    },
    "FI": {
        "flag": "🇫🇮", "name": "Finlandia",
        "keywords": [
            "FINLAND","FINNISH","SUOMI","FIN","YLE","MTV3 FI",
            "HELSINKI","YLE 1","YLE 2",
        ]
    },
    "CZ": {
        "flag": "🇨🇿", "name": "Rep. Checa",
        "keywords": [
            "CZECH","CZECHIA","CESKA","CZE","CT","PRIMA","NOVA CZ",
            "PRAGUE","PRAGA","CT1","CT2",
        ]
    },
    "HU": {
        "flag": "🇭🇺", "name": "Hungría",
        "keywords": [
            "HUNGARY","HUNGARIAN","MAGYARORSZÁG","HUN","DUNA",
            "RTL HU","TV2 HU","BUDAPEST","M1","M2",
        ]
    },
    "HR": {
        "flag": "🇭🇷", "name": "Croacia",
        "keywords": [
            "CROATIA","CROATIAN","HRVATSKA","HRV","HRT","NOVA HR",
            "ZAGREB","RTL HR","HRT 1","HRT 2",
        ]
    },
    "RS": {
        "flag": "🇷🇸", "name": "Serbia",
        "keywords": [
            "SERBIA","SERBIAN","SRBIJA","SRB","RTS","HAPPY TV",
            "BEOGRAD","BELGRADE","PINK TV","B92",
        ]
    },

    # ── AMÉRICAS ──────────────────────────────────────────────
    "US": {
        "flag": "🇺🇸", "name": "USA",
        "keywords": [
            "USA","UNITED STATES","AMERICAN","NBC","CBS","ABC US",
            "FOX US","CNN","MSNBC","CNBC","ESPN","HBO","SHOWTIME",
            "STARZ","FX","AMC","TNT","TBS","DISCOVERY US",
            "HISTORY US","LIFETIME","CARTOON NETWORK","NICKELODEON",
            "MTV US","VH1","BET","COMEDY CENTRAL","SYFY","BRAVO",
            "FOOD NETWORK","HGTV","ANIMAL PLANET","NEW YORK",
            "LOS ANGELES","CHICAGO","MIAMI",
        ]
    },
    "MX": {
        "flag": "🇲🇽", "name": "México",
        "keywords": [
            "MEXICO","MÉXICO","MEXICANO","MEX","TELEVISA","TV AZTECA",
            "CANAL DE LAS ESTRELLAS","AZTECA 7","AZTECA UNO","FORO TV",
            "ONCE TV","CANAL 22","GUADALAJARA","MONTERREY",
        ]
    },
    "AR": {
        "flag": "🇦🇷", "name": "Argentina",
        "keywords": [
            "ARGENTINA","ARGENTINO","ARG","EL TRECE","TELEFE",
            "LA NACION TV","CANAL 9 AR","AMERICA TV AR","TN","C5N",
            "BUENOS AIRES","CORDOBA AR","ROSARIO",
        ]
    },
    "CO": {
        "flag": "🇨🇴", "name": "Colombia",
        "keywords": [
            "COLOMBIA","COLOMBIANO","COL","RCN","CARACOL","CANAL 1 CO",
            "CITY TV","SEÑAL COLOMBIA","BOGOTA","MEDELLIN","CALI",
        ]
    },
    "CL": {
        "flag": "🇨🇱", "name": "Chile",
        "keywords": [
            "CHILE","CHILENO","CHL","TVN","CANAL 13 CL","CHV",
            "MEGA CL","LA RED","24 HORAS","SANTIAGO DE CHILE",
        ]
    },
    "PE": {
        "flag": "🇵🇪", "name": "Perú",
        "keywords": [
            "PERU","PERÚ","PERUANO","PER","LATINA TV","AMERICA TV PE",
            "ATV","LIMA","TRUJILLO","AREQUIPA",
        ]
    },
    "VE": {
        "flag": "🇻🇪", "name": "Venezuela",
        "keywords": [
            "VENEZUELA","VENEZOLANO","VEN","VENEVISION","TELEVEN",
            "GLOBOVISION","CARACAS","MARACAIBO",
        ]
    },
    "BR": {
        "flag": "🇧🇷", "name": "Brasil",
        "keywords": [
            "BRAZIL","BRASIL","BRASILEIRO","BRA","GLOBO","SBT",
            "RECORD BR","BAND","REDETV","GNT","MULTISHOW","SPORTV",
            "SAO PAULO","RIO DE JANEIRO","BRASILIA",
        ]
    },
    "EC": {
        "flag": "🇪🇨", "name": "Ecuador",
        "keywords": [
            "ECUADOR","ECUATORIANO","ECU","ECUAVISA","TC TELEVISION",
            "QUITO","GUAYAQUIL","CANAL UNO EC",
        ]
    },
    "BO": {
        "flag": "🇧🇴", "name": "Bolivia",
        "keywords": [
            "BOLIVIA","BOLIVIANO","BOL","ATB","RED UNO BO",
            "LA PAZ","SANTA CRUZ","COCHABAMBA",
        ]
    },
    "UY": {
        "flag": "🇺🇾", "name": "Uruguay",
        "keywords": [
            "URUGUAY","URUGUAYO","URU","CANAL 4 UY","CANAL 10 UY",
            "MONTEVIDEO","TNU",
        ]
    },
    "PY": {
        "flag": "🇵🇾", "name": "Paraguay",
        "keywords": [
            "PARAGUAY","PARAGUAYO","PAR","SNT","TELEFUTURO",
            "ASUNCION","ASUNCIÓN",
        ]
    },
    "CA": {
        "flag": "🇨🇦", "name": "Canadá",
        "keywords": [
            "CANADA","CANADIAN","CANADIEN","CBC","CTV","GLOBAL TV CA",
            "TORONTO","MONTREAL","VANCOUVER","TSN","SPORTSNET",
        ]
    },

    # ── ORIENTE MEDIO Y NORTE DE AFRICA ───────────────────────
    "MA": {
        "flag": "🇲🇦", "name": "Marruecos",
        "keywords": [
            "MAROC","MOROCCO","MARRUECOS","MAR","2M","SNRT",
            "AL AOULA","ARRABIA","MEDI 1","CASABLANCA","RABAT",
            "FES","MARRAKECH",
        ]
    },
    "DZ": {
        "flag": "🇩🇿", "name": "Argelia",
        "keywords": [
            "ALGERIA","ALGERIE","ARGELIA","ALG","ENTV","DZAIR TV",
            "ALGERIE 3","ALGERIE 5","ALGER","ORAN","CONSTANTINE",
        ]
    },
    "TN": {
        "flag": "🇹🇳", "name": "Túnez",
        "keywords": [
            "TUNISIA","TUNISIE","TUNEZ","TUN","WATANIYA","HANNIBAL TV",
            "NESSMA","TUNIS","SFAX","SOUSSE",
        ]
    },
    "LY": {
        "flag": "🇱🇾", "name": "Libia",
        "keywords": [
            "LIBYA","LIBIA","LBA","AL WATANIYA LY","TRIPOLI","BENGHAZI",
        ]
    },
    "EG": {
        "flag": "🇪🇬", "name": "Egipto",
        "keywords": [
            "EGYPT","EGYPTE","EGIPTO","EGY","NILE TV","CBC EG",
            "AL HAYAH","MBC MASR","ON TV","CAIRO","ALEXANDRIA","MASPERO",
        ]
    },
    "SA": {
        "flag": "🇸🇦", "name": "Arabia Saudí",
        "keywords": [
            "SAUDI","ARABIA SAUDI","KSA","MBC","ROTANA","AL ARABIYA",
            "SBC","RIYADH","JEDDAH","MECCA","MEDINA","MBC 1","MBC 2",
            "MBC 3","MBC 4","MBC ACTION","MBC DRAMA","MBC MAX",
        ]
    },
    "AE": {
        "flag": "🇦🇪", "name": "Emiratos",
        "keywords": [
            "UAE","EMIRATOS","EMIRATES","DUBAI","ABU DHABI","SHARJAH",
            "AD SPORTS","DUBAI TV","ABU DHABI TV",
        ]
    },
    "QA": {
        "flag": "🇶🇦", "name": "Qatar",
        "keywords": [
            "QATAR","QAT","AL JAZEERA","BEIN SPORTS","DOHA","BEINSPORTS",
        ]
    },
    "KW": {
        "flag": "🇰🇼", "name": "Kuwait",
        "keywords": [
            "KUWAIT","KUW","KTV","SCOPE TV","KUWAIT TV","AL RAI KW",
        ]
    },
    "LB": {
        "flag": "🇱🇧", "name": "Líbano",
        "keywords": [
            "LEBANON","LIBAN","LIBANO","LIB","LBC","MTV LIBAN",
            "AL JADEED","OTV LB","BEIRUT","FUTURE TV",
        ]
    },
    "IQ": {
        "flag": "🇮🇶", "name": "Irak",
        "keywords": [
            "IRAQ","IRAK","IRQ","IRAQIA","AL IRAQIA","BAGHDAD",
            "BASRA","KURDISTAN","NRT IQ",
        ]
    },
    "IR": {
        "flag": "🇮🇷", "name": "Irán",
        "keywords": [
            "IRAN","IRANIEN","IRANI","IRN","IRIB","TEHRAN","GEM TV IR",
        ]
    },

    # ── ASIA ──────────────────────────────────────────────────
    "IN": {
        "flag": "🇮🇳", "name": "India",
        "keywords": [
            "INDIA","INDIAN","HINDI","IND","STAR PLUS","ZEE TV","SONY IN",
            "COLORS","SAB TV","STAR SPORTS IN","STAR GOLD","SONY MAX",
            "ZEE CINEMA","SET MAX","AAJTAK","NDTV","BOLLYWOOD",
            "MUMBAI","DELHI","BENGALURU","CHENNAI",
        ]
    },
    "PK": {
        "flag": "🇵🇰", "name": "Pakistán",
        "keywords": [
            "PAKISTAN","PAKISTANI","URDU","PAK","GEO TV","ARY DIGITAL",
            "HUM TV","EXPRESS TV","PTV","KARACHI","LAHORE","ISLAMABAD",
        ]
    },
    "BD": {
        "flag": "🇧🇩", "name": "Bangladesh",
        "keywords": [
            "BANGLADESH","BANGLA","BAN","BTV","ATN BANGLA",
            "CHANNEL I BD","DHAKA","CHITTAGONG",
        ]
    },
    "CN": {
        "flag": "🇨🇳", "name": "China",
        "keywords": [
            "CHINA","CHINESE","CCTV","CHN","CCTV 1","CCTV 4",
            "PHOENIX TV","DRAGON TV","BEIJING","SHANGHAI","MANDARIN",
        ]
    },
    "JP": {
        "flag": "🇯🇵", "name": "Japón",
        "keywords": [
            "JAPAN","JAPANESE","JAPON","JPN","NHK","TV TOKYO",
            "FUJI TV","TBS JP","ANIME","TOKYO JP","OSAKA",
        ]
    },
    "KR": {
        "flag": "🇰🇷", "name": "Corea del Sur",
        "keywords": [
            "KOREA","KOREAN","COREA","KOR","KBS","MBC KR","SBS KR",
            "SEOUL","KDRAMA","K-DRAMA","ARIRANG",
        ]
    },
    "AF": {
        "flag": "🇦🇫", "name": "Afganistán",
        "keywords": [
            "AFGHANISTAN","AFGHAN","AFG","ARIANA TV","TOLO TV",
            "KABUL","PASHTO",
        ]
    },

    # ── AFRICA SUBSAHARIANA ────────────────────────────────────
    "NG": {
        "flag": "🇳🇬", "name": "Nigeria",
        "keywords": [
            "NIGERIA","NIGERIAN","NGA","CHANNELS TV","NTA","TVC NG",
            "LAGOS","ABUJA","NOLLYWOOD","ARISE TV",
        ]
    },
    "GH": {
        "flag": "🇬🇭", "name": "Ghana",
        "keywords": [
            "GHANA","GHANAIAN","GHA","GTV","TV3 GH","ACCRA",
            "KUMASI","JOY TV GH",
        ]
    },
    "SN": {
        "flag": "🇸🇳", "name": "Senegal",
        "keywords": [
            "SENEGAL","SENEGALAIS","SEN","RTS SN","2STV","DAKAR SN",
        ]
    },
    "ZA": {
        "flag": "🇿🇦", "name": "Sudáfrica",
        "keywords": [
            "SOUTH AFRICA","SUDAFRICA","RSA","SABC","DSTV","ETV ZA",
            "JOHANNESBURG","CAPE TOWN","DURBAN",
        ]
    },
    "CM": {
        "flag": "🇨🇲", "name": "Camerún",
        "keywords": [
            "CAMEROUN","CAMEROON","CMR","CRTV","YAOUNDÉ","DOUALA",
        ]
    },
    "CI": {
        "flag": "🇨🇮", "name": "Costa de Marfil",
        "keywords": [
            "COTE D'IVOIRE","IVORY COAST","ABIDJAN","RTI CI",
        ]
    },

    # ── INTERNACIONAL ─────────────────────────────────────────
    "INTL": {
        "flag": "🌍", "name": "Internacional",
        "keywords": [
            "INTERNATIONAL","INTERNACIONAL","EUROSPORT","EURONEWS",
            "AL JAZEERA ENGLISH","BBC WORLD","CNN INTERNATIONAL",
            "BLOOMBERG","DISCOVERY CHANNEL","NATIONAL GEOGRAPHIC",
            "HISTORY CHANNEL","ANIMAL PLANET","TRAVEL CHANNEL",
            "MOTORSPORT TV","RED BULL TV",
        ]
    },
}

# ════════════════════════════════════════════════════════════════
#  CABECERAS HTTP
# ════════════════════════════════════════════════════════════════
def build_headers(token: str = "") -> dict:
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
def safe_get(session: requests.Session, url: str, params: dict, token: str):
    headers = build_headers(token)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                url, params=params, headers=headers,
                timeout=REQUEST_TIMEOUT, allow_redirects=True
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("js", data)
        except requests.exceptions.Timeout:
            print(f"  ⚠  Timeout intento {attempt}/{MAX_RETRIES}")
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠  HTTP {e.response.status_code} intento {attempt}/{MAX_RETRIES}")
        except json.JSONDecodeError:
            print(f"  ⚠  Respuesta no es JSON intento {attempt}/{MAX_RETRIES}")
        except Exception as e:
            print(f"  ⚠  Error [{e}] intento {attempt}/{MAX_RETRIES}")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
    return None


def detect_language(text: str) -> str:
    upper = text.upper()
    for lang, keywords in LANGUAGE_KEYWORDS.items():
        for kw in keywords:
            pattern = r'(?:^|[\s|\-_\[\]():,])' + re.escape(kw) + r'(?:$|[\s|\-_\[\]():,])'
            if re.search(pattern, upper):
                return lang
    return "OTHER"


def detect_country(name: str, group: str = "", country_field: str = "") -> str:
    """
    Detecta el país de origen.
    Prioridad:
    1. Campo 'country' directo del portal
    2. Palabras clave en nombre del canal/contenido
    3. Palabras clave en el grupo/categoría
    """
    # Prioridad 1: campo directo del portal
    if country_field:
        upper_cf = country_field.upper().strip()
        for code, data in COUNTRY_KEYWORDS.items():
            if upper_cf == code or upper_cf == data["name"].upper():
                return code

    # Prioridad 2 y 3: palabras clave
    search_text = f"{name} {group}".upper()
    for code, data in COUNTRY_KEYWORDS.items():
        for kw in data["keywords"]:
            if not kw:
                continue
            pattern = r'(?:^|[\s|\-_\[\]():,./+])' + re.escape(kw) + r'(?:$|[\s|\-_\[\]():,./+])'
            if re.search(pattern, search_text):
                return code
    return "OTHER"


def clean_name(name: str) -> str:
    if not name:
        return "Sin nombre"
    return name.strip().replace(",", " -").replace('"', "'")


# ════════════════════════════════════════════════════════════════
#  DETECTOR AUTOMÁTICO DE PAGE_SIZE ÓPTIMO
# ════════════════════════════════════════════════════════════════
def detect_page_size(session: requests.Session, token: str) -> int:
    print("\n🔍 Detectando PAGE_SIZE óptimo del portal...")
    for size in PAGE_SIZES_TO_TRY:
        params = {
            "action":        "get_ordered_list",
            "type":          "itv",
            "genre":         "*",
            "p":             "1",
            "perpage":       str(size),
            "fav":           "0",
            "sortby":        "name",
            "JsHttpRequest": "1-xml",
        }
        result = safe_get(session, API_URL, params, token)
        if not result:
            continue

        if isinstance(result, dict):
            items = result.get("data", [])
            total = int(result.get("total_items", 0))
        elif isinstance(result, list):
            items = result
            total = len(items)
        else:
            continue

        received = len(items)
        print(f"  Probando PAGE_SIZE={size:>4} → recibidos={received:>4} / total={total:>6} → ", end="")

        if received == 0:
            print("❌ Sin datos")
            continue

        if received >= size or received == total:
            print("✅ ACEPTADO")
            print(f"  → PAGE_SIZE óptimo: {size}")
            return size
        else:
            print(f"⚠️  Respuesta parcial, probando menor...")

    print("  → Usando PAGE_SIZE mínimo: 14")
    return 14


# ════════════════════════════════════════════════════════════════
#  PAGINACIÓN AUTOMÁTICA
# ════════════════════════════════════════════════════════════════
def paginated_fetch(session: requests.Session, params_base: dict, token: str) -> list:
    global OPTIMAL_PAGE_SIZE
    all_items   = []
    page        = 1
    empty_pages = 0
    MAX_EMPTY   = 3

    while True:
        params = {
            **params_base,
            "p":       str(page),
            "perpage": str(OPTIMAL_PAGE_SIZE),
        }
        result = safe_get(session, API_URL, params, token)

        if not result:
            empty_pages += 1
            if empty_pages >= MAX_EMPTY:
                break
            time.sleep(RETRY_DELAY)
            continue

        if isinstance(result, dict):
            items = result.get("data", [])
            total = int(result.get("total_items", 0))
        elif isinstance(result, list):
            items = result
            total = len(items) if page == 1 else len(all_items) + len(items)
        else:
            break

        if not items:
            empty_pages += 1
            if empty_pages >= MAX_EMPTY:
                break
            page += 1
            continue

        empty_pages = 0
        all_items.extend(items)

        pct = (len(all_items) / total * 100) if total > 0 else 0
        print(f"      📄 Pág {page:>3}: +{len(items):>4} │ "
              f"Total: {len(all_items):>5}/{total:<6} │ "
              f"[{'█' * int(pct/5):<20}] {pct:.0f}%")

        if total > 0 and len(all_items) >= total:
            break
        if len(items) < OPTIMAL_PAGE_SIZE:
            break

        page += 1

        if OPTIMAL_PAGE_SIZE >= 500:
            time.sleep(0.1)
        elif OPTIMAL_PAGE_SIZE >= 100:
            time.sleep(0.2)
        else:
            time.sleep(0.4)

    return all_items

# ════════════════════════════════════════════════════════════════
#  FASE 1 → AUTENTICACIÓN
# ════════════════════════════════════════════════════════════════
def authenticate(session: requests.Session):
    print("\n🔐 FASE 1 · Autenticación con el portal...")
    print(f"   Portal  : {PORTAL_URL}")
    print(f"   MAC     : {MAC_ADDRESS}")
    print(f"   DeviceID: {DEVICE_ID}")

    handshake_params = {
        "action":        "handshake",
        "type":          "stb",
        "token":         "",
        "JsHttpRequest": "1-xml",
    }
    result = safe_get(session, API_URL, handshake_params, "")
    if not result:
        print("  ❌ Handshake FALLIDO: no hay respuesta.")
        return None

    token = result.get("token", "")
    if not token:
        print(f"  ❌ Handshake FALLIDO: sin token. Respuesta: {result}")
        return None

    print(f"  ✅ Token obtenido: {token[:20]}...")

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
        print("  ⚠  get_profile sin respuesta; se continúa con el token.")
    else:
        expiry = profile.get("end_date", "Desconocida")
        status = profile.get("status", "?")
        print(f"  ✅ Perfil activado · Estado: {status} · Expiración: {expiry}")

    return token

# ════════════════════════════════════════════════════════════════
#  RESOLVEDOR DE URLs DE STREAM
# ════════════════════════════════════════════════════════════════
def resolve_stream_url(session: requests.Session, token: str,
                       cmd: str, content_type: str, item_id: str) -> str:
    if not cmd:
        return ""
    if cmd.startswith("http://") or cmd.startswith("https://"):
        return cmd.strip()

    create_params = {
        "action":          "create_link",
        "type":            content_type,
        "cmd":             cmd,
        "series":          "0",
        "forced_storage":  "undefined",
        "disable_ad":      "0",
        "JsHttpRequest":   "1-xml",
    }
    result = safe_get(session, API_URL, create_params, token)
    if not result:
        return f"{PORTAL_URL}{cmd}" if cmd.startswith("/") else cmd

    if isinstance(result, dict):
        resolved = result.get("cmd", result.get("url", ""))
        if resolved:
            url_match = re.search(r'(https?://\S+)', resolved)
            if url_match:
                return url_match.group(1).strip()
            return resolved.strip()
    return ""

# ════════════════════════════════════════════════════════════════
#  FASE 2 → TV EN VIVO
# ════════════════════════════════════════════════════════════════
def fetch_live_tv(session: requests.Session, token: str) -> list:
    print("\n📺 FASE 2 · Extrayendo TV en Vivo...")
    channels = []

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

    if not any(g.get("id") == "*" for g in genres):
        genres.insert(0, {"id": "*", "title": "All"})

    print(f"  📂 Categorías: {len(genres)}")
    seen_ids = set()

    for genre in genres:
        genre_id    = genre.get("id", "*")
        genre_title = genre.get("title", "General")
        print(f"  ▸ [{genre_id}] {genre_title}")

        items = paginated_fetch(session, {
            "action":              "get_ordered_list",
            "type":                "itv",
            "genre":               genre_id,
            "force_ch_link_check": "",
            "fav":                 "0",
            "sortby":              "name",
            "JsHttpRequest":       "1-xml",
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
            country = detect_country(
                name,
                genre_title,
                ch.get("country", ch.get("country_code", ""))
            )
            stream_url = resolve_stream_url(session, token, cmd, "itv", ch_id)

            channels.append({
                "type":    "live",
                "id":      ch_id,
                "name":    name,
                "logo":    logo,
                "url":     stream_url,
                "group":   genre_title,
                "lang":    lang,
                "country": country,
                "epg_id":  ch.get("xmltv_id", ch.get("epg_id", "")),
            })

    print(f"  ✅ Total canales en vivo: {len(channels)}")
    return channels

# ════════════════════════════════════════════════════════════════
#  FASE 3 → PELÍCULAS (VOD)
# ════════════════════════════════════════════════════════════════
def fetch_movies(session: requests.Session, token: str) -> list:
    print("\n🎬 FASE 3 · Extrayendo Películas (VOD)...")
    movies = []

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
        print(f"  ▸ [{cat_id}] {cat_title}")

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
            country     = detect_country(
                name,
                cat_title,
                movie.get("country", movie.get("country_code", ""))
            )
            stream_url  = resolve_stream_url(session, token, cmd, "vod", mid)

            movies.append({
                "type":        "movie",
                "id":          mid,
                "name":        name,
                "logo":        logo,
                "url":         stream_url,
                "group":       cat_title,
                "lang":        lang,
                "country":     country,
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
def fetch_series(session: requests.Session, token: str) -> list:
    print("\n📺 FASE 4 · Extrayendo Series (rastreo profundo 3 niveles)...")
    episodes_list = []

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

        # Nivel 2: Series
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
            country     = detect_country(
                serie_name,
                cat_title,
                serie.get("country", serie.get("country_code", ""))
            )

            print(f"     ▸ Serie: {serie_name} (id={serie_id})")

            # Nivel 3a: Temporadas
            seasons_result = safe_get(session, API_URL, {
                "action":        "get_seasons",
                "type":          "series",
                "series_id":     serie_id,
                "JsHttpRequest": "1-xml",
            }, token)

            seasons = []
            if isinstance(seasons_result, list):
                seasons = seasons_result
            elif isinstance(seasons_result, dict):
                seasons = seasons_result.get("data", seasons_result.get("seasons", []))

            if not seasons:
                seasons = [{"id": "0", "name": "Temporada 1"}]

            print(f"       🎬 Temporadas: {len(seasons)}")

            for season in seasons:
                season_id   = season.get("id", "0")
                season_name = season.get("name", season.get("title", f"Temporada {season_id}"))
                season_num  = season.get("number", season_id)

                # Nivel 3b: Episodios
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
                    ep_id    = ep.get("id", "")
                    ep_name  = ep.get("name", ep.get("title", f"Episodio {ep_id}"))
                    ep_num   = ep.get("episode_num", ep.get("number", ""))
                    ep_cmd   = ep.get("cmd", "")

                    stream_url   = resolve_stream_url(session, token, ep_cmd, "series", ep_id)
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
                        "country":     country,
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

                time.sleep(0.2)
            time.sleep(0.3)

    print(f"\n  ✅ Total episodios: {len(episodes_list)}")
    return episodes_list

# ════════════════════════════════════════════════════════════════
#  GENERADOR M3U
# ════════════════════════════════════════════════════════════════
def generate_m3u(all_items: list) -> str:
    lines = [
        "#EXTM3U",
        f"# Generado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"# Portal: {PORTAL_URL}",
        f"# Total items: {len(all_items)}",
        "",
    ]

    for item in all_items:
        if not item.get("url"):
            continue

        name    = item.get("name", "Sin nombre")
        logo    = item.get("logo", "")
        url     = item["url"]
        epg_id  = item.get("epg_id", "")
        lang    = item.get("lang", "OTHER")
        country = item.get("country", "OTHER")
        itype   = item.get("type", "live")

        if itype == "live":
            group = f"TV · {item.get('group','General')} · {lang} · {country}"
        elif itype == "movie":
            group = f"PELICULAS · {item.get('group','Películas')} · {lang} · {country}"
        else:
            group = f"SERIES · {item.get('group','Series')} · {lang} · {country}"

        extinf = (
            f'#EXTINF:-1 '
            f'tvg-id="{epg_id}" '
            f'tvg-logo="{logo}" '
            f'group-title="{group}"'
        )

        if itype in ("movie", "series"):
            year     = item.get("year", "")
            director = item.get("director", "")
            rating   = item.get("rating", "")
            if year:     extinf += f' tvg-year="{year}"'
            if director: extinf += f' tvg-director="{director}"'
            if rating:   extinf += f' tvg-rating="{rating}"'

        lines.append(extinf)
        lines.append(name)
        lines.append(url)
        lines.append("")

    return "\n".join(lines)

# ════════════════════════════════════════════════════════════════
#  GENERADOR JSON (para el Dashboard)
# ════════════════════════════════════════════════════════════════
def generate_metadata_json(all_items: list) -> str:
    metadata = {
        "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "portal":    PORTAL_URL,
        "total":     len(all_items),
        "items":     all_items,
    }
    return json.dumps(metadata, ensure_ascii=False, indent=2)

# ════════════════════════════════════════════════════════════════
#  ESTADÍSTICAS
# ════════════════════════════════════════════════════════════════
def generate_stats(all_items: list) -> dict:
    live   = [i for i in all_items if i["type"] == "live"]
    movies = [i for i in all_items if i["type"] == "movie"]
    series = [i for i in all_items if i["type"] == "series"]
    unique_series = set(i.get("serie_name","") for i in series)

    langs     = {}
    countries = {}
    for item in all_items:
        l = item.get("lang", "OTHER")
        c = item.get("country", "OTHER")
        langs[l]     = langs.get(l, 0) + 1
        countries[c] = countries.get(c, 0) + 1

    return {
        "live_channels": len(live),
        "movies":        len(movies),
        "series":        len(unique_series),
        "episodes":      len(series),
        "languages":     langs,
        "countries":     countries,
        "total":         len(all_items),
    }

# ════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA PRINCIPAL
# ════════════════════════════════════════════════════════════════
def main():
    global OPTIMAL_PAGE_SIZE

    print("=" * 65)
    print("  🚀 Stalker MAC Portal → M3U Scraper")
    print(f"  📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 65)

    session = requests.Session()
    session.verify = False

    # FASE 1: Autenticación
    token = authenticate(session)
    if not token:
        print("\n❌ AUTENTICACIÓN FALLIDA · Abortando.")
        sys.exit(1)

    # Detectar PAGE_SIZE óptimo
    OPTIMAL_PAGE_SIZE = detect_page_size(session, token)
    print(f"\n⚡ Usando PAGE_SIZE = {OPTIMAL_PAGE_SIZE} items/página")

    all_items = []

    # FASE 2: TV en Vivo
    try:
        all_items.extend(fetch_live_tv(session, token))
    except Exception as e:
        print(f"\n⚠  Error en TV en Vivo: {e}")

    # FASE 3: Películas
    try:
        all_items.extend(fetch_movies(session, token))
    except Exception as e:
        print(f"\n⚠  Error en Películas: {e}")

    # FASE 4: Series
    try:
        all_items.extend(fetch_series(session, token))
    except Exception as e:
        print(f"\n⚠  Error en Series: {e}")

    # Estadísticas
    stats = generate_stats(all_items)
    print("\n" + "=" * 65)
    print("  📊 RESUMEN FINAL")
    print("=" * 65)
    print(f"  📺 Canales en vivo : {stats['live_channels']}")
    print(f"  🎬 Películas        : {stats['movies']}")
    print(f"  📺 Series únicas    : {stats['series']}")
    print(f"  📌 Episodios        : {stats['episodes']}")
    print(f"  🌍 Idiomas:")
    for lang, count in sorted(stats["languages"].items(), key=lambda x: -x[1]):
        print(f"     {lang:8s}: {count}")
    print(f"  🌐 Países (top 10):")
    for country, count in sorted(stats["countries"].items(), key=lambda x: -x[1])[:10]:
        print(f"     {country:8s}: {count}")
    print(f"  📁 TOTAL            : {stats['total']}")
    print("=" * 65)

    if not all_items:
        print("\n⚠  No se extrajeron items.")
        sys.exit(1)

    # Guardar archivos
    m3u_content = generate_m3u(all_items)
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"\n✅ playlist.m3u  ({len(m3u_content):,} bytes)")

    json_content = generate_metadata_json(all_items)
    with open("metadata.json", "w", encoding="utf-8") as f:
        f.write(json_content)
    print(f"✅ metadata.json ({len(json_content):,} bytes)")

    stats["generated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    stats["portal"]    = PORTAL_URL
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print("✅ stats.json")

    print("\n🎉 ¡Proceso completado!")
    print(f"   M3U : https://raw.githubusercontent.com/naimmeliana-prog/conversor_metrico/main/playlist.m3u")
    print(f"   Dashboard: https://naimmeliana-prog.github.io/conversor_metrico/")


if __name__ == "__main__":
    main()
