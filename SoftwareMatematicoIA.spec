# -*- mode: python ; coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Especificación de PyInstaller para "Software Matemático IA".
#
# Genera un ejecutable de una sola carpeta/archivo con la interfaz gráfica.
#
# Comando de build:
#   pyinstaller SoftwareMatematicoIA.spec --noconfirm
#
# Salida: dist/SoftwareMatematicoIA.exe
#
# NOTAS:
#   - La carpeta images/ se incluye como recurso dentro del ejecutable.
#   - El archivo .env NO se embebe: se lee desde la carpeta donde esté el
#     ejecutable (utils/config.py usa ruta_base()). El usuario debe copiar
#     su .env junto al .exe con GROUP_API_KEY / GROUP_BASE_URL / GROUP_MODEL.
#   - La base de datos software_matematico.db se crea junto al ejecutable.
# ---------------------------------------------------------------------------

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("images", "images")],
    hiddenimports=[
        "matplotlib",
        "numpy",
        "mpl_toolkits.mplot3d",
        "matplotlib.backends.backend_qtagg",
        "interfaces.calculadora",
        "logic.calculadora_logic",
        "utils.dialogo_ajustes_ia",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pandas",
        "google",
        "scipy",
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

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SoftwareMatematicoIA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/logo.ico',
)
