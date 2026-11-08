"""Promo Finder: upload microdrama screenplays, get ranked promo clips, review them.
Run locally:  python -m streamlit run app.py"""
import csv, html, io, json, os, zipfile
from collections import Counter

import streamlit as st

st.set_page_config(page_title="Promo Finder", page_icon=":material/play_circle:", layout="wide", initial_sidebar_state="expanded")

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600&display=swap');
__VARS__
html,body,[data-testid="stApp"]{background:var(--bg);color:var(--text);font-family:'Poppins',sans-serif}
[data-testid="stDecoration"],[data-testid="stMainMenu"],[data-testid="stStatusWidget"],.stAppDeployButton,.stDeployButton,#MainMenu,footer{display:none!important}
[data-testid="stExpandSidebarButton"],[data-testid="stSidebarCollapseButton"] button{opacity:1!important;visibility:visible!important}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:2.9rem;max-width:1180px}
[data-testid="stSidebar"],[data-testid="stSidebar"]>div{background:var(--surface)!important;border-right:1px solid var(--line)}
h1,h2,h3{font-family:'Poppins',sans-serif!important;font-weight:600!important;letter-spacing:-.01em}
.eyebrow{font:700 11px 'Poppins',sans-serif;letter-spacing:.22em;text-transform:uppercase;color:var(--accent)}
.hero h1{font-family:'Poppins',sans-serif;font-weight:600;font-size:2.7rem;line-height:1.05;margin:.35rem 0 .6rem;color:var(--text)}
.hero h1 em{font-style:italic;color:var(--gold)}
.hero{margin-bottom:1.6rem}.hero p,.hero [data-testid="stMarkdownContainer"] p{color:var(--accent)!important;font-weight:500;max-width:640px;font-size:1.02rem;line-height:1.55;margin:0}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:1.6rem 0 .6rem}
.stat{background:var(--surface);padding:16px 18px}
.stat b{display:block;font:600 1.7rem 'Poppins',sans-serif;color:var(--text)}
.stat span{font:500 10.5px 'Poppins',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin:18px 0 6px}
.card.top{border-color:var(--topline);box-shadow:0 0 0 1px rgba(34,184,196,.18)}
.row{display:flex;gap:22px;align-items:flex-start}
.rank{font:700 3.2rem/1 'Poppins',sans-serif;color:var(--accent);min-width:74px}
.grow{flex:1;min-width:0}
.meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
.clip{font:500 13px 'Poppins',sans-serif;color:var(--text)}
.chip{font:500 10.5px 'Poppins',sans-serif;letter-spacing:.08em;text-transform:uppercase;padding:3px 9px;border-radius:99px;border:1px solid var(--line);color:var(--muted)}
.chip.warn{color:var(--warn);border-color:var(--warnline)}.chip.gold{color:var(--gold);border-color:var(--goldline)}.chip.ok{color:var(--ok);border-color:var(--okline)}.chip.bad{color:var(--bad);border-color:var(--badline)}
.ring{width:62px;height:62px;border-radius:50%;display:grid;place-items:center;flex:none}
.ring i{width:48px;height:48px;border-radius:50%;background:var(--surface);display:grid;place-items:center;font:600 1.05rem 'Poppins',sans-serif;font-style:normal;color:var(--text)}
.beat{border-left:2px solid var(--line);padding:2px 0 2px 14px;margin:10px 0}
.beat.hook{border-color:var(--accent)}.beat.cliff{border-color:var(--gold)}
.beat small{font:500 10.5px 'Poppins',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.beat q{display:block;font:italic 400 1.12rem/1.45 'Poppins',sans-serif;color:var(--text);quotes:none;margin-top:2px}
.why{color:var(--muted);font-size:.93rem;line-height:1.55;margin:12px 0 4px}
.read{color:var(--muted);font-size:.84rem;margin-top:8px}.read b{color:var(--text);font-weight:500}
.bars{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-top:16px}
.bar small{font:500 10px 'Poppins',sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);display:flex;justify-content:space-between}
.bar div{height:5px;border-radius:9px;background:var(--line);margin-top:6px;overflow:hidden}.bar div i{display:block;height:100%;background:var(--accent)}
.tl{margin-top:14px}.tl small{font:500 10px 'Poppins',sans-serif;color:var(--muted);letter-spacing:.1em}
.tl div{position:relative;height:8px;border-radius:9px;background:var(--line);margin:5px 0 8px}.tl div i{position:absolute;top:0;height:100%;border-radius:9px;background:var(--gold)}
.tx{font:400 12.5px/1.65 'Poppins',sans-serif;color:var(--muted)}
.tx p{margin:2px 0}.tx .t{color:var(--faint);margin-right:10px}.tx .who{color:var(--text)}.tx .act{font-style:italic}
.tx .h{background:rgba(34,184,196,.16);border-radius:5px;padding:1px 5px}.tx .c{background:rgba(217,164,65,.16);border-radius:5px;padding:1px 5px}
.stButton>button{border-radius:9px;border:1px solid var(--line);background:transparent;color:var(--text);font:500 .85rem 'Poppins',sans-serif;padding:.35rem .9rem}
.stButton>button:hover{border-color:var(--accent);color:var(--text)}
.stButton>button[kind="primary"]{background:var(--accent);border-color:var(--accent);color:#fff}
.stTabs [data-baseweb="tab-list"]{gap:26px;border-bottom:1px solid var(--line)}
.stTabs [data-baseweb="tab"]{background:transparent;font:500 .92rem 'Poppins',sans-serif;color:var(--muted);padding:10px 0}
.stTabs [aria-selected="true"]{color:var(--text)}
div[data-testid="stExpander"]{border:1px solid var(--line);border-radius:10px;background:transparent}
.empty{border:1px dashed var(--line);border-radius:14px;padding:46px 30px;text-align:center;color:var(--muted);margin-top:1.4rem}
.empty b{display:block;font:600 1.4rem 'Poppins',sans-serif;color:var(--text);margin-bottom:6px}
.rowline{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding:9px 0;font-size:.92rem}.rowline span:last-child{font-family:'Poppins',sans-serif;color:var(--gold)}
@media(max-width:800px){.stats{grid-template-columns:repeat(2,1fr)}.bars{grid-template-columns:repeat(2,1fr)}.hero h1{font-size:2.2rem}.row{flex-direction:column;gap:8px}}
</style>"""

THEMES = {
    True: dict(bg="#050a0b", surface="#0a1618", surface2="#0e1f22", line="#15343a", text="#e4f1f1", muted="#7ea8ae", faint="#4d7479",
               accent="#1c9aa6", edge="#2a6670", gold="#d9a441", ok="#86b07f", bad="#b9534a", warn="#e0a458", warnline="#5b4526", goldline="#5b4a22",
               okline="#1f4a3c", badline="#4d2a2c", topline="#1f4f56", track="#0f2428"),
    False: dict(bg="#f3f9f9", surface="#ffffff", surface2="#e8f3f4", line="#cfe3e6", text="#0f2427", muted="#4d6f75", faint="#86a5aa",
                accent="#0e7f8c", edge="#6fa3ab", gold="#b07a14", ok="#3f7a4a", bad="#b03a30", warn="#a8661a", warnline="#e6cfa6", goldline="#e3cd9a",
                okline="#b5d3b8", badline="#e8b9b3", topline="#a3d6dc", track="#dcebed"),
}
st.session_state.setdefault("dark", st.query_params.get("theme", "dark") != "light")
T = THEMES[bool(st.session_state["dark"])]
TRACK, MUTED, GOLD = T["track"], T["muted"], T["gold"]

@st.cache_data
def watermark(rgb, peak):
    """1.png (black clapper on grey) as a transparent, tinted, very faint background mark."""
    import base64
    from PIL import Image
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "1.png")
    if not os.path.exists(path):
        return ""
    g = Image.open(path).convert("L")
    bg = sorted(g.getdata())[len(g.getdata()) // 2]  # the flat grey backdrop is the most common tone
    a = g.point(lambda v: int(min(1, max(0, bg - v - 12) / max(bg - 12, 1)) * 255 * peak))
    im = Image.new("RGBA", g.size, rgb + (0,)); im.putalpha(a)
    im = im.crop(a.point(lambda v: 255 if v > 2 else 0).getbbox() or (0, 0) + g.size)  # trim padding so it centres on the artwork
    buf = io.BytesIO(); im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


WM = watermark((90, 200, 210), .07) if st.session_state["dark"] else watermark((14, 127, 140), .07)
EXTRA = """<style>
html,body,[data-testid="stApp"],[data-testid="stApp"] *:not([data-testid="stIconMaterial"]):not([class*="material"]){font-family:'Poppins',sans-serif}
[data-testid="stApp"],[data-testid="stHeader"]{background:var(--bg)!important;color:var(--text)}
[data-testid="stHeader"]{background:transparent!important}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stWidgetLabel"] *,[data-testid="stRadio"] label *,
[data-testid="stToggle"] label *,[data-testid="stExpander"] summary *,[data-testid="stStatus"] summary *,[data-testid="stAlert"] *{color:var(--text)}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] *{color:var(--muted)!important;opacity:1!important}
[data-testid="stSidebar"] hr{border-color:var(--line)}
input,textarea,[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{background:var(--surface2)!important;color:var(--text)!important;border-color:var(--line)!important}
[data-baseweb="popover"] [role="listbox"],[data-baseweb="popover"] ul{background:var(--surface)!important;color:var(--text)!important}
[data-testid="stFileUploaderDropzone"]{background:var(--surface);border:1px solid var(--line)}
[data-testid="stFileUploaderDropzone"] *{color:var(--muted)}
[data-testid="stFileUploaderDropzone"] button{background:transparent;color:var(--text);border:1px solid var(--line)}
.stDownloadButton>button{border-radius:9px;border:1px solid var(--line);background:transparent;color:var(--text)}
.stDownloadButton>button:hover{border-color:var(--accent)}
.stButton>button[kind="primary"] *{color:#fff!important}
.stButton>button *{color:inherit}
.brand{display:flex;align-items:center;gap:11px;margin:0 0 1.8rem}
.brand svg{flex:none}
.brand b{display:block;font:700 1.22rem/1.1 'Poppins',sans-serif;letter-spacing:-.01em;color:var(--text)}
.brand span{font:500 9.5px 'Poppins',sans-serif;letter-spacing:.24em;text-transform:uppercase;color:var(--muted)}
.topbar{display:flex;align-items:center;gap:12px;margin:-.6rem 0 1.4rem}
.st-key-dark{position:fixed;top:.45rem;right:4.6rem;z-index:1000001;width:auto!important}
.st-key-dark label{background:var(--surface);border:1px solid var(--line);border-radius:99px;padding:.35rem .95rem .35rem .75rem;box-shadow:none}
.st-key-dark label p{font:500 .8rem 'Poppins',sans-serif;color:var(--text)}
/* native widgets: force our palette so light mode has no dark leftovers */
[data-testid="stExpander"] details,[data-testid="stExpander"] summary,[data-testid="stStatus"] details,[data-testid="stStatus"] summary{background:var(--surface)!important;color:var(--text)!important;border-radius:10px}
[data-testid="stExpander"] summary svg,[data-testid="stStatus"] summary svg{color:var(--muted)!important;fill:var(--muted)!important}
[data-testid="stTextInputRootElement"],[data-testid="stTextAreaRootElement"],[data-testid="stNumberInputContainer"],[data-baseweb="select"]>div{background:var(--surface2)!important;border:1px solid var(--line)!important;border-radius:10px!important;overflow:hidden}
[data-testid="stTextInputRootElement"]:focus-within,[data-testid="stTextAreaRootElement"]:focus-within,[data-testid="stNumberInputContainer"]:focus-within{border-color:var(--accent)!important}
input::placeholder,textarea::placeholder{color:var(--faint)!important;opacity:1!important}
[data-baseweb="input"] *,[data-baseweb="base-input"] *{background:var(--surface2)!important;color:var(--text)!important}
[data-baseweb="input"] svg{fill:var(--muted)!important;color:var(--muted)!important}
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{border-color:var(--accent)!important}
[data-testid="stRadioOption"]>div>div>div:first-child{background:var(--surface)!important;border:1.5px solid var(--muted)!important;border-radius:50%}
[data-testid="stRadioOption"]>div>div>div:first-child>div{background:transparent!important}
[data-testid="stRadioOption"][data-selected="true"]>div>div>div:first-child>div{background:#fff!important}
[data-testid="stTextInputRootElement"] button,[data-testid="stTextInputRootElement"] svg{color:var(--muted)!important;fill:var(--muted)!important}
[data-testid="stSidebarCollapseButton"] *,[data-testid="stExpandSidebarButton"] *{color:var(--muted)!important;fill:var(--muted)!important}
[data-testid="stRadioOption"][data-selected="true"]>div>div>div:first-child{background:var(--accent)!important;border-color:var(--accent)!important}
[data-testid="stCheckbox"] label>div:first-of-type{background:var(--line)!important;border-radius:99px}
[data-testid="stCheckbox"] label:has(input:checked)>div:first-of-type{background:var(--accent)!important}
[data-testid="stCheckbox"] label>div:first-of-type>div{background:#fff!important;box-shadow:0 1px 3px rgba(0,0,0,.3)}
[data-testid="stNumberInput"] button{background:var(--surface2)!important;color:var(--text)!important;border:none}
[data-testid="stSlider"] [data-baseweb="slider"]>div>div:first-child{background:var(--line)}
[data-testid="stSlider"] [data-testid="stTickBar"] *,[data-testid="stSliderThumbValue"]{color:var(--accent)!important}
[data-testid="stStatus"],[data-testid="stExpander"]{border:1px solid var(--line)!important;border-radius:12px!important;background:var(--surface)!important}
[data-testid="stStatus"] summary{display:flex!important;align-items:center;gap:.6rem;min-height:2.6rem;overflow:hidden}
[data-testid="stStatus"] summary [data-testid="stMarkdownContainer"],[data-testid="stStatus"] summary [data-testid="stMarkdownContainer"] *{color:var(--text)!important;min-width:0;white-space:normal;line-height:1.35}
[data-testid="stStatus"] [data-testid="stMarkdownContainer"] *{color:var(--text)}
[data-testid="stStatus"],[data-testid="stStatus"]>div{background:var(--surface)!important;color:var(--text)!important}
[data-testid="stCode"],[data-testid="stCode"] pre,[data-testid="stCode"] code{background:var(--surface2)!important;color:var(--text)!important;white-space:pre-wrap!important;word-break:break-word}
[data-testid="stCode"]{border:1px solid var(--bad);border-radius:10px}
/* polish */
[data-testid="stApp"]{background:var(--bg)!important}
.card{box-shadow:none;transition:transform .15s,border-color .15s}
.card:hover{transform:translateY(-1px);border-color:var(--accent)}
.stButton>button[kind="primary"]{background:var(--accent);box-shadow:none;border:none;font-weight:600}
.stButton>button,.stDownloadButton>button{transition:all .15s}
[data-testid="stSidebar"] .eyebrow{margin:6px 0 8px}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding-top:1.4rem}
.hero{margin-top:.4rem}
</style>"""
st.markdown(CSS.replace("__VARS__", ":root{" + "".join(f"--{k}:{v};" for k, v in T.items()) + "}"), unsafe_allow_html=True)
st.markdown(EXTRA + (f'<style>[data-testid="stMain"]{{background:url({WM}) center center / min(620px,62%) no-repeat scroll}}</style>' if WM else ""), unsafe_allow_html=True)

LOGO = """<svg width="{s}" height="{s}" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-label="Promo Finder logo">
<defs><linearGradient id="pfg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1c9aa6"/><stop offset="1" stop-color="#1c9aa6"/></linearGradient></defs>
<rect width="48" height="48" rx="13" fill="url(#pfg)"/>
<path d="M19 13.5v15.2c0 1 1.1 1.6 1.9 1l11.4-7.6c.8-.5.8-1.6 0-2.1L20.9 12.5c-.8-.6-1.9 0-1.9 1z" fill="#fff"/>
<rect x="10" y="35" width="28" height="3.4" rx="1.7" fill="#fff" opacity=".35"/><rect x="15" y="35" width="13" height="3.4" rx="1.7" fill="#f3c25c"/></svg>"""
BRAND = '<div class="brand">' + LOGO.format(s=40) + '<div><b>Promo Finder</b><span>Microdrama clips</span></div></div>'


# ------------------------------------------------------------------ sidebar styling (inline SVG line icons, no assets)
ICONS = {
    "upload": '<polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>',
    "folder": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    "sliders": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    "filter": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "chevron": '<polyline points="6 9 12 15 18 9"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "check_sq": '<polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "note": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
}


def svg(name, size=14, sw=2):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def mask(name):
    """CSS url() of an icon, used as a mask so pseudo-elements can take the theme colour."""
    from urllib.parse import quote
    s = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' "
         f"stroke-linecap='round' stroke-linejoin='round'>{ICONS[name]}</svg>").replace('"', "'")
    return f'url("data:image/svg+xml,{quote(s)}")'


def sec(icon, text):
    return f'<div class="sec">{svg(icon, 14)}<span>{text}</span></div>'


SB_CSS = """<style>
@keyframes pfspin{to{transform:rotate(360deg)}}
[data-testid="stSidebar"]{overflow-x:hidden}
[data-testid="stElementContainer"]:has(style){display:none}
.sec{display:flex;align-items:center;gap:8px;margin:18px 0 10px;font:700 11px 'Poppins',sans-serif;letter-spacing:.2em;text-transform:uppercase;color:var(--accent)}
.sec svg{flex:none}
/* source cards: a real st.radio, restyled */
[data-testid="stSidebar"] [data-testid="stRadioGroup"]{gap:8px}
[data-testid="stSidebar"] [data-testid="stRadioOption"]{display:flex;width:100%;margin:0;padding:10px 13px;border:1.5px solid var(--edge);border-radius:12px;background:var(--surface);cursor:pointer;transition:border-color .15s,background .15s}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover{border-color:var(--accent)}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"]{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 13%,var(--surface))}
[data-testid="stSidebar"] [data-testid="stRadioOption"] :has(>[data-testid="stMarkdownContainer"]){display:flex;align-items:center;gap:11px;width:100%}
[data-testid="stSidebar"] [data-testid="stRadioOption"] :has(>[data-testid="stMarkdownContainer"])>div:not([data-testid="stMarkdownContainer"]){display:none!important}
[data-testid="stSidebar"] [data-testid="stRadioOption"] :has(>[data-testid="stMarkdownContainer"])::before{content:"";flex:none;width:18px;height:18px;background:var(--muted);-webkit-mask:var(--ico) center/contain no-repeat;mask:var(--ico) center/contain no-repeat}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] :has(>[data-testid="stMarkdownContainer"])::before{background:var(--accent)}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input[value="0"]){--ico:__UPLOAD__}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input[value="1"]){--ico:__FOLDER__}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p{font-weight:500;font-size:.88rem;white-space:nowrap}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p{font-weight:600}
/* model settings expander */
[data-testid="stSidebar"] [data-testid="stExpander"]{margin-top:12px;border:1.5px solid var(--edge)!important;transition:border-color .15s}
[data-testid="stSidebar"] [data-testid="stExpander"]:hover{border-color:var(--accent)!important}
[data-testid="stSidebar"] [data-testid="stExpander"] summary{padding:.7rem .8rem;position:relative;cursor:pointer}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover{background:var(--surface2)!important}
[data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stIconMaterial"]{display:none}
[data-testid="stSidebar"] [data-testid="stExpander"] summary>span{display:flex;align-items:center;gap:8px;width:100%;padding-right:22px;min-width:0}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p{font-size:.8rem;font-weight:500;line-height:1.25;white-space:normal;overflow:visible}
[data-testid="stSidebar"] [data-testid="stExpander"] summary>span::before{content:"";flex:none;width:17px;height:17px;background:var(--accent);-webkit-mask:__GEAR__ center/contain no-repeat;mask:__GEAR__ center/contain no-repeat}
[data-testid="stSidebar"] [data-testid="stExpander"] summary::after{content:"";position:absolute;right:.8rem;top:50%;width:16px;height:16px;margin-top:-8px;background:var(--muted);-webkit-mask:__CHEV__ center/contain no-repeat;mask:__CHEV__ center/contain no-repeat;transition:transform .2s}
[data-testid="stSidebar"] [data-testid="stExpander"] details[open]>summary::after{transform:rotate(180deg);background:var(--accent)}
[data-testid="stSidebar"] [data-testid="stExpander"] details[open]>summary{border-bottom:1px solid var(--edge);border-radius:10px 10px 0 0}
/* filters */
[data-testid="stSidebar"] [data-testid="stSlider"]{padding-bottom:0;margin-bottom:0}
[data-testid="stSidebar"] [data-testid="stSliderThumbValue"],[data-testid="stSidebar"] [data-testid="stSliderThumbValue"] *{color:var(--accent)!important;font-weight:700;font-size:.8rem}
[data-testid="stSidebar"] [data-testid="stSlider"] input[type="range"]{accent-color:var(--accent)}
[data-testid="stSidebar"] [data-testid="stCheckbox"] label p{font-size:.84rem;font-weight:500;line-height:1.3}
[data-testid="stFileChip"]{background:var(--surface2)!important;border:1px solid var(--line);border-radius:10px}
[data-testid="stFileChipName"],[data-testid="stFileChipName"]+div{color:var(--text)!important}
[data-testid="stFileChipDeleteBtn"] svg{color:var(--muted)}
[data-testid="stSidebar"] [data-testid="stCheckbox"]+[data-testid="stCaptionContainer"]{margin:-2px 0 0 0}
/* live run card */
.rs{border:1px solid var(--line);background:var(--surface);border-radius:12px;padding:13px 14px 14px;margin:2px 0 8px}
.rs.done{border-color:var(--ok)}.rs.error{border-color:var(--bad)}
.rs-h{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font:600 .86rem 'Poppins',sans-serif;color:var(--text)}
.rs-h small{font:500 .72rem 'Poppins',sans-serif;color:var(--muted)}
.rs.done .rs-h{color:var(--ok)}.rs.error .rs-h{color:var(--bad)}
.pbar{height:4px;border-radius:9px;background:var(--line);margin:10px 0 8px;overflow:hidden}
.pbar i{display:block;height:100%;border-radius:9px;background:var(--accent);transition:width .35s}
.rs.done .pbar i{background:var(--ok)}.rs.error .pbar i{background:var(--bad)}
.stp{display:flex;align-items:center;gap:10px;padding:4px 0;font-size:.82rem;color:var(--muted)}
.stp .m{flex:none;width:18px;height:18px;display:grid;place-items:center}
.stp.cur{color:var(--text);font-weight:600}.stp.cur .m{color:var(--accent)}
.stp.done{color:var(--text)}.stp.done .m{color:var(--ok)}
.stp.err{color:var(--bad);font-weight:600}.stp.err .m{color:var(--bad)}
.stp.pend{opacity:.7}
.spin{width:14px;height:14px;border-radius:50%;border:2px solid var(--line);border-top-color:var(--accent);animation:pfspin .8s linear infinite}
</style>"""
st.markdown(SB_CSS.replace("__UPLOAD__", mask("upload")).replace("__FOLDER__", mask("folder")).replace("__GEAR__", mask("gear"))
            .replace("__CHEV__", mask("chevron")), unsafe_allow_html=True)

STEPS = [("Extract candidates", "search"), ("Validate and snap", "check_sq"), ("Blind-viewer test", "eye"),
         ("Judge", "star"), ("Posting notes", "note")]


def status_html(rs):
    kind, step = rs["status"], rs.get("step", 0)
    rows = ""
    for i, (name, ic) in enumerate(STEPS, 1):
        if kind == "done" or i < step:
            cls, mark = "done", svg("check", 14, 2.6)
        elif i == step and kind == "running":
            cls, mark = "cur", '<i class="spin"></i>'
        elif i == step and kind == "error":
            cls, mark = "err", svg("x", 14, 2.6)
        else:
            cls, mark = "pend", svg(ic, 14)
        rows += f'<div class="stp {cls}"><span class="m">{mark}</span>{i}. {name}</div>'
    pct = 100 if kind == "done" else max(3, 100 * (step - (0.5 if kind == "running" else 1)) / 5) if step else 3
    head = {"running": ("Reading the show", f"step {max(step, 1)} of 5"),
            "done": ("Done", f'{rs.get("clips", 0)} clips ranked'),
            "error": ("Run failed", f"at step {max(step, 1)} of 5")}[kind]
    return (f'<div class="rs {kind}"><div class="rs-h"><span>{head[0]}</span><small>{head[1]}</small></div>'
            f'<div class="pbar"><i style="width:{pct:.0f}%"></i></div>{rows}</div>')


E = lambda x: html.escape(str(x if x is not None else ""))


def fmt(t):
    return f"{int(t // 60):02d}:{t - 60 * int(t // 60):05.2f}"


def clip_label(c):
    return " + ".join(f"Ep {s['episode']}  {fmt(s['start'])} to {fmt(s['end'])}" for s in c["segments"])


def warns(c):
    """Real warnings only. Snapping to line edges is routine and shown on the method tab."""
    return [i for i in c["issues"] if i.startswith(("hook lands", "cliffhanger quote is"))]


def norm(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


# ------------------------------------------------------------------ sidebar
SAVED = [p for p in ("outputs/app_run", "outputs/run1", "outputs/smoke") if os.path.exists(p + "/ranked_promos.json")]
with st.sidebar:
    run_slot = st.empty()  # live run card, painted from the pipeline's progress callback


def paint(rs):
    with run_slot.container():
        if rs:
            st.markdown(status_html(rs), unsafe_allow_html=True)
            if rs["status"] == "error":
                st.code(rs.get("err", ""), language=None)


paint(st.session_state.get("runstate"))
running = st.session_state.get("running", False)

with st.sidebar:
    st.markdown(sec("upload", "Source"), unsafe_allow_html=True)
    opts = ["Upload screenplays"] + (["Open saved results"] if SAVED else [])
    mode = st.radio("Source", opts, index=0, label_visibility="collapsed")
    if mode == "Open saved results":
        saved_path = st.selectbox("Saved run", SAVED)
    else:
        st.markdown(sec("sliders", "Model settings"), unsafe_allow_html=True)
        with st.expander("Model and run settings", expanded=False):
            models = st.text_area("Model chain, tried in order (provider|model). Swap any model here.",
                                  ("\n".join(m.strip() for m in os.environ["LLM_MODELS"].split(",") if m.strip()) if os.environ.get("LLM_MODELS", "").strip()
                                  else "gemini|gemini-2.5-flash\nopenrouter|nvidia/nemotron-3-ultra-550b-a55b:free"), height=96)
            st.caption("API keys are optional: leave empty to use the keys set on the server.")
            gem = st.text_input("Gemini key", type="password")
            orr = st.text_input("OpenRouter key", type="password")
            run_id = st.text_input("Run id (change to force a fresh run)", "r1")
            top = st.number_input("Promos to return", 5, 50, 20)
            only = st.text_input("Only these episodes", "", placeholder="e.g. 1,2,3")
    st.markdown(sec("filter", "Filter results"), unsafe_allow_html=True)
    min_score = st.slider("Minimum score", 0, 100, 0)
    only_clean = st.toggle("Hide clips with warnings", False)
    only_cross = st.toggle("Only multi-segment promos", False)

# ------------------------------------------------------------------ hero
st.toggle("Dark mode", key="dark")
st.markdown(BRAND, unsafe_allow_html=True)
st.markdown("""<div class="hero"><div class="eyebrow">Microdrama promo finder</div>
<h1>Find the <em>45 seconds</em> that sell the show.</h1>
<p>Reads a timestamped screenplay and returns ranked promo clips. Every clip opens on a hook, ends on a cliffhanger, makes sense to someone who has never seen the show, and cites the exact start and end of each segment.</p></div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ run
if mode == "Upload screenplays":
    up = st.file_uploader("Drop the screenplay .txt files, or one .zip", type=["txt", "zip"], accept_multiple_files=True,
                          label_visibility="collapsed")
    go = st.button("Finding promos" if running else "Find promos", type="primary", key="findbtn", disabled=running or not up)
    if running:
        st.markdown('<style>.st-key-findbtn button::before{content:"";display:inline-block;width:13px;height:13px;margin-right:9px;'
                    'border:2px solid rgba(255,255,255,.45);border-top-color:#fff;border-radius:50%;animation:pfspin .8s linear infinite;vertical-align:-2px}'
                    '.st-key-findbtn button:disabled{background:var(--accent)!important;color:#fff!important;opacity:.85;cursor:progress}</style>',
                    unsafe_allow_html=True)
    if go:  # rerun once so the button renders disabled while the run executes
        st.session_state["running"] = True
        st.session_state["runstate"] = {"status": "running", "step": 0}
        st.rerun()
    if running:
        rs = st.session_state["runstate"]
        if gem: os.environ["GEMINI_API_KEY"] = gem
        if orr: os.environ["OPENROUTER_API_KEY"] = orr
        import re, tempfile
        from promofinder.llm import LLM
        from promofinder import pipeline as P
        box = st.status("Reading the show...", expanded=True)

        def on_progress(msg):
            """Feeds the main status box and the sidebar run card from the pipeline's '1/5 ...' lines."""
            box.write(msg)
            m = re.match(r"\s*(\d)/5", msg)
            if m:
                rs["step"] = int(m.group(1)); paint(rs)
            m = re.match(r"\s*done: (\d+) ranked", msg)
            if m:
                rs["clips"] = int(m.group(1))

        paint(rs)
        try:
            src = os.path.join(tempfile.mkdtemp(), "show"); os.makedirs(src)
            for f in up:
                if f.name.lower().endswith(".zip"):
                    with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                        for n in z.namelist():
                            if n.lower().endswith(".txt"):
                                open(os.path.join(src, os.path.basename(n)), "wb").write(z.read(n))
                else:
                    open(os.path.join(src, f.name), "wb").write(f.read())
            out = "outputs/app_run"
            P.run(src, LLM(models=[m.strip() for m in models.splitlines() if m.strip()]), out, run_id, int(top),
                  {int(x) for x in only.split(",") if x.strip()} or None, progress=on_progress)
            box.update(label="Done", state="complete", expanded=False)
            st.session_state["run_dir"] = out
            rs.update(status="done", step=5)
        except Exception as ex:
            box.update(label="Failed", state="error")
            import traceback; print(traceback.format_exc())
            rs.update(status="error", err=str(ex))
        finally:
            st.session_state["running"] = False
            st.session_state["runstate"] = rs
        st.rerun()  # re-enables the button and shows the result or the error
    rs0 = st.session_state.get("runstate")
    if rs0 and rs0["status"] == "error":
        st.markdown('<span class="chip bad">Run failed</span>', unsafe_allow_html=True)
        st.code(rs0.get("err", ""), language=None); st.stop()
    run_dir = st.session_state.get("run_dir")
else:
    st.session_state["running"] = False
    run_dir = saved_path if os.path.exists(os.path.join(saved_path, "ranked_promos.json")) else None
    if not run_dir:
        st.warning("No ranked_promos.json in that folder.")

if not run_dir:
    st.markdown('<div class="empty"><b>Nothing here yet</b>Drop the screenplay files in the box above, then press Find promos.</div>',
                unsafe_allow_html=True)
    st.stop()

# ------------------------------------------------------------------ data
@st.cache_resource
def local_show():
    """Parsed screenplays from a local data folder, used when a saved run lacks transcripts or episode lengths."""
    for d in ("data/show1", "data"):
        if os.path.isdir(d) and any(f.endswith(".txt") for f in os.listdir(d)):
            from promofinder.parse import load_show
            return {e.number: e for e in load_show(d)}
    return {}


def transcript_for(c):
    if c.get("transcript"):
        return c["transcript"]
    eps = local_show()
    if not eps:
        return []
    from promofinder.pipeline import build_transcript
    return build_transcript(eps, c["segments"])


J = lambda n, d=None: json.load(open(os.path.join(run_dir, n))) if os.path.exists(os.path.join(run_dir, n)) else d
ranked, allc, rej, meta = J("ranked_promos.json", []), J("all_scored_candidates.json", []), J("rejected_by_validators.json", []), J("show_meta.json", [])
if not meta and local_show():
    meta = [{"number": n, "duration": e.duration, "logline": e.logline} for n, e in sorted(local_show().items())]
dur = {m["number"]: m["duration"] for m in meta}
shown = [c for c in ranked if (c.get("score") or 0) >= min_score and (not only_clean or not warns(c))
         and (not only_cross or len(c["segments"]) > 1)]
st.session_state.setdefault("votes", {})
votes = st.session_state["votes"]

runtime = sum(dur.values()) / 60
st.markdown(f"""<div class="stats">
<div class="stat"><b>{len(meta) or "n/a"}</b><span>Episodes</span></div>
<div class="stat"><b>{f"{runtime:.0f} min" if meta else "n/a"}</b><span>Runtime read</span></div>
<div class="stat"><b>{len(allc) + len(rej)}</b><span>Candidates proposed</span></div>
<div class="stat"><b>{len(allc)}</b><span>Passed checks</span></div>
<div class="stat"><b>{len(ranked)}</b><span>Ranked promos</span></div></div>""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Ranked promos", "Show map", "Review", "How it was checked"])

# ------------------------------------------------------------------ cards
def vote(cid, val):
    """Click again to clear."""
    v = st.session_state["votes"]
    if v.get(cid) == val:
        v.pop(cid, None)
    else:
        v[cid] = val


def card(c):
    p = c.get("score_parts") or {}
    b = c.get("blind") or {}
    sc = c.get("score") or 0
    chips = [f'<span class="chip gold">{c["duration"]:.0f}s</span>']
    if len(c["segments"]) > 1: chips.append('<span class="chip">multi-segment</span>')
    chips += [f'<span class="chip warn">{E(i)}</span>' for i in warns(c)]
    v = votes.get(c["id"])
    if v: chips.append(f'<span class="chip {"ok" if v == "approved" else "bad"}">{v}</span>')
    tl = ""
    for s in c["segments"]:
        d = dur.get(s["episode"]) or max(s["end"], 1)
        tl += (f'<div class="tl"><small>EPISODE {s["episode"]}  {fmt(s["start"])} to {fmt(s["end"])}</small>'
               f'<div><i style="left:{100 * s["start"] / d:.1f}%;width:{max(1.5, 100 * (s["end"] - s["start"]) / d):.1f}%"></i></div></div>')
    names = [("hook", "Hook"), ("cliffhanger", "Cliffhanger"), ("standalone", "Standalone"), ("intensity", "Intensity"), ("premise", "Premise")]
    bars = "".join(f'<div class="bar"><small><span>{n}</span><span>{p.get(k, 0):.0f}</span></small><div><i style="width:{p.get(k, 0) * 10:.0f}%"></i></div></div>' for k, n in names)
    st.markdown(f"""<div class="card {'top' if c['rank'] <= 3 else ''}"><div class="row">
<div class="rank">{c['rank']:02d}</div><div class="grow">
<div class="meta"><span class="clip">{E(clip_label(c))}</span>{''.join(chips)}</div>
<div class="beat hook"><small>Hook at {fmt(c['hook']['at'])}</small><q>{E(c['hook']['quote'])}</q></div>
<div class="beat cliff"><small>Cliffhanger</small><q>{E(c['cliffhanger']['quote'])}</q></div>
<div class="why">{E(c.get('post_reason') or c.get('why'))}</div>
<div class="read"><b>Cold viewer ({b.get('standalone', 'n/a')}/5):</b> {E(b.get('what_is_happening', ''))}</div>
{tl}<div class="bars">{bars}</div></div>
<div class="ring" style="background:conic-gradient(var(--gold) {sc * 3.6:.0f}deg,var(--line) 0)"><i>{sc:.0f}</i></div></div></div>""",
                unsafe_allow_html=True)
    a, r, _ = st.columns([1.2, 1.2, 6])
    a.button("Approved" if v == "approved" else "Approve", key="a" + c["id"], on_click=vote, args=(c["id"], "approved"),
             type="primary" if v == "approved" else "secondary", use_container_width=True)
    r.button("Rejected" if v == "rejected" else "Reject", key="r" + c["id"], on_click=vote, args=(c["id"], "rejected"),
             type="primary" if v == "rejected" else "secondary", use_container_width=True)
    with st.expander("Read the clip"):
        hq, cq = norm(c["hook"]["quote"]), norm(c["cliffhanger"]["quote"])
        lines = []
        tr = transcript_for(c)
        if not tr:
            st.info("This run was saved without the script. Keep the screenplay files in data/show1 and reopen it, or run again.")
        for t in tr:
            txt = E(t["text"])
            nt = norm(t["text"])
            cls = "h" if len(nt) > 6 and hq and (nt in hq or hq in nt) else ""
            if not cls and len(nt) > 6 and cq and (nt in cq or cq in nt): cls = "c"
            if t["kind"] == "DIALOGUE":
                lines.append(f'<p><span class="t">{fmt(t["t"])}</span><span class="who">{E(t["speaker"])}</span> <span class="{cls}">{txt}</span></p>')
            else:
                lines.append(f'<p class="act"><span class="t">{fmt(t["t"])}</span><span class="{cls}">{"[sound] " if t["kind"] == "SOUND" else ""}{txt}</span></p>')
        st.markdown('<div class="tx">' + "".join(lines) + "</div>", unsafe_allow_html=True)


with tab1:
    st.caption(f"{len(shown)} of {len(ranked)} promos shown, best first. Approve or reject each clip (click again to undo). Decisions collect in the Review tab.")
    for c in shown:
        card(c)

# ------------------------------------------------------------------ map
with tab2:
    st.markdown("### Where the promos sit in the show")
    st.caption("Each column is an episode, top to bottom in time. Gold marks the five best promos, red the rest.")
    if not meta:
        st.info("This run has no show_meta.json.")
    else:
        W, H, n = 1100, 260, len(meta)
        cw = W / n; mx = max(dur.values())
        svg = [f'<svg viewBox="0 0 {W} {H + 26}" width="100%" xmlns="http://www.w3.org/2000/svg">']
        for i, m in enumerate(meta):
            h = H * m["duration"] / mx
            svg.append(f'<rect x="{i * cw + 2:.1f}" y="0" width="{cw - 4:.1f}" height="{h:.1f}" rx="3" fill="{TRACK}"/>')
        for c in ranked:
            for s in c["segments"]:
                if s["episode"] not in dur: continue
                i = [m["number"] for m in meta].index(s["episode"])
                y = H * s["start"] / mx; h = max(4, H * (s["end"] - s["start"]) / mx)
                col = GOLD if c["rank"] <= 5 else T["accent"]
                svg.append(f'<rect x="{i * cw + 2:.1f}" y="{y:.1f}" width="{cw - 4:.1f}" height="{h:.1f}" rx="3" fill="{col}"><title>#{c["rank"]}  Ep {s["episode"]}  {fmt(s["start"])} to {fmt(s["end"])}</title></rect>')
        for i, m in enumerate(meta):
            if m["number"] % 5 == 0 or i == 0:
                svg.append(f'<text x="{i * cw + cw / 2:.1f}" y="{H + 18}" fill="{MUTED}" font-size="11" text-anchor="middle" font-family="Poppins,sans-serif">{m["number"]}</text>')
        svg.append("</svg>")
        st.markdown("".join(svg), unsafe_allow_html=True)
        per = Counter(c["segments"][0]["episode"] for c in ranked)
        st.caption(f"Promos come from {len(per)} different episodes. Most from episode {per.most_common(1)[0][0]}." if per else "")

# ------------------------------------------------------------------ review
with tab3:
    st.markdown("### Your review")
    ok = [c for c in ranked if votes.get(c["id"]) == "approved"]
    no = [c for c in ranked if votes.get(c["id"]) == "rejected"]
    done = len(ok) + len(no)
    st.markdown(f'<div class="stats" style="grid-template-columns:repeat(3,1fr)"><div class="stat"><b>{len(ok)}</b><span>Approved</span></div>'
                f'<div class="stat"><b>{len(no)}</b><span>Rejected</span></div>'
                f'<div class="stat"><b>{(100 * len(ok) / done) if done else 0:.0f}%</b><span>Approval rate</span></div></div>', unsafe_allow_html=True)
    st.caption("Approve or reject on the Ranked promos tab. Download the approved list as the editor's posting queue.")
    if ok:
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["rank", "segments", "duration_s", "hook", "cliffhanger", "why"])
        for c in ok: w.writerow([c["rank"], clip_label(c), c["duration"], c["hook"]["quote"], c["cliffhanger"]["quote"], c.get("why", "")])
        st.download_button("Download approved clips (CSV)", buf.getvalue(), "approved_promos.csv", "text/csv")
        for c in ok: st.markdown(f"**#{c['rank']}**  {clip_label(c)}")
    st.download_button("Download all ranked promos (JSON)", json.dumps(ranked, indent=2, ensure_ascii=False), "ranked_promos.json")

# ------------------------------------------------------------------ method
with tab4:
    st.markdown("### What the guardrails caught")
    reasons = Counter()
    for r in rej:
        t = r["reason"]
        reasons["Quoted hook not found in the clip (invented)" if "hook quote" in t else
                "Quoted cliffhanger not found in the clip (invented)" if "cliffhanger quote" in t else
                "Longer than 60s or shorter than 20s" if "duration" in t else
                "Timestamp not near any real line" if "not near" in t else
                "Duplicate of a better clip" if "overlaps" in t else t[:50]] += 1
    if reasons:
        for k, v in reasons.most_common():
            st.markdown(f'<div class="rowline"><span>{E(k)}</span><span>{v}</span></div>', unsafe_allow_html=True)
    else:
        st.write("No rejected candidates in this run.")
    import re as _re
    snap = Counter(_re.sub(r"\d+(\.\d+)?s", "Ns", i.split(" (")[0]) for c in allc for i in c["issues"])
    if snap:
        st.markdown("### Fixes applied to kept clips")
        for k, v in snap.most_common(6):
            st.markdown(f'<div class="rowline"><span>{E(k)}</span><span>{v}</span></div>', unsafe_allow_html=True)
    st.markdown("### How a promo is chosen")
    st.markdown("""1. **Parse** the screenplay exactly (code, no AI), so every timestamp is real.
2. **Propose** candidate clips per episode (AI).
3. **Verify** in code: cut on line edges, 20 to 60 seconds, quoted hook and cliffhanger really exist in the clip.
4. **Cold-read** each clip with a model that knows nothing about the show, and score how well a new viewer follows it.
5. **Judge and rank**: hook 30, cliffhanger 30, standalone 20, intensity 10, premise 10, then a limit of two per episode.""")
