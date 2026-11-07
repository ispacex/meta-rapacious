# -*- coding: utf-8 -*-
"""
The pages of Toda's 2003 tables (MATH-442): toda2003.html (all columns of sections 5.6 and 6.5,
our checks, the discrepancies) and toda2003_s5.html (section 5 of the paper, transcribed).
Called from build_site.py; the transcriptions are metalibrary/toda03/*.txt and s5/*.html, read
with metalibrary/toda2003.py; the checks are metalibrary/toda03/check.py.
"""
import html
import re

import toda2003 as T

SYM = {"*": "●", "o": "○", ">": "▷", "(*)": "(●)"}
CON = {"=": "=", "->": "→", "<~": "↩"}


def chain_table(rows, nmax, cls="ch", stable_head=None):
    """A transcription drawn as in the source: one row of the table per printed row (labels above
    and below as rows of their own), odd columns the spheres, even ones the E^2 between them."""
    cols = list(range(2, nmax + 2))
    head = "".join(f"<th>{c}</th>" if c % 2 else "<th></th>" for c in cols)
    head = f"<tr><th class=l>$k$ \\ $n$</th>{head}<th class=l>{stable_head or ''}</th><th></th></tr>"
    body, prev_k = [], None
    for r in rows:
        cells = {c: "" for c in cols}
        tail, note = "", ""
        if r["kind"] == "m":
            for ch in r["chains"]:
                for c, kind, tok in ch["items"]:
                    cells[c] = (f'<span class=s>{SYM[tok]}</span>' if kind == "sym" else CON[tok])
                if ch["tail"] is not None:
                    tail = f"$=\\langle {ch['tail']}\\rangle$"
            cl = "m"
        elif r["kind"] in ("u", "l"):
            for c, t, arrow in r["labels"]:
                lab = f"${t}$"
                cells[c] = (f'{lab}<span class=ar>↖</span>' if r["kind"] == "u" else f'<span class=ar>↖</span>{lab}') if arrow else lab
            cl = r["kind"]
        else:
            note = f"${r['note']}$"
            cl = "r"
        first = r["k"] != prev_k
        kcell = f"$k={r['k']}$" if first else ""
        prev_k = r["k"]
        tds = "".join(f'<td class="{"o" if c % 2 else "e"}">{v}</td>' for c, v in cells.items())
        body.append(f'<tr class="{cl}{" first" if first else ""}"><td class=l>{kcell}</td>{tds}<td class=l>{tail}</td><td class=l>{note}</td></tr>')
    cw = "".join('<col class="o">' if c % 2 else '<col class="e">' for c in cols)
    width = 4.5 + sum(2.0 if c % 2 else 1.6 for c in cols) + 10 + 12
    colg = f'<colgroup><col class="k">{cw}<col class="t"><col class="n"></colgroup>'
    return (f'<div class="tw"><table class="{cls}" style="width:{width:.1f}em">{colg}<thead>{head}</thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def gname(orders):
    """[9, 3, 3] -> '9·3²' (Z/9 + (Z/3)^2); [] -> ''."""
    if not orders:
        return ""
    out = []
    for o in sorted(set(orders), reverse=True):
        e = orders.count(o)
        out.append(f"{o}" + ("" if e == 1 else {2: "²", 3: "³", 4: "⁴", 5: "⁵"}[e]))
    return "·".join(out)


def grid(g, st, ks, nmax, flag=None):
    """k rows, odd n columns, the group in each cell; the last column the stable group."""
    head = "".join(f"<th>{n}</th>" for n in range(3, nmax + 1, 2))
    body = []
    for k in ks:
        tds = []
        for n in range(3, nmax + 1, 2):
            v = gname(g.get((k, n), []))
            c = ' class="bad"' if flag and (k, n) in flag else ""
            tds.append(f"<td{c}>{v}</td>")
        stab = gname(sorted(o for o, _ in st.get(k, [])))
        body.append(f"<tr><th>{k}</th>{''.join(tds)}<td>{stab}</td></tr>")
    return (f'<div class="tw"><table class="gr"><thead><tr><th>$k$ \\ $n$</th>{head}<th>stable</th></tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def s5_body():
    """Section 5 of the paper: the transcribed pages, with the diagrams drawn from their files."""
    parts = []
    files = sorted((T.DIR / "s5").glob("p*.html"), key=lambda p: int(re.match(r"p(\d+)", p.name).group(1)))
    for f in files:
        s = f.read_text(encoding="utf-8")
        s = re.sub(r"<!--diagram:(\w+)-->", lambda m: chain_table(T.load(f"s5/{m.group(1)}.txt"), 23, "ch dg"), s)
        parts.append(s)
    parts.append("""<h3 id="s5.6">5.6 Table of 3-primary $k$-stem Groups for $k\\le55$</h3>
<p class="pg">[pp. 60–61]</p>
<p>Summerizing the results, we have the following table of ${}_3\\pi_{n+k}(S^n)$ for odd $n$ and $k\\le55$.</p>""")
    parts.append(chain_table(T.load("t56.txt"), T.T56_NMAX))
    return "\n".join(parts)


def write_csv(path):
    """data/toda2003_groups.csv: every cell of both tables."""
    import csv
    g56, _ = T.table56()
    g65, _ = T.table65()
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["section", "k", "n", "group", "log3_order", "mod_A"])
        for sec, g, ks, nmax, moda in (("5.6", g56, range(1, 56), T.T56_NMAX, 0), ("6.5", g65, range(56, 80), T.T65_NMAX, 1)):
            for k in ks:
                for n in range(3, nmax + 1, 2):
                    o = g.get((k, n), [])
                    w.writerow([sec, k, n, ".".join(map(str, sorted(o, reverse=True))) or "0", T.log3(o), moda])


CHECK_NAMES = {
    "A": ("Столбец $S^3$: новое прочтение против прежнего (выверенного 15.10.2026)",
          "The $S^3$ column: the new reading against the earlier one (checked on 15.10.2026)"),
    "B": ("Стабильная область ($k\\le2n-1$) и столбец «стабильно»: стабильные стемы — im $J$ и таблица A3.2 Равенеля",
          "The stable range ($k\\le2n-1$) and the column “stable”: the stable stems, im $J$ and Ravenel's Table A3.2"),
    "C": ("Тода 1962 (таблица A3.4 Равенеля), $n\\le21$, $k\\le19$: 3-часть, слагаемое за слагаемым",
          "Toda 1962 (Ravenel's Table A3.4), $n\\le21$, $k\\le19$: the 3-part, summand by summand"),
    "D": ("Нестабильный $E_2$ Адамса (sseq/ext и $H(\\Lambda(m))$)",
          "The unstable Adams $E_2$ (sseq/ext and $H(\\Lambda(m))$)"),
    "E": ("Тода против Тоды: диаграммы §5.2–5.5 (mod A) против таблицы §5.6; сферы рождения $u(\\cdot)$ из (5.4.2)–(5.4.3)",
          "Toda against Toda: the diagrams of §5.2–5.5 (mod A) against the table of §5.6; the spheres of origin $u(\\cdot)$ of (5.4.2)–(5.4.3)"),
}


def checks_html(lang, res, e2_info):
    t = (lambda ru, en: ru if lang == "ru" else en)
    rows = []
    for c, v in res.items():
        name = CHECK_NAMES[c][0 if lang == "ru" else 1]
        if c == "D":
            name += " " + e2_info
        probs = "<br>".join(html.escape(p) for p in v["problems"]) or t("расхождений нет", "no disagreement")
        cl = "bad" if v["problems"] else "ok"
        if not v["checked"]:
            probs, cl = t("не запускалась", "not run"), "amb"
        rows.append(f"<tr><td>{c}</td><td class=l>{name}</td><td>{v['checked']}</td><td class='l {cl}'>{probs}</td></tr>")
    head = t("<tr><th></th><th class=l>Проверка</th><th>клеток</th><th class=l>Результат</th></tr>",
             "<tr><th></th><th class=l>Check</th><th>cells</th><th class=l>Result</th></tr>")
    return f'<div class="tw"><table><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'


DISCREPANCIES = []  # filled in by build_site from DISC (below) and the checks


def toda_more(lang, res, e2_info, disc):
    """The part of toda2003.html after the S^3 column: all columns, checks, discrepancies."""
    t = (lambda ru, en: ru if lang == "ru" else en)
    g56, st56 = T.table56()
    g65, st65 = T.table65()
    legend = t("""<p>Обозначения Тоды (§5.2): $\\bullet\\cong\\mathbf Z/3$, $\\circ\\cong\\mathbf Z/9$, $\\triangleright\\cong\\mathbf Z/27$;
между соседними сферами — двойная надстройка $E^2$: «$=$» — биекция, «$\\to$» — нетривиальна и не биекция ($\\bullet\\to\\circ$, $\\circ\\to\\triangleright$ мономорфны,
$\\circ\\to\\bullet$, $\\triangleright\\to\\circ$ эпиморфны, $\\circ\\to\\circ$, $\\triangleright\\to\\triangleright$ — умножение на $p$); «$=\\langle x\\rangle$» — дальше та же группа до стабильной, $x$ — стабильная образующая.
Строка, которая кончается без «$=\\langle\\cdot\\rangle$», на следующей сфере уходит в ноль. Слагаемые, стоящие друг под другом, — отдельные слагаемые.</p>""",
              """<p>Toda's notation (§5.2): $\\bullet\\cong\\mathbf Z/3$, $\\circ\\cong\\mathbf Z/9$, $\\triangleright\\cong\\mathbf Z/27$;
between neighbouring spheres the double suspension $E^2$: “$=$” is a bijection, “$\\to$” is non-trivial and not a bijection ($\\bullet\\to\\circ$, $\\circ\\to\\triangleright$ injective,
$\\circ\\to\\bullet$, $\\triangleright\\to\\circ$ surjective, $\\circ\\to\\circ$, $\\triangleright\\to\\triangleright$ multiplication by $p$); “$=\\langle x\\rangle$”: the same group from there on up to the stable one, $x$ the stable generator.
A row that ends without “$=\\langle\\cdot\\rangle$” goes to zero on the next sphere. Summands written under each other are separate summands.</p>""")
    how = t(f"""<div class="box"><p><b>Как читали.</b> Каждую строку обеих таблиц переписали по картинкам страниц (400–600 dpi), OCR не используется:
он путает $\\bullet$ и $\\circ$ и теряет столбцы. Прочтение лежит в репозитории как текст, по строке на печатную строку
(<a href="https://github.com/ispacex/meta-rapacious/tree/main/metalibrary/toda03">metalibrary/toda03</a>, формат — в <code>toda2003.py</code>), группы в клетках выводятся из него программой.
Таблица §5.6 — целые группы (с α-семействами), таблица §6.5 — по модулю нестабильных α-семейств (mod A); в столбце $S^3$ выше мы вернули $A$, в остальных столбцах §6.5 — нет:
для них это не сделано, и сетка §6.5 ниже — mod A, как у Тоды.</p>
<p>Текст §5 целиком (с диаграммами и самой таблицей §5.6 в записи Тоды) — на отдельной странице: <a href="toda2003_s5.html">§5 статьи</a>.</p></div>""",
            f"""<div class="box"><p><b>How we read.</b> Every row of both tables was copied from the page images (400–600 dpi); OCR is not used:
it confuses $\\bullet$ with $\\circ$ and loses columns. The reading is kept in the repository as text, a line per printed row
(<a href="https://github.com/ispacex/meta-rapacious/tree/main/metalibrary/toda03">metalibrary/toda03</a>, the format is in <code>toda2003.py</code>), and the groups in the cells are derived from it by the program.
The table of §5.6 gives whole groups (alpha families included), the table of §6.5 gives them modulo the unstable alpha families (mod A); in the $S^3$ column above we added $A$ back, in the other columns of §6.5 we did not:
that has not been done for them, and the grid of §6.5 below is mod A, as in Toda.</p>
<p>The whole text of §5 (with the diagrams and the table of §5.6 in Toda's notation) is on a page of its own: <a href="toda2003_s5.html">§5 of the paper</a>.</p></div>""")
    gnote = t("<p class=muted>В клетке — группа: $9\\cdot3^2$ значит $\\mathbf Z/9\\oplus(\\mathbf Z/3)^2$, пусто — ноль. Последний столбец — стабильная группа.</p>",
              "<p class=muted>A cell holds the group: $9\\cdot3^2$ means $\\mathbf Z/9\\oplus(\\mathbf Z/3)^2$, empty means zero. The last column is the stable group.</p>")
    flag = set()
    for p in res["E"]["problems"] + res["D"]["problems"]:
        m = re.match(r"k=(\d+) n=(\d+)", p)
        if m:
            flag.add((int(m.group(1)), int(m.group(2))))
    s = t("<h2 id=all>Все столбцы</h2>", "<h2 id=all>All columns</h2>") + how + legend
    s += t("<h3>§5.6: ${}_3\\pi_{n+k}(S^n)$, $k\\le55$, целые группы</h3>", "<h3>§5.6: ${}_3\\pi_{n+k}(S^n)$, $k\\le55$, whole groups</h3>")
    s += t("<p>PDF, страницы 67–68 (печатные 60–61). Строк нет для $k=1,2,4,5,8,9,12,25$: там групп нет.</p>",
           "<p>PDF pages 67–68 (printed 60–61). There are no rows for $k=1,2,4,5,8,9,12,25$: the groups are zero there.</p>")
    s += gnote + grid(g56, st56, range(1, 56), T.T56_NMAX, flag)
    s += t("<h3>§6.5: ${}_3\\pi_{n+k}(S^n)$ mod A, $56\\le k\\le79$</h3>", "<h3>§6.5: ${}_3\\pi_{n+k}(S^n)$ mod A, $56\\le k\\le79$</h3>")
    s += t("<p>PDF, страницы 80–81 (печатные 73–74). Тода: «результаты для $k=76$ и $k=77$ ещё не окончательны, мы показываем пример; варианты — в предложении 6.3».</p>",
           "<p>PDF pages 80–81 (printed 73–74). Toda: “The results for $k=76$ and $k=77$ are not yet fixed and we show an example. The variations are seen in Proposition 6.3.”</p>")
    s += gnote + grid(g65, st65, range(56, 80), T.T65_NMAX)
    s += t("<p>Сама таблица §6.5 в записи Тоды:</p>", "<p>The table of §6.5 itself, in Toda's notation:</p>")
    s += chain_table(T.load("t65.txt"), T.T65_NMAX, stable_head="stable")
    s += t("<h2 id=checks>Проверки</h2>", "<h2 id=checks>Checks</h2>")
    s += t("""<p>Каждая проверка идёт по всем клеткам, к которым применима (<code>metalibrary/toda03/check.py</code>).
Проверки B–D независимы от Тоды 2003; E сверяет два места самой статьи, переписанные отдельно (диаграммы §5.2–5.5 и таблицу §5.6), так что ловит и наши ошибки прочтения.</p>""",
           """<p>Every check runs over every cell it applies to (<code>metalibrary/toda03/check.py</code>).
Checks B–D are independent of Toda 2003; E compares two places of the paper itself, copied separately (the diagrams of §5.2–5.5 and the table of §5.6), so it also catches our misreadings.</p>""")
    s += checks_html(lang, res, e2_info)
    s += t("<h2 id=disc>Расхождения</h2>", "<h2 id=disc>Discrepancies</h2>")
    s += "<ol>" + "".join(f"<li>{d[0 if lang == 'ru' else 1]}</li>" for d in disc) + "</ol>"
    s += t('<p><a href="data/toda2003_groups.csv">toda2003_groups.csv</a> — все клетки обеих таблиц (столбцы: раздел, $k$, $n$, группа, $\\log_3$ порядка, mod A).</p>',
           '<p><a href="data/toda2003_groups.csv">toda2003_groups.csv</a>: every cell of both tables (columns: section, $k$, $n$, group, $\\log_3$ of the order, mod A).</p>')
    return s


def s5_page(lang):
    t = (lambda ru, en: ru if lang == "ru" else en)
    intro = t("""<div class="box"><p>H. Toda, <i>Unstable 3-primary Homotopy Groups of Spheres</i>, Econoinformatics <b>29</b> (2003), §5 «Old Table of 3-primary Groups»,
печатные страницы 42–61 (PDF 49–68 скана <a href="https://www.sas.rochester.edu/mth/sites/doug-ravenel/otherpapers/Toda03-ocr.pdf">Toda03-ocr.pdf</a>).
Переписано по картинкам страниц, текст английский, как в оригинале; номера страниц — в квадратных скобках.
Опечатки оригинала сохранены и помечены [sic]. В скане страница с текстом «(3) Let $\\xi=\\alpha_1(7)\\circ\\varphi(10)$ …» напечатана дважды (два оттиска с номерами 58 и 59, PDF 65 и 66; математика одна и та же); дана один раз, по PDF 65.</p>
<p>Диаграммы — в записи Тоды: столбцы — нечётные сферы $S^n$, между ними — $E^2$; над строкой — образы $H$ (стрелка $\\nwarrow$ от точки), под строкой — прообразы $P$ (стрелка $\\nwarrow$ к точке); где Тода стрелки опускает, их нет и здесь. Обозначения — в §5.2 ниже и на странице <a href="toda2003.html">таблицы</a>.</p></div>""",
              """<div class="box"><p>H. Toda, <i>Unstable 3-primary Homotopy Groups of Spheres</i>, Econoinformatics <b>29</b> (2003), §5 “Old Table of 3-primary Groups”,
printed pages 42–61 (PDF 49–68 of the scan <a href="https://www.sas.rochester.edu/mth/sites/doug-ravenel/otherpapers/Toda03-ocr.pdf">Toda03-ocr.pdf</a>).
Copied from the page images; page numbers in square brackets.
Misprints of the original are kept and marked [sic]. In the scan the page with the text “(3) Let $\\xi=\\alpha_1(7)\\circ\\varphi(10)$ …” is printed twice (two printings numbered 58 and 59, PDF 65 and 66, with the same mathematics); it is given once, after PDF 65.</p>
<p>The diagrams are in Toda's notation: the columns are the odd spheres $S^n$, with $E^2$ between them; above a row the images under $H$ (the arrow $\\nwarrow$ from the dot), below it the preimages under $P$ (the arrow $\\nwarrow$ to the dot); where Toda leaves the arrows out, they are left out here too. The notation is in §5.2 below and on the page of the <a href="toda2003.html">table</a>.</p></div>""")
    return intro + s5_body()


CSS = """
table.gr { width:auto; font-size:.85rem; }
table.ch { table-layout:fixed; font-size:.85rem; }
table.ch col.k { width:4.5em; } table.ch col.o { width:2em; } table.ch col.e { width:1.6em; }
table.ch col.t { width:10em; } table.ch col.n { width:12em; }
table.ch td, table.ch th { border:0; padding:0; white-space:nowrap; vertical-align:middle; overflow:visible; }
table.ch td.e { color:var(--muted); } table.ch .s { font-size:.9em; line-height:1; }
table.ch tr.first td { padding-top:.45rem; } table.ch tr.u td, table.ch tr.l td { font-size:.8rem; }
table.ch .ar { color:var(--muted); font-size:.8em; }
table.gr td, table.gr th { padding:.1rem .3rem; white-space:nowrap; }
table.tr td { border:0; text-align:left; padding:.05rem .5rem; }
p.pg { color:var(--muted); font-size:.85rem; margin:1.2rem 0 .2rem; }
.sic { color:var(--badink); font-size:.8em; margin-left:.2em; }
p.c { text-align:center; }
"""
