import base64

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import _datos

COLOR_PRIMARY = "#065F46"
COLOR_ACCENT  = "#0EA5E9"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER  = "#EF4444"

# Disposiciones agrupadas que se muestran como columnas (se omiten "No Encontrado" y
# "Llamada Entrante" — igual que los pivots de la operación).
_DISPOS = [
    "Efectivo Interesado", "Efectivo No Interesado", "No cumple perfil",
    "Contacto con Tercero", "Se corta llamada", "No Contacto", "No Efectivo", "Prueba",
]
_DISPOS_COLOR = {
    "Efectivo Interesado": COLOR_SUCCESS, "Efectivo No Interesado": "#818CF8",
    "No cumple perfil": COLOR_WARNING, "Contacto con Tercero": "#38BDF8",
    "Se corta llamada": "#F97316", "No Contacto": COLOR_DANGER,
    "No Efectivo": "#94A3B8", "Prueba": "#64748B",
}


def _hms(seg: float) -> str:
    seg = int(round(seg or 0))
    return f"{seg // 3600}:{seg % 3600 // 60:02d}:{seg % 60:02d}"


# ─────────────────────────────────────────────
# LOGO
# ─────────────────────────────────────────────
_LOGO_PATH = "logo-scala-learning-transformacion-digital-universidades.webp"
try:
    with open(_LOGO_PATH, "rb") as _f:
        _logo_src = f"data:image/webp;base64,{base64.b64encode(_f.read()).decode()}"
except FileNotFoundError:
    _logo_src = ""

