# -*- coding: utf-8 -*-
"""
Picture of the coloured metalibrary's E^2 page and the rapacious differentials.

    python3 plot_e2.py [data/e2_metalib.csv] [ru|en ...]     -> out/7_e2_rapacious_<lang>[_dark].png/.svg

Top: every class of E^2 over pi_n(S^2) (n >= 4) at height s, coloured by its colour (number of
mu's); d_2 of the rapacious rule (colour +1) as arrows; classes on which the two fillings
("high"/"low", see rapacious.py) disagree are ringed. Bottom: what is left over pi_n, with
Toda's values for n <= 22 and the lecture's statements (pi_44 = 0, pi_71 = (Z/3)^2,
3-torsion for n >= 49).

Each picture is drawn twice: on white, and on the dark background of the site's dark theme
(the file with _dark). The class colours (viridis) are the same in both; only the ink, the grid
and the marks change.
"""
import collections
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import rapacious as R

HERE = pathlib.Path(__file__).resolve().parent
# colours of everything but the classes, per theme; dark = the site's dark theme (--bg, --ink, --muted)
THEMES = {
    "": dict(bg="white", ink="black", muted="#52606D", grid="#EEF0F3", rim="white", sure="#C0392B",
             amb="#E67E22", bar="#5B6B7C", toda="#2E86C1", lect="#8E5B2B", fam="#C0392B", vline="#B8C0CA"),
    "_dark": dict(bg="#14181D", ink="#E6E9EE", muted="#A3ADB9", grid="#262C34", rim="#B8C2CE", sure="#FF6B5B",
                  amb="#F5A35C", bar="#8796A8", toda="#5DADE2", lect="#D9A066", fam="#FF6B5B", vline="#56606C"),
}
T = {
    "ru": {
        "title": "Цветная метабиблиотека: лист E² и «хищная» спектральная последовательность (3-кручение πₙ(S²))",
        "s": "длина слова s (фильтрация Адамса)", "n": "n в πₙ(S²)",
        "colour": "цвет (число μ)", "d2": "хищный d₂ (цвет +1)", "amb": "зависит от порядка заполнения",
        "left": "осталось", "toda": "Тода", "lect": "лекция", "fam": "элемент Тоды / сэндвич",
        "note": "Цвет класса = его Q-вес в нестабильном Ext S³ (sseq, ветка форка ispacex/sseq math-54-qgrade); проверено поклеточно против лямбда-алгебры Иванова–Михайлова–Ву до π₇₅ и выборочно до π₈₅. Тода — таблица 2003 года (до π₈₂).",
        "lastcol": "последний столбец не окончателен: d₂ из πₙ₊₁ не посчитан",
    },
    "en": {
        "title": "Coloured metalibrary: page E² and the rapacious spectral sequence (3-torsion of πₙ(S²))",
        "s": "word length s (Adams filtration)", "n": "n in πₙ(S²)",
        "colour": "colour (number of μ's)", "d2": "rapacious d₂ (colour +1)", "amb": "depends on the filling order",
        "left": "left", "toda": "Toda", "lect": "lecture", "fam": "Toda element / sandwich",
        "note": "Colour of a class = its Q-weight in the unstable Ext of S³ (sseq, fork ispacex/sseq, branch math-54-qgrade); checked cell by cell against the Ivanov–Mikhailov–Wu lambda algebra up to π₇₅ and on samples up to π₈₅. Toda: the 2003 table (up to π₈₂).",
        "lastcol": "the last column is not final: d₂ from πₙ₊₁ is not computed",
    },
}


