import base64
import calendar
import io
import urllib.parse
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Hojas de Google Sheets (compartidas como "Cualquiera con el enlace: Lector").
# Base y Metas viven en archivos de Sheets separados.
_SHEET_ID = "14DOLvF_d-qhd-VBE62M6hnfqtOH3EYcggjBLgwHiC8w"
_SHEET_ID_METAS = "1byJ5Sw_P_xKew5xMbWz9KQSTQfc_J-Fm"


def _url_hoja(sheet_id: str, nombre_hoja: str) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nombre_hoja)}"
    )

# ─────────────────────────────────────────────
# COLORES (mismo esquema que Dashboard WFM, primario en verde esmeralda)
# ─────────────────────────────────────────────
COLOR_PRIMARY = "#065F46"
COLOR_ACCENT  = "#0EA5E9"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER  = "#EF4444"

_MES_ORDEN = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

_DOC_COLS = [
    "CERTIFICACIÓN",
    "Copia del acta de grado de bachiller",
    "Copia del Documento de identidad al 150%",
    "Acta de grado Profesional Universitario",
    "Afiliación a EPS o Sisben",
    "HABEAS DATA",
    "Copia de la prueba de estado para acceso a la educación superior (Pruebas ICFES)",
    "Soporte para descuento",
]
_DOC_PENDIENTE = {"NORECIBIDO", "ENVALIDACION", "NOACEPTADO"}


# ─────────────────────────────────────────────
# DESCARGA (idéntico a Dashboard WFM)
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
def _cargar_base() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID, "Base"))
    df.columns = df.columns.str.strip()
    return df


@st.cache_data(ttl=300, show_spinner=False)
def _cargar_metas() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID_METAS, "Consolidado"))
    df.columns = df.columns.str.strip()
    return df


# Festivos oficiales de Colombia 2026 (incluye Ley Emiliani: se trasladan al lunes siguiente).
_FESTIVOS_2026 = {
    date(2026, 1, 1), date(2026, 1, 12), date(2026, 3, 23), date(2026, 4, 2), date(2026, 4, 3),
    date(2026, 5, 1), date(2026, 5, 18), date(2026, 6, 8), date(2026, 6, 15), date(2026, 6, 29),
    date(2026, 7, 20), date(2026, 8, 7), date(2026, 8, 17), date(2026, 10, 12), date(2026, 11, 2),
    date(2026, 11, 16), date(2026, 12, 8), date(2026, 12, 25),
}


def _es_habil(d: date) -> bool:
    """Lunes a sábado, sin domingos ni festivos."""
    return d.weekday() != 6 and d not in _FESTIVOS_2026


def _dias_habiles(anio: int, mes: int, hasta: int | None = None) -> int:
    """Días hábiles (lunes a sábado, sin festivos) del mes, hasta el día `hasta` inclusive."""
    _, ultimo = calendar.monthrange(anio, mes)
    tope = min(hasta, ultimo) if hasta else ultimo
    return sum(1 for d in range(1, tope + 1) if _es_habil(date(anio, mes, d)))


def _dias_habiles_rango(fecha_ini: date, fecha_fin: date) -> int:
    """Días hábiles (lunes a sábado, sin festivos) en el rango [fecha_ini, fecha_fin] inclusive."""
    total_dias = (fecha_fin - fecha_ini).days + 1
    if total_dias <= 0:
        return 0
    return sum(1 for i in range(total_dias) if _es_habil(fecha_ini + timedelta(days=i)))


def _tabla_avance(base: pd.DataFrame, metas: pd.DataFrame, fecha_ini: date, fecha_fin: date) -> tuple[pd.DataFrame, pd.Series]:
    b = base[base["SUPERVISOR"].notna()].copy()
    b["_SUPERVISOR"] = b["SUPERVISOR"]

    real = b.groupby("_SUPERVISOR")["CRUCE COMPL"].agg(REAL_COMPLETAS="sum", _total="count")
    real["REAL_INCOMPLETAS"] = real["_total"] - real["REAL_COMPLETAS"]
    real["REAL_TOTAL"] = real["_total"]
    real = real.drop(columns="_total")

    dias_habiles_mes = _dias_habiles(fecha_fin.year, fecha_fin.month)
    dias_habiles_rango = _dias_habiles_rango(fecha_ini, fecha_fin)

    _cols_meta_necesarias = {"SUPERVISOR", "CC", "MES", "AÑO", "Meta inscripciones", "Meta inscripciones completas"}
    if _cols_meta_necesarias.issubset(metas.columns) and dias_habiles_mes:
        mes_corte = _MES_ORDEN[fecha_fin.month - 1]
        m = metas[(metas["MES"] == mes_corte) & (metas["AÑO"] == fecha_fin.year)].copy()
        meta_asesor = m.dropna(subset=["SUPERVISOR", "CC"]).drop_duplicates("CC").copy()
        meta_asesor["_meta_incompletas"] = meta_asesor["Meta inscripciones"] - meta_asesor["Meta inscripciones completas"]
        meta_sup = meta_asesor.groupby("SUPERVISOR")[["Meta inscripciones completas", "_meta_incompletas"]].sum()
        meta_sup["META_DIA_COMPLETAS"] = (meta_sup["Meta inscripciones completas"] / dias_habiles_mes * dias_habiles_rango).round().astype(int)
        meta_sup["META_DIA_INCOMPLETAS"] = (meta_sup["_meta_incompletas"] / dias_habiles_mes * dias_habiles_rango).round().astype(int)
        meta_sup["META_DIA_TOTAL"] = meta_sup["META_DIA_COMPLETAS"] + meta_sup["META_DIA_INCOMPLETAS"]
        meta_cols = meta_sup[["META_DIA_COMPLETAS", "META_DIA_INCOMPLETAS", "META_DIA_TOTAL"]]
    else:
        meta_cols = pd.DataFrame(columns=["META_DIA_COMPLETAS", "META_DIA_INCOMPLETAS", "META_DIA_TOTAL"])

    tabla = real.join(meta_cols, how="outer").fillna(0)
    for c in tabla.columns:
        tabla[c] = tabla[c].astype(int)

    tabla["FALTAN_COMPLETAS"] = (tabla["META_DIA_COMPLETAS"] - tabla["REAL_COMPLETAS"]).clip(lower=0)
    tabla["FALTAN_INCOMPLETAS"] = (tabla["META_DIA_INCOMPLETAS"] - tabla["REAL_INCOMPLETAS"]).clip(lower=0)
    tabla["FALTAN_TOTAL"] = (tabla["META_DIA_TOTAL"] - tabla["REAL_TOTAL"]).clip(lower=0)
    tabla = tabla.sort_index()

    total_general = tabla.sum(numeric_only=True)
    total_general.name = "Total general"
    total_general["FALTAN_COMPLETAS"] = max(total_general["META_DIA_COMPLETAS"] - total_general["REAL_COMPLETAS"], 0)
    total_general["FALTAN_INCOMPLETAS"] = max(total_general["META_DIA_INCOMPLETAS"] - total_general["REAL_INCOMPLETAS"], 0)
    total_general["FALTAN_TOTAL"] = max(total_general["META_DIA_TOTAL"] - total_general["REAL_TOTAL"], 0)

    return tabla, total_general


