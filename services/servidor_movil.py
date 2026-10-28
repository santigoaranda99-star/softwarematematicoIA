# -*- coding: utf-8 -*-
"""Servidor HTTP móvil integrado para capturar problemas con la cámara del celular.

Permite que el usuario escanee un código QR con su smartphone, abra una página web
optimizada para móviles, tome una foto del problema matemático con la cámara nativa
del teléfono y la envíe directamente a la aplicación de escritorio vía Wi-Fi local.
"""

import base64
import io
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap


def obtener_ip_local():
    """Detecta la dirección IP de la máquina en la red local (Wi-Fi / Ethernet)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Se conecta a una dirección externa arbitraria sin enviar paquetes reales
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()

    # Si es localhost pero hay otra interfaz de red activa
    if ip.startswith("127."):
        try:
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            for candidata in ips:
                if not candidata.startswith("127."):
                    return candidata
        except Exception:
            pass

    return ip


# ==============================================================================
# PÁGINA WEB MÓVIL (HTML5 + CSS3 + JS)
# ==============================================================================
HTML_PAGINA_MOVIL = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Cámara Móvil — Software Matemático IA</title>
    <style>
        :root {
            --primario: #2563EB;
            --primario-hover: #1D4ED8;
            --fondo: #F1F5F9;
            --texto: #0F172A;
            --texto-sec: #64748B;
            --tarjeta: #FFFFFF;
            --borde: #E2E8F0;
            --exito: #10B981;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }
        body {
            background-color: var(--fondo);
            color: var(--texto);
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            padding: 16px;
        }
        .header {
            width: 100%;
            max-width: 480px;
            background: linear-gradient(135deg, #0F2F66, #1E40AF);
            color: white;
            padding: 20px 18px;
            border-radius: 18px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(15, 47, 102, 0.2);
            margin-bottom: 16px;
        }
        .header h1 {
            font-size: 19px;
            font-weight: 800;
            margin-bottom: 4px;
        }
        .header p {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.85);
        }
        .card {
            width: 100%;
            max-width: 480px;
            background: var(--tarjeta);
            border: 1px solid var(--borde);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.04);
            margin-bottom: 14px;
        }
        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 8px;
        }
        .btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 14px;
            font-size: 15px;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .btn-primary {
            background: var(--primario);
            color: white;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }
        .btn-primary:active {
            transform: scale(0.98);
            background: var(--primario-hover);
        }
        .btn-secondary {
            background: #F8FAFC;
            color: #334155;
            border: 1.5px solid #CBD5E1;
        }
        .btn-secondary:active {
            background: #E2E8F0;
        }
        .btn-success {
            background: var(--exito);
            color: white;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            font-size: 16px;
        }
        .preview-container {
            display: none;
            margin-top: 14px;
            text-align: center;
        }
        .preview-img {
            max-width: 100%;
            max-height: 280px;
            border-radius: 12px;
            border: 2px solid var(--primario);
            object-fit: contain;
            background: #000;
        }
        .nota-box {
            margin-top: 14px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .nota-box label {
            font-size: 13px;
            font-weight: 600;
            color: var(--texto-sec);
        }
        .nota-input {
            width: 100%;
            padding: 10px 12px;
            border: 1.5px solid var(--borde);
            border-radius: 10px;
            font-size: 14px;
            outline: none;
        }
        .nota-input:focus {
            border-color: var(--primario);
        }
        .status-box {
            display: none;
            margin-top: 14px;
            padding: 14px;
            border-radius: 12px;
            font-size: 13px;
            text-align: center;
            font-weight: 600;
        }
        .status-loading {
            background: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
        }
        .status-success {
            background: #ECFDF5;
            color: #047857;
            border: 1px solid #A7F3D0;
        }
        .status-error {
            background: #FEF2F2;
            color: #B91C1C;
            border: 1px solid #FECACA;
        }
        .spinner {
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 2px solid rgba(29, 78, 216, 0.2);
            border-radius: 50%;
            border-top-color: #1D4ED8;
            animation: spin 0.8s linear infinite;
            vertical-align: middle;
            margin-right: 8px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .instrucciones {
            font-size: 12px;
            color: var(--texto-sec);
            text-align: center;
            line-height: 1.5;
            margin-top: 8px;
        }
    </style>
</head>
<body>

    <div class="header">
        <h1>📐 Software Matemático IA</h1>
        <p>Captura de problemas con la cámara del celular</p>
    </div>

    <div class="card">
        <input type="file" id="inputCamara" accept="image/*" capture="environment" style="display: none;">
        <input type="file" id="inputGaleria" accept="image/*" style="display: none;">

        <div class="btn-group" id="grupoBotonesCaptura">
            <button class="btn btn-primary" onclick="document.getElementById('inputCamara').click();">
                📸 Tomar Foto del Problema
            </button>
            <button class="btn btn-secondary" onclick="document.getElementById('inputGaleria').click();">
                🖼️ Seleccionar de la Galería
            </button>
        </div>

        <div class="preview-container" id="contenedorPreview">
            <img id="previewImg" class="preview-img" alt="Vista previa">

            <div class="nota-box">
                <label for="txtNota">Nota o pregunta opcional para la IA:</label>
                <input type="text" id="txtNota" class="nota-input" placeholder="Ej: Resolver paso a paso, simplificar...">
            </div>

            <div class="btn-group" style="margin-top: 14px;">
                <button class="btn btn-success" id="btnEnviar" onclick="enviarFoto();">
                    🚀 Enviar a la Computadora
                </button>
                <button class="btn btn-secondary" onclick="resetear();">
                    🔄 Tomar otra foto
                </button>
            </div>
        </div>

        <div id="statusBox" class="status-box"></div>
    </div>

    <div class="card">
        <p class="instrucciones">
            <b>💡 Instrucción:</b> Asegúrate de que el celular y la computadora estén conectados a la misma red Wi-Fi.<br>
            Al enviar la foto, el programa en tu PC la recibirá y comenzará a resolverla automáticamente.
        </p>
    </div>

    <script>
        let imagenBase64 = null;
        let mimeType = 'image/jpeg';

        const inputCamara = document.getElementById('inputCamara');
        const inputGaleria = document.getElementById('inputGaleria');
        const contenedorPreview = document.getElementById('contenedorPreview');
        const previewImg = document.getElementById('previewImg');
        const grupoBotones = document.getElementById('grupoBotonesCaptura');
        const statusBox = document.getElementById('statusBox');
        const btnEnviar = document.getElementById('btnEnviar');

        function procesarArchivo(file) {
            if (!file) return;
            mimeType = file.type || 'image/jpeg';

            const reader = new FileReader();
            reader.onload = function(e) {
                const img = new Image();
                img.onload = function() {
                    const canvas = document.createElement('canvas');
                    let ancho = img.width;
                    let alto = img.height;
                    const maxDim = 1600;

                    if (ancho > maxDim || alto > maxDim) {
                        if (ancho > alto) {
                            alto = Math.round((alto * maxDim) / ancho);
                            ancho = maxDim;
                        } else {
                            ancho = Math.round((ancho * maxDim) / alto);
                            alto = maxDim;
                        }
                    }

                    canvas.width = ancho;
                    canvas.height = alto;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, ancho, alto);

                    imagenBase64 = canvas.toDataURL('image/jpeg', 0.85);
                    mimeType = 'image/jpeg';

                    previewImg.src = imagenBase64;
                    contenedorPreview.style.display = 'block';
                    grupoBotones.style.display = 'none';
                    ocultarEstado();
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        }

        inputCamara.addEventListener('change', (e) => procesarArchivo(e.target.files[0]));
        inputGaleria.addEventListener('change', (e) => procesarArchivo(e.target.files[0]));

        function mostrarEstado(mensaje, tipo, mostrarSpinner = false) {
            statusBox.className = 'status-box status-' + tipo;
            statusBox.innerHTML = (mostrarSpinner ? '<span class="spinner"></span>' : '') + mensaje;
            statusBox.style.display = 'block';
        }

        function ocultarEstado() {
            statusBox.style.display = 'none';
        }

        function resetear() {
            imagenBase64 = null;
            inputCamara.value = '';
            inputGaleria.value = '';
            contenedorPreview.style.display = 'none';
            grupoBotones.style.display = 'flex';
            ocultarEstado();
        }

        async function enviarFoto() {
            if (!imagenBase64) {
                mostrarEstado('Por favor toma una foto primero.', 'error');
                return;
            }

            btnEnviar.disabled = true;
            mostrarEstado('Enviando imagen a tu computadora...', 'loading', true);

            const payload = {
                imagen_b64: imagenBase64,
                mime: mimeType,
                nota: document.getElementById('txtNota').value.trim()
            };

            try {
                const respuesta = await fetch('/subir_foto', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const resultado = await respuesta.json();

                if (respuesta.ok && resultado.ok) {
                    mostrarEstado('🎉 ¡Foto enviada con éxito! Revisa la pantalla de tu computadora, el problema ya se está resolviendo.', 'success');
                    btnEnviar.disabled = false;
                } else {
                    mostrarEstado('Error al enviar: ' + (resultado.error || 'Error desconocido'), 'error');
                    btnEnviar.disabled = false;
                }
            } catch (err) {
                mostrarEstado('No se pudo conectar con la computadora. Verifica que ambos sigan en la misma red Wi-Fi.', 'error');
                btnEnviar.disabled = false;
            }
        }
    </script>
</body>
</html>
"""


