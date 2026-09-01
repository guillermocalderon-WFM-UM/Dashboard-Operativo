import streamlit as st

st.set_page_config(
    page_title="Dashboard Operativo – Uniminuto",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CONTROL DE ACCESO — login con Google + lista de correos autorizados
#   Config en .streamlit/secrets.toml (ver secrets.toml.example).
#   · Sin sección [auth]      → la app queda abierta (útil en local).
#   · [auth] sin [access]     → basta con iniciar sesión con Google.
#   · [auth] + [access]       → además el correo debe estar en la lista
#                               (o pertenecer a un dominio permitido).
# ─────────────────────────────────────────────
_APP_NOMBRE = "Dashboard Operativo"


def _proteger_acceso() -> None:
    try:
        _auth_cfg = st.secrets["auth"]
    except Exception:
        return  # OAuth no configurado → no se exige login

    _provider = "google" if "google" in _auth_cfg else None
    try:
        _cid = str((_auth_cfg["google"]["client_id"] if _provider
                    else _auth_cfg.get("client_id", "")) or "")
    except Exception:
        _cid = ""
    if not _cid or "REEMPLAZA" in _cid.upper() or _cid.lower().startswith("xxxx"):
        return  # credenciales aún sin completar → no se exige login

    if not getattr(st.user, "is_logged_in", False):
        st.title(_APP_NOMBRE)
        st.write("Panel de uso interno. Iniciá sesión con tu cuenta de Google autorizada.")
        if st.button("Iniciar sesión con Google", type="primary"):
            st.login(_provider) if _provider else st.login()
        st.stop()

    _correo = (getattr(st.user, "email", "") or "").strip().lower()
    try:
        _acc = st.secrets["access"]
        _emails = {e.strip().lower() for e in _acc.get("emails", [])}
        _dominios = tuple("@" + d.strip().lower().lstrip("@") for d in _acc.get("domains", []))
    except Exception:
        _emails, _dominios = set(), ()

    _tiene_lista = bool(_emails or _dominios)
    _permitido = _correo in _emails or (bool(_dominios) and _correo.endswith(_dominios))
    if _tiene_lista and not _permitido:
        st.title(_APP_NOMBRE)
        st.error(f"La cuenta **{st.user.email}** no tiene acceso a este dashboard. "
                 "Solicitá que agreguen tu correo a la lista de autorizados.")
        st.button("Cambiar de cuenta", on_click=st.logout)
        st.stop()


_proteger_acceso()

# ─────────────────────────────────────────────
# NAVEGACIÓN (todas por ruta de archivo → navegación confiable)
# ─────────────────────────────────────────────
home_pg  = st.Page("home.py",                 title="Inicio",         icon="🏠", default=True)
insc_pg  = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
mat_pg   = st.Page("pages/2_Matriculas.py",    title="Matrículas",    icon="🎓")
cuart_pg = st.Page("pages/3_Cuartiles.py",     title="Cuartiles",     icon="🏆")
cont_pg  = st.Page("pages/4_Contactabilidad.py", title="Real time", icon="📞")

pg = st.navigation([home_pg, insc_pg, mat_pg, cuart_pg, cont_pg])
pg.run()
