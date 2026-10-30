# Precarga el msvcp140.dll del sistema en todo proceso de Python de este entorno (igual que
# main.py). PyQt5 trae una copia antigua; si se carga primero, onnxruntime y TensorFlow se
# caen al iniciar. Necesario para que PyInstaller pueda analizar el proyecto.
import os
import sys

if sys.platform == "win32":
    import ctypes
    try:
        ctypes.WinDLL(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "msvcp140.dll"))
    except OSError:
        pass
