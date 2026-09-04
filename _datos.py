"""Carga central de datos del Dashboard Operativo.

Todas las hojas de Google Sheets se descargan aquí, una sola vez, y se comparten
entre los 5 módulos (misma función cacheada → mismo caché de proceso).

· Descargas en paralelo (ThreadPool) — Matrículas baja 16 hojas a la vez.
· Caché en disco y SIN expiración automática: los datos quedan fijos hasta que
  el usuario pulse "🔄 Actualizar datos" (botón en cada sidebar).
"""

from __future__ import annotations

import concurrent.futures as _cf
import io
import unicodedata
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────
# IDENTIFICADORES DE HOJAS
# ─────────────────────────────────────────────
ID_INSCRIPCIONES = "14DOLvF_d-qhd-VBE62M6hnfqtOH3EYcggjBLgwHiC8w"
ID_METAS = "1byJ5Sw_P_xKew5xMbWz9KQSTQfc_J-Fm"
ID_LEADS = "1eJYJxr_9qOF4yTLjXU1fr1P9asoXdnzoY_MkWME9FhY"
ID_REALTIME = "1PRMsfsyAX60Ob6w4dBlVpl9yuivF2As_yPvfi9gJI6E"

# Base de matrículas: un archivo por mes. Cada uno trae la pestaña "Base" (matrículas del mes)
# y una pestaña "<Mes>" con el directorio de expertos (SIU, Agente, Documento, Supervisor,
# Coordinador). Al agregar un mes nuevo: compartirlo como "Cualquier persona con el enlace"
# (igual que los anteriores) y sumar su doc_id aquí.
SHEETS_MATRICULAS_MES = {
    "Enero":      "1q3VOEoaL07fkXxom-TP3ylKbV3m-o5AkZwEslEFC7Uc",
    "Febrero":    "13BPLLx18MEN_Ot3n9OzvjY63gVoFypAvLcrf0F2YN1M",
    "Marzo":      "1xeoMksfjbG6iopExDh9puhhMimo--xdyCcHayXJn_bQ",
    "Abril":      "1j_LsMWCYM291jm4TgRPNsWO3-vHrfH8xgtS-4cYTAnY",
    "Mayo":       "18oxEZZ4AEgivWysIYWcXb0vsJ6ZoqeqRMAMgAOb1XZo",
    "Junio":      "1vEhb7-DqJh8wFmR2MRzbCyzRX3hX-LGj38buxtc7vY8",
    "Julio":      "1WxvZXQqnNDg3fRpA3xoK4CzEb0y8XdXgknTvx3rHyOk",
    "Agosto":     "1-PwX6_PGhRJJiG4FD_1dqHDSG9jGNbBVsMpg-WOBv1c",
    "Septiembre": "1x9rz0v8sjKnjooXX1a0qwil3TivYNuMVttzp7gum44A",
}

_MES_ORDEN = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
_MES_A_NUM = {mes: i + 1 for i, mes in enumerate(_MES_ORDEN)}
_MES_ABREV = {
    "ene": "Enero", "feb": "Febrero", "mar": "Marzo", "abr": "Abril", "may": "Mayo",
    "jun": "Junio", "jul": "Julio", "ago": "Agosto", "sep": "Septiembre",
    "oct": "Octubre", "nov": "Noviembre", "dic": "Diciembre",
}
_VACIO = {"", "nan", "none", "#n/d", "#n/a", "#value!", "#ref!", "<na>"}

# `persist="disk"` → sobrevive reinicios de la app. Sin `ttl` → no expira solo.
_CACHE = dict(show_spinner="Descargando datos…", persist="disk")


# ─────────────────────────────────────────────
# DESCARGA
# ─────────────────────────────────────────────
def _url(sheet_id: str, hoja: str, tq: str | None = None) -> str:
    u = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(hoja)}"
    )
    if tq:
        u += "&tq=" + urllib.parse.quote(tq)
    return u


