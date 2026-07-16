import streamlit as st
import base64

COLOR_PRIMARY = "#28053F"
COLOR_ACCENT  = "#0EA5E9"

# objetos de página (mismos parámetros que en Dashboard.py → switch_page funciona)
insc_pg  = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
mat_pg   = st.Page("pages/2_Matriculas.py",    title="Matrículas",    icon="🎓")
cuart_pg = st.Page("pages/3_Cuartiles.py",     title="Cuartiles",     icon="🏆")
cont_pg  = st.Page("pages/4_Contactabilidad.py", title="Contactabilidad", icon="📞")

_MODULOS = {
    "insc": dict(
        icon="📝", title="Inscripciones", status="ok", status_label="Disponible", progress=100,
        desc="Seguimiento del embudo de inscripción: de prospecto a inscripción completa, por asesor, programa y período.",
        feats=["Embudo completo", "Ranking vs. meta", "Estado documental"],
        stats=[("🧭", "6", "Filtros activos"), ("📊", "6", "Gráficas y tablas"), ("⚡", "5 min", "Refresco de datos")],
        ac1="#0EA5E9", ac2="#6366F1",
        icobg="linear-gradient(135deg,rgba(14,165,233,0.22),rgba(99,102,241,0.10))",
        acbord="rgba(56,189,248,0.45)", page=insc_pg, cta="Abrir módulo →",
    ),
    "mat": dict(
        icon="🎓", title="Matrículas", status="wip", status_label="Próximamente", progress=40,
        desc="Seguimiento del proceso de matrícula: período, paquete inscrito y estatus del alumno, una vez completada la inscripción.",
        feats=["Por período y programa", "Tipo de admisión", "Seguimiento financiero"],
        ac1="#8B5CF6", ac2="#EC4899",
        icobg="linear-gradient(135deg,rgba(139,92,246,0.22),rgba(236,72,153,0.10))",
        acbord="rgba(167,139,250,0.45)", page=mat_pg, cta="Ver avance →",
    ),
    "cuart": dict(
        icon="🏆", title="Cuartiles", status="wip", status_label="Próximamente", progress=20,
        desc="Clasificación de asesores por desempeño en cuartiles, para identificar a los mejores y a quiénes necesitan refuerzo.",
        feats=["Ranking por cuartil", "Comparativo entre supervisores", "Evolución histórica"],
        ac1="#34D399", ac2="#059669",
        icobg="linear-gradient(135deg,rgba(52,211,153,0.22),rgba(5,150,105,0.10))",
        acbord="rgba(52,211,153,0.45)", page=cuart_pg, cta="Ver avance →",
    ),
    "cont": dict(
        icon="📞", title="Contactabilidad", status="wip", status_label="En desarrollo", progress=10,
        desc="Efectividad de contacto por asesor: intentos por lead, tasa de contacto efectivo y las franjas horarias con mejor respuesta.",
        feats=["Tasa de contacto", "Intentos por lead", "Franja horaria óptima"],
        ac1="#F97316", ac2="#F59E0B",
        icobg="linear-gradient(135deg,rgba(249,115,22,0.22),rgba(245,158,11,0.10))",
        acbord="rgba(249,115,22,0.45)", page=cont_pg, cta="Ver avance →",
    ),
}

# ── Logo base64 ──────────────────────────
_LOGO_PATH = "logo-scala-learning-transformacion-digital-universidades.webp"
try:
    with open(_LOGO_PATH, "rb") as _f:
        _logo_b64 = base64.b64encode(_f.read()).decode()
    _logo_src = f"data:image/webp;base64,{_logo_b64}"
except FileNotFoundError:
    _logo_src = ""

# ── Sidebar ──────────────────────────────
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

