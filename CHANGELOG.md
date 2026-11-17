# Historial de cambios

## 1.0.0-1 — 2026-11-17

Primera versión publicada, empaquetada a partir del script que el autor usaba en `~/hablar`.

### Añadido
- Paquete Debian `xleer` con los comandos `xleer`, `hablar` y `leer`, entrada de menú, icono y páginas de manual.
- `edge-tts` 7.3.1 incluido en el paquete, con versión y huella (SHA-256) fijadas.
- `xleer --imagen FICHERO`: usa una imagen en vez de capturar la pantalla (para pruebas).
- 11 pruebas unitarias y un script que prueba el `.deb` sin instalarlo.
- Código para Windows (experimental, sin validar; ver `docs/windows.md`).

### Cambiado respecto al script original
- El registro va a `~/.local/state/xleer/xleer.log` (antes, junto al código).
- Ya no depende de un entorno virtual en `~/hablar`: usa el Python del sistema y las librerías de Debian.
- `pkill` con patrones exactos: solo se paran procesos de xleer.
- Compatibilidad con Pillow 14: se sustituye `Image.getdata()`, que está obsoleto, por `get_flattened_data()` cuando existe.
- La cabecera del código y el texto del lanzador de escritorio describen lo que el programa hace de verdad: un clic lee ese párrafo **y lo que sigue debajo**.

### Comprobado
- Con una imagen sintética, el texto leído es idéntico al del script original en los 8 casos probados.
