#!/usr/bin/env python3
"""ZyraDesign social post renderer.

Usage: python3 build.py spec.json [outdir]
Renders two portrait images from one spec:
  ig.png / ig.jpg  1080x1350 (4:5 portrait): Instagram + Facebook
  li.png / li.jpg  1200x1500 (4:5 portrait, higher resolution): LinkedIn
Fonts: Outfit from node_modules (run `npm install` in this folder first).
"""
import json, math, random, subprocess, sys, pathlib, shutil

HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE / "node_modules/@fontsource/outfit/files"
BG = "#111111"
LOGO = HERE.parent / "assets" / "logo-zd.png"
CRIMSON = "#c8173f"      # mesh lines
ACCENT = "#d4194a"       # accent text

FORMATS = {
    "ig": dict(w=1080, h=1350, mesh_h=520, brand=64, tag=28, head=84, sub=44, item=40, note=34, pad=80, badge=96, icon=54),
}
# LinkedIn: same portrait layout rendered at 1200x1500 (every size scaled by 1200/1080)
_k = 1200 / 1080
FORMATS["li"] = {key: round(val * _k) for key, val in FORMATS["ig"].items()}


def font_faces():
    css = []
    ranges = {
        "latin": "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
        "latin-ext": "U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
    }
    for wgt in (300, 500, 700, 800):
        for sub, rng in ranges.items():
            f = FONTS / f"outfit-{sub}-{wgt}-normal.woff2"
            css.append(
                f"@font-face{{font-family:'Outfit';font-weight:{wgt};"
                f"src:url('file://{f}') format('woff2');unicode-range:{rng}}}"
            )
    return "\n".join(css)


def mesh_svg(w, h, seed=7, rows=40, cols=72, amp=0.30):
    """Crimson wireframe terrain, fading out towards the top."""
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]

    def height(u, v):
        return (math.sin(u * 5.1 + ph[0] + v * 2.0) * 0.5
                + math.sin(u * 9.3 + ph[1] - v * 3.1) * 0.3
                + math.sin(u * 2.2 + ph[2] + v * 4.0) * 0.6)

    pts = {}
    for i in range(rows + 1):
        v = i / rows
        for j in range(cols + 1):
            u = j / cols
            persp = 0.55 + 0.9 * v
            x = w / 2 + (u - 0.5) * w * 1.5 * persp
            base = h * (0.24 + 0.62 * v ** 1.25)
            y = base - height(u, v) * h * amp * (0.35 + 0.9 * v)
            pts[(i, j)] = (x, y)

    def path(seq):
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in seq)

    d = []
    for i in range(rows + 1):
        d.append(path([pts[(i, j)] for j in range(cols + 1)]))
    for j in range(cols + 1):
        d.append(path([pts[(i, j)] for i in range(rows + 1)]))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".45" stop-color="#fff" stop-opacity=".85"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>'
        f'<mask id="m"><rect width="{w}" height="{h}" fill="url(#fade)"/></mask></defs>'
        f'<g mask="url(#m)" fill="none" stroke="{CRIMSON}" stroke-width="1.0" stroke-linejoin="round">'
        f'<path d="{" ".join(d)}"/></g></svg>'
    )


ICONS = {
    "check": '<svg viewBox="0 0 48 48" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><path d="M15 25l6 6 12-13"/></svg>',
    "cross": f'<svg viewBox="0 0 48 48" fill="none" stroke="{ACCENT}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><path d="M17 17l14 14M31 17L17 31"/></svg>',
    "clock": '<svg viewBox="0 0 48 48" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><path d="M24 13v11l7 5"/></svg>',
    "bolt": '<svg viewBox="0 0 48 48" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><path d="M26 11L16 26h8l-2 11 10-15h-8z"/></svg>',
    "dot": '<svg viewBox="0 0 48 48" fill="none" stroke="#fff" stroke-width="3"><circle cx="24" cy="24" r="20"/><circle cx="24" cy="24" r="5" fill="#fff"/></svg>',
}

# Large line icons for the "hero" slot above the kicker (spec: "hero": "mail"). No ring, drawn inside a CSS circle.
_H = 'viewBox="0 0 48 48" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"'
HERO = {
    "mail": f'<svg {_H}><rect x="6" y="11" width="36" height="26" rx="4"/><path d="M7 14l17 13 17-13"/></svg>',
    "search": f'<svg {_H}><circle cx="21" cy="21" r="12"/><path d="M30 30l10 10"/></svg>',
    "bolt": f'<svg {_H}><path d="M27 6L12 27h11l-2 15 15-22H25z"/></svg>',
    "phone": f'<svg {_H}><rect x="14" y="5" width="20" height="38" rx="4"/><path d="M21 38h6"/></svg>',
    "shield": f'<svg {_H}><path d="M24 5l14 5v11c0 9-6 16-14 20C16 37 10 30 10 21V10z"/><path d="M18 24l5 5 8-9"/></svg>',
    "bulb": f'<svg {_H}><path d="M17 33c0-3-5-5-5-12a12 12 0 0124 0c0 7-5 9-5 12z"/><path d="M18 39h12M20 43h8"/></svg>',
    "chat": f'<svg {_H}><path d="M7 11h34v22H22l-9 8v-8H7z"/><path d="M15 20h18M15 26h11"/></svg>',
    "gear": f'<svg {_H}><circle cx="24" cy="24" r="6"/><path d="M24 5v6M24 37v6M5 24h6M37 24h6M10.5 10.5l4.2 4.2M33.3 33.3l4.2 4.2M10.5 37.5l4.2-4.2M33.3 14.7l4.2-4.2"/></svg>',
}


