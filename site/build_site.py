# -*- coding: utf-8 -*-
"""
The static site with the results: https://ispacex.github.io/metalibrary/

    (cd metalibrary && PLOT_NMAX=100 python3 plot_e2.py data/e2_qgrade.csv ru en)   # the two pictures
    python3 site/build_site.py [OUT_DIR]        # default: site/out/
    site/two_tier.sh OUT_DIR                    # search index into the form ispacex's engine reads

Reads only data that is already computed (no new computation): metalibrary/data/*.csv,
metalibrary/toda2003.py, metalibrary/out/7_e2_rapacious_{ru,en}.png.
The rapacious rule is re-run on that data (a fraction of a second). The output is a static
site (HTML, KaTeX from jsDelivr, CSV/JSON downloads) published from the public repository
ispacex/metalibrary via GitHub Pages; the code that makes it is this repository.

Two languages from one source: every text is written here twice, side by side, as t(ru, en).
English pages lie at the root, Russian ones in ru/ under the same file names; both link to the
same data/ files. The convention is the one of ispacex.github.io: <html lang>, hreflang links
to the twin (x-default is the English page), an EN/RU switch in the header, and one search
index for both languages in which every page names its `lang` -- the engine (sitesearch) then
offers a reader only the pages in the language of the page they are on, so a query is not
answered twice.

Until 16.10.2026 the Russian pages were at the root and the English ones in en/. The en/
addresses are linked from outside (the main page of ispacex.github.io among them), so en/ still
holds one small page per file that sends the reader to the same page at the root; those pages
are in neither search index.
"""
import collections
import csv
import html
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "metalibrary"))
import rapacious as R  # noqa: E402
import toda2003  # noqa: E402

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out"
LANGS = ("ru", "en")
SITE_TITLE = {"ru": "Цветная метабиблиотека: пересчёт", "en": "Coloured metalibrary: a recomputation"}
DATE = {"ru": "15.10.2026", "en": "15 October 2026"}

NAV = [("index.html", "Сводка", "Summary"), ("comparison.html", "Сравнение по n", "Comparison by n"),
       ("e2.html", "Классы E²", "E² classes"), ("differentials.html", "Дифференциалы", "Differentials"),
       ("toda2003.html", "Таблица Тоды 2003", "Toda's 2003 table"),
       ("method.html", "Метод и проверки", "Method and checks"), ("verify.html", "Проверяемость", "Verifiability"),
       ("data.html", "Данные", "Data"), ("notes.html", "Заметки об источниках", "Notes on sources"),
       ("search.html", "Поиск", "Search")]

# Colours: one set of custom properties, light on :root, dark under DARK. The theme is the system's
# unless the reader chose one with the switch in the header: then <html data-theme="light|dark">,
# set by THEME_HEAD before the first paint, so a dark page never flashes light. The ⌘K palette of
# sitesearch keeps its colours in --p-* on its own elements and defaults to dark; they are handed
# the page's colours here, so the palette follows the theme too.
DARK = """--ink:#e6e9ee; --muted:#a3adb9; --line:#38414c; --bg:#14181d; --soft:#1c2128; --bad:#4a2620;
        --badink:#ffb4a2; --ok:#1f3a27; --amb:#4a3d1c; --acc:#7fb0ec; --sel:rgba(127,176,236,.2);
        --veil:rgba(0,0,0,.6); --imgpad:6px; color-scheme:dark;"""
CSS = """
:root { --ink:#1f2933; --muted:#52606d; --line:#d9dee5; --bg:#ffffff; --soft:#f4f6f9;
        --bad:#fde8e4; --badink:#a33a1f; --ok:#e7f4ea; --amb:#fff3d6; --acc:#2e6db4; --sel:rgba(46,109,180,.12);
        --veil:rgba(15,20,30,.35); --imgpad:0; color-scheme:light; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { """ + DARK + """ } }
:root[data-theme="dark"] { """ + DARK + """ }
"""
CSS += """* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 -apple-system, "Segoe UI", Roboto, "DejaVu Sans", sans-serif; }
header { border-bottom:1px solid var(--line); background:var(--soft); }
header .wrap { padding-top:.7rem; padding-bottom:.8rem; }
header .top { display:flex; flex-wrap:wrap; align-items:center; gap:.5rem 1rem; margin-bottom:.6rem; }
header .title { font-weight:600; color:var(--ink); text-decoration:none; }
header .tools { display:flex; align-items:center; gap:.6rem; margin-left:auto; }
.lang { display:inline-flex; border:1px solid var(--line); border-radius:6px; overflow:hidden; font-size:.85rem; line-height:1.6; }
.lang a, .lang strong { padding:0 .6em; text-decoration:none; }
.lang a { color:var(--acc); background:var(--bg); }
.lang strong { background:var(--acc); color:var(--bg); }
.lang > * + * { border-left:1px solid var(--line); }
.theme { display:inline-flex; border:1px solid var(--line); border-radius:6px; overflow:hidden; font-size:.85rem; line-height:1.6; }
.theme button { display:inline-flex; align-items:center; height:1.6em; margin:0; padding:0 .5em; border:0; border-radius:0;
        background:var(--bg); color:var(--muted); font:inherit; cursor:pointer; }
.theme button + button { border-left:1px solid var(--line); }
.theme button:hover { color:var(--acc); }
.theme button:focus-visible { outline:2px solid var(--acc); outline-offset:-2px; }
.theme button[aria-pressed="true"] { background:var(--acc); color:var(--bg); }
.theme svg { width:1em; height:1em; fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; }
html:not(.js) .theme { display:none; }
#nav-palette, #nav-open { --p-bg:var(--bg); --p-fg:var(--ink); --p-line:var(--line); --p-sel:var(--sel);
        --p-mark:var(--acc); --p-veil:var(--veil); }
nav { display:flex; flex-wrap:wrap; gap:.4rem; }
nav a { color:var(--acc); text-decoration:none; white-space:nowrap; font-size:.92rem; line-height:1.5;
        padding:.15em .65em; border:1px solid var(--line); border-radius:6px; background:var(--bg); }
nav a:hover, nav a:focus-visible { border-color:var(--acc); }
nav a.cur { background:var(--acc); border-color:var(--acc); color:var(--bg); font-weight:600; }
@media (max-width:520px) { nav { gap:.3rem; } nav a { font-size:.85rem; padding:.1em .5em; } }
.wrap { max-width:1100px; margin:0 auto; padding:.9rem 16px; }
h1 { font-size:1.6rem; margin:.6rem 0 .8rem; } h2 { font-size:1.25rem; margin-top:2rem; }
a { color:var(--acc); } .muted { color:var(--muted); } small { color:var(--muted); }
.tw { overflow-x:auto; margin:1rem 0; border:1px solid var(--line); border-radius:6px;
      position:relative; }  /* KaTeX's absolutely placed pieces are clipped too, not left sticking out of the page */
table { border-collapse:collapse; width:100%; font-size:.9rem; font-variant-numeric:tabular-nums; }
th, td { border-bottom:1px solid var(--line); padding:.3rem .55rem; text-align:center; vertical-align:top; }
th { background:var(--soft); position:sticky; top:0; }
td.l, th.l { text-align:left; }
tr.bad td { background:var(--bad); } td.bad { background:var(--bad); color:var(--badink); font-weight:600; }
td.amb { background:var(--amb); } td.ok { background:var(--ok); }
.box { border-left:4px solid var(--acc); background:var(--soft); padding:.7rem 1rem; margin:1rem 0; border-radius:0 6px 6px 0; }
img { max-width:100%; height:auto; border:1px solid var(--line); border-radius:6px; background:#fff; padding:var(--imgpad); }
code { background:var(--soft); padding:0 .25em; border-radius:3px; }
footer { border-top:1px solid var(--line); margin-top:3rem; }
"""

KATEX = """<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
 onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]})"></script>"""


def plain(s):
    """Text for <title>: no KaTeX there."""
    for a, b in (("\\pi", "π"), ("^2", "²"), ("^3", "³"), ("$", ""), ("\\", "")):
        s = s.replace(a, b)
    return s


PAGES = []  # (lang, file, title, body) of every page, for the search index
ORIGIN = "https://ispacex.github.io"
BASE = "/metalibrary/"  # where GitHub Pages serves the site
SECTION = {"ru": "Метабиблиотека", "en": "Metalibrary"}


def url(lang, fn):
    """The address a page is served at, as the site's links name it (the index is the folder)."""
    return BASE + ("ru/" if lang == "ru" else "") + ("" if fn == "index.html" else fn)


# The search engine of ispacex.github.io (https://github.com/tombouctou/sitesearch), served from
# the same origin: a search page and the ⌘K palette on every page, as on the main site. The
# palette reads the reader's language off <html lang>; it is told where the full search of that
# language is and what to suggest in the empty field.
PLACEHOLDER = {"ru": "Куда идём? например: хищное правило, Тода, метод",
               "en": "Where to? for example: rapacious rule, Toda, method"}


def palette(lang):
    return (f'<script src="/sitesearch/palette.js" data-index="{BASE}nav-index.json" data-mount="header .pal" '
            f'data-search="{url(lang, "search.html")}" data-search-index="{BASE}search-index.json" '
            f'data-placeholder="{PLACEHOLDER[lang]}" defer></script>')


FOOTER = {
    "ru": """Пересчёт к лекции Р. В. Михайлова «Цветные метабиблиотеки. Разум пространства»
(02.09.2016). Данные от {date}. Все числа на этих страницах — 3-примарные: ранг 3-кручения, все слагаемые $\\mathbb Z/3$.<br>
Раздел <a href="https://ispacex.github.io/ru/math/">«Математика»</a> на ispacex.github.io.""",
    "en": """A recomputation for R. Mikhailov's lecture “Coloured metalibraries. The mind of space”
(2 September 2016). Data as of {date}. All numbers on these pages are 3-primary: the rank of the 3-torsion, all summands $\\mathbb Z/3$.<br>
Part of <a href="https://ispacex.github.io/math/">Mathematics</a> at ispacex.github.io.""",
}
# a footer line of its own on the verifiability page: whom to write to about the proof
CONTACT = {"ru": 'Связаться с нами: <a href="https://vissi.su">vissi.su</a>',
           "en": 'Contact: <a href="https://vissi.su">vissi.su</a>'}

# The theme switch: System (the default), Light, Dark. A choice other than System is kept in
# localStorage under THEME_KEY (the origin is ispacex.github.io, hence a name of the site's own) and
# put on <html data-theme> by THEME_HEAD, the first thing in <head>, before the stylesheet is
# applied. Without storage (a private window, blocked site data) every access throws, is caught,
# and the page simply follows the system. Without JavaScript the switch is hidden (html.js is set
# by the same script) and the system theme applies through the media query alone.
THEME_KEY = "metalibrary-theme"
THEME_HEAD = ("<script>(function(d){d.classList.add('js');try{var t=localStorage.getItem('" + THEME_KEY + "');"
              "if(t==='light'||t==='dark')d.setAttribute('data-theme',t)}catch(e){}})(document.documentElement)</script>")