# ─────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────
_insc_tab = _datos.realtime_inscripciones()
_socio = _datos.realtime_socio()
_INSC = _insc_tab.set_index("_ASESOR") if len(_insc_tab) else _insc_tab

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class='sbc'>
        <div class='sbc-orb sbc-orb-1'></div>
        <div class='sbc-orb sbc-orb-2'></div>
        <div class='sbc-orb sbc-orb-3'></div>
        <div class='sbc-live'><span class='sbc-pulse'></span>LIVE</div>
        <div class='sbc-body'>
            <div class='sbc-logo-wrap'>
                <img src='{_logo_src}' class='sbc-logo-img' />
            </div>
            <div class='sbc-name'>Dashboard Operativo</div>
            <div class='sbc-org'>Uniminuto &nbsp;·&nbsp; Scala Learning</div>
            <div class='sbc-stats'>
                <div class='sbc-stat'><span class='sbc-sv'>2026</span><span class='sbc-sl'>Año</span></div>
                <div class='sbc-sep'></div>
                <div class='sbc-stat'><span class='sbc-sv'>COM</span><span class='sbc-sl'>Área</span></div>
                <div class='sbc-sep'></div>
                <div class='sbc-stat'><span class='sbc-sv'>COL</span><span class='sbc-sl'>País</span></div>
            </div>
        </div>
        <div class='sbc-bar'></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""<div class='sbh'>
        <div class='sbh-num' style='color:#38BDF8!important;background:rgba(56,189,248,0.12);border-color:rgba(56,189,248,0.22)'>01</div>
        <div class='sbh-lbl'>Vista</div>
        <div class='sbh-rule'></div>
    </div>""", unsafe_allow_html=True)
    vista = st.selectbox("Vista", ["Detalle tiempo real", "Detalle día vencido"], label_visibility="collapsed")
    _es_hoy = vista == "Detalle tiempo real"

    # Solo se descarga la pestaña de la vista seleccionada (RT Yesterday es pesada).
    with st.spinner("Cargando llamadas…"):
        base = _datos.realtime_hoy() if _es_hoy else _datos.realtime_ayer()

    st.markdown("""<div class='sbh'>
        <div class='sbh-num' style='color:#34D399!important;background:rgba(52,211,153,0.12);border-color:rgba(52,211,153,0.22)'>02</div>
        <div class='sbh-lbl'>Filtros</div>
        <div class='sbh-rule'></div>
    </div>""", unsafe_allow_html=True)
    sup_sel = st.selectbox("Supervisor", ["Todos"] + sorted(s for s in base["_SUPERVISOR"].unique() if s and s != "Sin asignar"))
    _base_sup = base if sup_sel == "Todos" else base[base["_SUPERVISOR"] == sup_sel]
    asesor_sel = st.selectbox("Asesor", ["Todos"] + sorted(a for a in _base_sup["_ASESOR"].unique() if a and a != "Sin asignar"))
    disp_sel = st.selectbox("Disposición Agrupada", ["Todas"] + [d for d in _DISPOS if d in base["_DISPOSICION"].unique()])
    campana_sel = st.selectbox("Campaña", ["Todas"] + sorted(c for c in base["Campaña"].dropna().unique() if str(c).strip()))

    st.markdown("""
    <div class='sbf'>
        <div class='sbf-card'>
            <div class='sbf-glow'></div>
            <div class='sbf-row'>
                <div class='sbf-avatar'>GC<span class='sbf-online'></span></div>
                <div class='sbf-info'>
                    <div class='sbf-name'>Guillermo Calderón</div>
                    <div class='sbf-role'>Analista WFM · Scala Learning</div>
                </div>
            </div>
        </div>
        <div class='sbf-credit'><span class='sbf-spark'>⚡</span>Desarrollado por Workforce Management</div>
    </div>
    """, unsafe_allow_html=True)

_datos.boton_actualizar()

# ─────────────────────────────────────────────
# FILTRO
# ─────────────────────────────────────────────
b = base.copy()
if sup_sel != "Todos":
    b = b[b["_SUPERVISOR"] == sup_sel]
if asesor_sel != "Todos":
    b = b[b["_ASESOR"] == asesor_sel]
if campana_sel != "Todas":
    b = b[b["Campaña"] == campana_sel]
# `b_disp` aplica además el filtro de disposición (para las tablas que lo usan); `b` no.
b_disp = b if disp_sel == "Todas" else b[b["_DISPOSICION"] == disp_sel]

_fecha_txt = ", ".join(str(d) for d in sorted(base["_FECHA"].dropna().unique())) or "sin datos"
_actualiz = base["_INICIO"].max() if len(base) else pd.NaT

if not len(base):
    st.warning(f"La pestaña **{'RT Day' if _es_hoy else 'RT Yesterday'}** está vacía en este momento. "
               "El módulo se poblará cuando la hoja tenga datos.")
    st.stop()

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@500;600;700&display=swap');
    * {{ font-family:'Inter',sans-serif !important; }}
    span[data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined {{ font-family:'Material Symbols Rounded','Material Symbols Outlined' !important; }}
    [data-testid="stSidebarNav"] {{ display:none !important; }}
    [data-testid="stAppViewContainer"], .main {{
        background:
            radial-gradient(ellipse 90% 55% at 6% -6%, rgba(14,165,233,0.16) 0%, transparent 55%),
            radial-gradient(ellipse 80% 55% at 100% 0%, rgba(99,102,241,0.17) 0%, transparent 55%),
            linear-gradient(160deg,#071310 0%,#082017 45%,#050F0B 100%);
        background-attachment:fixed;
    }}
    [data-testid="stHeader"] {{ background:transparent !important; }}
    .block-container {{ padding-top:2rem; padding-bottom:1rem; }}
    @keyframes sbcPulse {{ 0%,100% {{ opacity:1;transform:scale(1); }} 50% {{ opacity:.3;transform:scale(.6); }} }}
    @keyframes sbcBar {{ 0% {{ background-position:0% 0%; }} 100% {{ background-position:200% 0%; }} }}

    [data-testid="stSidebarCollapseButton"] button,
    div[data-testid="collapsedControl"] button {{
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 10px !important; transition: all .2s ease !important;
    }}
    [data-testid="stSidebarCollapseButton"] button:hover,
    div[data-testid="collapsedControl"] button:hover {{ border-color: rgba(14,165,233,0.45) !important; }}
    [data-testid="stSidebarCollapseButton"] span {{ color: rgba(255,255,255,0.80) !important; font-size:20px !important; }}
    div[data-testid="stSidebarContent"] {{ width:100%!important; box-sizing:border-box!important; padding-right:0.75rem!important; }}
    div[data-testid="stSidebarContent"] > div {{ width:100%!important; }}

    /* ── Sidebar base ── */
    section[data-testid="stSidebar"] > div:first-child {{
        background:
            radial-gradient(ellipse 95% 42% at 8% 0%,    rgba(14,165,233,0.30) 0%, transparent 55%),
            radial-gradient(ellipse 90% 42% at 100% 26%, rgba(129,140,248,0.28) 0%, transparent 55%),
            radial-gradient(ellipse 85% 42% at 50% 102%, rgba(52,211,153,0.15) 0%, transparent 55%),
            linear-gradient(160deg, #071811 0%, #0C2B1D 45%, #061109 100%);
        border-right: 1px solid rgba(255,255,255,0.07);
    }}
    div[data-testid="stSidebarContent"] * {{ color: white !important; }}
    [data-testid="stSidebarHeader"] {{ padding-top:0.6rem!important; padding-bottom:0!important; }}
    [data-testid="stSidebarUserContent"] {{ padding-top:0!important; }}
    section[data-testid="stSidebar"] > div:first-child {{ display:flex!important; flex-direction:column!important; min-height:100vh!important; }}
    [data-testid="stSidebarUserContent"] {{ flex:1 1 auto!important; display:flex!important; flex-direction:column!important; }}
    [data-testid="stSidebarUserContent"] > div {{ flex:1 1 auto!important; display:flex!important; flex-direction:column!important; }}
    [data-testid="stSidebarUserContent"] [data-testid="stElementContainer"]:last-of-type {{ margin-top:auto!important; }}

    /* ── Brand card ── */
    .sbc {{ position:relative;border-radius:20px;overflow:hidden;margin:0 0 20px;padding:20px 18px 18px;
        background:linear-gradient(145deg,rgba(56,189,248,0.12) 0%,rgba(129,140,248,0.09) 55%,rgba(52,211,153,0.07) 100%),rgba(255,255,255,0.04);
        border:1px solid rgba(255,255,255,0.12); }}
    .sbc-orb {{ position:absolute;border-radius:50%;pointer-events:none; }}
    .sbc-orb-1 {{ width:140px;height:140px;background:radial-gradient(circle,rgba(56,189,248,0.18) 0%,transparent 70%);top:-50px;right:-40px; }}
    .sbc-orb-2 {{ width:90px;height:90px;background:radial-gradient(circle,rgba(129,140,248,0.16) 0%,transparent 70%);bottom:-30px;left:-25px; }}
    .sbc-orb-3 {{ width:60px;height:60px;background:radial-gradient(circle,rgba(52,211,153,0.14) 0%,transparent 70%);top:50%;right:12px; }}
    .sbc-live {{ position:absolute;top:14px;right:14px;display:flex;align-items:center;gap:5px;font-size:8px!important;font-weight:800!important;color:#34D399!important;background:rgba(52,211,153,0.13);border:1px solid rgba(52,211,153,0.30);padding:3px 9px 3px 7px;border-radius:99px;letter-spacing:0.10em;z-index:2; }}
    .sbc-pulse {{ width:5px;height:5px;background:#34D399;border-radius:50%;display:inline-block;animation:sbcPulse 1.8s ease-in-out infinite; }}
    .sbc-body {{ position:relative;z-index:1;text-align:center; }}
    .sbc-logo-wrap {{ margin-bottom:10px;display:flex;justify-content:center;align-items:center; }}
    .sbc-logo-img {{ max-width:150px!important;height:auto!important;filter:drop-shadow(0 4px 14px rgba(56,189,248,0.45)) brightness(1.05);display:block; }}
    .sbc-name {{ font-size:13px!important;font-weight:700!important;color:rgba(255,255,255,0.88)!important;letter-spacing:0!important;margin-bottom:4px!important; }}
    .sbc-org {{ font-size:10px!important;color:rgba(255,255,255,0.35)!important;margin-bottom:16px!important; }}
    .sbc-stats {{ display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.22);border-radius:12px;padding:10px 8px;border:1px solid rgba(255,255,255,0.07); }}
    .sbc-stat {{ flex:1;text-align:center; }}
    .sbc-sv {{ display:block;font-size:14px!important;font-weight:900!important;color:white!important;line-height:1;margin-bottom:3px; }}
    .sbc-sl {{ display:block;font-size:8px!important;font-weight:700!important;color:rgba(255,255,255,0.28)!important;letter-spacing:0.10em;text-transform:uppercase; }}
    .sbc-sep {{ width:1px;height:28px;background:rgba(255,255,255,0.09);flex-shrink:0; }}
    .sbc-bar {{ position:absolute;bottom:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#38BDF8,#818CF8,#34D399,#F59E0B,#38BDF8);background-size:300% 100%;animation:sbcBar 4s linear infinite; }}

    /* ── Section headers (sidebar) ── */
    .sbh {{ display:flex;align-items:center;gap:10px;margin:24px 0 12px; }}
    .sbh-num {{ font-size:10px!important;font-weight:900!important;width:28px;height:22px;border-radius:7px;border:1px solid;display:flex;align-items:center;justify-content:center;flex-shrink:0;letter-spacing:0.04em; }}
    .sbh-lbl {{ font-size:10px!important;font-weight:800!important;color:rgba(255,255,255,0.60)!important;letter-spacing:0.14em!important;text-transform:uppercase!important;white-space:nowrap!important; }}
    .sbh-rule {{ flex:1;height:1px;background:rgba(255,255,255,0.08); }}

    /* ── Dropdowns / selects ── */
    ul[role="listbox"] *, li[role="option"], li[role="option"] * {{ color:#1E293B !important; }}
    li[role="option"]:hover, li[role="option"][aria-selected="true"] {{ background:#F1F5F9 !important; }}
    div[data-testid="stSidebarContent"] .stSelectbox [data-baseweb="select"] span,
    div[data-testid="stSidebarContent"] .stSelectbox [data-baseweb="select"] div[class*="ValueContainer"] *,
    div[data-testid="stSidebarContent"] .stSelectbox [data-baseweb="select"] input {{ color:white !important; }}
    div[data-testid="stSidebarContent"] label,
    div[data-testid="stSidebarContent"] .stSelectbox label,
    div[data-testid="stSidebarContent"] [data-testid="stWidgetLabel"],
    div[data-testid="stSidebarContent"] [data-testid="stWidgetLabel"] p,
    div[data-testid="stSidebarContent"] [data-testid="stWidgetLabel"] span {{ font-size:11px!important;font-weight:500!important;color:rgba(255,255,255,0.50)!important; }}
    div[data-testid="stSidebarContent"] .stSelectbox > div > div,
    div[data-testid="stSidebarContent"] .stSelectbox > label + div > div {{ background:rgba(255,255,255,0.05)!important;border:1px solid rgba(255,255,255,0.12)!important;border-radius:9px!important;transition:border-color .18s, box-shadow .18s!important; }}
    div[data-testid="stSidebarContent"] .stSelectbox > div > div:hover {{ border-color:rgba(56,189,248,0.50)!important;box-shadow:0 0 0 3px rgba(56,189,248,0.10)!important; }}

    /* ── Footer ── */
    .sbf {{ margin-top:26px;padding:0; }}
    .sbf-card {{ position:relative;overflow:hidden;border-radius:16px;padding:14px 14px;background:linear-gradient(150deg,rgba(56,189,248,0.10),rgba(129,140,248,0.06));border:1px solid rgba(255,255,255,0.10);box-shadow:inset 0 1px 0 rgba(255,255,255,0.08); }}
    .sbf-glow {{ position:absolute;width:120px;height:120px;border-radius:50%;top:-50px;right:-40px;background:radial-gradient(circle,rgba(56,189,248,0.20),transparent 70%);pointer-events:none; }}
    .sbf-row {{ display:flex;align-items:center;gap:12px;position:relative;z-index:1; }}
    .sbf-avatar {{ position:relative;width:42px;height:42px;border-radius:13px;background:linear-gradient(135deg,#38BDF8 0%,#818CF8 100%);display:flex;align-items:center;justify-content:center;font-size:14px!important;font-weight:900!important;color:white!important;flex-shrink:0;letter-spacing:0.5px;box-shadow:0 6px 18px rgba(56,189,248,0.45),inset 0 1px 0 rgba(255,255,255,0.3); }}
    .sbf-online {{ position:absolute;bottom:-2px;right:-2px;width:12px;height:12px;border-radius:50%;background:#34D399;border:2.5px solid #130A2B;box-shadow:0 0 8px rgba(52,211,153,0.8);animation:sbcPulse 2s ease-in-out infinite; }}
    .sbf-name {{ font-size:12px!important;font-weight:700!important;color:rgba(255,255,255,0.92)!important;margin-bottom:3px!important; }}
    .sbf-role {{ font-size:10px!important;color:rgba(255,255,255,0.42)!important;line-height:1.3; }}
    .sbf-credit {{ display:flex;align-items:center;justify-content:center;gap:5px;margin-top:12px;font-size:9px!important;font-weight:600!important;color:rgba(255,255,255,0.30)!important;text-align:center;letter-spacing:0.06em; }}
    .sbf-spark {{ font-size:10px; }}

    .st-key-hdrbanner {{ position:relative;overflow:hidden;
        background:radial-gradient(ellipse 70% 130% at 2% -15%,rgba(14,165,233,0.34),transparent 60%),radial-gradient(ellipse 65% 130% at 100% 120%,rgba(129,140,248,0.34),transparent 60%),linear-gradient(155deg,#071811 0%,#0C2B1D 50%,#061109 100%);
        border:1px solid rgba(255,255,255,0.10);border-radius:20px;padding:18px 30px;margin-bottom:18px; }}
    .hb-eyebrow {{ display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.16);border-radius:99px;padding:5px 13px;margin-bottom:11px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.78);letter-spacing:0.12em;text-transform:uppercase; }}
    .hb-dot {{ width:7px;height:7px;border-radius:50%;background:#34D399;box-shadow:0 0 9px #34D399;animation:sbcPulse 1.8s ease-in-out infinite; }}
    .hb-title {{ font-family:'Space Grotesk',sans-serif!important;font-size:29px;font-weight:700;color:white;margin:0 0 9px;letter-spacing:-0.8px; }}
    .hb-meta {{ display:flex;flex-wrap:wrap;gap:8px; }}
    .hb-chip {{ display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.13);border-radius:9px;padding:5px 11px;font-size:11px;font-weight:600;color:rgba(255,255,255,0.74); }}
    .hb-chip b {{ color:#fff; }}
    .nav-lbl {{ font-size:9px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:rgba(255,255,255,0.40);margin:9px 0 7px; }}
    .st-key-hdrbanner [data-testid="stButton"] > button {{ color:#CBD3F2 !important;border-radius:9px !important;font-size:10px !important;font-weight:700 !important;height:32px !important;min-height:32px !important;padding:0 11px !important;border:1px solid rgba(255,255,255,0.12) !important;background:linear-gradient(180deg,rgba(255,255,255,0.085),rgba(255,255,255,0.025)) !important;white-space:nowrap !important; }}
    .st-key-hdrbanner [data-testid="stButton"] > button:hover {{ color:#EAF2FF !important;border-color:rgba(125,211,252,0.42) !important; }}
    .st-key-hdrbanner [data-testid="stButton"] > button[kind="primary"] {{ color:#F4F9FF !important;border:1px solid rgba(56,189,248,0.55) !important;background:linear-gradient(180deg,rgba(56,189,248,0.30),rgba(59,130,246,0.16)) !important; }}

    .kpi-card {{ background:linear-gradient(160deg,rgba(255,255,255,0.07),rgba(255,255,255,0.02));border-radius:20px;padding:20px 20px 16px;border:1px solid rgba(255,255,255,0.10);box-shadow:0 20px 44px -18px rgba(0,0,0,0.7);position:relative;overflow:hidden;min-height:140px;display:flex;flex-direction:column;justify-content:space-between;transition:transform .24s ease,border-color .24s ease; }}
    .kpi-card:hover {{ transform:translateY(-6px);border-color:var(--kc,{COLOR_ACCENT}); }}
    .kpi-card::before {{ content:'';position:absolute;top:0;left:0;right:0;height:4px;background:var(--kc,{COLOR_ACCENT}); }}
    .kpi-card::after {{ content:'';position:absolute;top:-40px;right:-40px;width:120px;height:120px;background:radial-gradient(circle,var(--kc,{COLOR_ACCENT}),transparent 70%);opacity:0.18;border-radius:50%; }}
    .kpi-bg-icon {{ position:absolute;bottom:12px;right:16px;font-size:44px;opacity:0.10;line-height:1; }}
    .kpi-label {{ font-size:10px;color:rgba(255,255,255,0.50);font-weight:700;text-transform:uppercase;letter-spacing:0.10em; }}
    .kpi-value {{ font-family:'Space Grotesk',sans-serif!important;font-size:29px;font-weight:700;line-height:1.1;margin:9px 0 4px;letter-spacing:-0.5px; }}
    .kpi-sub {{ font-size:11px;color:rgba(255,255,255,0.42); }}
    .kpi-bar-wrap {{ background:rgba(255,255,255,0.09);border-radius:99px;height:5px;margin-top:10px;overflow:hidden; }}
    .kpi-bar-fill {{ height:5px;border-radius:99px; }}

    .sec-header {{ background:radial-gradient(ellipse at 12% 35%,rgba(255,255,255,0.18),transparent 55%),var(--sc,{COLOR_PRIMARY});border-radius:20px;padding:20px 26px;margin:32px 0 16px;display:flex;align-items:center;gap:16px;border:1px solid rgba(255,255,255,0.14);position:relative;overflow:hidden; }}
    .sec-header::after {{ content:'';position:absolute;right:-35px;bottom:-45px;width:150px;height:150px;background:rgba(255,255,255,0.07);border-radius:50%; }}
    .sec-icon {{ width:52px;height:52px;border-radius:15px;display:flex;align-items:center;justify-content:center;font-size:25px;flex-shrink:0;background:rgba(255,255,255,0.18)!important;border:1px solid rgba(255,255,255,0.28)!important;position:relative;z-index:1; }}
    .sec-title {{ font-size:18px;font-weight:800;color:white;margin:0 0 4px;letter-spacing:-0.4px;position:relative;z-index:1; }}
    .sec-desc {{ font-size:12px;color:rgba(255,255,255,0.78);margin:0;position:relative;z-index:1; }}
    .sec-tag {{ font-size:10px;font-weight:700;color:white;background:rgba(255,255,255,0.20);border:1px solid rgba(255,255,255,0.35);padding:5px 14px;border-radius:99px;text-transform:uppercase;flex-shrink:0;align-self:flex-start;position:relative;z-index:1; }}

    .chart-hdr {{ display:flex;align-items:center;gap:12px;padding:12px 16px;background:linear-gradient(180deg,rgba(255,255,255,0.07),rgba(255,255,255,0.025));border-radius:14px;border:1px solid rgba(255,255,255,0.10);border-left:4px solid var(--cc,{COLOR_ACCENT});margin-bottom:12px; }}
    .ch-icon {{ font-size:18px;flex-shrink:0;width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12); }}
    .ch-title {{ font-size:13px;font-weight:800;color:#F1F4FF;margin:0 0 1px; }}
    .ch-sub {{ font-size:10.5px;color:rgba(255,255,255,0.45);margin:0; }}

    .tbl-hdr {{ padding:14px 20px;border-radius:14px;display:flex;align-items:center;gap:12px;margin-bottom:6px;background:linear-gradient(135deg,#0C2B1D,#0EA5E9); }}
    .tbl-hdr-icon {{ font-size:22px;flex-shrink:0; }}
    .tbl-hdr-title {{ font-size:14px;font-weight:800;color:white;margin:0 0 2px; }}
    .tbl-hdr-desc {{ font-size:11px;color:rgba(255,255,255,0.72);margin:0; }}
    .tbl-hdr-badge {{ font-size:10px;font-weight:700;color:white;background:rgba(255,255,255,0.20);border:1px solid rgba(255,255,255,0.35);padding:4px 12px;border-radius:99px;flex-shrink:0;margin-left:auto; }}

    div[data-testid="stPlotlyChart"] {{ background:linear-gradient(160deg,rgba(255,255,255,0.05),rgba(255,255,255,0.015)) !important;border-radius:18px !important;border:1px solid rgba(255,255,255,0.09) !important;padding:10px !important; }}

    .rt-tabla-wrap {{ overflow:auto;max-height:520px;border-radius:16px;border:1px solid rgba(255,255,255,0.10);box-shadow:0 20px 46px -18px rgba(0,0,0,0.7);background:rgba(6,15,11,0.55);margin-bottom:22px; }}
    .rt-tabla {{ width:100%;border-collapse:collapse;font-size:11px;white-space:nowrap; }}
    .rt-tabla th, .rt-tabla td {{ text-align:center;padding:7px 10px; }}
    .rt-tabla thead th {{ position:sticky;top:0;z-index:1;background:#10231B;color:rgba(255,255,255,0.94);font-weight:600;border-bottom:1px solid rgba(255,255,255,0.10);font-size:10px;letter-spacing:0.02em; }}
    .rt-tabla thead th.left {{ text-align:left; }}
    .rt-tabla tbody td {{ color:rgba(225,232,250,0.92);border-bottom:1px solid rgba(255,255,255,0.045); }}
    .rt-tabla tbody tr:nth-child(odd) {{ background:rgba(10,24,18,0.45); }}
    .rt-tabla tbody tr:hover {{ background:rgba(14,165,233,0.09); }}
    .rt-tabla td.name {{ font-weight:700;color:white;text-align:left; }}
    .rt-tabla tr.total td {{ font-weight:800!important;background:rgba(52,211,153,0.16)!important; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ENCABEZADO
# ─────────────────────────────────────────────
_home_pg = st.Page("home.py", title="Inicio", icon="🏠", default=True)
_insc_pg = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
_mat_pg = st.Page("pages/2_Matriculas.py", title="Matrículas", icon="🎓")
_cuart_pg = st.Page("pages/3_Cuartiles.py", title="Cuartiles", icon="🏆")

with st.container(key="hdrbanner"):
    st.markdown(f"""
    <div class='hb-eyebrow'><span class='hb-dot'></span>Centro de Control · Uniminuto 2026</div>
    <div class='hb-title'>Real Time</div>
    <div class='hb-meta'>
        <span class='hb-chip'>📅 <b>{_fecha_txt}</b></span>
        <span class='hb-chip'>🔄 Última llamada <b>{_actualiz.strftime('%H:%M') if pd.notna(_actualiz) else '—'}</b></span>
        <span class='hb-chip'>{"🟢 En vivo" if _es_hoy else "🔒 Cerrado"}</span>
    </div>
    <div class='nav-lbl'>⚡ Navegación</div>
    """, unsafe_allow_html=True)
    nb1, nb2, nb3, nb4, nb5, _s = st.columns([1.0, 1.35, 1.3, 1.35, 1.2, 1.0], vertical_alignment="center")
    with nb1:
        if st.button("🏠 Inicio", key="hdr_home", width="stretch"):
            st.switch_page(_home_pg)
    with nb2:
        if st.button("📝 Inscripciones", key="hdr_insc", width="stretch"):
            st.switch_page(_insc_pg)
    with nb3:
        if st.button("🎓 Matrículas", key="hdr_mat", width="stretch"):
            st.switch_page(_mat_pg)
    with nb4:
        if st.button("🏆 Cuartiles", key="hdr_cuart", width="stretch"):
            st.switch_page(_cuart_pg)
    with nb5:
        st.button("📞 Real time", key="hdr_cont", width="stretch", type="primary")

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
def kpi_bar(pct, color):
    return f"<div class='kpi-bar-wrap'><div class='kpi-bar-fill' style='width:{min(pct,100):.0f}%;background:{color}'></div></div>"


_bg = b[b["_GESTIONADA"]]          # gestionadas: excluye No Encontrado / Llamada Entrante
_tot = len(_bg)
_tot_marcadas = len(b)
_efectivas = int(_bg["_EFECTIVO"].sum())
_interesados = int((_bg["_DISPOSICION"] == "Efectivo Interesado").sum())
_seg_llamadas = _bg["_SEG_LLAMADA"].sum()
_asesores_activos = _bg.loc[_bg["_ASESOR"] != "Sin asignar", "_ASESOR"].nunique()
_pct_efec = _efectivas / _tot * 100 if _tot else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_ACCENT}'>
        <div class='kpi-bg-icon'>📞</div>
        <div><div class='kpi-label'>Llamadas gestionadas</div>
        <div class='kpi-value' style='color:#7DD3FC'>{_tot:,}</div>
        <div class='kpi-sub'>{_tot_marcadas:,} marcadas en total (incl. no encontrado)</div></div>
        {kpi_bar(_tot / _tot_marcadas * 100 if _tot_marcadas else 0, COLOR_ACCENT)}
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_SUCCESS}'>
        <div class='kpi-bg-icon'>✅</div>
        <div><div class='kpi-label'>Contacto efectivo</div>
        <div class='kpi-value' style='color:{COLOR_SUCCESS}'>{_efectivas:,}</div>
        <div class='kpi-sub'>{_pct_efec:.1f}% de las llamadas</div></div>
        {kpi_bar(_pct_efec, COLOR_SUCCESS)}
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class='kpi-card' style='--kc:#818CF8'>
        <div class='kpi-bg-icon'>🎯</div>
        <div><div class='kpi-label'>Efectivo Interesado</div>
        <div class='kpi-value' style='color:#818CF8'>{_interesados:,}</div>
        <div class='kpi-sub'>contactos con interés</div></div>
        {kpi_bar(_interesados / max(_efectivas, 1) * 100, "#818CF8")}
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_WARNING}'>
        <div class='kpi-bg-icon'>👥</div>
        <div><div class='kpi-label'>Asesores en gestión</div>
        <div class='kpi-value' style='color:{COLOR_WARNING}'>{_asesores_activos}</div>
        <div class='kpi-sub'>tiempo en llamadas: {_hms(_seg_llamadas)}</div></div>
        {kpi_bar(_asesores_activos, COLOR_WARNING)}
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COMPARATIVOS
# ─────────────────────────────────────────────
st.markdown(f"""<div class='sec-header' style='--sc:#38BDF8'>
    <div class='sec-icon'>📈</div>
    <div class='sec-text'><div class='sec-title'>Comparativos</div>
    <div class='sec-desc'>Ritmo de llamadas por hora, disposición de la gestión y comparativo por supervisor y campaña.</div></div>
    <span class='sec-tag' style='background:#38BDF8'>Gestión</span>
