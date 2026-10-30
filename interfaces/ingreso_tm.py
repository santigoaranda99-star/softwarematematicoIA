"""
Ingreso rápido por rostro, voz y postura con los modelos de Teachable Machine, y su vinculación.

- Rostro: Teachable Machine confirma que hay una persona real; quién es lo decide SFace entre
  todas las cuentas con rostro guardado (el modelo de TM confunde a personas parecidas).
- Voz: doble verificación. 1) La palabra clave secreta del usuario (plantilla MFCC/DTW de sus
  3 grabaciones) identifica la cuenta. 2) El modelo de voz de TM debe reconocer la misma voz
  que se registró al vincular. Decir el nombre de otra persona ya no basta para entrar.
- Postura: la clase del modelo de postura identifica la cuenta y, si la cuenta tiene rostro
  guardado, la cara que aparece en la cámara debe coincidir (SFace).

Con usuario escrito todo se verifica 1:1 contra esa cuenta; sin usuario, se identifica 1:N.
"""
import json

from controllers.usuario_controller import UsuarioController
from interfaces.captura_biometrica import campo
from utils.mensajes import Mensajes
from utils.umbrales_biometria import MARGEN_IDENTIFICACION, UMBRAL_PALABRA_CLAVE, UMBRAL_ROSTRO_SFACE

MUESTRAS_PALABRA = 3
MAX_GRABACIONES = 5      # grabaciones válidas como máximo para encontrar 3 parecidas
MAX_INTENTOS_VOZ = 8     # incluye las que se repiten por no oírse bien
_BOTONES = {"rostro": "📷 Rostro", "voz": "🎤 Voz", "postura": "🧍 Postura"}
_VIAS = {"rostro": "reconocimiento facial", "voz": "reconocimiento de voz",
         "postura": "reconocimiento de postura"}


def _dialogo(tipo):
    from interfaces.escaneo_tm import DialogoEscaneoPostura, DialogoEscaneoRostro, DialogoEscaneoVoz
    return {"rostro": DialogoEscaneoRostro, "voz": DialogoEscaneoVoz, "postura": DialogoEscaneoPostura}[tipo]


def _similitud_sface(datos, vectores):
    """Mejor similitud SFace entre los vectores del escaneo y el guardado. None si no hay guardado."""
    from services.clasificador_imagen import ClasificadorImagen

    try:
        guardado = json.loads(campo(datos, "embedding_facial") or "null")
    except ValueError:
        guardado = None
    if not guardado:
        return None
    if not vectores:
        return 0.0
    return max(ClasificadorImagen.comparar_embeddings(v, guardado) for v in vectores)


def _mejor_candidato(puntuaciones, umbral, escrito, texto_no_coincide, texto_parecido):
    """[(puntaje, datos)] → (datos, None) del mejor si supera el umbral y tiene ventaja clara."""
    puntuaciones = sorted(puntuaciones, key=lambda p: p[0], reverse=True)
    mejor, datos = puntuaciones[0]
    segundo = puntuaciones[1][0] if len(puntuaciones) > 1 else 0.0
    if mejor < umbral:
        return None, texto_no_coincide
    if not escrito and mejor - segundo < MARGEN_IDENTIFICACION:
        return None, texto_parecido
    return datos, None


def _filtrar_escrito(candidatos, escrito, que):
    if not escrito:
        return candidatos, None
    candidatos = [c for c in candidatos if c["usuario"].lower() == escrito.lower()]
    if not candidatos:
        return [], f"El usuario '{escrito}' no tiene {que} vinculado. Vincúlelo en '🔗 Vincular mi Biometría'."
    return candidatos, None


# =====================================================
# IDENTIFICACIÓN EN EL LOGIN
# =====================================================

