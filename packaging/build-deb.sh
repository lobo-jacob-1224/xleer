#!/usr/bin/env bash
# Construye dist/xleer_<version>_all.deb a partir de este repositorio.
# Necesita: dpkg-deb, curl, python3, gzip. La primera vez necesita red (baja edge-tts de PyPI con huella fijada).
# Uso:  bash packaging/build-deb.sh        (o:  make deb)
set -euo pipefail

RAIZ="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
VERSION="1.0.0-1"
PAQ="xleer"

# edge-tts va dentro del paquete (no esta en Debian). Rueda pura de Python, version y huella fijadas.
EDGE_VERSION="7.3.1"
EDGE_SHA256="2a3c79d6235a7a736d681233823ce5492e829b43eb47beae49aa181237a8f9a4"
EDGE_URL="https://files.pythonhosted.org/packages/35/86/3b97d755992777d5a9ca0e45a8ec96cc9858b2d6dd8f65f3f688d60e8709/edge_tts-${EDGE_VERSION}-py3-none-any.whl"

BUILD="$RAIZ/build"
CACHE="$BUILD/cache"
ARBOL="$BUILD/${PAQ}_${VERSION}_all"
DIST="$RAIZ/dist"
DEBIAN_SRC="$RAIZ/packaging/debian"

head -1 "$DEBIAN_SRC/changelog" | grep -q "^$PAQ ($VERSION) " || { echo "El changelog no corresponde a la version $VERSION"; exit 1; }

mkdir -p "$CACHE" "$DIST"
RUEDA="$CACHE/edge_tts-${EDGE_VERSION}-py3-none-any.whl"
[ -f "$RUEDA" ] || curl -fsSL -o "$RUEDA" "$EDGE_URL"
if ! echo "$EDGE_SHA256  $RUEDA" | sha256sum -c - >/dev/null 2>&1; then
  echo "La huella de edge-tts no coincide con la esperada: no continuo."
  rm -f "$RUEDA"
  exit 1
fi
EXTRAIDO="$CACHE/edge_tts_extraido"
rm -rf "${EXTRAIDO:?}"
python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$RUEDA" "$EXTRAIDO"

rm -rf "${ARBOL:?}"
mkdir -p "$ARBOL"/{DEBIAN,usr/bin,usr/lib/xleer/vendor,usr/share/applications,usr/share/icons/hicolor/scalable/apps,usr/share/doc/xleer,usr/share/man/man1}

# ---------- programa
install -m 0644 "$RAIZ/src/xleer.py"  "$ARBOL/usr/lib/xleer/xleer.py"
install -m 0644 "$RAIZ/src/hablar.py" "$ARBOL/usr/lib/xleer/hablar.py"
cp -r "$EXTRAIDO/edge_tts" "$ARBOL/usr/lib/xleer/vendor/edge_tts"
find "$ARBOL/usr/lib/xleer/vendor" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$ARBOL/usr/lib/xleer/vendor" -type f -exec chmod 0644 {} +
install -m 0644 "$EXTRAIDO/edge_tts-${EDGE_VERSION}.dist-info/licenses/LICENSE" "$ARBOL/usr/share/doc/xleer/LICENSE.edge-tts"

# ---------- comandos, escritorio, icono, manuales
install -m 0755 "$RAIZ/bin/xleer"  "$RAIZ/bin/hablar" "$RAIZ/bin/leer" "$ARBOL/usr/bin/"
install -m 0644 "$RAIZ/data/xleer.desktop" "$ARBOL/usr/share/applications/xleer.desktop"
install -m 0644 "$RAIZ/data/xleer.svg" "$ARBOL/usr/share/icons/hicolor/scalable/apps/xleer.svg"
for m in xleer hablar leer; do
  gzip -9n -c "$RAIZ/man/$m.1" > "$ARBOL/usr/share/man/man1/$m.1.gz"
  chmod 0644 "$ARBOL/usr/share/man/man1/$m.1.gz"
done

# ---------- documentacion
install -m 0644 "$DEBIAN_SRC/copyright" "$DEBIAN_SRC/README.Debian" "$ARBOL/usr/share/doc/xleer/"
gzip -9n -c "$DEBIAN_SRC/changelog" > "$ARBOL/usr/share/doc/xleer/changelog.Debian.gz"
chmod 0644 "$ARBOL/usr/share/doc/xleer/changelog.Debian.gz"

# ---------- control
find "$ARBOL" -type d -exec chmod 0755 {} +
TAM=$(du -sk --exclude=DEBIAN "$ARBOL" | cut -f1)
sed -e "s/@VERSION@/$VERSION/" -e "s/@TAM@/$TAM/" "$DEBIAN_SRC/control.in" > "$ARBOL/DEBIAN/control"
chmod 0644 "$ARBOL/DEBIAN/control"

# ---------- construir y dar la huella
dpkg-deb --root-owner-group --build "$ARBOL" "$DIST/${PAQ}_${VERSION}_all.deb" >/dev/null
( cd "$DIST" && sha256sum "${PAQ}_${VERSION}_all.deb" > SHA256SUMS )
echo "Paquete: $DIST/${PAQ}_${VERSION}_all.deb"
cat "$DIST/SHA256SUMS"
