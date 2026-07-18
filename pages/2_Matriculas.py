import base64
import calendar
import io
import urllib.parse
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Hojas de Google Sheets (compartidas como "Cualquiera con el enlace: Lector").
# Base y Metas viven en archivos de Sheets separados (Metas es el mismo archivo que usa Inscripciones).
_SHEET_ID = "1yh02o6obFpiMHUenyaBX6ZKmTivdSrY5_usVisb0I74"
_SHEET_ID_METAS = "1byJ5Sw_P_xKew5xMbWz9KQSTQfc_J-Fm"


def _url_hoja(sheet_id: str, nombre_hoja: str) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nombre_hoja)}"
    )


# ─────────────────────────────────────────────
# COLORES (mismo esquema que Inscripciones / Dashboard WFM)
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

_COLS_MONEY = [
    "Ingreso bruto", "Beca", "Descuento", "Vr Alivio", "Desc. Pronto pago",
    "Patrocinio", "Recargo", "Subsidio", "Crédito convenio2", "Crédito icetex",
    "Ingreso neto",
]


# ─────────────────────────────────────────────
# DESCARGA (idéntico a Inscripciones / Dashboard WFM)
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


def _money_to_float(s: pd.Series) -> pd.Series:
    """Convierte '$  1.234.567' / '-$  928.590' / '$  -' a float (miles con punto, sin decimales)."""
    cleaned = (
        s.astype(str).str.strip()
        .str.replace("$", "", regex=False)
        .str.replace("\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def _fmt_cop(v: float) -> str:
    return f"$ {v:,.0f}".replace(",", ".")


# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _cargar_base() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID, "Base"), encoding="utf-8", low_memory=False)
    df.columns = df.columns.str.strip()
    # La hoja trae "Cedula" vacía en las filas de relleno del rango — son las únicas filas válidas.
    df = df[df["Cedula"].notna()].copy()
    for c in _COLS_MONEY:
        if c in df.columns:
            df[c] = _money_to_float(df[c])
    df["NOMBRE_COMPLETO"] = (
        df["Nombres"].fillna("").str.strip() + " " + df["Apellidos"].fillna("").str.strip()
    ).str.strip()
    df["_SUPERVISOR"] = df["Supervisor.1"].fillna("Sin asignar")
    df["_ASESOR"] = df["Asesor.1"].fillna(df["Asesor"]).fillna("Sin asignar")
    # "Coordinador" trae inconsistencias de mayúscula inicial en la Base (ej. "luis Andres..."
    # vs "Luis Andres...") que duplican a la misma persona al agrupar.
    df["_COORDINADOR"] = (
        df["Coordinador"].fillna("Sin asignar").str.strip()
        .apply(lambda s: s[0].upper() + s[1:] if s else s)
    )
    return df


@st.cache_data(ttl=300, show_spinner=False)
def _cargar_metas() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID_METAS, "Consolidado"), encoding="utf-8", low_memory=False)
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


def _meses_en_rango(fecha_ini: date, fecha_fin: date) -> list[tuple[int, int]]:
    """Lista de (año, mes) cubiertos por el rango [fecha_ini, fecha_fin], inclusive."""
    out = []
    anio, mes = fecha_ini.year, fecha_ini.month
    while (anio, mes) <= (fecha_fin.year, fecha_fin.month):
        out.append((anio, mes))
        mes += 1
        if mes > 12:
            mes, anio = 1, anio + 1
    return out


def _meta_prorateada_por_mes(metas: pd.DataFrame, anio: int, mes: int, fecha_ini: date, fecha_fin: date) -> pd.Series:
    """Meta 'Meta matriculas' por supervisor para un mes del rango, prorrateada solo en los
    extremos parciales (si el rango cubre el mes completo, se toma la meta completa del mes)."""
    dias_habiles_mes = _dias_habiles(anio, mes)
    _cols_necesarias = {"SUPERVISOR", "CC", "MES", "AÑO", "Meta matriculas"}
    if not dias_habiles_mes or not _cols_necesarias.issubset(metas.columns):
        return pd.Series(dtype=float)

    _, ultimo_dia_mes = calendar.monthrange(anio, mes)
    cubierto_ini = max(fecha_ini, date(anio, mes, 1))
    cubierto_fin = min(fecha_fin, date(anio, mes, ultimo_dia_mes))
    dias_habiles_cubiertos = _dias_habiles_rango(cubierto_ini, cubierto_fin)

    mes_corte = _MES_ORDEN[mes - 1]
    m = metas[(metas["MES"] == mes_corte) & (metas["AÑO"] == anio)]
    meta_asesor = m.dropna(subset=["SUPERVISOR", "CC"]).drop_duplicates("CC")
    meta_sup_mes = meta_asesor.groupby("SUPERVISOR")["Meta matriculas"].sum()
    return meta_sup_mes / dias_habiles_mes * dias_habiles_cubiertos