# ── CSS ──────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@500;600;700&display=swap');
    * {{ font-family: 'Inter', sans-serif !important; }}
    /* restaurar la fuente de íconos Material (si no, sale el texto "keyboard_double_arrow_left") */
    span[data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="collapsedControl"] span,
    .material-symbols-rounded, .material-symbols-outlined, .material-icons {{
        font-family: 'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
    }}

    /* ══ FONDO GENERAL OSCURO + AURORA ══ */
    [data-testid="stAppViewContainer"] {{
        background:
            radial-gradient(ellipse 110% 70% at 8% -10%,  rgba(14,165,233,0.15) 0%, transparent 60%),
            radial-gradient(ellipse 100% 65% at 100% 0%,  rgba(99,102,241,0.15) 0%, transparent 60%),
            radial-gradient(ellipse 90% 70% at 85% 105%,  rgba(52,211,153,0.08) 0%, transparent 60%),
            radial-gradient(ellipse 80% 60% at 0% 100%,   rgba(99,102,241,0.07) 0%, transparent 60%),
            linear-gradient(160deg, #071310 0%, #082017 45%, #050F0B 100%);
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    .block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1180px; }}

    /* malla de puntos sutil sobre el fondo */
    [data-testid="stAppViewContainer"]::before {{
        content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
        background-image: radial-gradient(circle, rgba(255,255,255,0.035) 1px, transparent 1px);
        background-size: 34px 34px;
        mask-image: radial-gradient(ellipse 80% 80% at 50% 30%, black 0%, transparent 75%);
        -webkit-mask-image: radial-gradient(ellipse 80% 80% at 50% 30%, black 0%, transparent 75%);
    }}
    [data-testid="stAppViewContainer"] > .main {{ position: relative; z-index: 1; }}

    /* botón para colapsar el sidebar: ícono limpio, sin texto crudo */
    [data-testid="stSidebarCollapseButton"] button,
    div[data-testid="collapsedControl"] button {{
        background:rgba(255,255,255,0.06)!important;border:1px solid rgba(255,255,255,0.10)!important;
        border-radius:10px!important;transition:all .2s ease!important; }}
    [data-testid="stSidebarCollapseButton"] button:hover,
    div[data-testid="collapsedControl"] button:hover {{
        background:rgba(255,255,255,0.14)!important;border-color:rgba(56,189,248,0.4)!important; }}
    [data-testid="stSidebarCollapseButton"] span,
    div[data-testid="collapsedControl"] span {{ color:rgba(255,255,255,0.75)!important;font-size:20px!important; }}
    div[data-testid="stSidebarContent"] {{ width:100%!important;box-sizing:border-box!important;padding-right:0.75rem!important; }}
    div[data-testid="stSidebarContent"] > div {{ width:100%!important; }}

    /* ══ SIDEBAR · mismo fondo de diseño que el hero (sin grid) ══ */
    section[data-testid="stSidebar"] > div:first-child {{
        background:
            radial-gradient(ellipse 95% 42% at 8% 0%,    rgba(14,165,233,0.30) 0%, transparent 55%),
            radial-gradient(ellipse 90% 42% at 100% 26%, rgba(129,140,248,0.28) 0%, transparent 55%),
            radial-gradient(ellipse 85% 42% at 50% 102%, rgba(52,211,153,0.15) 0%, transparent 55%),
            linear-gradient(160deg, #071811 0%, #0C2B1D 45%, #061109 100%);
        border-right: 1px solid rgba(255,255,255,0.07);
    }}
    div[data-testid="stSidebarContent"] * {{ color: white !important; }}

    /* ══ Scala bien arriba + footer pegado al fondo del sidebar ══ */
    [data-testid="stSidebarHeader"] {{ padding-top:0.1rem!important; padding-bottom:0!important; min-height:0!important; }}
    section[data-testid="stSidebar"] .block-container {{ padding-top:0.5rem!important; padding-bottom:0.8rem!important; }}
    /* toda la cadena del sidebar a altura completa para poder anclar abajo */
    section[data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebarContent"] {{
        display:flex!important; flex-direction:column!important; min-height:100vh!important; }}
    [data-testid="stSidebarUserContent"] {{
        flex:1 1 auto!important; display:flex!important; flex-direction:column!important;
        padding-top:0!important; padding-bottom:0!important; }}
    [data-testid="stSidebarUserContent"] > div,
    [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {{
        flex:1 1 auto!important; display:flex!important; flex-direction:column!important; }}
    [data-testid="stSidebarUserContent"] [data-testid="stElementContainer"]:last-of-type {{
        margin-top:auto!important; margin-bottom:32px!important; }}

    /* ══ ANIMATIONS ══ */
    @keyframes sbcBar {{ 0% {{ background-position:0% 0%; }} 100% {{ background-position:200% 0%; }} }}
    @keyframes sbcPulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:.3; transform:scale(.6); }} }}
    @keyframes float {{ 0%,100% {{ transform:translateY(0px); }} 50% {{ transform:translateY(-9px); }} }}
    @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(28px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes shimmer {{ 0% {{ background-position:-200% 0; }} 100% {{ background-position:200% 0; }} }}
    @keyframes auroraMove {{
        0%   {{ transform:translate(0,0) scale(1);        }}
        33%  {{ transform:translate(40px,-30px) scale(1.15); }}
        66%  {{ transform:translate(-30px,25px) scale(0.92); }}
        100% {{ transform:translate(0,0) scale(1);        }}
    }}
    @keyframes ring {{ 0% {{ transform:scale(.85); opacity:.55; }} 100% {{ transform:scale(1.7); opacity:0; }} }}

    /* ══ BRAND CARD (sidebar) ══ */
    .sbc {{ position:relative;border-radius:20px;overflow:hidden;margin:-18px 0 20px;padding:20px 18px 18px;
            background:linear-gradient(145deg,rgba(56,189,248,0.12) 0%,rgba(129,140,248,0.09) 55%,rgba(52,211,153,0.07) 100%),rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.12); }}
    .sbc-orb {{ position:absolute;border-radius:50%;pointer-events:none; }}
    .sbc-orb-1 {{ width:140px;height:140px;background:radial-gradient(circle,rgba(56,189,248,0.18) 0%,transparent 70%);top:-50px;right:-40px; }}
    .sbc-orb-2 {{ width:90px;height:90px;background:radial-gradient(circle,rgba(129,140,248,0.16) 0%,transparent 70%);bottom:-30px;left:-25px; }}
    .sbc-orb-3 {{ width:60px;height:60px;background:radial-gradient(circle,rgba(52,211,153,0.14) 0%,transparent 70%);top:50%;right:12px; }}
    .sbc-live {{ position:absolute;top:14px;right:14px;display:flex;align-items:center;gap:5px;
                 font-size:8px!important;font-weight:800!important;color:#34D399!important;
                 background:rgba(52,211,153,0.13);border:1px solid rgba(52,211,153,0.30);
                 padding:3px 9px 3px 7px;border-radius:99px;letter-spacing:0.10em;z-index:2; }}
    .sbc-pulse {{ width:5px;height:5px;background:#34D399;border-radius:50%;display:inline-block;animation:sbcPulse 1.8s ease-in-out infinite; }}
    .sbc-body {{ position:relative;z-index:1;text-align:center; }}
    .sbc-logo-wrap {{ margin-bottom:10px;display:flex;justify-content:center;align-items:center; }}
    .sbc-logo-img {{ max-width:150px!important;height:auto!important;filter:drop-shadow(0 4px 14px rgba(56,189,248,0.45)) brightness(1.05);display:block; }}
    .sbc-name {{ font-size:13px!important;font-weight:700!important;color:rgba(255,255,255,0.88)!important;letter-spacing:0!important;margin-bottom:4px!important; }}
    .sbc-org  {{ font-size:10px!important;color:rgba(255,255,255,0.35)!important;margin-bottom:16px!important; }}
    .sbc-stats {{ display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.22);border-radius:12px;padding:10px 8px;border:1px solid rgba(255,255,255,0.07); }}
    .sbc-stat {{ flex:1;text-align:center; }}
    .sbc-sv {{ display:block;font-size:14px!important;font-weight:900!important;color:white!important;line-height:1;margin-bottom:3px; }}
    .sbc-sl  {{ display:block;font-size:8px!important;font-weight:700!important;color:rgba(255,255,255,0.28)!important;letter-spacing:0.10em;text-transform:uppercase; }}
    .sbc-sep {{ width:1px;height:28px;background:rgba(255,255,255,0.09);flex-shrink:0; }}
    .sbc-bar {{ position:absolute;bottom:0;left:0;right:0;height:3px;
                background:linear-gradient(90deg,#38BDF8,#818CF8,#34D399,#F59E0B,#38BDF8);
                background-size:300% 100%;animation:sbcBar 4s linear infinite; }}
    .sbf {{ margin-top:26px;padding:0; }}
    .sbf-card {{ position:relative;overflow:hidden;border-radius:16px;padding:14px 14px;
        background:linear-gradient(150deg,rgba(56,189,248,0.10),rgba(129,140,248,0.06));
        border:1px solid rgba(255,255,255,0.10);
        box-shadow:inset 0 1px 0 rgba(255,255,255,0.08); }}
    .sbf-glow {{ position:absolute;width:120px;height:120px;border-radius:50%;top:-50px;right:-40px;
        background:radial-gradient(circle,rgba(56,189,248,0.20),transparent 70%);pointer-events:none; }}
    .sbf-row {{ display:flex;align-items:center;gap:12px;position:relative;z-index:1; }}
    .sbf-avatar {{ position:relative;width:42px;height:42px;border-radius:13px;
                   background:linear-gradient(135deg,#38BDF8 0%,#818CF8 100%);
                   display:flex;align-items:center;justify-content:center;font-size:14px!important;font-weight:900!important;
                   color:white!important;flex-shrink:0;letter-spacing:0.5px;
                   box-shadow:0 6px 18px rgba(56,189,248,0.45),inset 0 1px 0 rgba(255,255,255,0.3); }}
    .sbf-online {{ position:absolute;bottom:-2px;right:-2px;width:12px;height:12px;border-radius:50%;
        background:#34D399;border:2.5px solid #130A2B;box-shadow:0 0 8px rgba(52,211,153,0.8);
        animation:sbcPulse 2s ease-in-out infinite; }}
    .sbf-name {{ font-size:12px!important;font-weight:700!important;color:rgba(255,255,255,0.92)!important;margin-bottom:3px!important; }}
    .sbf-role {{ font-size:10px!important;color:rgba(255,255,255,0.42)!important;line-height:1.3; }}
    .sbf-credit {{ display:flex;align-items:center;justify-content:center;gap:5px;
        margin-top:12px;font-size:9px!important;font-weight:600!important;
        color:rgba(255,255,255,0.30)!important;text-align:center;letter-spacing:0.06em; }}
    .sbf-spark {{ font-size:10px; }}

    /* ══════════ HERO ══════════ */
    .hero {{
        position:relative; border-radius:28px; overflow:hidden;
        padding:34px 50px 30px; text-align:center; margin-bottom:20px;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%);
        border:1px solid rgba(255,255,255,0.11);
        box-shadow:0 32px 90px rgba(0,0,0,0.50), inset 0 1px 0 rgba(255,255,255,0.12);
        backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
        animation:fadeUp 0.7s ease both;
    }}
    .hero-aurora {{ position:absolute; border-radius:50%; filter:blur(52px); pointer-events:none; z-index:0; }}
    .ha1 {{ width:420px;height:420px;background:radial-gradient(circle,rgba(14,165,233,0.52),transparent 65%);top:-160px;left:-110px;animation:auroraMove 14s ease-in-out infinite; }}
    .ha2 {{ width:380px;height:380px;background:radial-gradient(circle,rgba(129,140,248,0.48),transparent 65%);bottom:-170px;right:-80px;animation:auroraMove 18s ease-in-out infinite reverse; }}
    .ha3 {{ width:280px;height:280px;background:radial-gradient(circle,rgba(52,211,153,0.35),transparent 65%);top:25%;right:15%;animation:auroraMove 22s ease-in-out infinite; }}
    .ha4 {{ width:220px;height:220px;background:radial-gradient(circle,rgba(245,158,11,0.28),transparent 65%);bottom:-80px;left:10%;animation:auroraMove 26s ease-in-out infinite reverse; }}
    .hero::before {{
        content:''; position:absolute; inset:0; z-index:0;
        background-image:linear-gradient(rgba(255,255,255,0.045) 1px,transparent 1px),
                         linear-gradient(90deg,rgba(255,255,255,0.045) 1px,transparent 1px);
        background-size:44px 44px;
        mask-image:radial-gradient(ellipse 75% 75% at 50% 40%,black,transparent 82%);
        -webkit-mask-image:radial-gradient(ellipse 75% 75% at 50% 40%,black,transparent 82%);
    }}
    .hero-inner {{ position:relative; z-index:1; }}
    .hero-badge {{ display:inline-flex;align-items:center;gap:9px;
        background:rgba(52,211,153,0.08);
        border:1px solid rgba(52,211,153,0.28);
        border-radius:99px;padding:7px 20px;margin-bottom:28px;
        font-size:10.5px;font-weight:700;color:rgba(255,255,255,0.82);
        letter-spacing:0.14em;text-transform:uppercase;
        box-shadow:0 4px 22px rgba(0,0,0,0.28), 0 0 18px -6px rgba(52,211,153,0.30); }}
    .hero-badge-dot {{ position:relative;width:8px;height:8px; }}
    .hero-badge-dot::after {{ content:'';position:absolute;inset:0;border-radius:50%;background:#34D399; }}
    .hero-badge-dot::before {{ content:'';position:absolute;inset:0;border-radius:50%;border:2px solid #34D399;animation:ring 1.8s ease-out infinite; }}
    .hero-title {{ font-family:'Space Grotesk',sans-serif!important;
        font-size:44px;font-weight:800;color:white;margin:0 0 12px;
        letter-spacing:-1.8px;line-height:1.04;text-shadow:0 4px 44px rgba(0,0,0,0.45); }}
    .hero-title .grad {{ background:linear-gradient(90deg,#38BDF8 0%,#818CF8 35%,#34D399 70%,#38BDF8 100%);
        background-size:220% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;animation:shimmer 4s linear infinite; }}
    .hero-sub {{ font-size:15px;color:rgba(255,255,255,0.62);max-width:580px;
        margin:0 auto 0;line-height:1.68;font-weight:400; }}

    /* ══ SECTION LABEL ══ */
    .sec-lbl {{ display:flex;align-items:center;gap:12px;margin:38px 0 20px;
        font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;
        color:rgba(255,255,255,0.45); }}
    .sec-lbl::before {{ content:'';width:26px;height:2px;border-radius:2px;
        background:linear-gradient(90deg,#38BDF8,#818CF8); }}
    .sec-lbl::after {{ content:'';flex:1;height:1px;
        background:linear-gradient(90deg,rgba(255,255,255,0.14),transparent); }}

    /* ══ MODULE CARDS ══ */
    .mod {{ position:relative;border-radius:24px;overflow:hidden;
        padding:34px 30px 26px;display:flex;flex-direction:column;height:100%;
        background:linear-gradient(160deg,rgba(255,255,255,0.075) 0%,rgba(255,255,255,0.02) 100%);
        border:1px solid rgba(255,255,255,0.10);
        box-shadow:0 20px 50px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.08);
        backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
        transition:transform .3s cubic-bezier(.2,.8,.2,1),box-shadow .3s ease,border-color .3s ease;
        animation:fadeUp .8s ease both; }}
    .mod:hover {{ transform:translateY(-8px);
        border-color:var(--glow,rgba(255,255,255,0.25));
        box-shadow:0 32px 70px rgba(0,0,0,0.5),0 0 0 1px var(--glow,transparent),
                   0 0 50px -8px var(--glow,transparent); }}
    .mod-glow {{ position:absolute;top:-60px;right:-60px;width:200px;height:200px;border-radius:50%;
        background:radial-gradient(circle,var(--accent),transparent 70%);opacity:.16;pointer-events:none; }}
    .mod-head {{ display:flex;align-items:flex-start;justify-content:space-between;
        position:relative;z-index:1;margin-bottom:18px; }}
    .mod-ico {{ position:relative;width:64px;height:64px;border-radius:18px;
        display:flex;align-items:center;justify-content:center;font-size:30px;flex-shrink:0;
        background:var(--icobg);border:1px solid var(--glow,rgba(255,255,255,0.12));
        animation:float 3.8s ease-in-out infinite;
        box-shadow:0 10px 30px -6px var(--glow,transparent); }}
    .mod-badge {{ display:inline-flex;align-items:center;gap:6px;
        font-size:9.5px;font-weight:800;padding:5px 11px;border-radius:99px;
        letter-spacing:0.08em;text-transform:uppercase; }}
    .mod-badge-dot {{ width:6px;height:6px;border-radius:50%; }}
    .mod-title {{ font-family:'Space Grotesk',sans-serif!important;
        font-size:25px;font-weight:700;color:white;margin:0 0 9px;
        letter-spacing:-0.5px;position:relative;z-index:1; }}
    .mod-desc {{ font-size:13.5px;color:rgba(255,255,255,0.55);line-height:1.7;
        margin:0 0 22px;position:relative;z-index:1; }}
    .mod-feats {{ display:flex;flex-direction:column;gap:11px;margin-bottom:26px;
        position:relative;z-index:1; }}
    .mfeat {{ display:flex;align-items:center;gap:11px;font-size:12.5px;
        color:rgba(255,255,255,0.72);font-weight:500; }}
    .mfeat-ck {{ width:19px;height:19px;border-radius:6px;flex-shrink:0;
        display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:900;
        background:var(--icobg);color:var(--accent-solid);border:1px solid var(--glow,rgba(255,255,255,0.12)); }}
    .mod-div {{ height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.12),transparent);
        margin:0 0 16px;position:relative;z-index:1; }}
    .mod-foot {{ display:flex;align-items:flex-end;justify-content:space-between;gap:14px;
        margin-bottom:22px;position:relative;z-index:1; }}
    .mod-chips {{ display:flex;flex-direction:column;gap:7px; }}
    .mchip {{ display:inline-flex;align-items:center;gap:6px;align-self:flex-start;
        font-size:10.5px;font-weight:700;padding:5px 10px;border-radius:8px;
        background:var(--icobg);color:rgba(255,255,255,0.82);
        border:1px solid var(--glow,rgba(255,255,255,0.12)); }}
    .mchip b {{ color:var(--accent-solid);font-weight:800; }}
    .mspark {{ display:flex;align-items:flex-end;gap:4px;height:46px;padding:0 2px; }}
    .mspark span {{ width:7px;border-radius:4px;background:var(--accent);
        opacity:.55;transform-origin:bottom;transition:transform .4s cubic-bezier(.2,.8,.2,1),opacity .3s ease; }}
    .mod:hover .mspark span {{ opacity:.95;transform:scaleY(1.18); }}

    /* ══ MÓDULOS · riel + panel ══ */
    .sel-eyebrow {{ display:flex;align-items:center;gap:8px;margin:0 0 12px 2px;
        font-size:10px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:rgba(255,255,255,0.38); }}
    .sel-eyebrow .dot {{ width:6px;height:6px;border-radius:50%;background:#34D399;box-shadow:0 0 8px #34D399;
        animation:sbcPulse 1.8s ease-in-out infinite; }}

    /* -- tarjetas del riel -- */
    .rail-card-head {{ display:flex;align-items:center;gap:13px;position:relative;margin-bottom:16px; }}
    .rail-ico {{ width:44px;height:44px;flex-shrink:0;border-radius:13px;display:flex;align-items:center;justify-content:center;
        font-size:20px;background:var(--icobg);border:1px solid var(--acbord);
        box-shadow:0 6px 16px -6px var(--ac1); transition:transform .25s cubic-bezier(.2,.8,.2,1); }}
    .rail-txt {{ display:flex;flex-direction:column;gap:7px;min-width:0; }}
    .rail-title {{ font-family:'Space Grotesk',sans-serif!important;font-weight:700;font-size:15px;color:white;
        letter-spacing:-0.1px;line-height:1.2; }}
    .rail-status {{ display:inline-flex;align-items:center;gap:6px;font-size:9px;font-weight:800;
        padding:3px 9px;border-radius:99px;letter-spacing:0.07em;text-transform:uppercase;align-self:flex-start; }}
    .rail-status-ok {{ background:rgba(52,211,153,0.14);color:#34D399;border:1px solid rgba(52,211,153,0.30); }}
    .rail-status-wip {{ background:rgba(245,158,11,0.14);color:#FCD34D;border:1px solid rgba(245,158,11,0.30); }}
    .rail-status .dot {{ width:5px;height:5px;border-radius:50%;background:currentColor; }}
    .rail-active-flag {{ display:none; }}
    .rail-div {{ height:1px;background:linear-gradient(90deg,rgba(255,255,255,0.12),transparent);margin-bottom:2px; }}

    .st-key-railitem_insc, .st-key-railitem_mat, .st-key-railitem_cuart, .st-key-railitem_cont {{
        position:relative;border-radius:18px;padding:14px 16px 8px;margin-bottom:12px;overflow:hidden;
        background:linear-gradient(160deg,rgba(255,255,255,0.055) 0%,rgba(255,255,255,0.015) 100%);
        border:1px solid rgba(255,255,255,0.09);
        transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .3s ease,border-color .3s ease,background .3s ease;
    }}
    .st-key-railitem_insc:hover, .st-key-railitem_mat:hover, .st-key-railitem_cuart:hover, .st-key-railitem_cont:hover {{
        transform:translateY(-3px);border-color:var(--acbord); }}
    .st-key-railitem_insc:hover .rail-ico, .st-key-railitem_mat:hover .rail-ico,
    .st-key-railitem_cuart:hover .rail-ico, .st-key-railitem_cont:hover .rail-ico {{
        transform:scale(1.08) rotate(-4deg); }}
    .st-key-railitem_insc:has(.rail-active-flag), .st-key-railitem_mat:has(.rail-active-flag),
    .st-key-railitem_cuart:has(.rail-active-flag), .st-key-railitem_cont:has(.rail-active-flag) {{
        border-color:var(--acbord);
        background:linear-gradient(160deg,rgba(255,255,255,0.09) 0%,rgba(255,255,255,0.025) 100%);
        box-shadow:0 16px 36px -14px var(--ac1),inset 0 1px 0 rgba(255,255,255,0.10); }}
    .st-key-railitem_insc::before, .st-key-railitem_mat::before,
    .st-key-railitem_cuart::before, .st-key-railitem_cont::before {{
        content:'';position:absolute;left:0;top:10px;bottom:10px;width:3px;border-radius:3px;
        background:var(--ac1);opacity:0;transition:opacity .25s ease; }}
    .st-key-railitem_insc:has(.rail-active-flag)::before, .st-key-railitem_mat:has(.rail-active-flag)::before,
    .st-key-railitem_cuart:has(.rail-active-flag)::before, .st-key-railitem_cont:has(.rail-active-flag)::before {{ opacity:1; }}
    .st-key-railitem_insc  {{ --ac1:#0EA5E9;--ac2:#6366F1; --icobg:linear-gradient(135deg,rgba(14,165,233,0.24),rgba(99,102,241,0.10)); --acbord:rgba(56,189,248,0.5); }}
    .st-key-railitem_mat   {{ --ac1:#8B5CF6;--ac2:#EC4899; --icobg:linear-gradient(135deg,rgba(139,92,246,0.24),rgba(236,72,153,0.10)); --acbord:rgba(167,139,250,0.5); }}
    .st-key-railitem_cuart {{ --ac1:#34D399;--ac2:#059669; --icobg:linear-gradient(135deg,rgba(52,211,153,0.24),rgba(5,150,105,0.10)); --acbord:rgba(52,211,153,0.5); }}
    .st-key-railitem_cont  {{ --ac1:#F97316;--ac2:#F59E0B; --icobg:linear-gradient(135deg,rgba(249,115,22,0.24),rgba(245,158,11,0.10)); --acbord:rgba(249,115,22,0.5); }}

    .st-key-railitem_insc div[data-testid="stButton"], .st-key-railitem_mat div[data-testid="stButton"],
    .st-key-railitem_cuart div[data-testid="stButton"], .st-key-railitem_cont div[data-testid="stButton"] {{
        margin-top:8px; }}
    .st-key-railitem_insc div[data-testid="stButton"] > button, .st-key-railitem_mat div[data-testid="stButton"] > button,
    .st-key-railitem_cuart div[data-testid="stButton"] > button, .st-key-railitem_cont div[data-testid="stButton"] > button {{
        height:32px!important;min-height:32px!important;padding:0 4px!important;
        background:transparent!important;border:none!important;box-shadow:none!important;
        color:rgba(255,255,255,0.38)!important;font-size:10.5px!important;font-weight:700!important;
        text-align:center!important;justify-content:center!important;letter-spacing:0.03em!important; }}
    .st-key-railitem_insc div[data-testid="stButton"] > button:hover {{ color:#0EA5E9!important;transform:none!important;box-shadow:none!important; }}
    .st-key-railitem_mat div[data-testid="stButton"] > button:hover {{ color:#8B5CF6!important;transform:none!important;box-shadow:none!important; }}
    .st-key-railitem_cuart div[data-testid="stButton"] > button:hover {{ color:#34D399!important;transform:none!important;box-shadow:none!important; }}
    .st-key-railitem_cont div[data-testid="stButton"] > button:hover {{ color:#F97316!important;transform:none!important;box-shadow:none!important; }}
    .st-key-railitem_insc div[data-testid="stButton"] > button p, .st-key-railitem_mat div[data-testid="stButton"] > button p,
    .st-key-railitem_cuart div[data-testid="stButton"] > button p, .st-key-railitem_cont div[data-testid="stButton"] > button p {{
        text-align:center!important; }}

    /* -- panel de detalle -- */
    .mod-panel {{ position:relative;overflow:hidden;border-radius:24px;padding:32px 34px 28px;
        background:linear-gradient(160deg,rgba(255,255,255,0.075) 0%,rgba(255,255,255,0.02) 100%);
        border:1px solid rgba(255,255,255,0.10);
        box-shadow:0 24px 60px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,255,255,0.09);
        min-height:460px;display:flex;flex-direction:column;animation:fadeUp .5s ease both; }}
    .mod-panel::before {{ content:'';position:absolute;inset:0;z-index:0;
        background-image:linear-gradient(rgba(255,255,255,0.035) 1px,transparent 1px),
                         linear-gradient(90deg,rgba(255,255,255,0.035) 1px,transparent 1px);
        background-size:38px 38px;
        mask-image:radial-gradient(ellipse 70% 70% at 85% 15%,black,transparent 78%);
        -webkit-mask-image:radial-gradient(ellipse 70% 70% at 85% 15%,black,transparent 78%); }}
    .mod-panel-glow {{ position:absolute;top:-90px;right:-90px;width:260px;height:260px;border-radius:50%;
        background:radial-gradient(circle,var(--ac1),transparent 70%);opacity:0.20;pointer-events:none;
        animation:auroraMove 16s ease-in-out infinite; }}
    .mod-panel-glow2 {{ position:absolute;bottom:-100px;left:20%;width:220px;height:220px;border-radius:50%;
        background:radial-gradient(circle,var(--ac2),transparent 70%);opacity:0.14;pointer-events:none;
        animation:auroraMove 20s ease-in-out infinite reverse; }}
    .mod-panel-watermark {{ position:absolute;right:-10px;bottom:-30px;font-size:230px;line-height:1;
        opacity:0.05;pointer-events:none;transform:rotate(-8deg);filter:blur(0.5px); }}
    .mod-panel-top {{ display:flex;align-items:flex-start;justify-content:space-between;position:relative;z-index:1;margin-bottom:20px; }}
    .mod-panel-ico-ring {{ width:80px;height:80px;border-radius:22px;display:flex;align-items:center;justify-content:center;
        padding:5px;background:conic-gradient(var(--ac1) calc(var(--pct,100)*3.6deg),rgba(255,255,255,0.09) 0deg); }}
    .mod-panel-ico {{ width:100%;height:100%;border-radius:18px;display:flex;align-items:center;justify-content:center;
        font-size:30px;background:var(--icobg);border:1px solid var(--acbord);
        box-shadow:0 12px 30px -8px var(--ac1);animation:float 3.6s ease-in-out infinite; }}
    .mod-panel-ico-pct {{ position:absolute;bottom:-8px;right:-8px;background:#0a1712;border:1px solid var(--acbord);
        border-radius:99px;padding:2px 8px;font-size:10px;font-weight:800;color:var(--ac1);
        font-family:'Space Grotesk',sans-serif!important; }}
    .mod-panel-title {{ font-family:'Space Grotesk',sans-serif!important;font-size:32px;font-weight:700;color:white;
        margin:0 0 12px;letter-spacing:-0.6px;position:relative;z-index:1;text-wrap:balance; }}
    .mod-panel-title .grad {{ background:linear-gradient(90deg,var(--ac1),var(--ac2),var(--ac1));
        background-size:220% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;animation:shimmer 4s linear infinite; }}
    .mod-panel-desc {{ font-size:14px;color:rgba(255,255,255,0.60);line-height:1.8;
        margin:0 0 20px;max-width:540px;position:relative;z-index:1; }}
    .mod-panel-feats {{ display:flex;flex-wrap:wrap;gap:9px;margin-bottom:24px;position:relative;z-index:1; }}
    .pfeat {{ font-size:11.5px;color:rgba(255,255,255,0.78);background:rgba(255,255,255,0.05);
        border:1px solid rgba(255,255,255,0.11);padding:7px 13px;border-radius:9px;font-weight:600;
        display:inline-flex;align-items:center;gap:6px; }}

    /* -- trío de stats (módulo disponible) -- */
    .mod-stat-trio {{ display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px;position:relative;z-index:1; }}
    .mod-stat {{ text-align:center;padding:16px 10px;border-radius:14px;
        background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.09); }}
    .mod-stat-ico {{ font-size:19px;margin-bottom:8px; }}
    .mod-stat-val {{ font-family:'Space Grotesk',sans-serif!important;font-size:19px;font-weight:700;color:white;
        line-height:1;margin-bottom:5px; }}
    .mod-stat-lbl {{ font-size:9.5px;color:rgba(255,255,255,0.42);text-transform:uppercase;letter-spacing:0.06em;font-weight:700; }}

    /* -- etapas de avance (módulo en desarrollo) -- */
    .mod-stages {{ display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px;position:relative;z-index:1; }}
    .mod-stage {{ display:flex;align-items:center;gap:9px;padding:13px 12px;border-radius:14px;
        background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.09); }}
    .mod-stage-dot {{ width:11px;height:11px;border-radius:50%;flex-shrink:0;position:relative; }}
    .mod-stage-dot.done {{ background:#34D399;box-shadow:0 0 9px #34D399; }}
    .mod-stage-dot.active {{ background:#FBBF24;box-shadow:0 0 9px #FBBF24;animation:sbcPulse 1.6s ease-in-out infinite; }}
    .mod-stage-dot.pending {{ background:rgba(255,255,255,0.16); }}
    .mod-stage-lbl {{ font-size:11.5px;font-weight:600; }}
    .mod-stage.done .mod-stage-lbl {{ color:rgba(255,255,255,0.85); }}
    .mod-stage.active .mod-stage-lbl {{ color:#FCD34D; }}
    .mod-stage.pending .mod-stage-lbl {{ color:rgba(255,255,255,0.35); }}

    .mod-panel-div {{ height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.14),transparent);
        margin:0 0 20px;position:relative;z-index:1; }}
    .mod-panel-footrow {{ display:flex;align-items:center;justify-content:space-between;gap:18px;
        margin-top:auto;position:relative;z-index:1; }}
    .mspark2 {{ display:flex;align-items:flex-end;gap:4px;height:40px; }}
    .mspark2 span {{ width:6px;border-radius:3px;background:var(--ac1);opacity:.75; }}
    .mod-panel-livechip {{ display:inline-flex;align-items:center;gap:7px;font-size:11.5px;font-weight:700;
        color:rgba(255,255,255,0.82);background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.12);
        padding:7px 14px;border-radius:10px; }}
    .mod-panel-note {{ display:flex;align-items:center;gap:8px;font-size:12px;color:rgba(255,255,255,0.45);
        font-style:italic; }}

    /* ══ BUTTONS ══ */
    div[data-testid="stButton"] > button {{
        border-radius:14px!important;font-weight:700!important;font-size:14px!important;
        height:50px!important;letter-spacing:0.01em!important;
        transition:transform .2s ease,box-shadow .2s ease,filter .2s ease!important; }}
    div[data-testid="stButton"] > button[kind="primary"] {{
        background:linear-gradient(120deg,#0EA5E9 0%,#6366F1 55%,#8B5CF6 100%)!important;
        background-size:160% auto!important;color:white!important;border:none!important;
        box-shadow:0 10px 30px -6px rgba(99,102,241,0.6)!important; }}
    div[data-testid="stButton"] > button[kind="primary"]:hover {{
        transform:translateY(-3px)!important;filter:brightness(1.08)!important;
        box-shadow:0 16px 40px -8px rgba(99,102,241,0.75)!important; }}
    div[data-testid="stButton"] > button[kind="secondary"] {{
        background:rgba(255,255,255,0.05)!important;color:rgba(255,255,255,0.80)!important;
        border:1px solid rgba(255,255,255,0.18)!important; }}
    div[data-testid="stButton"] > button[kind="secondary"]:hover {{
        background:rgba(139,92,246,0.16)!important;border-color:rgba(167,139,250,0.6)!important;
        color:white!important;transform:translateY(-3px)!important;
        box-shadow:0 14px 34px -10px rgba(139,92,246,0.6)!important; }}

    /* ══ STATS STRIP ══ */
    .stats {{ display:flex;gap:16px;margin-top:34px;animation:fadeUp 1s ease both; }}
    .stat {{ flex:1;position:relative;overflow:hidden;border-radius:18px;padding:24px 18px;
        text-align:center;background:linear-gradient(160deg,rgba(255,255,255,0.06),rgba(255,255,255,0.015));
        border:1px solid rgba(255,255,255,0.09);
        box-shadow:0 12px 30px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.06);
        transition:transform .25s ease,border-color .25s ease; }}
    .stat:hover {{ transform:translateY(-4px);border-color:var(--sc); }}
    .stat::after {{ content:'';position:absolute;bottom:0;left:50%;transform:translateX(-50%);
        width:60%;height:2px;background:var(--sc);border-radius:2px;opacity:.7; }}
    .stat-ico {{ font-size:18px;margin-bottom:8px;opacity:.9; }}
    .stat-val {{ font-family:'Space Grotesk',sans-serif!important;
        font-size:30px;font-weight:700;color:white;line-height:1;margin-bottom:6px; }}
    .stat-lbl {{ font-size:10px;font-weight:700;color:rgba(255,255,255,0.42);
        text-transform:uppercase;letter-spacing:0.10em; }}

    /* ══ Ocultar el menú automático del sidebar ══ */
    [data-testid="stSidebarNav"] {{ display:none !important; }}

    /* ══ HERO · separador y tarjetas de estado ══ */
    .hero-divider {{ width:56px;height:1.5px;margin:22px auto 20px;border-radius:2px;
        background:linear-gradient(90deg,transparent,rgba(56,189,248,0.55),rgba(129,140,248,0.55),transparent); }}
    .hero-cards {{ display:flex;justify-content:center;gap:10px;flex-wrap:wrap; }}
    .hcard {{ display:flex;align-items:center;gap:13px;min-width:148px;
        background:rgba(255,255,255,0.05);
        border:1px solid rgba(255,255,255,0.09);
        border-top:2px solid var(--hc,rgba(56,189,248,0.50));
        border-radius:16px;padding:14px 20px;
        backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
        box-shadow:0 8px 28px rgba(0,0,0,0.22),inset 0 1px 0 rgba(255,255,255,0.07);
        transition:transform .24s cubic-bezier(.2,.8,.2,1),box-shadow .24s ease,background .24s ease; }}
    .hcard:hover {{ transform:translateY(-5px);background:rgba(255,255,255,0.09);
        box-shadow:0 18px 44px rgba(0,0,0,0.32),0 0 0 1px var(--hc,rgba(56,189,248,0.28)),
                   0 0 24px -8px var(--hc,rgba(56,189,248,0.28)); }}
    .hcard-ico {{ width:44px;height:44px;border-radius:13px;flex-shrink:0;
        display:flex;align-items:center;justify-content:center;font-size:20px;
        background:var(--hc-bg,rgba(56,189,248,0.12));
        border:1px solid var(--hc,rgba(56,189,248,0.22));
        box-shadow:0 4px 16px -4px var(--hc,rgba(56,189,248,0.30)); }}
    .hcard-txt {{ text-align:left; }}
    .hcard-lbl {{ font-size:8.5px;font-weight:700;letter-spacing:0.13em;text-transform:uppercase;
        color:var(--hc,rgba(56,189,248,0.80));margin-bottom:4px;display:block; }}
    .hcard-val {{ font-size:15px;font-weight:800;color:white;line-height:1;display:block; }}
    .hcard-val .dot {{ display:inline-block;width:7px;height:7px;border-radius:50%;background:#34D399;
        box-shadow:0 0 10px #34D399;margin-right:6px;animation:sbcPulse 1.8s ease-in-out infinite; }}

    /* ══ TICKER EN VIVO ══ */
    @keyframes nticker {{ 0% {{ transform:translateX(0); }} 100% {{ transform:translateX(-50%); }} }}
    .nticker-shell {{ display:flex;align-items:stretch;overflow:hidden;border-radius:14px;
        background:rgba(245,158,11,0.04);
        border:1px solid rgba(245,158,11,0.22);
        box-shadow:0 0 30px -8px rgba(245,158,11,0.12),inset 0 1px 0 rgba(255,255,255,0.06);
        margin:24px 0 0; }}
    .nticker-label {{ flex-shrink:0;display:flex;align-items:center;gap:8px;
        padding:12px 18px;font-size:8.5px;font-weight:800;letter-spacing:0.18em;
        text-transform:uppercase;color:#F59E0B;
        background:linear-gradient(135deg,rgba(245,158,11,0.18),rgba(245,158,11,0.08));
        border-right:1px solid rgba(245,158,11,0.22); }}
    .nticker-dot {{ width:7px;height:7px;border-radius:50%;background:#F59E0B;
        box-shadow:0 0 8px #F59E0B;
        animation:sbcPulse 1.8s ease-in-out infinite;flex-shrink:0; }}
    .nticker-track {{ overflow:hidden;flex:1;
        mask-image:linear-gradient(90deg,transparent 0%,black 5%,black 95%,transparent 100%);
        -webkit-mask-image:linear-gradient(90deg,transparent 0%,black 5%,black 95%,transparent 100%); }}
    .nticker-inner {{ display:flex;width:max-content;
        animation:nticker 38s linear infinite;padding:12px 0; }}
    .nticker-inner:hover {{ animation-play-state:paused; }}
    .nticker-item {{ display:flex;align-items:center;gap:10px;
        padding:0 48px;white-space:nowrap;
        font-size:13px;color:rgba(255,255,255,0.68);font-weight:500; }}
    .nticker-sep {{ color:rgba(245,158,11,0.35);font-size:18px;margin-left:6px; }}
    .ntag {{ font-size:8px;font-weight:800;padding:3px 8px;border-radius:5px;
        text-transform:uppercase;letter-spacing:0.09em;flex-shrink:0; }}
    .ntag-a {{ background:rgba(244,63,94,0.18);color:#FB7185;border:1px solid rgba(244,63,94,0.28); }}
    .ntag-u {{ background:rgba(14,165,233,0.18);color:#38BDF8;border:1px solid rgba(14,165,233,0.28); }}
    .ntag-n {{ background:rgba(52,211,153,0.18);color:#34D399;border:1px solid rgba(52,211,153,0.28); }}
    .ntag-p {{ background:rgba(245,158,11,0.18);color:#FCD34D;border:1px solid rgba(245,158,11,0.28); }}
</style>
""", unsafe_allow_html=True)

# ── HERO ─────────────────────────────────
st.markdown("""
<div class='hero'>
    <div class='hero-aurora ha1'></div>
    <div class='hero-aurora ha2'></div>
    <div class='hero-aurora ha3'></div>
    <div class='hero-aurora ha4'></div>
    <div class='hero-inner'>
        <div class='hero-badge'>
            <span class='hero-badge-dot'></span>
            Centro de Control · Uniminuto · 2026
        </div>
        <div class='hero-title'>
            Dashboard<br><span class='grad'>Operativo</span>
        </div>
        <div class='hero-sub'>
            Plataforma de análisis del proceso comercial y académico.
            Monitorea <b style='color:rgba(255,255,255,0.85)'>inscripciones</b>,
            <b style='color:rgba(255,255,255,0.85)'>matrículas</b>,
            <b style='color:rgba(255,255,255,0.85)'>cuartiles</b> y
            <b style='color:rgba(255,255,255,0.85)'>contactabilidad</b> en tiempo real, desde una sola base consolidada.
        </div>
        <div class='hero-divider'></div>
        <div class='hero-cards'>
            <div class='hcard' style='--hc:rgba(52,211,153,0.70);--hc-bg:rgba(52,211,153,0.13)'>
                <div class='hcard-ico'>⚡</div>
                <div class='hcard-txt'>
                    <span class='hcard-lbl'>Estado del sistema</span>
                    <span class='hcard-val'><span class='dot'></span>En línea</span>
                </div>
            </div>
            <div class='hcard' style='--hc:rgba(56,189,248,0.70);--hc-bg:rgba(56,189,248,0.13)'>
                <div class='hcard-ico'>◈</div>
                <div class='hcard-txt'>
                    <span class='hcard-lbl'>Seguimiento</span>
                    <span class='hcard-val'>Por asesor</span>
                </div>
            </div>
            <div class='hcard' style='--hc:rgba(129,140,248,0.70);--hc-bg:rgba(129,140,248,0.13)'>
                <div class='hcard-ico'>◷</div>
                <div class='hcard-txt'>
                    <span class='hcard-lbl'>Período activo</span>
                    <span class='hcard-val'>2026</span>
                </div>
            </div>
            <div class='hcard' style='--hc:rgba(245,158,11,0.70);--hc-bg:rgba(245,158,11,0.13)'>
                <div class='hcard-ico'>✦</div>
                <div class='hcard-txt'>
                    <span class='hcard-lbl'>Alianza</span>
                    <span class='hcard-val'>Uniminuto</span>
                </div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
"<div class='nticker-shell'>"
"<div class='nticker-label'><span class='nticker-dot'></span>EN VIVO</div>"
"<div class='nticker-track'><div class='nticker-inner'>"
"<div class='nticker-item'><span class='ntag ntag-u'>Nuevo</span>Dashboard Operativo — módulo de Inscripciones ya disponible <span class='nticker-sep'>·</span></div>"
"<div class='nticker-item'><span class='ntag ntag-p'>Próximamente</span>Matrículas, Cuartiles y Contactabilidad, en construcción <span class='nticker-sep'>·</span></div>"
"<div class='nticker-item'><span class='ntag ntag-u'>Nuevo</span>Dashboard Operativo — módulo de Inscripciones ya disponible <span class='nticker-sep'>·</span></div>"
"<div class='nticker-item'><span class='ntag ntag-p'>Próximamente</span>Matrículas, Cuartiles y Contactabilidad, en construcción <span class='nticker-sep'>·</span></div>"
"</div></div></div>",
unsafe_allow_html=True)

# ── MÓDULOS · riel + panel ────────────────
st.markdown("<div class='sec-lbl' style='margin-top:30px'>Módulos disponibles</div>", unsafe_allow_html=True)

if "home_mod" not in st.session_state:
    st.session_state.home_mod = "insc"

rail_col, panel_col = st.columns([1, 2.4], gap="medium")

with rail_col:
    for key, m in _MODULOS.items():
        active = st.session_state.home_mod == key
        badge_cls = "rail-status-ok" if m["status"] == "ok" else "rail-status-wip"
        with st.container(key=f"railitem_{key}"):
            active_flag = "<div class='rail-active-flag'></div>" if active else ""
            st.markdown(
                "<div class='rail-card-head'>"
                f"<div class='rail-ico'>{m['icon']}</div>"
                "<div class='rail-txt'>"
                f"<div class='rail-title'>{m['title']}</div>"
                f"<span class='rail-status {badge_cls}'><span class='dot'></span>{m['status_label']}</span>"
                "</div>"
                f"</div>{active_flag}"
                "<div class='rail-div'></div>",
                unsafe_allow_html=True,
            )
            if st.button("● viendo ahora" if active else "ver este módulo  →",
                         key=f"railbtn_{key}", width="stretch"):
                st.session_state.home_mod = key

with panel_col:
    m = _MODULOS[st.session_state.home_mod]
    pct = m["progress"]
    feats_html = "".join(f"<span class='pfeat'>✓ {f}</span>" for f in m["feats"])
    badge_cls = "rail-status-ok" if m["status"] == "ok" else "rail-status-wip"

    if m["status"] == "ok":
        stats_html = "<div class='mod-stat-trio'>"
        for ico, val, lbl in m["stats"]:
            stats_html += (
                f"<div class='mod-stat'><div class='mod-stat-ico'>{ico}</div>"
                f"<div class='mod-stat-val'>{val}</div><div class='mod-stat-lbl'>{lbl}</div></div>"
            )
        stats_html += "</div>"
        heights = [38, 62, 48, 78, 58, 90, 70, 100]
        bars = "".join(f"<span style='height:{h}%'></span>" for h in heights)
        foot_html = (
            "<div class='mod-panel-footrow'>"
            "<span class='mod-panel-livechip'>📡 Base en vivo · sincronizada con Google Sheets</span>"
            f"<div class='mspark2'>{bars}</div>"
            "</div>"
        )
    else:
        def _stage_state(done_at, active_at):
            if pct >= done_at:
                return "done"
            if pct >= active_at:
                return "active"
            return "pending"

        stage_defs = [("Definición", 33, 1), ("Diseño y datos", 66, 33), ("Lanzamiento", 100, 66)]
        stats_html = "<div class='mod-stages'>"
        for label, done_at, active_at in stage_defs:
            state = _stage_state(done_at, active_at)
            stats_html += (
                f"<div class='mod-stage {state}'><span class='mod-stage-dot {state}'></span>"
                f"<span class='mod-stage-lbl'>{label}</span></div>"
            )
        stats_html += "</div>"
        foot_html = (
            "<div class='mod-panel-footrow'>"
            "<span class='mod-panel-note'>🛠️ Seguimos construyendo este módulo, paso a paso.</span>"
            "</div>"
        )

    st.markdown("<div class='sel-eyebrow'><span class='dot'></span>Módulo seleccionado</div>", unsafe_allow_html=True)
    panel_html = (
        f"<div class='mod-panel' style='--ac1:{m['ac1']};--ac2:{m['ac2']};--icobg:{m['icobg']};--acbord:{m['acbord']};--pct:{pct}'>"
        "<div class='mod-panel-glow'></div>"
        "<div class='mod-panel-glow2'></div>"
        f"<div class='mod-panel-watermark'>{m['icon']}</div>"
        "<div class='mod-panel-top'>"
        "<div style='position:relative'>"
        f"<div class='mod-panel-ico-ring'><div class='mod-panel-ico'>{m['icon']}</div></div>"
        f"<div class='mod-panel-ico-pct'>{pct}%</div>"
        "</div>"
        f"<span class='rail-status {badge_cls}' style='font-size:10px;padding:5px 12px'>"
        f"<span class='dot'></span>{m['status_label']}</span>"
        "</div>"
        f"<div class='mod-panel-title'><span class='grad'>{m['title']}</span></div>"
        f"<p class='mod-panel-desc'>{m['desc']}</p>"
        f"<div class='mod-panel-feats'>{feats_html}</div>"
        f"{stats_html}"
        "<div class='mod-panel-div'></div>"
        f"{foot_html}"
        "</div>"
    )
    st.markdown(panel_html, unsafe_allow_html=True)
    if st.button(m["cta"], key=f"panel_cta_{st.session_state.home_mod}", width="stretch",
                 type="primary" if m["status"] == "ok" else "secondary"):
        st.switch_page(m["page"])

# ── STATS ─────────────────────────────────
st.markdown("""
<div class='stats'>
    <div class='stat' style='--sc:#38BDF8'>
        <div class='stat-ico'>📝</div>
        <div class='stat-val'>1</div>
        <div class='stat-lbl'>Módulo Disponible</div>
    </div>
    <div class='stat' style='--sc:#34D399'>
        <div class='stat-ico'>📅</div>
        <div class='stat-val'>2026</div>
        <div class='stat-lbl'>Año en Curso</div>
    </div>
    <div class='stat' style='--sc:#A78BFA'>
        <div class='stat-ico'>🧩</div>
        <div class='stat-val'>4</div>
        <div class='stat-lbl'>Módulos Totales</div>
    </div>
    <div class='stat' style='--sc:#FBBF24'>
        <div class='stat-ico'>🤝</div>
        <div class='stat-val' style='font-size:22px'>Alianza</div>
        <div class='stat-lbl'>Uniminuto</div>
    </div>
</div>
""", unsafe_allow_html=True)
