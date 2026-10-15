#!/usr/bin/env python3
"""Read-only frontend inventory for the consistent-web-ui skill.

Scans an explicitly chosen frontend directory and prints a compact summary, so an
agent can plan an audit without opening every file:

  * route candidates and the rule that inferred each one (file-based routers,
    router configs, theme templates, server views, plain HTML), plus layout
    shells and state screens (error, not-found, loading);
  * theme sources, custom-property tokens that are used but never defined,
    defined but never used, or defined in several files;
  * raw colour literals outside token definitions, near-duplicate colours,
    inline styles and utility-class arbitrary values;
  * value spread for spacing, font size, radius, z-index and motion durations,
    with the share of declarations that already use tokens;
  * theme-mode, motion, looping-animation and reduced-motion signals, locales,
    and detected frameworks / styling systems.

It never prints file contents - only paths, route patterns, token names, counts
and short literal values. Output is advisory: dynamic routes, runtime styles,
permissions and visual states still need inspection. Standard library only,
Python 3.8+.
"""
import argparse
import bisect
import json
import os
import re
import sys
from collections import Counter, defaultdict

# --------------------------------------------------------------------------- #
# File selection
# --------------------------------------------------------------------------- #
STYLE_EXT = {".css", ".scss", ".sass", ".less", ".styl", ".pcss", ".postcss"}
MARKUP_EXT = {".html", ".htm", ".liquid", ".php", ".phtml", ".twig", ".erb", ".hbs",
              ".handlebars", ".mustache", ".ejs", ".njk", ".pug", ".jinja", ".jinja2",
              ".cshtml", ".razor"}
COMPONENT_EXT = {".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx"}
SCRIPT_EXT = {".js", ".mjs", ".cjs", ".ts", ".mts", ".cts"}
SCAN_EXT = STYLE_EXT | MARKUP_EXT | COMPONENT_EXT | SCRIPT_EXT
JSLIKE_EXT = SCRIPT_EXT | {".jsx", ".tsx", ".vue", ".svelte", ".astro"}
PAGE_EXT = {".js", ".jsx", ".ts", ".tsx", ".mdx", ".md", ".vue", ".astro", ".svelte",
            ".html"}
ROUTE_FILE_EXT = {".js", ".jsx", ".ts", ".tsx", ".md", ".mdx"}

# Generated, vendored, test and backend folders are never entered.
SKIP_DIRS = {
    "node_modules", "bower_components", "jspm_packages", "vendor", "dist", "build", "out",
    "coverage", "storybook-static", "__pycache__", "venv", "__tests__", "__mocks__",
    "cypress", "e2e",
    # Backend boundary: this skill audits frontend code only.
    "server", "api", "db", "database", "migrations",
}
PARTIAL_DIRS = {"partials", "includes", "_includes", "components", "layouts", "_layouts",
                "snippets", "sections", "blocks", "parts", "fragments", "emails", "shared",
                "Shared"}
SKIP_NAME = re.compile(r"(\.min\.|\.d\.ts$|\.test\.|\.spec\.|\.stories\.|\.map$)")
MAX_BYTES = 512000