def _tabla_avance(base: pd.DataFrame, metas: pd.DataFrame, fecha_ini: date, fecha_fin: date) -> tuple[pd.DataFrame, pd.Series]:
    real = base.groupby("_SUPERVISOR").size().rename("REAL")

    meta_dia = pd.Series(dtype=float)
    for anio, mes in _meses_en_rango(fecha_ini, fecha_fin):
        meta_dia = meta_dia.add(_meta_prorateada_por_mes(metas, anio, mes, fecha_ini, fecha_fin), fill_value=0)
    meta_dia = meta_dia.round().astype(int)
    meta_dia.name = "META"

    tabla = pd.DataFrame({"REAL": real}).join(meta_dia, how="outer").fillna(0)
    tabla["REAL"] = tabla["REAL"].astype(int)
    tabla["META"] = tabla["META"].astype(int)
    tabla["FALTAN"] = (tabla["META"] - tabla["REAL"]).clip(lower=0)
    tabla = tabla.sort_index()

    total_general = tabla.sum(numeric_only=True)
    total_general.name = "Total general"
    total_general["FALTAN"] = max(total_general["META"] - total_general["REAL"], 0)

    return tabla, total_general


def _fila_avance_html(supervisor: str, real: int, meta: int, faltan: int, es_total: bool = False) -> str:
    pct = (real / meta * 100) if meta else (100.0 if real else 0.0)
    color = COLOR_SUCCESS if pct >= 100 else (COLOR_WARNING if pct >= 70 else COLOR_DANGER)
    faltan_style = "color:rgba(255,255,255,0.35)" if faltan == 0 else f"background:rgba(239,68,68,{min(faltan / max(meta, 1), 1) * 0.5 + 0.08:.2f})"
    row_cls = " class='total-row'" if es_total else ""
    return (
        f"<tr{row_cls}>"
        f"<td class='sup-cell'>{supervisor}</td>"
        f"<td>{real}</td>"
        f"<td>{meta}</td>"
        f"<td style='{faltan_style}'>{faltan}</td>"
        "<td class='cumpl-cell'><div class='cumpl-wrap'>"
        f"<div class='cumpl-bar-track'><div class='cumpl-bar-fill' style='width:{min(pct, 100):.0f}%;background:{color}'></div></div>"
        f"<span class='cumpl-pct' style='color:{color}'>{pct:.0f}%</span>"
        "</div></td></tr>"
    )


def _render_tabla_avance(tabla: pd.DataFrame, total_general: pd.Series):
    rows_html = "".join(
        _fila_avance_html(sup, tabla.loc[sup, "REAL"], tabla.loc[sup, "META"], tabla.loc[sup, "FALTAN"])
        for sup in tabla.index
    )
    rows_html += _fila_avance_html(
        "Total general", total_general["REAL"], total_general["META"], total_general["FALTAN"], es_total=True
    )
    table_html = (
        "<div class='avance-tabla-wrap'><table class='avance-tabla'><thead>"
        "<tr><th class='grp-sup'>Supervisor</th>"
        "<th class='grp-total'>Real</th><th class='grp-total'>Meta</th><th class='grp-total'>Faltan</th>"
        "<th class='grp-cumpl'>Cumplimiento</th></tr>"
        "</thead><tbody>"
        f"{rows_html}"
        "</tbody></table></div>"
    )
    with st.container(key="tabla_avance"):
        st.markdown(table_html, unsafe_allow_html=True)


def _fig_avance(tabla: pd.DataFrame) -> go.Figure:
    d = tabla.copy()
    d["gap"] = d["REAL"] - d["META"]
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
            for sup, r, mt, g in zip(d.index, d["REAL"], d["META"], d["gap"])
        ],
        hoverinfo="text",
    ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(255,255,255,0.25)")

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


