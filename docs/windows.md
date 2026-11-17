# xleer en Windows — estado

**Experimental y sin validar. No se publica ningún `.exe`.**

## Qué hay
`src/xleer.py` y `src/hablar.py` tienen ramas para Windows (`sys.platform == "win32"`):

| Función | Linux | Windows |
|---|---|---|
| Captura | `maim` | `PIL.ImageGrab` |
| Ventana bajo el ratón | `xdotool` + `xwininfo` | `user32` (`WindowFromPoint`, `GetAncestor`) + `dwmapi` |
| Posición del ratón y rueda | `xdotool` | `GetCursorPos`, `SetCursorPos`, `mouse_event` |
| OCR | `tesseract` del sistema | `tesseract.exe` junto al programa (carpeta `tesseract/`) |
| Voz | `hablar.py` + `mpv` | en el mismo proceso, con MCI (`winmm`) |
| Registro | `~/.local/state/xleer` | `%LOCALAPPDATA%\xleer` |

## Qué se probó y qué no
- Se compiló un `.exe` de un solo fichero con PyInstaller dentro de **Wine** (Python 3.15, PyInstaller 6.22, Tesseract 5.4 de Windows empaquetado): arrancó y leyó bien una imagen de prueba (`--imagen`).
- **No se validó** la cruz, el clic, la detección de ventana, el desplazamiento ni el audio, ni en Wine ni en Windows. En Wine las pruebas gráficas no fueron fiables (el cursor no iba donde se pedía), y un entorno Wine es demasiado distinto de Windows 11 como para dar por bueno nada.
- Un error real que sí apareció y está corregido en el código: en un `.exe` sin consola `sys.stdout` es `None` y `sys.stdout.flush()` hacía que el programa se cayera al terminar de leer.

## Pendiente
Compilar y probar en **Windows 11**. Con Python, Pillow, edge-tts y PyInstaller instalados y la carpeta `tesseract/` (con `tesseract.exe`, sus DLL y `tessdata/` con `spa`, `eng` y `osd`):

```
py -m PyInstaller --noconfirm --onefile --noconsole --name xleer --paths src --hidden-import hablar --add-data "tesseract;tesseract" src\xleer.py
```

Es la orden que se usó en Wine; en Windows 11 todavía no se ha ejecutado.
