# -*- mode: python ; coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Especificación de PyInstaller para "Software Matemático IA".
#
# Genera una CARPETA con el ejecutable y sus librerías (modo "onedir"): con Qt, OpenCV,
# onnxruntime y los modelos, un solo .exe ("onefile") tendría que descomprimirse entero
# cada vez que se abre y tardaría mucho más en arrancar.
#
# Comando de build:
#   pyinstaller SoftwareMatematicoIA.spec --noconfirm
#
# Salida: dist/SoftwareMatematicoIA/SoftwareMatematicoIA.exe
#
# NOTAS:
#   - images/ y models/ se incluyen como recursos (carpeta _internal).
#   - El archivo .env NO se embebe: se lee desde la carpeta del ejecutable
#     (utils/config.py usa ruta_base()). Copie su .env junto al .exe.
#   - La base de datos software_matematico.db se lee/crea junto al ejecutable:
#     copie la de database/ ahí para conservar las cuentas ya registradas.
#   - UPX desactivado: comprimir las DLL de TensorFlow, Qt u onnxruntime las corrompe.
#   - El entorno virtual necesita venv/Lib/site-packages/sitecustomize.py, que precarga el
#     msvcp140.dll del sistema (como main.py): sin él, el análisis de PyInstaller se cae al
#     importar onnxruntime después de PyQt5. Ver tools/sitecustomize.py.
# ---------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = [("images", "images"), ("models", "models")]
binaries = []
hiddenimports = [
    "onnxruntime",
    "ai_edge_litert.interpreter",
    "sounddevice",
    "vosk",
    "interfaces.escaneo_tm",
    "interfaces.ingreso_tm",
    "services.modelos_tm",
    "matplotlib",
    "numpy",
    "mpl_toolkits.mplot3d",
    "matplotlib.backends.backend_qtagg",
    "interfaces.calculadora",
    "logic.calculadora_logic",
    "utils.dialogo_ajustes_ia",
]

# Librerías nativas (DLL) y datos que el análisis estático no encuentra. Solo se recogen
# archivos, sin importar todos los submódulos: herramientas como onnxruntime.quantization
# no se usan y su importación revienta el análisis.
for paquete in ("ai_edge_litert", "onnxruntime", "vosk", "_sounddevice_data"):
    binaries += collect_dynamic_libs(paquete)
    datas += collect_data_files(paquete)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Todos los modelos corren con onnxruntime, LiteRT, OpenCV o NumPy: TensorFlow/Keras
        # solo se usan para convertir modelos (tools/) y no van en el ejecutable.
        "tensorflow",
        "tf_keras",
        "keras",
        "tensorboard",
        "tf2onnx",
        "torch",
        "onnx",
        "onnxruntime.quantization",
        "onnxruntime.transformers",
        "onnxruntime.tools",
        "ai_edge_litert.aot",
        "pandas",
        "IPython",
        "notebook",
        "pytest",
        "tkinter",
        "PyQt5.QtWebEngineCore",
        "PyQt5.QtWebEngineWidgets",
        "PyQt5.QtWebEngineQuick",
        "PyQt5.QtWebChannel",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# PyQt5 trae su propio runtime de Visual C++ (14.26) en PyQt5/Qt5/bin. onnxruntime y OpenCV
# necesitan uno más nuevo y, si se carga primero el de Qt, el programa se cae al iniciar
# (0xC0000005). Se quitan esas copias: Qt usa el runtime nuevo que queda en _internal.
_RUNTIME_VIEJO_QT = {"msvcp140.dll", "msvcp140_1.dll", "vcruntime140.dll", "vcruntime140_1.dll"}
a.binaries = [b for b in a.binaries
              if not (b[0].replace("\\", "/").lower().startswith("pyqt5/qt5/bin/")
                      and b[0].replace("\\", "/").rsplit("/", 1)[-1].lower() in _RUNTIME_VIEJO_QT)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SoftwareMatematicoIA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SoftwareMatematicoIA",
)
