import base64
import calendar
import html
import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import _datos

# Cuartiles cruza 4 hojas (Matrículas, Inscripciones, Metas, Leads); la carga vive en _datos.py.

# ─────────────────────────────────────────────
# COLORES (mismo esquema que Matrículas / Inscripciones)
# ─────────────────────────────────────────────
COLOR_PRIMARY = "#065F46"
COLOR_ACCENT  = "#0EA5E9"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER  = "#EF4444"
_MUTED = "#94A3B8"
_INDIGO = "#818CF8"

_MES_ORDEN = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

_COLOR_CUARTIL = {"Q1": COLOR_DANGER, "Q2": COLOR_WARNING, "Q3": COLOR_ACCENT, "Q4": COLOR_SUCCESS}
_CUARTIL_NUM = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
_ORDEN_Q = ["Q1", "Q2", "Q3", "Q4"]

# Objetivo fijo de media por cuartil para MATRÍCULAS (definido por la operación, no cambia).
_PROPUESTO_MAT = {"Q1": 6.5, "Q2": 9.5, "Q3": 13.0, "Q4": 39.5}


def _tabla_umbrales(df: pd.DataFrame, col_valor: str, col_cuartil: str, propuesto_fijo: dict | None = None) -> pd.DataFrame:
    """Resumen por cuartil: FOTO (límite inferior real del grupo), REAL (media del grupo),
    PROPUESTO (fijo para matrículas; = umbral real del Q siguiente para inscripciones) y
    %CUMPLIM = REAL / PROPUESTO."""
    sub = df.dropna(subset=[col_valor, col_cuartil])
    sub = sub[sub[col_cuartil].isin(_ORDEN_Q)]
    if sub.empty:
        return pd.DataFrame(columns=["FOTO", "REAL", "PROPUESTO", "CUMPL"], index=_ORDEN_Q)
    g = sub.groupby(col_cuartil)[col_valor]
    foto = g.min().reindex(_ORDEN_Q)
    real = g.mean().reindex(_ORDEN_Q)
    if propuesto_fijo:
        prop = pd.Series(propuesto_fijo).reindex(_ORDEN_Q).astype(float)
    else:
        # umbral para "pasar" a cada Q = límite inferior del Q siguiente; Q4 = máximo observado
        prop = pd.Series({
            "Q1": foto.get("Q2"), "Q2": foto.get("Q3"), "Q3": foto.get("Q4"),
            "Q4": float(sub[col_valor].max()),
        })
    out = pd.DataFrame({"FOTO": foto, "REAL": real, "PROPUESTO": prop})
    out["CUMPL"] = (out["REAL"] / out["PROPUESTO"] * 100).where(out["PROPUESTO"] > 0, 0.0)
    return out


_UMBRAL_CSS = """
<style>
.umb-panel{position:relative;border-radius:16px;padding:11px 13px 9px;
  background:linear-gradient(160deg,rgba(255,255,255,0.06) 0%,rgba(255,255,255,0.02) 100%);
  border:1px solid rgba(255,255,255,0.09);
  box-shadow:0 12px 30px -20px rgba(0,0,0,0.7),inset 0 1px 0 rgba(255,255,255,0.06);}
.umb-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
.umb-ico{width:24px;height:24px;border-radius:7px;display:flex;align-items:center;justify-content:center;
  font-size:12px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);flex-shrink:0;}
.umb-title{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:12px;color:#fff;letter-spacing:-0.1px;}
.umb-sub{font-size:8.5px;color:rgba(255,255,255,0.38);margin-top:0;}
.umb-row{display:grid;grid-template-columns:26px 1fr 1fr 1fr 96px;gap:7px;align-items:center;
  padding:5px 8px;border-radius:9px;margin-bottom:3px;
  background:linear-gradient(160deg,rgba(255,255,255,0.045),rgba(255,255,255,0.012));
  border:1px solid rgba(255,255,255,0.06);border-left:2px solid var(--q);}
.umb-row:last-child{margin-bottom:0;}
.umb-q{font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:11px;color:var(--q);
  text-align:center;}
.umb-cell{text-align:center;line-height:1.15;}
.umb-cell .lbl{display:block;font-size:6.5px;font-weight:800;letter-spacing:0.07em;text-transform:uppercase;
  color:rgba(255,255,255,0.30);}
.umb-cell .val{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:11px;color:rgba(255,255,255,0.92);}
.umb-cell.prop .val{color:#7DD3FC;}
.umb-bar-row{display:flex;align-items:center;gap:5px;}
.umb-bar-track{flex:1;height:4px;border-radius:99px;background:rgba(255,255,255,0.10);overflow:hidden;}
.umb-bar-fill{height:100%;border-radius:99px;box-shadow:0 0 6px -1px currentColor;}
.umb-pct{font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:10px;min-width:30px;text-align:right;}
</style>
"""


