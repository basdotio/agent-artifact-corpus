"""合并 data/crawl/*.json + 截图配色 → data/sites.json
用法: python3 tools/build.py tools（需 pip install pillow）
"""
import colorsys
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(sys.argv[1]).resolve()
CRAWL = ROOT / "data/crawl"
SHOTS = ROOT / "screenshots"

# 人工判定的站点类型（其余按标题关键词推断，默认 personal）
KIND_OVERRIDES = {
    "studio": [21, 35, 45, 46, 48, 57, 79, 82, 89, 97, 106, 110, 112, 119, 121, 128, 129, 130, 134, 136,
               137, 143, 151, 152, 155, 158, 159, 160, 161, 162, 164, 165, 166, 177, 178],
    "template": [108, 111],
    "product": [20, 50, 56, 84, 131],
    "company": [15, 90],
}
KIND_BY_ID = {i: k for k, ids in KIND_OVERRIDES.items() for i in ids}

ROLE_PATTERNS = {
    "product-designer": r"product design",
    "design-engineer": r"design engineer|ui engineer|design craftsman",
    "creative-developer": r"creative (front-?end )?develop|creative technologist|interactive develop|creative 3d|web developer|front-?end|développeur|developer",
    "ui-ux-designer": r"ui/?ux|ux/?ui|interactive designer|digital (experience |product )?designer|web ?designer|webdesign",
    "illustrator": r"illustrat|papercraft|lettering|sign painting",
    "motion-designer": r"motion|animat",
    "art-director": r"art director|creative director",
    "brand-designer": r"brand",
    "photographer": r"photograph",
    "no-code-builder": r"framer|webflow|no-code|tilda|tildе|тильд",
}

SERIF = r"serif(?!.*sans)|garamond|times|caslon|tiempos|playfair|editorial|baskerville|bodoni|didot|georgia|canela|ogg|reckless|freight|lora|libre|newsreader|instrument serif|gt sectra|span|ivar|domaine|recoleta|fraunces"
MONO = r"mono|code|courier|consolas|menlo|plex mono|space mono|fira|jetbrains|sf mono|input|berkeley"
SYSTEM = r"^(-apple-system|system-ui|blinkmacsystemfont|helvetica|arial|sans-serif|tahoma|verdana)"


def palette(img_path, n=6):
    img = Image.open(img_path).convert("RGB").resize((160, 100))
    q = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: n * 3]
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    out = []
    for c, idx in counts:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        out.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "share": round(c / total, 3),
                    "lum": round(0.2126 * r / 255 + 0.7152 * g / 255 + 0.0722 * b / 255, 3),
                    "sat": round(s if 0.08 < l < 0.92 else 0, 3)})
    return out


def color_profile(pal):
    lum = sum(p["lum"] * p["share"] for p in pal)
    sat = sum(p["sat"] * p["share"] for p in pal)
    accents = [p for p in pal if p["sat"] > 0.35 and p["share"] >= 0.02]
    accent = max(accents, key=lambda p: p["sat"] * p["share"])["hex"] if accents else None
    return {
        "theme": "dark" if lum < 0.35 else "light" if lum > 0.6 else "mid",
        "saturation": "mono" if sat < 0.08 and not accent else "muted" if sat < 0.25 else "vivid",
        "accent": accent,
        "meanLuminance": round(lum, 3),
        "palette": pal,
    }


def font_class(name):
    n = (name or "").lower()
    if re.search(MONO, n):
        return "mono"
    if re.search(SERIF, n):
        return "serif"
    if re.search(SYSTEM, n):
        return "system-sans"
    return "sans"


