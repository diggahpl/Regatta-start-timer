#!/usr/bin/env python3
"""Generates every drawing of the repository (SVG, standard library only).

    python3 tools/generate_diagrams.py              # docs/images/*.svg, hardware/*.svg
    python3 tools/generate_diagrams.py --social DIR # four 1200x627 social SVGs in DIR/src

The output is deterministic, so the drawings can be regenerated and diffed.
All coordinates are plain numbers on purpose: every figure is one function.
"""
import argparse
import html
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- palette and fonts -------------------------------------------------------
NAVY = "#0b1f3a"
INK = "#14263f"
MUTE = "#5b6b82"
LINE = "#c9d3e0"
PAPER = "#f6f8fb"
WHITE = "#ffffff"
SEA = "#1f6fb2"
AMBER = "#ffb020"
ORANGE = "#f2711c"
RED = "#d93c3c"
GREEN = "#1e9e5a"
YELLOW = "#f2c200"
TEAL = "#0d6f7a"
TEAL_DARK = "#09525a"
FONT = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', Menlo, Consolas, monospace"

# wire colour code shared by the schematic and the soldering diagram
W_CLK, W_DIO, W_START, W_RELAY, W_5V, W_GND = "#d9a900", "#2e9d57", "#2b6fd6", ORANGE, "#d93c3c", "#1c2430"


# --- svg helpers -------------------------------------------------------------
def esc(s):
    return html.escape(str(s), quote=False)


def el(tag, body=None, **kw):
    a = "".join(' %s="%s"' % (k.rstrip("_").replace("_", "-"), v) for k, v in kw.items() if v is not None)
    return "<%s%s/>" % (tag, a) if body is None else "<%s%s>%s</%s>" % (tag, a, body, tag)


def rect(x, y, w, h, fill="none", stroke=None, sw=1, rx=0, dash=None, opacity=None):
    return el("rect", x=x, y=y, width=w, height=h, rx=rx or None, fill=fill, stroke=stroke,
              stroke_width=sw if stroke else None, stroke_dasharray=dash, opacity=opacity)


def line(x1, y1, x2, y2, stroke=INK, sw=2, dash=None, cap="round", opacity=None):
    return el("line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, stroke_width=sw,
              stroke_dasharray=dash, stroke_linecap=cap, opacity=opacity)


def circle(cx, cy, r, fill="none", stroke=None, sw=1):
    return el("circle", cx=cx, cy=cy, r=r, fill=fill, stroke=stroke, stroke_width=sw if stroke else None)


def poly(points, stroke=INK, sw=2, fill="none", dash=None, close=False):
    tag = "polygon" if close else "polyline"
    pts = " ".join("%s,%s" % (x, y) for x, y in points)
    return el(tag, points=pts, fill=fill, stroke=stroke, stroke_width=sw if stroke else None,
              stroke_linejoin="round", stroke_linecap="round", stroke_dasharray=dash)


def path(d, fill="none", stroke=None, sw=1, dash=None, opacity=None, extra=None):
    kw = dict(d=d, fill=fill, stroke=stroke, stroke_width=sw if stroke else None, stroke_dasharray=dash,
              stroke_linejoin="round", stroke_linecap="round", opacity=opacity)
    if extra:
        kw.update(extra)
    return el("path", **kw)


def text(x, y, s, size=14, weight=400, fill=INK, anchor="start", family=FONT, ls=None, transform=None, halo=None):
    """halo = colour of an outline drawn under the glyphs, keeps text readable over guide lines."""
    return el("text", esc(s), x=x, y=y, font_family=family, font_size=size, font_weight=weight, fill=fill,
              text_anchor=anchor if anchor != "start" else None, letter_spacing=ls, transform=transform,
              stroke=halo, stroke_width=5 if halo else None, paint_order="stroke" if halo else None,
              stroke_linejoin="round" if halo else None)


def group(body, transform=None, **kw):
    return el("g", body, transform=transform, **kw)


def svg_doc(w, h, inner, title, desc):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-labelledby="t d">\n<title id="t">%s</title>\n<desc id="d">%s</desc>\n%s\n</svg>\n'
            % (w, h, w, h, esc(title), esc(desc), inner))


def card(w, h, fill=WHITE, stroke=LINE, rx=16):
    return rect(0.5, 0.5, w - 1, h - 1, fill=fill, stroke=stroke, sw=1, rx=rx)


# --- seven-segment display ---------------------------------------------------
SEGS = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg",
        "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def seg_digit(x, y, w, h, t, ch, on, off):
    v = h / 2 - 1.7 * t
    r = {
        "a": (x + 1.1 * t, y, w - 2.2 * t, t),
        "g": (x + 1.1 * t, y + h / 2 - t / 2, w - 2.2 * t, t),
        "d": (x + 1.1 * t, y + h - t, w - 2.2 * t, t),
        "f": (x, y + 1.1 * t, t, v),
        "b": (x + w - t, y + 1.1 * t, t, v),
        "e": (x, y + h / 2 + 0.6 * t, t, v),
        "c": (x + w - t, y + h / 2 + 0.6 * t, t, v),
    }
    out = []
    for name, (sx, sy, sw_, sh) in r.items():
        out.append(rect(round(sx, 1), round(sy, 1), round(sw_, 1), round(sh, 1),
                        fill=on if name in SEGS[ch] else off, rx=round(t / 2.2, 1)))
    return "".join(out)


def clock_display(x, y, w, h, t, gap, colon_w, digits, on, off):
    """Draws 'MM:SS' with four digits; returns the svg and the total width."""
    out, cx = [], x
    for i, ch in enumerate(digits):
        out.append(seg_digit(cx, y, w, h, t, ch, on, off))
        cx += w + gap
        if i == 1:
            mid = cx - gap / 2 + colon_w / 2 - gap / 2
            out.append(circle(round(mid, 1), round(y + h * 0.34, 1), round(t * 0.55, 1), fill=on))
            out.append(circle(round(mid, 1), round(y + h * 0.68, 1), round(t * 0.55, 1), fill=on))
            cx += colon_w
    return "".join(out), cx - gap - x


GLOW_DEFS = ('<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
             '<feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/>'
             '<feMergeNode in="SourceGraphic"/></feMerge></filter>')