def _identificar_rostro(escrito, resultado):
    candidatos, error = _filtrar_escrito(UsuarioController.usuarios_con_rostro(), escrito, "su rostro")
    if error:
        return None, error
    if not candidatos:
        return None, "Ninguna cuenta tiene su rostro vinculado. Use '🔗 Vincular mi Biometría'."
    vectores = resultado.get("vectores") or []
    if not vectores:
        return None, "No se pudo ver su rostro con claridad. Mire de frente con buena luz."
    puntuaciones = [(_similitud_sface(c, vectores) or 0.0, c) for c in candidatos]
    print("[IngresoTM] SFace: " + ", ".join(f"{c['usuario']}={s:.3f}" for s, c in puntuaciones))
    return _mejor_candidato(
        puntuaciones, UMBRAL_ROSTRO_SFACE, escrito,
        "El rostro no coincide con ninguna cuenta registrada. Mire de frente con buena luz, "
        "o vincule su rostro en '🔗 Vincular mi Biometría'.",
        "Su rostro se parece a más de una cuenta. Escriba su usuario y vuelva a intentarlo.")


def _identificar_voz(escrito, resultado):
    from utils import plantillas_biometricas as plantillas

    veredicto = resultado["veredicto"]
    if veredicto.rechazo in ("pocas", "falso"):
        return None, veredicto.motivo

    candidatos, error = _filtrar_escrito(UsuarioController.usuarios_con_plantilla("voz"), escrito,
                                         "su palabra clave")
    if error:
        return None, error
    if not candidatos:
        return None, "Ninguna cuenta tiene palabra clave registrada. Regístrela en '🔗 Vincular mi Biometría'."

    # 1) La palabra clave (contenido + timbre) identifica la cuenta
    puntuaciones = []
    for c in candidatos:
        confianza, _ = plantillas.comparar_voz(resultado["audio"], resultado["frecuencia"],
                                               json.loads(c["plantilla_voz"]))
        puntuaciones.append((confianza, c))
    print("[IngresoTM] Palabra clave: " + ", ".join(f"{c['usuario']}={s:.3f}" for s, c in puntuaciones))
    datos, error = _mejor_candidato(
        puntuaciones, UMBRAL_PALABRA_CLAVE, escrito,
        "La palabra clave o la voz no coinciden con ninguna cuenta. Diga su palabra clave como "
        "la grabó al registrarla.",
        "La grabación se parece a más de una cuenta. Escriba su usuario y vuelva a intentarlo.")
    if datos is None:
        return None, error

    # 2) El modelo de voz debe reconocer la misma voz que se registró con esa palabra
    esperada = campo(datos, "clase_tm_voz")
    if esperada and veredicto.clase.lower() != esperada.lower():
        print(f"[IngresoTM] ❌ Voz TM '{veredicto.clase or 'ninguna'}' ≠ registrada '{esperada}' "
              f"para '{datos['usuario']}' (votos {veredicto.conteo})")
        return None, ("La palabra clave es correcta, pero la voz no corresponde a la del dueño de la "
                      "cuenta. Debe decirla la misma persona que la registró.")
    return datos, None


def _postura_por_plantilla(escrito, resultado):
    """
    Usuarios que el modelo de Teachable Machine no conoce (cuentas nuevas): se comparan los
    17 puntos del cuerpo del escaneo con la plantilla de puntos que grabaron al registrarse.
    """
    from utils import plantillas_biometricas as plantillas
    from utils.umbrales_biometria import UMBRAL_SIMILITUD_POSTURA

    candidatos, error = _filtrar_escrito(UsuarioController.usuarios_con_plantilla("postura"), escrito,
                                         "su postura")
    if error:
        return None, error
    if not candidatos or not resultado.get("puntos"):
        return None, resultado["veredicto"].motivo or "No se reconoció ninguna postura registrada."
    puntuaciones = [(plantillas.comparar_postura(resultado["puntos"], json.loads(c["plantilla_postura"])), c)
                    for c in candidatos]
    print("[IngresoTM] Plantilla de postura: " + ", ".join(f"{c['usuario']}={s:.3f}" for s, c in puntuaciones))
    return _mejor_candidato(
        puntuaciones, UMBRAL_SIMILITUD_POSTURA, escrito,
        "La postura no coincide con ninguna registrada. Repita la misma postura que usó al registrarla.",
        "Su postura se parece a la de más de una cuenta. Escriba su usuario y vuelva a intentarlo.")