def main():
    args = [a for a in sys.argv[1:] if not a.endswith(".csv")]
    fn = next((a for a in sys.argv[1:] if a.endswith(".csv")), str(HERE / "data" / "e2_metalib.csv"))
    E2 = R.load_e2(fn)
    import os
    if os.environ.get("PLOT_NMAX"):  # draw only n <= PLOT_NMAX (one more column is read for d_r into it)
        lim = int(os.environ["PLOT_NMAX"])
        E2 = collections.Counter({k: v for k, v in E2.items() if k[0] <= lim + 1})
    nmax = max(n for n, _, _ in E2) - (1 if os.environ.get("PLOT_NMAX") else 0)
    import toda2003
    toda = toda2003.by_n()
    Eh, left_h, diffs_h = R.run(E2, +1, "high", nmax)
    El, left_l, diffs_l = R.run(E2, +1, "low", nmax)
    amb_nodes = {k for k in set(Eh) | set(El) if Eh.get(k, 0) != El.get(k, 0)}
    maxc = max(c for _, _, c in E2)
    cmap = plt.get_cmap("viridis", maxc + 1)
    for lang, theme in [(l, th) for l in (args or ["ru", "en"]) for th in THEMES]:
        t, C = T[lang], THEMES[theme]
        plt.rcdefaults()  # the light picture keeps matplotlib's black ink, as published before
        if theme:
            plt.rcParams.update({"text.color": C["ink"], "axes.labelcolor": C["ink"], "axes.edgecolor": C["muted"],
                                 "xtick.color": C["ink"], "ytick.color": C["ink"], "axes.facecolor": C["bg"],
                                 "figure.facecolor": C["bg"], "hatch.color": C["amb"]})
        fig, (ax, bx) = plt.subplots(2, 1, figsize=(19, 10.5), gridspec_kw={"height_ratios": [3.2, 1], "hspace": 0.12},
                                     sharex=True)
        # classes: several in one (n, s) are spread horizontally
        cell = collections.defaultdict(list)
        for (n, s, c), v in sorted(E2.items()):
            cell[(n, s)] += [c] * v
        pos = {}
        for (n, s), cs in cell.items():
            k = len(cs)
            for i, c in enumerate(cs):
                x = n + (i - (k - 1) / 2) * 0.22
                pos.setdefault((n, s, c), []).append(x)
                if n <= nmax:
                    ax.scatter([x], [s], s=46, color=cmap(c), edgecolor=C["rim"], linewidth=0.5, zorder=3)
        both = {(d["from"], d["to"]) for d in diffs_h} & {(d["from"], d["to"]) for d in diffs_l}
        for d in diffs_h + [x for x in diffs_l if (x["from"], x["to"]) not in {(y["from"], y["to"]) for y in diffs_h}]:
            a, b = d["from"], d["to"]
            if a[0] > nmax:
                continue
            xa, xb = pos[a][0], pos[b][0]
            sure = (a, b) in both
            ax.annotate("", (xb, b[1]), (xa, a[1]), arrowprops=dict(arrowstyle="->", color=C["sure"] if sure else C["amb"],
                                                                   lw=1.1 if sure else 1.0, ls="-" if sure else (0, (2, 1.5))))
        for k in amb_nodes:
            if k in pos:
                ax.scatter(pos[k][:1], [k[1]], s=150, facecolor="none", edgecolor=C["amb"], lw=1.4, zorder=2)
        ax.set_ylabel(t["s"])
        ax.set_ylim(0, max(s for _, s, _ in E2) + 1)
        ax.grid(axis="x", color=C["grid"], lw=0.6)
        ax.set_title(t["title"], fontsize=14)
        rim = dict(mec=C["rim"], mew=0.5) if theme else {}  # dark: the legend's dots get the rim of the plot's
        handles = [Line2D([], [], marker="o", ls="", color=cmap(c), label=str(c), **rim) for c in range(maxc + 1)]
        leg1 = ax.legend(handles=handles, title=t["colour"], ncol=min(maxc + 1, 16), loc="upper left", fontsize=8,
                         title_fontsize=9, frameon=False)
        ax.add_artist(leg1)
        ax.legend(handles=[Line2D([], [], color=C["sure"], label=t["d2"]),
                           Line2D([], [], color=C["amb"], ls="--", marker="o", mfc="none", label=t["amb"])],
                  loc="upper left", bbox_to_anchor=(0, 0.86), frameon=False, fontsize=9)
        for s_ in ("right", "top"):
            ax.spines[s_].set_visible(False)
        # bottom: survivors
        ns = list(range(4, nmax + 1))
        lo = [min(left_h[n], left_l[n]) for n in ns]
        hi = [max(left_h[n], left_l[n]) for n in ns]
        bx.bar(ns, lo, color=C["bar"], width=0.7, label=t["left"])
        bx.bar(ns, [h - l for h, l in zip(hi, lo)], bottom=lo, color="none", edgecolor=C["amb"], hatch="///",
               width=0.7, label=t["amb"])
        for n in ns:
            if n in toda:
                bx.scatter([n], [toda[n] + 0.35], marker="v", color=C["toda"], s=26, zorder=3)
            if (n % 4 == 2 and n >= 6) or (n % 4 == 1 and n >= 9):
                bx.scatter([n], [-0.35], marker="^", color=C["fam"], s=18, zorder=3)
        for n, v in ((44, 0), (71, 2)):
            if n <= nmax:
                bx.scatter([n], [v + 0.35], marker="*", color=C["lect"], s=90, zorder=4)
        if nmax >= 49:
            bx.axvspan(48.5, nmax + 0.5, ymin=0, ymax=0.06, color=C["lect"], alpha=0.25, lw=0)
        bx.axvline(nmax - 0.5, color=C["vline"], lw=0.8, ls=":")
        bx.text(nmax - 0.6, max(hi) + 0.6, t["lastcol"], ha="right", fontsize=8, color=C["muted"])
        bx.set_ylim(-0.8, max(hi) + 1.4)
        bx.set_xlim(3.5, nmax + 0.5)
        bx.set_xticks(range(4, nmax + 1, 2))
        bx.set_xlabel(t["n"])
        bx.legend(handles=[Line2D([], [], marker="s", ls="", color=C["bar"], label=t["left"]),
                           Line2D([], [], marker="s", ls="", mfc="none", mec=C["amb"], label=t["amb"]),
                           Line2D([], [], marker="v", ls="", color=C["toda"], label=t["toda"]),
                           Line2D([], [], marker="*", ls="", color=C["lect"], label=t["lect"] + " (π₄₄ = 0, π₇₁ = 2; ≥ 49: ≠ 0)"),
                           Line2D([], [], marker="^", ls="", color=C["fam"], label=t["fam"])],
                  loc="upper left", ncol=5, frameon=False, fontsize=8.5)
        for s_ in ("right", "top"):
            bx.spines[s_].set_visible(False)
        fig.text(0.5, 0.01, t["note"], ha="center", fontsize=8.5, color=C["muted"])
        out = HERE / "out"
        out.mkdir(exist_ok=True)
        for ext in ("png", "svg"):
            fig.savefig(out / f"7_e2_rapacious_{lang}{theme}.{ext}", dpi=140, bbox_inches="tight", facecolor=C["bg"])
        plt.close(fig)
        print("wrote", out / f"7_e2_rapacious_{lang}{theme}.png")


if __name__ == "__main__":
    main()