def chip(x, y, label, size=14):
    w = int(len(label) * size * 0.58 + 30)
    return (rect(x, y, w, 34, stroke="#6f9bc8", sw=1.5, rx=17, fill="rgba(255,255,255,0.06)")
            + text(x + w / 2, y + 22, label, size=size, weight=600, fill="#dbe8f6", anchor="middle")), w


# --- banner ------------------------------------------------------------------
def banner_body(w=1280, h=360, compact=False):
    """Hero artwork used for the README banner (1280x360) and the social hero."""
    defs = ('<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#0a1f3d"/><stop offset="1" stop-color="#14507f"/></linearGradient>'
            + GLOW_DEFS + "</defs>")
    o = [defs, rect(0, 0, w, h, fill="url(#bg)", rx=18)]
    for i, (op, dy) in enumerate(((0.10, 0), (0.07, 18), (0.05, 36))):
        base = h - 62 + dy
        d = ("M0 %d C %d %d, %d %d, %d %d S %d %d, %d %d S %d %d, %d %d"
             % (base, w * .12, base - 30, w * .25, base + 30, w * .375, base,
                w * .625, base - 30, w * .75, base, w * .875, base + 30, w, base))
        o.append(path(d, stroke="#ffffff", sw=2, opacity=op))
    tx = 72
    o.append(text(tx, 108, "ARDUINO · TM1637 · RELAY", size=16, weight=700, fill=AMBER, ls=3))
    o.append(text(tx, 184, "Regatta Start Timer", size=60, weight=800, fill=WHITE))
    o.append(text(tx, 226, "Five-minute start sequence with horn control.", size=22, fill="#cfe0f3"))
    o.append(text(tx, 256, "One button, one display, one relay.", size=22, fill="#cfe0f3"))
    cx = tx
    for label in ("Arduino Nano / Uno", "RRS 26 timing", "CC BY-NC 4.0"):
        c, cw = chip(cx, 286, label)
        o.append(c)
        cx += cw + 12
    # display panel
    px, py, pw, ph = 820, 56, 392, 214
    o.append(rect(px, py, pw, ph, fill="#05080d", stroke="#26405f", sw=2, rx=22))
    o.append(rect(px + 16, py + 16, pw - 32, ph - 32, fill="#070d14", stroke="#12202f", sw=1.5, rx=14))
    dg, total = clock_display(0, 0, 62, 118, 12, 14, 30, "0500", AMBER, "#0e0a03")
    dx = px + (pw - total) / 2
    dy = py + (ph - 118) / 2
    o.append(group(el("g", dg, filter="url(#glow)"), transform="translate(%.1f %.1f)" % (dx, dy)))
    o.append(circle(px + 90, 316, 20, fill=RED, stroke="#ffffff", sw=2))
    o.append(text(px + 124, 322, "START", size=14, weight=700, fill="#cfe0f3", ls=1.5))
    for i, bw in enumerate((6, 6, 6, 14)):
        o.append(rect(1090 + i * 24, 296, bw, 28, fill=AMBER, rx=2))
    o.append(text(1090, 344, "HORN", size=12, weight=700, fill="#cfe0f3", ls=2))
    return "".join(o)


def banner():
    return 1280, 360, banner_body(), "Regatta Start Timer banner", (
        "Banner with the project name, the tagline and a seven-segment display showing 05:00.")


# --- timeline ----------------------------------------------------------------
def timeline():
    w, h = 1280, 490
    x0, x1 = 230, 1230

    def X(t):
        return x0 + (x1 - x0) * t / 300.0

    o = [card(w, h)]
    o.append(text(40, 54, "Start sequence over time", size=26, weight=800))
    o.append(text(40, 80, "Default timing from the accepted press of START. Pulses are drawn wider than scale so they stay visible.",
                  size=14, fill=MUTE))
    # row labels
    for y, label in ((128, "Display"), (222, "Horn relay"), (322, "Flags"), (418, "LED D13")):
        o.append(text(40, y, label, size=15, weight=700))
    # axis with display values
    o.append(line(x0, 150, x1, 150, stroke=INK, sw=2))
    for t, label in ((0, "05:00"), (60, "04:00"), (120, "03:00"), (180, "02:00"), (240, "01:00"), (300, "00:00")):
        o.append(line(X(t), 144, X(t), 156, stroke=INK, sw=2))
        o.append(text(X(t), 130, label, size=17, weight=700, anchor="middle", family=MONO))
    # guides
    for t in (0, 60, 240, 300):
        o.append(line(X(t), 160, X(t), 446, stroke="#9fb0c6", sw=1.5, dash="2 5"))
    # horn pulses
    o.append(line(x0, 246, x1 + 20, 246, stroke=LINE, sw=2))
    for t, dur, name, secs in ((0, 1, "warning", "1 s"), (60, 1, "preparatory", "1 s"),
                               (240, 1, "one minute", "1 s"), (300, 2, "start", "2 s")):
        pw = 9 * dur
        o.append(rect(X(t), 196, pw, 50, fill=AMBER, rx=2))
        o.append(text(X(t) + pw / 2, 172, name, size=14, weight=700, anchor="middle", halo=WHITE))
        o.append(text(X(t) + pw / 2, 188, secs, size=12, fill=MUTE, anchor="middle", halo=WHITE))
    # flags
    o.append(rect(X(0), 296, X(300) - X(0), 22, fill=SEA, rx=4))
    o.append(text(X(0) + 12, 312, "class flag up", size=13, weight=600, fill=WHITE))
    o.append(rect(X(60), 326, X(240) - X(60), 22, fill=ORANGE, rx=4))
    o.append(text(X(60) + 12, 342, "preparatory flag (P, I, Z, U or black) up", size=13, weight=600, fill=WHITE))
    o.append(text(X(300) + 8, 312, "down", size=12, fill=MUTE))
    o.append(text(X(240) + 8, 342, "down", size=12, fill=MUTE))
    # LED
    o.append(line(x0, 414, x1, 414, stroke=SEA, sw=9, dash="6 6", cap="butt"))
    o.append(line(x1, 414, x1 + 34, 414, stroke=SEA, sw=9, cap="butt"))
    o.append(text(X(150), 440, "blinks 500 ms on, 500 ms off (not to scale)", size=13, fill=MUTE, anchor="middle", halo=WHITE))
    o.append(text(x1 + 17, 440, "steady", size=13, fill=MUTE, anchor="middle", halo=WHITE))
    o.append(text(40, 470, "t = 0 when the release of START is accepted (50 ms debounce). Default pulse lengths 1 s, 1 s, 1 s, 2 s; configurable in Config.h.",
                  size=13, fill=MUTE))
    return w, h, "".join(o), "Start sequence timeline", (
        "Timeline from 05:00 to 00:00 with the four horn pulses, the class and preparatory flags and the LED state.")