</div>""", unsafe_allow_html=True)


def _base_layout(h=300):
    return dict(height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
                margin=dict(l=45, r=20, t=15, b=35))


_ax = dict(gridcolor="rgba(255,255,255,0.07)", tickfont=dict(size=10, color="rgba(255,255,255,0.6)"), automargin=True)

def _orden_sin_asignar_ultimo(df, col_orden):
    """Ordena por col_orden desc pero deja las filas 'Sin asignar' al final."""
    d = df.copy()
    d["_z"] = (d.index.astype(str) == "Sin asignar").astype(int)
    return d.sort_values(["_z", col_orden], ascending=[True, False]).drop(columns="_z")


# Llamadas por hora (gestionadas)
_gh = _bg
_por_hora = _gh.groupby("_HORA").size() if len(_gh) else pd.Series(dtype=int)
if len(_por_hora):
    _por_hora = _por_hora.reindex(range(int(_por_hora.index.min()), int(_por_hora.index.max()) + 1), fill_value=0)
_ef_hora = _gh[_gh["_EFECTIVO"]].groupby("_HORA").size().reindex(_por_hora.index, fill_value=0) if len(_gh) else pd.Series(dtype=int)
st.markdown("<div class='chart-hdr' style='--cc:#38BDF8'><span class='ch-icon'>🕒</span><div><div class='ch-title'>Llamadas por hora</div><div class='ch-sub'>Gestionadas y contacto efectivo</div></div></div>", unsafe_allow_html=True)
_fh = go.Figure()
_fh.add_bar(x=[f"{h}:00" for h in _por_hora.index], y=list(_por_hora.values), name="Gestionadas", marker_color="#38BDF8")
_fh.add_scatter(x=[f"{h}:00" for h in _ef_hora.index], y=list(_ef_hora.values), name="Efectivas", mode="lines+markers", line=dict(color=COLOR_SUCCESS, width=2.5, shape="spline"))
_fh.update_layout(**_base_layout(300), legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10)), xaxis=_ax, yaxis=_ax)
st.plotly_chart(_fh, width="stretch", config={"displayModeBar": False})

c1, c2 = st.columns(2)
with c1:
    st.markdown("<div class='chart-hdr' style='--cc:#818CF8'><span class='ch-icon'>🧩</span><div><div class='ch-title'>Disposición de la gestión</div><div class='ch-sub'>Distribución de llamadas por resultado</div></div></div>", unsafe_allow_html=True)
    _dc = _bg["_DISPOSICION"].value_counts()
    _dc = _dc[[d for d in _DISPOS if d in _dc.index]] if len(_dc) else _dc
    _fd = go.Figure(go.Bar(x=list(_dc.values), y=list(_dc.index), orientation="h",
                           marker=dict(color=[_DISPOS_COLOR.get(k, "#94A3B8") for k in _dc.index]),
                           text=list(_dc.values), textposition="outside", cliponaxis=False))
    _fd.update_layout(**_base_layout(320), xaxis=_ax, yaxis=dict(**_ax, autorange="reversed"))
    st.plotly_chart(_fd, width="stretch", config={"displayModeBar": False})
with c2:
    st.markdown("<div class='chart-hdr' style='--cc:#34D399'><span class='ch-icon'>📣</span><div><div class='ch-title'>Por campaña</div><div class='ch-sub'>Top 10 por llamadas gestionadas</div></div></div>", unsafe_allow_html=True)
    _cc = _bg.groupby("Campaña").size().sort_values(ascending=False).head(10).sort_values()
    _fc = go.Figure(go.Bar(x=list(_cc.values), y=list(_cc.index), orientation="h", marker_color="#34D399",
                           text=list(_cc.values), textposition="outside", cliponaxis=False))
    _fc.update_layout(**_base_layout(320), xaxis=_ax, yaxis=_ax)
    st.plotly_chart(_fc, width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# TABLA 1 — Gestión por Asesor (réplica del pivot "Disposición Agrupada")
#   Inscripción / Completada = cruce con la pestaña "Inscripciones" (SIU)
#   disposiciones = conteo de "Disposición Agrupada" en el log · Total Llamadas = suma de esas
# ─────────────────────────────────────────────
st.markdown(f"""<div class='sec-header' style='--sc:{COLOR_PRIMARY}'>
    <div class='sec-icon'>🧑‍💼</div>
    <div class='sec-text'><div class='sec-title'>Gestión por Asesor</div>
    <div class='sec-desc'>Inscripción y Completada vienen del SIU (pestaña Inscripciones); las disposiciones, del log de llamadas.</div></div>
    <span class='sec-tag' style='background:{COLOR_PRIMARY}'>Tabla 1</span>