def norm_font(name):
    """Inter-SemiBold / GeistSans / PPNeueMontreal / inter → 统一字族名"""
    if not name:
        return None
    n = re.sub(r"[-_ ]?(thin|extralight|ultralight|light|regular|book|medium|semibold|demibold|bold|extrabold|black|heavy|italic|variable|vf|web|display|text)\b", "", name, flags=re.I)
    n = re.sub(r"^(PP|GT|TWK|ABC|NB) ?(?=[A-Z])", "", n.strip())
    n = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n)
    n = re.sub(r"\s+(Sans|Serif)$", lambda m: "" if n.lower().startswith("geist") else m.group(0), n)
    return n.strip().title() if n.islower() else n.strip()


def first(tech, keys, default):
    return next((k for k in keys if tech.get(k)), default)


def derive(rec):
    tech = rec.get("tech") or {}
    ctx = rec.get("canvasContexts") or {}
    layout = rec.get("layout") or {}
    typo = rec.get("typography") or {}
    webgl = bool(ctx.get("webgl") or ctx.get("webgl2") or ctx.get("experimental-webgl"))
    is3d = webgl or any(tech.get(k) for k in ("three", "spline", "ogl"))

    motion_libs = [k for k in ("gsap", "scrollTrigger", "lenis", "locomotive", "barba", "swup", "lottie", "rive",
                               "spline", "three", "ogl", "pixi", "p5", "matter") if tech.get(k)]
    score = (2 * bool(tech.get("gsap")) + bool(tech.get("scrollTrigger")) + bool(tech.get("lenis") or tech.get("locomotive"))
             + bool(tech.get("barba") or tech.get("swup")) + 2 * webgl + bool(tech.get("lottie") or tech.get("rive"))
             + (layout.get("cssAnimations", 0) > 10) + bool(layout.get("customCursor")) + bool(rec.get("preloader"))
             + (layout.get("videos", 0) > 0) + (layout.get("mixBlend", 0) > 0) + bool(rec.get("enterGate"))
             + bool((rec.get("canvas") or {}).get("fullscreen") and not webgl))
    motion = "high" if score >= 5 else "medium" if score >= 3 else "low" if score >= 1 else "static"

    text = " ".join(filter(None, [rec.get("name"), rec.get("title"), rec.get("description")])).lower()
    roles = [r for r, p in ROLE_PATTERNS.items() if re.search(p, text)]

    kind = KIND_BY_ID.get(rec["id"])
    kind_source = "manual" if kind else "auto"
    if not kind:
        kind = "studio" if re.search(r"\b(agency|agence|studio|company|lab)\b", text) else "personal"

    hero = typo.get("hero") or {}
    hero_size = hero.get("fontSize") or 0
    return {
        "kind": kind, "kindSource": kind_source,
        "roles": roles,
        "builder": first(tech, ["framer", "webflow", "readymag", "tilda", "wordpress", "squarespace", "wix", "cargo", "shopify"], "custom-code"),
        "framework": first(tech, ["next", "nuxt", "astro", "gatsby", "sveltekit", "remix", "react", "vue", "svelte"], "vanilla/unknown"),
        "motionLibs": motion_libs,
        "motionLevel": motion, "motionScore": score,
        "webgl": webgl, "is3D": is3d,
        "typography": {
            "primaryFont": (typo.get("fonts") or [None])[0],
            "primaryFamily": norm_font((typo.get("fonts") or [None])[0]),
            "heroFamily": norm_font(hero.get("fontFamily")),
            "fonts": typo.get("fonts"), "loadedFonts": typo.get("loadedFonts"),
            "primaryClass": font_class((typo.get("fonts") or [""])[0]),
            "heroFont": hero.get("fontFamily"), "heroClass": font_class(hero.get("fontFamily")),
            "heroSizePx": hero_size,
            "heroScale": "huge" if hero_size >= 120 else "large" if hero_size >= 64 else "medium" if hero_size >= 32 else "small",
            "heroUppercase": hero.get("textTransform") == "uppercase" or (hero.get("text", "").isupper() and len(hero.get("text", "")) > 3),
            "heroText": hero.get("text"),
        },
        "layout": {
            "pageHeightScreens": layout.get("pageHeightScreens"),
            "density": "sparse" if layout.get("wordCount", 0) < 150 else "dense" if layout.get("wordCount", 0) > 1200 else "normal",
            "customCursor": layout.get("customCursor"), "preloader": rec.get("preloader"),
            "enterGate": rec.get("enterGate"),
            "smoothScroll": bool(tech.get("lenis") or tech.get("locomotive")),
            "pageTransitions": bool(tech.get("barba") or tech.get("swup")),
            "video": layout.get("videos", 0) > 0, "fullscreenCanvas": (rec.get("canvas") or {}).get("fullscreen"),
            "mixBlend": layout.get("mixBlend", 0) > 0, "glass": layout.get("backdropBlur", 0) > 0,
            "wordCount": layout.get("wordCount"), "images": layout.get("images"), "sections": layout.get("sections"),
        },
    }


