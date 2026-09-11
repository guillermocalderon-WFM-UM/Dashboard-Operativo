import base64
import calendar
import html
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import _datos

# La carga de datos (8 archivos mensuales + directorio maestro de expertos) vive en _datos.py,
# compartida con el resto de módulos. Ver ese archivo para el detalle de la resolución.

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
_MES_A_NUM = {mes: i + 1 for i, mes in enumerate(_MES_ORDEN)}


# ─────────────────────────────────────────────
# CARGA DE DATOS  (compartida — ver _datos.py)
# ─────────────────────────────────────────────
_cargar_base = _datos.matriculas
_cargar_metas = _datos.metas


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


# ─────────────────────────────────────────────
# CENTRO DE OPERACIONES — sistema visual "ebi-*" (mismo lenguaje de Inscripciones)
# ─────────────────────────────────────────────
GREEN = "#10B981"
TEAL = "#34D399"
BLUE = "#38BDF8"
INDIGO = "#818CF8"
AMBER = "#F59E0B"
RED = "#F43F5E"
MUTED = "#94A3B8"
BG = "rgba(0,0,0,0)"
MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
WEEKDAYS = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab"]
PALETTE = [BLUE, TEAL, INDIGO, AMBER, "#EC4899", "#22D3EE", "#A3E635", "#FB7185"]


def _layout(height: int = 360, **kwargs) -> dict:
    out = dict(
        height=height, paper_bgcolor=BG, plot_bgcolor=BG,
        margin=dict(l=48, r=28, t=24, b=42),
        font=dict(family="Inter", size=11, color="rgba(255,255,255,.72)"),
        hoverlabel=dict(bgcolor="#0B2119", bordercolor="rgba(255,255,255,.16)", font_size=12),
        legend=dict(orientation="h", y=1.10, x=0, font=dict(size=10)),
    )
    out.update(kwargs)
    return out


AXIS = dict(
    gridcolor="rgba(255,255,255,.065)", zerolinecolor="rgba(255,255,255,.20)",
    tickfont=dict(size=10, color="rgba(255,255,255,.56)"), automargin=True,
)


def _safe(value) -> str:
    return html.escape(str(value))


def _available_months(base: pd.DataFrame) -> list[str]:
    """Meses con al menos una fecha valida en el universo global, incluidos parciales."""
    source = base["_DATE"] if "_DATE" in base else base.get("_FECHA", pd.Series(dtype=object))
    dates = pd.to_datetime(source, errors="coerce", dayfirst=True).dropna()
    present = set(dates.dt.month.astype(int))
    return [month for number, month in enumerate(MONTHS, 1) if number in present]


def _exclusive_change(key: str, exclusive: str) -> None:
    """Hace que Todos/Ninguna no puedan coexistir con opciones individuales."""
    current = list(st.session_state.get(key, []))
    previous = list(st.session_state.get(f"{key}__previous", []))
    if exclusive in current and exclusive not in previous:
        current = [exclusive]
    elif exclusive in current and any(value != exclusive and value not in previous for value in current):
        current = [value for value in current if value != exclusive]
    st.session_state[key] = current
    st.session_state[f"{key}__previous"] = current


def _exclusive_multiselect(
    label: str, options: list[str], key: str, exclusive: str,
    default: list[str] | None = None, empty_means_all: bool = False, **kwargs,
) -> list[str]:
    choices = [exclusive] + options
    valid = set(choices)
    had_value = key in st.session_state
    if had_value:
        cleaned = [value for value in st.session_state[key] if value in valid]
        if exclusive in cleaned and len(cleaned) > 1:
            cleaned = [exclusive]
        st.session_state[key] = cleaned
    initial = list(default or [])
    st.session_state.setdefault(f"{key}__previous", initial)
    selected = st.multiselect(
        label, choices, default=None if had_value else initial, key=key,
        on_change=_exclusive_change, args=(key, exclusive), **kwargs,
    )
    if exclusive in selected:
        return options if exclusive == "Todos" else []
    if not selected and empty_means_all:
        return options
    return [value for value in selected if value in options]


def _multiselect_all(label: str, options: list[str], key: str, default_all: bool = True) -> list[str]:
    return _exclusive_multiselect(
        label, options, key, "Todos", ["Todos"] if default_all else [],
        empty_means_all=True,
    )


def _rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


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


def _status(real: float, target: float) -> str:
    if pd.isna(target) or target <= 0:
        return "Sin meta"
    ratio = real / target
    return "Sobre meta" if ratio > 1.10 else ("En rango" if ratio >= .90 else "Bajo meta")


def _status_color(status: str) -> str:
    return {"Sobre meta": GREEN, "En rango": AMBER, "Bajo meta": RED}.get(status, MUTED)


def _prepare(base: pd.DataFrame) -> pd.DataFrame:
    d = base.copy()
    d["_DATE"] = d["_FECHA"]
    d = d.dropna(subset=["_DATE"]).copy()
    d["_SUP"] = d["_SUPERVISOR"].fillna("Sin asignar").astype(str)
    d["_COORD"] = d["_COORDINADOR"].fillna("Sin asignar").astype(str)
    d["_AGENT"] = d["_ASESOR"].fillna("Sin asignar").astype(str)
    d["_MONTH"] = d["_DATE"].dt.month.map(lambda n: MONTHS[n - 1])
    d["_YEAR"] = d["_DATE"].dt.year
    d["_DAY"] = d["_DATE"].dt.day
    return d


def _meta_rows(metas: pd.DataFrame, supervisors: list[str], months: list[str], agents: list[str] | None = None) -> pd.DataFrame:
    m = metas.copy()
    if "SUPERVISOR" not in m or "MES" not in m:
        return pd.DataFrame()
    m = m[m["SUPERVISOR"].astype(str).isin(supervisors) & m["MES"].isin(months)]
    if agents and "NOMBRE ASESOR" in m:
        m = m[m["NOMBRE ASESOR"].astype(str).isin(agents)]
    cc = "CC" if "CC" in m else "_CC" if "_CC" in m else None
    if cc:
        m = m.drop_duplicates([cc, "MES", "AÑO"] if "AÑO" in m else [cc, "MES"])
    m["_META"] = pd.to_numeric(m.get("Meta matriculas", 0), errors="coerce").fillna(0)
    return m


def _meta_by_supervisor(
    metas: pd.DataFrame, supervisors: list[str], months: list[str], start: date, end: date,
    reference: str, is_business_day, agents: list[str] | None = None,
) -> pd.DataFrame:
    m = _meta_rows(metas, supervisors, months, agents)
    if m.empty:
        return pd.DataFrame(columns=["_SUP", "_MONTH", "META"])
    if "AÑO" not in m:
        m["AÑO"] = end.year
    if reference == "Meta acumulada al corte":
        factors = {}
        for month in months:
            mn = MONTHS.index(month) + 1
            years = m.loc[m["MES"] == month, "AÑO"].dropna().astype(int).unique()
            for year in years:
                last = calendar.monthrange(year, mn)[1]
                mstart, mend = date(year, mn, 1), date(year, mn, last)
                lo, hi = max(start, mstart), min(end, mend)
                total = sum(is_business_day(mstart + timedelta(days=i)) for i in range(last))
                covered = 0 if hi < lo else sum(is_business_day(lo + timedelta(days=i)) for i in range((hi - lo).days + 1))
                factors[(month, year)] = covered / total if total else 0
        m["_FACTOR"] = [factors.get((row.MES, int(row.AÑO)), 0) for row in m.itertuples()]
    else:
        m["_FACTOR"] = 1.0
    m["META"] = m["_META"] * m["_FACTOR"]
    return (
        m.groupby(["SUPERVISOR", "MES"], as_index=False)["META"].sum()
        .rename(columns={"SUPERVISOR": "_SUP", "MES": "_MONTH"})
    )


def _supervisor_month(base: pd.DataFrame, supervisors: list[str], months: list[str]) -> pd.DataFrame:
    grid = pd.MultiIndex.from_product([supervisors, months], names=["_SUP", "_MONTH"]).to_frame(index=False)
    observed = (
        base[base["_SUP"].isin(supervisors) & base["_MONTH"].isin(months)]
        .groupby(["_SUP", "_MONTH"]).size().rename("REAL")
    )
    return grid.join(observed, on=["_SUP", "_MONTH"])


def _supervisor_daily(base, metas, supervisors, months, start, end, is_business_day, reference, meta_agents=None):
    subset = base[base["_SUP"].isin(supervisors) & base["_MONTH"].isin(months)].copy()
    if subset.empty:
        return pd.DataFrame()
    last_observed = min(end, base["_DATE"].max().date())
    first_observed = max(start, base["_DATE"].min().date())
    dates = [
        ts.date() for ts in pd.date_range(first_observed, last_observed, freq="D")
        if MONTHS[ts.month - 1] in months
    ]
    grid = pd.MultiIndex.from_product([supervisors, dates], names=["_SUP", "_DAY_DATE"]).to_frame(index=False)
    subset["_DAY_DATE"] = subset["_DATE"].dt.date
    observed = subset.groupby(["_SUP", "_DAY_DATE"]).size().rename("REAL")
    out = grid.join(observed, on=["_SUP", "_DAY_DATE"])
    out["_DATE_X"] = pd.to_datetime(out["_DAY_DATE"], errors="coerce")
    out["_MONTH"] = out["_DAY_DATE"].map(lambda d: MONTHS[d.month - 1])
    monthly = _meta_by_supervisor(
        metas, supervisors, months, start, end, "Meta mensual", is_business_day, meta_agents,
    ).rename(columns={"META": "META_MONTH"})
    out = out.merge(monthly, how="left", on=["_SUP", "_MONTH"])
    business_counts = {}
    for dt in dates:
        key = (dt.year, dt.month)
        if key not in business_counts:
            days = calendar.monthrange(*key)[1]
            business_counts[key] = sum(is_business_day(date(dt.year, dt.month, n)) for n in range(1, days + 1))
    out["IS_BUSINESS"] = out["_DAY_DATE"].map(is_business_day)
    out["META"] = [
        (float(mm) / business_counts.get((dt.year, dt.month), 1)) if business and pd.notna(mm) else np.nan
        for dt, mm, business in zip(out["_DAY_DATE"], out["META_MONTH"], out["IS_BUSINESS"])
    ]
    if reference == "Meta acumulada al corte":
        out = out.sort_values(["_SUP", "_DAY_DATE"])
        out["REAL"] = out.groupby("_SUP")["REAL"].cumsum()
        out["META"] = out["META"].fillna(0).groupby(out["_SUP"]).cumsum()
    return out