def _identificar_postura(escrito, resultado):
    veredicto = resultado["veredicto"]
    if resultado.get("antispoof_rechazo"):
        return None, veredicto.motivo
    candidatos = []
    if veredicto.aprobado:
        candidatos, error = _filtrar_escrito(
            UsuarioController.usuarios_por_clase_tm("postura", veredicto.clase), escrito, "esa postura")
        if len(candidatos) > 1:
            return None, "Hay varias cuentas con esa postura. Escriba su usuario y vuelva a intentarlo."

    if candidatos:
        datos = candidatos[0]          # el modelo de Teachable Machine conoce a esta persona
    else:
        datos, error = _postura_por_plantilla(escrito, resultado)
        if datos is None:
            return None, error

    similitud = _similitud_sface(datos, resultado.get("vectores"))
    if similitud is not None and similitud < UMBRAL_ROSTRO_SFACE:
        print(f"[IngresoTM] ❌ Postura '{veredicto.clase}' pero SFace no coincide con '{datos['usuario']}' "
              f"({similitud:.3f})")
        return None, ("La postura es correcta, pero la persona no coincide con el dueño de la cuenta. "
                      "Asegúrese de que también se vea su cara.")
    return datos, None


_IDENTIFICADORES = {"rostro": _identificar_rostro, "voz": _identificar_voz, "postura": _identificar_postura}


def _identificar(login, tipo, resultado):
    """Devuelve (datos_usuario, None) o (None, motivo_del_rechazo)."""
    veredicto = resultado["veredicto"]
    if tipo == "rostro" and not veredicto.aprobado:
        return None, veredicto.motivo
    return _IDENTIFICADORES[tipo](login.txtUsuario.text().strip(), resultado)


def ingresar(login, tipo):
    """Flujo de login de los botones 📷 Rostro / 🎤 Voz / 🧍 Postura."""
    from interfaces.biometria_ingreso import mostrar_fallo_biometrico

    if not login._puede_intentar():
        return
    resultado, error = _dialogo(tipo).ejecutar(login, getattr(login, "_modo_oscuro", False))
    if resultado is None and error is None:
        return  # cancelado

    datos, motivo = (None, error) if error else _identificar(login, tipo, resultado)
    if datos is None:
        print(f"[IngresoTM] ❌ {tipo}: {motivo}")
        login._registrar_fallo(tipo, motivo, login.txtUsuario.text().strip())
        mostrar_fallo_biometrico(login, tipo, motivo, lambda: ingresar(login, tipo), login._usar_contrasena)
        return

    v = resultado["veredicto"]
    print(f"[IngresoTM] ✅ {tipo}: '{datos['usuario']}' (clase {v.clase or '-'}, {v.confianza * 100:.1f}%)")
    login._conceder_acceso(datos, f"{tipo.capitalize()} (escaneo rápido)", _VIAS[tipo])


# =====================================================
# VINCULACIÓN
# =====================================================

def _avisar_vinculado(parent, tipo, al_terminar, detalle=""):
    Mensajes.informacion(parent, "Vinculado ✓",
                         f"{detalle}Desde ahora puede entrar con el botón '{_BOTONES[tipo]}'.")
    if al_terminar is not None:
        al_terminar()


