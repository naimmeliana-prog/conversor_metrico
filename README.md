# 📡 Stalker MAC → M3U Auto-Updater

Convierte tu portal MAC Stalker en una playlist M3U auto-actualizable
con dashboard web, filtros por idioma, posters y sinopsis.

## 🎯 Tus URLs M3U para la TV

* **📺 TV en Vivo:** `https://raw.githubusercontent.com/naimmeliana-prog/conversor_metrico/main/playlist_tv.m3u`
* **🎬 Películas:** `https://raw.githubusercontent.com/naimmeliana-prog/conversor_metrico/main/playlist_movies.m3u`
* **📺 Series:** `https://raw.githubusercontent.com/naimmeliana-prog/conversor_metrico/main/playlist_series.m3u`
* **🌐 M3U Global:** `https://raw.githubusercontent.com/naimmeliana-prog/conversor_metrico/main/playlist.m3u`

## 🌐 Dashboard Web
https://naimmeliana-prog.github.io/conversor_metrico/

┌─────────────────────────────────────────────────────────┐
│  📡 Mi IPTV Dashboard         [● Sin configurar] [⚙️]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📡  ¡Bienvenido!                                      │
│      1. Abre ⚙️ Configuración                          │
│      2. Introduce Portal URL + MAC                      │
│      3. Pulsa 🔄 Actualizar                             │
│                                                         │
└─────────────────────────────────────────────────────────┘

Al pulsar ⚙️ Configuración se abre el modal con:
text

┌─────────────────────────────────────────────────────────┐
│  ⚙️ Configuración del Portal                        [✕] │
├─────────────────────────────────────────────────────────┤
│  📡 CREDENCIALES DEL PORTAL MAC                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Portal URL: http://mag.greatott.me:80            │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ MAC: 00:1A:79:74:B1:B9                          │   │
│  └──────────────────────────────────────────────────┘   │
│  [🔌 Probar conexión]                                    │
│                                                         │
│  🐱 CREDENCIALES DE GITHUB                              │
│  ┌─────────────────┐ ┌──────────────────────────────┐   │
│  │ Usuario GitHub  │ │ Nombre del repositorio        │   │
│  └─────────────────┘ └──────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Token PAT: ghp_●●●●●●●●●●●●●●●       [👁️]     │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  🔗 URLS GENERADAS                                      │
│  Dashboard: https://naimmeliana-prog.github.io/...      │
│  M3U URL:   https://raw.githubusercontent.com/...       │
├─────────────────────────────────────────────────────────┤
│  [🗑️ Borrar]    [Cancelar]    [💾 Guardar configuración]│
└─────────────────────────────────────────────────────────┘

Al pulsar 🔄 Actualizar con token configurado:
Llama directamente a la API de GitHub POST /repos/.../actions/workflows/update.yml/dispatches
Pasa el portal_url y mac_address como inputs del workflow
El workflow los usa como variables de entorno en el scraper Python
Muestra barra de progreso y enlace directo a GitHub Actions
Flujo completo de datos:
text

Dashboard (navegador)
    │  Guarda en localStorage
    │  Portal URL + MAC + GitHub Token
    │
    ▼
GitHub API (workflow_dispatch)
    │  Pasa portal_url y mac_address como inputs
    │
    ▼
GitHub Actions (ubuntu-latest)
    │  scraper.py lee PORTAL_URL y MAC_ADDRESS
    │  desde variables de entorno
    │
    ▼
Portal Stalker
    │  Autenticación MAC → Token
    │  Extracción TV/Películas/Series/Episodios
    │
    ▼
GitHub Repository
    │  playlist.m3u + metadata.json + stats.json
    │
    ▼
Dashboard (reload)
    │  Carga metadata.json desde raw.githubusercontent.com
    │  Muestra posters, filtros, sinopsis

## ⚙️ Características
- ✅ 100% gratuito (GitHub Actions + GitHub Pages)
- ✅ Auto-actualización cada 12 horas
- ✅ TV en Vivo / Películas / Series
- ✅ Episodios con rastreo profundo (Serie→Temporada→Episodio)
- ✅ Filtros por idioma (ES, FR, EN, DE, IT, PT, AR...)
- ✅ Posters, sinopsis, año, reparto, rating
- ✅ Dashboard web con buscador
- ✅ 0 dispositivos propios como servidor

## 🚀 Configuración inicial
1. Ve a **Settings → Pages** → Source: `main` branch → `/` (root)
2. Ve a **Actions** → "Actualizar Playlist M3U" → **Run workflow**
3. Espera ~5-30 min (dependiendo del tamaño del portal)
4. Usa la URL M3U en TiviMate, VLC, IPTV Smarters, etc.

## 📱 Compatible con
- TiviMate, OTT Navigator, IPTV Smarters, GSE IPTV
- VLC Media Player, Kodi + PVR IPTV
- Cualquier reproductor con soporte M3U