</div>""", unsafe_allow_html=True)


def _ins(asesor, col):
    try:
        return int(_INSC.loc[asesor, col]) if asesor in _INSC.index else 0
    except Exception:
        return 0


def _conteo(df, idx_col, cat_col, cats):
    """crosstab vectorizado: filas = idx_col, columnas = cats (reindexadas, faltantes = 0)."""
    if not len(df):
        return pd.DataFrame(0, index=[], columns=cats)
    return pd.crosstab(df[idx_col], df[cat_col]).reindex(columns=cats, fill_value=0)


def _tabla1(df):
    g = df.groupby("_ASESOR")
    fd = pd.DataFrame({"SUP": g["_SUPERVISOR"].first()})
    cnt = _conteo(df, "_ASESOR", "_DISPOSICION", _DISPOS)
    for d in _DISPOS:
        fd[d] = cnt[d].reindex(fd.index, fill_value=0)
    fd["TOTAL"] = fd[_DISPOS].sum(axis=1)
    fd["INSCR"] = [_ins(a, "INSCRIPCION") for a in fd.index]
    fd["COMPL"] = [_ins(a, "COMPLETADA") for a in fd.index]
    fd = _orden_sin_asignar_ultimo(fd, "TOTAL")
    cols_disp = [d.replace("Efectivo ", "Efec. ").replace("Contacto con ", "") for d in _DISPOS]
    ths = "<th class='left'>Asesor</th><th class='left'>Supervisor</th><th>Inscripción</th><th>Completada</th>" + \
          "".join(f"<th>{c}</th>" for c in cols_disp) + "<th>Total Llamadas</th>"
    rows = "".join(
        f"<tr><td class='name'>{a}</td><td class='name' style='font-weight:400;color:rgba(255,255,255,0.6)'>{r['SUP']}</td>"
        f"<td>{int(r['INSCR'])}</td><td>{int(r['COMPL'])}</td>"
        + "".join(f"<td>{int(r[d])}</td>" for d in _DISPOS)
        + f"<td>{int(r['TOTAL'])}</td></tr>"
        for a, r in fd.iterrows()
    )
    t = fd.sum(numeric_only=True)
    rows += (f"<tr class='total'><td class='name'>Totales</td><td></td><td>{int(t['INSCR'])}</td><td>{int(t['COMPL'])}</td>"
             + "".join(f"<td>{int(t[d])}</td>" for d in _DISPOS) + f"<td>{int(t['TOTAL'])}</td></tr>")
    st.markdown(f"<div class='rt-tabla-wrap'><table class='rt-tabla'><thead><tr>{ths}</tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)


_tabla1(b)

# ─────────────────────────────────────────────
# TABLA 2 — Detalle por disposición (réplica pivot "Efectivo Interesado")
#   usa el filtro de Disposición Agrupada del sidebar (por defecto: Efectivo Interesado)
# ─────────────────────────────────────────────
_disp2 = disp_sel if disp_sel != "Todas" else "Efectivo Interesado"
_b2 = b[b["_DISPOSICION"] == _disp2]
st.markdown(f"""<div class='sec-header' style='--sc:#818CF8'>
    <div class='sec-icon'>🎯</div>
    <div class='sec-text'><div class='sec-title'>Detalle — {_disp2}</div>
    <div class='sec-desc'>TMO-AHT = tiempo en llamadas ÷ llamadas de esa disposición. Distribución por duración de la gestión.</div></div>
    <span class='sec-tag' style='background:#818CF8'>Tabla 2</span>
