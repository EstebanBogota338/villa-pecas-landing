# Villa Pecas 🏡

Landing page bilingüe para Villa Pecas, villa de lujo para grupos en
Restrepo, Meta (Colombia).

- Español: `/` → `index.html`
- English: `/en/` → `en/index.html`

## Tecnologías

- HTML5, CSS3 y JavaScript sin dependencias
- Responsive y accesible (WCAG AA en contraste y foco)
- Optimización de imágenes con Pillow (`scripts/optimizar_imagenes.py`)

## Arquitectura bilingüe

Son **dos documentos HTML estáticos**, no una inyección por JavaScript. Se
eligió así para que Google indexe el contenido en inglés sin depender de
renderizado y para que la página no pierda LCP ni gane CLS al cambiar de
idioma.

| Pieza | Dónde |
| --- | --- |
| Se declaran como pares | `<link rel="alternate" hreflang>` es / en / x-default en ambas cabeceras |
| Canonical propia | cada versión apunta a sí misma, no a la otra |
| Metadatos | `title`, `description`, `og:*`, `twitter:*` y JSON-LD traducidos por versión |
| Selector de idioma | `<a class="lang-switch">` en el navbar; por debajo de 600 px pasa al menú `.lang-menu-item` |
| Memoria de la elección | `localStorage['villapecas-lang']`; un script en el `<head>` redirige antes de pintar |
| CSS y JS compartidos | `style.css`, `js/main.js` y `js/analytics.js` (rutas `../` desde `/en/`) |

### Mantener las dos versiones

El HTML está duplicado a propósito (es lo que exige el SEO estático). Al
cambiar el contenido hay que tocar **los dos** archivos:

1. Texto visible → `index.html` y `en/index.html`.
2. Texto que solo está en una cabecera (title, description, og, JSON-LD).
3. Anclas (`#inicio`, `#nosotros`, `#espacios`, `#galeria`, `#contacto`):
   los `id` son los mismos en ambas versiones, para que la redirección por
   idioma conserve la sección.
4. Imágenes: las dos páginas comparten `assets/optimizado/` (desde `/en/`
   se referencia con `../assets/`).

## Analítica

`js/analytics.js` carga Google Analytics 4 **solo con consentimiento** del
visitante y envía el evento `click_whatsapp` con el bloque de origen.
Falta sustituir `GA_MEASUREMENT_ID` (`G-XXXXXXXXXX`) por el identificador
real; mientras siga el placeholder no se hace ninguna petición.

## Desarrollo

```bash
# vista local
python -m http.server 8000
# http://localhost:8000/      (español)
# http://localhost:8000/en/   (english)

# regenerar las imágenes optimizadas
python scripts/optimizar_imagenes.py
```

## Despliegue

GitHub Pages publica desde `main`:
<https://estebanbogota338.github.io/villa-pecas-landing/>