def _fig_programa(b: pd.DataFrame) -> go.Figure:
    top = b["Programa"].value_counts().head(10).sort_values()
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
    counts = b["Nivel Formación"].value_counts()
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


def _fig_financiacion(b: pd.DataFrame) -> go.Figure:
    counts = b["Financiación"].value_counts()
    colores = {"CONTADO": COLOR_ACCENT, "CREDITO": "#818CF8", "PENDIENTE": COLOR_WARNING}
    fig = go.Figure(go.Pie(
        labels=list(counts.index), values=list(counts.values), hole=0.58,
        marker=dict(colors=[colores.get(k, "#94A3B8") for k in counts.index],
                    line=dict(color="rgba(8,6,15,0.6)", width=2)),
        textinfo="label+percent", textfont=dict(size=11, color="white", family="Inter"),
    ))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
    )
    return fig


def _fig_tendencia(b: pd.DataFrame) -> go.Figure:
    d = b.dropna(subset=["_FECHA"])
    serie = d.groupby(d["_FECHA"].dt.date).size().sort_index()
    fig = go.Figure(go.Scatter(
        x=list(serie.index), y=list(serie.values), mode="lines",
        line=dict(color=COLOR_ACCENT, width=2, shape="spline"),
        fill="tozeroy", fillcolor="rgba(14,165,233,0.10)",
        hovertemplate="%{x|%d %b}<br>%{y} matrículas<extra></extra>",
    ))
    fig.update_layout(
        height=280, margin=dict(l=50, r=20, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Matrículas",
                   tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"), automargin=True),
    )
    return fig


_DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _fig_dia_semana(b: pd.DataFrame) -> go.Figure:
    d = b.dropna(subset=["_FECHA"])
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
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Matrículas",
                   tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"), automargin=True),
    )
    return fig


_PALETA_SUPERVISORES = ["#38BDF8", "#818CF8", "#34D399", "#F59E0B", "#F472B6", "#A78BFA", "#FB923C", "#2DD4BF"]


def _fig_supervisor_mes(base: pd.DataFrame, metas: pd.DataFrame) -> go.Figure:
    """% cumplimiento (real / meta mensual completa) por supervisor y mes.
    A diferencia de Inscripciones, aquí no hay un flag de completitud por registro
    (toda fila de la Base ya es una matrícula) — el cumplimiento se mide contra la meta."""
    d = base.dropna(subset=["MES", "_SUPERVISOR"]).copy()
    top_sup = d["_SUPERVISOR"].value_counts().head(8).index.tolist()
    d = d[d["_SUPERVISOR"].isin(top_sup)]
    real = d.groupby(["MES", "_SUPERVISOR"]).size()
    meses = [m for m in _MES_ORDEN if m in d["MES"].unique()]

    _cols_meta_ok = {"SUPERVISOR", "CC", "MES", "AÑO", "Meta matriculas"}.issubset(metas.columns)
    pct = {}
    for mes in meses:
        meta_sup = pd.Series(dtype=float)
        if _cols_meta_ok:
            anios_mes = d.loc[d["MES"] == mes, "AÑO"].dropna()
            anio = int(anios_mes.mode().iat[0]) if len(anios_mes) else None
            if anio is not None:
                m_meta = metas[(metas["MES"] == mes) & (metas["AÑO"] == anio)]
                meta_asesor = m_meta.dropna(subset=["SUPERVISOR", "CC"]).drop_duplicates("CC")
                meta_sup = meta_asesor.groupby("SUPERVISOR")["Meta matriculas"].sum()
        for sup in top_sup:
            r = real.get((mes, sup), 0)
            m = meta_sup.get(sup)
            pct[(mes, sup)] = (r / m * 100) if m else None

    fig = go.Figure()
    for i, sup in enumerate(top_sup):
        vals = [pct.get((mes, sup)) for mes in meses]
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


def _mapa_supervisor_coordinador(base: pd.DataFrame) -> pd.Series:
    d = base.dropna(subset=["_SUPERVISOR", "_COORDINADOR"])
    return d.groupby("_SUPERVISOR")["_COORDINADOR"].agg(lambda s: s.mode().iat[0])