def capturar_palabra_clave(parent, usuario_actual=None):
    """
    Registro adaptativo de la palabra clave (sirve para "Crear una cuenta" y para vincular):
    - Cada grabación se valida al momento; si no se oyó bien, se repite solo esa.
    - Se graba hasta MAX_GRABACIONES veces y se usan las 3 (o 2) más parecidas entre sí,
      así un cambio de tono en una grabación no obliga a empezar de nuevo.
    Devuelve (palabra, plantilla, clase_tm_voz) o None si se canceló o no se logró.
    """
    from interfaces.biometria_ingreso import DialogoPalabraIngreso
    from interfaces.escaneo_tm import DialogoEscaneoVoz
    from utils import plantillas_biometricas as plantillas

    palabra = DialogoPalabraIngreso.pedir(parent, usuario_actual)
    if not palabra:
        return None
    muestras, clases, aviso = [], [], ""
    for intento in range(1, MAX_INTENTOS_VOZ + 1):
        validas = len(muestras)
        instruccion = (f"{aviso}Diga su palabra clave con su voz normal" if validas == 0 else
                       f"{aviso}Repita su palabra clave (no hace falta el mismo tono exacto)")
        resultado, error = DialogoEscaneoVoz.ejecutar(
            parent, titulo=f"🎤 Palabra clave — grabación {validas + 1} de {MUESTRAS_PALABRA}",
            instruccion=instruccion)
        if error:
            Mensajes.advertencia(parent, "No se pudo grabar", error)
            return None
        if resultado is None:
            return None
        v = resultado["veredicto"]
        if v.rechazo == "falso":
            aviso = "⚠️ Se oyó un audio de teléfono. Hable usted directamente.\n"
            continue
        try:
            muestras.append(plantillas.caracteristicas_voz(resultado["audio"], resultado["frecuencia"]))
        except ValueError:
            aviso = "⚠️ No se oyó bien la palabra; hable un poco más fuerte.\n"
            continue
        if v.clase:
            clases.append(v.clase)
        aviso = "✓ Grabación lista. "

        if len(muestras) >= MUESTRAS_PALABRA:
            plantilla, _ = plantillas.mejor_grupo_voz(muestras)
            # 3 grabaciones compatibles: listo. Con solo 2 compatibles se sigue grabando
            # hasta MAX_GRABACIONES y, si no aparece una tercera, se aceptan esas 2.
            if plantilla and (len(plantilla["muestras"]) == 3 or len(muestras) >= MAX_GRABACIONES):
                conteo = {c: clases.count(c) for c in set(clases)}
                clase = max(conteo, key=conteo.get) if conteo and max(conteo.values()) >= 2 else ""
                print(f"[IngresoTM] Palabra clave lista con {len(muestras)} grabaciones; voz TM {conteo}")
                return palabra, plantilla, clase
            if len(muestras) >= MAX_GRABACIONES:
                break
            aviso = "Casi listo: una grabación más. "

    if Mensajes.confirmar(parent, "No se logró registrar la voz",
                          "Las grabaciones no se parecieron lo suficiente. Busque un lugar sin ruido y "
                          "diga siempre la misma palabra.\n\n¿Desea intentarlo de nuevo?"):
        return capturar_palabra_clave(parent, usuario_actual)
    return None


def _vincular_voz(parent, usuario, al_terminar):
    """Palabra clave secreta + la clase con que el modelo reconoce esa voz."""
    capturada = capturar_palabra_clave(parent, usuario)
    if capturada is None:
        return
    palabra, plantilla, clase = capturada
    if not UsuarioController.guardar_palabra_ingreso(usuario, palabra, plantilla) \
            or not UsuarioController.guardar_clase_tm(usuario, "voz", clase):
        Mensajes.error(parent, "Error de Base de Datos", "No se pudo guardar la palabra clave.")
        return
    print(f"[IngresoTM] Voz vinculada para '{usuario}': clase TM '{clase or 'sin clase'}'")
    _avisar_vinculado(parent, "voz", al_terminar,
                      "Su palabra clave quedó registrada. Para entrar, diga esa misma palabra: "
                      "debe coincidir la palabra y su voz.\n\n")