def _leer(sheet_id: str, hoja: str, tq: str | None = None, **kwargs) -> pd.DataFrame:
    # Descargar los bytes primero y luego parsear: `pd.read_csv(url)` sobre hojas grandes
    # (la de Inscripciones pesa ~60 MB) se cuelga / corta la conexión con gviz.
    req = urllib.request.Request(_url(sheet_id, hoja, tq), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
    df = pd.read_csv(io.BytesIO(raw), encoding="utf-8", low_memory=False, **kwargs)
    df.columns = df.columns.str.strip()
    return df


def _leer_paralelo(specs: list[tuple]) -> list[pd.DataFrame | None]:
    """specs = [(sheet_id, hoja, kwargs_dict), ...] → DataFrames en el mismo orden.
    Si una hoja falla (sin compartir, tab renombrado, etc.) queda `None` en su
    lugar en vez de tumbar toda la descarga — quien llama decide qué hacer."""
    out: list = [None] * len(specs)
    with _cf.ThreadPoolExecutor(max_workers=min(16, len(specs))) as ex:
        fut = {ex.submit(_leer, sid, hoja, **kw): i for i, (sid, hoja, kw) in enumerate(specs)}
        for f in _cf.as_completed(fut):
            try:
                out[fut[f]] = f.result()
            except Exception:
                out[fut[f]] = None
    return out


# ─────────────────────────────────────────────
# HELPERS DE TEXTO
# ─────────────────────────────────────────────
def _norm(s) -> str:
    """minúsculas, sin tildes, espacios colapsados — para cruzar llaves entre hojas."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _valido(s) -> bool:
    return _norm(s) not in _VACIO


def norm_cohorte(valor) -> str:
    """'Sep-26' / 'jul-26' / 'Julio-2026' → 'Septiembre-2026' / 'Julio-2026'."""
    s = str(valor).strip()
    if not _valido(s):
        return ""
    izq = s.split("-")[0].strip().lower()
    if izq[:3] in _MES_ABREV:
        mes = _MES_ABREV[izq[:3]]
    elif izq.capitalize() in _MES_A_NUM:
        mes = izq.capitalize()
    else:
        return s
    anio = "".join(c for c in s.split("-")[-1] if c.isdigit()) or "26"
    if len(anio) == 2:
        anio = "20" + anio
    return f"{mes}-{anio}"


# ─────────────────────────────────────────────
# LOADERS CACHEADOS
# ─────────────────────────────────────────────
@st.cache_data(**_CACHE)
def metas() -> pd.DataFrame:
    df = _leer(ID_METAS, "Consolidado")
    df["_CC"] = pd.to_numeric(df["CC"], errors="coerce").astype("Int64")
    return df


# No cuentan como inscripción los registros con SUB ESTADO cancelado o rechazado.
SUB_ESTADO_EXCLUIDOS = {"cancelada", "cancelado", "rechazado", "rechazada"}


@st.cache_data(**_CACHE)
def inscripciones() -> pd.DataFrame:
    """Base de Inscripciones. Solo desde enero 2026 y sin SUB ESTADO cancelado/rechazado.

    El recorte a 2026 se pide a Google en la consulta (columna X = FECHA_INSCRIPCION):
    la hoja completa pesa ~60 MB / 112k filas; con el filtro baja a ~34 MB / 60k y
    `pd.read_csv` deja de cortar la conexión.
    """
    try:
        df = _leer(ID_INSCRIPCIONES, "Base", tq="SELECT * WHERE X >= date '2026-01-01'")
        if df.empty:
            raise ValueError("consulta filtrada devolvió 0 filas")
    except Exception:
        df = _leer(ID_INSCRIPCIONES, "Base")  # respaldo: traer todo y filtrar aquí

    anio = pd.to_numeric(df["AÑO"], errors="coerce")
    sub = df["SUB ESTADO"].astype(str).str.strip().str.lower()
    df = df[(anio >= 2026) & ~sub.isin(SUB_ESTADO_EXCLUIDOS)].copy()
    df["_FECHA_INSC"] = pd.to_datetime(df["FECHA_INSCRIPCION"], errors="coerce", dayfirst=True)
    return df


@st.cache_data(**_CACHE)
def leads() -> pd.DataFrame:
    df = _leer(ID_LEADS, "Resumen diario")
    df["_FECHA"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["_FECHA"]).copy()
    df["_USUARIO"] = df["Usuario"].astype(str).str.strip().str.lower()
    df["_NOMBRE"] = df["Nombre"].fillna(df["Usuario"])
    df["_CC"] = pd.to_numeric(df["Cedula"], errors="coerce").astype("Int64")
    df["_INSUMO"] = pd.to_numeric(df["Leads asignados ese día"], errors="coerce").fillna(0).astype(int)
    df["MES"] = df["_FECHA"].dt.month.map(lambda m: _MES_ORDEN[int(m) - 1])
    df["AÑO"] = df["_FECHA"].dt.year
    return df


# ─────────────────────────────────────────────
# REAL TIME — log de llamadas (una fila por llamada)
# ─────────────────────────────────────────────
# Disposiciones que NO son gestión del asesor (el pivot las excluye del "Total Llamadas").
_RT_NO_GESTION = {"no encontrado", "llamada entrante", "sin dato"}


def _rt_a_segundos(s: pd.Series) -> pd.Series:
    """'H:MM:SS' o 'MM:SS' → segundos."""
    p = s.astype(str).str.strip().str.split(":", expand=True).apply(pd.to_numeric, errors="coerce")
    if p.shape[1] == 3:
        return (p[0].fillna(0) * 3600 + p[1].fillna(0) * 60 + p[2].fillna(0)).astype(float)
    if p.shape[1] == 2:
        return (p[0].fillna(0) * 60 + p[1].fillna(0)).astype(float)
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


# RT Day / RT Yesterday: 60 columnas, la fila 1 puede venir SIN encabezado (el dueño la
# quita/pone). Se leen SIN `tq=SELECT` (esa consulta dispara un recálculo carísimo si la hoja
# tiene fórmulas vivas) y se recortan las 14 columnas necesarias por POSICIÓN, en pandas.
_RT_USECOLS = [0, 2, 4, 8, 25, 26, 28, 51, 52, 53, 56, 57, 58, 59]
_RT_NAMES = ["Fecha de inicio", "Campaña", "Agente", "Aten.", "Tiempo atención", "Tiempo Conc.",
             "Disp.", "Asesor", "Supervisor", "Day of Week", "Disposición Agrupada",
             "Tiempo Ocio", "Tiempo Gestión", "Tip Contacto"]


def _rt_base(tab: str) -> pd.DataFrame:
    df = pd.read_csv(_url(ID_REALTIME, tab), header=None, skiprows=1,
                     usecols=_RT_USECOLS, names=_RT_NAMES, encoding="utf-8", low_memory=False)
    df["_INICIO"] = pd.to_datetime(df["Fecha de inicio"], errors="coerce")
    df = df.dropna(subset=["_INICIO"]).copy()
    df["_FECHA"] = df["_INICIO"].dt.date
    df["_HORA"] = df["_INICIO"].dt.hour
    _sin = {"", "no encontrado", "nan", "none", " "}
    df["_ASESOR"] = df["Asesor"].astype(str).str.strip()
    df["_ASESOR"] = df["_ASESOR"].where(~df["_ASESOR"].str.lower().isin(_sin), "Sin asignar")
    df["_SUPERVISOR"] = df["Supervisor"].astype(str).str.strip()
    df["_SUPERVISOR"] = df["_SUPERVISOR"].where(~df["_SUPERVISOR"].str.lower().isin(_sin), "Sin asignar")
    df["_DISPOSICION"] = df["Disposición Agrupada"].fillna("Sin dato").astype(str).str.strip()
    df["_GESTIONADA"] = ~df["_DISPOSICION"].str.lower().isin(_RT_NO_GESTION)
    df["_CONTESTADA"] = df["Aten."].astype(str).str.strip().str.lower().eq("si")
    df["_EFECTIVO"] = df["Tip Contacto"].astype(str).str.strip().str.lower().isin({"efectivo", "perfilamiento", "permanencia"})
    df["_SEG_LLAMADA"] = _rt_a_segundos(df["Tiempo atención"])
    df["_SEG_OCIO"] = _rt_a_segundos(df["Tiempo Ocio"])
    df["_SEG_TIPIF"] = _rt_a_segundos(df["Tiempo Conc."])
    df["_BUCKET"] = (
        df["Tiempo Gestión"].astype(str).str.strip().str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .map(RT_BUCKETS_MAP).fillna("—")
    )
    return df


RT_BUCKETS = ["Menor 2 Min", "Entre 2 y 5 Min", "Entre 5 y 8 Min",
              "Entre 8 y 10 Min", "Entre 10 y 14 Min", "Mayor a 14 Min"]
RT_BUCKETS_MAP = {
    "menor 2 min": "Menor 2 Min", "entre 2 y 5 min": "Entre 2 y 5 Min",
    "entre 5 y 8 min": "Entre 5 y 8 Min", "entre 8 y 10 min": "Entre 8 y 10 Min",
    "entre 10 y 14 min": "Entre 10 y 14 Min", "mayor a 14 min": "Mayor a 14 Min",
}


@st.cache_data(**_CACHE)
def realtime_socio() -> set:
    """Nombres de asesores en formación (pestaña 'Socio') → STATUS = OJT; el resto = Operación."""
    try:
        d = _leer(ID_REALTIME, "Socio")
        return {str(n).strip() for n in d["Agente"].dropna() if str(n).strip()}
    except Exception:
        return set()


@st.cache_data(**_CACHE)
def realtime_inscripciones() -> pd.DataFrame:
    """Pestaña 'Inscripciones' — resumen de inscripción/completada por asesor del día
    (fuente del SIU, no del log de llamadas). Se cruza por nombre de asesor."""
    try:
        d = _leer(ID_REALTIME, "Inscripciones")
    except Exception:
        return pd.DataFrame(columns=["_ASESOR", "INSCRIPCION", "COMPLETADA", "CANCELADA"])
    d["_ASESOR"] = d["Nombre Asesor"].astype(str).str.strip()
    for orig, col in [("Inscripción", "INSCRIPCION"), ("Completada", "COMPLETADA"), ("Cancelada", "CANCELADA")]:
        d[col] = pd.to_numeric(d.get(orig), errors="coerce").fillna(0).astype(int)
    return d[["_ASESOR", "INSCRIPCION", "COMPLETADA", "CANCELADA"]].drop_duplicates("_ASESOR")


@st.cache_data(**_CACHE)
def realtime_hoy() -> pd.DataFrame:
    """Log de llamadas del día en curso (pestaña 'RT Day')."""
    return _rt_base("RT Day")


@st.cache_data(**_CACHE)
def realtime_ayer() -> pd.DataFrame:
    """Log de llamadas del último día hábil cerrado (pestaña 'RT Yesterday')."""
    return _rt_base("RT Yesterday")


def _directorio_maestro(dirs: list[pd.DataFrame]) -> dict:
    """Une las pestañas de directorio en un mapa de experto: por usuario SIU y por nombre."""
    por_siu, por_agente = {}, {}
    for d in dirs:
        if d is None or not {"SIU", "Agente", "Supervisor", "Coordinador"}.issubset(d.columns):
            continue  # la pestaña no existe → gviz devolvió otra hoja
        doc_col = "Documento del agente" if "Documento del agente" in d.columns else None
        for m in d.to_dict("records"):
            agente = str(m.get("Agente", "")).strip()
            if not _valido(agente):
                continue
            rec = {
                "asesor": agente,
                "documento": str(m.get(doc_col, "")).strip() if doc_col else "",
                "supervisor": str(m.get("Supervisor", "")).strip(),
                "coordinador": str(m.get("Coordinador", "")).strip(),
            }
            siu = m.get("SIU", "")
            if _valido(siu):
                por_siu[_norm(siu)] = rec
            por_agente[_norm(agente)] = rec
    return {"siu": por_siu, "agente": por_agente}


@st.cache_data(**_CACHE)
def matriculas() -> pd.DataFrame:
    """Base de Matrículas: un archivo por mes (SHEETS_MATRICULAS_MES) + directorio
    maestro de expertos.

    Todas las filas de "Base" son matrículas y se conservan. El experto/supervisor/
    coordinador se resuelven contra el directorio maestro por "Usuario SIU" → "Usuario"
    → nombre de "EXPERTO ASIGNADO". Lo no encontrado queda "Sin asignar".
    """
    meses_ids = SHEETS_MATRICULAS_MES
    _meses = list(meses_ids.keys())
    specs = [(sid, "Base", {}) for sid in meses_ids.values()]
    specs += [(sid, mes, {"dtype": str}) for mes, sid in meses_ids.items()]
    frames = _leer_paralelo(specs)
    n = len(meses_ids)
    bases, dirs = frames[:n], frames[n:]

    # Un mes cuya hoja falle (p. ej. recién agregado y sin compartir aún) se
    # descarta en vez de tumbar los demás — aparece solo apenas se comparta.
    _ok = [i for i in range(n) if bases[i] is not None and dirs[i] is not None]
    if len(_ok) < n:
        _meses = [_meses[i] for i in _ok]
        bases = [bases[i] for i in _ok]
        dirs = [dirs[i] for i in _ok]

    for mes, b in zip(_meses, bases):
        b["_ARCHIVO_MES"] = mes
    df = pd.concat(bases, ignore_index=True)
    dirm = _directorio_maestro(dirs)

    # ── resolución vectorizada ──
    k_siu = df["Usuario SIU"].map(_norm)
    k_usr = df.get("Usuario", pd.Series("", index=df.index)).map(_norm)
    k_ea = df["EXPERTO ASIGNADO"].map(_norm)
    k_exp = df.get("Experto", pd.Series("", index=df.index)).map(_norm)

    invalida = k_siu.isin(_VACIO)
    key = k_siu.mask(invalida, k_usr)

    rec = key.map(dirm["siu"])
    rec = rec.where(rec.notna(), k_ea.map(dirm["agente"]))
    rec = rec.where(rec.notna(), k_exp.map(dirm["agente"]))

    def _campo(nombre, respaldo):
        val = rec.map(lambda r: r[nombre] if isinstance(r, dict) and r[nombre] else None)
        return val.fillna(respaldo).replace("", respaldo)

    ea_txt = df["EXPERTO ASIGNADO"].fillna("").astype(str).str.strip()
    df["_ASESOR"] = _campo("asesor", "").where(lambda s: s.ne(""), ea_txt).replace("", "Sin asignar")
    df["_SUPERVISOR"] = _campo("supervisor", "Sin asignar")
    df["_COORDINADOR"] = _campo("coordinador", "Sin asignar")
    df["_DOC_ASESOR"] = rec.map(lambda r: r["documento"] if isinstance(r, dict) else "").fillna("")
    df["_CC"] = pd.to_numeric(df["_DOC_ASESOR"], errors="coerce").astype("Int64")

    # ── columnas derivadas ──
    df["NOMBRE_COMPLETO"] = (
        df["Matriculado"].where(df["Matriculado"].map(_valido), df.get("NOMBRE"))
        .fillna("Sin nombre").astype(str).str.strip()
    )
    df["Cedula"] = df["CEDULA"]                        # el detalle espera la cédula del alumno
    df["Nivel Formación"] = df["Nivel"].where(df["Nivel"].map(_valido), df.get("NIVEL")).fillna("").astype(str).str.strip()
    df["Programa"] = df["Programa"].where(df["Programa"].map(_valido), df.get("PROGRAMA")).fillna("").astype(str).str.strip()
    df["COHORTE"] = df["Cohorte"].map(norm_cohorte).replace("", "Sin cohorte")

    df["_FECHA"] = pd.to_datetime(df["Fecontab"], format="%d/%m/%Y", errors="coerce")
    df["Fecha Contabilización"] = df["_FECHA"].dt.strftime("%d/%m/%Y")
    df["AÑO"] = df["_FECHA"].dt.year
    df["MES"] = df["_FECHA"].dt.month.map(lambda x: _MES_ORDEN[int(x) - 1] if pd.notna(x) else None)
    df["DÍA"] = df["_FECHA"].dt.day
    return df


# ─────────────────────────────────────────────
# CIFRA DE PORTADA — se calcula SOLO para el módulo enfocado (carga perezosa)
# ─────────────────────────────────────────────
def _serie_por_dia(dias: pd.Series) -> list[int]:
    dias = pd.to_numeric(dias, errors="coerce").dropna()
    if not len(dias):
        return []
    return [int((dias == x).sum()) for x in range(1, int(dias.max()) + 1)][-18:]


@st.cache_data(**_CACHE)
def cifra_modulo(key: str) -> dict:
    """Cifra destacada + mini-serie de UN módulo. Cacheada por clave: el home
    solo pide la del módulo seleccionado, así no descarga las 3 bases de golpe.

    Inscripciones/Matrículas usan el último mes con datos (no el calendario):
    a comienzos de mes la operación todavía reporta el mes anterior.
    """
    r = {"cifra": "—", "sub": "sin datos", "serie": []}
    try:
        if key == "insc":
            d = inscripciones()
            f = d["_FECHA_INSC"].dropna()
            if len(f):
                ref = f.max()
                m = d[d["_FECHA_INSC"].dt.to_period("M") == ref.to_period("M")]
                r["cifra"] = f"{len(m):,}".replace(",", ".")
                r["sub"] = f"inscripciones · {_MES_ORDEN[ref.month - 1].lower()}"
                r["serie"] = _serie_por_dia(m["_FECHA_INSC"].dt.day)

        elif key in ("mat", "cuart"):
            d = matriculas()
            fe = d["_FECHA"].dropna()
            if len(fe):
                ref = fe.max()
                m = d[d["_FECHA"].dt.to_period("M") == ref.to_period("M")]
                r["serie"] = _serie_por_dia(m["DÍA"])
                mes = _MES_ORDEN[ref.month - 1].lower()
                if key == "mat":
                    r["cifra"] = f"{len(m):,}".replace(",", ".")
                    r["sub"] = f"matrículas · {mes}"
                else:
                    exp = m.loc[m["_ASESOR"] != "Sin asignar", "_ASESOR"].nunique()
                    r["cifra"] = str(int(exp))
                    r["sub"] = f"expertos con matrícula · {mes}"

        elif key == "cont":
            d = realtime_hoy()
            if len(d):
                g = d[d["_GESTIONADA"]]
                pct = (g["_EFECTIVO"].sum() / len(g) * 100) if len(g) else 0
                r["cifra"] = f"{pct:.0f}%"
                r["sub"] = f"{len(g):,} llamadas · hoy".replace(",", ".")
                por_hora = g.groupby("_HORA").size()
                r["serie"] = [int(por_hora.get(h, 0)) for h in range(6, 21)]
    except Exception:
        pass
    return r


# ─────────────────────────────────────────────
# BOTÓN DE ACTUALIZACIÓN (para el sidebar de cada módulo)
# ─────────────────────────────────────────────
def boton_actualizar() -> None:
    if st.sidebar.button("🔄 Actualizar datos", use_container_width=True,
                         help="Vuelve a descargar todas las hojas de Google Sheets"):
        st.cache_data.clear()
        st.rerun()