_META_CUMPLIMIENTO = 62  # % de inscripciones completas exigido


_ORDEN_AVANCE = [
    "REAL_COMPLETAS", "META_DIA_COMPLETAS", "FALTAN_COMPLETAS",
    "REAL_INCOMPLETAS", "META_DIA_INCOMPLETAS", "FALTAN_INCOMPLETAS",
    "REAL_TOTAL", "META_DIA_TOTAL", "FALTAN_TOTAL",
]
_FALTAN_IDX = {2, 5, 8}  # posiciones de las columnas "Faltan" dentro de _ORDEN_AVANCE


def _fila_avance_html(supervisor: str, valores: list[int], es_total: bool = False) -> str:
    tds = [f"<td class='sup-cell'>{supervisor}</td>"]
    for i, v in enumerate(valores):
        cls = " class='faltan-cell'" if i in _FALTAN_IDX else ""
        tds.append(f"<td{cls}>{int(v)}</td>")
    real_completas, real_total = valores[0], valores[6]
    pct = (real_completas / real_total * 100) if real_total else 0
    color = COLOR_SUCCESS if pct >= _META_CUMPLIMIENTO else COLOR_DANGER
    tds.append(
        "<td class='cumpl-cell'><div class='cumpl-wrap'>"
        f"<div class='cumpl-bar-track'><div class='cumpl-bar-fill' style='width:{min(pct, 100):.0f}%;background:{color}'></div></div>"
        f"<span class='cumpl-pct' style='color:{color}'>{pct:.0f}%</span>"
        "</div></td>"
    )
    row_cls = " class='total-row'" if es_total else ""
    return f"<tr{row_cls}>" + "".join(tds) + "</tr>"


def _render_tabla_avance(tabla: pd.DataFrame, total_general: pd.Series):
    rows_html = "".join(
        _fila_avance_html(sup, [tabla.loc[sup, c] for c in _ORDEN_AVANCE])
        for sup in tabla.index
    )
    rows_html += _fila_avance_html(
        "Total general", [total_general[c] for c in _ORDEN_AVANCE], es_total=True
    )
    table_html = (
        "<div class='avance-tabla-wrap'><table class='avance-tabla'><thead>"
        "<tr><th rowspan='2'>Supervisor</th>"
        "<th colspan='3'>Completas</th><th colspan='3'>Incompletas</th><th colspan='3'>Total</th>"
        f"<th rowspan='2'>Cumplimiento<br><span class='cumpl-hdr-sub'>Meta {_META_CUMPLIMIENTO}%</span></th></tr>"
        "<tr><th>Real</th><th>Meta</th><th>Faltan</th>"
        "<th>Real</th><th>Meta</th><th>Faltan</th>"
        "<th>Real</th><th>Meta</th><th>Faltan</th></tr>"
        "</thead><tbody>"
        f"{rows_html}"
        "</tbody></table></div>"
    )
    with st.container(key="tabla_avance"):
        st.markdown(table_html, unsafe_allow_html=True)