# --- flags -------------------------------------------------------------------
F_BLUE, F_RED, F_YELLOW = "#2f55a4", "#e4252b", "#fde100"
F_EDGE = "#9aa7b8"


def flag_p(x, y, s):
    return rect(x, y, s, s, fill=F_BLUE) + rect(x + .32 * s, y + .32 * s, .36 * s, .36 * s, fill=WHITE)


def flag_i(x, y, s):
    return rect(x, y, s, s, fill=F_YELLOW, stroke=F_EDGE, sw=1) + circle(x + s / 2, y + s / 2, .21 * s, fill="#111")


def flag_z(x, y, s):
    c = (x + s / 2, y + s / 2)
    tri = lambda pts, f: poly(pts, stroke=None, fill=f, close=True)
    return (tri([(x, y), (x + s, y), c], F_YELLOW) + tri([(x, y), c, (x, y + s)], "#111")
            + tri([(x + s, y), (x + s, y + s), c], F_BLUE) + tri([(x, y + s), (x + s, y + s), c], F_RED))


def flag_u(x, y, s):
    h = s / 2
    return (rect(x, y, s, s, fill=WHITE, stroke=F_EDGE, sw=1) + rect(x, y, h, h, fill=F_RED)
            + rect(x + h, y + h, h, h, fill=F_RED))


def flag_black(x, y, s):
    return rect(x, y, s, s, fill="#111")


def flag_x(x, y, s):
    b = .17 * s
    return (rect(x, y, s, s, fill=WHITE, stroke=F_EDGE, sw=1) + rect(x + (s - b) / 2, y, b, s, fill=F_BLUE)
            + rect(x, y + (s - b) / 2, s, b, fill=F_BLUE))


def flag_first_substitute(x, y, s):
    w, h = 1.45 * s, .62 * s
    y0 = y + (s - h) / 2
    return (poly([(x, y0), (x + w, y0 + h / 2), (x, y0 + h)], stroke=None, fill=F_BLUE, close=True)
            + poly([(x, y0 + .2 * h), (x + .42 * w, y0 + h / 2), (x, y0 + .8 * h)], stroke=None, fill=F_YELLOW, close=True))


def flag_ap(x, y, s, uid="ap"):
    w, h = 1.45 * s, .66 * s
    y0 = y + (s - h) / 2
    shape = [(x, y0), (x + w, y0 + .32 * h), (x + w, y0 + .68 * h), (x, y0 + h)]
    clip = '<clipPath id="%s">%s</clipPath>' % (uid, poly(shape, stroke=None, fill="#000", close=True))
    sw_ = w / 5
    stripes = "".join(rect(x + i * sw_, y0, sw_ + .5, h, fill=F_RED if i % 2 == 0 else WHITE) for i in range(5))
    return clip + el("g", stripes, clip_path="url(#%s)" % uid) + poly(shape, stroke=F_EDGE, sw=1, close=True)


def flag_n(x, y, s):
    c = s / 4
    cells = "".join(rect(x + i * c, y + j * c, c, c, fill=F_BLUE if (i + j) % 2 == 0 else WHITE)
                    for i in range(4) for j in range(4))
    return cells + rect(x, y, s, s, stroke=F_EDGE, sw=1)


def flags():
    w, h = 1280, 640
    s = 108
    o = [card(w, h)]
    o.append(text(40, 54, "Race signals around the start", size=26, weight=800))
    o.append(text(40, 80, "The preparatory flag goes up at 4 minutes. The others are used when a start is recalled, postponed or abandoned.",
                  size=14, fill=MUTE))
    o.append(text(40, 128, "Preparatory signal, 4 minutes before the start", size=17, weight=700))
    row1 = ((flag_p, "P", "Preparatory signal"), (flag_i, "I", "Rule 30.1"), (flag_z, "Z", "Rule 30.2"),
            (flag_u, "U", "Rule 30.3"), (flag_black, "Black flag", "Rule 30.4"))
    for i, (fn, name, rule) in enumerate(row1):
        x = 60 + i * 245
        o.append(fn(x, 148, s))
        o.append(text(x, 288, name, size=18, weight=800))
        o.append(text(x, 310, rule, size=14))
        o.append(text(x, 330, "up: one sound, down: one long sound", size=12.5, fill=MUTE))
    o.append(line(40, 366, w - 40, 366, stroke=LINE, sw=1))
    o.append(text(40, 402, "Other signals", size=17, weight=700))
    row2 = ((flag_x, "X", "Individual recall", "up: one sound"),
            (flag_first_substitute, "First Substitute", "General recall", "up: two sounds, down: one"),
            (flag_ap, "AP", "Postponement", "up: two sounds, down: one"),
            (flag_n, "N", "Abandonment", "up: three sounds, down: one"))
    for i, (fn, name, meaning, snd) in enumerate(row2):
        x = 60 + i * 245
        o.append(fn(x, 422, s) if fn is not flag_ap else fn(x, 422, s, uid="apclip"))
        o.append(text(x, 562, name, size=18, weight=800))
        o.append(text(x, 584, meaning, size=14))
        o.append(text(x, 604, snd, size=12.5, fill=MUTE))
    o.append(text(1040, 452, "Sound notation", size=13, weight=700, fill=MUTE))
    o.append(text(1040, 472, "up: the flag is displayed", size=13, fill=MUTE))
    o.append(text(1040, 490, "down: the flag is removed", size=13, fill=MUTE))
    o.append(text(1040, 508, "After AP, N or First Substitute is", size=13, fill=MUTE))
    o.append(text(1040, 526, "removed, the warning signal follows", size=13, fill=MUTE))
    o.append(text(1040, 544, "one minute later.", size=13, fill=MUTE))
    o.append(text(w - 40, h - 14, "Flag designs redrawn after the World Sailing Race Signals, RRS 2025-2028",
                  size=11.5, fill=MUTE, anchor="end"))
    return w, h, "".join(o), "Race signals around the start", (
        "Preparatory flags P, I, Z, U and black, and the recall, postponement and abandonment flags X, First Substitute, AP and N.")


