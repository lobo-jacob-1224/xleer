# xleer

> La hermana de `xkill`, con puntería: congela la pantalla, pinchas un texto y la voz de Álvaro lo lee.

**xleer** lee en voz alta **cualquier texto que se vea en pantalla** —una web, un PDF, un terminal, una imagen—, aunque no se pueda seleccionar. Hace una captura, extrae el texto con OCR ([Tesseract](https://github.com/tesseract-ocr/tesseract)) y lo dice con la voz neuronal española `es-ES-AlvaroNeural` ([edge-tts](https://github.com/rany2/edge-tts)).

| Gesto | Qué hace |
|---|---|
| **Clic** sobre un texto | Lee ese párrafo y todo lo que sigue debajo, en su misma columna. Después baja la página con la rueda y sigue leyendo lo nuevo hasta que mueves el ratón. |
| **Arrastrar** un recuadro | Lee exactamente lo que hay dentro. |
| **Esc** o clic derecho | Cancela. |
| Lanzar `xleer` otra vez | Si Álvaro está hablando, se calla y lee lo nuevo. |

El paquete incluye además `hablar` (dice un texto) y `leer` (lee un `.txt` o un `.pdf`).

## Instalación (Debian y derivadas, sesión X11)

**Descarga directa del paquete compilado:** [`descargas/xleer_1.0.0-1_all.deb`](descargas/xleer_1.0.0-1_all.deb) (también en la [última versión](https://github.com/lobo-jacob-1224/xleer/releases/latest)). Desde la terminal:

```bash
wget https://github.com/lobo-jacob-1224/xleer/raw/main/descargas/xleer_1.0.0-1_all.deb
wget https://github.com/lobo-jacob-1224/xleer/raw/main/descargas/SHA256SUMS
sha256sum -c SHA256SUMS                 # opcional: comprobar la descarga
sudo apt install ./xleer_1.0.0-1_all.deb
```

`apt` instala solo las dependencias (Python, Tk, Pillow, `mpv`, `maim`, `xdotool`, `x11-utils`, `tesseract-ocr` con español e inglés y las librerías de `edge-tts`). Desinstalar: `sudo apt remove xleer`.

## Uso

```bash
xleer                         # la cruz: clic en un texto o arrastra un recuadro
hablar "Hola, mundo"          # dice el texto
cat notas.txt | hablar        # o lo lee de la entrada estándar
leer libro.pdf                # lee un .txt o un .pdf (pdf necesita poppler-utils)
xleer --solo-texto            # no habla, solo imprime lo que lee
```

Hay una entrada **xleer** en el menú de aplicaciones (Utilidades / Accesibilidad). Más detalle en `man xleer`.

## Cómo funciona

```
xleer ─► maim: captura ─► ventana Tk congelada con la cruz ─► clic o recuadro
      ─► xdotool + xwininfo: ventana que hay bajo el ratón
      ─► tesseract (spa+eng, imagen ×3, rama para fondos oscuros) ─► palabras con su posición
      ─► agrupa en filas, columnas y párrafos ─► texto
      ─► hablar.py ─► edge-tts (es-ES-AlvaroNeural) ─► mp3 ─► mpv
```

El código está en [`src/`](src): `xleer.py` (captura, OCR, agrupado en párrafos y «seguir leyendo») y `hablar.py` (voz y reproducción).

## Privacidad

- **El texto que lees se envía al servicio en línea de Microsoft Edge** a través de `edge-tts`: sin conexión no hay voz.
- `~/.local/state/xleer/xleer.log` guarda errores y los **primeros 300 caracteres de cada lectura**, sin rotación. Se puede borrar sin problema.

## Límites conocidos

- Solo **X11**: `maim`, `xdotool` y `xwininfo` son herramientas de X11. En Wayland no se ha probado.
- El OCR se equivoca con letra muy pequeña, fondos con ruido o poco contraste.
- La captura es de toda la pantalla; el comportamiento con varios monitores no se ha comprobado.
- La parte gráfica (la cruz, la detección de la ventana, el desplazamiento automático) y el audio no tienen pruebas automáticas: necesitan pantalla y sonido reales.
- El audio temporal usa un nombre fijo en `/tmp` (`hablar_alvaro.mp3`).

## Desarrollo

```bash
make test     # 11 pruebas unitarias, sin pantalla ni audio
make deb      # construye dist/xleer_*_all.deb
make check    # lo anterior + lintian + prueba del paquete sin instalarlo
```

Las pruebas con OCR usan una imagen sintética y se omiten si falta Tesseract en español o la fuente DejaVu. Comprobado en Debian 14 («forky», testing) con Python 3.14, Pillow 13 y Tesseract 5.5.

`edge-tts` no está en Debian: va dentro del paquete (`/usr/lib/xleer/vendor`) con versión y huella fijadas en [`packaging/build-deb.sh`](packaging/build-deb.sh).

## Windows

Existe código para Windows (captura con `ImageGrab`, ventana con la API de Windows, reproducción con MCI y `tesseract.exe` empaquetado), pero es **experimental y no está validado**: no se publica ningún `.exe`. Estado detallado en [`docs/windows.md`](docs/windows.md).

## Licencia

Aún sin licencia: el autor no ha elegido una, así que, hasta entonces, todos los derechos están reservados. `edge-tts` (incluido en el paquete) es LGPL-3.0.

## Autor

Jacobo Cánovas García.
