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

# ---- Identificación sin usuario escrito (1:N) ----
# Ventaja mínima del mejor candidato sobre el segundo para no confundir usuarios
MARGEN_IDENTIFICACION = 0.05
