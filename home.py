import streamlit as st
import base64

import _datos

COLOR_PRIMARY = "#28053F"
COLOR_ACCENT  = "#0EA5E9"

# objetos de página (mismos parámetros que en Dashboard.py → switch_page funciona)
insc_pg  = st.Page("pages/1_Inscripciones.py", title="Inscripciones", icon="📝")
mat_pg   = st.Page("pages/2_Matriculas.py",    title="Matrículas",    icon="🎓")
cuart_pg = st.Page("pages/3_Cuartiles.py",     title="Cuartiles",     icon="🏆")
cont_pg  = st.Page("pages/4_Contactabilidad.py", title="Real time", icon="📞")

_MODULOS = {
    "insc": dict(
        icon="📝", title="Inscripciones", page=insc_pg, tag="Comercial · embudo",
        desc="Embudo de inscripción, de prospecto a inscripción completa, por asesor, programa y período.",
        feats=["Embudo completo", "Ranking vs. meta", "Estado documental"],
        ac1="#0EA5E9", ac2="#6366F1",
        icobg="linear-gradient(135deg,rgba(14,165,233,0.28),rgba(99,102,241,0.12))",
        acbord="rgba(56,189,248,0.5)",
    ),
    "mat": dict(
        icon="🎓", title="Matrículas", page=mat_pg, tag="Comercial · matrícula",
        desc="Proceso de matrícula: período, paquete inscrito y estatus del alumno una vez completada la inscripción.",
        feats=["Avance vs. meta por supervisor", "Financiación y tipo de admisión", "Tendencia diaria"],
        ac1="#8B5CF6", ac2="#EC4899",
        icobg="linear-gradient(135deg,rgba(139,92,246,0.28),rgba(236,72,153,0.12))",
        acbord="rgba(167,139,250,0.5)",
    ),
    "cuart": dict(
        icon="🏆", title="Cuartiles", page=cuart_pg, tag="Desempeño de asesores",
        desc="Clasificación de asesores por desempeño en cuartiles, para reconocer a los mejores y reforzar a quienes lo necesitan.",
        feats=["Umbrales real vs. propuesto", "Ranking por cuartil", "Evolución de 6 meses"],
        ac1="#34D399", ac2="#059669",
        icobg="linear-gradient(135deg,rgba(52,211,153,0.28),rgba(5,150,105,0.12))",
        acbord="rgba(52,211,153,0.5)",
    ),
    "cont": dict(
        icon="📞", title="Real time", page=cont_pg, tag="Contacto en vivo",
        desc="Gestión de llamadas en tiempo real y cierre del día vencido: disposiciones, contacto efectivo, ritmo por hora y alertas.",
        feats=["Llamadas por hora", "Disposición por asesor", "Alertas del día"],
        ac1="#F97316", ac2="#F59E0B",
        icobg="linear-gradient(135deg,rgba(249,115,22,0.28),rgba(245,158,11,0.12))",
        acbord="rgba(249,115,22,0.5)",
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

_datos.boton_actualizar()

# ── CSS ──────────────────────────────────
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

    /* ══ FONDO GENERAL — plano, con un halo mínimo (sin dot-grid ni aurora) ══ */
    [data-testid="stAppViewContainer"] {{
        background:
            radial-gradient(ellipse 100% 55% at 6% -12%,  rgba(14,165,233,0.10) 0%, transparent 60%),
            radial-gradient(ellipse 90% 55% at 100% -6%,   rgba(99,102,241,0.09) 0%, transparent 60%),
            linear-gradient(160deg, #071310 0%, #082017 48%, #050F0B 100%);
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    .block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1200px; }}

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

    /* ══ SIDEBAR ══ */
    section[data-testid="stSidebar"] > div:first-child {{
        background:
            radial-gradient(ellipse 95% 42% at 8% 0%,    rgba(14,165,233,0.30) 0%, transparent 55%),
            radial-gradient(ellipse 90% 42% at 100% 26%, rgba(129,140,248,0.28) 0%, transparent 55%),
            radial-gradient(ellipse 85% 42% at 50% 102%, rgba(52,211,153,0.15) 0%, transparent 55%),
            linear-gradient(160deg, #071811 0%, #0C2B1D 45%, #061109 100%);
        border-right: 1px solid rgba(255,255,255,0.07);
    }}
    div[data-testid="stSidebarContent"] * {{ color: white !important; }}
    [data-testid="stSidebarHeader"] {{ padding-top:0.1rem!important; padding-bottom:0!important; min-height:0!important; }}
    section[data-testid="stSidebar"] .block-container {{ padding-top:0.5rem!important; padding-bottom:0.8rem!important; }}
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

    @keyframes sbcBar {{ 0% {{ background-position:0% 0%; }} 100% {{ background-position:200% 0%; }} }}
    @keyframes sbcPulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:.3; transform:scale(.6); }} }}
    @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(14px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes ring {{ 0% {{ transform:scale(.85); opacity:.55; }} 100% {{ transform:scale(1.7); opacity:0; }} }}
    @keyframes shimmer {{ 0% {{ background-position:-200% 0; }} 100% {{ background-position:200% 0; }} }}
    @keyframes auroraMove {{
        0%   {{ transform:translate(0,0) scale(1); }}
        33%  {{ transform:translate(36px,-26px) scale(1.12); }}
        66%  {{ transform:translate(-26px,22px) scale(0.93); }}
        100% {{ transform:translate(0,0) scale(1); }} }}
    @keyframes nticker {{ 0% {{ transform:translateX(0); }} 100% {{ transform:translateX(-50%); }} }}
    @media (prefers-reduced-motion:reduce) {{
        .hero-aurora, .nticker-inner, .hero-title .grad {{ animation:none !important; }} }}

    /* ══════════ HERO ══════════ */
    .hero {{ position:relative;border-radius:26px;overflow:hidden;padding:32px 48px 28px;text-align:center;margin-bottom:16px;
        background:linear-gradient(135deg,rgba(255,255,255,0.075) 0%,rgba(255,255,255,0.02) 100%);
        border:1px solid rgba(255,255,255,0.11);
        box-shadow:0 28px 80px -30px rgba(0,0,0,0.55),inset 0 1px 0 rgba(255,255,255,0.10);
        animation:fadeUp 0.6s ease both; }}
    .hero-aurora {{ position:absolute;border-radius:50%;filter:blur(54px);pointer-events:none;z-index:0; }}
    .ha1 {{ width:400px;height:400px;background:radial-gradient(circle,rgba(14,165,233,0.42),transparent 65%);top:-160px;left:-110px;animation:auroraMove 16s ease-in-out infinite; }}
    .ha2 {{ width:360px;height:360px;background:radial-gradient(circle,rgba(129,140,248,0.40),transparent 65%);bottom:-170px;right:-80px;animation:auroraMove 20s ease-in-out infinite reverse; }}
    .ha3 {{ width:250px;height:250px;background:radial-gradient(circle,rgba(52,211,153,0.28),transparent 65%);top:22%;right:14%;animation:auroraMove 24s ease-in-out infinite; }}
    .hero-inner {{ position:relative;z-index:1; }}
    .hero-badge {{ display:inline-flex;align-items:center;gap:9px;background:rgba(52,211,153,0.08);
        border:1px solid rgba(52,211,153,0.28);border-radius:99px;padding:7px 20px;margin-bottom:22px;
        font-size:10px;font-weight:700;color:rgba(255,255,255,0.80);letter-spacing:0.14em;text-transform:uppercase; }}
    .hero-badge-dot {{ position:relative;width:8px;height:8px; }}
    .hero-badge-dot::after {{ content:'';position:absolute;inset:0;border-radius:50%;background:#34D399; }}
    .hero-badge-dot::before {{ content:'';position:absolute;inset:0;border-radius:50%;border:2px solid #34D399;animation:ring 1.8s ease-out infinite; }}
    .hero-title {{ font-family:'Space Grotesk',sans-serif!important;font-size:42px;font-weight:800;color:white;
        margin:0 0 12px;letter-spacing:-1.6px;line-height:1.04; }}
    .hero-title .grad {{ background:linear-gradient(90deg,#38BDF8 0%,#818CF8 35%,#34D399 70%,#38BDF8 100%);
        background-size:220% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;animation:shimmer 5s linear infinite; }}
    .hero-sub {{ font-size:14.5px;color:rgba(255,255,255,0.60);max-width:560px;margin:0 auto;line-height:1.66; }}
    .hero-divider {{ width:52px;height:1.5px;margin:20px auto 18px;border-radius:2px;
        background:linear-gradient(90deg,transparent,rgba(56,189,248,0.55),rgba(129,140,248,0.55),transparent); }}
    .hero-cards {{ display:flex;justify-content:center;gap:10px;flex-wrap:wrap; }}
    .hcard {{ display:flex;align-items:center;gap:12px;min-width:150px;background:rgba(255,255,255,0.05);
        border:1px solid rgba(255,255,255,0.09);border-top:2px solid var(--hc,rgba(56,189,248,0.50));
        border-radius:15px;padding:13px 18px;
        box-shadow:0 8px 26px -12px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,255,255,0.06);
        transition:transform .22s cubic-bezier(.2,.8,.2,1),background .22s ease; }}
    .hcard:hover {{ transform:translateY(-4px);background:rgba(255,255,255,0.09); }}
    .hcard-ico {{ width:42px;height:42px;border-radius:12px;flex-shrink:0;display:flex;align-items:center;justify-content:center;
        font-size:19px;background:var(--hc-bg,rgba(56,189,248,0.12));border:1px solid var(--hc,rgba(56,189,248,0.22)); }}
    .hcard-txt {{ text-align:left; }}
    .hcard-lbl {{ font-size:8.5px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
        color:var(--hc,rgba(56,189,248,0.80));margin-bottom:4px;display:block; }}
    .hcard-val {{ font-size:14.5px;font-weight:800;color:white;line-height:1;display:block; }}
    .hcard-val .dot {{ display:inline-block;width:7px;height:7px;border-radius:50%;background:#34D399;
        box-shadow:0 0 10px #34D399;margin-right:6px;animation:sbcPulse 1.8s ease-in-out infinite; }}

    /* ══ TICKER ══ */
    .nticker-shell {{ display:flex;align-items:stretch;overflow:hidden;border-radius:14px;
        background:rgba(245,158,11,0.04);border:1px solid rgba(245,158,11,0.22);
        box-shadow:inset 0 1px 0 rgba(255,255,255,0.05);margin:0 0 6px; }}
    .nticker-label {{ flex-shrink:0;display:flex;align-items:center;gap:8px;padding:11px 17px;
        font-size:8.5px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:#F59E0B;
        background:linear-gradient(135deg,rgba(245,158,11,0.18),rgba(245,158,11,0.08));
        border-right:1px solid rgba(245,158,11,0.22); }}
    .nticker-dot {{ width:7px;height:7px;border-radius:50%;background:#F59E0B;box-shadow:0 0 8px #F59E0B;
        animation:sbcPulse 1.8s ease-in-out infinite;flex-shrink:0; }}
    .nticker-track {{ overflow:hidden;flex:1;
        mask-image:linear-gradient(90deg,transparent 0%,black 5%,black 95%,transparent 100%);
        -webkit-mask-image:linear-gradient(90deg,transparent 0%,black 5%,black 95%,transparent 100%); }}
    .nticker-inner {{ display:flex;width:max-content;animation:nticker 40s linear infinite;padding:11px 0; }}
    .nticker-inner:hover {{ animation-play-state:paused; }}
    .nticker-item {{ display:flex;align-items:center;gap:10px;padding:0 44px;white-space:nowrap;
        font-size:12.5px;color:rgba(255,255,255,0.66);font-weight:500; }}
    .nticker-sep {{ color:rgba(245,158,11,0.35);font-size:17px;margin-left:6px; }}
    .ntag {{ font-size:8px;font-weight:800;padding:3px 8px;border-radius:5px;text-transform:uppercase;letter-spacing:0.09em;flex-shrink:0; }}
    .ntag-u {{ background:rgba(14,165,233,0.18);color:#38BDF8;border:1px solid rgba(14,165,233,0.28); }}
    .ntag-n {{ background:rgba(52,211,153,0.18);color:#34D399;border:1px solid rgba(52,211,153,0.28); }}
    .ntag-p {{ background:rgba(245,158,11,0.18);color:#FCD34D;border:1px solid rgba(245,158,11,0.28); }}

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

    /* ══════════ PORTADA — foco + tira lateral ══════════ */
    .hm-eyebrow {{ display:flex;align-items:center;gap:11px;margin:26px 0 18px;
        font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:rgba(255,255,255,0.42); }}
    .hm-eyebrow::before {{ content:'';width:24px;height:2px;border-radius:2px;background:linear-gradient(90deg,#38BDF8,#818CF8); }}
    .hm-eyebrow::after {{ content:'';flex:1;height:1px;background:linear-gradient(90deg,rgba(255,255,255,0.12),transparent); }}

    /* riel y foco a la misma altura */
    div[data-testid="stHorizontalBlock"]:has(.st-key-hm_focus_wrap) {{ align-items:stretch; }}
    div[data-testid="stHorizontalBlock"]:has(.st-key-hm_focus_wrap) > div[data-testid="stColumn"] {{ display:flex;flex-direction:column; }}
    div[data-testid="stHorizontalBlock"]:has(.st-key-hm_focus_wrap) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {{ flex:1 1 auto;display:flex;flex-direction:column; }}
    .st-key-hm_focus_wrap {{ flex:1 1 auto;display:flex;flex-direction:column; }}
    .st-key-hm_focus_wrap [data-testid="stElementContainer"]:first-child {{ flex:1 1 auto;display:flex; }}

    /* -- tira lateral -- */
    .st-key-hm_rail_insc, .st-key-hm_rail_mat, .st-key-hm_rail_cuart, .st-key-hm_rail_cont {{
        position:relative;border-radius:16px;padding:15px 16px 13px;margin-bottom:12px;overflow:hidden;
        min-height:102px;box-sizing:border-box;
        display:flex;flex-direction:column;
        background:linear-gradient(160deg,rgba(255,255,255,0.055) 0%,rgba(255,255,255,0.015) 100%);
        border:1px solid rgba(255,255,255,0.10);border-left:2px solid var(--ac1);
        transition:border-color .25s ease,background .25s ease;
    }}
    .st-key-hm_rail_insc  {{ --ac1:#0EA5E9;--icobg:linear-gradient(135deg,rgba(14,165,233,0.28),rgba(99,102,241,0.12));--acbord:rgba(56,189,248,0.5); }}
    .st-key-hm_rail_mat   {{ --ac1:#8B5CF6;--icobg:linear-gradient(135deg,rgba(139,92,246,0.28),rgba(236,72,153,0.12));--acbord:rgba(167,139,250,0.5); }}
    .st-key-hm_rail_cuart {{ --ac1:#34D399;--icobg:linear-gradient(135deg,rgba(52,211,153,0.28),rgba(5,150,105,0.12));--acbord:rgba(52,211,153,0.5); }}
    .st-key-hm_rail_cont  {{ --ac1:#F97316;--icobg:linear-gradient(135deg,rgba(249,115,22,0.28),rgba(245,158,11,0.12));--acbord:rgba(249,115,22,0.5); }}
    .st-key-hm_rail_insc:hover, .st-key-hm_rail_mat:hover, .st-key-hm_rail_cuart:hover, .st-key-hm_rail_cont:hover {{
        transform:translateY(-2px);border-color:var(--acbord); }}
    .st-key-hm_rail_insc:has(.ri-on), .st-key-hm_rail_mat:has(.ri-on),
    .st-key-hm_rail_cuart:has(.ri-on), .st-key-hm_rail_cont:has(.ri-on) {{
        border-color:var(--acbord);
        background:linear-gradient(160deg,rgba(255,255,255,0.11) 0%,rgba(255,255,255,0.03) 100%);
        box-shadow:0 16px 34px -18px var(--ac1); }}
    .ri-top {{ display:flex;align-items:center;gap:9px;margin-bottom:9px; }}
    .ri-ico {{ width:30px;height:30px;flex-shrink:0;border-radius:9px;display:flex;align-items:center;justify-content:center;
        font-size:15px;background:var(--icobg);border:1px solid var(--acbord); }}
    .ri-name {{ font-family:'Space Grotesk',sans-serif!important;font-weight:700;font-size:12.5px;color:white;letter-spacing:-0.2px; }}
    .ri-cifra {{ font-family:'Space Grotesk',sans-serif!important;font-weight:700;font-size:17px;color:white;line-height:1;font-variant-numeric:tabular-nums; }}
    .ri-sub {{ font-size:9.5px;color:rgba(255,255,255,0.42);margin-top:3px; }}

    .st-key-hm_rail_insc div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]),
    .st-key-hm_rail_mat div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]),
    .st-key-hm_rail_cuart div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]),
    .st-key-hm_rail_cont div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]) {{ margin-top:auto; }}
    .st-key-hm_rail_insc div[data-testid="stButton"], .st-key-hm_rail_mat div[data-testid="stButton"],
    .st-key-hm_rail_cuart div[data-testid="stButton"], .st-key-hm_rail_cont div[data-testid="stButton"] {{ margin-top:10px; }}
    .st-key-hm_rail_insc div[data-testid="stButton"] > button, .st-key-hm_rail_mat div[data-testid="stButton"] > button,
    .st-key-hm_rail_cuart div[data-testid="stButton"] > button, .st-key-hm_rail_cont div[data-testid="stButton"] > button {{
        height:32px!important;min-height:32px!important;padding:0 10px!important;border-radius:9px!important;
        background:rgba(255,255,255,0.035)!important;border:1px solid rgba(255,255,255,0.12)!important;box-shadow:none!important;
        color:rgba(255,255,255,0.62)!important;font-size:10px!important;font-weight:700!important;
        justify-content:center!important;letter-spacing:0.03em!important;transition:all .18s ease!important; }}
    .st-key-hm_rail_insc div[data-testid="stButton"] > button:hover, .st-key-hm_rail_mat div[data-testid="stButton"] > button:hover,
    .st-key-hm_rail_cuart div[data-testid="stButton"] > button:hover, .st-key-hm_rail_cont div[data-testid="stButton"] > button:hover {{
        background:var(--icobg)!important;border-color:var(--acbord)!important;color:#fff!important; }}
    .st-key-hm_rail_insc:has(.ri-on) div[data-testid="stButton"] > button, .st-key-hm_rail_mat:has(.ri-on) div[data-testid="stButton"] > button,
    .st-key-hm_rail_cuart:has(.ri-on) div[data-testid="stButton"] > button, .st-key-hm_rail_cont:has(.ri-on) div[data-testid="stButton"] > button {{
        background:var(--icobg)!important;border-color:var(--acbord)!important;color:#fff!important; }}
    .st-key-hm_rail_insc div[data-testid="stButton"] > button p, .st-key-hm_rail_mat div[data-testid="stButton"] > button p,
    .st-key-hm_rail_cuart div[data-testid="stButton"] > button p, .st-key-hm_rail_cont div[data-testid="stButton"] > button p {{ text-align:center!important; }}

    /* -- panel de foco -- */
    .hm-focus {{ position:relative;overflow:hidden;border-radius:24px;padding:30px 34px 26px;
        min-height:392px;box-sizing:border-box;
        background:linear-gradient(160deg,rgba(255,255,255,0.075) 0%,rgba(255,255,255,0.02) 100%);
        border:1px solid rgba(255,255,255,0.10);border-top:3px solid var(--ac1);
        box-shadow:0 24px 60px -26px rgba(0,0,0,0.55),inset 0 1px 0 rgba(255,255,255,0.08);
        flex:1 1 auto;display:flex;flex-direction:column;animation:fadeUp .4s ease both; }}
    .hm-focus-glow {{ position:absolute;top:-100px;right:-90px;width:260px;height:260px;border-radius:50%;
        background:radial-gradient(circle,var(--ac1),transparent 70%);opacity:0.16;pointer-events:none; }}
    .hm-tag {{ display:inline-flex;align-items:center;gap:7px;font-size:9px;font-weight:800;letter-spacing:0.12em;
        text-transform:uppercase;color:var(--ac1);position:relative;z-index:1; }}
    .hm-tag::before {{ content:'';width:6px;height:6px;border-radius:50%;background:var(--ac1);box-shadow:0 0 8px var(--ac1); }}
    .hm-name {{ font-family:'Space Grotesk',sans-serif!important;font-size:30px;font-weight:700;color:white;
        letter-spacing:-0.6px;margin:10px 0 10px;position:relative;z-index:1; }}
    .hm-desc {{ font-size:13.5px;color:rgba(255,255,255,0.58);line-height:1.7;max-width:52ch;margin:0 0 22px;position:relative;z-index:1; }}
    .hm-big {{ font-family:'Space Grotesk',sans-serif!important;font-size:52px;font-weight:700;color:white;
        line-height:1;letter-spacing:-0.03em;position:relative;z-index:1;font-variant-numeric:tabular-nums; }}
    .hm-bigk {{ font-size:10px;color:rgba(255,255,255,0.46);text-transform:uppercase;letter-spacing:0.07em;
        margin:9px 0 18px;position:relative;z-index:1; }}
    .hm-chart {{ display:flex;align-items:flex-end;gap:4px;height:60px;margin-bottom:22px;position:relative;z-index:1; }}
    .hm-chart span {{ flex:1;border-radius:3px 3px 0 0;background:var(--ac1);opacity:0.42;min-height:3px; }}
    .hm-chart span:last-child {{ opacity:0.9; }}
    .hm-feats {{ display:flex;flex-wrap:wrap;gap:8px;margin-top:auto;position:relative;z-index:1; }}
    .hm-feat {{ font-size:11px;color:rgba(255,255,255,0.82);background:var(--icobg);
        border:1px solid rgba(255,255,255,0.12);padding:6px 12px;border-radius:9px;font-weight:600;
        display:inline-flex;align-items:center;gap:7px; }}
    .hm-feat::before {{ content:'';width:5px;height:5px;border-radius:50%;background:var(--ac1);box-shadow:0 0 6px var(--ac1);flex-shrink:0; }}

    /* ══ BOTÓN CTA ══ */
    .st-key-hm_cta div[data-testid="stButton"] > button {{
        border-radius:14px!important;font-family:'Space Grotesk',sans-serif!important;font-weight:700!important;font-size:14px!important;
        height:50px!important;letter-spacing:0.01em!important;color:white!important;border:none!important;
        transition:transform .2s ease,box-shadow .2s ease,filter .2s ease!important; }}
    .st-key-hm_cta div[data-testid="stButton"] > button:hover {{
        transform:translateY(-3px)!important;filter:brightness(1.08)!important; }}
</style>
""", unsafe_allow_html=True)

# ── ESTADO ───────────────────────────────
if "home_mod" not in st.session_state:
    st.session_state.home_mod = "insc"


def _barras(serie, n=18):
    """serie de enteros → alturas 6..100 (%). Serie vacía → mini onda plana."""
    serie = list(serie or [])[-n:]
    if not serie or max(serie) == 0:
        return [10, 14, 11, 16, 13, 18, 15, 20, 17, 22]
    tope = max(serie)
    return [max(6, round(v / tope * 100)) for v in serie]


# ── HERO ─────────────────────────────────
st.markdown("""
<div class='hero'>
    <div class='hero-aurora ha1'></div>
    <div class='hero-aurora ha2'></div>
    <div class='hero-aurora ha3'></div>
    <div class='hero-inner'>
        <div class='hero-badge'><span class='hero-badge-dot'></span>Centro de Control · Uniminuto · 2026</div>
        <div class='hero-title'>Dashboard&nbsp;<span class='grad'>Operativo</span></div>
        <div class='hero-sub'>Plataforma de análisis del proceso comercial y académico.
        Inscripciones, matrículas, cuartiles y real&nbsp;time desde una sola base consolidada.</div>
        <div class='hero-divider'></div>
        <div class='hero-cards'>
            <div class='hcard' style='--hc:rgba(52,211,153,0.70);--hc-bg:rgba(52,211,153,0.13)'>
                <div class='hcard-ico'>⚡</div>
                <div class='hcard-txt'><span class='hcard-lbl'>Estado del sistema</span>
                <span class='hcard-val'><span class='dot'></span>En línea</span></div>
            </div>
            <div class='hcard' style='--hc:rgba(56,189,248,0.70);--hc-bg:rgba(56,189,248,0.13)'>
                <div class='hcard-ico'>◈</div>
                <div class='hcard-txt'><span class='hcard-lbl'>Seguimiento</span>
                <span class='hcard-val'>Por asesor</span></div>
            </div>
            <div class='hcard' style='--hc:rgba(129,140,248,0.70);--hc-bg:rgba(129,140,248,0.13)'>
                <div class='hcard-ico'>◷</div>
                <div class='hcard-txt'><span class='hcard-lbl'>Período activo</span>
                <span class='hcard-val'>2026</span></div>
            </div>
            <div class='hcard' style='--hc:rgba(245,158,11,0.70);--hc-bg:rgba(245,158,11,0.13)'>
                <div class='hcard-ico'>✦</div>
                <div class='hcard-txt'><span class='hcard-lbl'>Alianza</span>
                <span class='hcard-val'>Uniminuto</span></div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

_TICK = (
    "<div class='nticker-item'><span class='ntag ntag-n'>Nuevo</span>"
    "Real time ya disponible — llamadas en vivo y cierre del día vencido<span class='nticker-sep'>·</span></div>"
    "<div class='nticker-item'><span class='ntag ntag-u'>Base 2026</span>"
    "Inscripciones, Matrículas y Cuartiles sobre base mensual consolidada<span class='nticker-sep'>·</span></div>"
    "<div class='nticker-item'><span class='ntag ntag-p'>Cuartiles</span>"
    "Histórico de 6 meses y umbrales real vs. propuesto<span class='nticker-sep'>·</span></div>"
)
st.markdown(
    "<div class='nticker-shell'><div class='nticker-label'><span class='nticker-dot'></span>En vivo</div>"
    "<div class='nticker-track'><div class='nticker-inner'>" + _TICK + _TICK + "</div></div></div>",
    unsafe_allow_html=True,
)

# ── PORTADA ──────────────────────────────
st.markdown("<div class='hm-eyebrow'>Módulos disponibles</div>", unsafe_allow_html=True)

rail_col, focus_col = st.columns([1, 2.35], gap="medium")

with rail_col:
    for key, m in _MODULOS.items():
        active = st.session_state.home_mod == key
        with st.container(key=f"hm_rail_{key}"):
            on = "<div class='ri-on'></div>" if active else ""
            st.markdown(
                f"<div class='ri-top'><span class='ri-ico'>{m['icon']}</span>"
                f"<span class='ri-name'>{m['title']}</span></div>"
                f"<div class='ri-sub'>{m['tag']}</div>{on}",
                unsafe_allow_html=True,
            )
            if st.button("● Seleccionado" if active else "Ver",
                         key=f"hm_railbtn_{key}", width="stretch"):
                st.session_state.home_mod = key
                st.rerun()

with focus_col:
    sel = st.session_state.home_mod
    m = _MODULOS[sel]
    with st.spinner("Cargando indicador…"):
        r = _datos.cifra_modulo(sel)
    bars = "".join(f"<span style='height:{h}%'></span>" for h in _barras(r.get("serie")))
    feats = "".join(f"<span class='hm-feat'>{f}</span>" for f in m["feats"])

    with st.container(key="hm_focus_wrap"):
        st.markdown(
            f"<div class='hm-focus' style='--ac1:{m['ac1']};--icobg:{m['icobg']}'>"
            "<div class='hm-focus-glow'></div>"
            "<div class='hm-tag'>Indicador principal</div>"
            f"<div class='hm-name'>{m['title']}</div>"
            f"<p class='hm-desc'>{m['desc']}</p>"
            f"<div class='hm-big'>{r.get('cifra', '—')}</div>"
            f"<div class='hm-bigk'>{r.get('sub', '')}</div>"
            f"<div class='hm-chart'>{bars}</div>"
            f"<div class='hm-feats'>{feats}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with st.container(key="hm_cta"):
        st.markdown(
            "<style>.st-key-hm_cta div[data-testid='stButton']>button{"
            f"background:linear-gradient(120deg,{m['ac1']},{m['ac2']})!important;"
            f"box-shadow:0 12px 32px -8px {m['ac1']}!important;}}"
            "</style>", unsafe_allow_html=True,
        )
        if st.button(f"Abrir módulo de {m['title']}  →", key=f"hm_cta_{sel}",
                     width="stretch", type="primary"):
            st.switch_page(m["page"])