THEME_BODY = """<script>(function(){var d=document.documentElement,K='""" + THEME_KEY + """',
b=document.querySelectorAll('.theme button');
function show(){var t=d.getAttribute('data-theme')||'system';
for(var i=0;i<b.length;i++)b[i].setAttribute('aria-pressed',b[i].getAttribute('data-t')===t?'true':'false')}
function set(t){if(t==='light'||t==='dark')d.setAttribute('data-theme',t);else{t='system';d.removeAttribute('data-theme')}show();return t}
for(var i=0;i<b.length;i++)b[i].addEventListener('click',function(){var t=set(this.getAttribute('data-t'));
try{if(t==='system')localStorage.removeItem(K);else localStorage.setItem(K,t)}catch(e){}});
addEventListener('storage',function(e){if(e.key===K)set(e.newValue)});show()})()</script>"""
THEMES = (("system", "как в системе", "system",  # a circle half filled: whatever the system says
           '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor"/>'),
          ("light", "светлая", "light",
           '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4'
           'M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
          ("dark", "тёмная", "dark", '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>'))


def theme_switch(lang):
    li = 1 if lang == "ru" else 2
    word = "Тема" if lang == "ru" else "Theme"
    return (f'<span class="theme" role="group" aria-label="{word}">' + "".join(
        f'<button type="button" data-t="{th[0]}" aria-pressed="{"true" if th[0] == "system" else "false"}" '
        f'aria-label="{word}: {th[li]}" title="{word}: {th[li]}">'
        f'<svg viewBox="0 0 24 24" aria-hidden="true">{th[3]}</svg></button>' for th in THEMES) + "</span>")


def page(lang, fn, title, body, contact=False):
    PAGES.append((lang, fn, title, body))
    li = 1 if lang == "ru" else 2
    nav = "".join(f'<a href="{n[0]}"{" class=cur aria-current=page" if n[0] == fn else ""}>{n[li]}</a>' for n in NAV)
    twin = {"en": f"ru/{fn}", "ru": f"../{fn}"}[lang]
    other = "en" if lang == "ru" else "ru"
    there = f'<a href="{twin}" hreflang="{other}" lang="{other}">{other.upper()}</a>'
    here = f'<strong lang="{lang}" aria-current="true">{lang.upper()}</strong>'
    switch = (f'<span class="lang" role="group" aria-label="{"Язык" if lang == "ru" else "Language"}">'
              + (here + there if lang == "en" else there + here) + "</span>")
    alt = "".join(f'\n<link rel="alternate" hreflang="{h}" href="{ORIGIN}{url(l, fn)}">'
                  for h, l in (("en", "en"), ("ru", "ru"), ("x-default", "en")))
    if lang == "ru":  # the data and its downloads are one set for both languages, at the root
        body = body.replace('href="data/', 'href="../data/')
    doc = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{THEME_HEAD}
<title>{html.escape(plain(title))} — {SITE_TITLE[lang]}</title>{alt}
<style>{CSS}</style>{KATEX}</head>
<body><header><div class="wrap"><div class="top"><a class="title" href="index.html">{SITE_TITLE[lang]}</a>
<div class="tools"><span class="pal"></span>{theme_switch(lang)}{switch}</div></div>
<nav aria-label="{"Разделы" if lang == "ru" else "Sections"}">{nav}</nav></div></header>
<main class="wrap"><h1>{html.escape(title)}</h1>
{body}
</main><footer><div class="wrap"><small>{FOOTER[lang].format(date=DATE[lang])}</small>{f'<p><small>{CONTACT[lang]}</small></p>' if contact else ""}</div></footer>
{THEME_BODY}
{palette(lang)}
</body></html>"""
    d = OUT if lang == "en" else OUT / "ru"
    d.mkdir(parents=True, exist_ok=True)
    (d / fn).write_text(doc, encoding="utf-8")


def moved_from_en():
    """en/<page>.html, where the English pages were until they moved to the root: a page that sends
    the reader on to the same page at the root. Written for every page of the site (they are all
    the NAV); not in PAGES, so not in the search."""
    d = OUT / "en"
    d.mkdir(exist_ok=True)
    for fn, *_ in NAV:
        to = html.escape(url("en", fn))
        (d / fn).write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Moved — {SITE_TITLE["en"]}</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{ORIGIN}{to}">
<meta http-equiv="refresh" content="0; url={to}">
<script>location.replace("{to}" + location.search + location.hash)</script>
</head>
<body><p>This page has moved to <a href="{to}">{ORIGIN}{to}</a>.</p></body></html>
""", encoding="utf-8")


