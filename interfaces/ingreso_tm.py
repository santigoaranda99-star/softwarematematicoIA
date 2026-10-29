"""
Ingreso rápido por rostro y por voz con los modelos de Teachable Machine, y su vinculación.

Login: escaneo (interfaces/escaneo_tm.py) → clase reconocida → usuario vinculado a esa clase.
- Con usuario escrito: debe coincidir con el reconocido (1:1).
- Sin usuario escrito: entra directo el usuario vinculado a la clase (1:N).
- Rostro: si la cuenta tiene vector SFace guardado, además debe coincidir (verificación extra).
"""
import json

from controllers.usuario_controller import UsuarioController
from interfaces.captura_biometrica import campo
from utils.mensajes import Mensajes
from utils.umbrales_biometria import UMBRAL_ROSTRO_SFACE

_NOMBRES = {"rostro": "rostro", "voz": "voz"}


def _dialogo(tipo):
    from interfaces.escaneo_tm import DialogoEscaneoRostro, DialogoEscaneoVoz
    return DialogoEscaneoRostro if tipo == "rostro" else DialogoEscaneoVoz


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


def _identificar(login, tipo, resultado):
    """Devuelve (datos_usuario, None) o (None, motivo_del_rechazo)."""
    veredicto = resultado["veredicto"]
    if not veredicto.aprobado:
        return None, veredicto.motivo

    escrito = login.txtUsuario.text().strip()
    candidatos = UsuarioController.usuarios_por_clase_tm(tipo, veredicto.clase)
    if escrito:
        candidatos = [c for c in candidatos if c["usuario"].lower() == escrito.lower()]
        if not candidatos:
            return None, (f"El {_NOMBRES[tipo]} reconocido no corresponde al usuario '{escrito}'. "
                          f"Si es su cuenta, vincúlela en '🔗 Vincular mi Biometría'.")
    elif not candidatos:
        return None, (f"Se reconoció a '{veredicto.clase}', pero ninguna cuenta tiene ese {_NOMBRES[tipo]} "
                      f"vinculado. Use '🔗 Vincular mi Biometría' una vez y luego podrá entrar directo.")
    elif len(candidatos) > 1:
        return None, "Hay varias cuentas con ese perfil. Escriba su usuario y vuelva a intentarlo."

    datos = candidatos[0]
    if tipo == "rostro":
        similitud = _similitud_sface(datos, resultado.get("vectores"))
        if similitud is not None and similitud < UMBRAL_ROSTRO_SFACE:
            print(f"[IngresoTM] ❌ SFace no coincide para '{datos['usuario']}' ({similitud:.3f})")
            return None, "El rostro no coincide con el registrado en la cuenta. Intente de nuevo con buena luz."
    return datos, None


def ingresar(login, tipo):
    """Flujo de login de los botones 📷 Rostro / 🎤 Voz."""
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
    print(f"[IngresoTM] ✅ {tipo}: '{datos['usuario']}' (clase {v.clase}, {v.confianza * 100:.1f}%)")
    via = "reconocimiento facial" if tipo == "rostro" else "reconocimiento de voz"
    login._conceder_acceso(datos, f"{tipo.capitalize()} ({v.confianza * 100:.1f}%)", via)


def vincular(parent, usuario, tipo, al_terminar=None):
    """Escanea una vez y vincula la clase reconocida (y, en rostro, el vector SFace) al usuario."""
    resultado, error = _dialogo(tipo).ejecutar(parent)
    if resultado is None and error is None:
        return
    veredicto = resultado["veredicto"] if resultado else None
    motivo = error or (None if veredicto.aprobado else veredicto.motivo)
    if motivo:
        if Mensajes.confirmar(parent, "No se pudo vincular", f"{motivo}\n\n¿Desea intentarlo de nuevo?"):
            vincular(parent, usuario, tipo, al_terminar)
        return

    otros = [f["usuario"] for f in UsuarioController.usuarios_por_clase_tm(tipo, veredicto.clase)
             if f["usuario"].lower() != usuario.lower() and campo(f, f"clase_tm_{tipo}")]
    if otros:
        Mensajes.advertencia(parent, "Ya Vinculado",
                             f"Ese {_NOMBRES[tipo]} ya está vinculado a la cuenta '{otros[0]}'.")
        return

    guardado = UsuarioController.guardar_clase_tm(usuario, tipo, veredicto.clase)
    if guardado and tipo == "rostro" and resultado.get("vectores"):
        UsuarioController.guardar_embedding_facial(usuario, resultado["vectores"][0])
    if not guardado:
        Mensajes.error(parent, "Error de Base de Datos", f"No se pudo guardar el {_NOMBRES[tipo]}.")
        return

    boton = "📷 Rostro" if tipo == "rostro" else "🎤 Voz"
    Mensajes.informacion(parent, "Vinculado ✓",
                         f"Su {_NOMBRES[tipo]} quedó vinculado ({veredicto.confianza * 100:.0f}% de confianza).\n\n"
                         f"Desde ahora puede entrar solo con el botón '{boton}', sin escribir nada.")
    if al_terminar is not None:
        al_terminar()