# Larger line-art scenes with an original character ("illustration" in spec, replaces "hero").
_W = 'fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"'
_A = '#d4194a'
ILLUS = {
    # Little character inspecting a crossed-out <meta keywords> tag with a magnifier.
    "detective": f"""<svg viewBox="0 0 460 270" xmlns="http://www.w3.org/2000/svg">
  <defs><clipPath id="headclip"><circle cx="140" cy="70" r="38"/></clipPath>
        <clipPath id="lensclip"><circle cx="316" cy="140" r="30"/></clipPath></defs>
  <ellipse cx="140" cy="258" rx="78" ry="9" fill="#000" opacity=".6"/>
  <!-- legs + shoes -->
  <path d="M126 200v48M154 200v48" stroke="#fff" stroke-width="7" stroke-linecap="round"/>
  <path d="M114 250h18M148 250h22" stroke="#fff" stroke-width="10" stroke-linecap="round"/>
  <!-- torso (hoodie with zip) -->
  <rect x="102" y="114" width="76" height="90" rx="26" fill="#1e1e1e" stroke="#fff" stroke-width="5"/>
  <path d="M140 122v44" stroke="{_A}" stroke-width="4" stroke-linecap="round"/>
  <!-- left arm on hip, fist -->
  <path d="M106 136q-24 20 -4 42" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round"/>
  <!-- tag under inspection -->
  <g transform="rotate(-6 370 150)">
    <rect x="296" y="124" width="150" height="54" rx="14" fill="#1b1b1b" stroke="#fff" stroke-width="4"/>
    <text x="371" y="159" text-anchor="middle" font-family="Outfit" font-weight="700" font-size="25" fill="#fff">&lt;keywords&gt;</text>
    <path d="M308 151h126" stroke="{_A}" stroke-width="4" stroke-linecap="round"/>
  </g>
  <circle cx="444" cy="122" r="19" fill="{_A}"/>
  <path d="M436 114l16 16M452 114l-16 16" stroke="#fff" stroke-width="5" stroke-linecap="round"/>
  <!-- magnifier: glass, ring, crimson handle -->
  <g clip-path="url(#lensclip)"><circle cx="316" cy="140" r="30" fill="#fff" opacity=".04"/></g>
  <path d="M294 162L260 184" stroke="#3a1420" stroke-width="16" stroke-linecap="round"/>
  <path d="M294 162L260 184" stroke="{_A}" stroke-width="11" stroke-linecap="round"/>
  <circle cx="316" cy="140" r="30" fill="none" stroke="#fff" stroke-width="6"/>
  <path d="M300 128q8 -9 20 -6" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".6"/>
  <!-- right arm reaching to handle, round hand gripping -->
  <path d="M176 136L212 170L250 182" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="258" cy="184" r="10" fill="#fff"/>
  <!-- head: face, hair clipped inside -->
  <circle cx="140" cy="70" r="38" fill="#1e1e1e"/>
  <g clip-path="url(#headclip)"><path d="M98 30h90v26q-26 -12 -56 -2q-18 6 -34 4z" fill="#fff"/></g>
  <circle cx="140" cy="70" r="38" fill="none" stroke="#fff" stroke-width="5"/>
  <path d="M150 63l11 -2M166 61l10 2" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
  <circle cx="156" cy="73" r="4.5" fill="#fff"/><circle cx="171" cy="73" r="4.5" fill="#fff"/>
  <path d="M152 92q9 -4 18 1" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
  <!-- thought marks -->
  <text x="190" y="40" font-family="Outfit" font-weight="800" font-size="44" fill="{_A}">?</text>
  <text x="216" y="24" font-family="Outfit" font-weight="800" font-size="28" fill="{_A}" opacity=".6">?</text>
</svg>""",
}