# --------------------------------------------------------------------------- #
# Patterns
# --------------------------------------------------------------------------- #
BLOCK_COMMENT = re.compile(r"/\*.*?\*/|<!--.*?-->", re.S)
HEX = re.compile(r"(?<![\w#&$.])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
HEX_ANCHOR_BEFORE = re.compile(
    r"(?:\b(?:href|to|xlink:href|src|action|data-target|data-bs-target|aria-controls)\s*=\s*"
    r"[\"'{]?\s*[\"'`]?|url\(\s*[\"']?)$", re.I)
HEX_SELECTOR_AFTER = re.compile(r"\s*[{:.>+~\[]")
COLOR_FN = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(\s*(?!var\()", re.I)

TOKEN_DEF = re.compile(r"(?<![\w-])(--[A-Za-z_][\w-]*)\s*:(?!:)")
TOKEN_DECL_SPAN = re.compile(r"(?<![\w-])--[A-Za-z_][\w-]*\s*:[^;{}]*")
JS_TOKEN_DEF = re.compile(r"setProperty\(\s*[\"'](--[\w-]+)[\"']|[\"'](--[A-Za-z_][\w-]*)[\"']\s*:")
TOKEN_USE = re.compile(r"(?:var|theme)\(\s*(--[A-Za-z_][\w-]*)\s*(,)?")
JS_TOKEN_READ = re.compile(r"getPropertyValue\(\s*[\"'](--[\w-]+)[\"']")
SCSS_VAR_SPAN = re.compile(r"(?m)^[ \t]*\$[A-Za-z_][\w-]*\s*:[^;]*")
LESS_VAR_SPAN = re.compile(r"(?m)^[ \t]*@[A-Za-z_][\w-]*\s*:[^;]*")
THEME_BLOCK_START = re.compile(r"@theme\b[^{;]*\{")
INLINE_STYLE = re.compile(r"(?<![\w-]):?style\s*=\s*[{\"']|\bstyle\s*:\s*\{")
TAILWIND_ENTRY_V4 = re.compile(r"@import\s+[\"']tailwindcss[\"']")
TAILWIND_ENTRY_V3 = re.compile(r"@tailwind\s+(?:base|components|utilities)\b")
THEME_OBJECT = re.compile(r"\b(?:createTheme|extendTheme|createSystem|createStitches|defineTokens|"
                          r"createGlobalTheme|createThemeContract)\s*\(")

CSS_DECL = re.compile(
    r"(?<![\w-])(margin|padding|gap|row-gap|column-gap|font-size|border-radius|z-index|"
    r"transition|animation)(-[a-z-]+)?\s*:\s*([^;{}\"'<>\n]+)", re.I)
JS_STYLE = re.compile(
    r"(?<![\w-])(margin|padding|gap|rowGap|columnGap|fontSize|borderRadius|zIndex)"
    r"(Top|Right|Bottom|Left|Inline|Block|X|Y)?\s*:\s*([\"'`]?)([^,\"'`}\n;]{1,40})\3")
LENGTH = re.compile(r"(?<![\w.#-])(-?\d*\.?\d+)(px|rem|em|%|vh|vw|ch|pt)?(?![\w(])")
TIME = re.compile(r"(?<![\w.-])(\d*\.?\d+)(ms|s)(?![\w-])")
TW_ARBITRARY = re.compile(
    r"(?<![\w-])-?(?:p|px|py|pt|pr|pb|pl|ps|pe|m|mx|my|mt|mr|mb|ml|ms|me|gap|gap-x|gap-y|"
    r"space-x|space-y|text|font|leading|tracking|rounded(?:-[a-z]{1,2})?|z|w|h|min-w|min-h|"
    r"max-w|max-h|size|top|right|bottom|left|inset|inset-x|inset-y|bg|border|ring|shadow|"
    r"duration|delay|translate-x|translate-y)-\[[^\]\s]{1,60}\]")

KEYFRAMES = re.compile(r"@(?:-webkit-)?keyframes\s+[\w-]+")
MOTION_DECL = re.compile(r"(?<![\w-])(?:transition|animation)(?:-[a-z-]+)?\s*:|\.animate\(", re.I)
INFINITE = re.compile(r"animation(?:-iteration-count)?\s*:[^;{}]*\binfinite\b|"
                      r"iterations\s*:\s*Infinity|repeat\s*:\s*Infinity", re.I)
TW_MOTION = re.compile(r"(?<![\w-])(?:transition(?:-[a-z]+)?|animate-[a-z-]+|duration-\d+|"
                       r"motion-(?:safe|reduce):[\w-]+)(?![\w-])")
TW_LOOP = re.compile(r"(?<![\w-])animate-(?:spin|ping|pulse|bounce)(?![\w-])")
WILL_CHANGE = re.compile(r"will-change\s*:|willChange\s*:")
REDUCED_MOTION = re.compile(r"prefers-reduced-motion|motion-reduce:|motion-safe:|useReducedMotion|"
                            r"reducedMotion\s*[=:]")
MODE_SIGNALS = {
    "prefers-color-scheme": re.compile(r"prefers-color-scheme"),
    "data-theme": re.compile(r"data-theme"),
    ".dark class": re.compile(r"(?<![\w-])\.dark(?![\w-])"),
    "tailwind dark:": re.compile(r"(?<![\w-])dark:[a-z\[]"),
    "data-bs-theme": re.compile(r"data-bs-theme"),
    "color-scheme property": re.compile(r"(?<![\w-])color-scheme\s*:"),
}

ROUTER_MARKER = re.compile(r"react-router|vue-router|@angular/router|RouterModule|createBrowserRouter|"
                           r"createHashRouter|createMemoryRouter|createRouter\(|<Route\b|useRoutes\(|"
                           r"wouter|@tanstack/react-router|@solidjs/router")
JSX_ROUTE_PATH = re.compile(r"<Route\b[^>]*?\bpath\s*=\s*\{?\s*[\"'`]([^\"'`]*)[\"'`]")
OBJ_ROUTE_PATH = re.compile(r"(?<![\w.])path\s*:\s*[\"'`]([^\"'`]*)[\"'`]")
ROUTE_LIKE = re.compile(r"^[\w\-/:.*\[\]()$@?~%]*$")
WP_TEMPLATE_NAME = re.compile(r"Template Name:\s*([^\n*]{1,60})")
WP_TEMPLATE = re.compile(
    r"^(index|front-page|home|singular|single(?:-[\w-]+)?|page(?:-[\w-]+)?|archive(?:-[\w-]+)?|"
    r"category(?:-[\w-]+)?|tag(?:-[\w-]+)?|taxonomy(?:-[\w-]+)?|author(?:-[\w-]+)?|date|search|404|"
    r"attachment|embed|privacy-policy)$")
LOCALE_CODE = re.compile(r"^[a-z]{2,3}(?:[-_][A-Za-z]{2,4})?$")
LOCALE_DIRS = {"locales", "locale", "i18n", "lang", "langs", "languages", "translations",
               "messages", "l10n"}
I18N_SEGMENTS = {"[locale]", "[lang]", "[lng]", "[[locale]]", "[[lang]]", ":locale", ":lang",
                 "$locale", "$lang", "{locale}", "{lang}"}

SHOPIFY_ROUTES = {
    "index": "/", "product": "/products/{handle}", "collection": "/collections/{handle}",
    "list-collections": "/collections", "cart": "/cart", "search": "/search",
    "page": "/pages/{handle}", "blog": "/blogs/{blog}", "article": "/blogs/{blog}/{article}",
    "404": "(not found)", "password": "/password", "gift_card": "(gift card)",
    "customers/account": "/account", "customers/order": "/account/orders/{id}",
    "customers/login": "/account/login", "customers/register": "/account/register",
    "customers/addresses": "/account/addresses", "customers/activate_account": "/account/activate",
    "customers/reset_password": "/account/reset",
}
WOO_ROUTES = {
    "single-product": "(product page)", "archive-product": "(shop / product archive)",
    "taxonomy-product-cat": "(product category)", "taxonomy-product-tag": "(product tag)",
    "cart/cart": "(cart)", "cart/cart-empty": "(empty cart)", "checkout/form-checkout": "(checkout)",
    "checkout/thankyou": "(order received)", "myaccount/my-account": "(my account)",
    "myaccount/orders": "(account orders)", "myaccount/view-order": "(order detail)",
    "myaccount/form-login": "(login)", "myaccount/downloads": "(downloads)",
    "myaccount/form-edit-account": "(account details)", "myaccount/my-address": "(addresses)",
    "myaccount/form-lost-password": "(lost password)",
}

PKG_GROUPS = {
    "frameworks": [
        ("next", "next"), ("nuxt", "nuxt"), ("astro", "astro"), ("@sveltejs/kit", "sveltekit"),
        ("@remix-run/react", "remix"), ("@react-router/dev", "react-router-framework"),
        ("react-router-dom", "react-router"), ("react-router", "react-router"),
        ("@tanstack/react-router", "tanstack-router"), ("@angular/core", "angular"),
        ("gatsby", "gatsby"), ("vue", "vue"), ("vue-router", "vue-router"), ("svelte", "svelte"),
        ("@solidjs/start", "solid-start"), ("solid-js", "solid"), ("@builder.io/qwik", "qwik"),
        ("preact", "preact"), ("react", "react"), ("@shopify/hydrogen", "hydrogen"),
    ],
    "styling": [
        ("tailwindcss", "tailwind"), ("bootstrap", "bootstrap"), ("@mui/material", "mui"),
        ("@chakra-ui/react", "chakra"), ("@mantine/core", "mantine"), ("antd", "antd"),
        ("styled-components", "styled-components"), ("@emotion/react", "emotion"),
        ("sass", "sass"), ("less", "less"), ("@vanilla-extract/css", "vanilla-extract"),
        ("@pandacss/dev", "panda"), ("unocss", "unocss"), ("bulma", "bulma"),
        ("@radix-ui/themes", "radix-themes"),
    ],
    "motion_libraries": [
        ("framer-motion", "framer-motion"), ("motion", "motion"), ("gsap", "gsap"),
        ("animejs", "animejs"), ("@react-spring/web", "react-spring"), ("lottie-web", "lottie"),
        ("lottie-react", "lottie"), ("@formkit/auto-animate", "auto-animate"),
    ],
    "i18n_libraries": [
        ("next-intl", "next-intl"), ("next-i18next", "next-i18next"),
        ("react-i18next", "react-i18next"), ("i18next", "i18next"), ("vue-i18n", "vue-i18n"),
        ("@nuxtjs/i18n", "nuxt-i18n"), ("svelte-i18n", "svelte-i18n"),
        ("@inlang/paraglide-js", "paraglide"), ("react-intl", "react-intl"),
        ("@lingui/core", "lingui"),
    ],
}
# Token prefixes that frameworks or libraries define at build/run time.
RUNTIME_TOKEN_PREFIXES = ("--tw-", "--radix-", "--swiper-", "--toastify-", "--rdp-")
FRAMEWORK_TOKEN_PREFIXES = {
    "bootstrap": ("--bs-",), "mui": ("--mui-",), "chakra": ("--chakra-",),
    "mantine": ("--mantine-",), "radix-themes": ("--accent-", "--gray-", "--color-"),
}
# Tokens a platform's own components read (defined by the theme, consumed outside it).
PLATFORM_CONSUMED_PREFIXES = {"shopify-theme": ("--shopify-", "--payment-terms-")}
TAILWIND4_NAMESPACES = ("--color-", "--font-", "--text-", "--tracking-", "--leading-",
                        "--breakpoint-", "--container-", "--spacing", "--radius-", "--shadow-",
                        "--inset-shadow-", "--drop-shadow-", "--blur-", "--perspective-",
                        "--aspect-", "--ease-", "--animate-", "--default-")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def join_route(segments):
    kept = [s for s in segments if s]
    return "/" + "/".join(kept)


def strip_groups(segments):
    """Drop Next.js/SvelteKit route groups and parallel-route slots."""
    return [s for s in segments if not (s.startswith("(") and s.endswith(")")) and not s.startswith("@")]


def normalize_hex(value):
    v = value.lower().lstrip("#")
    if len(v) in (3, 4):
        v = "".join(ch * 2 for ch in v)
    return "#" + v


def hex_to_rgb(value):
    v = normalize_hex(value)[1:7]
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def in_spans(position, starts, ends):
    i = bisect.bisect_right(starts, position) - 1
    return i >= 0 and position < ends[i]


def spans_of(regexes, text):
    spans = []
    for rx in regexes:
        spans.extend((m.start(), m.end()) for m in rx.finditer(text))
    spans.sort()
    return [s for s, _ in spans], [e for _, e in spans]


def block_bodies(start_rx, text):
    for m in start_rx.finditer(text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        yield text[m.end():i - 1]


def top(counter, n):
    return [[k, v] for k, v in counter.most_common(n)]


# --------------------------------------------------------------------------- #
# Framework and platform detection
# --------------------------------------------------------------------------- #
def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def detect_environment(root, all_files):
    detected = {key: set() for key in PKG_GROUPS}
    detected["platforms"] = set()
    tailwind_major = None
    names = set(all_files)
    for rel in all_files:
        base = os.path.basename(rel)
        if base == "package.json":
            data = read_json(os.path.join(root, rel)) or {}
            deps = {}
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                if isinstance(data.get(key), dict):
                    deps.update(data[key])
            for group, pairs in PKG_GROUPS.items():
                for package, label in pairs:
                    if package in deps:
                        detected[group].add(label)
            if "tailwindcss" in deps:
                digits = re.findall(r"\d+", str(deps["tailwindcss"]))
                if digits:
                    tailwind_major = max(tailwind_major or 0, int(digits[0]))
        elif base.startswith("tailwind.config."):
            detected["styling"].add("tailwind")
        elif base == "components.json":
            data = read_json(os.path.join(root, rel)) or {}
            if "ui.shadcn.com" in json.dumps(data):
                detected["styling"].add("shadcn/ui")
    if "layout/theme.liquid" in names or any(r.endswith("/layout/theme.liquid") for r in names):
        detected["platforms"].add("shopify-theme")
    wp_root = None
    for rel in all_files:
        if os.path.basename(rel) == "style.css":
            try:
                with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as handle:
                    head = handle.read(2000)
            except OSError:
                continue
            if "Theme Name:" in head:
                wp_root = os.path.dirname(rel)
                detected["platforms"].add("wordpress-theme")
                break
    if wp_root is None and "functions.php" in names and "index.php" in names:
        wp_root = ""
        detected["platforms"].add("wordpress-theme")
    if any(r.endswith("theme.json") and os.path.dirname(r) == (wp_root or "") for r in names) and wp_root is not None:
        detected["styling"].add("wordpress theme.json")
    if any("app/views/" in r and r.endswith(".erb") for r in names):
        detected["platforms"].add("rails-views")
    if any(r.endswith(".blade.php") for r in names):
        detected["platforms"].add("laravel-blade")
    if any(r.endswith(".cshtml") for r in names):
        detected["platforms"].add("aspnet-razor")
    return detected, tailwind_major, wp_root


# --------------------------------------------------------------------------- #
# Route classification (path based, runs on every walked file)
# --------------------------------------------------------------------------- #
def remix_segments(name_parts):
    out = []
    for seg in name_parts:
        if seg in ("_index", "index", "route"):
            continue
        if seg.startswith("$"):
            out.append("*" if seg == "$" else ":" + seg[1:])
        elif seg.startswith("_"):
            continue  # pathless layout segment
        elif seg.endswith("_"):
            out.append(seg[:-1])
        elif seg.startswith("(") and seg.endswith(")"):
            out.append(seg[1:-1] + "?")
        else:
            out.append(seg.replace("[", "").replace("]", ""))
    return out


def classify(rel, ctx):
    """Return (kind, route, source) or None. kind: route | shell | state."""
    parts = rel.split("/")
    dirs, filename = parts[:-1], parts[-1]
    stem, ext = os.path.splitext(filename)
    lower_dirs = [d.lower() for d in dirs]

    # SvelteKit
    if stem.startswith("+"):
        if "routes" in dirs and ext == ".svelte":
            segs = strip_groups(dirs[dirs.index("routes") + 1:])
            if stem == "+page":
                return "route", join_route(segs), "sveltekit"
            if stem == "+layout":
                return "shell", join_route(segs), "sveltekit layout"
            if stem == "+error":
                return "state", join_route(segs), "sveltekit error"
        return None

    # Next.js app router
    if "app" in dirs and ext in {".js", ".jsx", ".ts", ".tsx", ".mdx"}:
        i = dirs.index("app")
        if not (i + 1 < len(dirs) and dirs[i + 1] == "routes"):
            segs = strip_groups(dirs[i + 1:])
            if stem == "page":
                return "route", join_route(segs), "next-app"
            if stem in ("layout", "template"):
                return "shell", join_route(segs), "next-app " + stem
            if stem in ("error", "global-error", "not-found", "loading", "forbidden", "unauthorized"):
                return "state", join_route(segs), "next-app " + stem
            if stem in ("route", "default"):
                return None

    # File-based "routes" directories (Remix, React Router framework, TanStack, SolidStart)
    if "routes" in dirs and ext in ROUTE_FILE_EXT and ctx["routes_dir_enabled"]:
        i = dirs.index("routes")
        inner = dirs[i + 1:]
        if stem.startswith("-") or any(d.startswith("-") for d in inner):
            return None
        if stem in ("__root", "_root"):
            return "shell", "/", "file-routes root"
        if inner:  # folder route: only the route module counts
            if stem != "route":
                if ctx["nested_routes_dir"]:
                    name_parts = [p for d in inner for p in d.split(".")] + stem.split(".")
                    return "route", join_route(remix_segments(name_parts)), "file-routes"
                return None
            name_parts = [p for d in inner for p in d.split(".")]
        else:
            name_parts = stem.split(".")
        last = name_parts[-1] if name_parts else ""
        if last.startswith("_") and last not in ("_index",) and len(name_parts) == 1:
            return "shell", join_route(remix_segments(name_parts[:-1])), "file-routes layout"
        return "route", join_route(remix_segments(name_parts)), "file-routes"

    # pages/ directory (Next pages router, Nuxt, Astro, Gatsby, SPA page folders)
    if "pages" in dirs and ext in PAGE_EXT:
        i = dirs.index("pages")
        segs = dirs[i + 1:] + [stem]
        if stem in ("_app", "_document"):
            return "shell", "/", "pages " + stem
        if stem == "_error":
            return "state", "/", "pages _error"
        if not ctx["nuxt"] and any(s.startswith("_") for s in segs):
            return None
        segs = ["" if s == "index" else s for s in segs]
        route = join_route(strip_groups(segs))
        if stem in ("404", "500"):
            return "state", route, "pages " + stem
        return "route", route, "pages-dir"

    # Shopify theme templates
    if ctx["shopify"] and "templates" in dirs and ext in (".json", ".liquid"):
        i = dirs.index("templates")
        key = "/".join(dirs[i + 1:] + [stem])
        base = key.split(".")[0]
        route = SHOPIFY_ROUTES.get(base, "(" + base + ")")
        if key != base:
            route += " [" + key.split(".", 1)[1] + "]"
        return "route", route, "shopify-template"
    if ctx["shopify"] and "layout" in dirs and ext == ".liquid":
        return "shell", "/", "shopify layout"

    # WordPress classic / block themes and WooCommerce overrides
    if ctx["wp_root"] is not None:
        wp_rel = rel[len(ctx["wp_root"]) + 1:] if ctx["wp_root"] else rel
        wp_parts = wp_rel.split("/")
        if len(wp_parts) == 1 and ext == ".php" and WP_TEMPLATE.match(stem):
            kind = "state" if stem == "404" else "route"
            return kind, "(" + stem + ")", "wordpress-template"
        if len(wp_parts) == 1 and stem in ("header", "footer", "sidebar", "functions"):
            return ("shell", "(" + stem + ")", "wordpress-partial") if stem != "functions" else None
        if wp_parts[0] == "woocommerce" and ext == ".php":
            key = "/".join(wp_parts[1:])[:-4]
            if key in WOO_ROUTES:
                return "route", WOO_ROUTES[key], "woocommerce-template"
            return None
        if wp_parts[0] == "templates" and ext == ".html" and len(wp_parts) == 2:
            kind = "state" if stem == "404" else "route"
            return kind, "(" + stem + ")", "wordpress-block-template"
        if wp_parts[0] == "parts" and ext == ".html":
            return "shell", "(" + stem + ")", "wordpress-template-part"

    # Rails, Laravel, ASP.NET views
    if "views" in dirs and filename.endswith(".erb") and "app" in dirs:
        inner = dirs[dirs.index("views") + 1:]
        action = filename.split(".")[0]
        if "layouts" in inner:
            return "shell", "/", "rails layout"
        if action.startswith("_"):
            return None
        return "route", "/".join(inner) + "#" + action, "rails-view"
    if filename.endswith(".blade.php") and "views" in dirs:
        inner = dirs[dirs.index("views") + 1:]
        name = filename[:-len(".blade.php")]
        if "layouts" in inner:
            return "shell", "/", "blade layout"
        if name.startswith("_") or set(inner) & {"components", "partials", "includes"}:
            return None
        return "route", "view:" + ".".join(inner + [name]), "blade-view"
    if ext == ".cshtml":
        if stem.startswith("_") or "Shared" in dirs:
            return ("shell", "/", "razor layout") if stem.startswith("_Layout") else None
        if "Pages" in dirs:
            segs = dirs[dirs.index("Pages") + 1:] + ["" if stem == "Index" else stem]
            return "route", join_route(segs), "razor-page"
        if "Views" in dirs:
            inner = dirs[dirs.index("Views") + 1:]
            return "route", "/".join(inner + [stem]), "mvc-view"

    # Layout folders of other frameworks
    if ("layouts" in lower_dirs or "_layouts" in lower_dirs) and ext in (COMPONENT_EXT | MARKUP_EXT):
        return "shell", "/", "layout file"

    # Plain HTML documents and server templates
    if ext in (".html", ".htm"):
        if set(dirs) & PARTIAL_DIRS or stem.startswith("_"):
            return None
        segs = dirs + ([] if stem == "index" else [stem])
        source = "html-template" if "templates" in dirs else "html-file"
        if stem in ("404", "500", "offline"):
            return "state", join_route(segs), source
        return "route", join_route(segs), source
    return None


# --------------------------------------------------------------------------- #
# Main scan
# --------------------------------------------------------------------------- #
def walk(root, extra_skips):
    skips = SKIP_DIRS | set(extra_skips)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skips and not d.startswith("."))
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                real = os.path.realpath(full)
                if os.path.commonpath([real, root]) != root:
                    continue
            yield os.path.relpath(full, root).replace(os.sep, "/")


def census_css_value(category, value, census):
    value = value.strip()
    uses_token = "var(" in value or "theme(" in value
    bucket = census[category]
    bucket["declarations"] += 1
    if uses_token:
        bucket["tokenized"] += 1
        return
    if category == "z-index":
        match = re.match(r"-?\d+", value)
        if match:
            bucket["values"][match.group(0)] += 1
        return
    if category == "duration":
        for number, unit in TIME.findall(value):
            ms = float(number) * (1000 if unit == "s" else 1)
            bucket["values"][("%g" % ms) + "ms"] += 1
        return
    if category == "font-size" and value.startswith(("clamp(", "min(", "max(", "calc(")):
        bucket["values"][value.split("(")[0] + "(...)"] += 1
        return
    for number, unit in LENGTH.findall(value):
        if float(number) == 0:
            continue
        bucket["values"][number + (unit or "")] += 1


def scan(root, max_files, extra_skips):
    all_files = list(walk(root, extra_skips))
    detected, tailwind_major, wp_root = detect_environment(root, all_files)
    frameworks = detected["frameworks"]
    ctx = {
        "nuxt": "nuxt" in frameworks,
        "shopify": "shopify-theme" in detected["platforms"],
        "wp_root": wp_root,
        "routes_dir_enabled": bool(frameworks & {"remix", "react-router-framework", "tanstack-router",
                                                 "solid-start"}) or any("app/routes/" in f for f in all_files),
        "nested_routes_dir": bool(frameworks & {"tanstack-router", "solid-start"}),
    }
    if tailwind_major and tailwind_major >= 4:
        detected["styling"].add("tailwind-v4")

    routes, shells, states = [], [], []
    locales, i18n_route_param = set(), False
    for rel in all_files:
        result = classify(rel, ctx)
        if result:
            kind, route, source = result
            entry = {"route": route, "file": rel, "source": source}
            (routes if kind == "route" else shells if kind == "shell" else states).append(entry)
        parts = rel.split("/")
        if set(parts[:-1]) & I18N_SEGMENTS:
            i18n_route_param = True
        if set(d.lower() for d in parts[:-1]) & LOCALE_DIRS:
            base = parts[-1].split(".")[0]
            if LOCALE_CODE.match(base) and base != "index":
                locales.add(base)

    scan_files = [f for f in all_files
                  if os.path.splitext(f)[1].lower() in SCAN_EXT and not SKIP_NAME.search(os.path.basename(f))]
    truncated = len(scan_files) > max_files
    scan_files = scan_files[:max_files]

    counts = Counter()
    skipped_large = 0
    token_defs = defaultdict(set)
    theme_block_tokens = set()
    token_uses = Counter()
    uses_without_fallback = set()
    js_reads = set()
    preprocessor_vars = Counter()
    theme_sources = []
    color_rows, raw_hex_counter = [], Counter()
    totals = Counter()
    census = defaultdict(lambda: {"declarations": 0, "tokenized": 0, "values": Counter()})
    tw_arbitrary, tw_examples = Counter(), Counter()
    loop_files, will_change_files, mode_counts = [], [], Counter()
    motion_files = 0

    for rel in scan_files:
        path = os.path.join(root, rel)
        try:
            if os.path.getsize(path) > MAX_BYTES:
                skipped_large += 1
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                raw = handle.read()
        except OSError:
            continue
        ext = os.path.splitext(rel)[1].lower()
        base = os.path.basename(rel)
        counts[ext] += 1
        text = BLOCK_COMMENT.sub(" ", raw)
        is_theme_file = (base.startswith("tailwind.config.") or bool(THEME_OBJECT.search(text)))

        # tokens
        defs_here = TOKEN_DEF.findall(text)
        for token in defs_here:
            token_defs[token].add(rel)
        if ext in JSLIKE_EXT:
            for a, b in JS_TOKEN_DEF.findall(text):
                token_defs[a or b].add(rel)
            js_reads.update(JS_TOKEN_READ.findall(text))
        for body in block_bodies(THEME_BLOCK_START, text):
            theme_block_tokens.update(TOKEN_DEF.findall(body))
        for token, fallback in TOKEN_USE.findall(text):
            token_uses[token] += 1
            if not fallback:
                uses_without_fallback.add(token)
        pre_spans = []
        if ext in (".scss", ".sass"):
            pre_spans = [SCSS_VAR_SPAN]
            preprocessor_vars["sass"] += len(SCSS_VAR_SPAN.findall(text))
        elif ext == ".less":
            pre_spans = [LESS_VAR_SPAN]
            preprocessor_vars["less"] += len(LESS_VAR_SPAN.findall(text))

        reasons = []
        if len(set(defs_here)) >= 3:
            reasons.append("%d custom properties" % len(set(defs_here)))
        if THEME_BLOCK_START.search(text):
            reasons.append("tailwind @theme block")
        if base.startswith("tailwind.config."):
            reasons.append("tailwind config")
        if THEME_OBJECT.search(text):
            reasons.append("theme object")
        if pre_spans and len(pre_spans[0].findall(text)) >= 3:
            reasons.append("%d preprocessor variables" % len(pre_spans[0].findall(text)))
        if TAILWIND_ENTRY_V4.search(text):
            detected["styling"].add("tailwind-v4")
            reasons.append("tailwind entry (default theme unless @theme overrides)")
        elif TAILWIND_ENTRY_V3.search(text):
            reasons.append("tailwind entry (theme in tailwind.config)")
        placeholders = raw.count("TODO(brand)")
        if placeholders:
            reasons.append("%d unfinished TODO(brand) values" % placeholders)
        if reasons:
            theme_sources.append({"file": rel, "reasons": reasons, "weight": len(set(defs_here))})

        # colours
        starts, ends = spans_of([TOKEN_DECL_SPAN] + pre_spans, text)
        raw_hex = raw_fn = in_tokens = 0
        for m in HEX.finditer(text):
            before = text[max(0, m.start() - 40):m.start()]
            if HEX_ANCHOR_BEFORE.search(before) or HEX_SELECTOR_AFTER.match(text, m.end()):
                continue
            if is_theme_file or in_spans(m.start(), starts, ends):
                in_tokens += 1
            else:
                raw_hex += 1
                raw_hex_counter[normalize_hex(m.group(0))] += 1
        for m in COLOR_FN.finditer(text):
            if is_theme_file or in_spans(m.start(), starts, ends):
                in_tokens += 1
            else:
                raw_fn += 1
        inline = len(INLINE_STYLE.findall(text)) if ext not in STYLE_EXT else 0
        totals["raw_hex"] += raw_hex
        totals["raw_functions"] += raw_fn
        totals["in_token_definitions"] += in_tokens
        totals["inline_styles"] += inline
        if raw_hex or raw_fn or inline:
            color_rows.append({"file": rel, "raw_hex": raw_hex, "raw_functions": raw_fn,
                               "inline_styles": inline})

        # value census
        if not is_theme_file:
            for prop, _suffix, value in CSS_DECL.findall(text):
                prop = prop.lower()
                if prop in ("transition", "animation"):
                    census_css_value("duration", value, census)
                elif prop in ("margin", "padding", "gap", "row-gap", "column-gap"):
                    census_css_value("spacing", value, census)
                else:
                    census_css_value(prop, value, census)
            if ext in JSLIKE_EXT:
                for prop, _side, _quote, value in JS_STYLE.findall(text):
                    category = {"fontSize": "font-size", "borderRadius": "border-radius",
                                "zIndex": "z-index"}.get(prop, "spacing")
                    value = value.strip()
                    if re.fullmatch(r"-?\d*\.?\d+", value):
                        value = value if category == "z-index" else value + "px"
                        census_css_value(category, value, census)
                    elif LENGTH.fullmatch(value) or value.startswith("var("):
                        census_css_value(category, value, census)
        if ext not in STYLE_EXT:
            for m in TW_ARBITRARY.finditer(text):
                tw_arbitrary[rel] += 1
                tw_examples[m.group(0)] += 1

        # motion and modes
        has_motion = bool(KEYFRAMES.search(text) or MOTION_DECL.search(text)
                          or (ext not in STYLE_EXT and TW_MOTION.search(text)))
        motion_files += has_motion
        totals["keyframes"] += len(KEYFRAMES.findall(text))
        loops = len(INFINITE.findall(text)) + len(TW_LOOP.findall(text))
        if loops:
            loop_files.append([rel, loops])
        will = len(WILL_CHANGE.findall(text))
        if will:
            will_change_files.append([rel, will])
        totals["reduced_motion_guards"] += len(REDUCED_MOTION.findall(text))
        for label, rx in MODE_SIGNALS.items():
            mode_counts[label] += len(rx.findall(text))

        # router configs (content based)
        if ext in JSLIKE_EXT and ROUTER_MARKER.search(text):
            found = JSX_ROUTE_PATH.findall(text) + OBJ_ROUTE_PATH.findall(text)
            for value in dict.fromkeys(found):
                if len(value) <= 120 and ROUTE_LIKE.match(value) and "." not in value.split("/")[-1][:1]:
                    route = value if value else "(index)"
                    kind = "state" if value in ("*", "**", "/*") else "route"
                    (routes if kind == "route" else states).append(
                        {"route": route, "file": rel, "source": "router-config"})
        if ext == ".php" and ctx["wp_root"] is not None:
            name = WP_TEMPLATE_NAME.search(raw)  # the header lives inside a comment
            if name:
                routes.append({"route": "(template: " + name.group(1).strip() + ")", "file": rel,
                               "source": "wordpress-page-template"})

    # token analysis
    styling = detected["styling"]
    ignored_prefixes = list(RUNTIME_TOKEN_PREFIXES)
    for label, prefixes in FRAMEWORK_TOKEN_PREFIXES.items():
        if label in styling:
            ignored_prefixes.extend(prefixes)
    if "tailwind-v4" in styling:
        ignored_prefixes.extend(TAILWIND4_NAMESPACES)
    undefined = Counter({t: n for t, n in token_uses.items()
                         if t not in token_defs and t in uses_without_fallback
                         and not t.startswith(tuple(ignored_prefixes))})
    undefined_with_fallback = sum(1 for t in token_uses if t not in token_defs and t not in uses_without_fallback)
    consumed = tuple(p for label, prefixes in PLATFORM_CONSUMED_PREFIXES.items()
                     if label in detected["platforms"] for p in prefixes)
    unused = sorted(t for t in token_defs
                    if t not in token_uses and t not in js_reads
                    and not (consumed and t.startswith(consumed))
                    and not ("tailwind-v4" in styling and t in theme_block_tokens))
    multi = sorted(([t, len(f)] for t, f in token_defs.items() if len(f) > 1), key=lambda x: (-x[1], x[0]))

    # near-duplicate raw colours
    distinct = [c for c, _ in raw_hex_counter.most_common(60)]
    near = []
    for i, a in enumerate(distinct):
        for b in distinct[i + 1:]:
            ra, rb = hex_to_rgb(a), hex_to_rgb(b)
            distance = sum((x - y) ** 2 for x, y in zip(ra, rb)) ** 0.5
            if 0 < distance <= 12:
                near.append([a, b])
    theme_sources.sort(key=lambda s: (-(("tailwind @theme block" in s["reasons"]) or ("tailwind config" in s["reasons"])
                                        or ("theme object" in s["reasons"])), -s["weight"], s["file"]))

    def census_out(name):
        bucket = census[name]
        total = bucket["declarations"]
        return {"declarations": total, "tokenized": bucket["tokenized"],
                "tokenized_share": round(bucket["tokenized"] / total, 2) if total else None,
                "distinct_raw_values": len(bucket["values"]), "top_raw_values": top(bucket["values"], 12)}

    route_limit = 200
    return {
        "scan_root": root,
        "files_walked": len(all_files),
        "analyzed_files": sum(counts.values()),
        "file_types": dict(sorted(counts.items())),
        "content_scan_truncated": truncated,
        "skipped_large_files": skipped_large,
        "detected": {k: sorted(v) for k, v in detected.items()},
        "routes": {"count": len(routes), "by_source": dict(Counter(r["source"] for r in routes)),
                   "items": routes[:route_limit], "truncated": len(routes) > route_limit},
        "shells": shells[:60],
        "states": states[:60],
        "locales": sorted(locales),
        "i18n_route_param": i18n_route_param,
        "theme_sources": [{"file": s["file"], "reasons": s["reasons"]} for s in theme_sources[:12]],
        "tokens": {
            "defined": len(token_defs), "referenced": len(token_uses),
            "undefined_without_fallback": top(undefined, 30),
            "undefined_with_fallback_count": undefined_with_fallback,
            "possibly_unused_count": len(unused), "possibly_unused": unused[:30],
            "defined_in_several_files": multi[:25],
            "preprocessor_variables": dict(preprocessor_vars),
        },
        "colors": {
            "raw_hex": totals["raw_hex"], "raw_functions": totals["raw_functions"],
            "in_token_or_theme_definitions": totals["in_token_definitions"],
            "distinct_raw_hex": len(raw_hex_counter), "most_used_raw_hex": top(raw_hex_counter, 12),
            "near_duplicate_raw_hex": near[:12],
            "top_files": sorted(color_rows, key=lambda r: (-(r["raw_hex"] + r["raw_functions"] + r["inline_styles"]),
                                                           r["file"]))[:25],
        },
        "inline_styles": totals["inline_styles"],
        "values": {name: census_out(name) for name in ("spacing", "font-size", "border-radius", "z-index", "duration")},
        "utility_arbitrary_values": {"count": sum(tw_arbitrary.values()), "top_files": top(tw_arbitrary, 10),
                                     "examples": [k for k, _ in tw_examples.most_common(10)]},
        "motion": {"files_with_motion": motion_files, "keyframes": totals["keyframes"],
                   "looping_animation_files": sorted(loop_files, key=lambda x: -x[1])[:15],
                   "will_change_files": will_change_files[:15],
                   "reduced_motion_guards": totals["reduced_motion_guards"]},
        "theme_mode_signals": {k: v for k, v in mode_counts.items() if v},
        "warning": ("Heuristic inventory. Confirm routes against the router and navigation, inspect runtime "
                    "styles and visual states, and treat literals as leads, not automatic errors."),
    }


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def fmt_pairs(pairs, suffix="×"):
    return ", ".join("%s %s%s" % (k, suffix, v) for k, v in pairs)


def render_text(r):
    out = []
    add = out.append
    add("Frontend inventory (read-only, advisory) - %s" % r["scan_root"])
    add("Files: %d walked, %d analyzed %s; large skipped %d%s" % (
        r["files_walked"], r["analyzed_files"],
        "(" + ", ".join("%s %d" % kv for kv in r["file_types"].items()) + ")" if r["file_types"] else "",
        r["skipped_large_files"], "; CONTENT SCAN TRUNCATED (raise --max-files)" if r["content_scan_truncated"] else ""))
    d = r["detected"]
    add("Detected: " + "; ".join("%s: %s" % (k, ", ".join(v)) for k, v in d.items() if v) if any(d.values())
        else "Detected: no framework signals")
    rt = r["routes"]
    add("")
    add("Routes: %d (%s)%s" % (rt["count"], ", ".join("%s %d" % kv for kv in sorted(rt["by_source"].items())),
                               " - list truncated" if rt["truncated"] else ""))
    for item in rt["items"]:
        add("  %-36s %s  [%s]" % (item["route"], item["file"], item["source"]))
    if r["shells"]:
        add("Shells: " + "; ".join("%s (%s)" % (s["file"], s["source"]) for s in r["shells"][:20]))
    if r["states"]:
        add("States: " + "; ".join("%s %s (%s)" % (s["file"], s["route"], s["source"]) for s in r["states"][:20]))
    if r["locales"] or r["i18n_route_param"]:
        add("Locales: %s%s" % (", ".join(r["locales"]) or "-",
                               "; locale route parameter present" if r["i18n_route_param"] else ""))
    add("")
    add("Theme sources:" if r["theme_sources"] else "Theme sources: none found (no central token file)")
    for s in r["theme_sources"]:
        add("  %s - %s" % (s["file"], ", ".join(s["reasons"])))
    t = r["tokens"]
    add("Tokens: %d defined, %d referenced; preprocessor variables %s" % (
        t["defined"], t["referenced"], t["preprocessor_variables"] or "-"))
    if t["undefined_without_fallback"]:
        add("  used but never defined (no fallback): " + fmt_pairs(t["undefined_without_fallback"]))
    if t["undefined_with_fallback_count"]:
        add("  used but never defined (with fallback): %d" % t["undefined_with_fallback_count"])
    if t["possibly_unused"]:
        add("  defined but never referenced (%d): %s" % (t["possibly_unused_count"], ", ".join(t["possibly_unused"])))
    if t["defined_in_several_files"]:
        add("  defined in several files: " + ", ".join("%s (%d files)" % tuple(x) for x in t["defined_in_several_files"]))
    c = r["colors"]
    add("")
    add("Colours: %d raw hex + %d raw colour functions outside tokens; %d inside token/theme definitions; "
        "%d distinct raw hex" % (c["raw_hex"], c["raw_functions"], c["in_token_or_theme_definitions"], c["distinct_raw_hex"]))
    if c["most_used_raw_hex"]:
        add("  most used raw: " + fmt_pairs(c["most_used_raw_hex"]))
    if c["near_duplicate_raw_hex"]:
        add("  near-duplicates: " + ", ".join("%s~%s" % tuple(p) for p in c["near_duplicate_raw_hex"]))
    for row in c["top_files"][:12]:
        add("  %s: hex %d, functions %d, inline styles %d" % (row["file"], row["raw_hex"], row["raw_functions"],
                                                             row["inline_styles"]))
    add("Inline styles: %d" % r["inline_styles"])
    for name, v in r["values"].items():
        if not v["declarations"]:
            continue
        add("%s: %d declarations, %d%% via tokens, %d distinct raw values%s" % (
            name.capitalize(), v["declarations"], round(100 * (v["tokenized_share"] or 0)), v["distinct_raw_values"],
            (" (" + fmt_pairs(v["top_raw_values"]) + ")") if v["top_raw_values"] else ""))
    u = r["utility_arbitrary_values"]
    if u["count"]:
        add("Utility arbitrary values: %d (e.g. %s)" % (u["count"], ", ".join(u["examples"][:6])))
    m = r["motion"]
    add("")
    add("Motion: %d files, %d keyframes, %d reduced-motion guards" % (
        m["files_with_motion"], m["keyframes"], m["reduced_motion_guards"]))
    if m["looping_animation_files"]:
        add("  looping animations: " + ", ".join("%s ×%d" % tuple(x) for x in m["looping_animation_files"]))
    if m["will_change_files"]:
        add("  will-change: " + ", ".join("%s ×%d" % tuple(x) for x in m["will_change_files"]))
    if r["theme_mode_signals"]:
        add("Theme modes: " + ", ".join("%s %d" % kv for kv in r["theme_mode_signals"].items()))
    add("")
    add(r["warning"])
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compact, read-only frontend inventory")
    parser.add_argument("--root", required=True, help="Explicit frontend source directory")
    parser.add_argument("--max-files", type=int, default=4000, help="Content-scan file limit (routes use every file)")
    parser.add_argument("--exclude", action="append", default=[], metavar="DIR",
                        help="Extra directory name to skip; repeatable")
    parser.add_argument("--json", action="store_true", help="Emit full JSON instead of the compact text summary")
    args = parser.parse_args(argv)
    root = os.path.realpath(args.root)
    if not os.path.isdir(root) or args.max_files < 1:
        parser.error("choose an existing frontend directory and a positive --max-files")
    result = scan(root, args.max_files, args.exclude)
    if args.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
