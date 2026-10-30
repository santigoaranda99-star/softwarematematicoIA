"""
Umbrales de la autenticación biométrica, centralizados en un solo lugar.
Todos se expresan como fracción entre 0 y 1 (0.50 = 50 %).
"""

# ---- Voz ----
# Confianza mínima de la voz: se usa para la palabra de ingreso propia de cada usuario
# (similitud con su plantilla) y para las clases del modelo de Teachable Machine.
UMBRAL_CONFIANZA_VOZ = 0.50
# Correlación mínima con el vector de voz del sistema anterior (Teachable Machine)
UMBRAL_SIMILITUD_VOZ_TM = 0.50

# ---- Postura ----
# Similitud mínima entre la postura actual y la plantilla de postura del usuario
UMBRAL_SIMILITUD_POSTURA = 0.70
# Confianza mínima de la clase de postura del modelo de Teachable Machine (sistema anterior)
UMBRAL_CONFIANZA_POSTURA_TM = 0.80

# ---- Rostro ----
# Similitud coseno SFace mínima para identificar al usuario (recomendado por OpenCV)
UMBRAL_ROSTRO_SFACE = 0.35
# Confianza mínima del modelo facial de Teachable Machine (respaldo)
UMBRAL_ROSTRO_TM = 0.75

# ---- Ingreso rápido con los modelos de Teachable Machine (models/tm_rostro, models/tm_voz) ----
# El botón 📷 Rostro hace un escaneo continuo de la cara y el botón 🎤 Voz una grabación corta;
# los votos de todos los cuadros/ventanas se combinan antes de decidir.
INGRESO_RAPIDO_TM = True             # False = vuelve a los flujos anteriores (prueba de vida, palabra)
SEGUNDOS_ESCANEO_ROSTRO = 3.5
SEGUNDOS_ESCANEO_VOZ = 3.0
UMBRAL_ROSTRO_ESCANEO = 0.80         # probabilidad media mínima de la clase ganadora
VOTOS_ROSTRO_ESCANEO = 0.50          # fracción mínima de cuadros válidos que votan por ella
                                     # (la identidad además se confirma con SFace si la cuenta lo tiene)
FRACCION_CON_ROSTRO = 0.60           # cuadros que deben tener una cara detectada (YuNet)
UMBRAL_VOZ_ESCANEO = 0.75
VOTOS_VOZ_ESCANEO = 0.50
VENTANAS_VOZ_MINIMAS = 2             # ventanas de 1 s con voz (no ruido de fondo) necesarias
# Postura (models/my-pose-model): unos segundos para ponerse en posición y luego el escaneo.
# La cara que aparece en la cámara se confirma con SFace contra la cuenta.
SEGUNDOS_PREPARAR_POSTURA = 3.0
SEGUNDOS_ESCANEO_POSTURA = 4.0
UMBRAL_POSTURA_ESCANEO = 0.80
VOTOS_POSTURA_ESCANEO = 0.60
PUNTOS_POSTURA_MINIMOS = 7           # puntos del cuerpo visibles para que un cuadro cuente
# Voz: además de la clase del modelo, la palabra clave del usuario (plantilla MFCC/DTW)
UMBRAL_PALABRA_CLAVE = 0.50
# Quién detecta el celular/foto en el rostro: "antispoof" = MiniFASNetV2 (models/liveness),
# "clase_movil" = la clase "movil" de Teachable Machine (se confundía con caras reales).
SUPLANTACION_ROSTRO = "antispoof"
FRACCION_SUPLANTACION = 0.50        # rechazo si este % de votos es "movil" / "audio-tel"
                                     # (o si superan a la persona más votada)

# ---- Identificación sin usuario escrito (1:N) ----
# Ventaja mínima del mejor candidato sobre el segundo para no confundir usuarios
MARGEN_IDENTIFICACION = 0.05