def tex_text(s):
    """TeX of the pages as searchable bare text: $\\pi_{49}$ -> π49, \\mathbb Z/3 -> Z/3."""
    import re
    for a, b in (("\\pi", "π"), ("\\mathbb ", ""), ("\\le", "≤"), ("\\ge", "≥"), ("\\to", "→"),
                 ("\\oplus", "⊕"), ("\\circ", "∘"), ("\\Sigma", "Σ"), ("\\sigma", "σ"), ("\\nu", "ν"),
                 ("\\kappa", "κ"), ("\\eta", "η"), ("\\mu", "μ"), ("\\lambda", "λ"), ("\\alpha", "α"),
                 ("\\theta", "θ"), ("\\zeta", "ζ"), ("\\iota", "ι"), ("\\cong", "≅"), ("\\pmod", "mod"),
                 ("\\bar", ""), ("\\{", "{"), ("\\}", "}"), ("\\,", " "), ("\\;", " ")):
        s = s.replace(a, b)
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = re.sub(r"[_^]\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"[_^](\S)", r"\1", s)
    return re.sub(r"\s+", " ", s.replace("$", "").replace("{", "").replace("}", "")).strip()


def blocks_of(body):
    """The pieces of text of a page (FORMAT.md of sitesearch): paragraphs, list items, table rows,
    each with the heading above it."""
    from html.parser import HTMLParser
    out = []

    class P(HTMLParser):
        BLOCK = {"p", "li", "tr", "h2", "h3"}

        def __init__(self):
            super().__init__()
            self.buf, self.depth, self.section = [], 0, ""

        def handle_starttag(self, tag, attrs):
            if tag in self.BLOCK:
                self.flush()
                self.depth += 1
            elif tag in ("td", "th") and self.buf:
                self.buf.append(" · ")

        def handle_endtag(self, tag):
            if tag in self.BLOCK:
                text = self.flush()
                self.depth = max(0, self.depth - 1)
                if tag in ("h2", "h3"):
                    self.section = text
                elif text:
                    out.append({"text": text, "section": self.section} if self.section else text)

        def handle_data(self, data):
            self.buf.append(data)

        def flush(self):
            text = tex_text(html.unescape("".join(self.buf)))
            self.buf = []
            return text.strip(" ·")

    p = P()
    p.feed(body)
    return out


def write_search(order):
    """search-index.json (the text of every page) and nav-index.json (names only, for the palette).
    One index for both languages: each page names its `lang`, and the engine offers a reader only
    the pages in the language of the page they are reading (FORMAT.md of sitesearch)."""
    pages = []
    for lang, fn, title, body in PAGES:
        if fn == "search.html":
            continue
        pages.append({"url": url(lang, fn), "title": tex_text(title), "lang": lang,
                      "section": SECTION[lang], "order": order.get(fn, 9), "blocks": blocks_of(body)})
    (OUT / "search-index.json").write_text(json.dumps({"pages": pages}, ensure_ascii=False, separators=(",", ":")))
    nav = [{k: v for k, v in p.items() if k != "blocks"} for p in pages]
    (OUT / "nav-index.json").write_text(json.dumps({"pages": nav}, ensure_ascii=False, separators=(",", ":")))
    return sum(len(p["blocks"]) for p in pages)


def table(head, rows, cls=None):
    th = "".join(f"<th{' class=l' if h.startswith('<l>') else ''}>{h.removeprefix('<l>')}</th>" for h in head)
    body = []
    for i, r in enumerate(rows):
        rc = f' class="{cls[i]}"' if cls and cls[i] else ""
        tds = []
        for c in r:
            if isinstance(c, tuple):
                tds.append(f'<td class="{c[1]}">{c[0]}</td>')
            else:
                tds.append(f"<td>{c}</td>")
        body.append(f"<tr{rc}>{''.join(tds)}</tr>")
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data").mkdir(parents=True)
    md = ROOT / "metalibrary" / "data"
    # colours = Q-weight of the unstable Ext (sseq fork), checked against the lambda algebra
    E2 = R.load_e2(md / "e2_qgrade.csv")
    nmax = max(n for n, _, _ in E2)              # 150: d_r from pi_151 not computed
    last = nmax - 1                                # results final up to here
    brute = R.load_e2(md / "e2_metalib.csv")      # direct lambda-algebra enumeration, n <= 64
    nbrute = max(n for n, _, _ in brute)
    sseq = collections.Counter()
    for line in open(md / "sseq_S3_p3_150.csv"):
        n, s, k = map(int, line.split(","))
        if n > 3 and k:
            sseq[(n, s)] += k
    sseq_n = collections.Counter()
    for (n, s), v in sseq.items():
        sseq_n[n] += v
    nseq = max(n for n, _ in sseq)
    t62 = R.toda1962()
    t03 = toda2003.by_n()
    El, left_l, diffs_l = R.run(E2, +1, "low", nmax)
    Eh, left_h, diffs_h = R.run(E2, +1, "high", nmax)
    E5, left_5, diffs_5 = R.run(E2, +1, "low", nmax, extra=((5, 0),))
    tmax = max(t03)
    tlast = min(last, tmax)
    agree_upto = next(n for n in range(4, tlast + 1) if left_l[n] != t03.get(n, 0)) - 1
    dis = [n for n in range(4, tlast + 1) if left_l[n] != t03.get(n, 0)]
    zeros_rule = [n for n in range(49, last + 1) if left_l[n] == 0 or left_h[n] == 0]
    dis5 = [n for n in range(4, tlast + 1) if left_5[n] != t03.get(n, 0)]
    pis = ", ".join(f"$\\pi_{{{n}}}$" for n in dis)

    # ---------- data files: one set, written once, linked from both languages ----------
    shutil.copy(md / "e2_metalib.csv", OUT / "data" / "e2_metalib.csv")
    shutil.copy(md / "e2_qgrade.csv", OUT / "data" / "e2_coloured.csv")
    shutil.copy(md / "sseq_S3_p3_150.csv", OUT / "data" / "sseq_S3_p3.csv")
    shutil.copy(md / "sseq_qgrade_S3_p3_150.csv", OUT / "data" / "sseq_qweight_S3_p3.csv")
    json.dump({"note": f"rapacious rule on E^2 of the metalibrary, n <= {nmax} (final up to {last})",
               "low": diffs_l, "high": diffs_h, "low_with_colour_preserving_d5": diffs_5},
              open(OUT / "data" / "differentials.json", "w"), ensure_ascii=False, indent=1, default=list)
    # the picture, drawn by metalibrary/plot_e2.py in both languages: the English one at the root,
    # the Russian one beside the Russian pages under the same name
    shutil.copy(ROOT / "metalibrary" / "out" / "7_e2_rapacious_en.png", OUT / "e2_rapacious.png")
    (OUT / "ru").mkdir()
    shutil.copy(ROOT / "metalibrary" / "out" / "7_e2_rapacious_ru.png", OUT / "ru" / "e2_rapacious.png")

    v = dict(E2=E2, El=El, nmax=nmax, last=last, nbrute=nbrute, nseq=nseq, sseq_n=sseq_n, t62=t62, t03=t03,
             tmax=tmax, tlast=tlast, left_l=left_l, left_h=left_h, left_5=left_5, diffs_l=diffs_l,
             diffs_h=diffs_h, diffs_5=diffs_5, agree_upto=agree_upto, dis=dis, zeros_rule=zeros_rule,
             dis5=dis5, pis=pis)
    for lang in LANGS:
        site(lang, v)
    nblocks = write_search({h: i for i, (h, _, _) in enumerate(NAV)})
    moved_from_en()
    print("search index:", sum(1 for p in PAGES if p[1] != "search.html"), "pages,", nblocks, "blocks")
    (OUT / ".nojekyll").write_text("")
    print("site written to", OUT, "| final up to n =", last, "| agree up to", agree_upto, "| disagreements", dis)


def site(lang, v):
    """Every page in one language. `t(ru, en)` is the one place a text is chosen."""
    def t(ru, en):
        return ru if lang == "ru" else en

    E2, El, nmax, last, nbrute, nseq = v["E2"], v["El"], v["nmax"], v["last"], v["nbrute"], v["nseq"]
    sseq_n, t62, t03, tmax, tlast = v["sseq_n"], v["t62"], v["t03"], v["tmax"], v["tlast"]
    left_l, left_h = v["left_l"], v["left_h"]
    diffs_l, diffs_h, diffs_5 = v["diffs_l"], v["diffs_h"], v["diffs_5"]
    agree_upto, zeros_rule, dis5, pis = v["agree_upto"], v["zeros_rule"], v["dis5"], v["pis"]

    def family(n):
        if n % 4 == 2 and n >= 6:
            return t("элемент Тоды", "Toda element")
        if n % 4 == 1 and n >= 9:
            return t("сэндвич", "sandwich")
        return ""

    # ---------- comparison ----------
    rows, csvrows = [], []
    for n in range(4, nmax + 1):
        final = n <= last
        rl = left_l[n] if final else None
        rh = left_h[n] if final else None
        td = t03.get(n) if n <= tmax else None
        lect = {44: t("нет 3-кручения", "no 3-torsion"),
                71: t("предсказано $(\\mathbb Z/3)^2$", "predicted $(\\mathbb Z/3)^2$")}.get(n, "")
        if n >= 49:
            lect = (lect + "; " if lect else "") + t("гипотеза: есть", "conjecture: present")
        mark = ""
        if final and td is not None and rl != td:
            mark = t("правило ≠ Тода", "rule ≠ Toda")
        if n >= 49 and td == 0:
            mark = (mark + "; " if mark else "") + t("Тода: 0 при n ≥ 49", "Toda: 0 for n ≥ 49")
        if n == 71 and td != 2:
            mark = (mark + "; " if mark else "") + t("Тода: 1, не 2", "Toda: 1, not 2")
        if final and n >= 49 and rl == 0:
            mark = (mark + "; " if mark else "") + t("правило: 0 при n ≥ 49", "rule: 0 for n ≥ 49")
        cmp = "" if td is None else ("bad" if rl != td else "ok")
        rows.append([
            n, sseq_n[n] if n <= nseq else "",
            (rl, cmp) if final else ("—", ""),
            (rh, "amb" if final and rh != rl else "") if final else ("—", ""),
            "—" if td is None else td, t62.get(n, ""), family(n), lect, mark])
        csvrows.append({"n": n, "E2": sseq_n[n] if n <= nseq else "", "rapacious_low": rl if final else "",
                        "rapacious_high": rh if final else "", "toda2003": "" if td is None else td,
                        "toda1962": t62.get(n, ""),
                        "family": family(n), "lecture": lect.replace("$(\\mathbb Z/3)^2$", "(Z/3)^2")})
    if lang == "ru":  # one data file for both languages: the one the site has always published
        with open(OUT / "data" / "comparison.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(csvrows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(csvrows)

    zeros = (t("ни в одном варианте", "in either variant") if not zeros_rule
             else t("кроме ", "except for ") + ", ".join(map(str, zeros_rule)))
    page(lang, "comparison.html", t("Сравнение по n: правило, Тода, лекция",
                                    "Comparison by n: the rule, Toda, the lecture"), t(f"""
<p>Строка — группа $\\pi_n(S^2)=\\pi_n(S^3)$ ($n\\ge4$), 3-примарная часть. Число — ранг 3-кручения.</p>
<ul>
<li><b>E²</b> — нестабильный $E_2$ для $S^3$ при $p=3$ без башни над $\\pi_3$, то есть гомологии метабиблиотеки; цвета — $Q$-вес Ext (<a href="method.html">метод</a>), $n\\le{nmax}$.</li>
<li><b>хищное</b> — что остаётся после хищного правила с цветом $+1$. Две колонки — два способа заполнять цепочки: «low» и «high» (<a href="differentials.html">дифференциалы</a>). Результат окончателен до $n={last}$.</li>
<li><b>Тода 2003</b> — <a href="toda2003.html">наше прочтение</a> таблицы Тоды 2003 года ($n\\le{tmax}$); <b>Тода 1962</b> — его книга ($n\\le22$).</li>
</ul>
<div class="box">Хищное правило («low») совпадает с Тодой при всех $n\\le{agree_upto}$. Это ровно стемы $k=n-3<46$, которые Тода определил в 1967 году. Расхождения при $n\\le{tlast}$: {pis}; везде правило оставляет <i>больше</i> классов, чем Тода. Нулей при $49\\le n\\le{last}$ правило не даёт {zeros}.</div>
""", f"""
<p>Each row is the group $\\pi_n(S^2)=\\pi_n(S^3)$ ($n\\ge4$), its 3-primary part. A number is the rank of the 3-torsion.</p>
<ul>
<li><b>E²</b>: the unstable $E_2$ for $S^3$ at $p=3$ without the tower over $\\pi_3$, that is, the homology of the metalibrary; the colours are the $Q$-weight of Ext (<a href="method.html">method</a>), $n\\le{nmax}$.</li>
<li><b>rapacious</b>: what remains after the rapacious rule with colour $+1$. The two columns are two ways of filling the chains, “low” and “high” (<a href="differentials.html">differentials</a>). The result is final up to $n={last}$.</li>
<li><b>Toda 2003</b>: <a href="toda2003.html">our reading</a> of Toda's 2003 table ($n\\le{tmax}$); <b>Toda 1962</b>: his book ($n\\le22$).</li>
</ul>
<div class="box">The rapacious rule (“low”) agrees with Toda for all $n\\le{agree_upto}$. These are exactly the stems $k=n-3<46$ that Toda determined in 1967. Disagreements for $n\\le{tlast}$: {pis}; in every case the rule leaves <i>more</i> classes than Toda. For $49\\le n\\le{last}$ the rule gives no zeros {zeros}.</div>
""") + f"""{table(t(["n", "E²", "хищное<br>low", "хищное<br>high", "Тода<br>2003", "Тода<br>1962", "семейство", "<l>лекция", "<l>замечание"],
                   ["n", "E²", "rapacious<br>low", "rapacious<br>high", "Toda<br>2003", "Toda<br>1962", "family", "<l>lecture", "<l>remark"]),
       [r[:7] + [(r[7], "l"), (r[8], "l bad" if r[8] else "l")] for r in rows])}
<p><a href="data/comparison.csv">comparison.csv</a></p>""")

    # ---------- E2 classes ----------
    rowsE = []
    for n in range(4, nmax + 1):
        cl = sorted((s, c) for (m, s, c), k in E2.items() if m == n for _ in range(k))
        surv = sorted((s, c) for (m, s, c), k in El.items() if m == n and k for _ in range(k))
        fam = ""
        if n % 4 == 2 and n >= 6:
            fam = f"({(n - 2) // 4}, {(n - 6) // 4})"
        elif n % 4 == 1 and n >= 9:
            fam = f"({(n - 1) // 4}, {(n - 9) // 4})"
        rowsE.append([n, len(cl), (" ".join(f"({s},{c})" for s, c in cl), "l"),
                      (" ".join(f"({s},{c})" for s, c in surv) if n <= last else "—", "l"), fam,
                      t03.get(n, 0) if n <= tmax else "—"])
    page(lang, "e2.html", t("Классы E² по длине и цвету", "E² classes by length and colour"), t(f"""
<p>Каждый класс записан как (s, c): $s$ — длина слова (фильтрация Адамса), $c$ — цвет (число букв $\\mu$).
Цвета до $n={nmax}$ — $Q$-вес Ext; поклеточно проверены прямым счётом метабиблиотеки (<a href="method.html">метод</a>). «Осталось» — после хищного правила (цвет $+1$, «low»).
В колонке «семейство» — класс, стоящий на месте элемента Тоды ($n=4k+2$) или сэндвича ($n=4m+1$). Цвета этих классов идут 3 4 4 5 5 6 …, как сказано в лекции.</p>
<p><img src="e2_rapacious.png" alt="E² метабиблиотеки и хищные дифференциалы"></p>
<p class="muted">На картинке — до $n=100$; таблица ниже — до $n={nmax}$.</p>
""", f"""
<p>Each class is written as (s, c): $s$ is the length of the word (the Adams filtration), $c$ is the colour (the number of letters $\\mu$).
The colours up to $n={nmax}$ are the $Q$-weight of Ext, checked cell by cell against a direct computation of the metalibrary (<a href="method.html">method</a>). “Left” means after the rapacious rule (colour $+1$, “low”).
The column “family” gives the class standing in the place of a Toda element ($n=4k+2$) or of a sandwich ($n=4m+1$). The colours of these classes run 3 4 4 5 5 6 …, as stated in the lecture.</p>
<p><img src="e2_rapacious.png" alt="E² of the metalibrary and the rapacious differentials"></p>
<p class="muted">The picture goes up to $n=100$; the table below, up to $n={nmax}$.</p>
""") + f"""{table(t(["n", "dim E²", "<l>классы (s, c)", "<l>осталось после правила", "семейство (s, c)", "Тода 2003"],
                   ["n", "dim E²", "<l>classes (s, c)", "<l>left after the rule", "family (s, c)", "Toda 2003"]), rowsE)}
""" + t(f"""<p>Данные: <a href="data/e2_coloured.csv">e2_coloured.csv</a> ($E^2$ по $(n,s,\\text{{цвет}})$, $n\\le{nmax}$);
<a href="data/e2_metalib.csv">e2_metalib.csv</a> (прямой перебор: число слов, ранг дифференциала, гомологии по блокам, $n\\le{nbrute}$).</p>""",
        f"""<p>Data: <a href="data/e2_coloured.csv">e2_coloured.csv</a> ($E^2$ by $(n,s,\\text{{colour}})$, $n\\le{nmax}$);
<a href="data/e2_metalib.csv">e2_metalib.csv</a> (direct enumeration: the number of words, the rank of the differential, the homology by blocks, $n\\le{nbrute}$).</p>"""))

    # ---------- differentials ----------
    def drows(diffs):
        return [[f"$d_{{{x['r']}}}$", f"$\\pi_{{{x['from'][0]}}}$ ({x['from'][1]}, {x['from'][2]})",
                 f"$\\pi_{{{x['to'][0]}}}$ ({x['to'][1]}, {x['to'][2]})", x["rank"]] for x in diffs]
    only_l = [x for x in diffs_l if (x["from"], x["to"]) not in {(y["from"], y["to"]) for y in diffs_h}]
    only_h = [x for x in diffs_h if (x["from"], x["to"]) not in {(y["from"], y["to"]) for y in diffs_l}]
    d5 = [x for x in diffs_5 if x["r"] == 5 and x["from"][0] <= tmax + 1]
    amb = [n for n in range(4, min(last, tmax) + 1) if left_l[n] != left_h[n]]
    amb_note = "; ".join(
        f"$\\pi_{{{n}}}$: low {left_l[n]}, high {left_h[n]}, {t('Тода', 'Toda')} {t03[n]}"
        + (t(" — как low", " — as low") if t03[n] == left_l[n] else t(" — как high", " — as high")
           if t03[n] == left_h[n] else t(" — ни один", " — neither"))
        for n in amb)
    dh = t(["", "откуда (s, c)", "куда (s, c)", "ранг"], ["", "from (s, c)", "to (s, c)", "rank"])
    pis5 = ", ".join(f"$\\pi_{{{n}}}$" for n in dis5) or "—"
    page(lang, "differentials.html", t("Дифференциалы хищного правила", "Differentials of the rapacious rule"), t(f"""
<h2>Правило, как мы его поняли</h2>
<p>$d_r\\colon E_r(n,s,c)\\to E_r(n-1,\\,s+r,\\,c+1)$; на каждой странице $r=2,3,\\dots$ берётся максимальный ранг, который позволяют размерности. Страницы идут по порядку.</p>
<p>Из грамматики следует $\\text{{стем}}=4\\sum(\\text{{индексы}})-\\#\\lambda$, то есть $c\\equiv \\text{{стем}}+s \\pmod 4$. Поэтому стрелка «цвет $+1$» возможна только при $r\\equiv2\\pmod4$: $d_2, d_6, d_{{10}},\\dots$ Вариант «цвет $-1$» не даёт ни одного дифференциала, и в нём $\\pi_{{44}}$ остаётся с четырьмя классами, а лекция говорит, что там пусто.</p>
<h2>Где правило неоднозначно</h2>
<p>На странице $r$ возможные стрелки складываются в цепочки $x\\to y\\to z\\to\\cdots$ по убыванию $n$. Максимальный суммарный ранг на цепочке определён однозначно, а то, какие именно классы погибают, — нет. Средний класс может быть либо целью, либо источником. «low» заполняет цепочку от конца с меньшим $n$, «high» — от конца с большим. При $n\\le{last}$ варианты различаются только здесь:</p>
<p><b>только в «low»:</b></p>{table(dh, drows(only_l))}
<p><b>только в «high»:</b></p>{table(dh, drows(only_h))}
<p>Где варианты расходятся, а Тода известна ($n\\le{tmax}$): {amb_note}.</p>
<h2>Все дифференциалы («low»), $n\\le{tmax + 1}$</h2>
{table(dh, drows([x for x in diffs_l if x["from"][0] <= tmax + 1]))}
<p class="muted">Полный список до $n={nmax}$ — в <a href="data/differentials.json">differentials.json</a>.</p>
<h2>Чего правилу не хватает</h2>
<p>При $n\\le{tlast}$ правило расходится с Тодой в {pis}. Почти все лишние классы снимаются стрелками $d_5$ без смены цвета; при $p=3$ это $d_{{2p-1}}$, длина дифференциала Тоды. Если разрешить такие $d_5$ вдобавок к правилу (с тем же жадным заполнением), получаются такие $d_5$:</p>
{table(dh, drows(d5))}
<p>Остаются расхождения в {pis5}: жадный $d_5$ убивает там классы, которые у Тоды живы. Значит, Тоде нужны <i>некоторые</i> $d_5$ без смены цвета, но не все разрешённые. Ни один проверенный нами чисто цветовой вариант Тоду после $\\pi_{{48}}$ не воспроизводит.</p>
<p><a href="data/differentials.json">differentials.json</a></p>""", f"""
<h2>The rule as we understood it</h2>
<p>$d_r\\colon E_r(n,s,c)\\to E_r(n-1,\\,s+r,\\,c+1)$; on each page $r=2,3,\\dots$ the maximal rank the dimensions allow is taken. The pages are processed in order.</p>
<p>The grammar gives $\\text{{stem}}=4\\sum(\\text{{indices}})-\\#\\lambda$, that is, $c\\equiv \\text{{stem}}+s \\pmod 4$. Hence an arrow “colour $+1$” is possible only for $r\\equiv2\\pmod4$: $d_2, d_6, d_{{10}},\\dots$ The variant “colour $-1$” gives no differentials at all, and in it $\\pi_{{44}}$ keeps four classes, whereas the lecture says it is empty.</p>
<h2>Where the rule is ambiguous</h2>
<p>On page $r$ the possible arrows line up into chains $x\\to y\\to z\\to\\cdots$ with decreasing $n$. The maximal total rank on a chain is determined uniquely, but which classes die is not: a middle class can be either a target or a source. “low” fills a chain starting from the end with the smaller $n$, “high” from the end with the larger. For $n\\le{last}$ the two variants differ only here:</p>
<p><b>only in “low”:</b></p>{table(dh, drows(only_l))}
<p><b>only in “high”:</b></p>{table(dh, drows(only_h))}
<p>Where the variants differ and Toda's value is known ($n\\le{tmax}$): {amb_note}.</p>
<h2>All differentials (“low”), $n\\le{tmax + 1}$</h2>
{table(dh, drows([x for x in diffs_l if x["from"][0] <= tmax + 1]))}
<p class="muted">The full list up to $n={nmax}$ is in <a href="data/differentials.json">differentials.json</a>.</p>
<h2>What the rule is missing</h2>
<p>For $n\\le{tlast}$ the rule disagrees with Toda in {pis}. Almost all of the extra classes are removed by arrows $d_5$ that do not change the colour; at $p=3$ this is $d_{{2p-1}}$, the length of Toda's differential. Allowing such $d_5$ in addition to the rule (with the same greedy filling) gives the following $d_5$:</p>
{table(dh, drows(d5))}
<p>Disagreements remain in {pis5}: there the greedy $d_5$ kills classes that are alive in Toda. So Toda needs <i>some</i> colour-preserving $d_5$, but not all the allowed ones. None of the purely colour-based variants we checked reproduces Toda beyond $\\pi_{{48}}$.</p>
<p><a href="data/differentials.json">differentials.json</a></p>"""))

    # ---------- Toda 2003 ----------
    trows = []
    for k in sorted(toda2003.TOTAL):
        src = t("§5.6, с α-семействами", "§5.6, with α-families") if k in toda2003.OLD else "§6.5, mod A"
        printed = toda2003.OLD.get(k, toda2003.NEW_MOD_A.get(k))
        a = "" if k in toda2003.OLD else ("+1" if toda2003.alpha_on_s3(k) else "")
        note = t("Тода: не окончательно", "Toda: not final") if k in toda2003.NOT_FIXED else ""
        trows.append([k, k + 3, printed, a, toda2003.TOTAL[k], t62.get(k + 3, ""), (src, "l"), (note, "l")])
    if lang == "ru":
        with open(OUT / "data" / "toda2003_S3.csv", "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["k", "n", "printed", "alpha_added", "total", "toda1962", "source"])
            for r in trows:
                w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6][0]])
    page(lang, "toda2003.html", t("Столбец $S^3$ таблицы Тоды 2003 года", "The $S^3$ column of Toda's 2003 table"), t(f"""
<p>H. Toda, <i>Unstable 3-primary Homotopy Groups of Spheres</i>, Econoinformatics (Himeji Dokkyo University) <b>29</b> (2003), 1–77
(NDL BibID 6899969, CiNii crid 1523669554954337536). Скан с OCR — на странице Д. Равенеля:
<a href="https://www.sas.rochester.edu/mth/sites/doug-ravenel/otherpapers/Toda03-ocr.pdf">Toda03-ocr.pdf</a>
(страницы PDF 67–68 — §5.6, $k\\le55$; 80–81 — §6.5, $56\\le k\\le79$).</p>
<div class="box">
<p><b>Как читали.</b> Брали только столбец $n=3$, то есть $_3\\pi_{{3+k}}(S^3)={{}}_3\\pi_{{3+k}}(S^2)$. Каждая точка — $\\mathbb Z/3$ (по теореме Коэна–Мура–Нейзендорфера показатель 3-кручения $\\pi_*(S^3)$ равен 3). Строка таблицы, которая начинается правее $n=3$, не считается.</p>
<p><b>«mod A».</b> Таблица §6.5 дана по модулю нестабильных α-семейств. По §4.3 такое семейство даёт на $S^3$ по одному $\\mathbb Z/3$ в стемах $rq-2$ и $rq-1$ ($q=4$), то есть при $k\\equiv2,3\\pmod4$: это сэндвичи и элементы Тоды. Мы добавили их обратно (колонка «+α»). <b>Это место нашего прочтения стоит проверить в первую очередь.</b></p>
<p>Проверки прочтения: при $n\\le22$ совпадает с книгой Тоды 1962 года; ни в одном $n$ не превышает $E_2$.</p></div>
""", f"""
<p>H. Toda, <i>Unstable 3-primary Homotopy Groups of Spheres</i>, Econoinformatics (Himeji Dokkyo University) <b>29</b> (2003), 1–77
(NDL BibID 6899969, CiNii crid 1523669554954337536). An OCR'd scan is on D. Ravenel's page:
<a href="https://www.sas.rochester.edu/mth/sites/doug-ravenel/otherpapers/Toda03-ocr.pdf">Toda03-ocr.pdf</a>
(PDF pages 67–68: §5.6, $k\\le55$; 80–81: §6.5, $56\\le k\\le79$).</p>
<div class="box">
<p><b>How we read it.</b> We took only the column $n=3$, that is, $_3\\pi_{{3+k}}(S^3)={{}}_3\\pi_{{3+k}}(S^2)$. Each dot is a $\\mathbb Z/3$ (by the Cohen–Moore–Neisendorfer theorem the exponent of the 3-torsion of $\\pi_*(S^3)$ is 3). A row of the table that starts to the right of $n=3$ is not counted.</p>
<p><b>“mod A”.</b> The table of §6.5 is given modulo the unstable α-families. By §4.3 such a family contributes to $S^3$ one $\\mathbb Z/3$ in each of the stems $rq-2$ and $rq-1$ ($q=4$), that is, for $k\\equiv2,3\\pmod4$: these are the sandwiches and the Toda elements. We added them back (column “+α”). <b>This is the point of our reading to check first.</b></p>
<p>Checks of the reading: for $n\\le22$ it agrees with Toda's 1962 book; for no $n$ does it exceed $E_2$.</p></div>
""") + f"""{table(t(["k", "n", "напечатано", "+α", "итого", "Тода 1962", "<l>источник", "<l>"],
                   ["k", "n", "printed", "+α", "total", "Toda 1962", "<l>source", "<l>"]), trows)}
<p><a href="data/toda2003_S3.csv">toda2003_S3.csv</a></p>""")

    # ---------- method ----------
    page(lang, "method.html", t("Метод и проверки", "Method and checks"), t(f"""
<h2>Лямбда-алгебра</h2>
<p>Соглашения — как у С. О. Иванова, Р. В. Михайлова и Дж. Ву, <a href="https://arxiv.org/abs/1506.00952">arXiv:1506.00952</a>, §2, при $p=3$:
$\\deg\\lambda_i=4i-1$ ($i\\ge1$), $\\deg\\mu_j=4j$ ($j\\ge0$),
$a(k,j)=(-1)^{{j+1}}\\binom{{2(k-j)-1}}{{j}}$, $b(k,j)=(-1)^j\\binom{{2(k-j)}}{{j}}$.
Слово допустимо, если после $\\lambda_i$ следующий индекс $\\le 3i-1$, а после $\\mu_i$ — $\\le 3i$. $\\Lambda(1)$ — допустимые слова с первым индексом $\\le1$.</p>
<p>В статье $N(k)=k-[\\tfrac{{k+1}}{{p}}]$. Скобки мы читаем как потолок: с полом соотношение при $k=1$ содержало бы собственную левую часть. Дальше потолка все биномы и так нулевые. $N'(k)=k-\\lceil k/p\\rceil$.</p>
<p>Дифференциал — дифференцирование со знаком Кошуля, $\\partial(xy)=\\partial x\\cdot y+(-1)^{{|x|}}x\\,\\partial y$. Недопустимые произведения переписываются по соотношениям в допустимый базис, рекурсивно.</p>
<h2>Метабиблиотека</h2>
<p>Слова в $\\lambda_i,\\mu_i$ ($i\\ge1$), которые начинаются с $\\lambda_1$ или $\\mu_1$, кончаются на $\\lambda$ и допустимы. Это слова $\\Lambda(1)$ без $\\mu_0$, кончающиеся на $\\lambda$. Слова с $\\mu_0$ — это ровно слова, кончающиеся серией $\\mu_0$; они образуют подкомплекс $\\Lambda(1)\\mu_0$. Слова на $\\lambda$ образуют подкомплекс фактора $\\Lambda(1)/\\Lambda(1)\\mu_0$ — это проверено на каждом слове. Клетка слова: $n-1=2+4\\sum(\\text{{индексы}})-\\#\\lambda$; цвет — число $\\mu$.</p>
<h2>Проверки</h2>
<ul>
<li>$\\partial^2=0$ и $\\partial\\Lambda(1)\\subseteq\\Lambda(1)$ на всех 2,2 млн допустимых словах до стема 43.</li>
<li>$H(\\Lambda(1))$ совпадает с нестабильным $\\operatorname{{Ext}}$ сферы $S^3$ при $p=3$ из независимой программы <a href="https://github.com/JoeyBF/sseq">sseq/ext</a> (<code>resolve_unstable</code>, модуль <code>S_3[3]</code>) в каждой клетке (стем, $s$) до стема 43.</li>
<li>Гомологии метабиблиотеки при $n>3$ равны $H(\\Lambda(1))$ поклеточно по $(n,s,\\text{{цвет}})$ (до $n=46$) и равны $\\operatorname{{Ext}}$ из sseq по $(n,s)$ (до $n=75$). Выбрасывание $\\mu_0$ убирает только башню над $\\pi_3=\\mathbb Z$.</li>
<li>Две независимые реализации перебора — на Python и на Rust — дают побайтно один и тот же результат до $n=56$.</li>
</ul>
<h2>Цвет — это число бокштейнов</h2>
<p>У алгебры Стинрода при нечётном $p$ есть дополнительная градуировка: число $Q$ в элементе $Q(E)P(R)$ базиса Милнора. Её сохраняют все соотношения, а минимальная резольвента в sseq автоматически однородна по ней, поэтому $\\operatorname{{Ext}}$ получает третью градуировку $e$ ($Q$-вес). По степеням буквы отвечают: $\\lambda_i\\leftrightarrow P^i$ (вес 0), $\\mu_i\\leftrightarrow\\beta P^i$ (вес 1).</p>
<ul>
<li><b>Цвет $=e$</b> во всех 281 клетке $(n,s,\\text{{цвет}})$ при $4\\le n\\le75$, где цвета известны из прямого счёта лямбда-алгебры.</li>
<li>За $\\pi_{{75}}$ — во всех 180 клетках (67 ненулевых) до $\\pi_{{85}}$, посчитанных перебором блоков метабиблиотеки.</li>
<li>Поэтому $E^2$ с цветами на этом сайте до $n={nmax}$ взят из $Q$-веса (2 с счёта); за $\\pi_{{85}}$ равенство «цвет $=e$» не проверено независимо, но не нарушено нигде, где проверено.</li>
</ul>
<p>Вычисление $Q$-веса — пример <code>qgrade_dims</code> в форке <a href="https://github.com/ispacex/sseq/tree/math-54-qgrade">ispacex/sseq</a> (ветка <code>math-54-qgrade</code>).</p>
<h2>Границы</h2>
<ul><li>Хищное правило окончательно до $n={last}$; таблица Тоды 2003 года — до $n={tmax}$, так что сравнение с ней — до $n={tlast}$.</li>
<li>Тода 2003 $\\le E_2$ во всех $n\\le{tmax}$.</li></ul>
<p class="muted">Код открыт: <a href="https://github.com/ispacex/meta-rapacious">ispacex/meta-rapacious</a>.</p>""", f"""
<h2>The lambda algebra</h2>
<p>The conventions are those of S. O. Ivanov, R. Mikhailov and J. Wu, <a href="https://arxiv.org/abs/1506.00952">arXiv:1506.00952</a>, §2, at $p=3$:
$\\deg\\lambda_i=4i-1$ ($i\\ge1$), $\\deg\\mu_j=4j$ ($j\\ge0$),
$a(k,j)=(-1)^{{j+1}}\\binom{{2(k-j)-1}}{{j}}$, $b(k,j)=(-1)^j\\binom{{2(k-j)}}{{j}}$.
A word is admissible if the index following $\\lambda_i$ is $\\le 3i-1$ and the index following $\\mu_i$ is $\\le 3i$. $\\Lambda(1)$ consists of the admissible words with first index $\\le1$.</p>
<p>The paper has $N(k)=k-[\\tfrac{{k+1}}{{p}}]$. We read the brackets as the ceiling: with the floor, the relation for $k=1$ would contain its own left-hand side. Beyond the ceiling all the binomial coefficients vanish anyway. $N'(k)=k-\\lceil k/p\\rceil$.</p>
<p>The differential is a derivation with the Koszul sign, $\\partial(xy)=\\partial x\\cdot y+(-1)^{{|x|}}x\\,\\partial y$. Inadmissible products are rewritten in the admissible basis by the relations, recursively.</p>
<h2>The metalibrary</h2>
<p>The admissible words in $\\lambda_i,\\mu_i$ ($i\\ge1$) that begin with $\\lambda_1$ or $\\mu_1$ and end with a $\\lambda$. These are the words of $\\Lambda(1)$ without $\\mu_0$ that end with a $\\lambda$. The words containing $\\mu_0$ are exactly the words ending in a run of $\\mu_0$'s; they form the subcomplex $\\Lambda(1)\\mu_0$. The words ending in a $\\lambda$ form a subcomplex of the quotient $\\Lambda(1)/\\Lambda(1)\\mu_0$; this was checked on every word. The cell of a word: $n-1=2+4\\sum(\\text{{indices}})-\\#\\lambda$; the colour is the number of $\\mu$'s.</p>
<h2>Checks</h2>
<ul>
<li>$\\partial^2=0$ and $\\partial\\Lambda(1)\\subseteq\\Lambda(1)$ on all 2.2 million admissible words up to stem 43.</li>
<li>$H(\\Lambda(1))$ agrees with the unstable $\\operatorname{{Ext}}$ of the sphere $S^3$ at $p=3$ computed by the independent program <a href="https://github.com/JoeyBF/sseq">sseq/ext</a> (<code>resolve_unstable</code>, module <code>S_3[3]</code>) in every cell (stem, $s$) up to stem 43.</li>
<li>For $n>3$ the homology of the metalibrary equals $H(\\Lambda(1))$ cell by cell in $(n,s,\\text{{colour}})$ (up to $n=46$) and equals $\\operatorname{{Ext}}$ from sseq in $(n,s)$ (up to $n=75$). Discarding $\\mu_0$ removes only the tower over $\\pi_3=\\mathbb Z$.</li>
<li>Two independent implementations of the enumeration, in Python and in Rust, give byte-for-byte the same result up to $n=56$.</li>
</ul>
<h2>The colour is the number of Bocksteins</h2>
<p>For odd $p$ the Steenrod algebra carries an extra grading: the number of $Q$'s in an element $Q(E)P(R)$ of the Milnor basis. All the relations preserve it, and the minimal resolution in sseq is automatically homogeneous with respect to it, so $\\operatorname{{Ext}}$ acquires a third grading $e$ (the $Q$-weight). By degree, the letters correspond as $\\lambda_i\\leftrightarrow P^i$ (weight 0), $\\mu_i\\leftrightarrow\\beta P^i$ (weight 1).</p>
<ul>
<li><b>Colour $=e$</b> in all 281 cells $(n,s,\\text{{colour}})$ with $4\\le n\\le75$, where the colours are known from a direct computation in the lambda algebra.</li>
<li>Beyond $\\pi_{{75}}$: in all 180 cells (67 of them nonzero) up to $\\pi_{{85}}$ computed by enumerating the blocks of the metalibrary.</li>
<li>Therefore the coloured $E^2$ on this site up to $n={nmax}$ is taken from the $Q$-weight (2 s of computation); beyond $\\pi_{{85}}$ the equality “colour $=e$” has not been checked independently, but it fails nowhere it has been checked.</li>
</ul>
<p>The $Q$-weight is computed by the example <code>qgrade_dims</code> in the fork <a href="https://github.com/ispacex/sseq/tree/math-54-qgrade">ispacex/sseq</a> (branch <code>math-54-qgrade</code>).</p>
<h2>Limits</h2>
<ul><li>The rapacious rule is final up to $n={last}$; Toda's 2003 table goes up to $n={tmax}$, so the comparison with it goes up to $n={tlast}$.</li>
<li>Toda 2003 $\\le E_2$ for all $n\\le{tmax}$.</li></ul>
<p class="muted">The code is open: <a href="https://github.com/ispacex/meta-rapacious">ispacex/meta-rapacious</a>.</p>"""))

    # ---------- data ----------
    page(lang, "data.html", t("Данные", "Data"), t(f"""
<ul>
<li><a href="data/comparison.csv">comparison.csv</a> — по $n$: $E_2$, хищное правило («low»/«high»), Тода 2003, Тода 1962, семейство, лекция.</li>
<li><a href="data/e2_coloured.csv">e2_coloured.csv</a> — $E^2$ по $(n,s,\\text{{цвет}})$, $n\\le{nmax}$ (цвет $=Q$-вес).</li>
<li><a href="data/sseq_qweight_S3_p3.csv">sseq_qweight_S3_p3.csv</a> — нестабильный Ext для $S^3$ при $p=3$ по $(n,s,e)$, как его печатает <code>qgrade_dims</code>; строки <code>n,s,e,dim</code>, $n=t-s$.</li>
<li><a href="data/e2_metalib.csv">e2_metalib.csv</a> — прямой перебор метабиблиотеки по блокам $(n,s,\\text{{цвет}})$: число слов, ранг дифференциала, размерность $E^2$, $n\\le{nbrute}$.</li>
<li><a href="data/sseq_S3_p3.csv">sseq_S3_p3.csv</a> — тот же Ext из sseq/ext без веса: строки <code>n,s,dim</code>, $n\\le{nseq}$.</li>
<li><a href="data/differentials.json">differentials.json</a> — дифференциалы хищного правила (оба заполнения и вариант с $d_5$).</li>
<li><a href="data/toda2003_S3.csv">toda2003_S3.csv</a> — наше прочтение столбца $S^3$ таблицы Тоды 2003 года.</li>
</ul>""", f"""
<ul>
<li><a href="data/comparison.csv">comparison.csv</a>: by $n$, $E_2$, the rapacious rule (“low”/“high”), Toda 2003, Toda 1962, family, lecture (the last two columns are in Russian).</li>
<li><a href="data/e2_coloured.csv">e2_coloured.csv</a>: $E^2$ by $(n,s,\\text{{colour}})$, $n\\le{nmax}$ (colour $=Q$-weight).</li>
<li><a href="data/sseq_qweight_S3_p3.csv">sseq_qweight_S3_p3.csv</a>: the unstable Ext for $S^3$ at $p=3$ by $(n,s,e)$, as printed by <code>qgrade_dims</code>; rows <code>n,s,e,dim</code>, $n=t-s$.</li>
<li><a href="data/e2_metalib.csv">e2_metalib.csv</a>: direct enumeration of the metalibrary by blocks $(n,s,\\text{{colour}})$: the number of words, the rank of the differential, the dimension of $E^2$, $n\\le{nbrute}$.</li>
<li><a href="data/sseq_S3_p3.csv">sseq_S3_p3.csv</a>: the same Ext from sseq/ext without the weight; rows <code>n,s,dim</code>, $n\\le{nseq}$.</li>
<li><a href="data/differentials.json">differentials.json</a>: the differentials of the rapacious rule (both fillings and the variant with $d_5$).</li>
<li><a href="data/toda2003_S3.csv">toda2003_S3.csv</a>: our reading of the $S^3$ column of Toda's 2003 table (the source column is in Russian).</li>
</ul>"""))

    # ---------- index ----------
    page(lang, "index.html", t("Цветная метабиблиотека для 3-кручения $\\pi_n(S^2)$: наш пересчёт",
                               "The coloured metalibrary for the 3-torsion of $\\pi_n(S^2)$: our recomputation"), t(f"""
<p>Мы попробовали повторить «хищную спектралку» из первой лекции курса «Цветные метабиблиотеки. Разум пространства» (Р. В. Михайлов, 02.09.2016): посчитать лист $E^2$ цветной метабиблиотеки и применить к нему правило «съедать себя как можно быстрее, ограничиваясь только цветом».</p>
<h2>Что получилось</h2>
<ol>
<li><b>Лист $E^2$ метабиблиотеки с цветами посчитан до $\\pi_{{{nmax}}}$.</b> Цвет оказался числом бокштейнов ($Q$-весом) в нестабильном Ext; это проверено поклеточно прямым счётом лямбда-алгебры до $\\pi_{{75}}$ и выборочно до $\\pi_{{85}}$ (<a href="method.html">метод и проверки</a>).</li>
<li><b>Цвета сэндвичей и элементов Тоды</b> идут 3 4 4 5 5 6 …, как сказано в лекции (<a href="e2.html">классы</a>).</li>
<li><b>Хищное правило с цветом $+1$ совпадает с таблицей Тоды при всех $n\\le{agree_upto}$</b>, включая $\\pi_{{44}}=0$. Граница ровно на стемах $k<46$ — тех, что Тода определил в 1967 году.</li>
<li><b>Предсказания из лекции правило воспроизводит:</b> $\\pi_{{48}}=0$, а 3-кручение есть при всех $49\\le n\\le{last}$; в $\\pi_{{71}}$ — две копии $\\mathbb Z/3$ при одном из порядков поедания (<a href="comparison.html">сравнение</a>).</li>
<li><b>С таблицей Тоды 2003 года после $\\pi_{{48}}$ правило расходится</b> ({pis}), везде оставляя больше классов. У Тоды одна копия в $\\pi_{{71}}$ и нули в $\\pi_{{51}},\\pi_{{60}},\\pi_{{67}},\\pi_{{75}},\\pi_{{76}},\\pi_{{80}}$ (<a href="toda2003.html">наше прочтение</a>). Для $\\pi_{{49}}$–$\\pi_{{51}}$, $\\pi_{{59}}$, $\\pi_{{60}}$ это доказано так, что проверяется без доверия к нашей программе (<a href="verify.html">проверяемость</a>). Почти все лишние классы снимают $d_5$, сохраняющие цвет, но не все разрешённые (<a href="differentials.html">дифференциалы</a>).</li>
<li><b>Правило не определяет порядок поедания</b>, когда класс может быть и целью, и источником; от этого зависит, например, $\\pi_{{71}}$ (<a href="differentials.html">дифференциалы</a>).</li>
</ol>
<h2>Источники</h2>
<ul>
<li>Р. В. Михайлов, лекция 1 курса «Цветные метабиблиотеки. Разум пространства», лаборатория им. П. Л. Чебышева СПбГУ, 02.09.2016: <a href="https://www.youtube.com/watch?v=yE49kR_RA7o">YouTube</a>.</li>
<li>S. O. Ivanov, R. Mikhailov, J. Wu, <i>On nontriviality of homotopy groups of spheres</i>, <a href="https://arxiv.org/abs/1506.00952">arXiv:1506.00952</a> — лямбда-алгебра mod $p$.</li>
<li>H. Toda, <i>Unstable 3-primary Homotopy Groups of Spheres</i>, Econoinformatics 29 (2003) — <a href="https://www.sas.rochester.edu/mth/sites/doug-ravenel/otherpapers/Toda03-ocr.pdf">скан</a>; H. Toda, <i>Composition Methods in Homotopy Groups of Spheres</i>, 1962.</li>
<li>Проект sseq, программа ext: <a href="https://github.com/JoeyBF/sseq">github.com/JoeyBF/sseq</a> — независимое вычисление нестабильного Ext.</li>
</ul>
<h2>Сопутствующие репозитории</h2>
<ul>
<li><a href="https://github.com/ispacex/dimension-subrings">ispacex/dimension-subrings</a> — вычисления и Lean по размерным подгруппам: вопрос $D_5(G)\\subseteq\\gamma_4(G)$ для групп. Сопутствующая работа к статье В. Ионина, Р. В. Михайлова и Т. Петрова <i>Dimension subrings of Lie rings</i> (<a href="https://arxiv.org/abs/2610.02042">arXiv:2610.02042</a>), где аналогичное включение доказано для колец Ли. К метабиблиотеке отношения не имеет.</li>
<li><a href="https://gitlab.com/ispacex/cflint-fast-core">ispacex/cflint-fast-core</a> (GitLab) — быстрое ядро для целочисленных размерных подгрупп $D_n(G)$ конечных $p$-групп (C/FLINT).</li>
<li><a href="https://github.com/ispacex/meta-rapacious">ispacex/meta-rapacious</a> — код пересчёта: лямбда-алгебра, $E^2$ метабиблиотеки по цвету (Python и Rust), хищное правило, генератор и проверялки сертификатов, Lean-проект и генератор этого сайта (лицензия MIT).</li>
<li><a href="https://github.com/ispacex/metalibrary">ispacex/metalibrary</a> — данные и страницы этого сайта; сертификаты проверки выложены его <a href="https://github.com/ispacex/metalibrary/releases/tag/certificates-2026-10-15">релизом</a>. Страницы собираются кодом из <a href="https://github.com/ispacex/meta-rapacious">ispacex/meta-rapacious</a> (<a href="verify.html">проверяемость</a>).</li>
</ul>""", f"""
<p>We tried to reproduce the “rapacious spectral sequence” from the first lecture of the course “Coloured metalibraries. The mind of space” (R. Mikhailov, 2 September 2016): to compute the $E^2$ page of the coloured metalibrary and to apply to it the rule “eat yourself as fast as possible, constrained only by colour”.</p>
<h2>Results</h2>
<ol>
<li><b>The coloured $E^2$ page of the metalibrary is computed up to $\\pi_{{{nmax}}}$.</b> The colour turned out to be the number of Bocksteins (the $Q$-weight) in the unstable Ext; this was checked cell by cell against a direct computation in the lambda algebra up to $\\pi_{{75}}$ and selectively up to $\\pi_{{85}}$ (<a href="method.html">method and checks</a>).</li>
<li><b>The colours of the sandwiches and the Toda elements</b> run 3 4 4 5 5 6 …, as stated in the lecture (<a href="e2.html">classes</a>).</li>
<li><b>The rapacious rule with colour $+1$ agrees with Toda's table for all $n\\le{agree_upto}$</b>, including $\\pi_{{44}}=0$. The boundary is exactly the stems $k<46$, the ones Toda determined in 1967.</li>
<li><b>The rule reproduces the predictions of the lecture:</b> $\\pi_{{48}}=0$, and there is 3-torsion for all $49\\le n\\le{last}$; in $\\pi_{{71}}$ there are two copies of $\\mathbb Z/3$ under one of the orders of eating (<a href="comparison.html">comparison</a>).</li>
<li><b>Beyond $\\pi_{{48}}$ the rule disagrees with Toda's 2003 table</b> ({pis}), leaving more classes in every case. Toda has one copy in $\\pi_{{71}}$ and zeros in $\\pi_{{51}},\\pi_{{60}},\\pi_{{67}},\\pi_{{75}},\\pi_{{76}},\\pi_{{80}}$ (<a href="toda2003.html">our reading</a>). For $\\pi_{{49}}$–$\\pi_{{51}}$, $\\pi_{{59}}$, $\\pi_{{60}}$ this is proved in a way that can be checked without trusting our program (<a href="verify.html">verifiability</a>). Almost all of the extra classes are removed by colour-preserving $d_5$'s, but not by all the allowed ones (<a href="differentials.html">differentials</a>).</li>
<li><b>The rule does not determine the order of eating</b> when a class can be both a target and a source; $\\pi_{{71}}$, for instance, depends on it (<a href="differentials.html">differentials</a>).</li>
</ol>
<h2>Sources</h2>
<ul>
<li>R. Mikhailov, lecture 1 of the course <i>Tsvetnye metabiblioteki. Razum prostranstva</i> (Coloured metalibraries. The mind of space), Chebyshev Laboratory, St. Petersburg State University, 2 September 2016, in Russian: <a href="https://www.youtube.com/watch?v=yE49kR_RA7o">YouTube</a>.</li>
<li>S. O. Ivanov, R. Mikhailov, J. Wu, <i>On nontriviality of homotopy groups of spheres</i>, <a href="https://arxiv.org/abs/1506.00952">arXiv:1506.00952</a>: the mod-$p$ lambda algebra.</li>
<li>H. Toda, <i>Unstable 3-primary Homotopy Groups of Spheres</i>, Econoinformatics 29 (2003): <a href="https://www.sas.rochester.edu/mth/sites/doug-ravenel/otherpapers/Toda03-ocr.pdf">scan</a>; H. Toda, <i>Composition Methods in Homotopy Groups of Spheres</i>, 1962.</li>
<li>The sseq project, program ext: <a href="https://github.com/JoeyBF/sseq">github.com/JoeyBF/sseq</a>: an independent computation of the unstable Ext.</li>
</ul>
<h2>Related repositories</h2>
<ul>
<li><a href="https://github.com/ispacex/dimension-subrings">ispacex/dimension-subrings</a>: computations and Lean on dimension subgroups, the question $D_5(G)\\subseteq\\gamma_4(G)$ for groups. A companion to the paper of V. Ionin, R. Mikhailov and T. Petrov, <i>Dimension subrings of Lie rings</i> (<a href="https://arxiv.org/abs/2610.02042">arXiv:2610.02042</a>), which proves the analogous inclusion for Lie rings. It is not about the metalibrary.</li>
<li><a href="https://gitlab.com/ispacex/cflint-fast-core">ispacex/cflint-fast-core</a> (GitLab): a fast core for integral dimension subgroups $D_n(G)$ of finite $p$-groups (C/FLINT).</li>
<li><a href="https://github.com/ispacex/meta-rapacious">ispacex/meta-rapacious</a>: the code of the recomputation: the lambda algebra, the $E^2$ of the metalibrary by colour (Python and Rust), the rapacious rule, the generator and the checkers of the certificates, the Lean project and the generator of this site (MIT license).</li>
<li><a href="https://github.com/ispacex/metalibrary">ispacex/metalibrary</a>: the data and the pages of this site; the verification certificates are published as its <a href="https://github.com/ispacex/metalibrary/releases/tag/certificates-2026-10-15">release</a>. The pages are built by the code in <a href="https://github.com/ispacex/meta-rapacious">ispacex/meta-rapacious</a> (<a href="verify.html">verifiability</a>).</li>
</ul>"""))

    # ---------- verifiability ----------
    vrows = [[49, 2, 1], [50, 3, 1], [51, 1, 0], [59, 2, 1], [60, 1, 0]]
    page(lang, "verify.html", t("Проверяемость расхождения с Тодой", "Verifiability of the disagreement with Toda"), t("""
<p>Главный вывод сравнения — хищное правило оставляет больше классов, чем таблица Тоды 2003 года. Чтобы в этом не пришлось
верить нашей программе, для пяти первых расхождений мы сделали доказательство, которое проверяется независимо.</p>
<div class="box"><p><b>Утверждение.</b> Если применить хищное правило (стрелки $d_r\\colon(n,s,c)\\to(n-1,s+r,c+1)$, $r\\ge2$,
максимальный ранг на каждой странице) к настоящему листу $E^2$ метабиблиотеки, то над $\\pi_n(S^2)$ остаётся</p>
""" + table(["n", "правило (оба порядка заполнения)", "Тода 2003"], vrows) + """
<p>Значения Тоды не доказываются, а цитируются.</p></div>

<h2>Как устроено</h2>
<ol>
<li><b>Локальность.</b> Правило проводит стрелки только между ненулевыми клетками $E^2$, поэтому идёт отдельно на каждой
компоненте связности графа возможных стрелок. Для данных столбцов достаточно точных размерностей клеток этих компонент и того,
что все соседние клетки и все прочие клетки столбцов нулевые: 89 клеток (100 блоков дифференциала) для $\\pi_{49}$–$\\pi_{51}$
и 86 клеток (111 блоков, самый большой — 308 910 × 269 346) для $\\pi_{59}$–$\\pi_{60}$.</li>
<li><b>Сертификаты</b> пишет программа, которой доверять не нужно.
<ul><li><i>Ранг блока</i> $\\ge r$: векторы $y_1,\\dots,y_r$ из слов-источников, у которых $d(y_i)$ имеют попарно разные старшие
члены (матрица треугольная). Проверка — только вычисление $d$, без исключения Гаусса; в среднем 1,5 слова на вектор.</li>
<li><i>Ненулевая клетка</i> размерности $h$: $h$ циклов $z$ ($dz=0$) и $h$ коциклов $\\varphi$ ($\\varphi\\circ d=0$) с обратимой
матрицей $\\varphi_j(z_i)$.</li>
<li>Вместе с оценками рангов это даёт точную размерность каждой клетки.</li></ul></li>
<li><b>Проверялка</b> написана заново по §2 статьи Иванова–Михайлова–Ву (соотношения, $\\partial$, допустимость, перечисление слов)
и не использует код, которым считался $E^2$. Она проверяет сертификаты, полноту набора клеток и сама прогоняет правило.
Испорченный сертификат она отвергает (проверено четырьмя видами порчи).</li>
<li><b>Lean 4</b> — третья независимая реализация алгебры и тех же проверок. Теорема о числе выживших классов доказывается
вычислением (<code>native_decide</code>, то есть с доверием к компилятору Lean); неверное значение Lean отвергает.</li>
</ol>

<h2>Прогоны</h2>
""" + table(["столбцы", "генератор", "проверялка (Python)", "Lean"],
            [["π49–π51", "3 с", "34 с, 1,1 ГБ", "4,6 мин, 1,6 ГБ"],
             ["π59–π60", "72 с", "8 мин, 4,3 ГБ", "3 ч 28 мин, 7,7 ГБ"]]) + """
<p>Сертификаты занимают 1,5 и 19 МБ (сжатые).</p>

<h2>Чего здесь нет</h2>
<ul>
<li>Значения Тоды не проверяются.</li>
<li>Что $E^2$ этого комплекса — $E^2$ спектральной последовательности из статьи, и что лямбда-алгебра задана формулами §2 верно, —
математика статьи. Проверялки проверяют $d^2=0$ на малых клетках как тест соглашений.</li>
<li>Само правило — наше прочтение лекции (<a href="differentials.html">дифференциалы</a>).</li>
<li>В Lean не доказано, что вычислительные проверки влекут утверждения линейной алгебры: Lean здесь — независимая программа
с теоремой о результате её работы.</li>
</ul>

<p><b>Сертификаты выложены:</b> <a href="https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15/cert_49_50_51.tar.gz">cert_49_50_51.tar.gz</a> (1,5 МБ),
<a href="https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15/cert_59_60.tar.gz">cert_59_60.tar.gz</a> (19 МБ), контрольные суммы — <a href="https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15/SHA256SUMS">SHA256SUMS</a>
(<a href="https://github.com/ispacex/metalibrary/releases/tag/certificates-2026-10-15">релиз</a>). В архиве — по файлу на блок и на ненулевую клетку в формате, описанном выше.</p>
<p><b>Код генератора, проверялки и Lean-проекта открыт:</b> <a href="https://github.com/ispacex/meta-rapacious">ispacex/meta-rapacious</a>, каталог <a href="https://github.com/ispacex/meta-rapacious/tree/main/metalibrary/cert"><code>metalibrary/cert</code></a> (там же — как повторить проверку).</p>
""", """
<p>The main conclusion of the comparison is that the rapacious rule leaves more classes than Toda's 2003 table. So that this
need not rest on trust in our program, for the first five disagreements we made a proof that can be checked independently.</p>
<div class="box"><p><b>Claim.</b> If the rapacious rule (arrows $d_r\\colon(n,s,c)\\to(n-1,s+r,c+1)$, $r\\ge2$,
maximal rank on every page) is applied to the actual $E^2$ page of the metalibrary, then over $\\pi_n(S^2)$ there remain</p>
""" + table(["n", "the rule (both filling orders)", "Toda 2003"], vrows) + """
<p>Toda's values are quoted, not proved.</p></div>

<h2>How it works</h2>
<ol>
<li><b>Locality.</b> The rule draws arrows only between nonzero cells of $E^2$, so it runs separately on each connected
component of the graph of possible arrows. For the given columns it suffices to know the exact dimensions of the cells of these
components and that all the neighbouring cells and all the other cells of the columns are zero: 89 cells (100 blocks of the
differential) for $\\pi_{49}$–$\\pi_{51}$ and 86 cells (111 blocks, the largest 308,910 × 269,346) for $\\pi_{59}$–$\\pi_{60}$.</li>
<li><b>Certificates</b> are written by a program that need not be trusted.
<ul><li><i>Rank of a block</i> $\\ge r$: vectors $y_1,\\dots,y_r$ of source words whose $d(y_i)$ have pairwise distinct leading
terms (the matrix is triangular). Checking it is only computing $d$, with no Gaussian elimination; on average 1.5 words per vector.</li>
<li><i>A nonzero cell</i> of dimension $h$: $h$ cycles $z$ ($dz=0$) and $h$ cocycles $\\varphi$ ($\\varphi\\circ d=0$) with an
invertible matrix $\\varphi_j(z_i)$.</li>
<li>Together with the rank bounds this gives the exact dimension of every cell.</li></ul></li>
<li><b>The checker</b> is written from scratch following §2 of the Ivanov–Mikhailov–Wu paper (relations, $\\partial$,
admissibility, enumeration of words) and does not use the code that computed $E^2$. It checks the certificates and the
completeness of the set of cells, and runs the rule itself. It rejects a corrupted certificate (tested with four kinds of corruption).</li>
<li><b>Lean 4</b> is a third independent implementation of the algebra and of the same checks. The theorem on the number of
surviving classes is proved by computation (<code>native_decide</code>, that is, trusting the Lean compiler); Lean rejects a wrong value.</li>
</ol>

<h2>Runs</h2>
""" + table(["columns", "generator", "checker (Python)", "Lean"],
            [["π49–π51", "3 s", "34 s, 1.1 GB", "4.6 min, 1.6 GB"],
             ["π59–π60", "72 s", "8 min, 4.3 GB", "3 h 28 min, 7.7 GB"]]) + """
<p>The certificates take 1.5 and 19 MB (compressed).</p>

<h2>What is not covered here</h2>
<ul>
<li>Toda's values are not checked.</li>
<li>That the $E^2$ of this complex is the $E^2$ of the spectral sequence of the paper, and that the formulas of §2 define the
lambda algebra correctly, is the mathematics of the paper. The checkers verify $d^2=0$ on small cells as a test of the conventions.</li>
<li>The rule itself is our reading of the lecture (<a href="differentials.html">differentials</a>).</li>
<li>It is not proved in Lean that the computational checks imply the statements of linear algebra: Lean here is an independent
program with a theorem about the result of its own run.</li>
</ul>

<p><b>The certificates are published:</b> <a href="https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15/cert_49_50_51.tar.gz">cert_49_50_51.tar.gz</a> (1.5 MB),
<a href="https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15/cert_59_60.tar.gz">cert_59_60.tar.gz</a> (19 MB), checksums in <a href="https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15/SHA256SUMS">SHA256SUMS</a>
(<a href="https://github.com/ispacex/metalibrary/releases/tag/certificates-2026-10-15">release</a>). Each archive holds one file per block and per non-zero cell, in the format described above.</p>
<p><b>The code of the generator, the checker and the Lean project is open:</b> <a href="https://github.com/ispacex/meta-rapacious">ispacex/meta-rapacious</a>, directory <a href="https://github.com/ispacex/meta-rapacious/tree/main/metalibrary/cert"><code>metalibrary/cert</code></a> (with how to repeat the check).</p>
"""), contact=True)

    # ---------- notes on sources ----------
    page(lang, "notes.html", t("Заметки об источниках", "Notes on sources"), t("""
<p>Здесь — то, что мы заметили в чужих таблицах и программах, пока сверяли с ними свои данные.
<b>В отличие от остальных страниц, речь идёт о 2-примарной части</b> гомотопических групп сфер.</p>

<h2>Пакет Н. Стрикленда для Mathematica (Toda.m)</h2>
<p>N. Strickland, пакет о нестабильных гомотопических группах сфер до 19-го стема:
<a href="https://strickland1.org/toda/">strickland1.org/toda</a> (файлы <code>Toda.m</code>, <code>LambdaAlgebra.m</code>,
<code>LambdaData.m</code>, <code>TodaChecks.m</code>). Данные в основном из книги Тоды <i>Composition Methods in Homotopy Groups
of Spheres</i> (1962). Пакет хранит группы $\\pi_{n+k}(S^n)$ по модулю нечётного кручения, образующие, порядки и 962 соотношения
между композициями, надстройкой $E$, инвариантом Хопфа $H$ и умножением Уайтхеда $P$. Его лямбда-алгебра — только mod 2.</p>
<p>Mathematica у нас нет, поэтому данные пакета мы прочитали собственной программой и прогнали проверки согласованности:
перенос проверок автора (<code>TodaChecks.m</code>) и свои — на степени, порядки и лямбда-представителей. Независимая mod-2
лямбда-алгебра полностью совпала с <code>LambdaData.m</code>. Остальное нашлось как ошибки в данных:</p>
<ol>
<li><code>Toda.m</code>, строка 1623: правило <code>Sigma[Sigma[sigmasecond]] -&gt; 2 Sigma[sigma[8]]</code> приравнивает элементы разных групп,
$\\pi_{15}(S^8)$ и $\\pi_{16}(S^9)$; правило при этом срабатывает.</li>
<li>Строка 2126: <code>o[Sigma[sigmaprime],eta[15],epsilon[16]] -&gt; Sigma[zetaprime]</code> — справа должно быть $\\Sigma^2\\zeta'$.
Это единственное нарушение $E\\circ P=0$, которое находят проверки.</li>
<li>Строки 1947–1960: опечатка в имени функции (<code>AddRelations</code>), из-за неё три соотношения не добавляются.</li>
<li>Строка 1144: <code>AddOrderRule</code> вызван с четырьмя аргументами вместо пяти, поэтому элемент $w_n$ при нечётном $n$ не получает порядок 2.</li>
<li>Строка 1450: <code>SetOrder[o[nu[6],kappa[9]],4,"Toda, Theorem 12.7"]</code> — порядок $\\nu_6\\circ\\kappa_9$ равен 2, а не 4
(см. ниже). Из-за этого пакет даёт $\\pi_{23}(S^6)\\cong\\mathbb Z_4\\oplus(\\mathbb Z_2)^3$ вместо $(\\mathbb Z_2)^4$.</li>
<li>Строка 1563: <code>SetOrder[o[omega[17],nu[32]],2,...]</code> — опечатка, должно быть <code>nu[33]</code>; порядок
$\\omega_{17}\\circ\\nu_{33}$ поэтому не задан, и в $\\pi_{36}(S^{17})$ появляется лишнее слагаемое $\\mathbb Z$.</li>
<li>Не задан порядок $\\nu_7\\circ\\kappa_{10}$ (он равен 2: $\\pi_{24}(S^7)\\cong(\\mathbb Z_2)^4$, Тода, теорема 12.7), отсюда
лишнее $\\mathbb Z$ в $\\pi_{24}(S^7)$.</li>
<li>Мелкие ошибки в примерах документации <code>toda.pdf</code>.</li>
</ol>
<p>Помимо этого, проверки показывают пробелы — образы $E$, $H$, $P$ в 33, 14 и 29 группах не сводятся к образующим.
Автор сам предупреждает о такой неполноте на странице пакета, противоречий за ней не найдено.</p>

<h2>$\\pi_{23}(S^6)\\cong(\\mathbb Z_2)^4$: порядок $\\nu_6\\kappa_9$ равен 2</h2>
<p>Сверка групп пакета с таблицей Тоды в перепечатке Равенела (<i>Complex Cobordism</i>, 3-е изд., табл. A3.4, с. 390) дала 377
совпадений из 380 клеток ($2\\le n\\le21$, $k\\le19$). Все три расхождения — ошибки пакета (пп. 5–7 выше). Про $\\pi_{23}(S^6)$:</p>
<ul>
<li>таблица Тоды у Равенела и копия в <a href="https://math.pku.edu.cn/teachers/zhaoxa/_web_resource/_math_table/sphere_homotopy.htm">таблице PKU</a>: $(\\mathbb Z_2)^4$ (обе — перепечатки книги Тоды);</li>
<li>Miyauchi, Mukai, Ohara, <a href="https://arxiv.org/abs/1705.00273">arXiv:1705.00273</a>, §3, берут продолжение $\\nu_6\\kappa_9$ на пространство Мура $M^{24}$ — оно существует только при $2\\nu_6\\kappa_9=0$;</li>
<li><a href="https://arxiv.org/abs/2107.00154">arXiv:2107.00154</a>, доказательство предл. 3.4: $\\{P(E\\theta)+\\nu_6\\kappa_9,\\ \\eta_6\\mu_7\\sigma_{16}\\}\\cong(\\mathbb Z_2)^2$; так как $P(E\\theta)$ порядка 2 (это есть и в самом пакете, строка 1438), $2\\nu_6\\kappa_9=0$;</li>
<li>то же из соотношений: $2\\kappa_7=\\bar\\nu_7\\nu_{15}^2$ и $\\nu_6\\bar\\nu_9=P(\\nu_{13}^2)$ дают $2\\nu_6\\kappa_9=P(\\nu_{13}^4)=0$, так как $\\pi^s_{12}=0$ (наш вывод).</li>
</ul>
<p>Прямо это сказано у Y. Hirato, H. Kachi, J. Mukai, <i>21-st and 22-nd homotopy groups of the n-th rotation group</i>,
J. Fac. Sci. Shinshu Univ. 41 (2006), с. 12 (<a href="https://soar-ir.repo.nii.ac.jp/records/12005">открытый доступ</a>):
$\\pi^6_{23}=\\{P(\\Sigma\\theta),\\nu_6\\kappa_9,\\bar\\mu_6,\\eta_6\\mu_7\\sigma_{16}\\}\\cong(\\mathbb Z_2)^4$. Порядок 4 есть у соседнего
$\\nu_5\\kappa_8$ (там же, с. 11: $2\\nu_5\\kappa_8\\ne0$), видимо, отсюда и ошибка. Текст самой теоремы 12.7 книги Тоды в открытом
доступе мы не нашли.</p>
""", """
<p>Here is what we noticed in other people's tables and programs while checking our data against them.
<b>Unlike the other pages, this one is about the 2-primary part</b> of the homotopy groups of spheres.</p>

<h2>N. Strickland's Mathematica package (Toda.m)</h2>
<p>N. Strickland, a package on the unstable homotopy groups of spheres up to the 19th stem:
<a href="https://strickland1.org/toda/">strickland1.org/toda</a> (files <code>Toda.m</code>, <code>LambdaAlgebra.m</code>,
<code>LambdaData.m</code>, <code>TodaChecks.m</code>). The data come mainly from Toda's book <i>Composition Methods in Homotopy Groups
of Spheres</i> (1962). The package stores the groups $\\pi_{n+k}(S^n)$ modulo odd torsion, generators, orders and 962 relations
among compositions, the suspension $E$, the Hopf invariant $H$ and the Whitehead product $P$. Its lambda algebra is mod 2 only.</p>
<p>We have no Mathematica, so we read the package's data with our own program and ran consistency checks on it:
a port of the author's checks (<code>TodaChecks.m</code>) and our own, on degrees, orders and lambda representatives. An independent
mod-2 lambda algebra agreed with <code>LambdaData.m</code> completely. The rest turned up as errors in the data:</p>
<ol>
<li><code>Toda.m</code>, line 1623: the rule <code>Sigma[Sigma[sigmasecond]] -&gt; 2 Sigma[sigma[8]]</code> equates elements of different groups,
$\\pi_{15}(S^8)$ and $\\pi_{16}(S^9)$; and the rule does fire.</li>
<li>Line 2126: <code>o[Sigma[sigmaprime],eta[15],epsilon[16]] -&gt; Sigma[zetaprime]</code>: the right-hand side should be $\\Sigma^2\\zeta'$.
This is the only violation of $E\\circ P=0$ that the checks find.</li>
<li>Lines 1947–1960: a typo in a function name (<code>AddRelations</code>), because of which three relations are not added.</li>
<li>Line 1144: <code>AddOrderRule</code> is called with four arguments instead of five, so the element $w_n$ for odd $n$ does not get order 2.</li>
<li>Line 1450: <code>SetOrder[o[nu[6],kappa[9]],4,"Toda, Theorem 12.7"]</code>: the order of $\\nu_6\\circ\\kappa_9$ is 2, not 4
(see below). Because of this the package gives $\\pi_{23}(S^6)\\cong\\mathbb Z_4\\oplus(\\mathbb Z_2)^3$ instead of $(\\mathbb Z_2)^4$.</li>
<li>Line 1563: <code>SetOrder[o[omega[17],nu[32]],2,...]</code>: a typo, it should be <code>nu[33]</code>; so the order of
$\\omega_{17}\\circ\\nu_{33}$ is not set, and a spurious summand $\\mathbb Z$ appears in $\\pi_{36}(S^{17})$.</li>
<li>The order of $\\nu_7\\circ\\kappa_{10}$ is not set (it is 2: $\\pi_{24}(S^7)\\cong(\\mathbb Z_2)^4$, Toda, Theorem 12.7), hence
a spurious $\\mathbb Z$ in $\\pi_{24}(S^7)$.</li>
<li>Minor errors in the examples of the documentation <code>toda.pdf</code>.</li>
</ol>
<p>Besides these, the checks show gaps: the images under $E$, $H$, $P$ in 33, 14 and 29 groups respectively do not reduce to
generators. The author himself warns of such incompleteness on the package's page; no contradictions were found behind it.</p>

<h2>$\\pi_{23}(S^6)\\cong(\\mathbb Z_2)^4$: the order of $\\nu_6\\kappa_9$ is 2</h2>
<p>Comparing the package's groups with Toda's table as reprinted by Ravenel (<i>Complex Cobordism and Stable Homotopy Groups of
Spheres</i>, 3rd ed., Table A3.4, p. 390) gave 377 matches out of 380 cells ($2\\le n\\le21$, $k\\le19$). All three discrepancies
are errors of the package (items 5–7 above). On $\\pi_{23}(S^6)$:</p>
<ul>
<li>Toda's table in Ravenel and its copy in the <a href="https://math.pku.edu.cn/teachers/zhaoxa/_web_resource/_math_table/sphere_homotopy.htm">PKU table</a>: $(\\mathbb Z_2)^4$ (both are reprints of Toda's book);</li>
<li>Miyauchi, Mukai, Ohara, <a href="https://arxiv.org/abs/1705.00273">arXiv:1705.00273</a>, §3, take an extension of $\\nu_6\\kappa_9$ to the Moore space $M^{24}$, which exists only if $2\\nu_6\\kappa_9=0$;</li>
<li><a href="https://arxiv.org/abs/2107.00154">arXiv:2107.00154</a>, proof of Prop. 3.4: $\\{P(E\\theta)+\\nu_6\\kappa_9,\\ \\eta_6\\mu_7\\sigma_{16}\\}\\cong(\\mathbb Z_2)^2$; since $P(E\\theta)$ has order 2 (the package itself has this too, line 1438), $2\\nu_6\\kappa_9=0$;</li>
<li>the same from the relations: $2\\kappa_7=\\bar\\nu_7\\nu_{15}^2$ and $\\nu_6\\bar\\nu_9=P(\\nu_{13}^2)$ give $2\\nu_6\\kappa_9=P(\\nu_{13}^4)=0$, since $\\pi^s_{12}=0$ (our derivation).</li>
</ul>
<p>This is stated explicitly by Y. Hirato, H. Kachi, J. Mukai, <i>21-st and 22-nd homotopy groups of the n-th rotation group</i>,
J. Fac. Sci. Shinshu Univ. 41 (2006), p. 12 (<a href="https://soar-ir.repo.nii.ac.jp/records/12005">open access</a>):
$\\pi^6_{23}=\\{P(\\Sigma\\theta),\\nu_6\\kappa_9,\\bar\\mu_6,\\eta_6\\mu_7\\sigma_{16}\\}\\cong(\\mathbb Z_2)^4$. It is the neighbouring
$\\nu_5\\kappa_8$ that has order 4 (ibid., p. 11: $2\\nu_5\\kappa_8\\ne0$), which is probably where the error comes from. We have not
found the text of Theorem 12.7 of Toda's book itself in open access.</p>
"""))

    # ---------- search ----------
    page(lang, "search.html", t("Поиск по сайту", "Site search"), t(f"""
<p><input type="search" id="q" placeholder="например: 71, хищное правило, d5, Стрикленд" autocomplete="off" spellcheck="false"
 style="padding:.45em .6em;width:100%;max-width:32em;font-size:1em"></p>
<p id="status"></p>
<ul id="results" style="list-style:none;padding:0"></ul>
<p><small>Ищет по тексту всех страниц, включая строки таблиц. Несколько слов — найдутся места, где есть все они.
Регистр и «ё» не важны. Группу $\\pi_{{71}}$ ищите по номеру: «71» (найдутся и строки таблиц, и текст).
Поиск — движок сайта <a href="https://ispacex.github.io/search/">ispacex.github.io</a>; ⌘K / Ctrl-K на любой странице открывает переход по разделам.</small></p>
""", f"""
<p><input type="search" id="q" placeholder="for example: 71, rapacious rule, d5, Strickland" autocomplete="off" spellcheck="false"
 style="padding:.45em .6em;width:100%;max-width:32em;font-size:1em"></p>
<p id="status"></p>
<ul id="results" style="list-style:none;padding:0"></ul>
<p><small>Searches the text of every page, table rows included. Several words find the places that contain all of them.
Case does not matter. Look for the group $\\pi_{{71}}$ by its number: “71” (finds both table rows and text).
This page searches the English pages; <a href="ru/search.html" hreflang="ru">the Russian search</a> searches the Russian ones.
The search is the engine of <a href="https://ispacex.github.io/en/search/">ispacex.github.io</a>; ⌘K / Ctrl-K on any page opens the jump to a section.</small></p>
""") + f"""<style>#results li{{margin:0 0 1.1em}} #results .where{{font-size:.85em;color:var(--muted)}} #results mark{{background:rgba(255,200,80,.35);color:inherit}}</style>
<script src="/sitesearch/search.js"></script>
<script>SiteSearch.mount({{input: 'q', status: 'status', results: 'results', sources: [{{ url: '{BASE}search-index.json' }}]}});</script>""")


if __name__ == "__main__":
    main()