class ServidorMovilSignals(QObject):
    """Señales para comunicar el servidor HTTP en segundo plano con la interfaz PyQt."""

    foto_recibida = pyqtSignal(bytes, str, str)  # (imagen_bytes, mime, nota)
    dispositivo_conectado = pyqtSignal(str)       # ip_cliente


class ServidorMovilHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para la interfaz móvil y recepción de fotos."""

    servidor_obj = None

    def log_message(self, format, *args):
        """Silenciar logs excesivos en la consola."""
        pass

    def do_GET(self):
        """Entrega la página web móvil o respuesta a healthcheck."""
        if self.path in ("/", "/index.html"):
            contenido = HTML_PAGINA_MOVIL.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(contenido)))
            self.end_headers()
            self.wfile.write(contenido)

            if self.servidor_obj:
                cliente_ip = self.client_address[0]
                self.servidor_obj.signals.dispositivo_conectado.emit(cliente_ip)

        elif self.path == "/ping":
            resp = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Recibe la foto tomada desde el celular."""
        if self.path == "/subir_foto":
            try:
                longitud = int(self.headers.get("Content-Length", 0))
                cuerpo = self.rfile.read(longitud).decode("utf-8")
                datos = json.loads(cuerpo)

                imagen_b64 = datos.get("imagen_b64", "")
                mime = datos.get("mime", "image/jpeg")
                nota = datos.get("nota", "")

                # Extraer la parte binaria de Data URL: data:image/jpeg;base64,XXXX
                if "," in imagen_b64:
                    encabezado, base64_puro = imagen_b64.split(",", 1)
                    if "image/" in encabezado:
                        mime = encabezado.split(";")[0].replace("data:", "")
                else:
                    base64_puro = imagen_b64

                imagen_bytes = base64.b64decode(base64_puro)

                if self.servidor_obj:
                    self.servidor_obj.signals.foto_recibida.emit(
                        imagen_bytes, mime, nota
                    )

                respuesta = json.dumps({"ok": True, "mensaje": "Foto recibida"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(respuesta)))
                self.end_headers()
                self.wfile.write(respuesta)

            except Exception as e:
                respuesta = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(respuesta)))
                self.end_headers()
                self.wfile.write(respuesta)
        else:
            self.send_response(404)
            self.end_headers()


