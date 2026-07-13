PASO 1 — Preparar el repositorio
Ve a github.com/naimmeliana-prog/conversor_metrico y sube los 5 archivos con la siguiente estructura exacta:

text


conversor_metrico/
├── .github/
│   └── workflows/
│       └── update.yml      ← Crea la carpeta y el archivo
├── scraper.py
├── requirements.txt
├── index.html
└── README.md


PASO 2 — Activar GitHub Pages
Ve a tu repositorio → ⚙️ Settings → Pages
En Source selecciona Deploy from a branch
Branch: main, carpeta: / (root)
Guarda. En ~2 minutos tendrás tu dashboard en: https://naimmeliana-prog.github.io/conversor_metrico/


PASO 3 — Primera ejecución manual
Ve a la pestaña Actions de tu repositorio
Haz clic en "Actualizar Playlist M3U" en el panel izquierdo
Haz clic en el botón "Run workflow" (azul)
Espera (puede tardar 5-60 min según el tamaño del portal)
Verás los archivos playlist.m3u, metadata.json y stats.json aparecer en el repo


PASO 4 — Usar tu URL M3U
Copia esta URL y pégala en tu reproductor favorito:

text

https://raw.githubusercontent.com/naimmeliana-prog/conversor_metrico/main/playlist.m3u
⚠️ Notas técnicas importantes


Sobre la autenticación Stalker
1
 El protocolo define endpoints como `/stalker_portal/server/load.php`, cabeceras requeridas (`X-User-Agent`, `X-User-MAC`) y formatos de respuesta JSON con arrays anidados para categorías, canales y EPG. El scraper usa `/portal.php` que es el endpoint más universal y compatible con la mayoría de portales Stalker.
Sobre los episodios que no se reproducen

8
 En lugar de descargar un archivo `.m3u` con URLs de streams, el reproductor se conecta a una URL de portal e identifica por dirección MAC. El servidor comprueba si esa MAC está autorizada y devuelve la lista de contenido dinámicamente. Las URLs de stream de episodios **no están en el listado inicial**: hay que llamar a `create_link` por cada episodio. El scraper hace exactamente eso en 3 niveles: Serie → Temporada → Episodio → `create_link`.
Sobre el rate-limiting

6
 Si el handshake devuelve "HANDSHAKE SUCCESS" pero la grilla de descubrimiento está en blanco, el portal está limitando activamente la IP de tu servidor. No hagas clic ni refresques; detente y espera exactamente 5 minutos para que expire el enfriamiento de conexión del portal. El scraper incluye pausas de cortesía entre peticiones (`time.sleep`) para evitar esto.
Sobre la actualización automática

9
 Esto depende de con qué frecuencia tu proveedor IPTV actualiza la lista de canales o si tu token de autenticación expira. Si los canales cambian con frecuencia o los tokens expiran rápidamente (por ejemplo, cada 24 horas), la regeneración diaria puede ser necesaria. El workflow está configurado para cada 12 horas como balance óptimo.
