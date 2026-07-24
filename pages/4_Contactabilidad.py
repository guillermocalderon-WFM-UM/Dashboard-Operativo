import streamlit as st

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebarNav"] { display:none !important; }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse 110% 70% at 8% -10%,  rgba(14,165,233,0.15) 0%, transparent 60%),
            radial-gradient(ellipse 100% 65% at 100% 0%,  rgba(99,102,241,0.15) 0%, transparent 60%),
            linear-gradient(160deg, #071310 0%, #082017 45%, #050F0B 100%);
        background-attachment: fixed;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 3rem; max-width: 1180px; }
    section[data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(160deg, #071811 0%, #0C2B1D 45%, #061109 100%);
        border-right: 1px solid rgba(255,255,255,0.07);
    }
    div[data-testid="stSidebarContent"] * { color: white !important; }
    .wip {
        border-radius:24px; padding:60px 40px; text-align:center;
        background:linear-gradient(160deg,rgba(255,255,255,0.075) 0%,rgba(255,255,255,0.02) 100%);
        border:1px solid rgba(255,255,255,0.10);
        box-shadow:0 20px 50px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.08);
    }
    .wip-ico { font-size:44px;margin-bottom:16px; }
    .wip-title { font-family:'Space Grotesk',sans-serif!important;font-size:28px;font-weight:700;color:white;margin-bottom:10px; }
    .wip-sub { font-size:14px;color:rgba(255,255,255,0.55);max-width:520px;margin:0 auto;line-height:1.7; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='wip'>
    <div class='wip-ico'>📞</div>
    <div class='wip-title'>Real time</div>
    <div class='wip-sub'>
        Este módulo está en construcción. Aquí vivirá la efectividad de contacto por asesor:
        intentos por lead, tasa de contacto efectivo y las franjas horarias con mejor respuesta.
    </div>
</div>
""", unsafe_allow_html=True)