class ServidorMovil(QObject):
    """Gestiona el ciclo de vida del servidor HTTP local y la generación del código QR."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = ServidorMovilSignals()
        self.httpd = None
        self.hilo = None
        self.ip = obtener_ip_local()
        self.puerto = 8080
        self._activo = False

    def esta_activo(self):
        return self._activo

    def obtener_url(self):
        return f"http://{self.ip}:{self.puerto}/"

    def iniciar(self, puerto_preferido=8080):
        """Inicia el servidor HTTP en un hilo en segundo plano buscando un puerto libre."""
        if self._activo:
            return True, self.obtener_url()

        self.ip = obtener_ip_local()

        # Probar puertos a partir del preferido
        puerto_actual = puerto_preferido
        for _ in range(20):
            try:
                ServidorMovilHandler.servidor_obj = self
                self.httpd = ThreadingHTTPServer(("0.0.0.0", puerto_actual), ServidorMovilHandler)
                self.puerto = puerto_actual
                break
            except OSError:
                puerto_actual += 1

        if self.httpd is None:
            return False, "No se pudo encontrar un puerto libre en la máquina."

        self._activo = True
        self.hilo = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.hilo.start()

        return True, self.obtener_url()

    def detener(self):
        """Detiene el servidor HTTP si está en ejecución."""
        if self._activo and self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self._activo = False
            self.httpd = None

    def generar_qr_pixmap(self, tamano=240):
        """Genera un QPixmap con el código QR apuntando a la URL del servidor móvil."""
        url = self.obtener_url()

        try:
            import qrcode

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="#0F2F66", back_color="#FFFFFF")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())

            if not pixmap.isNull():
                return pixmap.scaled(
                    tamano, tamano,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
        except Exception as error:
            print("Error al generar QR:", error)

        return None