def _fig_avance(tabla: pd.DataFrame) -> go.Figure:
    d = tabla.copy()
    d["gap"] = d["REAL_TOTAL"] - d["META_DIA_TOTAL"]
    d = d.sort_values("gap")

    x_abs_max = max(d["gap"].abs().max(), 1) * 1.25
    fig = go.Figure(go.Bar(
        x=d["gap"], y=d.index, orientation="h",
        marker=dict(
            color=d["gap"], colorscale=[[0, "#DC2626"], [0.5, "rgba(148,163,184,0.35)"], [1, "#059669"]],
            cmid=0, cmin=-x_abs_max, cmax=x_abs_max,
            line=dict(color="rgba(255,255,255,0.18)", width=1), cornerradius=8,
        ),
        width=0.62,
        text=[f"{g:+d}" for g in d["gap"]],
        textposition="outside",
        textfont=dict(size=10.5, color="rgba(255,255,255,0.85)", family="Space Grotesk, sans-serif"),
        cliponaxis=False,
        hovertext=[
            f"<b>{sup}</b><br>Real: {r}<br>Meta: {mt}<br>{'Faltan' if g < 0 else 'Por encima de meta'}: {abs(g)}"
            for sup, r, mt, g in zip(d.index, d["REAL_TOTAL"], d["META_DIA_TOTAL"], d["gap"])
        ],
        hoverinfo="text",
    ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(255,255,255,0.25)")

    # franjas de fondo alternadas para dar profundidad sin recargar el gráfico
    for i in range(len(d.index)):
        if i % 2 == 0:
            fig.add_shape(
                type="rect", xref="paper", yref="y",
                x0=0, x1=1, y0=i - 0.5, y1=i + 0.5,
                fillcolor="rgba(255,255,255,0.025)", line_width=0, layer="below",
            )

    fig_h = max(260, len(d) * 24 + 50)
    fig.update_layout(
        height=fig_h,
        margin=dict(l=190, r=60, t=6, b=28),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        bargap=0.28,
        font=dict(family="Inter, sans-serif"),
        xaxis=dict(
            range=[-x_abs_max, x_abs_max],
            showgrid=True, gridcolor="rgba(255,255,255,0.045)", gridwidth=1, zeroline=False,
            tickfont=dict(color="rgba(255,255,255,0.32)", size=9), fixedrange=True,
            title=dict(text="Real − Meta", font=dict(size=10, color="rgba(255,255,255,0.35)")),
        ),
        yaxis=dict(showgrid=False, tickfont=dict(color="rgba(255,255,255,0.72)", size=10), fixedrange=True),
    )
    return fig


def _fig_embudo(b: pd.DataFrame) -> go.Figure:
    total = len(b)
    aspirantes = int((b["STATUS_INSCRIPCION"] == "ASPIRANTE").sum())
    completos = int((b["CRUCE COMPL"] == 1).sum())
    fig = go.Figure(go.Funnel(
        y=["Registros", "Aspirantes", "Cruce completo"],
        x=[total, aspirantes, completos],
        textinfo="value+percent initial",
        textfont=dict(size=12, color="white", family="Inter"),
        marker=dict(color=[COLOR_ACCENT, "#818CF8", COLOR_SUCCESS]),
        connector=dict(line=dict(color="rgba(255,255,255,0.15)", width=1)),
    ))
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
    )
    return fig


def _fig_tendencia(b: pd.DataFrame) -> go.Figure:
    d = b.copy()
    d["FECHA_INSCRIPCION"] = pd.to_datetime(d["FECHA_INSCRIPCION"], errors="coerce", dayfirst=True)
    serie = d.dropna(subset=["FECHA_INSCRIPCION"]).groupby(d["FECHA_INSCRIPCION"].dt.date).size().sort_index()
    fig = go.Figure(go.Scatter(
        x=list(serie.index), y=list(serie.values), mode="lines",
        line=dict(color=COLOR_ACCENT, width=2, shape="spline"),
        fill="tozeroy", fillcolor="rgba(14,165,233,0.10)",
        hovertemplate="%{x|%d %b}<br>%{y} inscripciones<extra></extra>",
    ))
    fig.update_layout(
        height=280, margin=dict(l=50, r=20, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Inscripciones",
                   tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"), automargin=True),
    )
    return fig


def _fig_documentos(b: pd.DataFrame) -> go.Figure:
    abiertos = b[b["CRUCE COMPL"] == 0]
    conteo = {c: int(abiertos[c].isin(_DOC_PENDIENTE).sum()) for c in _DOC_COLS}
    s = pd.Series(conteo).sort_values()
    fig = go.Figure(go.Bar(
        x=s.values, y=[c[:38] for c in s.index], orientation="h",
        marker=dict(color=COLOR_WARNING),
        text=s.values, textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color="#CBD3F2", family="Inter"),
    ))
    fig.update_layout(
        height=280, margin=dict(l=10, r=50, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
    )
    return fig


def _fig_programa(b: pd.DataFrame) -> go.Figure:
    top = b["PROGRAMA"].value_counts().head(10).sort_values()
    fig = go.Figure(go.Bar(
        x=top.values, y=[p[:42] for p in top.index], orientation="h",
        marker=dict(color="#818CF8"),
        text=top.values, textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color="#CBD3F2", family="Inter"),
    ))
    fig.update_layout(
        height=340, margin=dict(l=10, r=50, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
    )
    return fig


def _fig_nivel(b: pd.DataFrame) -> go.Figure:
    counts = b["NIVEL"].value_counts()
    fig = go.Figure(go.Bar(
        x=list(counts.index), y=list(counts.values),
        marker=dict(color=COLOR_SUCCESS),
        text=list(counts.values), textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color="#CBD3F2", family="Inter"),
    ))
    fig.update_layout(
        height=340, margin=dict(l=40, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
    )
    return fig


_PALETA_SUPERVISORES = ["#38BDF8", "#818CF8", "#34D399", "#F59E0B", "#F472B6", "#A78BFA", "#FB923C", "#2DD4BF"]


def _fig_supervisor_mes(b: pd.DataFrame) -> go.Figure:
    d = b.dropna(subset=["MES", "_SUPERVISOR"]).copy()
    top_sup = d["_SUPERVISOR"].value_counts().head(8).index.tolist()
    d = d[d["_SUPERVISOR"].isin(top_sup)]
    grp = d.groupby(["MES", "_SUPERVISOR"])["CRUCE COMPL"].mean() * 100
    meses = [m for m in _MES_ORDEN if m in d["MES"].unique()]

    fig = go.Figure()
    for i, sup in enumerate(top_sup):
        # None (no relleno con 0) para meses sin filas de este supervisor: corta la línea
        # en vez de mostrar un falso 0% (ej. supervisor que ya no está activo ese mes).
        vals = [grp.get((m, sup), None) for m in meses]
        color = _PALETA_SUPERVISORES[i % len(_PALETA_SUPERVISORES)]
        fig.add_trace(go.Scatter(
            x=meses, y=vals, mode="lines+markers", name=sup, connectgaps=False,
            line=dict(color=color, width=2.5, shape="spline", smoothing=0.9),
            marker=dict(size=6, color=color, line=dict(color="rgba(8,6,15,0.6)", width=1)),
            hovertemplate=f"<b>{sup}</b><br>%{{x}}: %{{y:.0f}}% cumplimiento<extra></extra>",
        ))
    fig.update_layout(
        height=400, margin=dict(l=50, r=40, t=10, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=9, color="rgba(255,255,255,0.58)"), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.55)"),
                   range=[-0.4, len(meses) - 0.6], automargin=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="% Cumplimiento", ticksuffix="%",
                   tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.55)"), automargin=True),
    )
    return fig


def _fig_coordinador(b: pd.DataFrame) -> go.Figure:
    d = b.dropna(subset=["COORDINADOR"]).copy()
    grp = d.groupby("COORDINADOR")["CRUCE COMPL"].agg(completas="sum", total="count")
    grp["incompletas"] = grp["total"] - grp["completas"]
    grp = grp.sort_values("total")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=grp.index, x=grp["completas"], orientation="h", name="Completas",
        marker=dict(color=COLOR_SUCCESS),
    ))
    fig.add_trace(go.Bar(
        y=grp.index, x=grp["incompletas"], orientation="h", name="Incompletas",
        marker=dict(color=COLOR_WARNING),
    ))
    fig.update_layout(
        barmode="stack", height=300, margin=dict(l=10, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=10, color="rgba(255,255,255,0.58)"), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.55)"),
                   automargin=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11, family="Inter", color="rgba(255,255,255,0.75)"),
                   automargin=True),
    )
    return fig


_DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _fig_dia_semana(b: pd.DataFrame) -> go.Figure:
    d = b.copy()
    d["_FECHA"] = pd.to_datetime(d["FECHA_INSCRIPCION"], errors="coerce", dayfirst=True)
    d = d.dropna(subset=["_FECHA"])
    conteo = d["_FECHA"].dt.weekday.map(lambda i: _DIAS_ES[i]).value_counts().reindex(_DIAS_ES).fillna(0)
    colores = [COLOR_DANGER if dia == "Domingo" else COLOR_ACCENT for dia in _DIAS_ES]
    fig = go.Figure(go.Bar(
        x=_DIAS_ES, y=conteo.values, marker=dict(color=colores),
        text=[int(v) for v in conteo.values], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color="#CBD3F2", family="Inter"),
    ))
    fig.update_layout(
        height=300, margin=dict(l=40, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        showlegend=False,
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Inscripciones",
                   tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"), automargin=True),
    )
    return fig


def _iniciales(nombre) -> str:
    partes = str(nombre).strip().split()
    if not partes:
        return "?"
    return (partes[0][0] + (partes[1][0] if len(partes) > 1 else "")).upper()


def _top_lista_html(filas: list[tuple[str, str, str]], color: str) -> str:
    rows = []
    for i, (nombre, meta, valor) in enumerate(filas, start=1):
        rows.append(
            f"<div class='top-row' style='--ac:{color}'>"
            f"<span class='top-rank'>{i:02d}</span>"
            f"<div class='top-avatar'>{_iniciales(nombre)}</div>"
            f"<div class='top-body'><div class='top-name'>{nombre}</div><div class='top-meta'>{meta}</div></div>"
            f"<span class='top-value' style='color:{color}'>{valor}</span>"
            "</div>"
        )
    return "<div class='top-list'>" + "".join(rows) + "</div>"


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
# CARGA + PRE-FILTRO PARA POBLAR LOS SELECTORES
# ─────────────────────────────────────────────
base_full = _cargar_base()
metas_full = _cargar_metas()
hoy = date.today()

_base_con_sup = base_full.copy()
_base_con_sup["_SUPERVISOR"] = _base_con_sup["SUPERVISOR"].fillna("Sin asignar")

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

    fechas_insc = pd.to_datetime(base_full["FECHA_INSCRIPCION"], errors="coerce", dayfirst=True).dropna().dt.date
    if len(fechas_insc):
        f_min, f_max = fechas_insc.min(), fechas_insc.max()
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

    cohorte_valores = sorted(base_full["COHORTE"].dropna().unique().tolist()) if "COHORTE" in base_full.columns else []
    cohorte_sel = st.selectbox("Cohorte", ["Todos"] + cohorte_valores)
    if not cohorte_valores:
        st.caption("⚠️ COHORTE aún vacía en Base — sin filtrar por cohorte.")

    mes_presentes = base_full["MES"].dropna().unique().tolist() if "MES" in base_full.columns else []
    mes_valores = [m for m in _MES_ORDEN if m in mes_presentes] + sorted(m for m in mes_presentes if m not in _MES_ORDEN)
    mes_sel = st.selectbox("Mes", ["Todos"] + mes_valores)

    supervisores = ["Todos"] + sorted(_base_con_sup["_SUPERVISOR"].unique().tolist())
    sup_sel = st.selectbox("Supervisor", supervisores)

    niveles = ["Todos"] + sorted(base_full["NIVEL"].dropna().unique().tolist())
    nivel_sel = st.selectbox("Nivel", niveles)

    programas = ["Todos"] + sorted(base_full["PROGRAMA"].dropna().unique().tolist())
    prog_sel = st.selectbox("Programa", programas)

    agentes = ["Todos"] + sorted(base_full["NOMBRE AGENT"].dropna().unique().tolist())
    agente_sel = st.selectbox("Agente", agentes)

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
            radial-gradient(ellipse 90% 55% at 6% -6%,  rgba(14,165,233,0.16) 0%, transparent 55%),
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
    div[data-testid="collapsedControl"] button:hover {{ border-color: rgba(14,165,233,0.45) !important; }}
    [data-testid="stSidebarCollapseButton"] span {{ color: rgba(255,255,255,0.80) !important; font-size:20px !important; }}
    div[data-testid="stSidebarContent"] {{ width:100%!important; box-sizing:border-box!important; padding-right:0.75rem!important; }}
    div[data-testid="stSidebarContent"] > div {{ width:100%!important; }}

    /* ── Header banner ── */
    .st-key-hdrbanner {{
        position: relative; overflow: hidden;
        background:
            radial-gradient(ellipse 70% 130% at 2% -15%,  rgba(14,165,233,0.34) 0%, transparent 60%),
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
        border-color:rgba(125,211,252,0.42) !important;
        background:linear-gradient(180deg, rgba(125,211,252,0.15), rgba(255,255,255,0.04)) !important; }}
    .st-key-hdrbanner [data-testid="stButton"] > button[kind="primary"] {{
        color:#F4F9FF !important; padding-left:20px !important;
        border:1px solid rgba(56,189,248,0.55) !important; border-top-color:rgba(186,225,255,0.62) !important;
        background:linear-gradient(180deg, rgba(56,189,248,0.30), rgba(59,130,246,0.16)) !important;
        box-shadow:inset 0 1px 0 rgba(255,255,255,0.22), 0 8px 22px -10px rgba(56,189,248,0.50) !important; }}
    .st-key-hdrbanner [data-testid="stButton"] > button[kind="primary"]::before {{
        content:""; position:absolute; left:8px; top:50%; transform:translateY(-50%);
        width:5px; height:5px; border-radius:50%; background:#7DD3FC; box-shadow:0 0 8px rgba(125,211,252,0.9); }}

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
    .kpi-value {{ font-family:'Space Grotesk',sans-serif!important;font-size:34px;font-weight:700;line-height:1.1;margin:10px 0 4px;position:relative;z-index:1;letter-spacing:-0.5px;text-shadow:0 2px 16px rgba(0,0,0,0.4); }}
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
    .sec-meta {{ text-align:center;flex-shrink:0;padding:9px 20px;background:rgba(255,255,255,0.96);border-radius:13px;border:1px solid rgba(255,255,255,0.5);box-shadow:0 6px 16px -6px rgba(0,0,0,0.3);position:relative;z-index:1; }}
    .sec-meta-val {{ font-family:'Space Grotesk',sans-serif!important;font-size:24px;font-weight:700;line-height:1.1;margin-bottom:2px;letter-spacing:-0.5px; }}
    .sec-meta-lab {{ font-size:9px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.08em; }}
    .sec-tag {{ font-size:10px;font-weight:700;color:white;background:rgba(255,255,255,0.20);border:1px solid rgba(255,255,255,0.35);padding:5px 14px;border-radius:99px;letter-spacing:0.06em;text-transform:uppercase;flex-shrink:0;align-self:flex-start;position:relative;z-index:1; }}

    /* ── Chart mini-headers ── */
    .chart-hdr {{ display:flex;align-items:center;gap:12px;padding:12px 16px;
        background:linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.025));
        border-radius:14px;border:1px solid rgba(255,255,255,0.10);border-left:4px solid var(--cc, {COLOR_ACCENT});
        box-shadow:0 8px 22px -10px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.06);margin-bottom:12px; }}
    .ch-icon {{ font-size:18px;line-height:1;flex-shrink:0;width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12); }}
    .ch-texts {{ flex:1;min-width:0; }}
    .ch-title {{ font-size:13px;font-weight:800;color:#F1F4FF;margin:0 0 1px;letter-spacing:-0.2px; }}
    .ch-sub {{ font-size:10.5px;color:rgba(255,255,255,0.45);margin:0; }}
    .ch-tag {{ margin-left:auto;font-size:9px;font-weight:700;color:var(--cc, {COLOR_ACCENT});background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.14);padding:3px 9px;border-radius:99px;letter-spacing:0.05em;flex-shrink:0;text-transform:uppercase; }}

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

    /* ── Tablas: vidrio oscuro + encabezado degradado ── */
    div[data-testid="stDataFrame"] {{ border-radius:16px !important; overflow:hidden !important; box-shadow:0 16px 38px -16px rgba(0,0,0,0.65) !important; border:1px solid rgba(255,255,255,0.10) !important; }}
    div[data-testid="stDataFrame"] div[role="columnheader"] {{ background: linear-gradient(135deg, #0C2B1D 0%, #10B981 100%) !important; color:white !important; font-weight:700 !important; }}
    div[data-testid="stDataFrame"] div[role="columnheader"] span {{ color:white !important; }}
    div[data-testid="stDataFrame"] ::-webkit-scrollbar {{ width:6px;height:6px; }}
    div[data-testid="stDataFrame"] ::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.04); }}
    div[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb {{ background: rgba(56,189,248,0.35); border-radius:99px; }}

    /* ── Tabla Avance vs. Meta: HTML propio (centrado real + barra de cumplimiento) ── */
    .avance-tabla-wrap {{ overflow:auto;max-height:420px;border-radius:16px;border:1px solid rgba(255,255,255,0.10);
        box-shadow:0 20px 46px -18px rgba(0,0,0,0.7);background:rgba(6,15,11,0.55);margin-bottom:22px; }}
    .avance-tabla {{ width:100%;border-collapse:collapse;font-size:10px;white-space:nowrap; }}
    .avance-tabla th, .avance-tabla td {{ text-align:center;padding:4px 8px; }}
    .avance-tabla thead th {{ position:sticky;top:0;z-index:1;
        background:#0F2318;color:rgba(255,255,255,0.94);
        font-weight:600;border-bottom:2px solid rgba(52,211,153,0.45); }}
    .avance-tabla thead tr:first-child th {{ font-size:10px;letter-spacing:0.01em;top:0; }}
    .avance-tabla thead tr:last-child th {{ font-size:8.5px;font-weight:600;color:rgba(255,255,255,0.55);
        padding-top:3px;padding-bottom:5px;top:23px;border-bottom:1px solid rgba(255,255,255,0.08); }}
    .cumpl-hdr-sub {{ display:block;font-size:7.5px;font-weight:500;color:rgba(255,255,255,0.45);margin-top:2px;
        letter-spacing:0.04em;text-transform:none; }}
    .avance-tabla tbody td {{ color:rgba(225,232,250,0.92);border-bottom:1px solid rgba(255,255,255,0.045); }}
    .avance-tabla tbody tr:nth-child(odd) {{ background:rgba(10,24,18,0.45); }}
    .avance-tabla tbody tr:hover {{ background:rgba(14,165,233,0.09); }}
    .avance-tabla td.sup-cell {{ font-weight:700;color:white; }}
    .avance-tabla td.faltan-cell {{ background:rgba(245,158,11,0.14); }}
    .avance-tabla tr.total-row td {{ font-weight:800!important;background:rgba(52,211,153,0.16)!important; }}
    .cumpl-cell {{ min-width:130px; }}
    .cumpl-wrap {{ display:flex;align-items:center;gap:7px;justify-content:center; }}
    .cumpl-bar-track {{ flex:1;max-width:64px;height:6px;border-radius:99px;
        background:rgba(255,255,255,0.10);overflow:hidden; }}
    .cumpl-bar-fill {{ height:100%;border-radius:99px;box-shadow:0 0 8px -1px currentColor; }}
    .cumpl-pct {{ font-weight:800;font-size:10px;min-width:30px;text-align:right; }}
    .avance-tabla-wrap::-webkit-scrollbar {{ width:6px;height:6px; }}
    .avance-tabla-wrap::-webkit-scrollbar-track {{ background:rgba(255,255,255,0.04); }}
    .avance-tabla-wrap::-webkit-scrollbar-thumb {{ background:rgba(56,189,248,0.35);border-radius:99px; }}

    /* ── Listas "Top" (rankings) ── */
    .top-list {{ display:flex;flex-direction:column;gap:8px; }}
    .top-row {{ display:flex;align-items:center;gap:12px;padding:10px 16px;border-radius:12px;
        background:linear-gradient(160deg,rgba(255,255,255,0.05),rgba(255,255,255,0.015));
        border:1px solid rgba(255,255,255,0.09);
        transition:transform .2s ease,border-color .2s ease; }}
    .top-row:hover {{ transform:translateX(4px);border-color:var(--ac); }}
    .top-rank {{ font-family:'Space Grotesk',sans-serif!important;font-weight:800;font-size:12px;
        color:rgba(255,255,255,0.32);width:20px;flex-shrink:0; }}
    .top-avatar {{ width:34px;height:34px;border-radius:10px;flex-shrink:0;display:flex;align-items:center;justify-content:center;
        font-size:11.5px;font-weight:800;color:white;background:var(--ac);
        box-shadow:0 4px 12px -3px var(--ac); }}
    .top-body {{ flex:1;min-width:0; }}
    .top-name {{ font-size:12.5px;font-weight:700;color:white;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }}
    .top-meta {{ font-size:10.5px;color:rgba(255,255,255,0.45);white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }}
    .top-value {{ flex-shrink:0;font-family:'Space Grotesk',sans-serif!important;font-weight:800;font-size:14px; }}

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

    /* ── Dropdowns / selects (listas claras con texto oscuro) ── */
    ul[role="listbox"] *, li[role="option"], li[role="option"] * {{ color:#1E293B !important; }}
    li[role="option"]:hover, li[role="option"][aria-selected="true"] {{ background:#F1F5F9 !important; }}

    /* ── Calendario del selector de fecha (fondo oscuro, texto claro) ── */
    div[data-baseweb="calendar"] * {{ color: rgba(255,255,255,0.85) !important; }}
    div[data-baseweb="calendar"] button[disabled] {{ color: rgba(255,255,255,0.20) !important; }}
    div[data-testid="stSidebarContent"] .stSelectbox [data-baseweb="select"] span,
    div[data-testid="stSidebarContent"] .stSelectbox [data-baseweb="select"] div[class*="ValueContainer"] *,
    div[data-testid="stSidebarContent"] .stSelectbox [data-baseweb="select"] input {{ color:white !important; }}
    div[data-testid="stSidebarContent"] input[type="text"] {{ color:white !important; }}
    div[data-testid="stSidebarContent"] label,
    div[data-testid="stSidebarContent"] .stSelectbox label,
    div[data-testid="stSidebarContent"] [data-testid="stWidgetLabel"],
    div[data-testid="stSidebarContent"] [data-testid="stWidgetLabel"] p,
    div[data-testid="stSidebarContent"] [data-testid="stWidgetLabel"] span {{ font-size:11px!important;font-weight:500!important;color:rgba(255,255,255,0.50)!important; }}
    div[data-testid="stSidebarContent"] .stDateInput label,
    div[data-testid="stSidebarContent"] .stDateInput [data-testid="stWidgetLabel"],
    div[data-testid="stSidebarContent"] .stDateInput [data-testid="stWidgetLabel"] p {{ font-size:11px!important;font-weight:600!important;color:#38BDF8!important; }}
    div[data-testid="stSidebarContent"] .stSelectbox > div > div,
    div[data-testid="stSidebarContent"] .stSelectbox > label + div > div {{ background:rgba(255,255,255,0.05)!important;border:1px solid rgba(255,255,255,0.12)!important;border-radius:9px!important;transition:border-color .18s, box-shadow .18s!important; }}
    div[data-testid="stSidebarContent"] .stSelectbox > div > div:hover {{ border-color:rgba(56,189,248,0.50)!important;box-shadow:0 0 0 3px rgba(56,189,248,0.10)!important; }}
    div[data-testid="stSidebarContent"] .stDateInput > div > div > input {{ background:rgba(255,255,255,0.05)!important;border:1px solid rgba(255,255,255,0.12)!important;border-radius:9px!important;color:white!important;font-size:11px!important; }}
    div[data-testid="stSidebarContent"] .stDateInput > div > div > input:focus {{ border-color:rgba(56,189,248,0.50)!important;box-shadow:0 0 0 3px rgba(56,189,248,0.10)!important; }}

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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# APLICAR FILTROS
# ─────────────────────────────────────────────
b = _base_con_sup.copy()
_fecha_insc = pd.to_datetime(b["FECHA_INSCRIPCION"], errors="coerce", dayfirst=True).dt.date
mask = (_fecha_insc >= fecha_ini) & (_fecha_insc <= fecha_fin)
if cohorte_sel != "Todos":
    mask &= b["COHORTE"] == cohorte_sel
if mes_sel != "Todos":
    mask &= b["MES"] == mes_sel
if sup_sel != "Todos":
    mask &= b["_SUPERVISOR"] == sup_sel
if nivel_sel != "Todos":
    mask &= b["NIVEL"] == nivel_sel
if prog_sel != "Todos":
    mask &= b["PROGRAMA"] == prog_sel
if agente_sel != "Todos":
    mask &= b["NOMBRE AGENT"] == agente_sel
b = b[mask].copy()

_base_avance = base_full
if cohorte_sel != "Todos":
    _base_avance = _base_avance[_base_avance["COHORTE"] == cohorte_sel]
if mes_sel != "Todos":
    _base_avance = _base_avance[_base_avance["MES"] == mes_sel]
_fecha_insc_avance = pd.to_datetime(_base_avance["FECHA_INSCRIPCION"], errors="coerce", dayfirst=True).dt.date
_base_avance = _base_avance[(_fecha_insc_avance >= fecha_ini) & (_fecha_insc_avance <= fecha_fin)]
tabla, total_general = _tabla_avance(_base_avance, metas_full, fecha_ini, fecha_fin)

total_insc = len(b)
pct_cruce = (b["CRUCE COMPL"].mean() * 100) if total_insc else 0
cumplimiento = (total_general["REAL_TOTAL"] / total_general["META_DIA_TOTAL"] * 100) if total_general["META_DIA_TOTAL"] else 0
pendientes_doc = int((b[b["CRUCE COMPL"] == 0][_DOC_COLS].isin(_DOC_PENDIENTE)).any(axis=1).sum()) if total_insc else 0

_home_pg = st.Page("home.py", title="Inicio", icon="🏠", default=True)
_mat_pg = st.Page("pages/2_Matriculas.py", title="Matrículas", icon="🎓")
_cuart_pg = st.Page("pages/3_Cuartiles.py", title="Cuartiles", icon="🏆")
_cont_pg = st.Page("pages/4_Contactabilidad.py", title="Contactabilidad", icon="📞")

# ─────────────────────────────────────────────
# ENCABEZADO
# ─────────────────────────────────────────────
rango = f"{fecha_ini.strftime('%d/%m/%Y')} – {fecha_fin.strftime('%d/%m/%Y')}"
with st.container(key="hdrbanner"):
    st.markdown(f"""
    <div class='hb-eyebrow'><span class='hb-dot'></span>Centro de Control · Uniminuto 2026</div>
    <div class='hb-title'>Módulo de Inscripciones</div>
    <div class='hb-meta'>
        <span class='hb-chip'>📅 <b>{rango}</b></span>
        <span class='hb-chip'>🧭 Cohorte <b>{cohorte_sel}</b></span>
    </div>
    <div class='nav-lbl'>⚡ Navegación</div>
    """, unsafe_allow_html=True)
    nb1, nb2, nb3, nb4, nb5, _nsp = st.columns([1.0, 1.35, 1.3, 1.35, 1.6, 1.2], vertical_alignment="center")
    with nb1:
        if st.button("🏠 Inicio", key="hdr_home", width="stretch"):
            st.switch_page(_home_pg)
    with nb2:
        st.button("📝 Inscripciones", key="hdr_insc", width="stretch", type="primary")
    with nb3:
        if st.button("🎓 Matrículas", key="hdr_mat", width="stretch"):
            st.switch_page(_mat_pg)
    with nb4:
        if st.button("🏆 Cuartiles", key="hdr_cuart", width="stretch"):
            st.switch_page(_cuart_pg)
    with nb5:
        if st.button("📞 Contactabilidad", key="hdr_cont", width="stretch"):
            st.switch_page(_cont_pg)

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
def kpi_bar(pct, color, max_val=100):
    fill = min(pct / max_val * 100, 100) if max_val else 0
    return f"<div class='kpi-bar-wrap'><div class='kpi-bar-fill' style='width:{fill:.0f}%;background:{color};'></div></div>"


cumpl_color = COLOR_SUCCESS if cumplimiento >= 100 else (COLOR_WARNING if cumplimiento >= 70 else COLOR_DANGER)
cruce_color = COLOR_SUCCESS if pct_cruce >= 60 else (COLOR_WARNING if pct_cruce >= 40 else COLOR_DANGER)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_ACCENT}'>
        <div class='kpi-bg-icon'>📝</div>
        <div>
            <div class='kpi-label'>Total inscripciones</div>
            <div class='kpi-value' style='color:#7DD3FC'>{total_insc:,}</div>
            <div class='kpi-sub'>en el rango seleccionado</div>
        </div>
        {kpi_bar(total_insc, COLOR_ACCENT, max(total_insc, 1))}
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class='kpi-card' style='--kc:{cruce_color}'>
        <div class='kpi-bg-icon'>✅</div>
        <div>
            <div class='kpi-label'>Cruce completo</div>
            <div class='kpi-value' style='color:{cruce_color}'>{pct_cruce:.1f}%</div>
            <div class='kpi-sub'>del total filtrado</div>
        </div>
        {kpi_bar(pct_cruce, cruce_color)}
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class='kpi-card' style='--kc:{cumpl_color}'>
        <div class='kpi-bg-icon'>🎯</div>
        <div>
            <div class='kpi-label'>Cumplimiento meta día</div>
            <div class='kpi-value' style='color:{cumpl_color}'>{cumplimiento:.0f}%</div>
            <div class='kpi-sub'>real vs. meta prorrateada</div>
        </div>
        {kpi_bar(cumplimiento, cumpl_color)}
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_WARNING}'>
        <div class='kpi-bg-icon'>📄</div>
        <div>
            <div class='kpi-label'>Pendientes documentación</div>
            <div class='kpi-value' style='color:{COLOR_WARNING}'>{pendientes_doc:,}</div>
            <div class='kpi-sub'>soportes pendientes</div>
        </div>
        {kpi_bar(pendientes_doc, COLOR_WARNING, max(total_insc, 1))}
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COMPARATIVOS
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#38BDF8'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(56,189,248,0.20),rgba(56,189,248,0.06))'>📐</div>
    <div class='sec-text'>
        <div class='sec-title'>Comparativos</div>
        <div class='sec-desc'>Evolución del cumplimiento por supervisor, comparativo por coordinador y patrón semanal de inscripción.</div>
    </div>
    <span class='sec-tag' style='background:#38BDF8'>Tendencias</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""<div class='chart-hdr' style='--cc:#38BDF8'>
    <span class='ch-icon'>📈</span>
    <div class='ch-texts'><div class='ch-title'>Cumplimiento por supervisor y mes</div><div class='ch-sub'>Top 8 supervisores por volumen · % de inscripciones completas</div></div>
</div>""", unsafe_allow_html=True)
st.plotly_chart(_fig_supervisor_mes(b), width="stretch", config={"displayModeBar": False})

ccol1, ccol2 = st.columns(2)
with ccol1:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_PRIMARY}'>
        <span class='ch-icon'>🧭</span>
        <div class='ch-texts'><div class='ch-title'>Por coordinador</div><div class='ch-sub'>Completas vs. incompletas</div></div>
    </div>""", unsafe_allow_html=True)
    st.plotly_chart(_fig_coordinador(b), width="stretch", config={"displayModeBar": False})
with ccol2:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_ACCENT}'>
        <span class='ch-icon'>🗓️</span>
        <div class='ch-texts'><div class='ch-title'>Por día de la semana</div><div class='ch-sub'>Patrón operativo de registro</div></div>
    </div>""", unsafe_allow_html=True)
    st.plotly_chart(_fig_dia_semana(b), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# AVANCE VS. META POR SUPERVISOR
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_PRIMARY}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(52,211,153,0.20),rgba(52,211,153,0.06))'>🎯</div>
    <div class='sec-text'>
        <div class='sec-title'>Avance vs. Meta por Supervisor</div>
        <div class='sec-desc'>Meta mensual ÷ días hábiles del mes (lunes a sábado, sin festivos) × días hábiles del período seleccionado.</div>
    </div>
    <div class='sec-meta'>
        <div class='sec-meta-val' style='color:{COLOR_PRIMARY}'>{_dias_habiles_rango(fecha_ini, fecha_fin)}/{_dias_habiles(fecha_fin.year, fecha_fin.month)}</div>
        <div class='sec-meta-lab'>Días hábiles</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_PRIMARY}'>Plan vs. real</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""<div class='tbl-hdr' style='background:linear-gradient(135deg,#0C2B1D,#0EA5E9)'>
    <span class='tbl-hdr-icon'>📋</span>
    <div class='tbl-hdr-body'>
        <div class='tbl-hdr-title'>Inscripciones Completas e Incompletas por Supervisor</div>
        <div class='tbl-hdr-desc'>Real · Meta · Faltan · Cumplimiento (meta {_META_CUMPLIMIENTO}% completas) — cohorte y período seleccionados</div>
    </div>
    <span class='tbl-hdr-badge'>{len(tabla)} supervisores</span>
</div>""", unsafe_allow_html=True)
_render_tabla_avance(tabla, total_general)

st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_PRIMARY}'>
    <span class='ch-icon'>📊</span>
    <div class='ch-texts'>
        <div class='ch-title'>Brecha Real − Meta día por supervisor</div>
        <div class='ch-sub'>Verde: al día o adelantado · Rojo: por debajo de la meta</div>
    </div>
    <span class='ch-tag' style='color:{COLOR_PRIMARY}'>Diverging</span>
</div>""", unsafe_allow_html=True)
st.plotly_chart(_fig_avance(tabla), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# TOP POR PROGRAMA
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#8B5CF6'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(139,92,246,0.20),rgba(139,92,246,0.06))'>🎓</div>
    <div class='sec-text'>
        <div class='sec-title'>Inscripciones por Programa</div>
        <div class='sec-desc'>Top 10 programas con más inscripciones, sobre el rango y filtros seleccionados.</div>
    </div>
    <span class='sec-tag' style='background:#8B5CF6'>Top 10</span>
</div>
""", unsafe_allow_html=True)
st.plotly_chart(_fig_programa(b), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# TENDENCIA
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_ACCENT}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(14,165,233,0.20),rgba(14,165,233,0.06))'>📈</div>
    <div class='sec-text'>
        <div class='sec-title'>Tendencia Diaria</div>
        <div class='sec-desc'>Inscripciones registradas por día en el rango seleccionado.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_ACCENT}'>Serie diaria</span>