# --- circuit symbols ---------------------------------------------------------
def ground(x, y, c=INK):
    return (line(x - 12, y, x + 12, y, c, 2) + line(x - 8, y + 5, x + 8, y + 5, c, 2) + line(x - 4, y + 10, x + 4, y + 10, c, 2))


def fuse_h(x, y):
    return rect(x - 22, y - 8, 44, 16, fill=WHITE, stroke=INK, sw=2, rx=2) + line(x - 22, y, x + 22, y, INK, 1.5)


def fuse_v(x, y):
    return rect(x - 8, y - 20, 16, 40, fill=WHITE, stroke=INK, sw=2, rx=2) + line(x, y - 20, x, y + 20, INK, 1.5)


def dot(x, y, c=INK, r=4.5):
    return circle(x, y, r, fill=c)


def pin_dot(x, y):
    return circle(x, y, 4.5, fill=WHITE, stroke=INK, sw=1.5)


def net5v(x, y, direction="left"):
    """Stub with a +5V flag. direction = side the stub points to."""
    sgn = -1 if direction == "left" else 1
    x2 = x + sgn * 26
    anchor = "end" if direction == "left" else "start"
    return (line(x, y, x2, y, W_5V, 2.5) + line(x2, y - 8, x2, y + 8, W_5V, 2.5)
            + text(x2 + sgn * 6, y + 5, "+5V", size=13, weight=700, fill=W_5V, anchor=anchor, family=MONO))


def netgnd(x, y, direction="left"):
    sgn = -1 if direction == "left" else 1
    x2 = x + sgn * 26
    return line(x, y, x2, y, W_GND, 2.5) + line(x2, y, x2, y + 12, W_GND, 2.5) + ground(x2, y + 12, W_GND)


