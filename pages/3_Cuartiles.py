import base64
import io
import urllib.parse

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Hojas de Google Sheets (compartidas como "Cualquiera con el enlace: Lector").
# Cuartiles cruza 3 hojas: Base de Matrículas (fuente del cuartil), Base de Inscripciones
# (solo para mostrar su real/meta) y Metas (respaldo para que salgan todos los asesores).
_SHEET_ID_MATRICULAS = "1yh02o6obFpiMHUenyaBX6ZKmTivdSrY5_usVisb0I74"
_SHEET_ID_INSCRIPCIONES = "14DOLvF_d-qhd-VBE62M6hnfqtOH3EYcggjBLgwHiC8w"
_SHEET_ID_METAS = "1byJ5Sw_P_xKew5xMbWz9KQSTQfc_J-Fm"
_SHEET_ID_LEADS = "1eJYJxr_9qOF4yTLjXU1fr1P9asoXdnzoY_MkWME9FhY"


def _url_hoja(sheet_id: str, nombre_hoja: str) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(nombre_hoja)}"
    )


# ─────────────────────────────────────────────
# COLORES (mismo esquema que Matrículas / Inscripciones)
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

_COLOR_CUARTIL = {"Q1": COLOR_DANGER, "Q2": COLOR_WARNING, "Q3": COLOR_ACCENT, "Q4": COLOR_SUCCESS}
_CUARTIL_NUM = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}


# ─────────────────────────────────────────────
# DESCARGA (idéntico a Matrículas / Inscripciones)
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
def _cargar_matriculas() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID_MATRICULAS, "Base"), encoding="utf-8", low_memory=False)
    df.columns = df.columns.str.strip()
    df = df[df["Cedula"].notna()].copy()
    df["_CC"] = pd.to_numeric(df["Documento"], errors="coerce").astype("Int64")
    df["_ASESOR"] = df["Asesor.1"].fillna(df["Asesor"]).fillna("Sin asignar")
    df["_SUPERVISOR"] = df["Supervisor.1"].fillna("Sin asignar")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def _cargar_inscripciones() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID_INSCRIPCIONES, "Base"), encoding="utf-8", low_memory=False)
    df.columns = df.columns.str.strip()
    df = df[df["DNI"].notna()].copy()
    df["_CC"] = pd.to_numeric(df["CEDULA AGENT"], errors="coerce").astype("Int64")
    df["_ASESOR"] = df["NOMBRE AGENT"].fillna("Sin asignar")
    df["_SUPERVISOR"] = df["SUPERVISOR"].fillna("Sin asignar")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def _cargar_metas() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID_METAS, "Consolidado"), encoding="utf-8", low_memory=False)
    df.columns = df.columns.str.strip()
    df["_CC"] = pd.to_numeric(df["CC"], errors="coerce").astype("Int64")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def _cargar_leads() -> pd.DataFrame:
    df = pd.read_csv(_url_hoja(_SHEET_ID_LEADS, "Resumen diario"), encoding="utf-8", low_memory=False)
    df.columns = df.columns.str.strip()
    df["_FECHA"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["_FECHA"]).copy()
    df["_CC"] = pd.to_numeric(df["Cedula"], errors="coerce").astype("Int64")
    df["_INSUMO"] = pd.to_numeric(df["Leads asignados ese día"], errors="coerce").fillna(0).astype(int)
    df["MES"] = df["_FECHA"].dt.month.map(lambda m: _MES_ORDEN[int(m) - 1])
    df["AÑO"] = df["_FECHA"].dt.year
    return df


_COLS_CLASIFICACION = [
    "ASESOR", "SUPERVISOR", "META_INSC", "META_MAT", "REAL_INSC", "REAL_MAT", "INSUMO",
    "CUMPL_INSC", "CUMPL_MAT", "CUARTIL", "CUARTIL_INSC",
]