</div>""", unsafe_allow_html=True)
if len(_b2):
    g2 = _b2.groupby("_ASESOR")
    ef_asesor = b[b["_EFECTIVO"]].groupby("_ASESOR").size()
    f2 = pd.DataFrame({"SUP": g2["_SUPERVISOR"].first(), "LLAM": g2.size(), "SEG": g2["_SEG_LLAMADA"].sum()})
    f2["EFEC_TOT"] = [int(ef_asesor.get(a, 0)) for a in f2.index]
    f2["INSCR"] = [_ins(a, "INSCRIPCION") for a in f2.index]
    f2["COMPL"] = [_ins(a, "COMPLETADA") for a in f2.index]
    bkc = _conteo(_b2, "_ASESOR", "_BUCKET", _datos.RT_BUCKETS)
    for bk in _datos.RT_BUCKETS:
        f2[bk] = bkc[bk].reindex(f2.index, fill_value=0)
    f2 = _orden_sin_asignar_ultimo(f2, "LLAM")
    ths = ("<th class='left'>Asesor</th><th class='left'>Supervisor</th><th>Inscripción</th><th>Completada</th>"
           "<th>Efectivas totales</th><th>TMO-AHT</th><th>Llamadas</th>"
           + "".join(f"<th>{bk}</th>" for bk in _datos.RT_BUCKETS))
    rows = "".join(
        f"<tr><td class='name'>{a}</td><td class='name' style='font-weight:400;color:rgba(255,255,255,0.6)'>{r['SUP']}</td>"
        f"<td>{int(r['INSCR'])}</td><td>{int(r['COMPL'])}</td><td>{int(r['EFEC_TOT'])}</td>"
        f"<td>{_hms(r['SEG'] / r['LLAM']) if r['LLAM'] else '—'}</td><td>{int(r['LLAM'])}</td>"
        + "".join(f"<td>{int(r[bk])}</td>" for bk in _datos.RT_BUCKETS) + "</tr>"
        for a, r in f2.iterrows()
    )
    t = f2.sum(numeric_only=True)
    rows += (f"<tr class='total'><td class='name'>Totales</td><td></td><td>{int(t['INSCR'])}</td><td>{int(t['COMPL'])}</td>"
             f"<td>{int(t['EFEC_TOT'])}</td><td>{_hms(t['SEG'] / t['LLAM']) if t['LLAM'] else '—'}</td><td>{int(t['LLAM'])}</td>"
             + "".join(f"<td>{int(t[bk])}</td>" for bk in _datos.RT_BUCKETS) + "</tr>")
    st.markdown(f"<div class='rt-tabla-wrap'><table class='rt-tabla'><thead><tr>{ths}</tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)
else:
    st.caption(f"Sin llamadas de {_disp2} para los filtros seleccionados.")

# ─────────────────────────────────────────────
# TABLA 3 — Tiempos por asesor (réplica pivot "Tiempo Tipificación / en llamadas")
# ─────────────────────────────────────────────
st.markdown(f"""<div class='sec-header' style='--sc:#F97316'>
    <div class='sec-icon'>⏱️</div>
    <div class='sec-text'><div class='sec-title'>Tiempos por Asesor</div>
    <div class='sec-desc'>Tiempo de tipificación (conclusión), ocio real y tiempo en llamadas — total y por disposición.</div></div>
    <span class='sec-tag' style='background:#F97316'>Tabla 3</span>
