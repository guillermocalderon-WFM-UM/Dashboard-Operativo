import time

import streamlit as st

st.set_page_config(
    page_title="Dashboard Operativo – Uniminuto",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cada cuánto se exige volver a iniciar sesión (el cookie de Streamlit dura 30 días;
# esto lo acorta comparando la hora de login del token).
_SESION_MAX_SEG = 60 * 60  # 1 hora

# ─────────────────────────────────────────────
# CONTROL DE ACCESO — login con Google + lista de correos autorizados
#   Config en .streamlit/secrets.toml (ver secrets.toml.example).
#   · Sin sección [auth]      → la app queda abierta (útil en local).
#   · [auth] sin [access]     → basta con iniciar sesión con Google.
#   · [auth] + [access]       → además el correo debe estar en la lista
#                               (o pertenecer a un dominio permitido).
# ─────────────────────────────────────────────
_APP_NOMBRE = "Dashboard Operativo"
# Pantalla de acceso: cada app usa su propio fondo/acento (igual que su dashboard).
_ACCENT = "#0EA5E9"
_LOGIN_BG = "linear-gradient(165deg,#061109 0%,#0a1f17 68%,#071712 100%)"  # verde-teal (Operativo)
_LOGIN_EYEBROW = "Scala Learning · Uniminuto · 2026"

_G_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E"
    "%3Cpath fill='%234285F4' d='M45 24c0-1.6-.1-3.1-.4-4.6H24v9.1h11.8c-.5 2.7-2 5-4.4 6.6v5.5h7.1C42.7 37 45 31 45 24z'/%3E"
    "%3Cpath fill='%2334A853' d='M24 46c5.9 0 10.9-2 14.5-5.3l-7.1-5.5c-2 1.3-4.5 2.1-7.4 2.1-5.7 0-10.5-3.8-12.2-9H4.5v5.7C8.1 41.6 15.5 46 24 46z'/%3E"
    "%3Cpath fill='%23FBBC05' d='M11.8 28.3c-.4-1.3-.7-2.7-.7-4.3s.3-3 .7-4.3v-5.7H4.5C3 17 2 20.4 2 24s1 7 2.5 10z'/%3E"
    "%3Cpath fill='%23EA4335' d='M24 10.7c3.2 0 6.1 1.1 8.4 3.3l6.3-6.3C34.9 4.1 29.9 2 24 2 15.5 2 8.1 6.4 4.5 14l7.3 5.7c1.7-5.2 6.5-9 12.2-9z'/%3E"
    "%3C/svg%3E"
)


def _portada_acceso(cuerpo_html: str) -> None:
    """Pantalla editorial oscura para login / sin-acceso (misma para ambas apps)."""
    partes = _APP_NOMBRE.split()
    n1 = " ".join(partes[:-1]) if len(partes) > 1 else _APP_NOMBRE
    n2 = partes[-1] if len(partes) > 1 else ""
    _sys = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&display=swap');
      [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
      [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], #MainMenu {{ display:none !important; }}
      [data-testid="stAppViewContainer"], .stApp {{ background:{_LOGIN_BG} !important; }}
      [data-testid="stAppViewContainer"]::before {{
        content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
        background:radial-gradient(360px 360px at 82% 14%, {_ACCENT}30, transparent 70%); }}
      @media (prefers-reduced-motion:no-preference) {{
        [data-testid="stAppViewContainer"]::before {{ animation:lgnDrift 20s ease-in-out infinite; }} }}
      @keyframes lgnDrift {{ 0%,100%{{transform:translate(0,0);}} 50%{{transform:translate(-26px,20px);}} }}
      .lgn-bar {{ position:fixed; top:0; left:0; right:0; height:3px; z-index:50;
        background:linear-gradient(90deg,#38BDF8,#818CF8,#34D399,#F59E0B,#38BDF8); }}
      .block-container {{ max-width:760px !important; padding-top:13vh !important; padding-bottom:6rem !important; position:relative; z-index:1; }}
      .lgn-eye {{ font-family:'Space Grotesk',sans-serif; font-weight:600; font-size:11px;
        letter-spacing:.22em; text-transform:uppercase; color:rgba(233,241,236,.5); }}
      .lgn-wm {{ font-family:'Space Grotesk',sans-serif; font-weight:700; letter-spacing:-.035em;
        line-height:1.02; font-size:clamp(38px,7.4vw,66px); color:#fff; margin:16px 0 0; }}
      .lgn-grad {{ background:linear-gradient(92deg,#38bdf8,#818cf8 42%,#34d399 78%,#38bdf8);
        -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
      .lgn-rule {{ height:1px; background:linear-gradient(90deg,rgba(255,255,255,.22),transparent); margin:24px 0 20px; }}
      .lgn-copy {{ font-family:{_sys}; font-size:13.5px; color:rgba(233,241,236,.62);
        max-width:48ch; line-height:1.75; }}
      .lgn-copy b {{ color:#fff; }}
      .lgn-hint {{ font-family:{_sys}; font-size:11px; color:rgba(233,241,236,.38); margin-top:12px; }}
      .stButton > button {{ font-family:'Space Grotesk',sans-serif !important; font-weight:700 !important;
        font-size:14px !important; color:#fff !important; background:rgba(255,255,255,.03) !important;
        border:1px solid rgba(255,255,255,.28) !important; border-radius:12px !important;
        padding:13px 22px !important; height:auto !important; margin-top:22px !important;
        transition:background .18s, border-color .18s, transform .18s, box-shadow .18s !important; }}
      .stButton > button p {{ font-weight:700 !important; }}
      .stButton > button:hover {{ transform:translateY(-2px) !important; }}
      .st-key-btn_login button {{ position:relative; padding-left:48px !important; }}
      .st-key-btn_login button::before {{ content:''; position:absolute; left:20px; top:50%;
        transform:translateY(-50%); width:18px; height:18px;
        background:url("{_G_SVG}") center/contain no-repeat; }}
      .st-key-btn_login button:hover {{ background:linear-gradient(120deg,{_ACCENT},#6366F1) !important;
        border-color:transparent !important; box-shadow:0 16px 42px -14px {_ACCENT} !important; }}
      .st-key-btn_cambiar button:hover {{ border-color:{_ACCENT} !important; }}
    </style>
    <div class='lgn-bar'></div>
    <div class='lgn-eye'>{_LOGIN_EYEBROW}</div>
    <div class='lgn-wm'>{n1}<br><span class='lgn-grad'>{n2}</span></div>
    <div class='lgn-rule'></div>
    {cuerpo_html}
    """, unsafe_allow_html=True)


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
        _expiro = st.session_state.pop("_sesion_expiro", False)
        _txt = ("Tu sesión expiró (máximo 1 hora). Volvé a iniciar sesión para continuar."
                if _expiro else
                "Panel de uso interno del equipo. El acceso está restringido: "
                "necesitás una cuenta de Google autorizada.")
        _portada_acceso(f"<div class='lgn-copy'>{_txt}</div>")
        if st.button("Iniciar sesión con Google", key="btn_login"):
            st.login(_provider) if _provider else st.login()
        st.markdown("<div class='lgn-hint'>La sesión dura 1 hora.</div>", unsafe_allow_html=True)
        st.stop()

    # Caducidad de sesión: si el token se emitió hace más de _SESION_MAX_SEG, re-login.
    try:
        _iat = float(st.user.get("iat"))
    except (TypeError, ValueError, AttributeError):
        _iat = None
    if _iat and time.time() - _iat > _SESION_MAX_SEG:
        st.session_state["_sesion_expiro"] = True
        st.logout()
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
        _portada_acceso(
            f"<div class='lgn-copy'>La cuenta <b>{st.user.email}</b> no está autorizada "
            "para este panel. Escribí a Workforce Management para pedir acceso.</div>"
        )
        st.button("Cambiar de cuenta", key="btn_cambiar", on_click=st.logout)
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
