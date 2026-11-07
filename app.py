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
.block-container{padding-top:.9rem;max-width:1180px}
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
               accent="#1c9aa6", gold="#d9a441", ok="#86b07f", bad="#b9534a", warn="#e0a458", warnline="#5b4526", goldline="#5b4a22",
               okline="#1f4a3c", badline="#4d2a2c", topline="#1f4f56", track="#0f2428"),
    False: dict(bg="#f3f9f9", surface="#ffffff", surface2="#e8f3f4", line="#cfe3e6", text="#0f2427", muted="#4d6f75", faint="#86a5aa",
                accent="#0e7f8c", gold="#b07a14", ok="#3f7a4a", bad="#b03a30", warn="#a8661a", warnline="#e6cfa6", goldline="#e3cd9a",
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
    st.markdown('<div class="eyebrow">Source</div>', unsafe_allow_html=True)
    opts = ["Upload screenplays"] + (["Open saved results"] if SAVED else [])
    mode = st.radio("Source", opts, index=0, label_visibility="collapsed")
    if mode == "Open saved results":
        saved_path = st.selectbox("Saved run", SAVED)
    else:
        with st.expander("Model and run settings"):
            models = st.text_area("Model chain, tried in order (provider|model). Swap any model here.",
                                  ("\n".join(m.strip() for m in os.environ["LLM_MODELS"].split(",") if m.strip()) if os.environ.get("LLM_MODELS", "").strip()
                                  else "gemini|gemini-2.5-flash\nopenrouter|nvidia/nemotron-3-ultra-550b-a55b:free"), height=96)
            st.caption("API keys are optional: leave empty to use the keys set on the server.")
            gem = st.text_input("Gemini key", type="password")
            orr = st.text_input("OpenRouter key", type="password")
            run_id = st.text_input("Run id (change to force a fresh run)", "r1")
            top = st.number_input("Promos to return", 5, 50, 20)
            only = st.text_input("Only these episodes", "", placeholder="e.g. 1,2,3")
    st.markdown("---")
    st.markdown('<div class="eyebrow">Filter results</div>', unsafe_allow_html=True)
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
    go = st.button("Find promos", type="primary", disabled=not up)
    if go:
        if gem: os.environ["GEMINI_API_KEY"] = gem
        if orr: os.environ["OPENROUTER_API_KEY"] = orr
        import tempfile
        src = os.path.join(tempfile.mkdtemp(), "show"); os.makedirs(src)
        for f in up:
            if f.name.lower().endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                    for n in z.namelist():
                        if n.lower().endswith(".txt"):
                            open(os.path.join(src, os.path.basename(n)), "wb").write(z.read(n))
            else:
                open(os.path.join(src, f.name), "wb").write(f.read())
        from promofinder.llm import LLM
        from promofinder import pipeline as P
        box = st.status("Reading the show...", expanded=True)
        try:
            out = "outputs/app_run"
            P.run(src, LLM(models=[m.strip() for m in models.splitlines() if m.strip()]), out, run_id, int(top),
                  {int(x) for x in only.split(",") if x.strip()} or None, progress=box.write)
            box.update(label="Done", state="complete", expanded=False)
            st.session_state["run_dir"] = out
        except Exception as ex:
            box.update(label="Failed", state="error")
            import traceback; print(traceback.format_exc())
            st.code(str(ex)); st.stop()
    run_dir = st.session_state.get("run_dir")
else:
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
