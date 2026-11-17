#!/usr/bin/env bash
# Prueba el .deb de dist/ SIN instalarlo: lo extrae a una carpeta temporal y ejecuta lo que lleva dentro.
# No captura la pantalla, no habla, no usa la red y no toca tu sistema.
# Uso:  bash packaging/probar-deb.sh        (o:  make check)
set -uo pipefail

RAIZ="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
DEB="$(ls "$RAIZ"/dist/xleer_*_all.deb 2>/dev/null | tail -1)"
[ -n "$DEB" ] || { echo "No hay .deb en dist/: ejecuta antes  make deb"; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP:?}"' EXIT
FALLOS=0
ok()  { printf '  [OK]    %s\n' "$*"; }
mal() { printf '  [FALLA] %s\n' "$*"; FALLOS=$((FALLOS+1)); }

echo "== $(basename "$DEB")"
dpkg-deb -x "$DEB" "$TMP/x"
dpkg-deb -e "$DEB" "$TMP/ctl"
X="$TMP/x"

for f in usr/bin/xleer usr/bin/hablar usr/bin/leer usr/lib/xleer/xleer.py usr/lib/xleer/hablar.py \
         usr/lib/xleer/vendor/edge_tts/__init__.py usr/share/applications/xleer.desktop \
         usr/share/icons/hicolor/scalable/apps/xleer.svg usr/share/man/man1/xleer.1.gz \
         usr/share/doc/xleer/copyright usr/share/doc/xleer/changelog.Debian.gz; do
  [ -e "$X/$f" ] && ok "contiene $f" || mal "falta $f"
done

for s in usr/bin/xleer usr/bin/hablar usr/bin/leer; do
  bash -n "$X/$s" && ok "sintaxis de $s" || mal "sintaxis de $s"
done
python3 -m py_compile "$X/usr/lib/xleer/xleer.py" "$X/usr/lib/xleer/hablar.py" && ok "los .py compilan" || mal "los .py no compilan"
find "$X" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null

command -v desktop-file-validate >/dev/null && { desktop-file-validate "$X/usr/share/applications/xleer.desktop" && ok "xleer.desktop valido" || mal "xleer.desktop no valido"; }

# funcional: lee una imagen sintetica con el xleer.py del paquete (si hay tesseract con spa)
if command -v tesseract >/dev/null && tesseract --list-langs 2>/dev/null | grep -qx spa && [ -e /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf ]; then
  python3 "$RAIZ/tests/imagen_sintetica.py" "$TMP/s.png" >/dev/null
  export XDG_STATE_HOME="$TMP/estado"
  SAL=$(python3 "$X/usr/lib/xleer/xleer.py" --imagen "$TMP/s.png" --punto 700 50 --solo-texto 2>/dev/null)
  case "$SAL" in *"Columna derecha texto distinto"*) ok "xleer.py del paquete lee la imagen de prueba";; *) mal "xleer.py del paquete no leyo bien: $SAL";; esac
  [ -s "$XDG_STATE_HOME/xleer/xleer.log" ] && ok "el registro va a la carpeta de estado, no junto al codigo" || mal "no se creo el registro de estado"
  sed "s#^LIB=/usr/lib/xleer#LIB=$X/usr/lib/xleer#" "$X/usr/bin/xleer" > "$TMP/lanzador.sh"
  SAL=$(bash "$TMP/lanzador.sh" --imagen "$TMP/s.png" --caja 30 180 520 250 --solo-texto 2>/dev/null)
  case "$SAL" in *"Segundo parrafo de la misma columna"*) ok "el lanzador /usr/bin/xleer funciona";; *) mal "el lanzador no leyo bien: $SAL";; esac
else
  echo "  [omitido] prueba funcional: faltan tesseract (spa) o la fuente DejaVu"
fi

echo
[ "$FALLOS" -eq 0 ] && echo "RESULTADO: el paquete esta bien (0 fallos)" || echo "RESULTADO: $FALLOS fallo(s)"
exit "$FALLOS"
