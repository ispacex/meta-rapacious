"""Link preview card (Open Graph image, 1200x630 PNG) of a site of ispacex.github.io/math.

    python3 og_card.py OUT.png LANG "Title" "Subtitle"

Pillow and the macOS system fonts; the cards are committed, so this runs only when a title changes."""
import sys
from PIL import Image, ImageDraw, ImageFont

W, H, PAD = 1200, 630, 80
INK, MUTED, ACC, LINE = "#1f2933", "#52606d", "#2e6db4", "#d9dee5"
HELV = "/System/Library/Fonts/Helvetica.ttc"


def font(size, bold=False):
    return ImageFont.truetype(HELV, size, index=1 if bold else 0)


SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def runs(text):
    """(text, is_subscript) pieces: Helvetica has no subscript digits, so they are drawn small and low."""
    out = []
    for ch in text:
        sub = ch in "₀₁₂₃₄₅₆₇₈₉"
        if out and out[-1][1] == sub:
            out[-1][0] += ch.translate(SUB)
        else:
            out.append([ch.translate(SUB), sub])
    return out


def width(d, text, f):
    return sum(d.textlength(t, font=f.font_variant(size=int(f.size * .62)) if s else f) for t, s in runs(text))


def draw(d, xy, text, f, fill):
    x, y = xy
    for t, s in runs(text):
        g = f.font_variant(size=int(f.size * .62)) if s else f
        d.text((x, y + (f.size * .42 if s else 0)), t, font=g, fill=fill)
        x += d.textlength(t, font=g)


def wrap(d, text, f, width_):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if width(d, t, f) <= width_ or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def card(out, lang, title, sub):
    im = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 16, H], fill=ACC)
    top = "ispacex.github.io · " + ("Математика" if lang == "ru" else "Mathematics")
    d.text((PAD, PAD - 10), top, font=font(30), fill=ACC)
    y = PAD + 80
    for size in (76, 68, 60):
        ft = font(size, bold=True)
        tl = wrap(d, title, ft, W - 2 * PAD)
        if len(tl) <= 2:
            break
    for l in tl:
        draw(d, (PAD, y), l, ft, INK)
        y += int(size * 1.18)
    y += 24
    d.line([PAD, y, PAD + 120, y], fill=LINE, width=4)
    y += 36
    fs = font(36)
    for l in wrap(d, sub, fs, W - 2 * PAD)[:4]:
        draw(d, (PAD, y), l, fs, MUTED)
        y += 50
    im.save(out, optimize=True)


if __name__ == "__main__":
    card(*sys.argv[1:5])