def capturar_postura(parent, usuario_actual=None):
    """
    Un solo escaneo con los puntos del cuerpo en pantalla (sirve para "Crear una cuenta" y
    para vincular). Guarda siempre la plantilla de puntos (los tres tercios del escaneo hacen
    de 3 capturas) y, si el modelo de Teachable Machine reconoce a la persona, también su clase.
    Devuelve {"plantilla", "clase", "vectores"} o None si se canceló o no se logró.
    """
    from interfaces.escaneo_tm import DialogoEscaneoPostura
    from utils import plantillas_biometricas as plantillas

    resultado, error = DialogoEscaneoPostura.ejecutar(parent, registro=True)
    if resultado is None and error is None:
        return None
    capturas = (resultado or {}).get("capturas") or []
    motivo = error
    if not motivo and resultado.get("antispoof_rechazo"):
        motivo = resultado["veredicto"].motivo
    if not motivo and len(capturas) < 3:
        motivo = ("No se vio su cuerpo durante todo el escaneo. Aléjese para que se vean su cabeza, "
                  "hombros, brazos y torso, y mantenga la postura quieta.")
    if not motivo:
        ok, plantilla, motivo = plantillas.crear_plantilla_postura(capturas)
        if ok:
            veredicto = resultado["veredicto"]
            clase = ""
            if veredicto.aprobado:
                ajenos = [f for f in UsuarioController.usuarios_por_clase_tm("postura", veredicto.clase)
                          if not usuario_actual or f["usuario"].lower() != usuario_actual.lower()]
                clase = "" if ajenos else veredicto.clase
            print(f"[IngresoTM] Postura capturada: plantilla de 3 capturas, clase TM '{clase or 'ninguna'}'")
            return {"plantilla": plantilla, "clase": clase, "vectores": resultado.get("vectores") or []}
        motivo = "Mantenga la misma postura quieta durante todo el escaneo."
    if Mensajes.confirmar(parent, "No se pudo registrar la postura", f"{motivo}\n\n¿Desea intentarlo de nuevo?"):
        return capturar_postura(parent, usuario_actual)
    return None


def _vincular_postura(parent, usuario, al_terminar):
    capturada = capturar_postura(parent, usuario)
    if capturada is None:
        return
    similitud = _similitud_sface(UsuarioController.buscar_usuario(usuario), capturada["vectores"])
    if similitud is not None and similitud < UMBRAL_ROSTRO_SFACE:
        Mensajes.advertencia(parent, "No se pudo vincular",
                             "La persona de la cámara no coincide con el rostro de esta cuenta. "
                             "Asegúrese de que se vea su cara mientras hace la postura.")
        return
    if not UsuarioController.guardar_plantilla_postura(usuario, capturada["plantilla"]) \
            or not UsuarioController.guardar_clase_tm(usuario, "postura", capturada["clase"]):
        Mensajes.error(parent, "Error de Base de Datos", "No se pudo guardar la postura.")
        return
    _avisar_vinculado(parent, "postura", al_terminar, "Su postura quedó registrada.\n\n")


def vincular(parent, usuario, tipo, al_terminar=None):
    """Vincula rostro (vector SFace), voz (palabra clave + voz) o postura (puntos + clase)."""
    if tipo == "voz":
        _vincular_voz(parent, usuario, al_terminar)
        return
    if tipo == "postura":
        _vincular_postura(parent, usuario, al_terminar)
        return

    resultado, error = _dialogo(tipo).ejecutar(parent)
    if resultado is None and error is None:
        return
    veredicto = resultado["veredicto"] if resultado else None
    motivo = error or (None if veredicto.aprobado else veredicto.motivo)
    if motivo:
        if Mensajes.confirmar(parent, "No se pudo vincular", f"{motivo}\n\n¿Desea intentarlo de nuevo?"):
            vincular(parent, usuario, tipo, al_terminar)
        return

    vectores = resultado.get("vectores") or []
    if tipo == "rostro":
        # La identidad del rostro la da SFace: el rostro no debe parecerse ya a otra cuenta
        if not vectores:
            Mensajes.advertencia(parent, "No se pudo vincular",
                                 "No se pudo extraer el rostro con claridad. Mire de frente con buena luz.")
            return
        otros = [f["usuario"] for f in UsuarioController.usuarios_con_rostro()
                 if f["usuario"].lower() != usuario.lower()
                 and (_similitud_sface(f, vectores) or 0.0) >= UMBRAL_ROSTRO_SFACE]
    if otros:
        Mensajes.advertencia(parent, "No se pudo vincular",
                             f"Ese rostro ya está vinculado a la cuenta '{otros[0]}'.")
        return

    guardado = UsuarioController.guardar_clase_tm(usuario, tipo, veredicto.clase)
    if guardado and tipo == "rostro":
        guardado = UsuarioController.guardar_embedding_facial(usuario, vectores[0])
    if not guardado:
        Mensajes.error(parent, "Error de Base de Datos", "No se pudo guardar la vinculación.")
        return
    _avisar_vinculado(parent, tipo, al_terminar,
                      f"Quedó vinculado ({veredicto.confianza * 100:.0f}% de confianza).\n\n")