def _render_supervisor(base, metas, start, end, is_business_day, global_agents):
    _panel_title("📈", "Cumplimiento por Supervisor", "Matriculas diarias o mensuales frente a la zona objetivo.", "REAL vs META")
    supervisors = sorted(x for x in base["_SUP"].unique() if x != "Sin asignar")
    months = _available_months(base)
    c1, c2, c3 = st.columns([2.3, .8, 1.4])
    with c1:
        selected = _exclusive_multiselect(
            "Supervisor", supervisors, "mat_v3_sup_series", "Todos", ["Todos"],
            placeholder="Selecciona uno o varios supervisores",
        )
    with c2:
        granularity = st.selectbox("Granularidad", ["Mensual", "Diario"], key="mat_v3_sup_gran")
    with c3:
        selected_months = _multiselect_all("Meses", months, "mat_v2_sup_months")
        selected_months = [month for month in months if month in selected_months]
    references = ["Meta diaria", "Meta acumulada al corte", "Sin meta"] if granularity == "Diario" else ["Meta mensual", "Meta acumulada al corte", "Sin meta"]
    c4, c5, c6 = st.columns([1.2, 1.05, 1.5])
    with c4:
        reference = st.selectbox("Referencia / Meta", references, key="mat_v2_sup_ref")
    with c5:
        view = st.selectbox("Visualizacion", ["Real + Meta", "Solo Real", "Brecha"], key="mat_v2_sup_view")
    with c6:
        bands = _exclusive_multiselect("Bandas de meta", selected, "mat_v2_sup_band", "Ninguna", ["Ninguna"])
    if not selected:
        st.info("Selecciona uno o varios supervisores para comparar su comportamiento.")
        return
    if not selected_months:
        st.info("No hay meses disponibles dentro de los filtros globales.")
        return
    chips = "".join(f"<span style='--dot:{PALETTE[i % len(PALETTE)]}'>● {_safe(s)}</span>" for i, s in enumerate(selected)) if len(selected) <= 5 else f"<span>{len(selected)} supervisores seleccionados</span>"
    st.markdown(f"<div class='ebi-selected'>{chips}</div>", unsafe_allow_html=True)
    if granularity == "Diario":
        d = _supervisor_daily(base, metas, selected, selected_months, start, end, is_business_day, reference, global_agents)
        xcol, sort_col = "_DATE_X", "_DATE_X"
        order = sorted(d["_DATE_X"].dropna().unique()) if len(d) else []
    else:
        d = _supervisor_month(base, selected, selected_months)
        meta = _meta_by_supervisor(metas, selected, selected_months, start, end, reference, is_business_day, global_agents)
        d = d.merge(meta, how="left", on=["_SUP", "_MONTH"])
        # La etiqueta del mes nunca se usa para ordenar la trayectoria.
        d["_MONTH_ORDER"] = d["_MONTH"].map({month: pos for pos, month in enumerate(MONTHS)})
        xcol, sort_col, order = "_MONTH", "_MONTH_ORDER", selected_months
    if reference == "Sin meta":
        d["META"] = np.nan
    elif granularity == "Mensual":
        d["META"] = d["META"].fillna(0)
    d["LOW"] = d["META"] * .9; d["HIGH"] = d["META"] * 1.1
    d["GAP"] = d["REAL"] - d["META"]
    d["PCT"] = np.where(d["META"] > 0, d["REAL"] / d["META"] * 100, np.nan)
    d["STATUS"] = [_status(r, m) for r, m in zip(d["REAL"], d["META"])]
    fig = go.Figure()
    color_by_supervisor = {sup: PALETTE[i % len(PALETTE)] for i, sup in enumerate(selected)}
    active_bands = bands if reference != "Sin meta" and view == "Real + Meta" else []
    for band_supervisor in active_bands:
        f = d[d["_SUP"] == band_supervisor].sort_values(sort_col).copy()
        # La referencia visual interpola solo huecos no laborables para formar un
        # corredor continuo; los valores productivos y la meta de días hábiles no cambian.
        visual_meta = f["META"].interpolate(limit_direction="both") if granularity == "Diario" else f["META"]
        f["BAND_META"] = visual_meta; f["BAND_LOW"] = visual_meta * .9; f["BAND_HIGH"] = visual_meta * 1.1
        color = color_by_supervisor[band_supervisor]
        band_custom = np.column_stack([f["BAND_META"], f["BAND_LOW"], f["BAND_HIGH"]])
        band_time = "%{x|%d/%m/%Y}" if granularity == "Diario" else "%{x}"
        fig.add_scatter(x=f[xcol], y=f["BAND_HIGH"], mode="lines", line=dict(color=_rgba(color,.24), width=.8, shape="spline", smoothing=.35), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=f[xcol], y=f["BAND_LOW"], mode="lines", line=dict(color=_rgba(color,.24), width=.8, shape="spline", smoothing=.35), fill="tonexty", fillcolor=_rgba(color,.07), customdata=band_custom, hovertemplate=f"<b>{_safe(band_supervisor)}</b><br>{band_time}<br>Meta: %{{customdata[0]:,.1f}}<br>Rango: %{{customdata[1]:,.1f}} – %{{customdata[2]:,.1f}}<extra>Banda de tolerancia ±10 %</extra>", showlegend=False)
        fig.add_scatter(x=f[xcol], y=f["BAND_META"], mode="lines", line=dict(color=_rgba(color,.72), width=1.4, dash="dashdot", shape="spline", smoothing=.35), hoverinfo="skip", showlegend=False)
    if view == "Brecha" and reference != "Sin meta":
        fig.add_hline(y=0, line=dict(color=INDIGO, width=1.5, dash="dash"))
    for i, sup in enumerate(selected):
        s = d[d["_SUP"] == sup].sort_values(sort_col)
        y = s["GAP"] if view == "Brecha" and reference != "Sin meta" else s["REAL"]
        custom = np.column_stack([s["REAL"], s["META"], s["LOW"], s["HIGH"], s["GAP"], s["PCT"], s["STATUS"]])
        time_hover = "%{x|%d/%m/%Y}<br>Mes: %{x|%B}" if granularity == "Diario" else "Mes: %{x}"
        fig.add_scatter(
            x=s[xcol], y=y, mode="lines+markers", name=sup, showlegend=True,
            connectgaps=False,
            line=dict(color=color_by_supervisor[sup], width=2.6, shape="spline", smoothing=.35),
            marker=dict(symbol="circle", size=5.5, color=color_by_supervisor[sup], opacity=.82, line=dict(color="#071712", width=.8)),
            customdata=custom,
            hovertemplate=("<b>%{fullData.name}</b><br>" + time_hover + "<br>Real: %{customdata[0]:,.0f}<br>Meta esperada: %{customdata[1]:,.1f}"
                           "<br>Rango objetivo: %{customdata[2]:,.1f} – %{customdata[3]:,.1f}<br>Brecha: %{customdata[4]:+,.1f}"
                           "<br>Cumplimiento: %{customdata[5]:.1f} %<br>Estado: %{customdata[6]}<extra></extra>"),
        )
    xaxis = {**AXIS, "tickformat": "%d %b", "nticks": 16} if granularity == "Diario" else {**AXIS, "categoryorder": "array", "categoryarray": order}
    ytitle = "Brecha" if view == "Brecha" else ("Matriculas acumuladas" if reference == "Meta acumulada al corte" and granularity == "Diario" else "Matriculas")
    fig.update_layout(**_layout(455, margin=dict(l=52, r=28, t=12, b=45)), showlegend=True, hovermode="closest", xaxis=xaxis, yaxis={**AXIS, "title": ytitle})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _coord_map(base: pd.DataFrame) -> dict[str, str]:
    d = base[(base["_SUP"] != "Sin asignar") & (base["_COORD"] != "Sin asignar")]
    if d.empty:
        return {}
    return d.groupby("_SUP")["_COORD"].agg(lambda s: s.mode().iat[0]).to_dict()


def _coordinator_data(base, metas, coords, months, start, end, is_business_day, meta_agents=None, reference="Meta acumulada al corte"):
    b = base[base["_COORD"].isin(coords) & base["_MONTH"].isin(months)]
    real = b.groupby(["_COORD", "_MONTH"]).size().rename("REAL").reset_index()
    sups = sorted(b["_SUP"].unique())
    mm = _meta_by_supervisor(metas, sups, months, start, end, reference, is_business_day, meta_agents)
    mapping = _coord_map(b)
    mm["_COORD"] = mm["_SUP"].map(mapping)
    mt = mm.groupby(["_COORD", "_MONTH"])["META"].sum().reset_index()
    d = real.merge(mt, how="outer", on=["_COORD", "_MONTH"]).fillna(0)
    d["GAP"] = d["REAL"] - d["META"]
    d["PCT"] = np.where(d["META"] > 0, d["REAL"] / d["META"] * 100, np.nan)
    return d