# --- schematic ---------------------------------------------------------------
def schematic():
    w, h = 1400, 940
    o = [card(w, h)]
    o.append(text(40, 54, "Wiring schematic", size=26, weight=800))
    o.append(text(40, 80, "The 5 V logic and the 12 V horn circuit share no connection. Only the dry contact of relay module K1 crosses the isolation line.",
                  size=14, fill=MUTE))
    # domains
    o.append(rect(30, 110, 690, 790, fill="#eaf2fb", stroke="#b9d0ea", sw=1.5, rx=16))
    o.append(text(54, 142, "5 V LOGIC DOMAIN", size=14, weight=800, fill=SEA, ls=1.5))
    o.append(text(54, 162, "powered from USB only", size=13, fill=MUTE))
    o.append(rect(750, 110, 620, 790, fill="#fdf1e6", stroke="#f0c9a2", sw=1.5, rx=16))
    o.append(text(774, 142, "12 V HORN DOMAIN", size=14, weight=800, fill="#b4531a", ls=1.5))
    o.append(text(774, 162, "separate battery or supply", size=13, fill=MUTE))
    o.append(line(735, 110, 735, 900, stroke="#7a8aa0", sw=2, dash="8 6"))
    o.append(text(727, 505, "no shared ground", size=12, fill=MUTE, anchor="middle", transform="rotate(-90 727 505)"))

    # --- left domain: Arduino
    o.append(rect(130, 185, 160, 44, fill=WHITE, stroke=INK, sw=2, rx=8))
    o.append(text(210, 212, "USB 5 V source", size=14, weight=700, anchor="middle"))
    o.append(line(210, 229, 210, 245, W_5V, 3))
    o.append(rect(130, 271, 160, 489, fill=TEAL, stroke=TEAL_DARK, sw=2, rx=10))
    o.append(rect(170, 245, 80, 26, fill=LINE, stroke=INK, sw=1.5, rx=3))
    o.append(text(210, 263, "USB", size=12, weight=700, anchor="middle", family=MONO))
    o.append(text(210, 306, "Arduino Nano", size=16, weight=800, fill=WHITE, anchor="middle"))
    o.append(text(210, 326, "or Uno R3", size=13, fill="#cfe9ec", anchor="middle"))
    pins = (("D6", 360, W_RELAY), ("D4", 500, W_START), ("D3", 580, W_CLK), ("D2", 610, W_DIO),
            ("5V", 680, W_5V), ("GND", 715, W_GND))
    for name, y, c in pins:
        o.append(text(278, y + 5, name, size=13, weight=700, fill=WHITE, anchor="end", family=MONO))
    # signal wires
    o.append(line(290, 360, 520, 360, W_RELAY, 3))
    o.append(line(290, 500, 540, 500, W_START, 3))
    o.append(line(290, 580, 520, 580, W_CLK, 3))
    o.append(line(290, 610, 520, 610, W_DIO, 3))
    o.append(net5v(290, 680, "right"))
    o.append(netgnd(290, 715, "right"))
    # START button
    o.append(circle(540, 500, 4.5, fill=INK) + circle(600, 500, 4.5, fill=INK))
    o.append(line(540, 500, 594, 472, INK, 3))
    o.append(line(604, 500, 650, 500, W_START, 3))
    o.append(netgnd(650, 500, "right").replace('x1="650"', 'x1="650"'))
    o.append(text(570, 530, "START", size=13, weight=800, anchor="middle"))
    o.append(text(570, 546, "normally open", size=11.5, fill=MUTE, anchor="middle"))
    # relay module K1
    o.append(rect(520, 320, 250, 135, fill=WHITE, stroke=INK, sw=2.5, rx=8))
    o.append(text(645, 340, "Relay module K1", size=14, weight=800, anchor="middle"))
    o.append(text(645, 392, "1 channel, 5 V", size=12, fill=MUTE, anchor="middle"))
    o.append(text(645, 410, "opto-isolated", size=12, fill=MUTE, anchor="middle"))
    for name, y in (("IN", 360), ("VCC", 395), ("GND", 430)):
        o.append(text(532, y + 5, name, size=12.5, weight=700, family=MONO))
        o.append(pin_dot(520, y))
    for name, y in (("COM", 360), ("NO", 395)):
        o.append(text(758, y + 5, name, size=12.5, weight=700, anchor="end", family=MONO))
        o.append(pin_dot(770, y))
    o.append(net5v(520, 395, "left"))
    o.append(netgnd(520, 430, "left"))
    # TM1637
    o.append(rect(520, 560, 180, 140, fill=WHITE, stroke=INK, sw=2.5, rx=8))
    o.append(text(640, 585, "TM1637", size=14, weight=800, anchor="middle"))
    o.append(text(640, 603, "4-digit display", size=12, fill=MUTE, anchor="middle"))
    for name, y in (("CLK", 580), ("DIO", 610), ("VCC", 645), ("GND", 675)):
        o.append(text(532, y + 5, name, size=12.5, weight=700, family=MONO))
        o.append(pin_dot(520, y))
    o.append(net5v(520, 645, "left"))
    o.append(netgnd(520, 675, "left"))
    o.append(text(54, 850, "The Arduino feeds only the coil of relay module K1.", size=13, fill=MUTE))
    o.append(text(54, 869, "Every +5V flag and every ground symbol is the same net.", size=13, fill=MUTE))

    # --- right domain
    red12 = "#b42318"
    # rails and wires
    o.append(line(1320, 215, 1287, 215, red12, 3.5))
    o.append(line(1243, 215, 1220, 215, red12, 3.5))
    o.append(line(1170, 215, 905, 215, red12, 3.5))
    o.append(line(1320, 215, 1320, 472, red12, 3.5))
    o.append(line(1320, 488, 1320, 800, W_GND, 3.5))
    o.append(line(1320, 800, 1020, 800, W_GND, 3.5))
    o.append(line(1130, 215, 1130, 400, red12, 3.5))
    o.append(line(1130, 470, 1130, 530, red12, 3.5))
    o.append(line(1130, 602, 1130, 800, W_GND, 3.5))
    o.append(poly([(905, 215), (905, 265)], red12, 3.5))
    o.append(poly([(905, 305), (905, 360), (770, 360)], red12, 3.5))
    o.append(poly([(770, 395), (1020, 395), (1020, 410)], red12, 3.5))
    o.append(line(960, 395, 960, 446, red12, 3.5))
    o.append(poly([(960, 472), (960, 540), (1020, 540)], W_GND, 3.5))
    o.append(line(1020, 500, 1020, 800, W_GND, 3.5))
    # components
    o.append(fuse_h(1265, 215) + text(1265, 192, "F1 main fuse", size=13, weight=700, anchor="middle"))
    o.append(circle(1170, 215, 4.5, fill=INK) + circle(1220, 215, 4.5, fill=INK) + line(1170, 215, 1214, 196, INK, 3))
    o.append(text(1195, 244, "S1", size=13, weight=800, anchor="middle"))
    o.append(text(1195, 260, "master switch", size=12, fill=MUTE, anchor="middle"))
    o.append(fuse_v(905, 285) + text(922, 282, "F2", size=13, weight=800) + text(922, 299, "small fuse, e.g. 2 A", size=12, fill=MUTE))
    o.append(text(1308, 246, "+12 V", size=13, weight=800, fill=red12, anchor="end"))
    # diode D1 (anode down, cathode bar up)
    o.append(poly([(948, 472), (972, 472), (960, 448)], INK, 2.5, fill=WHITE, close=True) + line(946, 446, 974, 446, INK, 3))
    o.append(text(944, 466, "D1", size=13, weight=800, anchor="end") + text(944, 482, "1N4007", size=11.5, fill=MUTE, anchor="end"))
    # K2 coil
    o.append(rect(1004, 410, 32, 90, fill=WHITE, stroke=INK, sw=2.5, rx=3))
    o.append(text(1020, 461, "K2", size=13, weight=800, anchor="middle"))
    o.append(text(1048, 486, "coil, 12 V", size=12, fill=MUTE))
    o.append(dot(960, 395) + dot(1020, 540))
    # K2 contact
    o.append(circle(1130, 400, 4.5, fill=WHITE, stroke=INK, sw=2) + circle(1130, 470, 4.5, fill=WHITE, stroke=INK, sw=2))
    o.append(line(1130, 470, 1113, 410, INK, 3))
    o.append(text(1146, 404, "30", size=12.5, weight=700, family=MONO) + text(1146, 474, "87", size=12.5, weight=700, family=MONO))
    o.append(text(1146, 440, "K2 contact", size=12.5, weight=800))
    o.append(line(1040, 440, 1118, 440, MUTE, 1.8, dash="5 4"))
    # motor and optional capacitor
    o.append(circle(1130, 566, 36, fill=WHITE, stroke=INK, sw=3) + text(1130, 577, "M", size=30, weight=800, anchor="middle"))
    o.append(text(1142, 640, "compressor", size=13, weight=800))
    o.append(dot(1130, 510) + dot(1130, 625))
    o.append(poly([(1130, 510), (1210, 510), (1210, 545)], MUTE, 2, dash="5 4"))
    o.append(poly([(1210, 557), (1210, 625), (1130, 625)], MUTE, 2, dash="5 4"))
    o.append(line(1196, 545, 1224, 545, INK, 2.5) + line(1196, 557, 1224, 557, INK, 2.5))
    o.append(text(1236, 548, "C1 100 nF", size=12, weight=700) + text(1236, 564, "optional", size=11.5, fill=MUTE))
    # battery
    o.append(line(1304, 472, 1336, 472, INK, 4) + line(1311, 488, 1329, 488, INK, 6))
    o.append(text(1290, 482, "12 V", size=13, weight=800, anchor="end") + text(1290, 498, "battery", size=12, fill=MUTE, anchor="end"))
    o.append(text(1304, 788, "battery minus", size=12, fill=MUTE, anchor="end"))
    o.append(dot(1130, 215) + dot(905, 215) + dot(1130, 800) + dot(1020, 800))
    o.append(text(790, 346, "K1 contact, dry", size=11.5, fill=MUTE))
    o.append(text(774, 842, "Compressor current flows only through F1, S1, K2 and their wiring.", size=13, fill=MUTE))
    o.append(text(774, 861, "A small compressor within the contact rating of the module can be", size=13, fill=MUTE))
    o.append(text(774, 880, "switched by K1 directly (option A, see docs/hardware.md).", size=13, fill=MUTE))
    return w, h, "".join(o), "Wiring schematic", (
        "Schematic with a 5 V logic domain (Arduino, TM1637, START button, relay module K1) and a separate 12 V horn domain "
        "(fuse F1, switch S1, automotive relay K2 with flyback diode D1, compressor). Only the dry contact of K1 crosses between them.")