</div>""", unsafe_allow_html=True)
g3 = b.groupby("_ASESOR")
f3 = pd.DataFrame({
    "SUP": g3["_SUPERVISOR"].first(),
    "TIP": g3["_SEG_TIPIF"].sum(), "OCIO": g3["_SEG_OCIO"].sum(), "LLAM": g3["_SEG_LLAMADA"].sum(),
})
f3["LLAM_EI"] = b[b["_DISPOSICION"] == "Efectivo Interesado"].groupby("_ASESOR")["_SEG_LLAMADA"].sum().reindex(f3.index).fillna(0)
f3["LLAM_ENI"] = b[b["_DISPOSICION"] == "Efectivo No Interesado"].groupby("_ASESOR")["_SEG_LLAMADA"].sum().reindex(f3.index).fillna(0)
f3 = _orden_sin_asignar_ultimo(f3, "LLAM")
rows = "".join(
    f"<tr><td class='name'>{a}</td><td class='name' style='font-weight:400;color:rgba(255,255,255,0.6)'>{r['SUP']}</td>"
    f"<td style='color:#FB7185'>{_hms(r['TIP'])}</td><td style='color:#FB7185'>{_hms(r['OCIO'])}</td>"
    f"<td style='color:#34D399'>{_hms(r['LLAM'])}</td><td style='color:#34D399'>{_hms(r['LLAM_EI'])}</td><td style='color:#34D399'>{_hms(r['LLAM_ENI'])}</td></tr>"
    for a, r in f3.iterrows()
)
t = f3.sum(numeric_only=True)
rows += (f"<tr class='total'><td class='name'>Totales</td><td></td>"
         f"<td>{_hms(t['TIP'])}</td><td>{_hms(t['OCIO'])}</td><td>{_hms(t['LLAM'])}</td>"
         f"<td>{_hms(t['LLAM_EI'])}</td><td>{_hms(t['LLAM_ENI'])}</td></tr>")
st.markdown(
    "<div class='rt-tabla-wrap'><table class='rt-tabla'><thead><tr>"
    "<th class='left'>Asesor</th><th class='left'>Supervisor</th><th>Tiempo Tipificación</th><th>Tiempo Ocio Real</th>"
    "<th>T. en llamadas · Total</th><th>· Efectivo Interesado</th><th>· Efectivo No Interesado</th>"
    f"</tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ALERTAS TIPIFICACIONES — réplica de la hoja ALERTAS
#   filtro: Disposición Agrupada = "No Contacto"  ·  Tiempo Total = Σ Tiempo Conc.
#   Tiempo BF = Σ Tiempo Ocio  ·  STATUS = OJT si el agente está en la hoja Socio
# ─────────────────────────────────────────────
if _es_hoy:
    _nc = base[(base["_DISPOSICION"] == "No Contacto") & (base["_ASESOR"] != "Sin asignar")]
    if len(_nc):
        al = _nc.groupby(["_ASESOR", "_SUPERVISOR"]).agg(
            LLAM=("_ASESOR", "size"), T_TOTAL=("_SEG_TIPIF", "sum"), T_BF=("_SEG_OCIO", "sum"),
        ).reset_index().sort_values("T_TOTAL", ascending=False)
        al["STATUS"] = al["_ASESOR"].apply(lambda a: "OJT" if a in _socio else "Operación")
        al = al.head(25)
        rows = "".join(
            f"<tr><td class='name'>{r['_ASESOR']}</td>"
            f"<td class='name' style='font-weight:400;color:rgba(255,255,255,0.6)'>{r['_SUPERVISOR']}</td>"
            f"<td>{int(r['LLAM'])}</td>"
            f"<td style='color:#FB7185;font-weight:700'>{_hms(r['T_TOTAL'])}</td>"
            f"<td>{_hms(r['T_BF'])}</td>"
            f"<td>{r['STATUS']}</td></tr>"
            for _, r in al.iterrows()
        )
        st.markdown(f"""<div class='tbl-hdr' style='background:linear-gradient(135deg,#7f1d1d,#F43F5E)'>
            <span class='tbl-hdr-icon'>🔔</span>
            <div class='tbl-hdr-body'><div class='tbl-hdr-title'>ALERTAS TIPIFICACIONES</div>
            <div class='tbl-hdr-desc'>Disposición Agrupada = No Contacto · ordenado por Tiempo Total · top 25</div></div>
            <span class='tbl-hdr-badge'>{len(al)} agentes</span></div>""", unsafe_allow_html=True)
        st.markdown(
            "<div class='rt-tabla-wrap'><table class='rt-tabla'><thead><tr>"
            "<th class='left'>Agente</th><th class='left'>Supervisor</th><th>Cant. Llamadas</th>"
            "<th>Tiempo Total</th><th>Tiempo BF</th><th>STATUS</th>"
            "</tr></thead><tbody>" + rows + "</tbody></table></div>", unsafe_allow_html=True,
        )
    else:
        st.caption("Sin llamadas de No Contacto en el día.")