def _render_coordinator(base, metas, start, end, is_business_day, meta_agents=None):
    _panel_title("🧭", "Cumplimiento por Coordinador", "Produccion, meta y brecha por frente de coordinacion.", "BULLET")
    coords = sorted(x for x in base["_COORD"].unique() if x != "Sin asignar")
    months = _available_months(base)
    c1, c2, c3, c4 = st.columns([1.6, 1.3, 1.2, 1.1])
    with c1: selected = _multiselect_all("Coordinador", coords, "mat_v2_coord")
    with c2:
        selected_months = _multiselect_all("Mes", months, "mat_v2_coord_month")
        selected_months = [month for month in months if month in selected_months]
    with c3: order = st.selectbox("Ordenar por", ["Mayor produccion", "Mayor cumplimiento", "Mayor deficit", "Mayor superavit", "Alfabetico"], key="mat_v2_coord_order")
    with c4: view = st.selectbox("Vista", ["Real vs Meta", "Brecha", "Evolucion"], key="mat_v2_coord_view")
    if not selected or not selected_months:
        st.info("No hay coordinadores disponibles para esta seleccion."); return
    d = _coordinator_data(base, metas, selected, selected_months, start, end, is_business_day, meta_agents)
    if view == "Evolucion":
        fig = go.Figure()
        for i, coord in enumerate(selected):
            s = d[d["_COORD"] == coord].set_index("_MONTH").reindex(selected_months).reset_index()
            fig.add_scatter(x=selected_months, y=s["REAL"], mode="lines+markers", name=coord, line=dict(width=2.5, color=PALETTE[i % len(PALETTE)], shape="spline", smoothing=.55), customdata=np.column_stack([s["META"], s["GAP"], s["PCT"]]), hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>Real: %{y:,.0f}<br>Meta: %{customdata[0]:,.0f}<br>Brecha: %{customdata[1]:+,.0f}<br>Cumplimiento: %{customdata[2]:.1f}%<extra></extra>")
        fig.update_layout(**_layout(380), xaxis=AXIS, yaxis={**AXIS, "title": "Matriculas"})
    else:
        a = d.groupby("_COORD", as_index=False)[["REAL", "META"]].sum(); a["GAP"] = a["REAL"] - a["META"]; a["PCT"] = np.where(a["META"] > 0, a["REAL"] / a["META"] * 100, np.nan)
        if order == "Mayor produccion": a = a.sort_values("REAL")
        elif order == "Mayor cumplimiento": a = a.sort_values("PCT")
        elif order == "Mayor deficit": a = a.sort_values("GAP", ascending=False)
        elif order == "Mayor superavit": a = a.sort_values("GAP")
        else: a = a.sort_values("_COORD", ascending=False)
        if view == "Brecha":
            colors = [GREEN if x >= 0 else RED for x in a["GAP"]]
            fig = go.Figure(go.Bar(x=a["GAP"], y=a["_COORD"], orientation="h", marker_color=colors, customdata=np.column_stack([a["REAL"], a["META"], a["PCT"]]), hovertemplate="<b>%{y}</b><br>Brecha: %{x:+,.0f}<br>Real: %{customdata[0]:,.0f}<br>Meta: %{customdata[1]:,.0f}<br>Cumplimiento: %{customdata[2]:.1f}%<extra></extra>"))
            fig.add_vline(x=0, line=dict(color="white", width=1))
        else:
            fig = go.Figure()
            xmax = max(float(a[["REAL", "META"]].max().max()) * 1.18, 1)
            for idx, row in enumerate(a.itertuples()):
                for lo, hi, color in [(0, .9, "rgba(244,63,94,.08)"), (.9, 1, "rgba(245,158,11,.09)"), (1, 1.1, "rgba(16,185,129,.09)"), (1.1, xmax / max(row.META, 1), "rgba(56,189,248,.07)")]:
                    x0, x1 = lo * row.META, min(hi * row.META, xmax)
                    if x1 > x0: fig.add_shape(type="rect", x0=x0, x1=x1, y0=idx-.37, y1=idx+.37, fillcolor=color, line_width=0, layer="below")
            fig.add_bar(x=a["REAL"], y=a["_COORD"], orientation="h", marker_color=BLUE, width=.34, name="Real", customdata=np.column_stack([a["META"], a["GAP"], a["PCT"]]), hovertemplate="<b>%{y}</b><br>Real: %{x:,.0f}<br>Meta: %{customdata[0]:,.0f}<br>Brecha: %{customdata[1]:+,.0f}<br>Cumplimiento: %{customdata[2]:.1f}%<extra></extra>")
            fig.add_scatter(x=a["META"], y=a["_COORD"], mode="markers", marker=dict(symbol="line-ns-open", size=22, color="white", line=dict(width=3)), name="Meta", hovertemplate="%{y}<br>Meta: %{x:,.0f}<extra></extra>")
        fig.update_layout(**_layout(max(300, len(a)*62)), xaxis=AXIS, yaxis={**AXIS, "title": ""}, barmode="overlay")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _business_dates(year: int, month: int, cutoff: date, is_business_day) -> list[date]:
    end = min(date(year, month, calendar.monthrange(year, month)[1]), cutoff)
    if end < date(year, month, 1): return []
    return [date(year, month, d) for d in range(1, end.day + 1) if is_business_day(date(year, month, d))]


def _render_weekday(base, is_business_day):
    _panel_title("🗓️", "Comportamiento por Dia de la Semana", "Promedios comparables por dia habil y patrones por equipo.", "PATRON")
    months = _available_months(base)
    c1, c2, c3 = st.columns(3)
    with c1: metric = st.selectbox("Metrica", ["Promedio diario", "Total"], key="mat_v2_w_metric")
    with c2: compare = st.selectbox("Comparar", ["General", "Coordinadores", "Supervisores"], key="mat_v2_w_compare")
    with c3:
        selected_months = _multiselect_all("Mes", months, "mat_v2_w_month")
        selected_months = [month for month in months if month in selected_months]
    d = base[base["_MONTH"].isin(selected_months)].copy(); d = d[d["_DATE"].dt.date.map(is_business_day)]
    d["_WD"] = d["_DATE"].dt.weekday.map(dict(enumerate(WEEKDAYS)))
    # Denominador calendario: incluye dias habiles observados con produccion cero.
    # El rango termina en la ultima fecha real, por lo que nunca convierte futuro en cero.
    denom = {wd: 0 for wd in WEEKDAYS}
    if len(d):
        for dt in pd.date_range(d["_DATE"].min().normalize(), d["_DATE"].max().normalize(), freq="D"):
            day = dt.date()
            wd = dict(enumerate(WEEKDAYS)).get(dt.weekday())
            if wd and is_business_day(day) and MONTHS[dt.month - 1] in selected_months:
                denom[wd] += 1
    group = "_COORD" if compare == "Coordinadores" else "_SUP" if compare == "Supervisores" else None
    groups = ["General"] if group is None else sorted(x for x in d[group].unique() if x != "Sin asignar")
    rows = []
    for g in groups:
        dg = d if group is None else d[d[group] == g]
        for wd in WEEKDAYS:
            total = len(dg[dg["_WD"] == wd])
            value = total / max(denom[wd], 1) if metric == "Promedio diario" else total
            rows.append((g, wd, value, total))
    out = pd.DataFrame(rows, columns=["GRUPO", "DIA", "VALOR", "TOTAL"])
    if compare == "General":
        fig = go.Figure(go.Bar(x=WEEKDAYS, y=out["VALOR"], marker_color=[BLUE, BLUE, TEAL, TEAL, INDIGO, AMBER], customdata=out[["TOTAL"]], hovertemplate="%{x}<br>Valor: %{y:.1f}<br>Total: %{customdata[0]}<extra></extra>"))
    else:
        p = out.pivot(index="GRUPO", columns="DIA", values="VALOR").reindex(columns=WEEKDAYS).fillna(0)
        fig = go.Figure(go.Heatmap(z=p.values, x=p.columns, y=p.index, colorscale=[[0,"#0B2A21"],[.45,"#0EA5E9"],[1,"#6EE7B7"]], colorbar=dict(title=metric, thickness=10), text=np.round(p.values,1), texttemplate="%{text}", hovertemplate="%{y}<br>%{x}: %{z:.1f}<extra></extra>"))
    fig.update_layout(**_layout(max(330, len(groups)*38)), xaxis=AXIS, yaxis=AXIS)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _render_trend(base):
    _panel_title("〽️", "Tendencia Diaria", "Produccion observada de un unico mes; el futuro permanece vacio.", "DIARIO")
    months = _available_months(base)
    c1, c2, c3 = st.columns(3)
    with c1: month = st.selectbox("Mes", months, index=max(len(months)-1,0), key="mat_v2_t_month") if months else None
    with c2: visual = st.selectbox("Visual", ["Barras", "Linea"], key="mat_v2_t_visual")
    with c3: smooth = st.selectbox("Suavizado", ["Ninguno", "Media movil 7 dias"], key="mat_v2_t_smooth")
    if not month: st.info("Sin meses disponibles."); return None
    d = base[base["_MONTH"] == month].copy(); last = d["_DATE"].max().date()
    first = date(last.year, last.month, 1); idx = pd.date_range(first, last, freq="D")
    daily = d.groupby(d["_DATE"].dt.normalize()).size().reindex(idx, fill_value=0).rename("TOTAL").to_frame()
    daily["MM7"] = daily["TOTAL"].rolling(7, min_periods=1).mean()
    daily["DOW"] = daily.index.day_name()
    fig = go.Figure()
    custom = np.column_stack([daily["TOTAL"], daily["MM7"], daily["DOW"]])
    hover = "%{x|%d/%m/%Y}<br>Matriculas: %{customdata[0]}<br>Media movil: %{customdata[1]:.1f}<br>%{customdata[2]}<extra></extra>"
    y = daily["MM7"] if smooth != "Ninguno" else daily["TOTAL"]
    if visual == "Linea":
        fig.add_scatter(x=daily.index, y=y, mode="lines+markers", line=dict(color=BLUE,width=3,shape="spline",smoothing=.55), marker=dict(size=6), customdata=custom, hovertemplate=hover)
    else:
        fig.add_bar(x=daily.index, y=y, marker_color=GREEN, customdata=custom, hovertemplate=hover)
        if smooth != "Ninguno":
            fig.add_scatter(x=daily.index, y=daily["MM7"], mode="lines", line=dict(color=BLUE,width=2.5,shape="spline",smoothing=.55), name="Media movil 7d", customdata=custom, hovertemplate=hover)
    fig.update_layout(**_layout(390), xaxis={**AXIS,"dtick":86400000}, yaxis={**AXIS,"title":"Matriculas"})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    return month


def _gap_data(base, metas, month, level, start, end, is_business_day, meta_agents=None):
    d = base[base["_MONTH"] == month]
    supervisors = sorted(d["_SUP"].unique())
    mm = _meta_by_supervisor(metas, supervisors, [month], start, end, "Meta acumulada al corte", is_business_day, meta_agents)
    real = d.groupby("_SUP").size().rename("REAL").reset_index()
    x = real.merge(mm.groupby("_SUP")["META"].sum().reset_index(), how="outer", on="_SUP").fillna(0)
    if level == "Coordinador":
        mapping = _coord_map(d); x["NIVEL"] = x["_SUP"].map(mapping).fillna("Sin asignar"); x = x.groupby("NIVEL",as_index=False)[["REAL","META"]].sum()
    else: x = x.rename(columns={"_SUP":"NIVEL"})
    x["GAP"] = x["REAL"] - x["META"]; x["PCT_GAP"] = np.where(x["META"]>0, x["GAP"]/x["META"]*100, np.nan)
    x["STATUS"] = [_status(r,m) for r,m in zip(x["REAL"],x["META"])]
    return x


def _render_gap(base, metas, start, end, is_business_day, meta_agents=None):
    _panel_title("⚖️", "Brecha Real vs Meta", "Cero representa la meta; izquierda es deficit y derecha superavit.", "INTERVENCION")
    months = _available_months(base)
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: level=st.selectbox("Nivel",["Supervisor","Coordinador"],key="mat_v2_g_level")
    with c2: month=st.selectbox("Mes",months,index=max(len(months)-1,0),key="mat_v2_g_month") if months else None
    with c3: show=st.selectbox("Mostrar",["Todos","Solo bajo meta","En riesgo","Sobre meta"],key="mat_v2_g_show")
    with c4: order=st.selectbox("Orden",["Mayor deficit","Mayor superavit","Alfabetico"],key="mat_v2_g_order")
    with c5: unit=st.selectbox("Unidad",["Matriculas","Porcentaje"],key="mat_v2_g_unit")
    if not month: return
    x=_gap_data(base,metas,month,level,start,end,is_business_day,meta_agents)
    if show=="Solo bajo meta": x=x[x["STATUS"]=="Bajo meta"]
    elif show=="En riesgo": x=x[x["STATUS"]=="En rango"]
    elif show=="Sobre meta": x=x[x["STATUS"]=="Sobre meta"]
    if order=="Mayor deficit": x=x.sort_values("GAP",ascending=False)
    elif order=="Mayor superavit": x=x.sort_values("GAP")
    else: x=x.sort_values("NIVEL",ascending=False)
    counts=x["STATUS"].value_counts()
    st.markdown(f"<div class='ebi-kpis'><span><b style='color:{GREEN}'>{counts.get('Sobre meta',0)}</b> SOBRE META</span><span><b style='color:{AMBER}'>{counts.get('En rango',0)}</b> EN RANGO</span><span><b style='color:{RED}'>{counts.get('Bajo meta',0)}</b> BAJO META</span></div>",unsafe_allow_html=True)
    val=x["PCT_GAP"] if unit=="Porcentaje" else x["GAP"]
    fig=go.Figure(go.Bar(x=val,y=x["NIVEL"],orientation="h",marker_color=[_status_color(s) for s in x["STATUS"]],customdata=np.column_stack([x["REAL"],x["META"],x["GAP"],x["PCT_GAP"],x["STATUS"]]),hovertemplate="<b>%{y}</b><br>Real: %{customdata[0]:,.0f}<br>Meta: %{customdata[1]:,.0f}<br>Brecha: %{customdata[2]:+,.0f}<br>Brecha %: %{customdata[3]:+.1f}%<br>%{customdata[4]}<extra></extra>"))
    fig.add_vrect(x0=-10 if unit=="Porcentaje" else -float(x["META"].mean()*.1 if len(x) else 0),x1=10 if unit=="Porcentaje" else float(x["META"].mean()*.1 if len(x) else 0),fillcolor="rgba(99,102,241,.10)",line_width=0,layer="below")
    fig.add_vline(x=0,line=dict(color="white",width=1.5)); fig.update_layout(**_layout(max(330,len(x)*38)),xaxis=AXIS,yaxis=AXIS)
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})