def _render_tabla_umbrales(t: pd.DataFrame, titulo: str, icono: str, sub: str) -> None:
    def _n(x):
        return "—" if pd.isna(x) else f"{x:,.1f}".replace(",", ".")

    rows = []
    for q in _ORDEN_Q:
        if q not in t.index:
            continue
        r = t.loc[q]
        cq = _COLOR_CUARTIL[q]
        pct = 0.0 if pd.isna(r["CUMPL"]) else float(r["CUMPL"])
        cpct = COLOR_SUCCESS if pct >= 100 else (COLOR_WARNING if pct >= 70 else COLOR_DANGER)
        foto = "&gt; " + _n(r["FOTO"]) if q == "Q4" else _n(r["FOTO"])
        rows.append(
            f"<div class='umb-row' style='--q:{cq}'>"
            f"<div class='umb-q'>{q}</div>"
            f"<div class='umb-cell'><span class='lbl'>Foto</span><span class='val'>{foto}</span></div>"
            f"<div class='umb-cell'><span class='lbl'>Real</span><span class='val'>{_n(r['REAL'])}</span></div>"
            f"<div class='umb-cell prop'><span class='lbl'>Prop.</span><span class='val'>{_n(r['PROPUESTO'])}</span></div>"
            f"<div class='umb-bar-row'>"
            f"<div class='umb-bar-track'><div class='umb-bar-fill' style='width:{min(pct,100):.0f}%;background:{cpct}'></div></div>"
            f"<span class='umb-pct' style='color:{cpct}'>{pct:.0f}%</span>"
            f"</div></div>"
        )
    st.markdown(
        _UMBRAL_CSS
        + f"<div class='umb-panel'><div class='umb-head'><div class='umb-ico'>{icono}</div>"
        f"<div><div class='umb-title'>{titulo}</div><div class='umb-sub'>{sub}</div></div></div>"
        + "".join(rows)
        + "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# DESCARGA (idéntico a Matrículas / Inscripciones)
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _excel_bytes(df):
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
# Matrículas ya viene resuelta (8 mensuales + directorio): trae _CC, _ASESOR, _SUPERVISOR, _COORDINADOR, MES, AÑO.
_cargar_matriculas = _datos.matriculas
_cargar_metas = _datos.metas
_cargar_leads = _datos.leads


@st.cache_data(show_spinner=False)
def _cargar_inscripciones() -> pd.DataFrame:
    df = _datos.inscripciones()
    df = df[df["DNI"].notna()].copy()
    df["_CC"] = pd.to_numeric(df["CEDULA AGENT"], errors="coerce").astype("Int64")
    df["_ASESOR"] = df["NOMBRE AGENT"].fillna("Sin asignar")
    df["_SUPERVISOR"] = df["SUPERVISOR"].fillna("Sin asignar")
    df["_DIA"] = df["_FECHA_INSC"].dt.day
    return df


_COLS_CLASIFICACION = [
    "ASESOR", "SUPERVISOR", "COORDINADOR", "META_INSC", "META_MAT", "REAL_INSC", "REAL_MAT", "INSUMO",
    "CUMPL_INSC", "CUMPL_MAT", "CUARTIL", "CUARTIL_INSC",
]


def _dia_de(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


@st.cache_data(show_spinner=False)
def _tabla_clasificacion(mes_sel: str, mes_corte: str | None = None, dia_corte: int | None = None) -> pd.DataFrame:
    """Universo del mes = todos los asesores con Meta asignada ese MES/AÑO (Metas es el
    respaldo para que aparezcan aunque tengan 0 real). El cuartil se calcula sobre REAL_MAT
    de ese universo completo — un asesor en 0 matrículas es un dato de desempeño válido,
    no se excluye. Cacheado por mes: se llama muchas veces (evolución + período).

    `mes_corte`/`dia_corte`: si el mes que se está clasificando es `mes_corte`, solo se
    cuentan matrículas/inscripciones/insumo hasta el día `dia_corte` (inclusive). En
    cualquier otro mes el recorte no aplica y se cuenta el mes completo."""
    mat, insc, metas, leads = _cargar_matriculas(), _cargar_inscripciones(), _cargar_metas(), _cargar_leads()
    anios = metas.loc[metas["MES"] == mes_sel, "AÑO"].dropna()
    if not len(anios):
        return pd.DataFrame(columns=_COLS_CLASIFICACION)
    anio_sel = int(anios.mode().iat[0])

    _cut = dia_corte if (dia_corte is not None and mes_corte == mes_sel) else None

    m = metas[(metas["MES"] == mes_sel) & (metas["AÑO"] == anio_sel)]
    meta_asesor = (
        m.dropna(subset=["_CC"]).drop_duplicates("_CC").set_index("_CC")
        .rename(columns={
            "NOMBRE ASESOR": "_ASESOR_META", "SUPERVISOR": "_SUPERVISOR_META",
            "Meta inscripciones": "META_INSC", "Meta matriculas": "META_MAT",
        })
        [["_ASESOR_META", "_SUPERVISOR_META", "META_INSC", "META_MAT"]]
    )

    _mat_mes = mat[(mat["MES"] == mes_sel) & (mat["AÑO"] == anio_sel)]
    _insc_mes = insc[(insc["MES"] == mes_sel) & (insc["AÑO"] == anio_sel)]
    _leads_mes = leads[(leads["MES"] == mes_sel) & (leads["AÑO"] == anio_sel)]
    if _cut is not None:
        _mat_mes = _mat_mes[_dia_de(_mat_mes["DÍA"]) <= _cut]
        _insc_mes = _insc_mes[_dia_de(_insc_mes["_DIA"]) <= _cut]
        _leads_mes = _leads_mes[_leads_mes["_FECHA"].dt.day <= _cut]

    real_mat = (
        _mat_mes.dropna(subset=["_CC"])
        .groupby("_CC").agg(
            REAL_MAT=("_CC", "size"), _ASESOR_MAT=("_ASESOR", "first"),
            _SUPERVISOR_MAT=("_SUPERVISOR", "first"), _COORDINADOR_MAT=("_COORDINADOR", "first"),
        )
    )
    real_insc = (
        _insc_mes.dropna(subset=["_CC"])
        .groupby("_CC").agg(
            REAL_INSC=("_CC", "size"), _ASESOR_INSC=("_ASESOR", "first"),
            _SUPERVISOR_INSC=("_SUPERVISOR", "first"), _COORDINADOR_INSC=("COORDINADOR", "first"),
        )
    )
    insumo_mes = (
        _leads_mes.dropna(subset=["_CC"])
        .groupby("_CC")["_INSUMO"].sum().rename("INSUMO")
    )

    tabla = meta_asesor.join(real_mat, how="outer").join(real_insc, how="outer").join(insumo_mes, how="left")
    if not len(tabla):
        return pd.DataFrame(columns=_COLS_CLASIFICACION)

    for c in ("META_INSC", "META_MAT", "REAL_INSC", "REAL_MAT", "INSUMO"):
        tabla[c] = tabla[c].fillna(0).astype(int)

    tabla["ASESOR"] = tabla["_ASESOR_MAT"].fillna(tabla["_ASESOR_INSC"]).fillna(tabla["_ASESOR_META"]).fillna("Sin asignar")
    tabla["SUPERVISOR"] = tabla["_SUPERVISOR_MAT"].fillna(tabla["_SUPERVISOR_INSC"]).fillna(tabla["_SUPERVISOR_META"]).fillna("Sin asignar")
    tabla["COORDINADOR"] = tabla["_COORDINADOR_MAT"].fillna(tabla["_COORDINADOR_INSC"]).fillna("Sin asignar")

    # Matrículas trae el supervisor/coordinador ya resuelto contra el directorio; la
    # columna cruda de Inscripciones a veces llega más corta ("Tatiana Martinez" en vez
    # de "Tatiana Martinez Quintero"). Se consolidan las variantes de esta tabla en la
    # forma más completa — mismo criterio que usa Matrículas en _datos.py.
    tabla["SUPERVISOR"] = _datos.canonicalizar_nombres(tabla["SUPERVISOR"])
    tabla["COORDINADOR"] = _datos.canonicalizar_nombres(tabla["COORDINADOR"])

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


@st.cache_data(show_spinner=False)
def _tabla_periodo(mes_sel: str, meses_ventana: tuple, mes_corte: str | None = None, dia_corte: int | None = None) -> pd.DataFrame:
    """Igual que `_tabla_clasificacion` pero soporta mes_sel == 'Todos': SUMA
    matrículas/inscripciones/meta/insumo de cada asesor en la ventana de meses y
    recalcula cuartiles sobre ese total. El recorte por día solo afecta a `mes_corte`;
    los demás meses de la ventana se cuentan completos."""
    if mes_sel != "Todos":
        return _tabla_clasificacion(mes_sel, mes_corte, dia_corte)

    partes = [_tabla_clasificacion(m, mes_corte, dia_corte) for m in meses_ventana]
    partes = [p for p in partes if len(p)]
    if not partes:
        return pd.DataFrame(columns=_COLS_CLASIFICACION)
    allp = pd.concat(partes, ignore_index=True)
    # Cada mes ya viene canonicalizado por separado (_tabla_clasificacion), pero la forma
    # "ganadora" puede variar de un mes a otro si un mes no trae la variante completa. Se
    # vuelve a consolidar sobre el conjunto de los 6 meses, que sí suele traerla, para que
    # el "first" de abajo no herede una forma corta por casualidad del orden de los meses.
    allp["SUPERVISOR"] = _datos.canonicalizar_nombres(allp["SUPERVISOR"])
    allp["COORDINADOR"] = _datos.canonicalizar_nombres(allp["COORDINADOR"])
    t = allp.groupby("ASESOR", as_index=False).agg(
        SUPERVISOR=("SUPERVISOR", "first"), COORDINADOR=("COORDINADOR", "first"),
        META_INSC=("META_INSC", "sum"), META_MAT=("META_MAT", "sum"),
        REAL_INSC=("REAL_INSC", "sum"), REAL_MAT=("REAL_MAT", "sum"), INSUMO=("INSUMO", "sum"),
    )
    for c in ("META_INSC", "META_MAT", "REAL_INSC", "REAL_MAT", "INSUMO"):
        t[c] = t[c].round().astype(int)
    t["CUMPL_INSC"] = np.where(t["META_INSC"] > 0, t["REAL_INSC"] / t["META_INSC"] * 100,
                               np.where(t["REAL_INSC"] > 0, 100.0, 0.0))
    t["CUMPL_MAT"] = np.where(t["META_MAT"] > 0, t["REAL_MAT"] / t["META_MAT"] * 100,
                              np.where(t["REAL_MAT"] > 0, 100.0, 0.0))
    if len(t) >= 4:
        t["CUARTIL"] = pd.qcut(t["REAL_MAT"].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
        t["CUARTIL_INSC"] = pd.qcut(t["REAL_INSC"].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
    else:
        t["CUARTIL"] = t["CUARTIL_INSC"] = "Q4"
    return t[_COLS_CLASIFICACION].sort_values("REAL_MAT", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def _tabla_evolucion_reciente(meses_recientes: tuple, mes_corte: str | None = None, dia_corte: int | None = None) -> tuple[list[dict], list[str]]:
    """Una fila por asesor con Matrículas/Inscripciones/Cuartil (de cada métrica) de cada uno
    de los meses de la ventana, más un cuartil CONSOLIDADO por métrica (sobre el promedio
    mensual) y si evolucionó (comparando su primer y último cuartil de matrículas válido).
    Universo = unión de asesores clasificados en cualquiera de esos meses."""
    meses_recientes = list(meses_recientes)
    tablas_mes = {}
    for mes in meses_recientes:
        t = _tabla_clasificacion(mes, mes_corte, dia_corte)
        # Un mismo nombre puede tener dos cédulas distintas en la base (dato duplicado/reingreso);
        # sin agrupar, t.loc[asesor] devolvería 2 filas en vez de 1 y rompería el resto de la función.
        tablas_mes[mes] = t.groupby("ASESOR", as_index=True).agg(
            SUPERVISOR=("SUPERVISOR", "first"), COORDINADOR=("COORDINADOR", "first"),
            REAL_MAT=("REAL_MAT", "sum"),
            REAL_INSC=("REAL_INSC", "sum"),
            CUARTIL=("CUARTIL", "first"),
            CUARTIL_INSC=("CUARTIL_INSC", "first"),
        )

    # Igual que en _tabla_periodo: se consolidan las variantes de supervisor/coordinador
    # sobre el conjunto de TODOS los meses de la ventana (más variantes disponibles = mejor
    # forma canónica), no mes a mes — si no, cada mes podría "ganar" una forma distinta.
    if tablas_mes:
        _sup_all = pd.concat([t["SUPERVISOR"] for t in tablas_mes.values()])
        _coord_all = pd.concat([t["COORDINADOR"] for t in tablas_mes.values()])
        _sup_all = _datos.canonicalizar_nombres(_sup_all)
        _coord_all = _datos.canonicalizar_nombres(_coord_all)
        _i = 0
        for t in tablas_mes.values():
            n = len(t)
            t["SUPERVISOR"] = _sup_all.iloc[_i:_i + n].values
            t["COORDINADOR"] = _coord_all.iloc[_i:_i + n].values
            _i += n

    todos_asesores = set()
    for t in tablas_mes.values():
        todos_asesores.update(t.index)

    filas = []
    for asesor in todos_asesores:
        supervisor = "Sin asignar"
        coordinador = "Sin asignar"
        cuartiles_validos = []
        meses_data = []
        mat_total = insc_total = 0
        for mes in meses_recientes:
            t = tablas_mes[mes]
            if asesor in t.index:
                row = t.loc[asesor]
                supervisor = row["SUPERVISOR"]
                coordinador = row["COORDINADOR"]
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

        n = len(meses_recientes) or 1
        filas.append({
            "ASESOR": asesor, "SUPERVISOR": supervisor, "COORDINADOR": coordinador, "MESES": meses_data,
            "MAT_TOTAL": mat_total, "INSC_TOTAL": insc_total,
            "MAT_PROM": mat_total / n, "INSC_PROM": insc_total / n, "DELTA": delta,
        })

    # Cuartil consolidado: sobre el PROMEDIO mensual de los n_meses de TODO el universo
    # (el ranking es idéntico al de la suma; se promedia para que el número mostrado sea
    # "matrículas por mes" y calce con las tablas de umbrales).
    if len(filas) >= 4:
        mat_prom = pd.Series([f["MAT_PROM"] for f in filas])
        insc_prom = pd.Series([f["INSC_PROM"] for f in filas])
        q_mat = pd.qcut(mat_prom.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
        q_insc = pd.qcut(insc_prom.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
        for f, qm, qi in zip(filas, q_mat, q_insc):
            f["CUARTIL_MAT_CONSOLIDADO"] = qm
            f["CUARTIL_INSC_CONSOLIDADO"] = qi
    else:
        for f in filas:
            f["CUARTIL_MAT_CONSOLIDADO"] = "Q4"
            f["CUARTIL_INSC_CONSOLIDADO"] = "Q4"

    filas.sort(key=lambda f: f["MAT_TOTAL"], reverse=True)
    return filas, meses_recientes


def _racha_actual_q(fila: dict, q: str = "Q1") -> int:
    """Meses CONSECUTIVOS más recientes en que el asesor cerró en el cuartil `q`
    (cuenta hacia atrás desde el último mes con dato; se corta en el primer mes
    sin dato o en otro cuartil). `fila['MESES']` va de más antiguo a más reciente."""
    racha = 0
    for m in reversed(fila["MESES"]):
        if m is None or m["CUARTIL"] != q:
            break
        racha += 1
    return racha


# ─────────────────────────────────────────────
# TABLA HTML — Clasificación de asesores (cálculo y HTML intactos)
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
# TABLA HTML — Evolución reciente (últimos N meses; cálculo y HTML intactos)
# ─────────────────────────────────────────────
def _qcell_html(valor, cuartil: str) -> str:
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
    celda_consolidado = (
        _qcell_html(f"{fila['MAT_PROM']:.1f}", fila["CUARTIL_MAT_CONSOLIDADO"])
        + _qcell_html(f"{fila['INSC_PROM']:.1f}", fila["CUARTIL_INSC_CONSOLIDADO"])
    )
    return (
        "<tr>"
        f"<td class='sup-cell'>{fila['ASESOR']}</td>"
        f"<td>{fila['SUPERVISOR']}</td>"
        f"{celdas_meses}"
        f"{celda_consolidado}"
        f"<td>{_badge_evolucion_html(fila['DELTA'])}</td>"
        "</tr>"
    )


def _df_evolucion_export(filas: list[dict], meses_recientes: list[str]) -> pd.DataFrame:
    """Aplana `_filas_evolucion` (una fila por asesor, con lista MESES anidada) a un
    DataFrame de una fila por asesor con una columna por mes, para exportar a Excel."""
    filas_export = []
    for f in filas:
        fila = {"ASESOR": f["ASESOR"], "SUPERVISOR": f["SUPERVISOR"]}
        for mes, datos_mes in zip(meses_recientes, f["MESES"]):
            fila[f"MAT. {mes.upper()}"] = datos_mes["MAT"] if datos_mes else None
            fila[f"CUARTIL MAT. {mes.upper()}"] = datos_mes["CUARTIL"] if datos_mes else None
            fila[f"INSC. {mes.upper()}"] = datos_mes["INSC"] if datos_mes else None
            fila[f"CUARTIL INSC. {mes.upper()}"] = datos_mes["CUARTIL_INSC"] if datos_mes else None
        fila["PROMEDIO MAT."] = round(f["MAT_PROM"], 1)
        fila["CUARTIL MAT. CONSOLIDADO"] = f["CUARTIL_MAT_CONSOLIDADO"]
        fila["PROMEDIO INSC."] = round(f["INSC_PROM"], 1)
        fila["CUARTIL INSC. CONSOLIDADO"] = f["CUARTIL_INSC_CONSOLIDADO"]
        _delta = f["DELTA"]
        fila["EVOLUCIÓN"] = (
            "Sin datos" if _delta is None
            else "Subió" if _delta > 0
            else "Bajó" if _delta < 0
            else "Se mantuvo"
        )
        filas_export.append(fila)
    return pd.DataFrame(filas_export)


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
        f"<th class='grp-consolidado' colspan='2'>Promedio ({len(meses_recientes)} meses)</th>"
        "<th class='grp-total' rowspan='2'>Evolución</th></tr>"
        f"<tr>{meses_subheaders}<th class='grp-consolidado'>Mat.</th><th class='grp-consolidado'>Insc.</th></tr>"
        "</thead><tbody>"
        f"{rows_html}"
        "</tbody></table></div>"
    )
    with st.container(key="tabla_evolucion"):
        st.markdown(table_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SISTEMA VISUAL "ebi-*" (mismo lenguaje de Inscripciones / Matrículas)
# ─────────────────────────────────────────────
def _safe(value) -> str:
    return html.escape(str(value))


def _panel_title(icon: str, title: str, description: str, tag: str = "") -> None:
    badge = f"<span class='ebi-tag'>{_safe(tag)}</span>" if tag else ""
    st.markdown(
        f"<div class='ebi-head'><div class='ebi-icon'>{icon}</div>"
        f"<div class='ebi-copy'><div class='ebi-title'>{_safe(title)}</div>"
        f"<div class='ebi-sub'>{_safe(description)}</div></div>{badge}</div>",
        unsafe_allow_html=True,
    )


def _section(label: str, title: str) -> None:
    st.markdown(
        f"<div class='ebi-section'><span>{_safe(label)}</span><b>{_safe(title)}</b><i></i></div>",
        unsafe_allow_html=True,
    )


def _number_es(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _percent_es(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") + " %"


# ─────────────────────────────────────────────
# GRÁFICOS
# ─────────────────────────────────────────────
# Todas las gráficas comparten alto y márgenes para quedar alineadas a la misma altura.
_FIG_H = 330
_LAYOUT_BASE = dict(
    height=_FIG_H, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"),
    margin=dict(l=50, r=25, t=45, b=45),
)
_AXIS = dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.55)"), automargin=False)
_LEGEND = dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10, color="rgba(255,255,255,0.58)"), bgcolor="rgba(0,0,0,0)")


def _rgba_hex(hex_color: str, alpha: float) -> str:
    v = hex_color.lstrip("#")
    r, g, b = (int(v[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _render_cuartil_stack(tabla: pd.DataFrame, group_col: str, key: str) -> None:
    if not len(tabla):
        st.caption("Sin datos para esta gráfica."); return
    c1, c2 = st.columns(2)
    with c1:
        vista = st.selectbox("Ver como", ["Conteo de asesores", "% del equipo"], key=f"{key}_vista")
    with c2:
        orden = st.selectbox("Ordenar por", ["Mayor volumen", "Alfabético", "Mayor % en Q1", "Mayor % en Q4"], key=f"{key}_orden")
    grp = tabla.groupby(group_col)["CUARTIL"].value_counts().unstack(fill_value=0)
    for q in _ORDEN_Q:
        if q not in grp.columns:
            grp[q] = 0
    grp = grp[_ORDEN_Q]
    total = grp.sum(axis=1)
    pct = grp.div(total.replace(0, 1), axis=0) * 100
    if orden == "Mayor volumen":
        order_idx = total.sort_values().index
    elif orden == "Alfabético":
        order_idx = pd.Index(sorted(grp.index, reverse=True))
    elif orden == "Mayor % en Q1":
        order_idx = pct["Q1"].sort_values().index
    else:
        order_idx = pct["Q4"].sort_values().index
    grp, pct = grp.loc[order_idx], pct.loc[order_idx]
    fuente = pct if vista == "% del equipo" else grp
    fig = go.Figure()
    for q in _ORDEN_Q:
        custom = np.column_stack([grp[q], pct[q]])
        fig.add_trace(go.Bar(
            y=fuente.index, x=fuente[q], orientation="h", name=q, marker=dict(color=_COLOR_CUARTIL[q]),
            customdata=custom,
            hovertemplate=f"<b>%{{y}}</b><br>{q}: %{{customdata[0]:.0f}} asesores (%{{customdata[1]:.0f}}%)<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", height=max(280, len(grp) * 26 + 60), margin=dict(l=10, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"), legend=_LEGEND,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(size=10, family="Inter", color="rgba(255,255,255,0.55)"),
                   automargin=True, ticksuffix="%" if vista == "% del equipo" else ""),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11, family="Inter", color="rgba(255,255,255,0.75)"),
                   automargin=True),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _fig_movilidad_sankey(filas: list[dict], meses_recientes: list[str]) -> go.Figure | None:
    """Flujo de asesores entre cuartiles a lo largo de TODA la ventana de meses
    (no solo inicio→fin): una columna de nodos por mes, un enlace por cada
    transición de cuartil observada entre dos meses consecutivos."""
    n = len(meses_recientes)
    node_index: dict[tuple, int] = {}
    labels, colors, x_pos, y_pos = [], [], [], []
    for mi, mes in enumerate(meses_recientes):
        for qi, q in enumerate(_ORDEN_Q):
            node_index[(mi, q)] = len(labels)
            labels.append(f"{mes[:3]} · {q}")
            colors.append(_COLOR_CUARTIL[q])
            x_pos.append(0.001 + mi * (0.998 / max(n - 1, 1)))
            y_pos.append(0.04 + qi * 0.30)

    flows: dict[tuple, int] = {}
    for f in filas:
        meses_data = f["MESES"]
        for mi in range(n - 1):
            m1, m2 = meses_data[mi], meses_data[mi + 1]
            if m1 and m2:
                k = (node_index[(mi, m1["CUARTIL"])], node_index[(mi + 1, m2["CUARTIL"])])
                flows[k] = flows.get(k, 0) + 1
    if not flows:
        return None

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(
            label=labels, color=colors, x=x_pos, y=y_pos, pad=9, thickness=13,
            line=dict(color="rgba(255,255,255,.18)", width=.6),
            hovertemplate="%{label}: %{value} asesores<extra></extra>",
        ),
        link=dict(
            source=[s for s, _ in flows], target=[t for _, t in flows], value=list(flows.values()),
            color=[_rgba_hex(colors[s], .30) for s, _ in flows],
            hovertemplate="%{source.label} → %{target.label}<br>%{value} asesores<extra></extra>",
        ),
    ))
    fig.update_layout(
        height=460, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=10, color="rgba(255,255,255,.80)"),
        margin=dict(l=6, r=6, t=10, b=6),
    )
    return fig


def _render_movilidad(filas: list[dict], meses_recientes: list[str]) -> None:
    """Vista de flujo completo (Sankey, mes a mes) o resumen inicio→fin
    (heatmap 4x4 con clic para ver quiénes)."""
    c1, c2 = st.columns([1.3, 1])
    with c1:
        vista = st.selectbox("Vista", ["Flujo completo (Sankey)", "Inicio → Fin (matriz)"], key="cuart_mov_vista")
    with c2:
        grupos = sorted({f["SUPERVISOR"] for f in filas if f["SUPERVISOR"] != "Sin asignar"})
        sup_local = st.selectbox("Supervisor", ["Todos"] + grupos, key="cuart_mov_sup")
    filas_f = filas if sup_local == "Todos" else [f for f in filas if f["SUPERVISOR"] == sup_local]
    if not filas_f:
        st.caption("Sin datos para esta selección."); return

    if vista.startswith("Flujo"):
        if len(meses_recientes) < 2:
            st.caption("Se necesitan al menos 2 meses para ver el flujo."); return
        fig = _fig_movilidad_sankey(filas_f, meses_recientes)
        if fig is None:
            st.caption("Sin trayectorias suficientes para dibujar el flujo."); return
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption("Cada columna es un mes; el grosor del enlace es la cantidad de asesores que hicieron esa transición de cuartil.")
        return

    idx = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3}
    M = [[0] * 4 for _ in range(4)]
    quien: dict[tuple, list[str]] = {}
    for f in filas_f:
        qs = [m["CUARTIL"] for m in f["MESES"] if m]
        if len(qs) >= 2:
            i, j = idx[qs[0]], idx[qs[-1]]
            M[i][j] += 1
            quien.setdefault((i, j), []).append(f["ASESOR"])
    fig = go.Figure(go.Heatmap(
        z=M, x=["Q1", "Q2", "Q3", "Q4"], y=["Q1", "Q2", "Q3", "Q4"],
        text=M, texttemplate="%{text}", textfont=dict(size=14, color="white"),
        colorscale=[[0, "rgba(129,140,248,0.05)"], [1, "#818CF8"]], showscale=False,
        xgap=3, ygap=3,
        hovertemplate="De %{y} a %{x}: %{z} asesores<extra></extra>",
    ))
    fig.update_layout(
        **{**_LAYOUT_BASE, "height": 420, "margin": dict(l=70, r=25, t=20, b=55)},
        xaxis=dict(title="Cuartil al final", tickfont=dict(size=12, color="rgba(255,255,255,0.75)")),
        yaxis=dict(title="Cuartil al inicio", autorange="reversed", tickfont=dict(size=12, color="rgba(255,255,255,0.75)")),
    )
    event = st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="cuart_movilidad", on_select="rerun", selection_mode="points")
    try:
        point = event.selection.points[0]
        qi, qf = point["y"], point["x"]
        nombres = sorted(quien.get((idx[qi], idx[qf]), []))
        if nombres:
            st.markdown(f"**{qi} → {qf}** ({len(nombres)} asesores): " + ", ".join(_safe(n) for n in nombres))
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        pass


def _render_embudo_insumo(tabla: pd.DataFrame) -> None:
    """Embudo Insumo (leads) → Inscripción → Matrícula, agrupable por cuartil,
    supervisor o coordinador."""
    if not len(tabla):
        st.caption("Sin datos."); return
    c1, c2 = st.columns(2)
    with c1:
        agrupar = st.selectbox("Agrupar por", ["Cuartil", "Supervisor", "Coordinador"], key="cuart_emb_group")
    with c2:
        vista = st.selectbox("Vista", ["Promedio por asesor", "Total del grupo"], key="cuart_emb_vista")
    col = {"Cuartil": "CUARTIL", "Supervisor": "SUPERVISOR", "Coordinador": "COORDINADOR"}[agrupar]
    agg = "mean" if vista == "Promedio por asesor" else "sum"
    g = tabla.groupby(col)[["INSUMO", "REAL_INSC", "REAL_MAT"]].agg(agg)
    if col == "CUARTIL":
        g = g.reindex(_ORDEN_Q).fillna(0)
    else:
        g = g[g.index != "Sin asignar"].sort_values("REAL_MAT", ascending=False).head(15)
    fig = go.Figure()
    fig.add_bar(x=g.index, y=g["INSUMO"], name="Insumo (leads)", marker_color=_INDIGO,
                text=[f"{v:.1f}" for v in g["INSUMO"]], textposition="outside")
    fig.add_bar(x=g.index, y=g["REAL_INSC"], name="Inscripciones", marker_color=COLOR_ACCENT,
                text=[f"{v:.1f}" for v in g["REAL_INSC"]], textposition="outside")
    fig.add_bar(x=g.index, y=g["REAL_MAT"], name="Matrículas", marker_color=COLOR_SUCCESS,
                text=[f"{v:.1f}" for v in g["REAL_MAT"]], textposition="outside")
    fig.update_layout(
        barmode="group", **_LAYOUT_BASE, legend=_LEGEND,
        xaxis=dict(tickfont=dict(size=10, color="rgba(255,255,255,0.75)")), yaxis=_AXIS,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _render_scatter_insc_mat(tabla: pd.DataFrame) -> None:
    """Inscripciones vs Matrículas por asesor, con color y tamaño configurables."""
    if not len(tabla):
        st.caption("Sin datos."); return
    c1, c2 = st.columns(2)
    with c1:
        color_por = st.selectbox("Color por", ["Cuartil", "Supervisor", "Coordinador"], key="cuart_sc_color")
    with c2:
        tam_por = st.selectbox("Tamaño del punto", ["Igual", "Insumo", "Cumplimiento Mat."], key="cuart_sc_size")

    if tam_por == "Insumo":
        tam_serie = tabla["INSUMO"].astype(float)
    elif tam_por == "Cumplimiento Mat.":
        tam_serie = tabla["CUMPL_MAT"].astype(float)
    else:
        tam_serie = None
    sizeref = (2.0 * max(float(tam_serie.max()), 1.0) / (20.0 ** 2)) if tam_serie is not None else None

    color_col = {"Cuartil": "CUARTIL", "Supervisor": "SUPERVISOR", "Coordinador": "COORDINADOR"}[color_por]
    if color_col == "CUARTIL":
        grupos, color_map = _ORDEN_Q, _COLOR_CUARTIL
    else:
        grupos = sorted(x for x in tabla[color_col].unique() if x != "Sin asignar")
        palette = [COLOR_ACCENT, COLOR_SUCCESS, _INDIGO, COLOR_WARNING, COLOR_DANGER, "#2DD4BF", "#F472B6", "#FB923C"]
        color_map = {g: palette[i % len(palette)] for i, g in enumerate(grupos)}

    fig = go.Figure()
    for g in grupos:
        d = tabla[tabla[color_col] == g]
        if not len(d):
            continue
        marker = dict(color=color_map[g], line=dict(color="rgba(8,6,15,0.5)", width=1))
        if tam_serie is not None:
            marker.update(size=tam_serie.loc[d.index], sizemode="area", sizeref=sizeref, sizemin=4)
        else:
            marker["size"] = 8
        fig.add_scatter(
            x=d["REAL_INSC"], y=d["REAL_MAT"], mode="markers", name=str(g), marker=marker,
            text=d["ASESOR"], hovertemplate="<b>%{text}</b><br>Insc: %{x}<br>Mat: %{y}<extra></extra>",
        )
    x = tabla["REAL_INSC"].to_numpy(dtype=float)
    y = tabla["REAL_MAT"].to_numpy(dtype=float)
    if len(x) >= 2 and np.ptp(x) > 0:
        b, a = np.polyfit(x, y, 1)
        x_line = np.array([x.min(), x.max()])
        fig.add_scatter(
            x=x_line, y=b * x_line + a, mode="lines", name="Tendencia",
            line=dict(color="rgba(255,255,255,.55)", width=2, dash="dash"), hoverinfo="skip",
        )
    fig.update_layout(
        **_LAYOUT_BASE, legend=_LEGEND,
        xaxis=dict(title="Inscripciones", **_AXIS), yaxis=dict(title="Matrículas", **_AXIS),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ─────────────────────────────────────────────
# PERFIL DE DESEMPEÑO (radar) — nuevo
# ─────────────────────────────────────────────
def _perfil_asesor(tabla: pd.DataFrame, filas_evolucion: list[dict], asesor: str) -> dict | None:
    row = tabla[tabla["ASESOR"] == asesor]
    if row.empty:
        return None
    row = row.iloc[0]
    fila_evo = next((f for f in filas_evolucion if f["ASESOR"] == asesor), None)
    mats_mensuales = [m["MAT"] for m in (fila_evo["MESES"] if fila_evo else []) if m]
    media = float(np.mean(mats_mensuales)) if mats_mensuales else 0.0
    desv = float(np.std(mats_mensuales)) if len(mats_mensuales) > 1 else 0.0
    consistencia = 100 / (1 + (desv / media if media else 9))
    conversion = (row["REAL_MAT"] / row["REAL_INSC"] * 100) if row["REAL_INSC"] else 0.0
    return {
        "Cumplimiento": min(float(row["CUMPL_MAT"]), 150.0),
        "Volumen": float(row["REAL_MAT"]),
        "Conversion": conversion,
        "Consistencia": consistencia,
        "Insumo": float(row["INSUMO"]),
    }


def _render_perfil(tabla: pd.DataFrame, filas_evolucion: list[dict]) -> None:
    _panel_title("◉", "Perfil de Desempeño", "Cinco dimensiones normalizadas para comparar asesores, no solo volumen.", "0–100")
    asesores = sorted(tabla["ASESOR"].unique().tolist())
    if not asesores:
        st.caption("Sin asesores para comparar."); return
    default = tabla.sort_values("REAL_MAT", ascending=False)["ASESOR"].head(2).tolist()
    seleccionados = st.multiselect(
        "Comparar asesores (máximo 3)", asesores, default=default, max_selections=3, key="cuart_radar_asesores",
    )
    if not seleccionados:
        st.info("Selecciona uno o varios asesores para comparar su perfil."); return
    perfiles = {a: _perfil_asesor(tabla, filas_evolucion, a) for a in seleccionados}
    perfiles = {a: p for a, p in perfiles.items() if p}
    if not perfiles:
        st.info("Sin datos suficientes."); return
    max_vol = max(p["Volumen"] for p in perfiles.values()) or 1.0
    max_insumo = max(p["Insumo"] for p in perfiles.values()) or 1.0
    axes = ["Cumplimiento", "Volumen", "Conversión", "Consistencia", "Insumo"]
    defs = {
        "Cumplimiento": "% de meta de matrículas alcanzada",
        "Volumen": "Matrículas relativo al mejor del grupo comparado",
        "Conversión": "Matrículas / inscripciones del mes",
        "Consistencia": "100 / (1 + coeficiente de variación mensual)",
        "Insumo": "Leads utilizados, relativo al mejor del grupo comparado",
    }
    palette = [COLOR_ACCENT, COLOR_SUCCESS, _INDIGO]
    fig = go.Figure()
    for i, (asesor, p) in enumerate(perfiles.items()):
        vals = [
            min(p["Cumplimiento"], 100), p["Volumen"] / max_vol * 100, min(p["Conversion"], 100),
            p["Consistencia"], p["Insumo"] / max_insumo * 100,
        ]
        vals += vals[:1]
        theta = axes + axes[:1]
        fig.add_scatterpolar(
            r=vals, theta=theta, fill="toself", name=asesor,
            line=dict(color=palette[i % len(palette)], width=2),
            fillcolor="rgba(56,189,248,.08)",
            customdata=[defs[a] for a in theta],
            hovertemplate="%{theta}: %{r:.1f}<br>%{customdata}<extra>%{fullData.name}</extra>",
        )
    fig.update_layout(
        height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="rgba(255,255,255,0.72)"), legend=_LEGEND,
        polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,.10)", tickfont=dict(size=9)),
                   angularaxis=dict(gridcolor="rgba(255,255,255,.08)")),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ─────────────────────────────────────────────
# RIESGO DE CUARTIL (proyección Monte Carlo) — nuevo
# ─────────────────────────────────────────────
def _historial_diario_mat(asesor: str, mes: str, anio: int) -> pd.Series:
    """Serie diaria (índice 1..N) de matrículas de UN asesor en un mes/año dado."""
    mat = _cargar_matriculas()
    d = mat[(mat["_ASESOR"] == asesor) & (mat["MES"] == mes) & (mat["AÑO"] == anio)]
    ultimo_dia = calendar.monthrange(anio, _MES_ORDEN.index(mes) + 1)[1]
    dias = pd.to_numeric(d["DÍA"], errors="coerce").dropna().astype(int)
    return dias.value_counts().reindex(range(1, ultimo_dia + 1), fill_value=0).sort_index()


def _proyeccion_cuartil(asesor: str, mes: str, anio: int, dia_corte: int | None, umbral_mat: pd.DataFrame, seed: int = 42) -> dict:
    """Bootstrap simple sobre el ritmo diario observado del asesor (a nivel de
    Cuartiles se trabaja por mes, sin el calendario de días hábiles que sí usan
    Inscripciones/Matrículas) para estimar en qué cuartil cerraría, comparando
    contra los umbrales REALES (FOTO) de `umbral_mat`."""
    serie = _historial_diario_mat(asesor, mes, anio)
    ultimo_dia = len(serie)
    corte = min(dia_corte, ultimo_dia) if dia_corte else ultimo_dia
    observado = serie.loc[:corte] if corte else serie
    restante = ultimo_dia - corte
    actual = int(observado.sum())
    if restante <= 0 or observado.empty or observado.sum() == 0:
        outcomes = np.full(2000, float(actual))
    else:
        rng = np.random.default_rng(seed)
        pool = observado.to_numpy()
        outcomes = actual + rng.choice(pool, size=(2000, restante), replace=True).sum(axis=1)

    bordes = {q: umbral_mat.loc[q, "FOTO"] for q in _ORDEN_Q if q in umbral_mat.index and pd.notna(umbral_mat.loc[q, "FOTO"])}

    def _cuartil_de(v: float) -> str:
        if "Q4" in bordes and v >= bordes["Q4"]:
            return "Q4"
        if "Q3" in bordes and v >= bordes["Q3"]:
            return "Q3"
        if "Q2" in bordes and v >= bordes["Q2"]:
            return "Q2"
        return "Q1"

    cuartiles_sim = pd.Series([_cuartil_de(v) for v in outcomes])
    dist = cuartiles_sim.value_counts(normalize=True).reindex(_ORDEN_Q, fill_value=0.0) * 100
    p10, p50, p90 = np.percentile(outcomes, [10, 50, 90])
    return {
        "actual": actual, "p10": float(p10), "p50": float(p50), "p90": float(p90),
        "dist": dist, "restante": restante, "cuartil_p50": _cuartil_de(p50),
    }


def _render_riesgo_cuartil(tabla: pd.DataFrame, mes_corte: str | None, dia_corte: int | None) -> None:
    _panel_title("◎", "Riesgo de Cuartil", "Simulación del cierre de mes (ritmo reciente) contra los umbrales reales del mes de corte.", "PREDICTIVO")
    if not mes_corte:
        st.info("Selecciona un mes de corte en el sidebar para proyectar."); return
    tabla_corte = _tabla_clasificacion(mes_corte)
    if tabla_corte.empty:
        st.info("Sin datos para proyectar este mes."); return
    umbral_corte = _tabla_umbrales(tabla_corte, "REAL_MAT", "CUARTIL", _PROPUESTO_MAT)
    metas_full = _cargar_metas()
    anios = metas_full.loc[metas_full["MES"] == mes_corte, "AÑO"].dropna()
    if not len(anios):
        st.info("Sin datos para proyectar este mes."); return
    anio_sel = int(anios.mode().iat[0])
    asesores = sorted(tabla["ASESOR"].unique().tolist())
    if not asesores:
        st.info("Sin asesores para proyectar."); return
    asesor = st.selectbox("Asesor", asesores, key="cuart_riesgo_asesor")
    stats = _proyeccion_cuartil(asesor, mes_corte, anio_sel, dia_corte, umbral_corte)
    cuartil_actual_s = tabla.loc[tabla["ASESOR"] == asesor, "CUARTIL"]
    cuartil_actual = cuartil_actual_s.iloc[0] if len(cuartil_actual_s) else "—"
    color_actual = _COLOR_CUARTIL.get(cuartil_actual, _MUTED)
    color_p50 = _COLOR_CUARTIL.get(stats["cuartil_p50"], _MUTED)
    st.markdown(
        f"<div class='ebi-forecast'>"
        f"<span>CUARTIL ACTUAL<b style='color:{color_actual}'>{cuartil_actual}</b></span>"
        f"<span>MATRÍCULAS A LA FECHA<b>{_number_es(stats['actual'])}</b></span>"
        f"<span>PROYECCIÓN P50<b>{_number_es(stats['p50'])}</b></span>"
        f"<span>RANGO P10–P90<b>{_number_es(stats['p10'])} – {_number_es(stats['p90'])}</b></span>"
        f"<span>CUARTIL PROYECTADO<b style='color:{color_p50}'>{stats['cuartil_p50']}</b></span>"
        f"</div>", unsafe_allow_html=True,
    )
    fig = go.Figure(go.Bar(
        x=_ORDEN_Q, y=[float(stats["dist"][q]) for q in _ORDEN_Q],
        marker_color=[_COLOR_CUARTIL[q] for q in _ORDEN_Q],
        text=[f"{stats['dist'][q]:.0f}%" for q in _ORDEN_Q], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(**{**_LAYOUT_BASE, "height": 280}, xaxis=_AXIS, yaxis={**_AXIS, "title": "Probabilidad (%)", "range": [0, 108]})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ─────────────────────────────────────────────
# ALERTAS DE RIESGO (racha en Q1) — nuevo, reemplaza Top10/Últimos10
# ─────────────────────────────────────────────
def _render_alertas_riesgo(filas: list[dict], meses_recientes: list[str]) -> None:
    riesgo = sorted(
        (f for f in filas if _racha_actual_q(f, "Q1") >= 2),
        key=lambda f: (_racha_actual_q(f, "Q1"), -f["MAT_PROM"]), reverse=True,
    )
    _panel_title("⚠", "Alertas de Riesgo", f"Asesores con 2 o más meses seguidos en Q1, de los últimos {len(meses_recientes)} meses.", f"{len(riesgo)} EN RIESGO")
    if not riesgo:
        st.success("Nadie lleva 2 o más meses seguidos en Q1."); return
    cards = []
    for f in riesgo:
        racha = _racha_actual_q(f, "Q1")
        cards.append(
            "<article class='ebi-incident critical'><div class='ebi-inc-dot'>●</div>"
            f"<div class='ebi-inc-body'><div class='ebi-inc-name'>{_safe(f['ASESOR'])}</div>"
            f"<div class='ebi-inc-sup'>{_safe(f['SUPERVISOR'])}</div>"
            f"<div class='ebi-inc-main'><strong>{racha} meses seguidos en Q1</strong>"
            f"<span>Promedio: {f['MAT_PROM']:.1f} matrículas/mes</span></div>"
            f"<div class='ebi-inc-foot'><span>Últimos {len(meses_recientes)} meses: <b>{int(f['MAT_TOTAL'])} matrículas</b></span></div></div>"
            f"<div class='ebi-inc-badge'>{racha} MESES</div></article>"
        )
    st.markdown("<div class='ebi-inc-scroll'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def _render_overview_kpis(tabla_mes: pd.DataFrame, filas_evolucion: list[dict], mes_lbl: str) -> None:
    total = len(tabla_mes)
    n_q1 = int((tabla_mes["CUARTIL"] == "Q1").sum()) if total else 0
    n_q4 = int((tabla_mes["CUARTIL"] == "Q4").sum()) if total else 0
    cumpl = float(tabla_mes["CUMPL_MAT"].mean()) if total else 0.0
    insumo_total = int(tabla_mes["INSUMO"].sum()) if total else 0
    en_riesgo = sum(1 for f in filas_evolucion if _racha_actual_q(f, "Q1") >= 2)
    color_cumpl = COLOR_SUCCESS if cumpl >= 100 else (COLOR_WARNING if cumpl >= 70 else COLOR_DANGER)
    cards = [
        ("👥", "Total asesores", _number_es(total), f"cuartilizados · {mes_lbl}", COLOR_ACCENT, ""),
        ("⚠️", "Asesores en Q1", _number_es(n_q1), "25% de menor volumen", COLOR_DANGER, ""),
        ("🏆", "Asesores en Q4", _number_es(n_q4), "25% de mayor volumen", COLOR_SUCCESS, ""),
        ("🎯", "Cumplimiento promedio", _percent_es(cumpl), "meta de matrículas", color_cumpl,
         f"<div class='ebi-overview-track'><i style='width:{min(max(cumpl, 0), 100):.1f}%'></i></div>"),
        ("📥", "Insumo total", _number_es(insumo_total), "leads asignados · " + mes_lbl, _INDIGO, ""),
        ("🚨", "En riesgo", _number_es(en_riesgo), "2+ meses seguidos en Q1", COLOR_DANGER, ""),
    ]
    html_cards = "".join(
        f"<article class='ebi-overview-card' style='--accent:{color}'>"
        f"<div class='ebi-overview-icon'>{icon}</div>"
        f"<strong>{value}</strong><small>{label}</small>"
        f"<span class='ebi-overview-detail'>{detail}</span>"
        f"{extra}</article>"
        for icon, label, value, detail, color, extra in cards
    )
    st.markdown(f"<div class='ebi-overview'>{html_cards}</div>", unsafe_allow_html=True)


def _css() -> None:
    st.markdown("""
    <style>
    .ebi-top{position:relative;overflow:hidden;margin:0 0 10px;padding:19px 22px;border:1px solid rgba(56,189,248,.16);border-radius:16px;background:linear-gradient(110deg,rgba(56,189,248,.075),rgba(16,185,129,.035) 55%,rgba(129,140,248,.045));display:flex;align-items:center;justify-content:space-between;gap:24px;box-shadow:inset 0 1px 0 rgba(255,255,255,.035)}
    .ebi-top::before{content:'';position:absolute;inset:0 auto 0 0;width:3px;background:linear-gradient(180deg,#38BDF8,#34D399)}.ebi-top::after{content:'';position:absolute;width:260px;height:160px;right:-90px;top:-105px;border-radius:50%;background:radial-gradient(circle,rgba(56,189,248,.11),transparent 70%);pointer-events:none}.ebi-top-copy{position:relative;z-index:1;min-width:0}.ebi-top-context{display:flex;align-items:center;gap:7px;margin-bottom:5px;font-size:8px;font-weight:850;letter-spacing:.18em;color:#7DD3FC}.ebi-top-context i{display:block;width:18px;height:1px;background:#38BDF8}.ebi-top h1{font-family:'Space Grotesk',sans-serif!important;font-size:26px!important;line-height:1.08!important;color:white;margin:0!important}.ebi-top p{font-size:10px;color:rgba(255,255,255,.43);margin:6px 0 0}.ebi-period{position:relative;z-index:1;display:flex;flex-direction:column;align-items:flex-end;gap:3px;flex:0 0 auto;padding-left:22px;border-left:1px solid rgba(255,255,255,.09)}.ebi-period span{font-size:7px;font-weight:800;letter-spacing:.15em;color:rgba(255,255,255,.35)}.ebi-period b{font-family:'Space Grotesk',sans-serif;font-size:11px;letter-spacing:.04em;color:#7DD3FC;white-space:nowrap}
    div.st-key-cuart_module_nav{margin:0 0 8px;padding:5px;border:1px solid rgba(255,255,255,.08);border-radius:14px;background:rgba(255,255,255,.03)}div.st-key-cuart_module_nav div[data-testid='stHorizontalBlock']{gap:6px}div.st-key-cuart_module_nav button{min-height:40px!important;border:1px solid transparent!important;border-radius:10px!important;background:transparent!important;color:rgba(255,255,255,.55)!important;box-shadow:none!important;font-size:11px!important;font-weight:650!important;transition:background .16s,color .16s,border-color .16s!important}div.st-key-cuart_module_nav button:hover{color:white!important;background:rgba(255,255,255,.045)!important;border-color:rgba(255,255,255,.08)!important}div.st-key-cuart_module_nav button[kind='primary']{color:#7DD3FC!important;background:color-mix(in srgb,#38BDF8 14%,transparent)!important;border-color:color-mix(in srgb,#38BDF8 30%,transparent)!important;box-shadow:none!important}
    .ebi-overview{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:11px;margin:14px 0 6px}.ebi-overview-card{position:relative;overflow:hidden;min-width:0;text-align:center;padding:18px 10px 15px;border-radius:16px;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.08)}.ebi-overview-icon{width:36px;height:36px;margin:0 auto 11px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:15px;color:var(--accent);background:linear-gradient(150deg,color-mix(in srgb,var(--accent) 24%,transparent),color-mix(in srgb,var(--accent) 6%,transparent));border:1px solid color-mix(in srgb,var(--accent) 35%,transparent)}.ebi-overview-card>strong{display:block;font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:700;line-height:1;color:#fff}.ebi-overview-card>small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:rgba(255,255,255,.42);font-size:8px;letter-spacing:.06em;text-transform:uppercase;margin-top:7px}.ebi-overview-detail{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:rgba(255,255,255,.28);font-size:7.5px;margin-top:3px}.ebi-overview-track{height:3px;margin-top:9px;border-radius:99px;background:rgba(255,255,255,.08);overflow:hidden}.ebi-overview-track i{display:block;height:100%;border-radius:inherit;background:var(--accent)}
    .ebi-section{display:flex;align-items:center;gap:10px;margin:22px 0 9px}.ebi-section span{font-size:9px;font-weight:800;letter-spacing:.16em;color:#38BDF8}.ebi-section b{font-family:'Space Grotesk',sans-serif;font-size:15px;color:white}.ebi-section i{height:1px;flex:1;background:linear-gradient(90deg,rgba(255,255,255,.14),transparent)}
    .ebi-head{display:flex;align-items:center;gap:11px;margin:10px 0 5px;padding:10px 12px;border-left:2px solid #38BDF8;background:linear-gradient(90deg,rgba(56,189,248,.07),transparent);border-radius:0 12px 12px 0}.ebi-icon{width:31px;height:31px;display:flex;align-items:center;justify-content:center;border-radius:9px;background:rgba(255,255,255,.07)}.ebi-copy{flex:1}.ebi-title{font-family:'Space Grotesk',sans-serif;font-size:14px;font-weight:700;color:#fff}.ebi-sub{font-size:10px;color:rgba(255,255,255,.43);margin-top:2px}.ebi-tag{font-size:8px;font-weight:800;letter-spacing:.10em;color:#7DD3FC;border:1px solid rgba(56,189,248,.24);border-radius:99px;padding:4px 8px}
    .ebi-kpis,.ebi-forecast{display:flex;gap:10px;margin:8px 0}.ebi-kpis span,.ebi-forecast span{flex:1;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:8px 12px;font-size:9px;letter-spacing:.08em;color:rgba(255,255,255,.45)}.ebi-kpis b,.ebi-forecast b{font-family:'Space Grotesk',sans-serif;font-size:17px;margin-right:7px;color:white}.ebi-forecast span{display:flex;flex-direction:column;gap:4px}.ebi-forecast b{font-size:20px;margin:0}
    .ebi-inc-scroll{max-height:560px;overflow-y:auto;padding:2px 6px 2px 1px;scrollbar-width:thin;scrollbar-color:rgba(148,163,184,.35) transparent}.ebi-incident{position:relative;display:flex;gap:10px;margin:0 0 9px;padding:13px 12px;border-radius:12px;background:linear-gradient(120deg,rgba(255,255,255,.045),rgba(255,255,255,.018));border:1px solid rgba(255,255,255,.07);border-left:3px solid var(--incident);box-shadow:0 8px 22px -18px rgba(0,0,0,.9)}.ebi-incident.warning{--incident:#F59E0B}.ebi-incident.critical{--incident:#F43F5E}.ebi-inc-dot{color:var(--incident);font-size:10px;padding-top:3px}.ebi-inc-body{min-width:0;flex:1}.ebi-inc-name{font-size:12px;font-weight:750;color:rgba(255,255,255,.94);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ebi-inc-sup{font-size:9px;color:rgba(255,255,255,.40);margin:2px 0 9px}.ebi-inc-main{display:flex;flex-direction:column;gap:2px}.ebi-inc-main strong{font-family:'Space Grotesk',sans-serif;font-size:13px;color:white}.ebi-inc-main span{font-size:9px;color:rgba(255,255,255,.52)}.ebi-inc-foot{display:flex;gap:12px;flex-wrap:wrap;margin-top:9px;padding-top:7px;border-top:1px solid rgba(255,255,255,.06);font-size:8px;color:rgba(255,255,255,.38)}.ebi-inc-foot b{color:rgba(255,255,255,.70)}.ebi-inc-badge{align-self:flex-start;font-size:7px;font-weight:850;letter-spacing:.08em;color:var(--incident);background:color-mix(in srgb,var(--incident) 10%,transparent);border:1px solid color-mix(in srgb,var(--incident) 28%,transparent);border-radius:99px;padding:3px 6px;white-space:nowrap}
    @media(max-width:1100px){.ebi-overview{grid-template-columns:repeat(3,minmax(0,1fr))}.ebi-inc-scroll{max-height:500px}.ebi-forecast{flex-wrap:wrap}.ebi-forecast span{min-width:42%}}
    @media(max-width:720px){.ebi-top{align-items:flex-start;flex-direction:column;gap:13px}.ebi-period{align-items:flex-start;padding:0;border-left:0}.ebi-overview{grid-template-columns:repeat(2,minmax(0,1fr))}}
    div[data-testid='stVerticalBlockBorderWrapper']{border-color:rgba(255,255,255,.08)!important;background:rgba(255,255,255,.018)!important;border-radius:16px!important}
    </style>
    """, unsafe_allow_html=True)


def render(
    tabla_mes: pd.DataFrame, tabla_vista: pd.DataFrame, filas_evolucion: list[dict], meses_evolucion: list[str],
    umbral_mat: pd.DataFrame, umbral_insc: pd.DataFrame, umbral_lbl: str,
    mes_sel: str, mes_corte: str | None, dia_corte: int | None, mes_lbl: str, periodo_lbl: str,
) -> None:
    _css()
    st.markdown(
        f"<div class='ebi-top'><div class='ebi-top-copy'>"
        f"<div class='ebi-top-context'><i></i>CUARTILES</div>"
        f"<h1>Centro de Operaciones</h1>"
        f"<p>Clasificacion, calibracion y riesgo de cuartil por asesor</p></div>"
        f"<div class='ebi-period'><span>MES</span><b>{_safe(mes_sel or '—')}</b></div></div>",
        unsafe_allow_html=True,
    )
    home_pg = st.Page("home.py", title="Inicio", icon="🏠", default=True)
    insc_pg = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
    mat_pg = st.Page("pages/2_Matriculas.py", title="Matriculas", icon="🎓")
    rt_pg = st.Page("pages/4_Contactabilidad.py", title="Real time", icon="📞")
    with st.container(key="cuart_module_nav"):
        n1, n2, n3, n4, n5 = st.columns(5)
        with n1:
            if st.button("⌂  Inicio", key="cuart_nav_home", width="stretch"): st.switch_page(home_pg)
        with n2:
            if st.button("▤  Inscripciones", key="cuart_nav_ins", width="stretch"): st.switch_page(insc_pg)
        with n3:
            if st.button("◆  Matriculas", key="cuart_nav_mat", width="stretch"): st.switch_page(mat_pg)
        with n4: st.button("◇  Cuartiles", key="cuart_nav_q", width="stretch", type="primary")
        with n5:
            if st.button("●  Real time", key="cuart_nav_rt", width="stretch"): st.switch_page(rt_pg)

    _render_overview_kpis(tabla_mes, filas_evolucion, mes_lbl)

    _section("A", "CALIBRACION")
    with st.container(border=True):
        _panel_title("📐", "Umbrales de Cuartil", f"Cortes reales por cuartil frente al objetivo propuesto — {umbral_lbl}.", "CALIBRACION")
        c1, c2 = st.columns(2)
        with c1: _render_tabla_umbrales(umbral_mat, "Matrículas", "🎓", "Propuesto fijo · Q1 6,5 · Q2 9,5 · Q3 13 · Q4 39,5")
        with c2: _render_tabla_umbrales(umbral_insc, "Inscripciones", "📝", "Propuesto = umbral real del cuartil siguiente")

    _section("B", "EVOLUCION")
    with st.container(border=True):
        _panel_title("📈", "Evolución Reciente", f"Matrículas e inscripciones por asesor en {', '.join(meses_evolucion) if meses_evolucion else 'los últimos meses'}.", f"{len(filas_evolucion)} ASESORES")
        if filas_evolucion:
            _render_tabla_evolucion(filas_evolucion, meses_evolucion)
            _export_evo = _df_evolucion_export(filas_evolucion, meses_evolucion)
            _b64_evo = base64.b64encode(_excel_bytes(_export_evo)).decode()
            st.markdown(
                f'<div style="text-align:right;margin-top:-6px;margin-bottom:2px">'
                f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{_b64_evo}" '
                f'download="evolucion_reciente.xlsx" '
                f'style="font-size:0.72rem;color:rgba(255,255,255,0.35);text-decoration:none;letter-spacing:0.03em">'
                f'↓ Exportar Excel</a></div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Sin histórico suficiente para mostrar la evolución.")
    with st.container(border=True):
        _panel_title("🔀", "Movilidad de Cuartiles", "Flujo de asesores entre cuartiles mes a mes, o resumen inicio→fin.", "TRAYECTORIA")
        if filas_evolucion:
            _render_movilidad(filas_evolucion, meses_evolucion)
        else:
            st.caption("Sin histórico suficiente.")

    _section("C", "DISTRIBUCION")
    with st.container(border=True):
        _panel_title("🧭", "Cuartil de Matrículas por Supervisor", f"Asesores de cada supervisor por cuartil — {periodo_lbl}.", "DISTRIBUCION")
        _render_cuartil_stack(tabla_vista, "SUPERVISOR", "cuart_stack_sup")
    with st.container(border=True):
        _panel_title("🧭", "Cuartil de Matrículas por Coordinador", f"Asesores de cada coordinador por cuartil — {periodo_lbl}.", "DISTRIBUCION")
        _render_cuartil_stack(tabla_vista, "COORDINADOR", "cuart_stack_coord")

    _section("D", "DIAGNOSTICO")
    d1, d2 = st.columns(2)
    with d1:
        with st.container(border=True):
            _panel_title("📊", "Insumo → Inscripción → Matrícula", "Embudo de 3 etapas, agrupable por cuartil, supervisor o coordinador.", "EMBUDO")
            _render_embudo_insumo(tabla_vista)
    with d2:
        with st.container(border=True):
            _panel_title("✨", "Inscripciones vs Matrículas", "Cada punto es un asesor · color y tamaño configurables · línea = tendencia.", "RELACION")
            _render_scatter_insc_mat(tabla_vista)
    with st.container(border=True):
        if len(tabla_vista): _render_perfil(tabla_vista, filas_evolucion)
        else: _panel_title("◉", "Perfil de Desempeño", "Cinco dimensiones normalizadas para comparar asesores.", "0–100"); st.caption("Sin datos.")
    with st.container(border=True):
        _render_riesgo_cuartil(tabla_vista, mes_corte, dia_corte)
    with st.container(border=True):
        _render_alertas_riesgo(filas_evolucion, meses_evolucion)

    _section("E", "CONTROL")
    with st.container(border=True):
        _panel_title("🏆", "Clasificación de Asesores", "Meta y real de inscripciones y matrículas por asesor, con su cuartil de desempeño.", f"{len(tabla_vista)} ASESORES")
        if len(tabla_vista):
            _render_tabla_clasificacion(tabla_vista)
            _export = tabla_vista.rename(columns={
                "ASESOR": "ASESOR", "SUPERVISOR": "SUPERVISOR", "COORDINADOR": "COORDINADOR",
                "META_INSC": "META INSCRIPCIONES", "META_MAT": "META MATRICULAS",
                "REAL_INSC": "INSCRIPCIONES", "REAL_MAT": "MATRICULAS", "INSUMO": "INSUMO (LEADS)",
                "CUMPL_INSC": "CUMPLIMIENTO INSCRIPCIONES %", "CUMPL_MAT": "CUMPLIMIENTO MATRICULAS %",
                "CUARTIL": "CUARTIL",
            })
            _b64 = base64.b64encode(_excel_bytes(_export)).decode()
            st.markdown(
                f'<div style="text-align:right;margin-top:-14px;margin-bottom:8px">'
                f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{_b64}" '
                f'download="cuartiles_{mes_sel.lower()}.xlsx" '
                f'style="font-size:0.72rem;color:rgba(255,255,255,0.35);text-decoration:none;letter-spacing:0.03em">'
                f'↓ Exportar Excel</a></div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Sin asesores para esta selección.")


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
# Los DataFrames completos ya no se pasan a mano: las tablas pesadas (_tabla_clasificacion,
# _tabla_periodo, _tabla_evolucion_reciente) están cacheadas por mes y leen de _datos por dentro.
_meses_mat = _cargar_matriculas()["MES"].dropna().unique()
meses_disponibles = [m for m in _MES_ORDEN if m in _meses_mat]

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

    _MESES_VENTANA = meses_disponibles[-6:]
    if meses_disponibles:
        mes_sel = st.selectbox("Mes", ["Todos"] + _MESES_VENTANA, index=0)
    else:
        mes_sel = None
        st.caption("⚠️ Sin datos de matrículas para cuartilizar.")

    # Recorte por día: útil para el mes en curso (aún incompleto). Solo afecta al mes elegido
    # aquí; el resto del período se cuenta completo.
    if meses_disponibles:
        mes_corte = st.selectbox("Recortar por día · mes", meses_disponibles,
                                 index=len(meses_disponibles) - 1,
                                 help="El corte por día se aplica solo a este mes; los demás quedan completos.")
        _dia_raw = st.slider("Contar hasta el día", 1, 31, 31,
                             help="Cuenta matrículas e inscripciones registradas hasta ese día del mes (inclusive). 31 = mes completo.")
        dia_corte = None if _dia_raw >= 31 else int(_dia_raw)
    else:
        mes_corte = dia_corte = None

    st.markdown("""<div class='sbh'>
        <div class='sbh-num' style='color:#34D399!important;background:rgba(52,211,153,0.12);border-color:rgba(52,211,153,0.22)'>02</div>
        <div class='sbh-lbl'>Filtros</div>
        <div class='sbh-rule'></div>
    </div>""", unsafe_allow_html=True)

    tabla_mes_full = (
        _tabla_periodo(mes_sel, tuple(_MESES_VENTANA), mes_corte, dia_corte)
        if mes_sel else pd.DataFrame(columns=_COLS_CLASIFICACION)
    )

    coordinadores = ["Todos"] + sorted(c for c in tabla_mes_full["COORDINADOR"].unique().tolist() if c and c != "Sin asignar")
    coord_sel = st.selectbox("Coordinador", coordinadores)

    _base_sup = tabla_mes_full if coord_sel == "Todos" else tabla_mes_full[tabla_mes_full["COORDINADOR"] == coord_sel]
    supervisores = ["Todos"] + sorted(s for s in _base_sup["SUPERVISOR"].unique().tolist() if s and s != "Sin asignar")
    sup_sel = st.selectbox("Supervisor", supervisores)

    # Los expertos disponibles dependen del coordinador/supervisor elegido.
    _base_exp = _base_sup if sup_sel == "Todos" else _base_sup[_base_sup["SUPERVISOR"] == sup_sel]
    expertos = ["Todos"] + sorted(e for e in _base_exp["ASESOR"].unique().tolist() if e and e != "Sin asignar")
    exp_sel = st.selectbox("Experto", expertos)

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

    @keyframes sbcPulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:.3; transform:scale(.6); }} }}
    @keyframes sbcBar {{ 0% {{ background-position:0% 0%; }} 100% {{ background-position:200% 0%; }} }}

    /* ── Plotly chart: tarjeta de vidrio oscuro ── */
    div[data-testid="stPlotlyChart"] {{
        background: linear-gradient(160deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015)) !important;
        border-radius: 18px !important; box-shadow: 0 16px 38px -16px rgba(0,0,0,0.65) !important;
        border: 1px solid rgba(255,255,255,0.09) !important; overflow: visible !important; padding: 10px !important;
    }}

    /* ── Tabla Clasificación / Evolución: HTML propio (mismo esquema que Avance vs. Meta) ── */
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

if not mes_sel:
    st.stop()

tabla_mes = tabla_mes_full
tabla_vista = tabla_mes
if coord_sel != "Todos":
    tabla_vista = tabla_vista[tabla_vista["COORDINADOR"] == coord_sel]
if sup_sel != "Todos":
    tabla_vista = tabla_vista[tabla_vista["SUPERVISOR"] == sup_sel]
if exp_sel != "Todos":
    tabla_vista = tabla_vista[tabla_vista["ASESOR"] == exp_sel]

_es_todos = mes_sel == "Todos"
_n_ventana = len(_MESES_VENTANA)
_periodo_lbl = "el total de los últimos 6 meses" if _es_todos else mes_sel
_mes_lbl = "Total 6 meses" if _es_todos else mes_sel

# ─────────────────────────────────────────────
# UMBRALES DE CUARTIL — real vs propuesto (mes seleccionado)
# ─────────────────────────────────────────────
# El propuesto de matrículas es un objetivo POR MES, así que los umbrales siempre se miden
# sobre matrículas/inscripciones por mes (con "Todos" se divide el total entre 6).
_umbral_base = tabla_mes_full.copy()
_umbral_lbl = mes_sel
if _es_todos and len(_umbral_base):
    for _c in ("REAL_MAT", "REAL_INSC"):
        _umbral_base[_c] = _umbral_base[_c] / _n_ventana
    _umbral_lbl = "promedio mensual (6 meses)"

_umbral_mat = _tabla_umbrales(_umbral_base, "REAL_MAT", "CUARTIL", _PROPUESTO_MAT)
_umbral_insc = _tabla_umbrales(_umbral_base, "REAL_INSC", "CUARTIL_INSC")

# ─────────────────────────────────────────────
# EVOLUCIÓN RECIENTE (VENTANA DE 6 MESES)
# ─────────────────────────────────────────────
# La ventana termina en el mes seleccionado en el filtro "Mes" (y sus 5 meses previos).
# Con "Todos" se muestran los últimos 6 meses disponibles.
_N_MESES_EVOLUCION = 6
if _es_todos:
    _ventana_evol = meses_disponibles[-_N_MESES_EVOLUCION:]
else:
    _idx_sel = meses_disponibles.index(mes_sel)
    _ventana_evol = meses_disponibles[max(0, _idx_sel - _N_MESES_EVOLUCION + 1): _idx_sel + 1]
_filas_evolucion, _meses_evolucion = _tabla_evolucion_reciente(tuple(_ventana_evol), mes_corte, dia_corte)
if coord_sel != "Todos":
    _filas_evolucion = [f for f in _filas_evolucion if f["COORDINADOR"] == coord_sel]
if sup_sel != "Todos":
    _filas_evolucion = [f for f in _filas_evolucion if f["SUPERVISOR"] == sup_sel]
if exp_sel != "Todos":
    _filas_evolucion = [f for f in _filas_evolucion if f["ASESOR"] == exp_sel]

# Vista Executive BI integrada en esta página.
render(
    tabla_mes=tabla_mes, tabla_vista=tabla_vista,
    filas_evolucion=_filas_evolucion, meses_evolucion=_meses_evolucion,
    umbral_mat=_umbral_mat, umbral_insc=_umbral_insc, umbral_lbl=_umbral_lbl,
    mes_sel=mes_sel, mes_corte=mes_corte, dia_corte=dia_corte,
    mes_lbl=_mes_lbl, periodo_lbl=_periodo_lbl,
)
st.stop()