def main():
    arch = json.loads((ROOT / "data/archetypes.json").read_text())
    sites = []
    for f in sorted(CRAWL.glob("*.json")):
        rec = json.loads(f.read_text())
        sid = f"{rec['id']:03d}"
        shots = {k: f"screenshots/{sid}-{k}.jpg" for k in ("gate", "desktop", "desktop-2", "mobile") if (SHOTS / f"{sid}-{k}.jpg").exists()}
        site = {"id": rec["id"], "name": rec["name"], "url": rec["url"], "finalUrl": rec.get("finalUrl"),
                "ok": rec.get("ok", False), "error": rec.get("error"), "httpStatus": rec.get("status"),
                "title": rec.get("title"), "description": rec.get("description"), "lang": rec.get("lang"),
                "screenshots": shots}
        # 站点自身不可用（限流 / 人机验证）不算有效样本
        title = (rec.get("title") or "").lower()
        if rec.get("ok") and (rec.get("status") in (403, 429) or "rate limited" in title or "challenge" in title or "just a moment" in title):
            site["ok"] = False
            site["error"] = f"blocked: HTTP {rec.get('status')} {rec.get('title')}"
        if str(rec["id"]) in arch["invalid"]:
            site["ok"] = False
            site["error"] = f"invalid: {arch['invalid'][str(rec['id'])]}"
        if site["ok"]:
            site.update(derive(rec))
            a = arch["assignments"].get(str(rec["id"]), [None])
            site["archetype"] = a[0]
            site["archetypeSecondary"] = a[1] if len(a) > 1 and a[1] != "low" else None
            site["archetypeConfidence"] = "low" if "low" in a else "high"
            shot = SHOTS / f"{sid}-desktop.jpg"
            if shot.exists():
                site["color"] = color_profile(palette(shot))
                site["color"]["cssBackground"] = (rec.get("color") or {}).get("background")
                site["color"]["cssText"] = (rec.get("color") or {}).get("text")
            site["social"] = [k for k, v in (rec.get("social") or {}).items() if v]
            site["raw"] = {"tech": [k for k, v in (rec.get("tech") or {}).items() if v],
                           "canvasContexts": rec.get("canvasContexts"), "generator": rec.get("generator"),
                           "loadMs": rec.get("loadMs"), "iframes": (rec.get("layout") or {}).get("iframes")}
        sites.append(site)

    out = {"archetypes": arch["archetypes"], "source": "RicoUI（@ricouii）《180 个优秀设计师/创意开发者个人网站清单》 https://x.com/ricouii/status/2111384617127387211",
           "count": len(sites), "okCount": sum(s["ok"] for s in sites), "sites": sites}
    (ROOT / "data/sites.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    tpl = (Path(__file__).parent / "gallery_template.html").read_text()
    embedded = json.dumps(out, ensure_ascii=False).replace("</", "<\\/")
    (ROOT / "gallery.html").write_text(tpl.replace("/*DATA*/null", embedded))
    print(f"wrote {len(sites)} sites ({out['okCount']} ok) + gallery.html")


if __name__ == "__main__":
    main()