def _heatmap(base, row_col, rows, month, is_business_day, key, observed_through=None):
    d=base[base["_MONTH"]==month].copy()
    if d.empty: st.info("Sin datos para el mes seleccionado."); return None
    if not rows: st.info("No hay responsables disponibles para construir la matriz."); return None
    year=int(d["_YEAR"].mode().iat[0]); last_data=observed_through or d["_DATE"].max().date(); days=calendar.monthrange(year,MONTHS.index(month)+1)[1]
    grouped=d.groupby([row_col,"_DAY"]).size()
    pv=grouped.unstack(fill_value=0).reindex(index=rows,columns=range(1,days+1),fill_value=0)
    z=pv.astype(float).values; text=pv.astype(str).values.astype(object)
    custom=np.empty((len(rows),days,2),dtype=object)
    hover=np.empty((len(rows),days),dtype=object)
    for i in range(len(rows)):
        for j,day in enumerate(range(1,days+1)):
            custom[i,j]=[day,int(pv.iat[i,j])]
            hover[i,j]=(f"<b>{_safe(rows[i])}</b><br>{day:02d}/{MONTHS.index(month)+1:02d}/{year}<br>Matriculas: {custom[i,j,1]}")
    for j,day in enumerate(range(1,days+1)):
        dt=date(year,MONTHS.index(month)+1,day)
        if dt>last_data:
            z[:,j]=-2; text[:,j]=""
            for i,row in enumerate(rows): hover[i,j]=f"<b>{_safe(row)}</b><br>{dt:%d/%m/%Y}<br>Futuro / sin informacion"
        elif not is_business_day(dt):
            z[:,j]=-1; text[:,j]="·"
            for i,row in enumerate(rows): hover[i,j]=f"<b>{_safe(row)}</b><br>{dt:%d/%m/%Y}<br>Dia no laborable"
    vmax=max(float(np.nanmax(z)),1)
    colors=[[0,"#07130F"],[1/(vmax+2)-.001,"#07130F"],[1/(vmax+2),"#334155"],[2/(vmax+2)-.001,"#334155"],[2/(vmax+2),"#7F1D2D"],[min(1,3/(vmax+2)),"#064E3B"],[1,"#34D399"]]
    fig=go.Figure(go.Heatmap(z=z,x=[f"{i:02d}" for i in range(1,days+1)],y=rows,zmin=-2,zmax=vmax,colorscale=colors,showscale=True,colorbar=dict(title="Matriculas",thickness=10,tick0=0,dtick=max(1,int(np.ceil(vmax/5)))),text=text,texttemplate="%{text}",customdata=custom,hovertext=hover,hovertemplate="%{hovertext}<extra></extra>",xgap=2,ygap=2))
    fig.update_layout(**_layout(max(320,len(rows)*31+110),margin=dict(l=150,r=30,t=20,b=45)),xaxis={**AXIS,"side":"top"},yaxis=AXIS)
    event=st.plotly_chart(fig,width="stretch",config={"displayModeBar":False},key=key,on_select="rerun",selection_mode="points")
    try:
        point=event.selection.points[0]
        cell=point.get("customdata")
        day=cell[0] if isinstance(cell,(list,tuple)) else int(point["x"])
        return str(point["y"]),int(day)
    except (AttributeError,IndexError,KeyError,TypeError,ValueError):
        return None


def _cell_detail(base,row_col,row,month,day):
    d=base[(base[row_col]==row)&(base["_MONTH"]==month)&(base["_DAY"]==day)]
    if d.empty: return
    dt=d["_DATE"].iloc[0].strftime("%d/%m/%Y"); total=len(d)
    st.markdown(f"**{_safe(row)} · {dt}** — {total} matriculas · {d['_AGENT'].nunique()} asesores activos")
    agent=d.groupby("_AGENT").size().reset_index(name="Matriculas").rename(columns={"_AGENT":"Asesor"})
    st.dataframe(agent[["Asesor","Matriculas"]],width="stretch",hide_index=True)
    detail=[c for c in ["Cedula","NOMBRE_COMPLETO","Programa","Nivel Formación","COHORTE","Fecha Contabilización"] if c in d]
    if detail:
        with st.expander("Detalle de matriculas"):
            st.dataframe(d[detail],width="stretch",hide_index=True)


def _alerts(base, supervisor, month, is_business_day):
    d=base[(base["_SUP"]==supervisor)&(base["_MONTH"]==month)].copy()
    if d.empty: return pd.DataFrame(),pd.DataFrame()
    cutoff=base.loc[base["_MONTH"]==month,"_DATE"].max().date(); year=cutoff.year; mn=cutoff.month
    biz=_business_dates(year,mn,cutoff,is_business_day); alerts=[]; critical=[]
    for agent,da in d[d["_AGENT"]!="Sin asignar"].groupby("_AGENT"):
        start=da["_DATE"].min().date(); valid=[x for x in biz if x>=start]
        by=da.groupby(da["_DATE"].dt.date).size(); zeros=[x for x in valid if int(by.get(x,0))==0]
        prod=int(len(da)); dates_con_matricula=sorted(da["_DATE"].dt.date.unique())
        for z in zeros:
            previous=[x for x in dates_con_matricula if x<z]
            alerts.append({"Agente":agent,"Supervisor":supervisor,"Fecha":z.strftime("%d/%m/%Y"),"Ultima matricula":max(previous).strftime("%d/%m/%Y") if previous else "—","Produccion mes":prod})
        streak=[]
        for dt in valid+[None]:
            if dt in zeros: streak.append(dt)
            elif streak:
                if len(streak)>=2:
                    previous=[x for x in dates_con_matricula if x<streak[0]]
                    critical.append({"Agente":agent,"Supervisor":supervisor,"Dias consecutivos":len(streak),"Desde":streak[0].strftime("%d/%m/%Y"),"Hasta":streak[-1].strftime("%d/%m/%Y"),"Ultima matricula":max(previous).strftime("%d/%m/%Y") if previous else "—","Produccion mes":prod})
                streak=[]
    alert_df=pd.DataFrame(alerts)
    if len(alert_df):
        alert_df["_ORDER"]=pd.to_datetime(alert_df["Fecha"],dayfirst=True); alert_df=alert_df.sort_values("_ORDER",ascending=False).drop(columns="_ORDER")
    critical_df=pd.DataFrame(critical)
    if len(critical_df):
        critical_df["_ORDER"]=pd.to_datetime(critical_df["Hasta"],dayfirst=True); critical_df=critical_df.sort_values(["Dias consecutivos","_ORDER"],ascending=[False,False]).drop(columns="_ORDER")
    return alert_df,critical_df


def _pretty_date(value) -> str:
    if value == "—" or pd.isna(value): return "—"
    parsed=pd.to_datetime(value,dayfirst=True,errors="coerce")
    if pd.isna(parsed): return _safe(value)
    short=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"][parsed.month-1]
    return f"{parsed.day:02d} {short} {parsed.year}"


def _incident_cards(frame: pd.DataFrame, critical: bool=False) -> None:
    if frame.empty:
        st.success("Sin alertas para la seleccion.")
        return
    cards=[]
    for _,row in frame.iterrows():
        if critical:
            headline=f"<strong>{int(row['Dias consecutivos'])} dias consecutivos</strong><span>{_pretty_date(row['Desde'])} → {_pretty_date(row['Hasta'])}</span>"
            badge=f"{int(row['Dias consecutivos'])} DIAS"
            tone="critical"; icon="●"
        else:
            headline=f"<strong>{_pretty_date(row['Fecha'])}</strong><span>0 matriculas registradas</span>"
            badge="ALERTA"; tone="warning"; icon="●"
        cards.append(
            f"<article class='ebi-incident {tone}'><div class='ebi-inc-dot'>{icon}</div>"
            f"<div class='ebi-inc-body'><div class='ebi-inc-name'>{_safe(row['Agente'])}</div>"
            f"<div class='ebi-inc-sup'>{_safe(row['Supervisor'])}</div><div class='ebi-inc-main'>{headline}</div>"
            f"<div class='ebi-inc-foot'><span>Ultima matricula: <b>{_pretty_date(row['Ultima matricula'])}</b></span>"
            f"<span>Produccion del mes: <b>{int(row['Produccion mes'])}</b></span></div></div>"
            f"<div class='ebi-inc-badge'>{badge}</div></article>"
        )
    st.markdown("<div class='ebi-inc-scroll'>"+"".join(cards)+"</div>",unsafe_allow_html=True)


def _render_matrix_alerts(base, supervisor, month, is_business_day):
    """Alertas subordinadas a la selección de la matriz diaria por asesor."""
    alerts, critical = _alerts(base, supervisor, month, is_business_day)
    a1, a2 = st.columns(2)
    with a1:
        _panel_title("🟠", "Alertas", "Dias operativos sin matriculas.", f"{len(alerts)} EVENTOS")
        _incident_cards(alerts, critical=False)
    with a2:
        _panel_title(
            "🔴", "Alertas criticas",
            f"Rachas de dos o mas dias habiles sin matricula · {month}.",
            f"{len(critical)} RACHA(S)",
        )
        _incident_cards(critical, critical=True)


