# Optimizacion de imagenes del sitio

Generado por `scripts/optimizar_imagenes.py`. Los originales de `img/`
**no se modifican**: las versiones optimizadas van a `assets/optimizado/`.

## Peso de la pagina

| | Antes | Despues |
| --- | --- | --- |
| HTML + CSS + JS | 60 KB | 60 KB |
| Imagenes | 16.90 MB | 1.46 MB |
| **Lo que descarga el visitante** | **16.96 MB** | **1.52 MB** |
| `og:image` (solo previews de enlaces, no la descarga el visitante) | — | 111 KB |

Reduccion de la pagina: **91.0%** (15.43 MB menos en imagenes).

## Anchos aplicados

| Grupo | Imagenes | Ancho maximo | Criterio |
| --- | --- | --- | --- |
| Carrusel de galeria | 7 | 1200 px | `.gallery-slide` se pinta a ~680x420 |
| Tarjetas de espacios | 9 | 800 px | `.room-image` se pinta a 443x280 |
| Fondo del hero | 1 | 1920 px | fondo a pantalla completa con overlay |
| Seccion Nosotros | 1 | 1200 px | `.about-image` 766x520 recortada por `object-fit` |

## Detalle por imagen

| Imagen | Grupo | Original | Salida | Peso antes | Peso despues | Ahorro | Ajuste |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PiscGal.webp` | Carrusel de galeria | 4000x2250 | 1200x675 | 370 KB | 35 KB | -90% | no aplicado |
| `TurcGal.webp` | Carrusel de galeria | 8000x4500 | 1200x675 | 1657 KB | 77 KB | -95% | no aplicado |
| `SHumedGal.webp` | Carrusel de galeria | 1600x900 | 1200x675 | 170 KB | 92 KB | -45% | no aplicado |
| `SSecaGal.webp` | Carrusel de galeria | 4000x2250 | 1200x675 | 532 KB | 49 KB | -91% | no aplicado |
| `CocGal.webp` | Carrusel de galeria | 1600x900 | 1200x675 | 106 KB | 60 KB | -44% | no aplicado |
| `BBQGal.webp` | Carrusel de galeria | 4000x2250 | 1200x675 | 1240 KB | 159 KB | -87% | no aplicado |
| `ParqGal.webp` | Carrusel de galeria | 4000x2250 | 1200x675 | 1274 KB | 156 KB | -88% | no aplicado |
| `HabGrid.webp` | Tarjetas de espacios | 900x506 | 800x450 | 54 KB | 34 KB | -38% | no aplicado |
| `PiscGrid.webp` | Tarjetas de espacios | 900x506 | 800x450 | 107 KB | 26 KB | -76% | no aplicado |
| `TurcoGrid.webp` | Tarjetas de espacios | 900x506 | 800x450 | 147 KB | 51 KB | -65% | no aplicado |
| `SHumedGrid.webp` | Tarjetas de espacios | 900x506 | 800x450 | 139 KB | 45 KB | -67% | no aplicado |
| `SSecaGrid.webp` | Tarjetas de espacios | 4000x2250 | 800x450 | 392 KB | 24 KB | -94% | no aplicado |
| `CocGrid.webp` | Tarjetas de espacios | 4000x2250 | 800x450 | 2281 KB | 31 KB | -99% | no aplicado |
| `BBQGrid.webp` | Tarjetas de espacios | 4000x2250 | 800x450 | 2562 KB | 49 KB | -98% | no aplicado |
| `ParqGrid.webp` | Tarjetas de espacios | 4000x2250 | 800x450 | 1591 KB | 94 KB | -94% | no aplicado |
| `ECafeGrid.jpg` | Tarjetas de espacios | 4000x2250 | 800x450 | 1764 KB | 34 KB | -98% | no aplicado |
| `Hero.webp` | Fondo del hero | 4000x2250 | 1920x1080 | 2160 KB | 121 KB | -94% | no aplicado |
| `Naturaleza.webp` | Seccion Nosotros | 2268x4032 | 1200x2133 | 756 KB | 363 KB | -52% | no aplicado |

## Nota sobre el color

El script no sube la saturacion por defecto. Mide la saturacion de la imagen ya
redimensionada y la compara con la misma imagen despues de codificarla a WebP.
Solo si el encoder pierde mas de un 2% aplica una compensacion parcial y acotada
(maximo +10%), y verifica que efectivamente recupere color antes de guardarla.

**No se aplico ningun ajuste de color**: la perdida de saturacion tras codificar a WebP quedo por debajo del 2% en las 18 imagenes, asi que subir la saturacion solo habria inventado color que la foto no tenia.

## og:image

`assets/og-image.jpg` (1200x630, formato Open Graph 1.91:1),
recortada del hero optimizado. Se usa JPEG y no WebP porque WhatsApp y algunas
redes antiguas no aceptan WebP como imagen de previsualizacion.

## Lazy loading

- **Hero: no.** Es el elemento mas grande de la primera pantalla (LCP). Ademas se
  carga desde CSS (`.hero-background`), donde el atributo `loading` no existe.
- **Carrusel: solo desde la 3a imagen.** Las dos primeras quedan visibles al entrar
  a la seccion; el resto se carga con `loading="lazy"`.
- **Tarjetas de espacios, Nosotros y Contacto: si.** Estan bajo el pliegue.

## Como regenerar

```bash
python scripts/optimizar_imagenes.py
```