def _fig_coordinador(tabla: pd.DataFrame, mapa_sup_coord: pd.Series) -> go.Figure:
    d = tabla.copy()
    d["_COORDINADOR"] = d.index.map(mapa_sup_coord)
    d = d.dropna(subset=["_COORDINADOR"])
    grp = d.groupby("_COORDINADOR")[["REAL", "FALTAN"]].sum().sort_values("REAL")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=grp.index, x=grp["REAL"], orientation="h", name="Real",
        marker=dict(color=COLOR_SUCCESS),
    ))
    fig.add_trace(go.Bar(
        y=grp.index, x=grp["FALTAN"], orientation="h", name="Faltan para la meta",
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
base_full["_FECHA"] = pd.to_datetime(base_full["Fecha Contabilización"], errors="coerce", dayfirst=True)

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

    fechas_mat = base_full["_FECHA"].dropna().dt.date
    if len(fechas_mat):
        f_min, f_max = fechas_mat.min(), fechas_mat.max()
    else:
        f_min = f_max = hoy
    # Unas pocas filas traen fechas históricas residuales (2021-2025, previas a la operación
    # real de la Base). El valor por defecto arranca en el mes en curso; min_value conserva
    # el histórico completo por si se quiere consultar manualmente.
    f_ini_default = max(f_min, date(f_max.year, f_max.month, 1))

    # Cohorte y Mes son etiquetas operativas, no derivadas de Fecha Contabilización: hay
    # matriculados de un cohorte/mes en curso que pagaron hace años (reingresos). Por eso,
    # al sincronizar el rango de fechas con la selección se ignoran las fechas anteriores al
    # año en curso — si no, esos residuales angostan o abren el rango de forma engañosa.
    _cutoff_operativo = date(f_max.year, 1, 1)

    def _sincronizar_fechas_con_filtro(columna: str, valor_key: str):
        """Al elegir Cohorte/Mes, el rango de fechas salta a cubrir ese filtro —
        si no, el rango puede quedar sin intersección con la selección (o al revés,
        volver a abrirse a años de historial) y la tabla/gráficos salen vacíos o sucios."""
        valor = st.session_state.get(valor_key)
        if not valor or valor == "Todos":
            return
        fechas_sub = base_full.loc[base_full[columna] == valor, "_FECHA"].dropna().dt.date
        fechas_recientes = fechas_sub[fechas_sub >= _cutoff_operativo]
        objetivo = fechas_recientes if len(fechas_recientes) else fechas_sub
        if len(objetivo):
            st.session_state["fecha_ini_widget"] = objetivo.min()
            st.session_state["fecha_fin_widget"] = objetivo.max()

    st.session_state.setdefault("fecha_ini_widget", f_ini_default)
    st.session_state.setdefault("fecha_fin_widget", f_max)
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_ini = st.date_input("Desde", min_value=f_min, max_value=f_max, key="fecha_ini_widget")
    with col_f2:
        fecha_fin = st.date_input("Hasta", min_value=f_min, max_value=f_max, key="fecha_fin_widget")

    st.markdown("""<div class='sbh'>
        <div class='sbh-num' style='color:#34D399!important;background:rgba(52,211,153,0.12);border-color:rgba(52,211,153,0.22)'>02</div>
        <div class='sbh-lbl'>Filtros</div>
        <div class='sbh-rule'></div>
    </div>""", unsafe_allow_html=True)

    cohorte_valores = sorted(base_full["COHORTE"].dropna().unique().tolist())
    cohorte_sel = st.selectbox(
        "Cohorte", ["Todos"] + cohorte_valores, key="cohorte_sel_widget",
        on_change=_sincronizar_fechas_con_filtro, args=("COHORTE", "cohorte_sel_widget"),
    )

    mes_presentes = base_full["MES"].dropna().unique().tolist()
    mes_valores = [m for m in _MES_ORDEN if m in mes_presentes] + sorted(m for m in mes_presentes if m not in _MES_ORDEN)
    mes_sel = st.selectbox(
        "Mes", ["Todos"] + mes_valores, key="mes_sel_widget",
        on_change=_sincronizar_fechas_con_filtro, args=("MES", "mes_sel_widget"),
    )

    supervisores = ["Todos"] + sorted(base_full["_SUPERVISOR"].unique().tolist())
    sup_sel = st.selectbox("Supervisor", supervisores)

    niveles = ["Todos"] + sorted(base_full["Nivel Formación"].dropna().unique().tolist())
    nivel_sel = st.selectbox("Nivel", niveles)

    programas = ["Todos"] + sorted(base_full["Programa"].dropna().unique().tolist())
    prog_sel = st.selectbox("Programa", programas)

    estados = ["Todos"] + sorted(base_full["ESTADO"].dropna().unique().tolist())
    estado_sel = st.selectbox("Estado", estados)

    financiaciones = ["Todos"] + sorted(base_full["Financiación"].dropna().unique().tolist())
    financiacion_sel = st.selectbox("Financiación", financiaciones)

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
    .avance-tabla {{ width:100%;border-collapse:collapse;font-size:11px;white-space:nowrap; }}
    .avance-tabla th, .avance-tabla td {{ text-align:center;padding:7px 12px; }}
    .avance-tabla thead th {{ position:sticky;top:0;z-index:1;
        color:rgba(255,255,255,0.94);font-weight:600;
        border-bottom:1px solid rgba(255,255,255,0.10);font-size:10.5px;letter-spacing:0.02em; }}
    .avance-tabla thead th.grp-sup {{ background:#10231B;text-align:left; }}
    .avance-tabla thead th.grp-total {{ background:#182420; }}
    .avance-tabla thead th.grp-cumpl {{ background:linear-gradient(180deg, rgba(14,165,233,0.22), rgba(14,165,233,0.08)); }}
    .avance-tabla tbody td {{ color:rgba(225,232,250,0.92);border-bottom:1px solid rgba(255,255,255,0.045); }}
    .avance-tabla tbody tr:nth-child(odd) {{ background:rgba(10,24,18,0.45); }}
    .avance-tabla tbody tr:hover {{ background:rgba(14,165,233,0.09); }}
    .avance-tabla td.sup-cell {{ font-weight:700;color:white;text-align:left; }}
    .avance-tabla tr.total-row td {{ font-weight:800!important;background:rgba(52,211,153,0.16)!important; }}
    .cumpl-cell {{ min-width:150px; }}
    .cumpl-wrap {{ display:flex;align-items:center;gap:7px;justify-content:center; }}
    .cumpl-bar-track {{ flex:1;max-width:80px;height:6px;border-radius:99px;
        background:rgba(255,255,255,0.10);overflow:hidden; }}
    .cumpl-bar-fill {{ height:100%;border-radius:99px;box-shadow:0 0 8px -1px currentColor; }}
    .cumpl-pct {{ font-weight:800;font-size:11px;min-width:34px;text-align:right; }}
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
b = base_full.copy()
mask = (b["_FECHA"].dt.date >= fecha_ini) & (b["_FECHA"].dt.date <= fecha_fin)
if cohorte_sel != "Todos":
    mask &= b["COHORTE"] == cohorte_sel
if mes_sel != "Todos":
    mask &= b["MES"] == mes_sel
if sup_sel != "Todos":
    mask &= b["_SUPERVISOR"] == sup_sel
if nivel_sel != "Todos":
    mask &= b["Nivel Formación"] == nivel_sel
if prog_sel != "Todos":
    mask &= b["Programa"] == prog_sel
if estado_sel != "Todos":
    mask &= b["ESTADO"] == estado_sel
if financiacion_sel != "Todos":
    mask &= b["Financiación"] == financiacion_sel
b = b[mask].copy()

# Igual a `b` pero sin el recorte de Desde/Hasta: el comparativo de cumplimiento por
# supervisor y mes necesita ver varios meses a la vez, y por defecto Desde/Hasta solo
# cubren el mes en curso (para no arrastrar los residuales históricos de la Base).
mask_sin_fecha = pd.Series(True, index=base_full.index)
if cohorte_sel != "Todos":
    mask_sin_fecha &= base_full["COHORTE"] == cohorte_sel
if mes_sel != "Todos":
    mask_sin_fecha &= base_full["MES"] == mes_sel
if sup_sel != "Todos":
    mask_sin_fecha &= base_full["_SUPERVISOR"] == sup_sel
if nivel_sel != "Todos":
    mask_sin_fecha &= base_full["Nivel Formación"] == nivel_sel
if prog_sel != "Todos":
    mask_sin_fecha &= base_full["Programa"] == prog_sel
if estado_sel != "Todos":
    mask_sin_fecha &= base_full["ESTADO"] == estado_sel
if financiacion_sel != "Todos":
    mask_sin_fecha &= base_full["Financiación"] == financiacion_sel
b_sin_fecha = base_full[mask_sin_fecha].copy()

_base_avance = base_full
if cohorte_sel != "Todos":
    _base_avance = _base_avance[_base_avance["COHORTE"] == cohorte_sel]
if mes_sel != "Todos":
    _base_avance = _base_avance[_base_avance["MES"] == mes_sel]
_base_avance = _base_avance[(_base_avance["_FECHA"].dt.date >= fecha_ini) & (_base_avance["_FECHA"].dt.date <= fecha_fin)]
tabla, total_general = _tabla_avance(_base_avance, metas_full, fecha_ini, fecha_fin)

total_mat = len(b)
pct_credito = (b["Financiación"] == "CREDITO").mean() * 100 if total_mat else 0
descuento_total = abs(b["Descuento"].sum()) if total_mat else 0.0
cumplimiento = (total_general["REAL"] / total_general["META"] * 100) if total_general["META"] else 0

_home_pg = st.Page("home.py", title="Inicio", icon="🏠", default=True)
_insc_pg = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
_cuart_pg = st.Page("pages/3_Cuartiles.py", title="Cuartiles", icon="🏆")
_cont_pg = st.Page("pages/4_Contactabilidad.py", title="Contactabilidad", icon="📞")

# ─────────────────────────────────────────────
# ENCABEZADO
# ─────────────────────────────────────────────
rango = f"{fecha_ini.strftime('%d/%m/%Y')} – {fecha_fin.strftime('%d/%m/%Y')}"
with st.container(key="hdrbanner"):
    st.markdown(f"""
    <div class='hb-eyebrow'><span class='hb-dot'></span>Centro de Control · Uniminuto 2026</div>
    <div class='hb-title'>Módulo de Matrículas</div>
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
        if st.button("📝 Inscripciones", key="hdr_insc", width="stretch"):
            st.switch_page(_insc_pg)
    with nb3:
        st.button("🎓 Matrículas", key="hdr_mat", width="stretch", type="primary")
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
credito_color = "#818CF8"
faltan_total = int(total_general["FALTAN"])
faltan_color = COLOR_SUCCESS if faltan_total == 0 else COLOR_DANGER

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_ACCENT}'>
        <div class='kpi-bg-icon'>🎓</div>
        <div>
            <div class='kpi-label'>Total matrículas</div>
            <div class='kpi-value' style='color:#7DD3FC'>{total_mat:,}</div>
            <div class='kpi-sub'>en el rango seleccionado</div>
        </div>
        {kpi_bar(total_mat, COLOR_ACCENT, max(total_mat, 1))}
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class='kpi-card' style='--kc:{faltan_color}'>
        <div class='kpi-bg-icon'>🚩</div>
        <div>
            <div class='kpi-label'>Faltan para la meta</div>
            <div class='kpi-value' style='color:{faltan_color}'>{faltan_total:,}</div>
            <div class='kpi-sub'>matrículas · suma de todos los supervisores</div>
        </div>
        {kpi_bar(faltan_total, faltan_color, max(int(total_general["META"]), 1))}
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
    st.markdown(f"""<div class='kpi-card' style='--kc:{credito_color}'>
        <div class='kpi-bg-icon'>💳</div>
        <div>
            <div class='kpi-label'>% Crédito</div>
            <div class='kpi-value' style='color:{credito_color}'>{pct_credito:.1f}%</div>
            <div class='kpi-sub'>Descuento otorgado: {_fmt_cop(descuento_total)}</div>
        </div>
        {kpi_bar(pct_credito, credito_color)}
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COMPARATIVOS
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#38BDF8'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(56,189,248,0.20),rgba(56,189,248,0.06))'>📐</div>
    <div class='sec-text'>
        <div class='sec-title'>Comparativos</div>
        <div class='sec-desc'>Evolución del cumplimiento por supervisor, comparativo por coordinador y patrón semanal de matrícula.</div>
    </div>
    <span class='sec-tag' style='background:#38BDF8'>Tendencias</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""<div class='chart-hdr' style='--cc:#38BDF8'>
    <span class='ch-icon'>📈</span>
    <div class='ch-texts'><div class='ch-title'>Cumplimiento por supervisor y mes</div><div class='ch-sub'>Top 8 supervisores por volumen · % real vs. meta mensual</div></div>
</div>""", unsafe_allow_html=True)
st.plotly_chart(_fig_supervisor_mes(b_sin_fecha, metas_full), width="stretch", config={"displayModeBar": False})

_mapa_sup_coord = _mapa_supervisor_coordinador(base_full)
ccol1, ccol2 = st.columns(2)
with ccol1:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_PRIMARY}'>
        <span class='ch-icon'>🧭</span>
        <div class='ch-texts'><div class='ch-title'>Por coordinador</div><div class='ch-sub'>Real vs. faltan para la meta</div></div>
    </div>""", unsafe_allow_html=True)
    st.plotly_chart(_fig_coordinador(tabla, _mapa_sup_coord), width="stretch", config={"displayModeBar": False})
with ccol2:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_ACCENT}'>
        <span class='ch-icon'>🗓️</span>
        <div class='ch-texts'><div class='ch-title'>Por día de la semana</div><div class='ch-sub'>Patrón operativo de contabilización</div></div>
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
        <div class='sec-desc'>Meta mensual (Meta matriculas) ÷ días hábiles del mes (lunes a sábado, sin festivos) × días hábiles del período seleccionado.</div>
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
        <div class='tbl-hdr-title'>Matrículas por Supervisor</div>
        <div class='tbl-hdr-desc'>Real · Meta · Faltan · Cumplimiento — cohorte y período seleccionados</div>
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
# DISTRIBUCIÓN
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#8B5CF6'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(139,92,246,0.20),rgba(139,92,246,0.06))'>🧩</div>
    <div class='sec-text'>
        <div class='sec-title'>Distribución</div>
        <div class='sec-desc'>Matrículas por programa, nivel de formación y forma de financiación.</div>
    </div>
    <span class='sec-tag' style='background:#8B5CF6'>Composición</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""<div class='chart-hdr' style='--cc:#818CF8'>
    <span class='ch-icon'>🎓</span>
    <div class='ch-texts'><div class='ch-title'>Top 10 programas</div><div class='ch-sub'>Sobre el rango y filtros seleccionados</div></div>
</div>""", unsafe_allow_html=True)
st.plotly_chart(_fig_programa(b), width="stretch", config={"displayModeBar": False})

dcol1, dcol2 = st.columns(2)
with dcol1:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_SUCCESS}'>
        <span class='ch-icon'>📚</span>
        <div class='ch-texts'><div class='ch-title'>Por nivel de formación</div><div class='ch-sub'>Pregrado · Especialización · Maestría</div></div>
    </div>""", unsafe_allow_html=True)
    st.plotly_chart(_fig_nivel(b), width="stretch", config={"displayModeBar": False})
with dcol2:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_ACCENT}'>
        <span class='ch-icon'>💳</span>
        <div class='ch-texts'><div class='ch-title'>Por financiación</div><div class='ch-sub'>Contado · Crédito · Pendiente</div></div>
    </div>""", unsafe_allow_html=True)
    st.plotly_chart(_fig_financiacion(b), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# TENDENCIA
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_ACCENT}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(14,165,233,0.20),rgba(14,165,233,0.06))'>📈</div>
    <div class='sec-text'>
        <div class='sec-title'>Tendencia</div>
        <div class='sec-desc'>Matrículas contabilizadas por día en el rango seleccionado.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_ACCENT}'>Serie diaria</span>
</div>
""", unsafe_allow_html=True)
st.plotly_chart(_fig_tendencia(b), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# TOPS
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#F59E0B'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(245,158,11,0.20),rgba(245,158,11,0.06))'>🏅</div>
    <div class='sec-text'>
        <div class='sec-title'>Tops y Rankings</div>
        <div class='sec-desc'>Los asesores, matrículas y supervisores más destacados del período.</div>
    </div>
    <span class='sec-tag' style='background:#F59E0B'>Ranking</span>
</div>
""", unsafe_allow_html=True)

_top_asesores = (
    b.dropna(subset=["_ASESOR"]).groupby("_ASESOR")
    .agg(total=("_ASESOR", "size"), sup=("_SUPERVISOR", "first"))
    .sort_values("total", ascending=False).head(10)
)
_top_supervisores = (
    b.dropna(subset=["_SUPERVISOR"]).groupby("_SUPERVISOR")
    .agg(total=("_SUPERVISOR", "size"), ingreso=("Ingreso neto", "sum"))
    .sort_values("total", ascending=False).head(10)
)
_ultimas = b.dropna(subset=["_FECHA"]).sort_values("_FECHA", ascending=False).head(10)

tcol1, tcol2, tcol3 = st.columns(3)
with tcol1:
    st.markdown("""<div class='chart-hdr' style='--cc:#38BDF8'>
        <span class='ch-icon'>🧑‍💻</span>
        <div class='ch-texts'><div class='ch-title'>Top 10 asesores</div><div class='ch-sub'>Con más matrículas</div></div>
    </div>""", unsafe_allow_html=True)
    _filas = [(nom, str(row["sup"]), f"{int(row['total'])}") for nom, row in _top_asesores.iterrows()]
    st.markdown(_top_lista_html(_filas, "#38BDF8"), unsafe_allow_html=True)
with tcol2:
    st.markdown("""<div class='chart-hdr' style='--cc:#F59E0B'>
        <span class='ch-icon'>🕓</span>
        <div class='ch-texts'><div class='ch-title'>Top 10 últimas</div><div class='ch-sub'>Matrículas más recientes</div></div>
    </div>""", unsafe_allow_html=True)
    _filas = [
        (row["NOMBRE_COMPLETO"], str(row["Programa"])[:28], row["_FECHA"].strftime("%d/%m/%Y"))
        for _, row in _ultimas.iterrows()
    ]
    st.markdown(_top_lista_html(_filas, "#F59E0B"), unsafe_allow_html=True)
with tcol3:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_SUCCESS}'>
        <span class='ch-icon'>👥</span>
        <div class='ch-texts'><div class='ch-title'>Top 10 supervisores</div><div class='ch-sub'>Por volumen total</div></div>
    </div>""", unsafe_allow_html=True)
    _filas = [
        (sup, f"{_fmt_cop(row['ingreso'])} ingreso neto", f"{int(row['total'])}")
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
        <div class='sec-desc'>Listado de matrículas filtradas, descargable en Excel.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_PRIMARY}'>{total_mat} matrículas</span>
</div>
""", unsafe_allow_html=True)

_detalle = b.copy()
_detalle["Ingreso neto"] = _detalle["Ingreso neto"].map(_fmt_cop)
_detalle["Descuento"] = _detalle["Descuento"].map(_fmt_cop)
cols_detalle = {
    "NOMBRE_COMPLETO": "NOMBRE", "Cedula": "CEDULA", "Programa": "PROGRAMA",
    "Nivel Formación": "NIVEL", "COHORTE": "COHORTE", "ESTADO": "ESTADO",
    "Financiación": "FINANCIACIÓN", "Ingreso neto": "INGRESO NETO", "Descuento": "DESCUENTO",
    "_ASESOR": "ASESOR", "_SUPERVISOR": "SUPERVISOR", "_COORDINADOR": "COORDINADOR",
    "Fecha Contabilización": "FECHA CONTABILIZACIÓN",
}
_detalle = _detalle[[c for c in cols_detalle if c in _detalle.columns]].rename(columns=cols_detalle)

st.markdown(f"""<div class='tbl-hdr' style='background:linear-gradient(135deg,#0C2B1D,#0EA5E9)'>
    <span class='tbl-hdr-icon'>📑</span>
    <div class='tbl-hdr-body'>
        <div class='tbl-hdr-title'>Listado de Matrículas</div>
        <div class='tbl-hdr-desc'>Registros individuales — cohorte y período seleccionados</div>
    </div>
    <span class='tbl-hdr-badge'>{total_mat} matrículas</span>
</div>""", unsafe_allow_html=True)
df_descarga(_detalle, "matriculas_detalle.xlsx", width="stretch", hide_index=True, height=360)