def _render_matrices(base,roster,is_business_day,global_supervisor):
    """`roster` es el universo COMPLETO de supervisores/asesores (sin recorte de fecha
    ni de mes) — de ahí sale quién aparece en la matriz, para que un asesor con cero
    matriculas en el mes elegido siga la fila en vez de desaparecer. `base` (ya
    filtrada por fecha/mes) sigue siendo la fuente de los valores dia a dia."""
    months=_available_months(base)
    _panel_title("▦","Matriz diaria por Supervisor","Produccion por dia; gris es no laborable y vacio es futuro.","HEATMAP")
    month=st.selectbox("Mes",months,index=max(len(months)-1,0),key="mat_v2_ms_month") if months else None
    if month:
        cutoff=base.loc[base["_MONTH"]==month,"_DATE"].max().date()
        rows=sorted(x for x in roster["_SUP"].unique() if x!="Sin asignar")
        selected=_heatmap(base,"_SUP",rows,month,is_business_day,"mat_v2_ms_heat",cutoff)
        if selected: _cell_detail(base,"_SUP",selected[0],month,selected[1])
    _panel_title("👤","Matriz diaria por Asesor","Se construye solo para un supervisor, protegiendo el rendimiento de la pagina.","SEGUIMIENTO")
    supervisors=sorted(x for x in roster["_SUP"].unique() if x!="Sin asignar")
    default=supervisors.index(global_supervisor)+1 if global_supervisor in supervisors else 0
    supervisor=st.selectbox("Supervisor",["Todos"]+supervisors,index=default,key="mat_v2_ma_sup")
    if supervisor=="Todos":
        st.info("Selecciona un supervisor para visualizar el comportamiento diario de sus asesores.")
    else:
        month_a=st.selectbox("Mes de asesores",months,index=max(len(months)-1,0),key="mat_v2_ma_month")
        cutoff_a=base.loc[base["_MONTH"]==month_a,"_DATE"].max().date()
        rows=sorted(x for x in roster.loc[roster["_SUP"]==supervisor,"_AGENT"].unique() if x!="Sin asignar")
        selected=_heatmap(base[base["_SUP"]==supervisor],"_AGENT",rows,month_a,is_business_day,"mat_v2_ma_heat",cutoff_a)
        if selected: _cell_detail(base,"_AGENT",selected[0],month_a,selected[1])
        _render_matrix_alerts(base, supervisor, month_a, is_business_day)


def _supervisor_summary(base,metas,month,start,end,is_business_day,meta_agents=None):
    d=base[base["_MONTH"]==month]; sups=sorted(x for x in d["_SUP"].unique() if x!="Sin asignar")
    meta=_meta_by_supervisor(metas,sups,[month],start,end,"Meta acumulada al corte",is_business_day,meta_agents).groupby("_SUP")["META"].sum()
    rows=[]
    for sup in sups:
        s=d[d["_SUP"]==sup]; total=len(s); agents=max(s.loc[s["_AGENT"]!="Sin asignar","_AGENT"].nunique(),1); target=float(meta.get(sup,0))
        daily=s.groupby(s["_DATE"].dt.date).size(); mean=daily.mean() if len(daily) else 0; cv=daily.std()/mean if mean else 9
        cutoff=s["_DATE"].max().date(); biz=_business_dates(cutoff.year,cutoff.month,cutoff,is_business_day); active=sum(int(daily.get(x,0))>0 for x in biz)
        programas=s["Programa"].replace("",pd.NA).dropna().nunique()
        rows.append({"SUP":sup,"Cumplimiento":min(total/target*100,100) if target else 0,"Volumen":total,"Diversidad":programas,"Consistencia":100/(1+cv),"Productividad":total/agents,"Continuidad":active/len(biz)*100 if biz else 0,"Agentes":agents,"Meta":target})
    out=pd.DataFrame(rows)
    for c in ["Volumen","Productividad","Diversidad"]:
        mx=out[c].max() if len(out) else 0; out[c+"_N"]=out[c]/mx*100 if mx else 0
    return out


def _render_analysis(base,metas,start,end,is_business_day,meta_agents=None):
    months=_available_months(base)
    if not months:return
    _panel_title("◉","Perfil Operativo","Seis dimensiones normalizadas para comparar perfiles, no solo volumen.","0–100")
    c1,c2=st.columns([1,2])
    with c1: month=st.selectbox("Mes",months,index=max(len(months)-1,0),key="mat_v2_r_month")
    summary=_supervisor_summary(base,metas,month,start,end,is_business_day,meta_agents)
    with c2: selected=st.multiselect("Comparar supervisores (maximo 3)",summary["SUP"].tolist(),default=summary.sort_values("Volumen",ascending=False)["SUP"].head(2).tolist(),max_selections=3,key="mat_v2_r_sup")
    axes=["Cumplimiento","Volumen","Diversidad","Consistencia","Productividad","Continuidad"]
    defs={"Cumplimiento":"Matriculas / meta al corte","Volumen":"Matriculas relativo al mejor equipo","Diversidad":"Programas distintos gestionados, relativo al mejor equipo","Consistencia":"100 / (1 + coeficiente de variacion diaria)","Productividad":"Matriculas por asesor, relativo al mejor equipo","Continuidad":"Dias habiles con produccion / dias habiles observados"}
    fig=go.Figure()
    for i,sup in enumerate(selected):
        r=summary[summary["SUP"]==sup].iloc[0]; vals=[r["Cumplimiento"],r["Volumen_N"],r["Diversidad_N"],r["Consistencia"],r["Productividad_N"],r["Continuidad"]]; vals+=vals[:1]; theta=axes+axes[:1]
        fig.add_scatterpolar(r=vals,theta=theta,fill="toself",name=sup,line=dict(color=PALETTE[i],width=2),fillcolor="rgba(56,189,248,.08)",customdata=[defs[a] for a in theta],hovertemplate="%{theta}: %{r:.1f}<br>%{customdata}<extra>%{fullData.name}</extra>")
    fig.update_layout(**_layout(440),polar=dict(bgcolor=BG,radialaxis=dict(range=[0,100],gridcolor="rgba(255,255,255,.10)",tickfont=dict(size=9)),angularaxis=dict(gridcolor="rgba(255,255,255,.08)")))
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})
    _panel_title("⚡","Productividad por Asesor Activo","Distingue escala de equipo de eficiencia real por persona.","CAPACIDAD")
    c1,c2,c3=st.columns(3)
    with c1: pmonth=st.selectbox("Mes",months,index=months.index(month),key="mat_v2_p_month")
    pdata=_supervisor_summary(base,metas,pmonth,start,end,is_business_day,meta_agents)
    coords=sorted(x for x in base["_COORD"].unique() if x!="Sin asignar")
    with c2: pcoords=_multiselect_all("Coordinador",coords,"mat_v2_p_coord")
    allowed=set(base.loc[base["_COORD"].isin(pcoords),"_SUP"]); pdata=pdata[pdata["SUP"].isin(allowed)]
    with c3: psups=_multiselect_all("Supervisor",pdata["SUP"].tolist(),"mat_v2_p_sup")
    pdata=pdata[pdata["SUP"].isin(psups)].sort_values("Productividad")
    fig=go.Figure(go.Bar(x=pdata["Productividad"],y=pdata["SUP"],orientation="h",marker_color=TEAL,customdata=pdata[["Volumen","Agentes"]],hovertemplate="<b>%{y}</b><br>Productividad: %{x:.1f}<br>Produccion total: %{customdata[0]:,.0f}<br>Asesores activos: %{customdata[1]:,.0f}<extra></extra>")); fig.update_layout(**_layout(max(320,len(pdata)*37)),xaxis={**AXIS,"title":"Matriculas por asesor activo"},yaxis=AXIS)
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})


def _render_projection(base,metas,start,end,is_business_day,meta_agents=None):
    _panel_title("◎","Proyeccion de Cierre de Mes","Estimacion lineal por ritmo observado en dias habiles.","FORECAST")
    months=_available_months(base); c1,c2,c3=st.columns(3)
    with c1: month=st.selectbox("Mes",months,index=max(len(months)-1,0),key="mat_v2_f_month") if months else None
    with c2: level=st.selectbox("Nivel",["General","Coordinador","Supervisor"],key="mat_v2_f_level")
    if not month:return
    d=base[base["_MONTH"]==month]
    options=["General"] if level=="General" else sorted(x for x in d["_COORD" if level=="Coordinador" else "_SUP"].unique() if x!="Sin asignar")
    with c3: entity=st.selectbox(level,options,key="mat_v2_f_entity")
    if level!="General": d=d[d["_COORD" if level=="Coordinador" else "_SUP"]==entity]
    if d.empty:st.info("Sin datos para proyectar.");return
    cutoff=d["_DATE"].max().date(); mn=cutoff.month; year=cutoff.year; elapsed=len(_business_dates(year,mn,cutoff,is_business_day)); month_end=date(year,mn,calendar.monthrange(year,mn)[1]); total_days=len(_business_dates(year,mn,month_end,is_business_day))
    actual=int(len(d))
    projection=actual/elapsed*total_days if elapsed else 0
    sups=sorted(d["_SUP"].unique()); target=float(_meta_by_supervisor(metas,sups,[month],date(year,mn,1),month_end,"Meta mensual",is_business_day,meta_agents).META.sum())
    gap=projection-target; xmax=max(target,projection,actual,1)*1.12
    st.markdown(f"<div class='ebi-forecast'><span>META<b>{target:,.0f}</b></span><span>ACTUAL<b>{actual:,.0f}</b></span><span>PROYECCION<b>{projection:,.0f}</b></span><span>BRECHA PROYECTADA<b style='color:{GREEN if gap>=0 else RED}'>{gap:+,.0f}</b></span></div>",unsafe_allow_html=True)
    fig=go.Figure(); fig.add_bar(y=[entity],x=[actual],orientation="h",marker_color=GREEN,width=.28,name="Actual",hovertemplate="Actual: %{x:,.0f}<extra></extra>"); fig.add_scatter(x=[projection],y=[entity],mode="markers",marker=dict(symbol="diamond",size=14,color=BLUE),name="Proyeccion",hovertemplate="Proyeccion: %{x:,.0f}<extra></extra>"); fig.add_scatter(x=[target],y=[entity],mode="markers",marker=dict(symbol="line-ns-open",size=28,color="white",line=dict(width=3)),name="Meta",hovertemplate="Meta: %{x:,.0f}<extra></extra>"); fig.add_shape(type="line",x0=actual,x1=projection,y0=0,y1=0,line=dict(color=BLUE,width=3,dash="dot")); fig.update_layout(**_layout(230),xaxis={**AXIS,"range":[0,xmax]},yaxis=AXIS)
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})


def _metric_daily_history(frame, cutoff, is_business_day):
    if frame.empty:
        return pd.Series(dtype=float)
    d = frame[frame["_DATE"].dt.date <= cutoff]
    if d.empty:
        return pd.Series(dtype=float)
    grouped = d.groupby(d["_DATE"].dt.normalize()).size()
    first = max(d["_DATE"].min().date(), cutoff - timedelta(days=120))
    calendar_days = [dt for dt in pd.date_range(first, cutoff, freq="D") if is_business_day(dt.date())]
    return grouped.reindex(calendar_days, fill_value=0).astype(float)