# --- soldering diagram -------------------------------------------------------
LANE_GND, LANE_5V = 830, 860


def hop_path(points, lanes, skip=()):
    """Orthogonal path; horizontal segments hop over vertical lanes they do not join."""
    r = 7
    d = "M%s %s" % points[0]
    for (xa, ya), (xb, yb) in zip(points, points[1:]):
        if ya == yb:
            hits = sorted((lx for lx, y0, y1, lid in lanes
                           if lid not in skip and y0 < ya < y1 and min(xa, xb) + r < lx < max(xa, xb) - r),
                          reverse=xb < xa)
            for lx in hits:
                sweep = 1 if xb > xa else 0
                d += " H%s a%d %d 0 0 %d %d 0" % (lx - r * (1 if xb > xa else -1), r, r, sweep, 2 * r * (1 if xb > xa else -1))
            d += " H%s" % xb
        else:
            d += " V%s" % yb
    return d


def wiring():
    w, h = 1400, 900
    o = [card(w, h)]
    o.append(text(40, 54, "Soldering diagram", size=26, weight=800))
    o.append(text(40, 80, "Eleven wires and two splices. No custom board: the Arduino itself carries everything.", size=14, fill=MUTE))
    # Nano
    bx, by, bw, bh = 300, 210, 190, 500
    o.append(rect(bx, by, bw, bh, fill=TEAL, stroke=TEAL_DARK, sw=2, rx=10))
    o.append(rect(bx + 55, 172, 80, 52, fill=LINE, stroke=INK, sw=1.5, rx=4))
    o.append(text(bx + 95, 205, "USB", size=13, weight=800, anchor="middle", family=MONO))
    o.append(rect(bx + 75, 410, 40, 40, fill="#10161d", rx=3))
    o.append(circle(bx + 95, 330, 11, fill="#d9e2ea", stroke=TEAL_DARK, sw=1.5))
    left = ["D13", "3V3", "AREF", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "5V", "RST", "GND", "VIN"]
    right = ["D12", "D11", "D10", "D9", "D8", "D7", "D6", "D5", "D4", "D3", "D2", "GND", "RST", "D0", "D1"]
    used_left = {"5V": W_5V}
    used_right = {"D6": W_RELAY, "D4": W_START, "D3": W_CLK, "D2": W_DIO, "GND": W_GND}
    row_y = lambda r: 250 + 29 * (r - 1)
    for r in range(1, 16):
        y = row_y(r)
        for names, px, anchor, tx, used in ((left, bx + 12, "start", bx + 27, used_left), (right, bx + bw - 12, "end", bx + bw - 27, used_right)):
            name = names[r - 1]
            c = used.get(name)
            if c and not (names is left and name == "GND"):
                pw_ = 38 if len(name) > 2 else 30
                pill_x = tx - 4 if anchor == "start" else tx - pw_ + 4
                o.append(rect(pill_x, y - 11, pw_, 22, fill=c, rx=11))
                o.append(text(tx, y + 4.5, name, size=12.5, weight=800, fill=INK if c == W_CLK else WHITE, anchor=anchor, family=MONO))
            else:
                o.append(text(tx, y + 4.5, name, size=12, weight=600, fill="#d4eef0", anchor=anchor, family=MONO))
            o.append(circle(px, y, 7 if c else 6, fill="#e8c76a", stroke=c or "#b8942e", sw=3 if c else 1.5))
    o.append(text(40, 214, "Arduino Nano", size=16, weight=800))
    o.append(text(40, 234, "top view, USB connector up", size=13, fill=MUTE))
    o.append(text(40, 254, "An Uno R3 has the same pins:", size=13, fill=MUTE))
    o.append(text(40, 272, "use jumper wires instead.", size=13, fill=MUTE))

    # devices
    dx = 900
    # relay module
    o.append(rect(dx, 190, 300, 190, fill=WHITE, stroke=INK, sw=2.5, rx=8))
    o.append(text(dx + 150, 214, "Relay module K1", size=15, weight=800, anchor="middle"))
    o.append(rect(dx + 205, 232, 28, 98, fill="#2f8f4e", rx=3))
    for name, y in (("IN", 240), ("GND", 280), ("VCC", 320)):
        o.append(text(dx + 14, y + 5, name, size=13, weight=700, family=MONO))
        o.append(pin_dot(dx, y))
    for name, y in (("COM", 240), ("NO", 280), ("NC", 320)):
        o.append(circle(dx + 219, y, 7, fill="#d4e7d9", stroke="#1d5c32", sw=2))
        o.append(text(dx + 244, y + 5, name, size=13, weight=700, family=MONO))
    o.append(text(dx + 150, 365, "COM and NO go to the 12 V circuit (see schematic)", size=11.5, fill=MUTE, anchor="middle"))
    # button
    o.append(rect(dx, 420, 300, 120, fill=WHITE, stroke=INK, sw=2.5, rx=8))
    o.append(text(dx + 150, 444, "START push button, normally open", size=14, weight=800, anchor="middle"))
    o.append(circle(dx + 190, 492, 30, fill="#cfd6df", stroke=INK, sw=2.5) + circle(dx + 190, 492, 20, fill=RED))
    for name, y in (("A", 455), ("B", 505)):
        o.append(pin_dot(dx, y))
        o.append(text(dx + 14, y + 5, "lug " + name, size=13, weight=700, family=MONO))
    # TM1637
    o.append(rect(dx, 590, 300, 190, fill=WHITE, stroke=INK, sw=2.5, rx=8))
    o.append(text(dx + 150, 612, "TM1637 display module", size=15, weight=800, anchor="middle"))
    for name, y in (("CLK", 630), ("DIO", 670), ("VCC", 710), ("GND", 750)):
        o.append(text(dx + 14, y + 5, name, size=13, weight=700, family=MONO))
        o.append(pin_dot(dx, y))
    o.append(rect(dx + 110, 650, 172, 96, fill="#05080d", rx=8))
    dg, total = clock_display(0, 0, 28, 52, 6, 7, 16, "0500", AMBER, "#0e0a03")
    o.append(group(dg, transform="translate(%.1f %d)" % (dx + 110 + (172 - total) / 2, 672)))

    # wires
    lanes = [(LANE_GND, 280, 760, "gnd"), (LANE_5V, 320, 815, "5v")]
    wires = [
        (1, [(478, 511), (700, 511), (700, 630), (dx, 630)], W_CLK, ()),
        (2, [(478, 540), (660, 540), (660, 670), (dx, 670)], W_DIO, ()),
        (10, [(478, 482), (600, 482), (600, 455), (dx, 455)], W_START, ()),
        (11, [(478, 424), (560, 424), (560, 240), (dx, 240)], W_RELAY, ()),
        (6, [(478, 569), (510, 569), (510, 760), (LANE_GND, 760), (LANE_GND, 280), (dx, 280)], W_GND, ("gnd",)),
        (9, [(LANE_GND, 505), (dx, 505)], W_GND, ("gnd",)),
        (7, [(LANE_GND, 750), (dx, 750)], W_GND, ("gnd",)),
        (3, [(312, 569), (240, 569), (240, 815), (LANE_5V, 815), (LANE_5V, 320), (dx, 320)], W_5V, ("5v",)),
        (4, [(LANE_5V, 710), (dx, 710)], W_5V, ("5v",)),
    ]
    for num, pts, color, skip in wires:
        d = hop_path(pts, lanes, skip)
        o.append(path(d, stroke="#ffffff", sw=7))        # white casing keeps crossings readable
        o.append(path(d, stroke=color, sw=4))
    # splice markers and junction dots
    for x, y in ((LANE_GND, 505), (LANE_GND, 750), (LANE_5V, 710)):
        o.append(dot(x, y, INK, 5))
    o.append(circle(LANE_GND, 760, 11, fill=W_GND, stroke=WHITE, sw=2) + text(LANE_GND, 765, "B", size=13, weight=800, fill=WHITE, anchor="middle"))
    o.append(circle(LANE_5V, 815, 11, fill=W_5V, stroke=WHITE, sw=2) + text(LANE_5V, 820, "A", size=13, weight=800, fill=WHITE, anchor="middle"))
    # wire number badges (the number of the wire as in docs/hardware.md)
    badges = {1: (770, 630), 2: (770, 670), 10: (770, 455), 11: (770, 240), 6: (560, 760), 9: (882, 505),
              7: (882, 750), 3: (240, 700), 4: (882, 710), 5: (LANE_5V, 380), 8: (LANE_GND, 380)}
    for n, (x, y) in badges.items():
        o.append(circle(x, y, 10, fill=WHITE, stroke=INK, sw=1.5) + text(x, y + 4.5, n, size=12.5, weight=800, anchor="middle"))
    # legend
    o.append(text(dx, 836, "Wire colours", size=13, weight=800))
    items = ((W_CLK, "yellow: CLK (D3)"), (W_DIO, "green: DIO (D2)"), (W_START, "blue: START (D4)"),
             (W_RELAY, "orange: relay IN (D6)"), (W_5V, "red: 5V"), (W_GND, "black: GND"))
    for i, (c, label) in enumerate(items):
        x, y = dx + (i % 3) * 150, 856 + (i // 3) * 20
        o.append(line(x, y - 4, x + 22, y - 4, c, 4))
        o.append(text(x + 28, y, label, size=12, fill=INK))
    o.append(text(40, 868, "A: 5V splice joins wires 3, 4 and 5.   B: GND splice joins wires 6, 7, 8 and 9.", size=13, fill=MUTE))
    o.append(text(40, 886, "Header order differs between modules, read the silkscreen.", size=13, fill=MUTE))
    return w, h, "".join(o), "Soldering diagram", (
        "Pictorial wiring of an Arduino Nano to a TM1637 display, a START button and a relay module with eleven numbered, "
        "colour-coded wires and two splices.")


# --- social images -----------------------------------------------------------
SW, SH = 1200, 627


def hero_social():
    defs = ('<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a1f3d"/>'
            '<stop offset="1" stop-color="#14507f"/></linearGradient>' + GLOW_DEFS + "</defs>")
    o = [defs, rect(0, 0, SW, SH, fill="url(#bg)")]
    for op, dy in ((0.10, 0), (0.07, 22), (0.05, 44)):
        base = SH - 70 + dy
        o.append(path("M0 %d C 150 %d, 300 %d, 450 %d S 750 %d, 900 %d S 1050 %d, 1200 %d"
                      % (base, base - 34, base + 34, base, base - 34, base, base + 34, base),
                      stroke="#ffffff", sw=2, opacity=op))
    o.append(text(64, 96, "ARDUINO · TM1637 · RELAY", size=18, weight=700, fill=AMBER, ls=3))
    o.append(text(64, 180, "Regatta Start", size=70, weight=800, fill=WHITE))
    o.append(text(64, 256, "Timer", size=70, weight=800, fill=WHITE))
    o.append(text(64, 306, "Five-minute start sequence with horn control.", size=24, fill="#cfe0f3"))
    o.append(text(64, 340, "One button, one display, one relay.", size=24, fill="#cfe0f3"))
    px, py, pw, ph = 640, 70, 500, 270
    o.append(rect(px, py, pw, ph, fill="#05080d", stroke="#26405f", sw=2, rx=26))
    o.append(rect(px + 18, py + 18, pw - 36, ph - 36, fill="#070d14", stroke="#12202f", sw=1.5, rx=16))
    dg, total = clock_display(0, 0, 80, 150, 15, 18, 38, "0500", AMBER, "#0e0a03")
    o.append(group(el("g", dg, filter="url(#glow)"), transform="translate(%.1f %.1f)" % (px + (pw - total) / 2, py + (ph - 150) / 2)))
    facts = (("1", "button"), ("5:00", "countdown"), ("4", "horn signals"), ("110", "test scenarios"))
    for i, (big, small) in enumerate(facts):
        x = 64 + i * 276
        o.append(rect(x, 420, 252, 108, fill="rgba(255,255,255,0.07)", stroke="#6f9bc8", sw=1.2, rx=14))
        o.append(text(x + 24, 478, big, size=44, weight=800, fill=AMBER))
        o.append(text(x + 24, 508, small, size=17, fill="#dbe8f6"))
    o.append(text(64, 584, "Original project by diggahpl · CC BY-NC 4.0 · github.com/diggahpl/Regatta-start-timer", size=16, fill="#9fc0e0"))
    return "".join(o)


def flags_social():
    """Bigger flags with short captions for the social image (drawn in card coordinates 1104x441)."""
    w, h = 1104, 441
    o = []
    o.append(text(36, 36, "4 minutes before the start the preparatory flag goes up", size=20, weight=800))
    row1 = ((flag_p, "P", "preparatory signal", ""),
            (flag_i, "I", "rule 30.1", "return around an end"),
            (flag_z, "Z", "rule 30.2", "20% penalty"),
            (flag_u, "U", "rule 30.3", "disqualified"),
            (flag_black, "Black", "rule 30.4", "disqualified, even if restarted"))
    for i, (fn, name, line2, line3) in enumerate(row1):
        x = 36 + i * 212
        o.append(fn(x, 52, 100))
        o.append(text(x, 182, name, size=22, weight=800))
        o.append(text(x, 205, line2, size=16))
        o.append(text(x, 225, line3, size=14.5, fill=MUTE))
    o.append(line(36, 246, w - 36, 246, stroke=LINE, sw=1))
    o.append(text(36, 278, "Other signals", size=20, weight=800))
    row2 = ((flag_x, "X", "individual recall"),
            (flag_first_substitute, "First Substitute", "general recall"),
            (flag_ap, "AP", "postponement"),
            (flag_n, "N", "abandonment"))
    for i, (fn, name, meaning) in enumerate(row2):
        x = 36 + i * 232
        o.append(fn(x, 292, 80) if fn is not flag_ap else fn(x, 292, 80, uid="apsoc"))
        o.append(text(x, 394, name, size=19, weight=800))
        o.append(text(x, 416, meaning, size=15.5))
    o.append(text(930, 322, "New warning signal", size=15, weight=700))
    o.append(text(930, 342, "1 minute after the", size=15, fill=MUTE))
    o.append(text(930, 360, "flag is removed", size=15, fill=MUTE))
    return w, h, "".join(o)


def social_card(fig, title, caption, crop=None):
    """White card on the navy background; crop = (x, y, w, h) window of the figure to show."""
    fw, fh, inner = fig[0], fig[1], fig[2]
    cx, cy, cw, ch = crop or (0, 0, fw, fh)
    kx, ky, kw, kh = 48, 104, 1104, 494
    s = min(kw / cw, kh / ch)
    tx = kx + (kw - cw * s) / 2 - cx * s
    ty = ky + (kh - ch * s) / 2 - cy * s
    defs = ('<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a1f3d"/>'
            '<stop offset="1" stop-color="#14507f"/></linearGradient>'
            '<clipPath id="cardclip"><rect x="%d" y="%d" width="%d" height="%d" rx="14"/></clipPath>'
            '<clipPath id="cropclip"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath></defs>'
            % (kx, ky, kw, kh, cx, cy, cw, ch))
    o = [defs, rect(0, 0, SW, SH, fill="url(#bg)")]
    o.append(text(48, 58, title, size=32, weight=800, fill=WHITE))
    o.append(text(48, 88, caption, size=17, fill="#cfe0f3"))
    o.append(rect(kx, ky, kw, kh, fill=WHITE, rx=14))
    framed = el("g", inner, clip_path="url(#cropclip)")
    o.append(el("g", group(framed, transform="translate(%.2f %.2f) scale(%.4f)" % (tx, ty, s)), clip_path="url(#cardclip)"))
    o.append(text(48, 620, "Regatta Start Timer \u00b7 original project by diggahpl \u00b7 CC BY-NC 4.0", size=14, fill="#9fc0e0"))
    return "".join(o)


# --- main --------------------------------------------------------------------
def write(path_, content):
    os.makedirs(os.path.dirname(path_), exist_ok=True)
    with open(path_, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("wrote", os.path.relpath(path_, ROOT))


def emit(rel, fig):
    w, h, inner, title, desc = fig
    write(os.path.join(ROOT, rel), svg_doc(w, h, inner, title, desc))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--social", metavar="DIR", help="write the four 1200x627 social SVGs to DIR/src")
    args = ap.parse_args()
    if args.social:
        out = os.path.join(args.social, "src")
        socials = (
            ("1-hero.svg", (SW, SH, hero_social(), "Regatta Start Timer", "Social hero image."), None),
            ("2-wiring.svg", None, ("Eleven wires, two splices, no custom board", "Soldering diagram for the Arduino, the TM1637 display, the START button and the relay module.", (20, 150, 1360, 745))),
            ("3-schematic.svg", None, ("Two isolated domains: 5 V logic and 12 V horn", "Only the dry contact of the relay module crosses between them.", (20, 100, 1360, 810))),
            ("4-timeline.svg", None, ("Five minutes, four horn signals", "Warning, preparatory, one-minute and starting signal, with the flags that go with them.", (20, 104, 1259, 372))),
            ("5-flags.svg", None, ("Visual signals of the start (RRS 26)", "Times are taken from the flags, the horn only accompanies them", None)),
        )
        figs = {"2-wiring.svg": wiring(), "3-schematic.svg": schematic(), "4-timeline.svg": timeline(),
                "5-flags.svg": flags_social()}
        for name, fig, meta in socials:
            if fig is not None:
                svg = svg_doc(SW, SH, fig[2], fig[3], fig[4])
            else:
                title, caption, crop = meta
                svg = svg_doc(SW, SH, social_card(figs[name], title, caption, crop), title, caption)
            write(os.path.join(out, name), svg)
        return
    emit("docs/images/banner.svg", banner())
    emit("docs/images/timeline.svg", timeline())
    emit("docs/images/flags.svg", flags())
    emit("hardware/schematic.svg", schematic())
    emit("hardware/wiring.svg", wiring())


if __name__ == "__main__":
    main()