</div>
""", unsafe_allow_html=True)
st.plotly_chart(_fig_tendencia(b), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# ESTADO DOCUMENTAL
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_WARNING}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(245,158,11,0.20),rgba(245,158,11,0.06))'>📄</div>
    <div class='sec-text'>
        <div class='sec-title'>Estado Documental</div>
        <div class='sec-desc'>Soportes pendientes en casos aún sin cruce completo.</div>
    </div>
    <div class='sec-meta'>
        <div class='sec-meta-val' style='color:{COLOR_WARNING}'>{pendientes_doc}</div>
        <div class='sec-meta-lab'>Casos abiertos</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_WARNING}'>Seguimiento</span>
</div>
""", unsafe_allow_html=True)
st.plotly_chart(_fig_documentos(b), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# DISTRIBUCIÓN
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_SUCCESS}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(16,185,129,0.20),rgba(16,185,129,0.06))'>🧩</div>
    <div class='sec-text'>
        <div class='sec-title'>Distribución</div>
        <div class='sec-desc'>Embudo de inscripción y por nivel académico.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_SUCCESS}'>Composición</span>
</div>
""", unsafe_allow_html=True)
dcol1, dcol2 = st.columns(2)
with dcol1:
    st.markdown("""<div class='chart-hdr' style='--cc:#818CF8'>
        <span class='ch-icon'>🔻</span>
        <div class='ch-texts'><div class='ch-title'>Embudo de inscripción</div><div class='ch-sub'>Registros → Aspirantes → Cruce completo</div></div>
    </div>""", unsafe_allow_html=True)
    st.plotly_chart(_fig_embudo(b), width="stretch", config={"displayModeBar": False})
with dcol2:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_SUCCESS}'>
        <span class='ch-icon'>📚</span>
        <div class='ch-texts'><div class='ch-title'>Por nivel</div><div class='ch-sub'>Pregrado · Especialización · Maestría</div></div>
    </div>""", unsafe_allow_html=True)
    st.plotly_chart(_fig_nivel(b), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# TOPS
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#F59E0B'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(245,158,11,0.20),rgba(245,158,11,0.06))'>🏅</div>
    <div class='sec-text'>
        <div class='sec-title'>Tops y Rankings</div>
        <div class='sec-desc'>Los agentes, inscripciones y supervisores más destacados del período.</div>
    </div>
    <span class='sec-tag' style='background:#F59E0B'>Ranking</span>
</div>
""", unsafe_allow_html=True)

_top_agentes = (
    b.dropna(subset=["NOMBRE AGENT"]).groupby("NOMBRE AGENT")
    .agg(total=("NOMBRE AGENT", "size"), sup=("_SUPERVISOR", "first"))
    .sort_values("total", ascending=False).head(10)
)
_top_supervisores = (
    b.dropna(subset=["_SUPERVISOR"]).groupby("_SUPERVISOR")
    .agg(total=("_SUPERVISOR", "size"), completas=("CRUCE COMPL", "mean"))
    .sort_values("total", ascending=False).head(10)
)
_ultimas = b.copy()
_ultimas["_FECHA"] = pd.to_datetime(_ultimas["FECHA_INSCRIPCION"], errors="coerce", dayfirst=True)
_ultimas = _ultimas.dropna(subset=["_FECHA", "NOMBRE"]).sort_values("_FECHA", ascending=False).head(10)

tcol1, tcol2, tcol3 = st.columns(3)
with tcol1:
    st.markdown("""<div class='chart-hdr' style='--cc:#38BDF8'>
        <span class='ch-icon'>🧑‍💻</span>
        <div class='ch-texts'><div class='ch-title'>Top 10 expertos</div><div class='ch-sub'>Con más inscripciones</div></div>
    </div>""", unsafe_allow_html=True)
    _filas = [(nom, str(row["sup"]), f"{int(row['total'])}") for nom, row in _top_agentes.iterrows()]
    st.markdown(_top_lista_html(_filas, "#38BDF8"), unsafe_allow_html=True)
with tcol2:
    st.markdown("""<div class='chart-hdr' style='--cc:#F59E0B'>
        <span class='ch-icon'>🕓</span>
        <div class='ch-texts'><div class='ch-title'>Top 10 últimas</div><div class='ch-sub'>Inscripciones más recientes</div></div>
    </div>""", unsafe_allow_html=True)
    _filas = [
        (row["NOMBRE"], str(row["PROGRAMA"])[:28], row["_FECHA"].strftime("%d/%m/%Y"))
        for _, row in _ultimas.iterrows()
    ]
    st.markdown(_top_lista_html(_filas, "#F59E0B"), unsafe_allow_html=True)
with tcol3:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_SUCCESS}'>
        <span class='ch-icon'>👥</span>
        <div class='ch-texts'><div class='ch-title'>Top 10 supervisores</div><div class='ch-sub'>Por volumen total</div></div>
    </div>""", unsafe_allow_html=True)
    _filas = [
        (sup, f"{row['completas'] * 100:.0f}% completas", f"{int(row['total'])}")
        for sup, row in _top_supervisores.iterrows()
    ]
    st.markdown(_top_lista_html(_filas, COLOR_SUCCESS), unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DETALLE
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_PRIMARY}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(6,95,70,0.30),rgba(6,95,70,0.10))'>🔎</div>
    <div class='sec-text'>
        <div class='sec-title'>Detalle</div>
        <div class='sec-desc'>Listado de casos filtrados, descargable en Excel.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_PRIMARY}'>{total_insc} casos</span>
</div>
""", unsafe_allow_html=True)

cols_detalle = [c for c in [
    "NOMBRE", "PROGRAMA", "NIVEL", "STATUS_INSCRIPCION", "CRUCE COMPL",
    "VENDEDOR INICIAL", "NOMBRE AGENT", "_SUPERVISOR", "FECHA_INSCRIPCION",
] if c in b.columns]
df_descarga(b[cols_detalle].rename(columns={"_SUPERVISOR": "SUPERVISOR"}), "inscripciones_detalle.xlsx", width="stretch", hide_index=True, height=360)