def _probabilistic_forecast(history, actual, target, cutoff, month_end, is_business_day, seed=42):
    remaining = [
        dt for dt in pd.date_range(cutoff + timedelta(days=1), month_end, freq="D")
        if is_business_day(dt.date())
    ]
    recent = history.tail(60)
    if recent.empty or not remaining:
        outcomes = np.full(2000, float(actual))
    else:
        baseline = float(recent.tail(30).mean())
        momentum = float(recent.tail(10).mean()) / baseline if baseline > 0 else 1.0
        momentum = float(np.clip(momentum, .70, 1.30))
        rng = np.random.default_rng(seed)
        future = np.zeros(2000)
        for dt in remaining:
            same_weekday = recent[recent.index.weekday == dt.weekday()]
            pool = same_weekday if len(same_weekday) >= 2 else recent
            future += rng.choice(pool.to_numpy(), size=len(future), replace=True) * momentum
        outcomes = actual + future
    p10, p50, p90 = np.percentile(outcomes, [10, 50, 90])
    probability = float(np.mean(outcomes >= target) * 100) if target > 0 else np.nan
    expected_daily = float(np.mean(outcomes - actual) / len(remaining)) if remaining else 0.0
    required_daily = max(target - actual, 0) / len(remaining) if remaining else 0.0
    if target <= 0:
        goal_date = "Sin meta"
    elif actual >= target:
        goal_date = _pretty_date(cutoff)
    elif expected_daily <= 0:
        goal_date = "Fuera del mes"
    else:
        days_needed = int(np.ceil((target - actual) / expected_daily))
        goal_date = _pretty_date(remaining[days_needed - 1]) if 0 < days_needed <= len(remaining) else "Fuera del mes"
    return {
        "p10": float(p10), "p50": float(p50), "p90": float(p90),
        "probability": probability, "required_daily": float(required_daily),
        "expected_daily": expected_daily, "goal_date": goal_date,
        "remaining_days": len(remaining),
    }


def _forecast_actual(frame):
    return int(len(frame))


def _forecast_risk_data(scope, metas, month, cutoff, month_end, is_business_day, meta_agents):
    month_scope = scope[scope["_MONTH"] == month]
    supervisors = sorted(x for x in month_scope["_SUP"].unique() if x != "Sin asignar")
    targets = _meta_by_supervisor(
        metas, supervisors, [month], date(cutoff.year, cutoff.month, 1), month_end,
        "Meta mensual", is_business_day, meta_agents,
    ).groupby("_SUP")["META"].sum()
    rows = []
    for pos, supervisor in enumerate(supervisors):
        sup_scope = scope[scope["_SUP"] == supervisor]
        actual = _forecast_actual(month_scope[month_scope["_SUP"] == supervisor])
        target = float(targets.get(supervisor, 0))
        history = _metric_daily_history(sup_scope, cutoff, is_business_day)
        stats = _probabilistic_forecast(history, actual, target, cutoff, month_end, is_business_day, 100 + pos)
        probability = stats["probability"]
        risk = "Sin meta" if pd.isna(probability) else ("Bajo" if probability >= 75 else "Medio" if probability >= 40 else "Alto")
        rows.append({"Supervisor": supervisor, "Actual": actual, "Meta": target, "P50": stats["p50"], "Probabilidad": probability, "Riesgo": risk})
    return pd.DataFrame(rows)


def _render_predictive(base,metas,start,end,is_business_day,meta_agents=None):
    _panel_title("◎","Proyeccion probabilistica de cierre","Simulacion por ritmo reciente y patron de dias habiles.","PREDICTIVO")
    months=_available_months(base); c1,c2,c3=st.columns(3)
    with c1: month=st.selectbox("Mes",months,index=max(len(months)-1,0),key="mat_v4_pf_month") if months else None
    with c2: level=st.selectbox("Nivel",["General","Coordinador","Supervisor"],key="mat_v4_pf_level")
    if not month:return
    month_base=base[base["_MONTH"]==month]
    options=["General"] if level=="General" else sorted(x for x in month_base["_COORD" if level=="Coordinador" else "_SUP"].unique() if x!="Sin asignar")
    with c3: entity=st.selectbox(level,options,key="mat_v4_pf_entity")
    scope=base
    if level!="General": scope=scope[scope["_COORD" if level=="Coordinador" else "_SUP"]==entity]
    d=scope[scope["_MONTH"]==month]
    if d.empty:st.info("Sin datos para proyectar.");return
    cutoff=month_base["_DATE"].max().date(); mn=cutoff.month; year=cutoff.year; month_end=date(year,mn,calendar.monthrange(year,mn)[1])
    actual=_forecast_actual(d)
    sups=sorted(d["_SUP"].unique()); target=float(_meta_by_supervisor(metas,sups,[month],date(year,mn,1),month_end,"Meta mensual",is_business_day,meta_agents).META.sum())
    history=_metric_daily_history(scope,cutoff,is_business_day)
    stats=_probabilistic_forecast(history,actual,target,cutoff,month_end,is_business_day)
    projection=stats["p50"]; gap=projection-target; probability=stats["probability"]
    probability_text="—" if pd.isna(probability) else _percent_es(probability)
    interval=f"{_number_es(stats['p10'])} – {_number_es(stats['p90'])}"
    st.markdown(
        f"<div class='ebi-forecast ebi-forecast-predictive'>"
        f"<span>META<b>{_number_es(target)}</b><small>{stats['remaining_days']} dias habiles restantes</small></span>"
        f"<span>ACTUAL<b>{_number_es(actual)}</b><small>Corte: {_pretty_date(cutoff)}</small></span>"
        f"<span>PROYECCION P50<b>{_number_es(projection)}</b><small>Escenario central</small></span>"
        f"<span>RANGO PROBABLE 80 %<b>{interval}</b><small>Percentiles P10–P90</small></span>"
        f"<span>PROBABILIDAD DE META<b style='color:{GREEN if not pd.isna(probability) and probability>=75 else AMBER if not pd.isna(probability) and probability>=40 else RED}'>{probability_text}</b><small>2.000 escenarios</small></span>"
        f"<span>RITMO REQUERIDO<b>{stats['required_daily']:.1f}/dia</b><small>Fecha estimada: {stats['goal_date']}</small></span></div>",
        unsafe_allow_html=True,
    )
    xmax=max(target,stats["p90"],actual,1)*1.12
    fig=go.Figure()
    fig.add_scatter(x=[stats["p10"],stats["p90"]],y=[entity,entity],mode="lines",line=dict(color="rgba(56,189,248,.26)",width=18),name="Rango probable 80 %",hovertemplate="Rango P10–P90: %{x:,.0f}<extra></extra>")
    fig.add_bar(y=[entity],x=[actual],orientation="h",marker_color=GREEN,width=.25,name="Actual",hovertemplate="Actual: %{x:,.0f}<extra></extra>")
    fig.add_scatter(x=[projection],y=[entity],mode="markers",marker=dict(symbol="diamond",size=15,color=BLUE),name="Proyeccion P50",hovertemplate="Proyeccion mediana: %{x:,.0f}<extra></extra>")
    fig.add_scatter(x=[target],y=[entity],mode="markers",marker=dict(symbol="line-ns-open",size=29,color="white",line=dict(width=3)),name="Meta",hovertemplate="Meta: %{x:,.0f}<extra></extra>")
    fig.add_shape(type="line",x0=actual,x1=projection,y0=0,y1=0,line=dict(color=BLUE,width=3,dash="dot"))
    fig.update_layout(**_layout(240),xaxis={**AXIS,"range":[0,xmax]},yaxis=AXIS)
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})

    risk=_forecast_risk_data(scope,metas,month,cutoff,month_end,is_business_day,meta_agents)
    if not risk.empty:
        _panel_title("⚠", "Riesgo predictivo por Supervisor", "Probabilidad estimada de alcanzar la meta mensual.", "PRIORIZACION")
        risk=risk.sort_values(["Probabilidad","P50"],ascending=[False,False],na_position="first")
        colors={"Alto":RED,"Medio":AMBER,"Bajo":GREEN,"Sin meta":MUTED}
        fig=go.Figure(go.Bar(
            x=risk["Probabilidad"].fillna(0),y=risk["Supervisor"],orientation="h",
            marker_color=[colors[x] for x in risk["Riesgo"]],
            text=["Sin meta" if pd.isna(p) else f"{p:.0f}%" for p in risk["Probabilidad"]],textposition="outside",cliponaxis=False,
            customdata=risk[["Actual","Meta","P50","Riesgo"]],
            hovertemplate="<b>%{y}</b><br>Probabilidad de meta: %{x:.1f}%<br>Actual: %{customdata[0]:,.0f}<br>Meta: %{customdata[1]:,.0f}<br>Proyeccion P50: %{customdata[2]:,.0f}<br>Riesgo: %{customdata[3]}<extra></extra>",
        ))
        fig.add_vrect(x0=0,x1=40,fillcolor="rgba(244,63,94,.035)",line_width=0,layer="below")
        fig.add_vrect(x0=40,x1=75,fillcolor="rgba(245,158,11,.035)",line_width=0,layer="below")
        fig.add_vrect(x0=75,x1=100,fillcolor="rgba(16,185,129,.035)",line_width=0,layer="below")
        fig.update_layout(**_layout(max(300,len(risk)*35+90)),xaxis={**AXIS,"range":[0,108],"title":"Probabilidad de cumplir (%)"},yaxis=AXIS,showlegend=False)
        st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})


