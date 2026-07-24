import base64
import io
import urllib.parse
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Hoja de Google Sheets (compartida como "Cualquiera con el enlace: Lector").
_SHEET_ID = "1eJYJxr_9qOF4yTLjXU1fr1P9asoXdnzoY_MkWME9FhY"


def _url_hoja(sheet_id: str, nombre_hoja: str) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nombre_hoja)}"
    )


# ─────────────────────────────────────────────
# COLORES (mismo esquema que el resto del dashboard, acento rosa como en el home)
# ─────────────────────────────────────────────
COLOR_PRIMARY = "#065F46"
COLOR_ACCENT  = "#F43F5E"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER  = "#EF4444"

_MES_ORDEN = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

_PALETA = ["#F43F5E", "#38BDF8", "#818CF8", "#34D399", "#F59E0B", "#A78BFA", "#FB923C", "#2DD4BF"]


# ─────────────────────────────────────────────
# DESCARGA (idéntico al resto de páginas)
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _excel_bytes(df):
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def df_descarga(df, nombre_archivo, **kwargs):
    st.dataframe(df, **kwargs)
    b64 = base64.b64encode(_excel_bytes(df)).decode()
    st.markdown(
        f'<div style="text-align:right;margin-top:-6px;margin-bottom:8px">'
        f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" '
        f'download="{nombre_archivo}" '
        f'style="font-size:0.72rem;color:rgba(255,255,255,0.35);text-decoration:none;letter-spacing:0.03em" '
        f'onmouseover="this.style.color=\'rgba(255,255,255,0.75)\'" '
        f'onmouseout="this.style.color=\'rgba(255,255,255,0.35)\'">'
        f'↓ Exportar Excel</a></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _cargar_leads() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID, "Resumen diario"), encoding="utf-8", low_memory=False)
    df.columns = df.columns.str.strip()
    df["_FECHA"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["_FECHA"]).copy()
    df["_USUARIO"] = df["Usuario"].astype(str).str.strip().str.lower()
    df["_NOMBRE"] = df["Nombre"].fillna(df["Usuario"])
    df["_CC"] = pd.to_numeric(df["Cedula"], errors="coerce").astype("Int64")
    df["_INSUMO"] = pd.to_numeric(df["Leads asignados ese día"], errors="coerce").fillna(0).astype(int)
    df["MES"] = df["_FECHA"].dt.month.map(lambda m: _MES_ORDEN[int(m) - 1])
    df["AÑO"] = df["_FECHA"].dt.year
    return df


def _ultimo_valor(serie: pd.Series) -> str:
    """Última asignación no vacía de Supervisor/Coordinador en el rango (puede ir llenándose con el tiempo)."""
    s = serie.dropna()
    return str(s.iloc[-1]) if len(s) else "Sin asignar"


def _tabla_usuarios(d: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for usuario, g in d.sort_values("_FECHA").groupby("_USUARIO"):
        filas.append({
            "USUARIO": g["Usuario"].iloc[-1],
            "NOMBRE": g["_NOMBRE"].iloc[-1],
            "SUPERVISOR": _ultimo_valor(g["Supervisor"]),
            "COORDINADOR": _ultimo_valor(g["Coordinador"]),
            "INSUMO": int(g["_INSUMO"].sum()),
            "DIAS": g["_FECHA"].nunique(),
        })
    tabla = pd.DataFrame(filas)
    if not len(tabla):
        return pd.DataFrame(columns=["USUARIO", "NOMBRE", "SUPERVISOR", "COORDINADOR", "INSUMO", "DIAS", "PROMEDIO_DIA"])
    tabla["PROMEDIO_DIA"] = (tabla["INSUMO"] / tabla["DIAS"]).round(1)
    return tabla.sort_values("INSUMO", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────
# TABLA HTML
# ─────────────────────────────────────────────
def _fila_usuario_html(row) -> str:
    return (
        "<tr>"
        f"<td class='sup-cell'>{row['NOMBRE']}</td>"
        f"<td>{row['USUARIO']}</td>"
        f"<td>{row['SUPERVISOR']}</td>"
        f"<td>{row['COORDINADOR']}</td>"
        f"<td>{row['INSUMO']}</td>"
        f"<td>{row['PROMEDIO_DIA']}</td>"
        "</tr>"
    )


def _render_tabla_usuarios(tabla: pd.DataFrame):
    rows_html = "".join(_fila_usuario_html(r) for _, r in tabla.iterrows())
    table_html = (
        "<div class='avance-tabla-wrap'><table class='avance-tabla'><thead><tr>"
        "<th class='grp-sup'>Nombre</th><th class='grp-sup'>Usuario</th>"
        "<th class='grp-sup'>Supervisor</th><th class='grp-sup'>Coordinador</th>"
        "<th class='grp-total'>Insumo</th><th class='grp-total'>Prom./día</th>"
        "</tr></thead><tbody>"
        f"{rows_html}"
        "</tbody></table></div>"
    )
    with st.container(key="tabla_usuarios_leads"):
        st.markdown(table_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────
def _fig_barra_horizontal(indice, valores, color, height=None, top_n=None):
    # ojo: si indice/valores llegan como Series (con su propio índice numérico),
    # pd.Series(valores, index=indice) los REALINEA por índice en vez de emparejarlos
    # por posición -> todo termina en NaN. .to_numpy() lo evita.
    indice = indice.to_numpy() if hasattr(indice, "to_numpy") else indice
    valores = valores.to_numpy() if hasattr(valores, "to_numpy") else valores
    serie = pd.Series(valores, index=indice).sort_values()
    if top_n:
        serie = serie.tail(top_n)
    fig = go.Figure(go.Bar(
        x=serie.values, y=[str(i)[:38] for i in serie.index], orientation="h",
        marker=dict(color=color),
        text=serie.values, textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color="#CBD3F2", family="Inter"),
    ))
    fig.update_layout(
        height=height or max(280, len(serie) * 24 + 60), margin=dict(l=10, r=50, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
    )
    return fig


def _fig_tendencia(d: pd.DataFrame) -> go.Figure:
    serie = d.groupby(d["_FECHA"].dt.date)["_INSUMO"].sum().sort_index()
    fig = go.Figure(go.Scatter(
        x=list(serie.index), y=list(serie.values), mode="lines+markers",
        line=dict(color=COLOR_ACCENT, width=2.5, shape="spline", smoothing=0.7),
        marker=dict(size=5, color=COLOR_ACCENT, line=dict(color="rgba(8,6,15,0.6)", width=1)),
        fill="tozeroy", fillcolor="rgba(244,63,94,0.12)",
        hovertemplate="<b>%{x}</b><br>%{y} leads<extra></extra>",
    ))
    fig.update_layout(
        height=300, margin=dict(l=40, r=20, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.55)"), automargin=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Leads asignados",
                   tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.55)"), automargin=True),
    )
    return fig


# ─────────────────────────────────────────────
# LOGO
# ─────────────────────────────────────────────
_LOGO_PATH = "logo-scala-learning-transformacion-digital-universidades.webp"
try:
    with open(_LOGO_PATH, "rb") as _f:
        _logo_b64 = base64.b64encode(_f.read()).decode()
    _logo_src = f"data:image/webp;base64,{_logo_b64}"
except FileNotFoundError:
    _logo_src = ""

# ─────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────
leads_full = _cargar_leads()
hoy = date.today()

# ─────────────────────────────────────────────
# SIDEBAR — FILTROS
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
        <div class='sbh-lbl'>Período</div>
        <div class='sbh-rule'></div>
    </div>""", unsafe_allow_html=True)

    if len(leads_full):
        f_min, f_max = leads_full["_FECHA"].dt.date.min(), leads_full["_FECHA"].dt.date.max()
    else:
        f_min = f_max = hoy
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_ini = st.date_input("Desde", value=f_min, min_value=f_min, max_value=f_max)
    with col_f2:
        fecha_fin = st.date_input("Hasta", value=f_max, min_value=f_min, max_value=f_max)

    st.markdown("""<div class='sbh'>
        <div class='sbh-num' style='color:#34D399!important;background:rgba(52,211,153,0.12);border-color:rgba(52,211,153,0.22)'>02</div>
        <div class='sbh-lbl'>Filtros</div>
        <div class='sbh-rule'></div>
    </div>""", unsafe_allow_html=True)

    supervisores = ["Todos"] + sorted(leads_full["Supervisor"].dropna().unique().tolist())
    sup_sel = st.selectbox("Supervisor", supervisores)
    if len(supervisores) == 1:
        st.caption("⚠️ Supervisor aún vacío en la hoja — sin filtrar por supervisor.")

    coordinadores = ["Todos"] + sorted(leads_full["Coordinador"].dropna().unique().tolist())
    coord_sel = st.selectbox("Coordinador", coordinadores)
    if len(coordinadores) == 1:
        st.caption("⚠️ Coordinador aún vacío en la hoja — sin filtrar por coordinador.")

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

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@500;600;700&display=swap');
    * {{ font-family: 'Inter', sans-serif !important; }}
    span[data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="collapsedControl"] span,
    .material-symbols-rounded, .material-symbols-outlined, .material-icons {{
        font-family: 'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
    }}
    [data-testid="stSidebarNav"] {{ display:none !important; }}

    [data-testid="stAppViewContainer"], .main {{
        background:
            radial-gradient(ellipse 90% 55% at 6% -6%,  rgba(244,63,94,0.14) 0%, transparent 55%),
            radial-gradient(ellipse 80% 55% at 100% 0%, rgba(99,102,241,0.17) 0%, transparent 55%),
            radial-gradient(ellipse 75% 60% at 92% 100%, rgba(52,211,153,0.08) 0%, transparent 55%),
            radial-gradient(ellipse 60% 50% at 0% 100%, rgba(99,102,241,0.07) 0%, transparent 55%),
            linear-gradient(160deg, #071310 0%, #082017 45%, #050F0B 100%);
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    .block-container {{ padding-top: 2rem; padding-bottom: 1rem; }}

    [data-testid="stSidebarCollapseButton"] button,
    div[data-testid="collapsedControl"] button {{
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 10px !important; transition: all .2s ease !important;
    }}
    [data-testid="stSidebarCollapseButton"] button:hover,
    div[data-testid="collapsedControl"] button:hover {{ border-color: rgba(244,63,94,0.45) !important; }}
    [data-testid="stSidebarCollapseButton"] span {{ color: rgba(255,255,255,0.80) !important; font-size:20px !important; }}
    div[data-testid="stSidebarContent"] {{ width:100%!important; box-sizing:border-box!important; padding-right:0.75rem!important; }}
    div[data-testid="stSidebarContent"] > div {{ width:100%!important; }}

    /* ── Header banner ── */
    .st-key-hdrbanner {{
        position: relative; overflow: hidden;
        background:
            radial-gradient(ellipse 70% 130% at 2% -15%,  rgba(244,63,94,0.30) 0%, transparent 60%),
            radial-gradient(ellipse 65% 130% at 100% 120%, rgba(129,140,248,0.34) 0%, transparent 60%),
            radial-gradient(ellipse 55% 110% at 72% 130%,  rgba(52,211,153,0.16) 0%, transparent 60%),
            linear-gradient(155deg, #071811 0%, #0C2B1D 50%, #061109 100%);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 20px; padding: 18px 30px; margin-bottom: 18px;
        box-shadow: 0 18px 46px -18px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.08);
    }}
    .hb-eyebrow {{ display:inline-flex;align-items:center;gap:8px;
        background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.16);
        border-radius:99px;padding:5px 13px;margin-bottom:11px;
        font-size:10px;font-weight:700;color:rgba(255,255,255,0.78);
        letter-spacing:0.12em;text-transform:uppercase; }}
    .hb-dot {{ width:7px;height:7px;border-radius:50%;background:#34D399;
        box-shadow:0 0 9px #34D399;animation:sbcPulse 1.8s ease-in-out infinite; }}
    .hb-title {{ font-family:'Space Grotesk',sans-serif!important;
        font-size:29px;font-weight:700;color:white;margin:0 0 9px;
        letter-spacing:-0.8px;line-height:1.05; }}
    .hb-meta {{ display:flex;flex-wrap:wrap;gap:8px;margin:0 0 2px; }}
    .hb-chip {{ display:inline-flex;align-items:center;gap:6px;
        background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.13);
        border-radius:9px;padding:5px 11px;font-size:11px;font-weight:600;color:rgba(255,255,255,0.74); }}
    .hb-chip b {{ color:#fff;font-weight:700; }}
    .nav-lbl {{ font-size:9px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;
        color:rgba(255,255,255,0.40);margin:3px 0 7px; }}
    .st-key-hdrbanner [data-testid="stVerticalBlock"] {{ gap: 0.5rem !important; }}
    .st-key-hdrbanner [data-testid="stButton"] > button {{
        position:relative; z-index:2; overflow:hidden; white-space:nowrap !important;
        color:#CBD3F2 !important; border-radius:9px !important;
        font-size:10px !important; font-weight:700 !important;
        height:32px !important; min-height:32px !important; padding:0 11px !important;
        border:1px solid rgba(255,255,255,0.12) !important; border-top-color:rgba(255,255,255,0.18) !important;
        background:linear-gradient(180deg, rgba(255,255,255,0.085), rgba(255,255,255,0.025)) !important;
        box-shadow:inset 0 1px 0 rgba(255,255,255,0.10), inset 0 -2px 6px -2px rgba(0,0,0,0.35), 0 4px 12px -8px rgba(8,3,24,0.60) !important;
        transition:transform .16s ease, box-shadow .16s ease, background .16s ease, border-color .16s ease, color .16s ease !important;
    }}
    .st-key-hdrbanner [data-testid="stButton"] > button p {{ white-space:nowrap !important; margin:0 !important; }}
    .st-key-hdrbanner [data-testid="stButton"] > button:hover {{
        color:#EAF2FF !important; transform:translateY(-1px) !important;
        border-color:rgba(251,113,133,0.42) !important;
        background:linear-gradient(180deg, rgba(251,113,133,0.15), rgba(255,255,255,0.04)) !important; }}
    .st-key-hdrbanner [data-testid="stButton"] > button[kind="primary"] {{
        color:#FFF4F6 !important; padding-left:20px !important;
        border:1px solid rgba(244,63,94,0.55) !important; border-top-color:rgba(255,205,215,0.62) !important;
        background:linear-gradient(180deg, rgba(244,63,94,0.30), rgba(219,39,119,0.16)) !important;
        box-shadow:inset 0 1px 0 rgba(255,255,255,0.22), 0 8px 22px -10px rgba(244,63,94,0.50) !important; }}
    .st-key-hdrbanner [data-testid="stButton"] > button[kind="primary"]::before {{
        content:""; position:absolute; left:8px; top:50%; transform:translateY(-50%);
        width:5px; height:5px; border-radius:50%; background:#FB7185; box-shadow:0 0 8px rgba(251,113,133,0.9); }}

    @keyframes sbcPulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:.3; transform:scale(.6); }} }}
    @keyframes sbcBar {{ 0% {{ background-position:0% 0%; }} 100% {{ background-position:200% 0%; }} }}

    /* ── KPI cards ── */
    .kpi-card {{
        background: linear-gradient(160deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.02) 100%);
        border-radius: 20px; padding: 22px 22px 18px;
        box-shadow: 0 20px 44px -18px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.08);
        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
        position: relative; overflow: hidden; min-height: 148px;
        display: flex; flex-direction: column; justify-content: space-between;
        border: 1px solid rgba(255,255,255,0.10);
        transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
    }}
    .kpi-card:hover {{
        transform: translateY(-6px); border-color: var(--kc, {COLOR_ACCENT});
        box-shadow: 0 30px 60px -22px rgba(0,0,0,0.8), 0 0 36px -12px var(--kc, {COLOR_ACCENT}), inset 0 1px 0 rgba(255,255,255,0.10);
    }}
    .kpi-card::before {{ content:'';position:absolute;top:0;left:0;right:0;height:4px;
        background:var(--kc, {COLOR_PRIMARY});box-shadow:0 0 18px -2px var(--kc, {COLOR_PRIMARY}); }}
    .kpi-card::after {{ content:'';position:absolute;top:-40px;right:-40px;width:120px;height:120px;
        background:radial-gradient(circle,var(--kc, {COLOR_PRIMARY}),transparent 70%);opacity:0.22;border-radius:50%; }}
    .kpi-bg-icon {{ position:absolute;bottom:12px;right:16px;font-size:46px;opacity:0.10;line-height:1;pointer-events:none;z-index:0; }}
    .kpi-label {{ font-size:10px;color:rgba(255,255,255,0.50);font-weight:700;text-transform:uppercase;letter-spacing:0.10em;position:relative;z-index:1; }}
    .kpi-value {{ font-family:'Space Grotesk',sans-serif!important;font-size:30px;font-weight:700;line-height:1.1;margin:10px 0 4px;position:relative;z-index:1;letter-spacing:-0.5px;text-shadow:0 2px 16px rgba(0,0,0,0.4); }}
    .kpi-sub {{ font-size:11px;color:rgba(255,255,255,0.42);position:relative;z-index:1; }}
    .kpi-bar-wrap {{ background:rgba(255,255,255,0.09);border-radius:99px;height:5px;margin-top:12px;overflow:hidden;position:relative;z-index:1; }}
    .kpi-bar-fill {{ height:5px;border-radius:99px;box-shadow:0 0 10px -1px currentColor; }}

    /* ── Section header ── */
    .sec-header {{
        background:
            radial-gradient(ellipse at 12% 35%, rgba(255,255,255,0.18) 0%, transparent 55%),
            radial-gradient(ellipse at 92% 135%, rgba(0,0,0,0.24) 0%, transparent 55%),
            var(--sc, {COLOR_PRIMARY});
        border-radius: 20px; padding: 22px 28px; margin: 34px 0 18px;
        box-shadow: 0 18px 42px -12px rgba(15,23,42,0.45);
        position: relative; overflow: hidden;
        display: flex; align-items: center; gap: 18px;
        border: 1px solid rgba(255,255,255,0.14);
    }}
    .sec-header::before {{ content:'';position:absolute;left:-25px;top:-35px;width:130px;height:130px;background:rgba(255,255,255,0.10);border-radius:50%; }}
    .sec-header::after {{ content:'';position:absolute;right:-35px;bottom:-45px;width:150px;height:150px;background:rgba(255,255,255,0.07);border-radius:50%; }}
    .sec-icon {{ width:56px;height:56px;border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:27px;flex-shrink:0;position:relative;z-index:1;
        background:rgba(255,255,255,0.18) !important;border:1px solid rgba(255,255,255,0.28) !important;box-shadow:0 8px 18px -6px rgba(0,0,0,0.4); }}
    .sec-text {{ flex:1;min-width:0;position:relative;z-index:1; }}
    .sec-title {{ font-size:19px;font-weight:800;color:white;margin:0 0 5px 0;letter-spacing:-0.4px; }}
    .sec-desc {{ font-size:12px;color:rgba(255,255,255,0.78);margin:0;line-height:1.6; }}
    .sec-tag {{ font-size:10px;font-weight:700;color:white;background:rgba(255,255,255,0.20);border:1px solid rgba(255,255,255,0.35);padding:5px 14px;border-radius:99px;letter-spacing:0.06em;text-transform:uppercase;flex-shrink:0;align-self:flex-start;position:relative;z-index:1; }}

    /* ── Table headers ── */
    .tbl-hdr {{ padding:14px 20px;border-radius:14px;display:flex;align-items:center;gap:12px;margin-bottom:6px;box-shadow:0 4px 18px rgba(0,0,0,0.15);position:relative;overflow:hidden; }}
    .tbl-hdr::before {{ content:'';position:absolute;left:-10px;top:-10px;width:60px;height:60px;background:rgba(255,255,255,0.08);border-radius:50%; }}
    .tbl-hdr::after {{ content:'';position:absolute;right:-20px;bottom:-20px;width:80px;height:80px;background:rgba(255,255,255,0.10);border-radius:50%; }}
    .tbl-hdr-icon {{ font-size:24px;flex-shrink:0;position:relative;z-index:1; }}
    .tbl-hdr-body {{ flex:1;position:relative;z-index:1; }}
    .tbl-hdr-title {{ font-size:14px;font-weight:800;color:white;margin:0 0 2px;letter-spacing:-0.2px; }}
    .tbl-hdr-desc {{ font-size:11px;color:rgba(255,255,255,0.72);margin:0; }}
    .tbl-hdr-badge {{ font-size:10px;font-weight:700;color:white;background:rgba(255,255,255,0.20);border:1px solid rgba(255,255,255,0.35);padding:4px 12px;border-radius:99px;flex-shrink:0;white-space:nowrap;position:relative;z-index:1; }}

    /* ── Plotly chart: tarjeta de vidrio oscuro ── */
    div[data-testid="stPlotlyChart"] {{
        background: linear-gradient(160deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015)) !important;
        border-radius: 18px !important; box-shadow: 0 16px 38px -16px rgba(0,0,0,0.65) !important;
        border: 1px solid rgba(255,255,255,0.09) !important; overflow: visible !important; padding: 10px !important;
    }}

    /* ── Tabla de usuarios ── */
    .avance-tabla-wrap {{ overflow:auto;max-height:520px;border-radius:16px;border:1px solid rgba(255,255,255,0.10);
        box-shadow:0 20px 46px -18px rgba(0,0,0,0.7);background:rgba(6,15,11,0.55);margin-bottom:22px; }}
    .avance-tabla {{ width:100%;border-collapse:collapse;font-size:11px;white-space:nowrap; }}
    .avance-tabla th, .avance-tabla td {{ text-align:center;padding:7px 12px; }}
    .avance-tabla thead th {{ position:sticky;top:0;z-index:1;
        color:rgba(255,255,255,0.94);font-weight:600;
        border-bottom:1px solid rgba(255,255,255,0.10);font-size:10.5px;letter-spacing:0.02em; }}
    .avance-tabla thead th.grp-sup {{ background:#10231B;text-align:left; }}
    .avance-tabla thead th.grp-total {{ background:#182420; }}
    .avance-tabla tbody td {{ color:rgba(225,232,250,0.92);border-bottom:1px solid rgba(255,255,255,0.045); }}
    .avance-tabla tbody tr:nth-child(odd) {{ background:rgba(10,24,18,0.45); }}
    .avance-tabla tbody tr:hover {{ background:rgba(244,63,94,0.09); }}
    .avance-tabla td.sup-cell {{ font-weight:700;color:white;text-align:left; }}
    .avance-tabla-wrap::-webkit-scrollbar {{ width:6px;height:6px; }}
    .avance-tabla-wrap::-webkit-scrollbar-track {{ background:rgba(255,255,255,0.04); }}
    .avance-tabla-wrap::-webkit-scrollbar-thumb {{ background:rgba(244,63,94,0.35);border-radius:99px; }}

    /* ── Sidebar base ── */
    section[data-testid="stSidebar"] > div:first-child {{
        background:
            radial-gradient(ellipse 95% 42% at 8% 0%,    rgba(244,63,94,0.24) 0%, transparent 55%),
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
        background:linear-gradient(145deg,rgba(244,63,94,0.12) 0%,rgba(129,140,248,0.09) 55%,rgba(52,211,153,0.07) 100%),rgba(255,255,255,0.04);
        border:1px solid rgba(255,255,255,0.12); }}
    .sbc-orb {{ position:absolute;border-radius:50%;pointer-events:none; }}
    .sbc-orb-1 {{ width:140px;height:140px;background:radial-gradient(circle,rgba(244,63,94,0.18) 0%,transparent 70%);top:-50px;right:-40px; }}
    .sbc-orb-2 {{ width:90px;height:90px;background:radial-gradient(circle,rgba(129,140,248,0.16) 0%,transparent 70%);bottom:-30px;left:-25px; }}
    .sbc-orb-3 {{ width:60px;height:60px;background:radial-gradient(circle,rgba(52,211,153,0.14) 0%,transparent 70%);top:50%;right:12px; }}
    .sbc-live {{ position:absolute;top:14px;right:14px;display:flex;align-items:center;gap:5px;font-size:8px!important;font-weight:800!important;color:#34D399!important;background:rgba(52,211,153,0.13);border:1px solid rgba(52,211,153,0.30);padding:3px 9px 3px 7px;border-radius:99px;letter-spacing:0.10em;z-index:2; }}
    .sbc-pulse {{ width:5px;height:5px;background:#34D399;border-radius:50%;display:inline-block;animation:sbcPulse 1.8s ease-in-out infinite; }}
    .sbc-body {{ position:relative;z-index:1;text-align:center; }}
    .sbc-logo-wrap {{ margin-bottom:10px;display:flex;justify-content:center;align-items:center; }}
    .sbc-logo-img {{ max-width:150px!important;height:auto!important;filter:drop-shadow(0 4px 14px rgba(244,63,94,0.45)) brightness(1.05);display:block; }}
    .sbc-name {{ font-size:13px!important;font-weight:700!important;color:rgba(255,255,255,0.88)!important;letter-spacing:0!important;margin-bottom:4px!important; }}
    .sbc-org {{ font-size:10px!important;color:rgba(255,255,255,0.35)!important;margin-bottom:16px!important; }}
    .sbc-stats {{ display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.22);border-radius:12px;padding:10px 8px;border:1px solid rgba(255,255,255,0.07); }}
    .sbc-stat {{ flex:1;text-align:center; }}
    .sbc-sv {{ display:block;font-size:14px!important;font-weight:900!important;color:white!important;line-height:1;margin-bottom:3px; }}
    .sbc-sl {{ display:block;font-size:8px!important;font-weight:700!important;color:rgba(255,255,255,0.28)!important;letter-spacing:0.10em;text-transform:uppercase; }}
    .sbc-sep {{ width:1px;height:28px;background:rgba(255,255,255,0.09);flex-shrink:0; }}
    .sbc-bar {{ position:absolute;bottom:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#F43F5E,#818CF8,#34D399,#F59E0B,#F43F5E);background-size:300% 100%;animation:sbcBar 4s linear infinite; }}

    /* ── Section headers (sidebar) ── */
    .sbh {{ display:flex;align-items:center;gap:10px;margin:24px 0 12px; }}
    .sbh-num {{ font-size:10px!important;font-weight:900!important;width:28px;height:22px;border-radius:7px;border:1px solid;display:flex;align-items:center;justify-content:center;flex-shrink:0;letter-spacing:0.04em; }}
    .sbh-lbl {{ font-size:10px!important;font-weight:800!important;color:rgba(255,255,255,0.60)!important;letter-spacing:0.14em!important;text-transform:uppercase!important;white-space:nowrap!important; }}
    .sbh-rule {{ flex:1;height:1px;background:rgba(255,255,255,0.08); }}

    /* ── Dropdowns / selects (listas claras con texto oscuro) ── */
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
    div[data-testid="stSidebarContent"] .stSelectbox > div > div:hover {{ border-color:rgba(244,63,94,0.50)!important;box-shadow:0 0 0 3px rgba(244,63,94,0.10)!important; }}

    /* ── Footer ── */
    .sbf {{ margin-top:26px;padding:0; }}
    .sbf-card {{ position:relative;overflow:hidden;border-radius:16px;padding:14px 14px;background:linear-gradient(150deg,rgba(244,63,94,0.10),rgba(129,140,248,0.06));border:1px solid rgba(255,255,255,0.10);box-shadow:inset 0 1px 0 rgba(255,255,255,0.08); }}
    .sbf-glow {{ position:absolute;width:120px;height:120px;border-radius:50%;top:-50px;right:-40px;background:radial-gradient(circle,rgba(244,63,94,0.20),transparent 70%);pointer-events:none; }}
    .sbf-row {{ display:flex;align-items:center;gap:12px;position:relative;z-index:1; }}
    .sbf-avatar {{ position:relative;width:42px;height:42px;border-radius:13px;background:linear-gradient(135deg,#F43F5E 0%,#818CF8 100%);display:flex;align-items:center;justify-content:center;font-size:14px!important;font-weight:900!important;color:white!important;flex-shrink:0;letter-spacing:0.5px;box-shadow:0 6px 18px rgba(244,63,94,0.45),inset 0 1px 0 rgba(255,255,255,0.3); }}
    .sbf-online {{ position:absolute;bottom:-2px;right:-2px;width:12px;height:12px;border-radius:50%;background:#34D399;border:2.5px solid #130A2B;box-shadow:0 0 8px rgba(52,211,153,0.8);animation:sbcPulse 2s ease-in-out infinite; }}
    .sbf-name {{ font-size:12px!important;font-weight:700!important;color:rgba(255,255,255,0.92)!important;margin-bottom:3px!important; }}
    .sbf-role {{ font-size:10px!important;color:rgba(255,255,255,0.42)!important;line-height:1.3; }}
    .sbf-credit {{ display:flex;align-items:center;justify-content:center;gap:5px;margin-top:12px;font-size:9px!important;font-weight:600!important;color:rgba(255,255,255,0.30)!important;text-align:center;letter-spacing:0.06em; }}
    .sbf-spark {{ font-size:10px; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# NAVEGACIÓN + ENCABEZADO
# ─────────────────────────────────────────────
_home_pg = st.Page("home.py", title="Inicio", icon="🏠", default=True)
_insc_pg = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
_mat_pg = st.Page("pages/2_Matriculas.py", title="Matrículas", icon="🎓")
_cuart_pg = st.Page("pages/3_Cuartiles.py", title="Cuartiles", icon="🏆")
_cont_pg = st.Page("pages/4_Contactabilidad.py", title="Real time", icon="📞")

rango = f"{fecha_ini.strftime('%d/%m/%Y')} – {fecha_fin.strftime('%d/%m/%Y')}"
with st.container(key="hdrbanner"):
    st.markdown(f"""
    <div class='hb-eyebrow'><span class='hb-dot'></span>Centro de Control · Uniminuto 2026</div>
    <div class='hb-title'>Módulo de Leads</div>
    <div class='hb-meta'>
        <span class='hb-chip'>📅 <b>{rango}</b></span>
        <span class='hb-chip'>🧭 Supervisor <b>{sup_sel}</b></span>
        <span class='hb-chip'>🧭 Coordinador <b>{coord_sel}</b></span>
    </div>
    <div class='nav-lbl'>⚡ Navegación</div>
    """, unsafe_allow_html=True)
    nb1, nb2, nb3, nb4, nb5, nb6, _nsp = st.columns([1.0, 1.35, 1.3, 1.35, 1.2, 1.1, 1.0], vertical_alignment="center")
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
        if st.button("📞 Real time", key="hdr_cont", width="stretch"):
            st.switch_page(_cont_pg)
    with nb6:
        st.button("🎯 Leads", key="hdr_leads", width="stretch", type="primary")

if not len(leads_full):
    st.warning("Sin datos en la hoja 'Resumen diario'.")
    st.stop()

# ─────────────────────────────────────────────
# FILTRO DEL RANGO SELECCIONADO
# ─────────────────────────────────────────────
mask = (leads_full["_FECHA"].dt.date >= fecha_ini) & (leads_full["_FECHA"].dt.date <= fecha_fin)
if sup_sel != "Todos":
    mask &= leads_full["Supervisor"] == sup_sel
if coord_sel != "Todos":
    mask &= leads_full["Coordinador"] == coord_sel
d = leads_full[mask].copy()

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
def kpi_bar(pct, color, max_val=100):
    fill = min(pct / max_val * 100, 100) if max_val else 0
    return f"<div class='kpi-bar-wrap'><div class='kpi-bar-fill' style='width:{fill:.0f}%;background:{color};'></div></div>"


total_insumo = int(d["_INSUMO"].sum())
dias_con_datos = d["_FECHA"].nunique()
promedio_dia = total_insumo / dias_con_datos if dias_con_datos else 0
asesores_activos = d["_USUARIO"].nunique()

tabla_usuarios = _tabla_usuarios(d)
if len(tabla_usuarios):
    top_asesor = tabla_usuarios.iloc[0]
    top_asesor_txt = f"{top_asesor['NOMBRE']}"
    top_asesor_val = int(top_asesor["INSUMO"])
else:
    top_asesor_txt, top_asesor_val = "—", 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_ACCENT}'>
        <div class='kpi-bg-icon'>🎯</div>
        <div>
            <div class='kpi-label'>Insumo total</div>
            <div class='kpi-value' style='color:#FB7185'>{total_insumo:,}</div>
            <div class='kpi-sub'>leads asignados en el período</div>
        </div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class='kpi-card' style='--kc:#38BDF8'>
        <div class='kpi-bg-icon'>📊</div>
        <div>
            <div class='kpi-label'>Promedio diario</div>
            <div class='kpi-value' style='color:#38BDF8'>{promedio_dia:.0f}</div>
            <div class='kpi-sub'>leads por día, todos los asesores</div>
        </div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_SUCCESS}'>
        <div class='kpi-bg-icon'>👥</div>
        <div>
            <div class='kpi-label'>Asesores activos</div>
            <div class='kpi-value' style='color:{COLOR_SUCCESS}'>{asesores_activos}</div>
            <div class='kpi-sub'>con leads asignados en el rango</div>
        </div>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_WARNING}'>
        <div class='kpi-bg-icon'>🏅</div>
        <div>
            <div class='kpi-label'>Asesor top</div>
            <div class='kpi-value' style='color:{COLOR_WARNING};font-size:18px'>{top_asesor_txt}</div>
            <div class='kpi-sub'>{top_asesor_val:,} leads en el período</div>
        </div>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABLA — USUARIO / SUPERVISOR / COORDINADOR
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_PRIMARY}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(244,63,94,0.20),rgba(244,63,94,0.06))'>🎯</div>
    <div class='sec-text'>
        <div class='sec-title'>Insumo por Asesor</div>
        <div class='sec-desc'>Leads asignados por asesor en el período, con su supervisor y coordinador.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_PRIMARY}'>Ordenado por insumo</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""<div class='tbl-hdr' style='background:linear-gradient(135deg,#0C2B1D,#F43F5E)'>
    <span class='tbl-hdr-icon'>📋</span>
    <div class='tbl-hdr-body'>
        <div class='tbl-hdr-title'>Asesores — {rango}</div>
        <div class='tbl-hdr-desc'>Supervisor y coordinador según el último dato disponible en la hoja</div>
    </div>
    <span class='tbl-hdr-badge'>{len(tabla_usuarios)} asesores</span>
</div>""", unsafe_allow_html=True)
_render_tabla_usuarios(tabla_usuarios)

_export = tabla_usuarios.rename(columns={
    "USUARIO": "USUARIO", "NOMBRE": "NOMBRE", "SUPERVISOR": "SUPERVISOR", "COORDINADOR": "COORDINADOR",
    "INSUMO": "INSUMO (LEADS)", "DIAS": "DIAS CON DATOS", "PROMEDIO_DIA": "PROMEDIO POR DIA",
})
b64 = base64.b64encode(_excel_bytes(_export)).decode()
st.markdown(
    f'<div style="text-align:right;margin-top:-14px;margin-bottom:8px">'
    f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" '
    f'download="leads_asesores.xlsx" '
    f'style="font-size:0.72rem;color:rgba(255,255,255,0.35);text-decoration:none;letter-spacing:0.03em">'
    f'↓ Exportar Excel</a></div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# INSUMO POR EXPERTO
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#F43F5E'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(244,63,94,0.20),rgba(244,63,94,0.06))'>👤</div>
    <div class='sec-text'>
        <div class='sec-title'>Insumo por Experto</div>
        <div class='sec-desc'>Top 20 asesores por leads asignados en el período seleccionado.</div>
    </div>
    <span class='sec-tag' style='background:#F43F5E'>Top 20</span>
</div>
""", unsafe_allow_html=True)
if len(tabla_usuarios):
    st.plotly_chart(
        _fig_barra_horizontal(tabla_usuarios["NOMBRE"], tabla_usuarios["INSUMO"], "#F43F5E", top_n=20),
        width="stretch", config={"displayModeBar": False},
    )
else:
    st.caption("Sin datos para el período seleccionado.")

# ─────────────────────────────────────────────
# INSUMO POR SUPERVISOR
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#38BDF8'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(56,189,248,0.20),rgba(56,189,248,0.06))'>🧭</div>
    <div class='sec-text'>
        <div class='sec-title'>Insumo por Supervisor</div>
        <div class='sec-desc'>Suma de leads asignados a los asesores de cada supervisor.</div>
    </div>
    <span class='sec-tag' style='background:#38BDF8'>Por supervisor</span>
</div>
""", unsafe_allow_html=True)
grp_sup = d.dropna(subset=["Supervisor"]).groupby("Supervisor")["_INSUMO"].sum()
if len(grp_sup):
    st.plotly_chart(
        _fig_barra_horizontal(grp_sup.index, grp_sup.values, "#38BDF8"),
        width="stretch", config={"displayModeBar": False},
    )
else:
    st.caption("⚠️ Aún no hay valores de Supervisor en la hoja 'Resumen diario' para el período seleccionado.")

# ─────────────────────────────────────────────
# INSUMO POR COORDINADOR
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#818CF8'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(129,140,248,0.20),rgba(129,140,248,0.06))'>🧑‍💼</div>
    <div class='sec-text'>
        <div class='sec-title'>Insumo por Coordinador</div>
        <div class='sec-desc'>Suma de leads asignados a los asesores de cada coordinador.</div>
    </div>
    <span class='sec-tag' style='background:#818CF8'>Por coordinador</span>
</div>
""", unsafe_allow_html=True)
grp_coord = d.dropna(subset=["Coordinador"]).groupby("Coordinador")["_INSUMO"].sum()
if len(grp_coord):
    st.plotly_chart(
        _fig_barra_horizontal(grp_coord.index, grp_coord.values, "#818CF8"),
        width="stretch", config={"displayModeBar": False},
    )
else:
    st.caption("⚠️ Aún no hay valores de Coordinador en la hoja 'Resumen diario' para el período seleccionado.")

# ─────────────────────────────────────────────
# TENDENCIA DIARIA
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_SUCCESS}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(16,185,129,0.20),rgba(16,185,129,0.06))'>📈</div>
    <div class='sec-text'>
        <div class='sec-title'>Tendencia Diaria</div>
        <div class='sec-desc'>Total de leads asignados por día, todos los asesores.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_SUCCESS}'>Serie diaria</span>
</div>
""", unsafe_allow_html=True)
if len(d):
    st.plotly_chart(_fig_tendencia(d), width="stretch", config={"displayModeBar": False})
else:
    st.caption("Sin datos para el período seleccionado.")
