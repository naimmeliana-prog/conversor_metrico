#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests, json, time, os, hashlib, re, sys
from datetime import datetime

PORTALS_FILE = "portals.json"
PORTAL_PATH = "/portal.php"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

LANGUAGE_KEYWORDS = {
    "ES": ["ES","ESP","ESPAÑOL","SPANISH","SPAIN","LATINO","LAT","CAST","CASTELLANO"],
    "FR": ["FR","FRE","FRENCH","FRANCE","FRANÇAIS","FRA"],
    "EN": ["EN","ENG","ENGLISH","UK","US","USA","GBR"],
    "DE": ["DE","DEU","GERMAN","GERMANY","DEUTSCH"],
    "IT": ["IT","ITA","ITALIAN","ITALY","ITALIANO"],
    "PT": ["PT","POR","PORTUGUESE","PORTUGAL","BRASIL","BR"],
    "AR": ["AR","ARA","ARABIC","ARABE"],
    "NL": ["NL","NED","DUTCH","HOLLAND"],
    "PL": ["PL","POL","POLISH","POLSKA"],
    "RU": ["RU","RUS","RUSSIAN","ROSSIA"],
    "TR": ["TR","TUR","TURKISH","TÜRKIYE"]
}

# Diccionario reducido para el scraper (el dashboard tiene el completo)
COUNTRY_KEYWORDS = {
    "ES": ["ESPAÑA","SPAIN","TVE","ANTENA 3","TELECINCO","LA SEXTA","CUATRO","MOVISTAR"],
    "FR": ["FRANCE","FRANCAIS","TF1","M6","CANAL+ FR"],
    "GB": ["UK","BBC","ITV","SKY SPORTS","BT SPORT","CHANNEL 4"],
    "US": ["USA","NBC","CBS","ABC US","FOX US","HBO","CNN","ESPN"],
    "MX": ["MEXICO","MÉXICO","TELEVISA","AZTECA"],
    "AR": ["ARGENTINA","TELEFE","EL TRECE","TYC"],
    "CO": ["COLOMBIA","CARACOL","RCN"],
    "CL": ["CHILE","TVN","CHV"],
    "PE": ["PERU","LATINA"],
    "IT": ["ITALIA","RAI","MEDIASET"],
    "PT": ["PORTUGAL","RTP","SIC"],
    "DE": ["GERMANY","ARD","ZDF","RTL DE"]
}

class StalkerPortal:
    def __init__(self, p_cfg):
        self.id, self.name, self.url, self.mac = p_cfg["id"], p_cfg["name"], p_cfg["url"].rstrip("/"), p_cfg["mac"]
        self.color = p_cfg.get("color", "#e94560")
        self.enabled = p_cfg.get("enabled", True)
        self.token = ""
        self.session = requests.Session()
        self.session.verify = False
        self.device_id = hashlib.md5(self.mac.encode()).hexdigest()[:13].upper()

    def safe_get(self, params):
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200",
            "X-User-Agent": "Model: MAG250; Link: WiFi",
            "Cookie": f"mac={self.mac}; stb_lang=en; device_id={self.device_id};",
            "Authorization": f"Bearer {self.token}" if self.token else ""
        }
        for a in range(MAX_RETRIES):
            try:
                r = self.session.get(self.url + PORTAL_PATH, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
                return r.json().get("js", r.json())
            except: time.sleep(2)
        return None

    def authenticate(self):
        res = self.safe_get({"action": "handshake", "type": "stb", "JsHttpRequest": "1-xml"})
        if res and "token" in res:
            self.token = res["token"]
            self.safe_get({"action": "get_profile", "type": "stb", "id": self.mac, "JsHttpRequest": "1-xml"})
            return True
        return False

    def fetch_items(self, itype):
        action = "get_ordered_list"
        items = []
        # Obtenemos categorías
        cats_res = self.safe_get({"action": "get_categories" if itype != "itv" else "get_genres", "type": itype, "JsHttpRequest": "1-xml"})
        cats = cats_res if isinstance(cats_res, list) else cats_res.get("data", []) if isinstance(cats_res, dict) else []
        if not cats: cats = [{"id": "*", "title": "General"}]
        
        for cat in cats:
            p = {"action": action, "type": itype, "JsHttpRequest": "1-xml", "p": 1, "perpage": 100}
            p["category" if itype != "itv" else "genre"] = cat.get("id", "*")
            res = self.safe_get(p)
            data = res.get("data", []) if isinstance(res, dict) else res if isinstance(res, list) else []
            for item in data:
                name = item.get("name", item.get("title", "Unknown"))
                lang = "OTHER"
                for l, kws in LANGUAGE_KEYWORDS.items():
                    if any(re.search(r'\b'+re.escape(k)+r'\b', name.upper()) for k in kws): lang = l; break
                
                ctry = "OTHER"
                for c, kws in COUNTRY_KEYWORDS.items():
                    if any(k in name.upper() for k in kws): ctry = c; break

                items.append({
                    "type": "live" if itype == "itv" else "movie" if itype == "vod" else "series",
                    "id": f"{self.id}_{item.get('id')}",
                    "name": name,
                    "logo": item.get("logo", item.get("tv_logo", item.get("poster", ""))),
                    "url": item.get("cmd", ""),
                    "group": cat.get("title", cat.get("name", "General")),
                    "lang": lang,
                    "country": ctry,
                    "portal_id": self.id,
                    "portal_name": self.name,
                    "portal_color": self.color
                })
        return items

def main():
    if not os.path.exists(PORTALS_FILE): return
    with open(PORTALS_FILE, "r") as f: portals_cfg = json.load(f)
    
    all_items = []
    active_portals = [p for p in portals_cfg if p.get("enabled")]
    
    for p_cfg in active_portals:
        p = StalkerPortal(p_cfg)
        if p.authenticate():
            all_items.extend(p.fetch_items("itv"))
            all_items.extend(p.fetch_items("vod"))
            all_items.extend(p.fetch_items("series"))
            
    with open("metadata.json", "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.now().strftime("%Y-%m-%d %H:%M"), "items": all_items}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__": main()