def _tabla_clasificacion(mat: pd.DataFrame, insc: pd.DataFrame, metas: pd.DataFrame, leads: pd.DataFrame, mes_sel: str) -> pd.DataFrame:
    """Universo del mes = todos los asesores con Meta asignada ese MES/AÑO (Metas es el
    respaldo para que aparezcan aunque tengan 0 real). El cuartil se calcula sobre REAL_MAT
    de ese universo completo — un asesor en 0 matrículas es un dato de desempeño válido,
    no se excluye."""
    anios = metas.loc[metas["MES"] == mes_sel, "AÑO"].dropna()
    if not len(anios):
        return pd.DataFrame(columns=_COLS_CLASIFICACION)
    anio_sel = int(anios.mode().iat[0])

    m = metas[(metas["MES"] == mes_sel) & (metas["AÑO"] == anio_sel)]
    meta_asesor = (
        m.dropna(subset=["_CC"]).drop_duplicates("_CC").set_index("_CC")
        .rename(columns={
            "NOMBRE ASESOR": "_ASESOR_META", "SUPERVISOR": "_SUPERVISOR_META",
            "Meta inscripciones": "META_INSC", "Meta matriculas": "META_MAT",
        })
        [["_ASESOR_META", "_SUPERVISOR_META", "META_INSC", "META_MAT"]]
    )

    real_mat = (
        mat[(mat["MES"] == mes_sel) & (mat["AÑO"] == anio_sel)].dropna(subset=["_CC"])
        .groupby("_CC").agg(REAL_MAT=("_CC", "size"), _ASESOR_MAT=("_ASESOR", "first"), _SUPERVISOR_MAT=("_SUPERVISOR", "first"))
    )
    real_insc = (
        insc[(insc["MES"] == mes_sel) & (insc["AÑO"] == anio_sel)].dropna(subset=["_CC"])
        .groupby("_CC").agg(REAL_INSC=("_CC", "size"), _ASESOR_INSC=("_ASESOR", "first"), _SUPERVISOR_INSC=("_SUPERVISOR", "first"))
    )
    insumo_mes = (
        leads[(leads["MES"] == mes_sel) & (leads["AÑO"] == anio_sel)].dropna(subset=["_CC"])
        .groupby("_CC")["_INSUMO"].sum().rename("INSUMO")
    )

    tabla = meta_asesor.join(real_mat, how="outer").join(real_insc, how="outer").join(insumo_mes, how="left")
    if not len(tabla):
        return pd.DataFrame(columns=_COLS_CLASIFICACION)

    for c in ("META_INSC", "META_MAT", "REAL_INSC", "REAL_MAT", "INSUMO"):
        tabla[c] = tabla[c].fillna(0).astype(int)

    tabla["ASESOR"] = tabla["_ASESOR_MAT"].fillna(tabla["_ASESOR_INSC"]).fillna(tabla["_ASESOR_META"]).fillna("Sin asignar")
    tabla["SUPERVISOR"] = tabla["_SUPERVISOR_MAT"].fillna(tabla["_SUPERVISOR_INSC"]).fillna(tabla["_SUPERVISOR_META"]).fillna("Sin asignar")

    tabla["CUMPL_INSC"] = np.where(
        tabla["META_INSC"] > 0, tabla["REAL_INSC"] / tabla["META_INSC"] * 100,
        np.where(tabla["REAL_INSC"] > 0, 100.0, 0.0),
    )
    tabla["CUMPL_MAT"] = np.where(
        tabla["META_MAT"] > 0, tabla["REAL_MAT"] / tabla["META_MAT"] * 100,
        np.where(tabla["REAL_MAT"] > 0, 100.0, 0.0),
    )

    if len(tabla) >= 4:
        tabla["CUARTIL"] = pd.qcut(tabla["REAL_MAT"].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
        tabla["CUARTIL_INSC"] = pd.qcut(tabla["REAL_INSC"].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
    else:
        tabla["CUARTIL"] = "Q4"
        tabla["CUARTIL_INSC"] = "Q4"

    tabla = tabla[_COLS_CLASIFICACION].sort_values("REAL_MAT", ascending=False)
    return tabla.reset_index(drop=True)


def _tabla_evolucion_reciente(
    mat: pd.DataFrame, insc: pd.DataFrame, metas: pd.DataFrame, leads: pd.DataFrame,
    meses_disponibles: list[str], n_meses: int = 3,
) -> tuple[list[dict], list[str]]:
    """Una fila por asesor con Matrículas/Inscripciones/Cuartil (de cada métrica) de cada uno
    de los últimos n_meses, más un cuartil CONSOLIDADO por métrica (calculado sobre la suma de
    los n_meses, no mes a mes) y si evolucionó (comparando su primer y último cuartil de
    matrículas válido en la ventana). Universo = unión de asesores clasificados en cualquiera
    de esos meses (todos los expertos, no sólo los del mes más reciente)."""
    meses_recientes = meses_disponibles[-n_meses:]
    tablas_mes = {}
    for mes in meses_recientes:
        t = _tabla_clasificacion(mat, insc, metas, leads, mes)
        # Un mismo nombre puede tener dos cédulas distintas en la base (dato duplicado/reingreso);
        # sin agrupar, t.loc[asesor] devolvería 2 filas en vez de 1 y rompería el resto de la función.
        tablas_mes[mes] = t.groupby("ASESOR", as_index=True).agg(
            SUPERVISOR=("SUPERVISOR", "first"),
            REAL_MAT=("REAL_MAT", "sum"),
            REAL_INSC=("REAL_INSC", "sum"),
            CUARTIL=("CUARTIL", "first"),
            CUARTIL_INSC=("CUARTIL_INSC", "first"),
        )

    todos_asesores = set()
    for t in tablas_mes.values():
        todos_asesores.update(t.index)

    filas = []
    for asesor in todos_asesores:
        supervisor = "Sin asignar"
        cuartiles_validos = []
        meses_data = []
        mat_total = insc_total = 0
        for mes in meses_recientes:
            t = tablas_mes[mes]
            if asesor in t.index:
                row = t.loc[asesor]
                supervisor = row["SUPERVISOR"]
                meses_data.append({
                    "MAT": int(row["REAL_MAT"]), "CUARTIL": row["CUARTIL"],
                    "INSC": int(row["REAL_INSC"]), "CUARTIL_INSC": row["CUARTIL_INSC"],
                })
                cuartiles_validos.append(_CUARTIL_NUM[row["CUARTIL"]])
                mat_total += int(row["REAL_MAT"])
                insc_total += int(row["REAL_INSC"])
            else:
                meses_data.append(None)

        delta = cuartiles_validos[-1] - cuartiles_validos[0] if len(cuartiles_validos) >= 2 else None

        filas.append({
            "ASESOR": asesor, "SUPERVISOR": supervisor, "MESES": meses_data,
            "MAT_TOTAL": mat_total, "INSC_TOTAL": insc_total, "DELTA": delta,
        })

    # Cuartil consolidado: se calcula sobre la suma de los n_meses de TODO el universo, no
    # promediando los cuartiles mensuales (evita que un mes malo puntual pese más de la cuenta).
    if len(filas) >= 4:
        mat_totales = pd.Series([f["MAT_TOTAL"] for f in filas])
        insc_totales = pd.Series([f["INSC_TOTAL"] for f in filas])
        q_mat = pd.qcut(mat_totales.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
        q_insc = pd.qcut(insc_totales.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
        for f, qm, qi in zip(filas, q_mat, q_insc):
            f["CUARTIL_MAT_CONSOLIDADO"] = qm
            f["CUARTIL_INSC_CONSOLIDADO"] = qi
    else:
        for f in filas:
            f["CUARTIL_MAT_CONSOLIDADO"] = "Q4"
            f["CUARTIL_INSC_CONSOLIDADO"] = "Q4"

    filas.sort(key=lambda f: f["MAT_TOTAL"], reverse=True)
    return filas, meses_recientes


# ─────────────────────────────────────────────
# TABLA HTML — Clasificación de asesores
# ─────────────────────────────────────────────
def _cumpl_cell_html(pct: float) -> str:
    color = COLOR_SUCCESS if pct >= 100 else (COLOR_WARNING if pct >= 70 else COLOR_DANGER)
    return (
        "<td class='cumpl-cell'><div class='cumpl-wrap'>"
        f"<div class='cumpl-bar-track'><div class='cumpl-bar-fill' style='width:{min(pct, 100):.0f}%;background:{color}'></div></div>"
        f"<span class='cumpl-pct' style='color:{color}'>{pct:.0f}%</span>"
        "</div></td>"
    )


def _fila_clasificacion_html(row) -> str:
    color_q = _COLOR_CUARTIL.get(row["CUARTIL"], "#94A3B8")
    return (
        "<tr>"
        f"<td class='sup-cell'>{row['ASESOR']}</td>"
        f"<td>{row['SUPERVISOR']}</td>"
        f"<td>{row['META_INSC']}</td>"
        f"<td>{row['META_MAT']}</td>"
        f"<td>{row['REAL_INSC']}</td>"
        f"<td>{row['REAL_MAT']}</td>"
        f"<td>{row['INSUMO']}</td>"
        f"{_cumpl_cell_html(row['CUMPL_INSC'])}"
        f"{_cumpl_cell_html(row['CUMPL_MAT'])}"
        f"<td><span class='cuartil-badge' style='background:{color_q}22;color:{color_q};border-color:{color_q}66'>{row['CUARTIL']}</span></td>"
        "</tr>"
    )


def _render_tabla_clasificacion(tabla: pd.DataFrame):
    rows_html = "".join(_fila_clasificacion_html(r) for _, r in tabla.iterrows())
    table_html = (
        "<div class='avance-tabla-wrap'><table class='avance-tabla'><thead><tr>"
        "<th class='grp-sup'>Asesor</th><th class='grp-sup'>Supervisor</th>"
        "<th class='grp-total'>Meta Insc.</th><th class='grp-total'>Meta Mat.</th>"
        "<th class='grp-total'>Insc.</th><th class='grp-total'>Mat.</th><th class='grp-total'>Insumo</th>"
        "<th class='grp-cumpl'>Cumpl. Insc.</th><th class='grp-cumpl'>Cumpl. Mat.</th>"
        "<th class='grp-total'>Cuartil</th>"
        "</tr></thead><tbody>"
        f"{rows_html}"
        "</tbody></table></div>"
    )
    with st.container(key="tabla_clasificacion"):
        st.markdown(table_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LISTAS "TOP" (rankings)
# ─────────────────────────────────────────────
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
# GRÁFICOS
# ─────────────────────────────────────────────
def _fig_conversion(tabla: pd.DataFrame, min_insumo: int = 30, top_n: int = 15) -> go.Figure:
    """Conversión = Matrículas reales / Insumo (leads) recibidos, en %. Sólo asesores con
    insumo suficiente (min_insumo) para que el % no sea ruido de muestras muy chicas."""
    d = tabla[tabla["INSUMO"] >= min_insumo].copy()
    d["CONVERSION"] = d["REAL_MAT"] / d["INSUMO"] * 100
    d = d.sort_values("CONVERSION", ascending=False).head(top_n).sort_values("CONVERSION")

    mediana = d["CONVERSION"].median() if len(d) else 0
    colores = [COLOR_SUCCESS if v >= mediana else COLOR_WARNING for v in d["CONVERSION"].tolist()]

    fig = go.Figure(go.Bar(
        x=d["CONVERSION"].tolist(), y=[str(a)[:34] for a in d["ASESOR"].tolist()], orientation="h",
        marker=dict(color=colores),
        text=[f"{v:.1f}%" for v in d["CONVERSION"].tolist()], textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color="#CBD3F2", family="Inter"),
        customdata=d["INSUMO"].tolist(),
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% conversión<br>%{customdata} leads recibidos<extra></extra>",
    ))
    fig.update_layout(
        height=max(280, len(d) * 26 + 60), margin=dict(l=10, r=50, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", ticksuffix="%",
                   tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"), automargin=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.62)"),
                   automargin=True),
    )
    return fig


def _fig_cuartil_supervisor(tabla: pd.DataFrame) -> go.Figure:
    grp = tabla.groupby(["SUPERVISOR", "CUARTIL"]).size().unstack(fill_value=0)
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        if q not in grp.columns:
            grp[q] = 0
    grp = grp[["Q1", "Q2", "Q3", "Q4"]]
    grp = grp.loc[grp.sum(axis=1).sort_values().index]

    fig = go.Figure()
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        fig.add_trace(go.Bar(
            y=grp.index, x=grp[q], orientation="h", name=q,
            marker=dict(color=_COLOR_CUARTIL[q]),
        ))
    fig.update_layout(
        barmode="stack", height=max(280, len(grp) * 26 + 60), margin=dict(l=10, r=20, t=10, b=10),
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


# ─────────────────────────────────────────────
# TABLA HTML — Evolución reciente (últimos N meses)
# ─────────────────────────────────────────────
def _qcell_html(valor: int, cuartil: str) -> str:
    color_q = _COLOR_CUARTIL.get(cuartil, "#94A3B8")
    return (
        "<td class='qcell'>"
        f"<span class='qcell-val'>{valor}</span>"
        f"<span class='cuartil-badge qcell-badge' style='background:{color_q}22;color:{color_q};border-color:{color_q}66'>{cuartil}</span>"
        "</td>"
    )


def _celda_mes_html(datos_mes) -> str:
    if not datos_mes:
        return "<td class='mes-vacio'>—</td><td class='mes-vacio'>—</td>"
    return _qcell_html(datos_mes["MAT"], datos_mes["CUARTIL"]) + _qcell_html(datos_mes["INSC"], datos_mes["CUARTIL_INSC"])


def _badge_evolucion_html(delta) -> str:
    if delta is None:
        return "<span class='evo-badge evo-na'>Sin datos</span>"
    if delta > 0:
        return "<span class='evo-badge evo-up'>▲ Subió</span>"
    if delta < 0:
        return "<span class='evo-badge evo-down'>▼ Bajó</span>"
    return "<span class='evo-badge evo-flat'>● Se mantuvo</span>"


def _fila_evolucion_html(fila: dict) -> str:
    celdas_meses = "".join(_celda_mes_html(m) for m in fila["MESES"])
    celda_consolidado = _qcell_html(fila["MAT_TOTAL"], fila["CUARTIL_MAT_CONSOLIDADO"]) + _qcell_html(fila["INSC_TOTAL"], fila["CUARTIL_INSC_CONSOLIDADO"])
    return (
        "<tr>"
        f"<td class='sup-cell'>{fila['ASESOR']}</td>"
        f"<td>{fila['SUPERVISOR']}</td>"
        f"{celdas_meses}"
        f"{celda_consolidado}"
        f"<td>{_badge_evolucion_html(fila['DELTA'])}</td>"
        "</tr>"
    )


def _render_tabla_evolucion(filas: list[dict], meses_recientes: list[str]):
    rows_html = "".join(_fila_evolucion_html(f) for f in filas)
    meses_headers = "".join(f"<th class='grp-mes' colspan='2'>{mes}</th>" for mes in meses_recientes)
    meses_subheaders = "".join(
        "<th class='grp-mes'>Mat.</th><th class='grp-mes'>Insc.</th>" for _ in meses_recientes
    )
    table_html = (
        "<div class='avance-tabla-wrap'><table class='avance-tabla'><thead>"
        "<tr><th class='grp-sup' rowspan='2'>Asesor</th><th class='grp-sup' rowspan='2'>Supervisor</th>"
        f"{meses_headers}"
        "<th class='grp-consolidado' colspan='2'>Consolidado (3 meses)</th>"
        "<th class='grp-total' rowspan='2'>Evolución</th></tr>"
        f"<tr>{meses_subheaders}<th class='grp-consolidado'>Mat.</th><th class='grp-consolidado'>Insc.</th></tr>"
        "</thead><tbody>"
        f"{rows_html}"
        "</tbody></table></div>"
    )
    with st.container(key="tabla_evolucion"):
        st.markdown(table_html, unsafe_allow_html=True)


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
mat_full = _cargar_matriculas()
insc_full = _cargar_inscripciones()
metas_full = _cargar_metas()
leads_full = _cargar_leads()

meses_disponibles = [m for m in _MES_ORDEN if m in mat_full["MES"].unique()]

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

    if meses_disponibles:
        mes_sel = st.selectbox("Mes", meses_disponibles, index=len(meses_disponibles) - 1)
    else:
        mes_sel = None
        st.caption("⚠️ Sin datos de matrículas para cuartilizar.")

    st.markdown("""<div class='sbh'>
        <div class='sbh-num' style='color:#34D399!important;background:rgba(52,211,153,0.12);border-color:rgba(52,211,153,0.22)'>02</div>
        <div class='sbh-lbl'>Filtros</div>
        <div class='sbh-rule'></div>
    </div>""", unsafe_allow_html=True)

    tabla_mes_full = _tabla_clasificacion(mat_full, insc_full, metas_full, leads_full, mes_sel) if mes_sel else pd.DataFrame(columns=_COLS_CLASIFICACION)
    supervisores = ["Todos"] + sorted(tabla_mes_full["SUPERVISOR"].unique().tolist())
    sup_sel = st.selectbox("Supervisor", supervisores)

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

    /* ── Tabla Clasificación: HTML propio (mismo esquema que Avance vs. Meta) ── */
    .avance-tabla-wrap {{ overflow:auto;max-height:520px;border-radius:16px;border:1px solid rgba(255,255,255,0.10);
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
    .cuartil-badge {{ display:inline-block;padding:3px 13px;border-radius:99px;font-weight:800;font-size:11px;border:1px solid;letter-spacing:0.03em; }}

    /* ── Tabla Evolución reciente (últimos N meses) ── */
    .avance-tabla thead th.grp-mes {{ background:linear-gradient(180deg, rgba(129,140,248,0.20), rgba(129,140,248,0.07)); }}
    .avance-tabla thead th.grp-consolidado {{ background:linear-gradient(180deg, rgba(244,63,94,0.22), rgba(244,63,94,0.08)); }}
    .avance-tabla td.mes-vacio {{ color:rgba(255,255,255,0.25); }}
    .qcell {{ white-space:nowrap; }}
    .qcell-val {{ font-weight:700;color:white;margin-right:7px; }}
    .qcell-badge {{ padding:2px 9px !important;font-size:9.5px !important; }}
    .evo-badge {{ display:inline-flex;align-items:center;gap:4px;padding:3px 11px;border-radius:99px;font-weight:800;font-size:10.5px;white-space:nowrap; }}
    .evo-up {{ background:rgba(52,211,153,0.16);color:{COLOR_SUCCESS}; }}
    .evo-down {{ background:rgba(239,68,68,0.16);color:{COLOR_DANGER}; }}
    .evo-flat {{ background:rgba(148,163,184,0.16);color:#94A3B8; }}
    .evo-na {{ background:rgba(148,163,184,0.08);color:rgba(255,255,255,0.30); }}

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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# NAVEGACIÓN + ENCABEZADO
# ─────────────────────────────────────────────
_home_pg = st.Page("home.py", title="Inicio", icon="🏠", default=True)
_insc_pg = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
_mat_pg = st.Page("pages/2_Matriculas.py", title="Matrículas", icon="🎓")
_cont_pg = st.Page("pages/4_Contactabilidad.py", title="Real time", icon="📞")
_leads_pg = st.Page("pages/5_Leads.py", title="Leads", icon="🎯")

with st.container(key="hdrbanner"):
    st.markdown(f"""
    <div class='hb-eyebrow'><span class='hb-dot'></span>Centro de Control · Uniminuto 2026</div>
    <div class='hb-title'>Módulo de Cuartiles</div>
    <div class='hb-meta'>
        <span class='hb-chip'>📅 Mes <b>{mes_sel or "—"}</b></span>
        <span class='hb-chip'>🧭 Basado en volumen de Matrículas</span>
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
        st.button("🏆 Cuartiles", key="hdr_cuart", width="stretch", type="primary")
    with nb5:
        if st.button("📞 Real time", key="hdr_cont", width="stretch"):
            st.switch_page(_cont_pg)
    with nb6:
        if st.button("🎯 Leads", key="hdr_leads", width="stretch"):
            st.switch_page(_leads_pg)

if not mes_sel:
    st.stop()

tabla_mes = tabla_mes_full
tabla_vista = tabla_mes if sup_sel == "Todos" else tabla_mes[tabla_mes["SUPERVISOR"] == sup_sel]

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
def kpi_bar(pct, color, max_val=100):
    fill = min(pct / max_val * 100, 100) if max_val else 0
    return f"<div class='kpi-bar-wrap'><div class='kpi-bar-fill' style='width:{fill:.0f}%;background:{color};'></div></div>"


total_asesores = len(tabla_mes)
n_q1 = int((tabla_mes["CUARTIL"] == "Q1").sum())
n_q4 = int((tabla_mes["CUARTIL"] == "Q4").sum())
cumpl_prom_mat = tabla_mes["CUMPL_MAT"].mean() if total_asesores else 0.0
color_cumpl = COLOR_SUCCESS if cumpl_prom_mat >= 100 else (COLOR_WARNING if cumpl_prom_mat >= 70 else COLOR_DANGER)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_ACCENT}'>
        <div class='kpi-bg-icon'>👥</div>
        <div>
            <div class='kpi-label'>Total asesores</div>
            <div class='kpi-value' style='color:#7DD3FC'>{total_asesores}</div>
            <div class='kpi-sub'>cuartilizados en {mes_sel}</div>
        </div>
        {kpi_bar(total_asesores, COLOR_ACCENT, max(total_asesores, 1))}
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_DANGER}'>
        <div class='kpi-bg-icon'>⚠️</div>
        <div>
            <div class='kpi-label'>Asesores en Q1</div>
            <div class='kpi-value' style='color:{COLOR_DANGER}'>{n_q1}</div>
            <div class='kpi-sub'>25% de menor volumen de matrículas</div>
        </div>
        {kpi_bar(n_q1, COLOR_DANGER, max(total_asesores, 1))}
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class='kpi-card' style='--kc:{COLOR_SUCCESS}'>
        <div class='kpi-bg-icon'>🏆</div>
        <div>
            <div class='kpi-label'>Asesores en Q4</div>
            <div class='kpi-value' style='color:{COLOR_SUCCESS}'>{n_q4}</div>
            <div class='kpi-sub'>25% de mayor volumen de matrículas</div>
        </div>
        {kpi_bar(n_q4, COLOR_SUCCESS, max(total_asesores, 1))}
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class='kpi-card' style='--kc:{color_cumpl}'>
        <div class='kpi-bg-icon'>🎯</div>
        <div>
            <div class='kpi-label'>Cumplimiento promedio</div>
            <div class='kpi-value' style='color:{color_cumpl}'>{cumpl_prom_mat:.0f}%</div>
            <div class='kpi-sub'>meta de matrículas, todos los asesores</div>
        </div>
        {kpi_bar(cumpl_prom_mat, color_cumpl)}
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# EVOLUCIÓN RECIENTE (ÚLTIMOS 3 MESES) — primera tabla del módulo
# ─────────────────────────────────────────────
_N_MESES_EVOLUCION = 3
_filas_evolucion, _meses_evolucion = _tabla_evolucion_reciente(
    mat_full, insc_full, metas_full, leads_full, meses_disponibles, n_meses=_N_MESES_EVOLUCION
)

st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_ACCENT}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(14,165,233,0.20),rgba(14,165,233,0.06))'>📈</div>
    <div class='sec-text'>
        <div class='sec-title'>Evolución Reciente</div>
        <div class='sec-desc'>Matrículas e inscripciones de cada asesor en {", ".join(_meses_evolucion) if _meses_evolucion else "los últimos meses"}, con su cuartil por cada métrica — y un cuartil consolidado sobre la suma de los 3 meses.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_ACCENT}'>{len(_filas_evolucion)} asesores</span>
</div>
""", unsafe_allow_html=True)

if _filas_evolucion:
    _render_tabla_evolucion(_filas_evolucion, _meses_evolucion)
else:
    st.caption("Sin histórico suficiente para mostrar la evolución.")

# ─────────────────────────────────────────────
# DISTRIBUCIÓN DEL CUARTIL CONSOLIDADO POR SUPERVISOR
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:#818CF8'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(129,140,248,0.20),rgba(129,140,248,0.06))'>🧭</div>
    <div class='sec-text'>
        <div class='sec-title'>Desempeño Sostenido por Supervisor</div>
        <div class='sec-desc'>Cuántos asesores de cada supervisor caen en cada cuartil CONSOLIDADO de matrículas de {", ".join(_meses_evolucion) if _meses_evolucion else "los últimos meses"} — no un mes bueno aislado, sino el trimestre completo.</div>
    </div>
    <span class='sec-tag' style='background:#818CF8'>Trimestral</span>
</div>
""", unsafe_allow_html=True)
if _filas_evolucion:
    _df_consolidado = pd.DataFrame([
        {"SUPERVISOR": f["SUPERVISOR"], "CUARTIL": f["CUARTIL_MAT_CONSOLIDADO"]} for f in _filas_evolucion
    ])
    st.plotly_chart(_fig_cuartil_supervisor(_df_consolidado), width="stretch", config={"displayModeBar": False})
else:
    st.caption("Sin histórico suficiente para esta gráfica.")

# ─────────────────────────────────────────────
# CLASIFICACIÓN DE ASESORES
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:{COLOR_PRIMARY}'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(52,211,153,0.20),rgba(52,211,153,0.06))'>🏆</div>
    <div class='sec-text'>
        <div class='sec-title'>Clasificación de Asesores</div>
        <div class='sec-desc'>Meta y real de inscripciones y matrículas por asesor, con su cuartil de desempeño del mes.</div>
    </div>
    <span class='sec-tag' style='background:{COLOR_PRIMARY}'>Q1 = menor volumen · Q4 = mayor volumen</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""<div class='tbl-hdr' style='background:linear-gradient(135deg,#0C2B1D,#0EA5E9)'>
    <span class='tbl-hdr-icon'>📋</span>
    <div class='tbl-hdr-body'>
        <div class='tbl-hdr-title'>Asesores — {mes_sel}</div>
        <div class='tbl-hdr-desc'>Ordenado por matrículas reales, de mayor a menor</div>
    </div>
    <span class='tbl-hdr-badge'>{len(tabla_vista)} asesores</span>
</div>""", unsafe_allow_html=True)
_render_tabla_clasificacion(tabla_vista)

_export = tabla_vista.rename(columns={
    "ASESOR": "ASESOR", "SUPERVISOR": "SUPERVISOR",
    "META_INSC": "META INSCRIPCIONES", "META_MAT": "META MATRICULAS",
    "REAL_INSC": "INSCRIPCIONES", "REAL_MAT": "MATRICULAS", "INSUMO": "INSUMO (LEADS)",
    "CUMPL_INSC": "CUMPLIMIENTO INSCRIPCIONES %", "CUMPL_MAT": "CUMPLIMIENTO MATRICULAS %",
    "CUARTIL": "CUARTIL",
})
b64 = base64.b64encode(_excel_bytes(_export)).decode()
st.markdown(
    f'<div style="text-align:right;margin-top:-14px;margin-bottom:8px">'
    f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" '
    f'download="cuartiles_{mes_sel.lower()}.xlsx" '
    f'style="font-size:0.72rem;color:rgba(255,255,255,0.35);text-decoration:none;letter-spacing:0.03em">'
    f'↓ Exportar Excel</a></div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# TOP 10 Y ÚLTIMOS 10 DEL MES
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#F59E0B'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(245,158,11,0.20),rgba(245,158,11,0.06))'>🏅</div>
    <div class='sec-text'>
        <div class='sec-title'>Top 10 y Últimos 10</div>
        <div class='sec-desc'>Extremos de desempeño del mes por volumen de matrículas.</div>
    </div>
    <span class='sec-tag' style='background:#F59E0B'>Ranking</span>
</div>
""", unsafe_allow_html=True)

_top10 = tabla_mes.sort_values("REAL_MAT", ascending=False).head(10)
_ultimos10 = tabla_mes.sort_values("REAL_MAT", ascending=True).head(10)

tcol1, tcol2 = st.columns(2)
with tcol1:
    st.markdown("""<div class='chart-hdr' style='--cc:#34D399'>
        <span class='ch-icon'>🥇</span>
        <div class='ch-texts'><div class='ch-title'>Top 10 asesores</div><div class='ch-sub'>Más matrículas del mes</div></div>
    </div>""", unsafe_allow_html=True)
    _filas = [(row["ASESOR"], row["SUPERVISOR"], f"{int(row['REAL_MAT'])}") for _, row in _top10.iterrows()]
    st.markdown(_top_lista_html(_filas, COLOR_SUCCESS), unsafe_allow_html=True)
with tcol2:
    st.markdown(f"""<div class='chart-hdr' style='--cc:{COLOR_DANGER}'>
        <span class='ch-icon'>⚠️</span>
        <div class='ch-texts'><div class='ch-title'>Últimos 10 asesores</div><div class='ch-sub'>Menos matrículas del mes</div></div>
    </div>""", unsafe_allow_html=True)
    _filas = [(row["ASESOR"], row["SUPERVISOR"], f"{int(row['REAL_MAT'])}") for _, row in _ultimos10.iterrows()]
    st.markdown(_top_lista_html(_filas, COLOR_DANGER), unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COMPARATIVO ENTRE SUPERVISORES
# ─────────────────────────────────────────────
st.markdown("""
<div class='sec-header' style='--sc:#38BDF8'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(56,189,248,0.20),rgba(56,189,248,0.06))'>🧭</div>
    <div class='sec-text'>
        <div class='sec-title'>Comparativo entre Supervisores</div>
        <div class='sec-desc'>Cuántos asesores de cada supervisor caen en cada cuartil.</div>
    </div>
    <span class='sec-tag' style='background:#38BDF8'>Distribución</span>
</div>
""", unsafe_allow_html=True)
st.plotly_chart(_fig_cuartil_supervisor(tabla_mes), width="stretch", config={"displayModeBar": False})

# ─────────────────────────────────────────────
# INSUMO VS. CONVERSIÓN
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='sec-header' style='--sc:#F43F5E'>
    <div class='sec-icon' style='background:linear-gradient(135deg,rgba(244,63,94,0.20),rgba(244,63,94,0.06))'>🎯</div>
    <div class='sec-text'>
        <div class='sec-title'>Insumo vs. Conversión</div>
        <div class='sec-desc'>Qué porcentaje de los leads asignados a cada asesor terminó en matrícula — mide eficiencia, no solo volumen.</div>
    </div>
    <span class='sec-tag' style='background:#F43F5E'>Matrículas ÷ Insumo</span>
</div>
""", unsafe_allow_html=True)

_MIN_INSUMO_CONVERSION = 30
_con_insumo = tabla_mes[tabla_mes["INSUMO"] >= _MIN_INSUMO_CONVERSION]
if len(_con_insumo):
    st.plotly_chart(_fig_conversion(tabla_mes, min_insumo=_MIN_INSUMO_CONVERSION), width="stretch", config={"displayModeBar": False})
    st.caption(f"Sólo asesores con al menos {_MIN_INSUMO_CONVERSION} leads recibidos en el mes (para que el % no sea ruido de muestras muy chicas). Top 15 por conversión.")
else:
    st.caption("Sin insumo (leads) suficiente este mes para calcular conversión — revisa que la hoja de Leads tenga la Cedula de estos asesores.")