def _number_es(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _percent_es(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") + " %"


def _render_overview_kpis(base, metas, start, end, is_business_day, meta_agents=None):
    """Resumen ejecutivo del mismo universo delimitado por los filtros globales."""
    total = int(len(base))
    supervisors = sorted(x for x in base["_SUP"].unique() if x != "Sin asignar")
    months = _available_months(base)
    cutoff = min(end, date.today())
    meta = _meta_by_supervisor(
        metas, supervisors, months, start, cutoff,
        "Meta acumulada al corte", is_business_day, meta_agents,
    )
    target = float(meta["META"].sum()) if "META" in meta else 0.0
    compliance = total / target * 100 if target > 0 else np.nan
    gap = total - target
    dias_rango = _dias_habiles_rango(start, end)
    ticket = total / dias_rango if dias_rango else 0.0
    asesores_activos = base.loc[base["_AGENT"] != "Sin asignar", "_AGENT"].nunique()

    if pd.isna(compliance):
        compliance_value, compliance_detail, compliance_color = "—", "Sin meta disponible", MUTED
        progress = 0.0
    elif compliance >= 100:
        compliance_value, compliance_detail, compliance_color = _percent_es(compliance), "Meta alcanzada", GREEN
        progress = 100.0
    elif compliance >= 90:
        compliance_value, compliance_detail, compliance_color = _percent_es(compliance), "En rango de cumplimiento", AMBER
        progress = compliance
    else:
        compliance_value, compliance_detail, compliance_color = _percent_es(compliance), "Bajo la meta", RED
        progress = compliance

    if target <= 0:
        gap_value, gap_detail, gap_color = "—", "Sin meta para comparar", MUTED
    elif gap > 0:
        gap_value, gap_detail, gap_color = f"+{_number_es(gap)}", f"Superavit de {_number_es(gap)}", GREEN
    elif gap < 0:
        gap_value, gap_detail, gap_color = f"−{_number_es(abs(gap))}", f"Faltan {_number_es(abs(gap))}", RED
    else:
        gap_value, gap_detail, gap_color = "0", "Meta alcanzada", GREEN

    cards = [
        ("◎", "Total matriculas", _number_es(total), "Registros del periodo", BLUE, ""),
        ("◇", "Meta al corte", _number_es(target), f"Corte: {_pretty_date(cutoff)}", INDIGO, ""),
        ("↗", "Cumplimiento", compliance_value, compliance_detail, compliance_color,
         f"<div class='ebi-overview-track'><i style='width:{min(max(progress, 0), 100):.1f}%'></i></div>"),
        ("±", "Brecha vs meta", gap_value, gap_detail, gap_color, ""),
        ("📆", "Ticket promedio dia", f"{ticket:.1f}".replace(".", ","), f"{dias_rango} dias habiles en el rango", TEAL, ""),
        ("👤", "Asesores activos", _number_es(asesores_activos), "Con al menos una matricula", GREEN, ""),
    ]
    html_cards = "".join(
        f"<article class='ebi-overview-card' style='--accent:{color}'>"
        f"<div class='ebi-overview-head'><span>{icon}</span><b>{label}</b></div>"
        f"<strong>{value}</strong><small>{detail}</small>{extra}</article>"
        for icon, label, value, detail, color, extra in cards
    )
    st.markdown(f"<div class='ebi-overview'>{html_cards}</div>", unsafe_allow_html=True)


def _css():
    st.markdown("""
    <style>
    .ebi-top{position:relative;overflow:hidden;margin:0 0 10px;padding:19px 22px;border:1px solid rgba(56,189,248,.16);border-radius:16px;background:linear-gradient(110deg,rgba(56,189,248,.075),rgba(16,185,129,.035) 55%,rgba(129,140,248,.045));display:flex;align-items:center;justify-content:space-between;gap:24px;box-shadow:inset 0 1px 0 rgba(255,255,255,.035)}
    .ebi-top::before{content:'';position:absolute;inset:0 auto 0 0;width:3px;background:linear-gradient(180deg,#38BDF8,#34D399)}.ebi-top::after{content:'';position:absolute;width:260px;height:160px;right:-90px;top:-105px;border-radius:50%;background:radial-gradient(circle,rgba(56,189,248,.11),transparent 70%);pointer-events:none}.ebi-top-copy{position:relative;z-index:1;min-width:0}.ebi-top-context{display:flex;align-items:center;gap:7px;margin-bottom:5px;font-size:8px;font-weight:850;letter-spacing:.18em;color:#7DD3FC}.ebi-top-context i{display:block;width:18px;height:1px;background:#38BDF8}.ebi-top h1{font-family:'Space Grotesk',sans-serif!important;font-size:26px!important;line-height:1.08!important;color:white;margin:0!important}.ebi-top p{font-size:10px;color:rgba(255,255,255,.43);margin:6px 0 0}.ebi-period{position:relative;z-index:1;display:flex;flex-direction:column;align-items:flex-end;gap:3px;flex:0 0 auto;padding-left:22px;border-left:1px solid rgba(255,255,255,.09)}.ebi-period span{font-size:7px;font-weight:800;letter-spacing:.15em;color:rgba(255,255,255,.35)}.ebi-period b{font-family:'Space Grotesk',sans-serif;font-size:11px;letter-spacing:.04em;color:#7DD3FC;white-space:nowrap}
    div.st-key-mat_module_nav{margin:0 0 8px;padding:5px;border:1px solid rgba(255,255,255,.085);border-radius:13px;background:rgba(2,17,13,.55);box-shadow:0 8px 30px -26px rgba(0,0,0,.9)}div.st-key-mat_module_nav div[data-testid='stHorizontalBlock']{gap:5px}div.st-key-mat_module_nav button{min-height:39px!important;border:1px solid transparent!important;border-radius:9px!important;background:transparent!important;color:rgba(255,255,255,.62)!important;box-shadow:none!important;font-size:11px!important;font-weight:650!important;transition:background .16s,color .16s,border-color .16s!important}div.st-key-mat_module_nav button:hover{color:white!important;background:rgba(255,255,255,.045)!important;border-color:rgba(255,255,255,.075)!important}div.st-key-mat_module_nav button[kind='primary']{color:#7DD3FC!important;background:linear-gradient(135deg,rgba(56,189,248,.14),rgba(16,185,129,.08))!important;border-color:rgba(56,189,248,.22)!important;box-shadow:inset 0 -2px 0 #38BDF8!important}
    .ebi-overview{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;margin:14px 0 6px}.ebi-overview-card{position:relative;overflow:hidden;min-width:0;padding:13px 13px 12px;border-radius:13px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 10%,rgba(255,255,255,.035)),rgba(255,255,255,.018));border:1px solid rgba(255,255,255,.09);box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}.ebi-overview-card::before{content:'';position:absolute;left:0;right:0;top:0;height:2px;background:var(--accent)}.ebi-overview-head{display:flex;align-items:center;gap:7px;min-width:0}.ebi-overview-head span{display:flex;align-items:center;justify-content:center;width:22px;height:22px;flex:0 0 22px;border-radius:7px;background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--accent);font-size:11px;font-weight:900}.ebi-overview-head b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:rgba(255,255,255,.56);font-size:8px;letter-spacing:.075em;text-transform:uppercase}.ebi-overview-card>strong{display:block;margin:10px 0 2px;font-family:'Space Grotesk',sans-serif;font-size:22px;line-height:1;color:#fff}.ebi-overview-card>small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:rgba(255,255,255,.40);font-size:8px}.ebi-overview-track{height:3px;margin-top:9px;border-radius:99px;background:rgba(255,255,255,.08);overflow:hidden}.ebi-overview-track i{display:block;height:100%;border-radius:inherit;background:var(--accent)}
    .ebi-section{display:flex;align-items:center;gap:10px;margin:22px 0 9px}.ebi-section span{font-size:9px;font-weight:800;letter-spacing:.16em;color:#38BDF8}.ebi-section b{font-family:'Space Grotesk',sans-serif;font-size:15px;color:white}.ebi-section i{height:1px;flex:1;background:linear-gradient(90deg,rgba(255,255,255,.14),transparent)}
    .ebi-head{display:flex;align-items:center;gap:11px;margin:10px 0 5px;padding:10px 12px;border-left:2px solid #38BDF8;background:linear-gradient(90deg,rgba(56,189,248,.07),transparent);border-radius:0 12px 12px 0}.ebi-icon{width:31px;height:31px;display:flex;align-items:center;justify-content:center;border-radius:9px;background:rgba(255,255,255,.07)}.ebi-copy{flex:1}.ebi-title{font-family:'Space Grotesk',sans-serif;font-size:14px;font-weight:700;color:#fff}.ebi-sub{font-size:10px;color:rgba(255,255,255,.43);margin-top:2px}.ebi-tag{font-size:8px;font-weight:800;letter-spacing:.10em;color:#7DD3FC;border:1px solid rgba(56,189,248,.24);border-radius:99px;padding:4px 8px}
    .ebi-kpis,.ebi-forecast{display:flex;gap:10px;margin:8px 0}.ebi-kpis span,.ebi-forecast span{flex:1;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:8px 12px;font-size:9px;letter-spacing:.08em;color:rgba(255,255,255,.45)}.ebi-kpis b,.ebi-forecast b{font-family:'Space Grotesk',sans-serif;font-size:17px;margin-right:7px;color:white}.ebi-forecast span{display:flex;flex-direction:column;gap:4px}.ebi-forecast b{font-size:22px;margin:0}.ebi-forecast small{font-size:8px;letter-spacing:0;color:rgba(255,255,255,.35)}.ebi-forecast-predictive{display:grid;grid-template-columns:repeat(6,minmax(0,1fr))}.ebi-forecast-predictive span{min-width:0}.ebi-forecast-predictive b{font-size:18px;white-space:nowrap}
    .ebi-selected{display:flex;flex-wrap:wrap;gap:6px;margin:2px 0 7px}.ebi-selected span{font-size:9px;color:rgba(255,255,255,.58);padding:3px 7px;border:1px solid rgba(255,255,255,.08);border-radius:99px;background:rgba(255,255,255,.025)}.ebi-selected span::first-letter{color:var(--dot)}
    .ebi-inc-scroll{max-height:560px;overflow-y:auto;padding:2px 6px 2px 1px;scrollbar-width:thin;scrollbar-color:rgba(148,163,184,.35) transparent}.ebi-incident{position:relative;display:flex;gap:10px;margin:0 0 9px;padding:13px 12px;border-radius:12px;background:linear-gradient(120deg,rgba(255,255,255,.045),rgba(255,255,255,.018));border:1px solid rgba(255,255,255,.07);border-left:3px solid var(--incident);box-shadow:0 8px 22px -18px rgba(0,0,0,.9)}.ebi-incident.warning{--incident:#F59E0B}.ebi-incident.critical{--incident:#F43F5E}.ebi-inc-dot{color:var(--incident);font-size:10px;padding-top:3px}.ebi-inc-body{min-width:0;flex:1}.ebi-inc-name{font-size:12px;font-weight:750;color:rgba(255,255,255,.94);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ebi-inc-sup{font-size:9px;color:rgba(255,255,255,.40);margin:2px 0 9px}.ebi-inc-main{display:flex;flex-direction:column;gap:2px}.ebi-inc-main strong{font-family:'Space Grotesk',sans-serif;font-size:13px;color:white}.ebi-inc-main span{font-size:9px;color:rgba(255,255,255,.52)}.ebi-inc-foot{display:flex;gap:12px;flex-wrap:wrap;margin-top:9px;padding-top:7px;border-top:1px solid rgba(255,255,255,.06);font-size:8px;color:rgba(255,255,255,.38)}.ebi-inc-foot b{color:rgba(255,255,255,.70)}.ebi-inc-badge{align-self:flex-start;font-size:7px;font-weight:850;letter-spacing:.08em;color:var(--incident);background:color-mix(in srgb,var(--incident) 10%,transparent);border:1px solid color-mix(in srgb,var(--incident) 28%,transparent);border-radius:99px;padding:3px 6px;white-space:nowrap}
    @media(max-width:1100px){.ebi-overview,.ebi-forecast-predictive{grid-template-columns:repeat(3,minmax(0,1fr))}.ebi-inc-scroll{max-height:500px}.ebi-forecast:not(.ebi-forecast-predictive){flex-wrap:wrap}.ebi-forecast:not(.ebi-forecast-predictive) span{min-width:42%}}
    @media(max-width:720px){.ebi-top{align-items:flex-start;flex-direction:column;gap:13px}.ebi-period{align-items:flex-start;padding:0;border-left:0}.ebi-overview{grid-template-columns:repeat(2,minmax(0,1fr))}}
    div[data-testid='stVerticalBlockBorderWrapper']{border-color:rgba(255,255,255,.08)!important;background:rgba(255,255,255,.018)!important;border-radius:16px!important}
    </style>
    """,unsafe_allow_html=True)


def render(base, metas, fecha_ini, fecha_fin, tabla, total_general, render_table, is_business_day, global_supervisor="Todos", global_agent="Todos", base_roster=None):
    _css(); d=_prepare(base)
    d_roster=_prepare(base_roster) if base_roster is not None else d
    st.markdown(
        f"<div class='ebi-top'><div class='ebi-top-copy'>"
        f"<div class='ebi-top-context'><i></i>MATRICULAS</div>"
        f"<h1>Centro de Operaciones</h1>"
        f"<p>Produccion, capacidad, riesgo y cierre proyectado</p></div>"
        f"<div class='ebi-period'><span>PERIODO ANALIZADO</span>"
        f"<b>{_pretty_date(fecha_ini)} — {_pretty_date(fecha_fin)}</b></div></div>",
        unsafe_allow_html=True,
    )
    root=Path(__file__).resolve().parent.parent
    home_pg=st.Page(str(root/"home.py"),title="Inicio",icon="🏠",default=True)
    insc_pg=st.Page(str(root/"pages/1_Inscripciones.py"),title="Inscripciones",icon="📝")
    quart_pg=st.Page(str(root/"pages/3_Cuartiles.py"),title="Cuartiles",icon="🏆")
    rt_pg=st.Page(str(root/"pages/4_Contactabilidad.py"),title="Real time",icon="📞")
    with st.container(key="mat_module_nav"):
        n1,n2,n3,n4,n5=st.columns(5)
        with n1:
            if st.button("⌂  Inicio",key="mat_v2_nav_home",width="stretch"): st.switch_page(home_pg)
        with n2:
            if st.button("▤  Inscripciones",key="mat_v2_nav_ins",width="stretch"): st.switch_page(insc_pg)
        with n3: st.button("◆  Matriculas",key="mat_v2_nav_mat",width="stretch",type="primary")
        with n4:
            if st.button("◇  Cuartiles",key="mat_v2_nav_q",width="stretch"): st.switch_page(quart_pg)
        with n5:
            if st.button("●  Real time",key="mat_v2_nav_rt",width="stretch"): st.switch_page(rt_pg)
    if d.empty:
        st.warning("No hay matriculas dentro de los filtros globales seleccionados."); return
    meta_agents=[global_agent] if global_agent!="Todos" else None
    _render_overview_kpis(d,metas,fecha_ini,fecha_fin,is_business_day,meta_agents)
    _section("A", "MONITOREO")
    with st.container(border=True): _render_supervisor(d,metas,fecha_ini,fecha_fin,is_business_day,meta_agents)
    with st.container(border=True): _render_coordinator(d,metas,fecha_ini,fecha_fin,is_business_day,meta_agents)
    _section("B", "PRODUCCION")
    with st.container(border=True): _render_weekday(d,is_business_day)
    with st.container(border=True): _render_trend(d)
    _section("C", "CONTROL")
    with st.container(border=True):
        _panel_title("📋","Matriculas por Supervisor","Tabla operativa conservada sin cambios de estructura ni calculo.",f"{len(tabla)} SUPERVISORES")
        render_table(tabla,total_general)
    with st.container(border=True): _render_gap(d,metas,fecha_ini,fecha_fin,is_business_day,meta_agents)
    _section("D", "SEGUIMIENTO OPERATIVO")
    with st.container(border=True): _render_matrices(d,d_roster,is_business_day,global_supervisor)
    _section("E", "ANALISIS")
    with st.container(border=True): _render_analysis(d,metas,fecha_ini,fecha_fin,is_business_day,meta_agents)
    with st.container(border=True): _render_projection(d,metas,fecha_ini,fecha_fin,is_business_day,meta_agents)
    with st.container(border=True): _render_predictive(d,metas,fecha_ini,fecha_fin,is_business_day,meta_agents)


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
# _FECHA, AÑO, MES y DÍA se derivan de "Fecontab" (fecha de contabilización) dentro de _cargar_base.

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

    def _bounds_mes(mes_nombre: str):
        """Primer y último día del mes calendario `mes_nombre` (año del último dato)."""
        if mes_nombre not in _MES_ORDEN:
            return None
        mnum = _MES_ORDEN.index(mes_nombre) + 1
        yr = f_max.year
        return date(yr, mnum, 1), date(yr, mnum, calendar.monthrange(yr, mnum)[1])

    def _sincronizar_fechas_con_filtro(columna: str, valor_key: str):
        """Al elegir Cohorte/Mes, el rango de fechas salta a cubrir ese filtro —
        si no, el rango puede quedar sin intersección con la selección (o al revés,
        volver a abrirse a años de historial) y la tabla/gráficos salen vacíos o sucios.

        Con **Mes** salta al mes calendario COMPLETO: la tabla Avance vs. Meta muestra
        la meta del mes entero aunque estemos a mitad de mes; para verla con corte a la
        fecha se ajusta Desde/Hasta a mano (dentro del mes). Con **Cohorte** —etiqueta
        no derivada de la fecha— salta al rango real de fechas de esa cohorte."""
        valor = st.session_state.get(valor_key)
        if columna == "MES":
            b = _bounds_mes(valor) if valor and valor != "Todos" else None
            st.session_state["fecha_ini_widget"], st.session_state["fecha_fin_widget"] = b or (f_ini_default, f_max)
            return
        if not valor or valor == "Todos":
            return
        fechas_sub = base_full.loc[base_full[columna] == valor, "_FECHA"].dropna().dt.date
        fechas_recientes = fechas_sub[fechas_sub >= _cutoff_operativo]
        objetivo = fechas_recientes if len(fechas_recientes) else fechas_sub
        if len(objetivo):
            st.session_state["fecha_ini_widget"] = objetivo.min()
            st.session_state["fecha_fin_widget"] = objetivo.max()

    # Con un Mes elegido, el selector de Período solo permite días de ese mes.
    _mes_activo = st.session_state.get("mes_sel_widget", "Todos")
    _bm = _bounds_mes(_mes_activo) if _mes_activo != "Todos" else None
    picker_min, picker_max = _bm if _bm else (f_min, f_max)

    st.session_state.setdefault("fecha_ini_widget", f_ini_default)
    st.session_state.setdefault("fecha_fin_widget", f_max)
    if not (picker_min <= st.session_state["fecha_ini_widget"] <= picker_max):
        st.session_state["fecha_ini_widget"] = picker_min
    if not (picker_min <= st.session_state["fecha_fin_widget"] <= picker_max):
        st.session_state["fecha_fin_widget"] = picker_max
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_ini = st.date_input("Desde", min_value=picker_min, max_value=picker_max, key="fecha_ini_widget")
    with col_f2:
        fecha_fin = st.date_input("Hasta", min_value=picker_min, max_value=picker_max, key="fecha_fin_widget")

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

    coordinadores = ["Todos"] + sorted(c for c in base_full["_COORDINADOR"].unique().tolist() if c and c != "Sin asignar")
    coord_sel = st.selectbox("Coordinador", coordinadores)

    supervisores = ["Todos"] + sorted(base_full["_SUPERVISOR"].unique().tolist())
    sup_sel = st.selectbox("Supervisor", supervisores)

    expertos = ["Todos"] + sorted(e for e in base_full["_ASESOR"].unique().tolist() if e and e != "Sin asignar")
    experto_sel = st.selectbox("Experto asignado", expertos)

    niveles = ["Todos"] + sorted(base_full["Nivel Formación"].replace("", pd.NA).dropna().unique().tolist())
    nivel_sel = st.selectbox("Nivel", niveles)

    programas = ["Todos"] + sorted(base_full["Programa"].replace("", pd.NA).dropna().unique().tolist())
    prog_sel = st.selectbox("Programa", programas)

    periodos = ["Todos"] + sorted(base_full["PERIODO ACADEMICO"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist())
    periodo_sel = st.selectbox("Periodo académico", periodos)

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
def _mask_filtros(df: pd.DataFrame, *, incluir_mes: bool = True) -> pd.Series:
    """Máscara de los filtros del sidebar (sin el recorte Desde/Hasta). Con
    `incluir_mes=False` se omite el filtro de Mes: así el roster de supervisores/
    asesores (quién existe) no depende de qué mes se esté mirando — solo los
    valores del heatmap dependen del mes."""
    m = pd.Series(True, index=df.index)
    if cohorte_sel != "Todos":
        m &= df["COHORTE"] == cohorte_sel
    if incluir_mes and mes_sel != "Todos":
        m &= df["MES"] == mes_sel
    if coord_sel != "Todos":
        m &= df["_COORDINADOR"] == coord_sel
    if sup_sel != "Todos":
        m &= df["_SUPERVISOR"] == sup_sel
    if experto_sel != "Todos":
        m &= df["_ASESOR"] == experto_sel
    if nivel_sel != "Todos":
        m &= df["Nivel Formación"] == nivel_sel
    if prog_sel != "Todos":
        m &= df["Programa"] == prog_sel
    if periodo_sel != "Todos":
        m &= df["PERIODO ACADEMICO"].astype(str).str.strip() == periodo_sel
    return m


b = base_full.copy()
mask = _mask_filtros(b) & (b["_FECHA"].dt.date >= fecha_ini) & (b["_FECHA"].dt.date <= fecha_fin)
b = b[mask].copy()

# Universo de supervisores/asesores para las matrices (Sección D): sin recorte de
# fecha ni de mes, para que quien no matriculó en el periodo/mes elegido siga
# apareciendo en la fila (con ceros) en vez de desaparecer.
b_roster = base_full[_mask_filtros(base_full, incluir_mes=False)].copy()

_base_avance = base_full
if cohorte_sel != "Todos":
    _base_avance = _base_avance[_base_avance["COHORTE"] == cohorte_sel]
if mes_sel != "Todos":
    _base_avance = _base_avance[_base_avance["MES"] == mes_sel]
_base_avance = _base_avance[(_base_avance["_FECHA"].dt.date >= fecha_ini) & (_base_avance["_FECHA"].dt.date <= fecha_fin)]
tabla, total_general = _tabla_avance(_base_avance, metas_full, fecha_ini, fecha_fin)

# Vista Executive BI integrada en esta página. La carga, los filtros globales y
# la tabla de avance continúan trabajando sobre el mismo subconjunto filtrado.
render(
    base=b,
    metas=metas_full,
    fecha_ini=fecha_ini,
    fecha_fin=fecha_fin,
    tabla=tabla,
    total_general=total_general,
    render_table=_render_tabla_avance,
    is_business_day=_es_habil,
    global_supervisor=sup_sel,
    global_agent=experto_sel,
    base_roster=b_roster,
)
st.stop()