def html(spec, fmt):
    f = FORMATS[fmt]
    ig = True  # portrait layout only
    items = "".join(
        f'<div class="item"><span class="ic">{ICONS.get(it.get("icon", "dot"))}</span><span>{it["text"]}</span></div>'
        for it in spec.get("items", [])
    )
    head = "<br>".join(spec["headline"])
    hero = f'<div class="hero">{HERO[spec["hero"]]}</div>' if spec.get("hero") else ""
    if spec.get("illustration"):
        hero = f'<div class="illus">{ILLUS[spec["illustration"]]}</div>'
    kicker = f'<div class="kicker">{spec["kicker"]}</div>' if spec.get("kicker") else ""
    sub = f'<div class="sub">{spec["sub"]}</div>' if spec.get("sub") else ""
    note = f'<div class="note">{spec["note"]}</div>' if spec.get("note") else ""
    css = f"""
{font_faces()}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{f['w']}px;height:{f['h']}px}}
body{{background:{BG};color:#fff;font-family:'Outfit',sans-serif;position:relative;overflow:hidden}}
.mesh{{position:absolute;left:0;bottom:0;width:{f['w']}px;height:{f['mesh_h']}px}}
.top{{position:absolute;top:{f['pad'] * (0.6 if ig else 0.55):.0f}px;left:0;right:0;text-align:{'center' if ig else 'left'};{'' if ig else f"padding-left:{f['pad']}px"}}}
.brand{{font-size:{f['brand']}px;line-height:1;letter-spacing:.01em}}
.brand b{{font-weight:800}} .brand i{{font-style:normal;font-weight:300}}
.tag{{font-size:{f['tag']}px;font-weight:500;margin-top:{f['tag'] * .35:.0f}px;letter-spacing:.02em}}
.main{{position:absolute;left:{f['pad']}px;right:{f['pad']}px;top:{f"{round((195 if spec.get('illustration') else 215 if spec.get('hero') else 250) * f['w'] / 1080)}px" if ig else '150px'};text-align:{'center' if ig else 'left'}}}
.hero{{width:{round(f['head'] * 1.35)}px;height:{round(f['head'] * 1.35)}px;margin:0 auto {round(f['head'] * .3)}px;padding:{round(f['head'] * .2)}px;border-radius:50%;border:2px solid {ACCENT};box-shadow:0 0 36px rgba(212,25,74,.45), inset 0 0 22px rgba(212,25,74,.18)}} .hero svg{{width:100%;height:100%;display:block}}
.illus{{width:{round(f['w']*.5)}px;margin:0 auto {round(f['head']*.25)}px}} .illus svg{{width:100%;height:auto;display:block;overflow:visible}}
.kicker{{font-size:{f['tag'] * (1.0 if ig else 1.0):.0f}px;font-weight:700;letter-spacing:.22em;color:{ACCENT};margin-bottom:{f['head'] * .35:.0f}px}}
h1{{font-size:{f['head']}px;line-height:1.06;font-weight:800;text-transform:uppercase;letter-spacing:.005em}}
h1 em{{font-style:normal;color:{ACCENT}}}
.sub{{font-size:{f['sub']}px;line-height:1.3;font-weight:500;margin-top:{f['sub'] * .8:.0f}px;{'max-width:860px;margin-left:auto;margin-right:auto' if ig else 'max-width:760px'}}}
.items{{margin-top:{f['item'] * 1.2:.0f}px;display:flex;flex-direction:column;gap:{f['item'] * .55:.0f}px;{'align-items:center' if ig else ''}}}
.item{{display:flex;align-items:center;gap:{f['item'] * .5:.0f}px;font-size:{f['item']}px;font-weight:500}}
.ic{{width:{f['icon']}px;height:{f['icon']}px;flex:none;display:block}} .ic svg{{width:100%;height:100%;display:block}}
.note{{position:absolute;left:{f['pad']}px;right:{f['pad']}px;bottom:{f['badge'] * (1.7 if ig else 1.0):.0f}px;font-size:{f['note']}px;font-weight:500;text-align:{'center' if ig else 'left'};text-shadow:0 2px 12px #000}}
.badge{{position:absolute;right:{f['pad'] * .45:.0f}px;bottom:{f['pad'] * .45:.0f}px;width:{f['badge']}px;height:{f['badge']}px;border-radius:50%;
 background:radial-gradient(circle at 30% 25%,#3a2a33,#141014);border:2px solid rgba(255,255,255,.28);display:flex;align-items:center;justify-content:center;box-shadow:0 0 24px rgba(200,23,63,.35)}}
.badge img{{width:{f['badge'] * .62:.0f}px;height:auto;display:block}}
"""
    return f"""<!DOCTYPE html><html lang="cs"><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="mesh">{mesh_svg(f['w'], f['mesh_h'], seed=spec.get('seed', 7))}</div>
<div class="top"><div class="brand"><b>ZYRA</b><i>DESIGN</i></div><div class="tag">Tvorba webů na míru</div></div>
<div class="main">{hero}{kicker}<h1>{head}</h1>{sub}<div class="items">{items}</div></div>
{note}
<div class="badge"><img src="file://{LOGO}"></div>
</body></html>"""


def render(spec, outdir):
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    for fmt, f in FORMATS.items():
        page = outdir / f"{fmt}.html"
        page.write_text(html(spec, fmt), encoding="utf-8")
        png = outdir / f"{fmt}.png"
        subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", "--force-device-scale-factor=1",
                        f"--window-size={f['w']},{f['h']}", f"--screenshot={png}", f"file://{page}"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # JPEG copy (Instagram requires JPEG)
        try:
            from PIL import Image
            Image.open(png).convert("RGB").save(outdir / f"{fmt}.jpg", quality=92)
        except ImportError:
            pass
        page.unlink()
        print("rendered", png)


if __name__ == "__main__":
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    render(spec, pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else HERE / "out"))
