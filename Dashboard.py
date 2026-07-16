import streamlit as st

st.set_page_config(
    page_title="Dashboard Operativo – Uniminuto",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# NAVEGACIÓN (todas por ruta de archivo → navegación confiable)
# Sin login: acceso libre, sin validación de correo.
# ─────────────────────────────────────────────
home_pg  = st.Page("home.py",                 title="Inicio",         icon="🏠", default=True)
insc_pg  = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
mat_pg   = st.Page("pages/2_Matriculas.py",    title="Matrículas",    icon="🎓")
cuart_pg = st.Page("pages/3_Cuartiles.py",     title="Cuartiles",     icon="🏆")
cont_pg  = st.Page("pages/4_Contactabilidad.py", title="Contactabilidad", icon="📞")

pg = st.navigation([home_pg, insc_pg, mat_pg, cuart_pg, cont_pg])
pg.run()
