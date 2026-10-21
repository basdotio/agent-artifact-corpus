"""
Módulo de Inteligencia, Copywriting y Heurística Anti-IA para LinkedIn (MCP Linkedin).
Inspirado y adaptado del benchmark de Jakeschincariol/linkedin-agent-skill.
Implementación 100% nativa en Python stdlib, sin dependencias externas pesadas.
"""

import os
import re
import json
import statistics
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

DATA_DIR = Path(__file__).parent / "data"
SLOP_FILE = DATA_DIR / "slop.json"
HOOKS_FILE = DATA_DIR / "hooks.json"
RUBRIC_FILE = DATA_DIR / "rubric.json"

URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+\.\S+")
SENT_RE = re.compile(r"[^.!?\n]+[.!?]*")
WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúñÑ']+")
CONTRACTIONS_EN = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
PRONOUNS = re.compile(r"\b(i|me|my|mine|we|us|our|you|your|yo|mí|mi|mis|nosotros|nosotras|nuestro|nuestra|nuestros|nuestras|tú|te|tu|tus|usted|ustedes)\b", re.IGNORECASE)
NUMBERS = re.compile(r"\b\d[\d,.]*%?\b|[\$€£]\s*\d")
PROPER = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}\b", re.MULTILINE)

# Slop léxico bilingüe adicional para LinkedIn en español
SPANISH_SLOP_ADDITIONS = [
    {"find": "en el vertiginoso mundo actual", "replace": "hoy en día", "family": "openers"},
    {"find": "en la era digital actual", "replace": "actualmente", "family": "openers"},
    {"find": "en el cambiante mundo de", "replace": "en", "family": "openers"},
    {"find": "profundizar en", "replace": "analizar", "family": "verbs"},
    {"find": "inmersión profunda", "replace": "análisis detallado", "family": "nouns"},
    {"find": "apalancar", "replace": "aprovechar", "family": "verbs"},
    {"find": "apalancando", "replace": "aprovechando", "family": "verbs"},
    {"find": "sin fisuras", "replace": "fluido", "family": "adjectives"},
    {"find": "punta de lanza", "replace": "referente", "family": "nouns"},
    {"find": "cambio de juego", "replace": "hito decisivo", "family": "nouns"},
    {"find": "cambiador de juego", "replace": "innovación clave", "family": "nouns"},
    {"find": "a la vanguardia", "replace": "actualizado", "family": "adjectives"},
    {"find": "revolucionario", "replace": "nuevo", "family": "adjectives"},
    {"find": "testimonio de", "replace": "prueba de", "family": "nouns"},
    {"find": "dejar que eso se asiente", "replace": "", "family": "closers"},
    {"find": "¿cuáles son tus pensamientos?", "replace": "", "family": "closers"},
    {"find": "¿qué opinas al respecto?", "replace": "", "family": "closers"},
    {"find": "estoy emocionado de compartir", "replace": "comparto", "family": "openers"},
    {"find": "me siento honrado de", "replace": "", "family": "openers"},
]


def _load_json_data(file_path: Path) -> dict:
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_slop_data() -> dict:
    data = _load_json_data(SLOP_FILE)
    if "words" in data and "phrases" in data:
        # Enriquecer con frases en español si no existen ya
        existing_finds = {w["find"].lower() for w in (data["words"] + data["phrases"])}
        for item in SPANISH_SLOP_ADDITIONS:
            if item["find"].lower() not in existing_finds:
                if " " in item["find"]:
                    data["phrases"].append(item)
                else:
                    data["words"].append(item)
    return data


def get_hooks_data() -> dict:
    return _load_json_data(HOOKS_FILE)


def get_rubric_data() -> dict:
    return _load_json_data(RUBRIC_FILE)


def _cp(spec: str):
    """'U+200B' -> 0x200B;  'U+E0000-U+E007F' -> (start, end)."""
    if "-" in spec:
        a, b = spec.split("-")
        return (int(a[2:], 16), int(b[2:], 16))
    return int(spec[2:], 16)


def protect_urls(text: str) -> Tuple[str, List[str]]:
    found = []

    def stash(m):
        found.append(m.group(0))
        return f"\x00URL{len(found) - 1}\x00"

    return URL_RE.sub(stash, text), found


def restore_urls(text: str, found: List[str]) -> str:
    for i, url in enumerate(found):
        text = text.replace(f"\x00URL{i}\x00", url)
    return text


def _match_case(src: str, repl: str) -> str:
    if not repl:
        return repl
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def pass_invisible(text: str, lex: dict) -> Tuple[str, List[dict]]:
    hits = []
    for entry in lex.get("invisible", []):
        cp = _cp(entry["cp"])
        if isinstance(cp, tuple):
            pattern = "[" + re.escape(chr(cp[0])) + "-" + re.escape(chr(cp[1])) + "]"
        else:
            pattern = re.escape(chr(cp))
        n = len(re.findall(pattern, text))
        if n:
            hits.append({
                "name": entry["cp"] + " " + entry["name"],
                "count": n,
                "action": entry["action"]
            })
            text = re.sub(pattern, "" if entry["action"] == "delete" else " ", text)
    stray = [c for c in text if unicodedata.category(c) == "Cf"]
    if stray:
        hits.append({
            "name": "other invisible format chars",
            "count": len(stray),
            "action": "delete"
        })
        text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return text, hits


def pass_typographic(text: str, lex: dict) -> Tuple[str, List[dict]]:
    hits = []
    for entry in lex.get("typographic", []):
        ch = entry["from"]
        n = text.count(ch)
        if not n:
            continue
        hits.append({
            "name": f"{ch} {entry['name']}",
            "count": n,
            "to": entry["to"].strip() or "(space)"
        })
        if ch == "—":
            text = re.sub(r"\s*—\s*", ", ", text)
        elif ch == "–":
            text = re.sub(r"\s*–\s*(?=\d)", "-", text)
            text = re.sub(r"\s+–\s+", ", ", text)
            text = text.replace("–", "-")
        else:
            text = text.replace(ch, entry["to"])
    text = re.sub(r",\s*([,.;:!?])", r"\1", text)
    text = re.sub(r",\s*\n", "\n", text)
    return text, hits


def pass_lexical(text: str, lex: dict) -> Tuple[str, List[dict]]:
    hits = []
    entries = sorted(lex.get("phrases", []) + lex.get("words", []),
                     key=lambda e: len(e["find"]), reverse=True)
    for entry in entries:
        find = entry["find"]
        pattern = re.compile(r"\b" + re.escape(find).replace(r"\ ", r"\s+") + r"\b", re.IGNORECASE)
        found = pattern.findall(text)
        if not found:
            continue
        hits.append({
            "find": find,
            "replace": entry["replace"] or "(deleted)",
            "count": len(found),
            "family": entry.get("family", "general")
        })
        text = pattern.sub(lambda m: _match_case(m.group(0), entry["replace"]), text)

    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"(?m)^[ \t]*([,.;:])\s*", "", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(
        r",\s*(also|so|still|basically|in the end|también|por tanto|básicamente|al final)\s*,\s*",
        lambda m: ". " + m.group(1)[0].upper() + m.group(1)[1:] + ", ",
        text,
        flags=re.IGNORECASE
    )
    return text, hits


def scan_structures(text: str, lex: dict) -> List[dict]:
    flags = []
    for s in lex.get("structures", []):
        try:
            pattern = re.compile(s["regex"], re.MULTILINE)
        except re.error:
            continue
        found = pattern.findall(text)
        if found:
            flags.append({
                "name": s["name"],
                "count": len(found),
                "fix": s["fix"]
            })
    lens = [len(s.split()) for s in SENT_RE.findall(text) if len(s.split()) > 2]
    if len(lens) >= 4:
        mean = sum(lens) / len(lens)
        var = sum((n - mean) ** 2 for n in lens) / len(lens)
        cv = (var ** 0.5) / mean if mean else 0
        if cv < 0.35:
            flags.append({
                "name": f"Longitud de oraciones uniforme (variación {cv:.2f})",
                "count": len(lens),
                "fix": "Divide una oración a la mitad y alarga otra. Los textos de IA son excesivamente uniformes."
            })
    return flags


def humanize_text(text: str) -> Tuple[str, dict]:
    """
    Limpia el texto en 3 pasadas (invisibles, tipografía, léxico) y detecta estructuras típicas de IA.
    """
    lex = get_slop_data()
    protected_text, urls = protect_urls(text)
    clean_text, inv = pass_invisible(protected_text, lex)
    clean_text, typo = pass_typographic(clean_text, lex)
    clean_text, lexi = pass_lexical(clean_text, lex)
    clean_text = restore_urls(clean_text, urls).strip() + "\n"

    report = {
        "invisible_count": sum(h["count"] for h in inv),
        "invisible_hits": inv,
        "typographic_count": sum(h["count"] for h in typo),
        "typographic_hits": typo,
        "lexical_count": sum(h["count"] for h in lexi),
        "lexical_hits": lexi,
        "structural_tells": scan_structures(clean_text, lex),
        "total_artefacts_removed": sum(h["count"] for h in inv) + sum(h["count"] for h in typo) + sum(h["count"] for h in lexi)
    }
    return clean_text, report


def _clamp(n: float) -> float:
    return max(0.0, min(100.0, n))


def _scale(value: float, human: float, machine: float) -> float:
    if human == machine:
        return 50.0
    return _clamp((value - machine) / (human - machine) * 100)


def detect_ai_markers(text: str) -> dict:
    """
    Panel heurístico de 5 verificaciones (Burstiness, Specificity, Slop Density, Fingerprint, Voice).
    Devuelve puntuación humana (0-100) y veredicto ('PASS', 'REVIEW', 'FLAGGED').
    """
    lex = get_slop_data()
    w = WORD_RE.findall(text)
    sents = [s.strip() for s in SENT_RE.findall(text) if len(s.split()) > 2]

    # 1. Burstiness
    if len(sents) < 4:
        score_burst = 50.0
        detail_burst = "Texto demasiado corto para juzgar ritmo de oraciones (< 4 oraciones)."
    else:
        lens = [len(s.split()) for s in sents]
        mean = statistics.mean(lens)
        cv = statistics.pstdev(lens) / mean if mean else 0
        score_burst = _scale(cv, human=0.70, machine=0.22)
        detail_burst = f"Variación de longitud: {cv:.2f} en {len(lens)} oraciones (óptimo: 0.55+)."

    # 2. Specificity
    if len(w) < 20:
        score_spec = 50.0
        detail_spec = "Texto breve (< 20 palabras)."
    else:
        per100 = 100 / len(w)
        hits_num = len(NUMBERS.findall(text))
        hits_prop = len(set(PROPER.findall(text)))
        tot_hits = hits_num + hits_prop
        density_spec = tot_hits * per100
        score_spec = _scale(density_spec, human=6.0, machine=0.5)
        detail_spec = f"{tot_hits} marcadores concretos (números/nombres), {density_spec:.1f} por 100 palabras."

    # 3. Slop Density
    if not w:
        score_slop = 50.0
        detail_slop = "Texto vacío."
    else:
        hits_slop, found_slop = 0, []
        for entry in lex.get("words", []) + lex.get("phrases", []):
            pattern = re.compile(r"\b" + re.escape(entry["find"]).replace(r"\ ", r"\s+") + r"\b", re.IGNORECASE)
            n = len(pattern.findall(text))
            if n:
                hits_slop += n
                found_slop.append(entry["find"])
        density_slop = hits_slop * 100 / len(w)
        score_slop = _scale(density_slop, human=0.0, machine=4.0)
        detail_slop = f"{hits_slop} términos cliché identificados ({density_slop:.1f} por 100 palabras)."
        if found_slop:
            detail_slop += f" [{', '.join(sorted(found_slop)[:5])}]"

    # 4. Fingerprint
    invisible_cnt = sum(1 for c in text if unicodedata.category(c) == "Cf")
    em_cnt = text.count("—")
    curly_cnt = sum(text.count(c) for c in "‘’“”")
    ellip_cnt = text.count("…")
    nbsp_cnt = sum(text.count(c) for c in "   ")
    total_fingerprint = invisible_cnt * 4 + em_cnt * 2 + curly_cnt + ellip_cnt + nbsp_cnt
    per1k = total_fingerprint * 1000 / max(len(text), 1)
    score_fingerprint = _scale(per1k, human=0.0, machine=12.0)
    detail_fingerprint = f"{invisible_cnt} invisibles, {em_cnt} guiones em, {curly_cnt} comillas tipográficas, {nbsp_cnt} espacios no separables."

    # 5. Voice
    if len(w) < 20:
        score_voice = 50.0
        detail_voice = "Texto breve (< 20 palabras)."
    else:
        per100 = 100 / len(w)
        is_spanish = bool(re.search(r"[áéíóúñÁÉÍÓÚÑ]|\b(de|en|el|la|los|las|por|con|para)\b", text, re.IGNORECASE))
        if is_spanish:
            es_contractions = len(re.findall(r"\b(al|del)\b", text, re.IGNORECASE)) * per100
            pronouns_cnt = len(re.findall(r"\b(yo|tú|él|ella|nosotros|nosotras|me|te|se|nos|os|le|les|mi|mis|tu|tus|su|sus|mío|mía|nuestro|nuestra)\b", text, re.IGNORECASE)) * per100
            contr_score = _scale(es_contractions, human=2.0, machine=0.0)
        else:
            contractions_cnt = len(CONTRACTIONS_EN.findall(text)) * per100
            pronouns_cnt = len(PRONOUNS.findall(text)) * per100
            contr_score = _scale(contractions_cnt, human=3.0, machine=0.0)

        struct_tells = 0
        tell_names = []
        for s in lex.get("structures", []):
            try:
                n = len(re.compile(s["regex"], re.MULTILINE).findall(text))
            except re.error:
                continue
            if n:
                struct_tells += n
                tell_names.append(s["id"])

        bullets = [len(b.split()) for b in re.findall(r"(?m)^\s*[-*•]\s+(.+)$", text)]
        uniform_bullets = (len(bullets) >= 3 and statistics.pstdev(bullets) < 1.6)
        score_voice = (contr_score * 0.25
                       + _scale(pronouns_cnt, human=6.0, machine=0.5) * 0.35
                       + _clamp(100 - struct_tells * 22) * 0.40)
        if uniform_bullets:
            score_voice -= 12
            tell_names.append("viñetas-uniformes")
        score_voice = _clamp(score_voice)
        detail_voice = f"{pronouns_cnt:.1f} pronombres personales/100 pal, {struct_tells} estructuras cliché."
        if tell_names:
            detail_voice += f" [{', '.join(tell_names[:4])}]"

    checks = {
        "BURSTINESS": {"score": round(score_burst, 1), "detail": detail_burst},
        "SPECIFICITY": {"score": round(score_spec, 1), "detail": detail_spec},
        "SLOP_DENSITY": {"score": round(score_slop, 1), "detail": detail_slop},
        "FINGERPRINT": {"score": round(score_fingerprint, 1), "detail": detail_fingerprint},
        "VOICE": {"score": round(score_voice, 1), "detail": detail_voice}
    }

    scores = [v["score"] for v in checks.values()]
    overall = round(statistics.mean(scores) * 0.6 + min(scores) * 0.4, 1)
    verdict = "PASS" if overall >= 70 and min(scores) >= 55 else ("REVIEW" if overall >= 50 else "FLAGGED")

    weakest = min(checks.keys(), key=lambda k: checks[k]["score"])

    return {
        "human_score": overall,
        "verdict": verdict,
        "weakest_signal": weakest,
        "checks": checks
    }


def score_hook(text: str, formula_id: Optional[int] = None) -> dict:
    """
    Analiza las primeras dos líneas del texto como gancho para LinkedIn (21 fórmulas de hooks.json).
    Evalúa longitud móvil (140 car) y escritorio (210 car), identificando trampas habituales.
    """
    hooks_data = get_hooks_data()
    all_formulas = hooks_data.get("hooks", [])

    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return {"error": "El texto proporcionado está vacío."}

    line1 = lines[0]
    line2 = lines[1] if len(lines) > 1 else ""

    len_l1 = len(line1)
    mobile_ok = len_l1 <= 140
    desktop_ok = len_l1 <= 210

    # Evaluación de trampas
    traps = []
    if "?" in line1 and not any(c.isdigit() for c in line1) and len(line1.split()) < 7:
        traps.append("Pregunta genérica en línea 1. Evita preguntas con respuesta obvia o estilo 'thoughts?'.")
    if "," in line1 and line1.count(",") >= 3:
        traps.append("Posible acumulación de ideas en la línea 1. Mantén una sola idea por gancho.")
    if not re.search(r"\d", line1):
        traps.append("Sin números concretos. Las cifras específicas ($4.200, 18 meses, 3 clientes) multiplican el CTR.")
    if line2 and (line2.lower().startswith("pero antes") or line2.lower().startswith("déjame explicarte")):
        traps.append("Línea 2 gastada en contexto. La línea 2 debe pagar de inmediato la promesa de la línea 1.")

    matched_formula = None
    if formula_id:
        matched_formula = next((f for f in all_formulas if f["id"] == formula_id), None)

    # Sugerencias de fórmulas
    suggested = []
    for f in all_formulas:
        if formula_id and f["id"] == formula_id:
            continue
        suggested.append({
            "id": f["id"],
            "name": f["name"],
            "template": f["template"],
            "example": f["example"],
            "best_for": f["best_for"]
        })

    return {
        "hook_line_1": line1,
        "hook_line_1_length": len_l1,
        "mobile_visible_140": mobile_ok,
        "desktop_visible_210": desktop_ok,
        "payoff_line_2": line2,
        "traps_detected": traps,
        "specified_formula": matched_formula,
        "recommended_formulas": suggested[:4]
    }


def score_profile_rubric(profile_data: dict) -> dict:
    """
    Evalúa los datos de un perfil de LinkedIn frente a la rúbrica de 12 elementos (rubric.json, 100 pts).
    Genera puntuación total y recomendaciones prioritarias 'Fix-First'.
    """
    rubric = get_rubric_data()
    items = rubric.get("items", [])

    results = []
    total_score = 0
    max_total = rubric.get("total", 100)

    # 1. Headline (12 pts)
    headline = profile_data.get("headline", "")
    h_pts = 0
    h_feedback = ""
    if len(headline) > 60:
        h_pts += 6
        if any(char.isdigit() for char in headline) or "|" in headline or "•" in headline:
            h_pts += 6
            h_feedback = "Excelente titular con posicionamiento, separadores y especificidad."
        else:
            h_feedback = "Buen tamaño, pero se recomienda añadir prueba o valor específico."
    elif len(headline) > 15:
        h_pts = 5
        h_feedback = "Titular muy breve. Aprovecha los hasta 220 caracteres para comunicar a quién ayudas y con qué prueba."
    else:
        h_pts = 2
        h_feedback = "Titular vacío o genérico (solo puesto de trabajo)."
    results.append({"id": "headline", "max_points": 12, "score": h_pts, "feedback": h_feedback})
    total_score += h_pts

    # 2. About Open (10 pts)
    about = profile_data.get("about", "")
    about_lines = [l.strip() for l in about.split("\n") if l.strip()]
    about_open = " ".join(about_lines[:2]) if about_lines else ""
    ao_pts = 0
    ao_feedback = ""
    if about_open:
        if len(about_open) > 80:
            if not about_open.lower().startswith("mi nombre") and not about_open.lower().startswith("soy "):
                ao_pts = 10
                ao_feedback = "Apertura atractiva centrada en la audiencia y sin clichés egocéntricos."
            else:
                ao_pts = 6
                ao_feedback = "Abre con tu propio nombre/cargo en vez de apelar al dolor del lector."
        else:
            ao_pts = 4
            ao_feedback = "Apertura demasiado corta."
    else:
        ao_feedback = "Sección 'Acerca de' ausente o sin apertura."
    results.append({"id": "about_open", "max_points": 10, "score": ao_pts, "feedback": ao_feedback})
    total_score += ao_pts

    # 3. About Body (10 pts)
    ab_pts = 0
    ab_feedback = ""
    if len(about) > 300:
        if len(about) <= 1500:
            ab_pts = 10
            ab_feedback = "Longitud óptima (< 1.400 car) con desarrollo claro."
        else:
            ab_pts = 7
            ab_feedback = "Muy extenso (> 1.500 car). Requiere poda para mantener la atención."
    elif len(about) > 50:
        ab_pts = 4
        ab_feedback = "Cuerpo del 'Acerca de' escaso."
    else:
        ab_feedback = "Sin cuerpo en 'Acerca de'."
    results.append({"id": "about_body", "max_points": 10, "score": ab_pts, "feedback": ab_feedback})
    total_score += ab_pts

    # 4. Featured (8 pts)
    featured = profile_data.get("featured", [])
    feat_pts = min(8, len(featured) * 3) if featured else 0
    results.append({
        "id": "featured",
        "max_points": 8,
        "score": feat_pts,
        "feedback": f"{len(featured)} elementos destacados. (Recomendado: 3 elementos: post estrella, prueba y contacto)."
    })
    total_score += feat_pts

    # 5. Current Role (10 pts)
    exp = profile_data.get("experience", [])
    exp_pts = 0
    exp_feedback = ""
    if exp:
        first_role = str(exp[0])
        if len(first_role) > 80 and any(c.isdigit() for c in first_role):
            exp_pts = 10
            exp_feedback = "Puesto actual detallado con resultados cuantificables."
        elif len(first_role) > 30:
            exp_pts = 6
            exp_feedback = "Puesto actual presente pero enfocado en tareas en vez de logros con métricas."
        else:
            exp_pts = 4
            exp_feedback = "Puesto actual sin descripción de impacto."
    else:
        exp_feedback = "No se detectaron experiencias laborales."
    results.append({"id": "current_role", "max_points": 10, "score": exp_pts, "feedback": exp_feedback})
    total_score += exp_pts

    # 6. Experience Depth (8 pts)
    depth_pts = min(8, len(exp) * 2)
    results.append({
        "id": "experience_depth",
        "max_points": 8,
        "score": depth_pts,
        "feedback": f"{len(exp)} puestos registrados con trayectoria contrastada."
    })
    total_score += depth_pts

    # 7. Skills (6 pts)
    skills = profile_data.get("skills", [])
    skills_pts = 6 if len(skills) >= 3 else (len(skills) * 2)
    results.append({
        "id": "skills",
        "max_points": 6,
        "score": skills_pts,
        "feedback": f"{len(skills)} aptitudes detectadas (las top 3 deben ser el foco principal)."
    })
    total_score += skills_pts

    # 8. Activity (10 pts)
    act = profile_data.get("recent_activity", [])
    act_pts = 10 if len(act) >= 3 else (len(act) * 3)
    results.append({
        "id": "activity",
        "max_points": 10,
        "score": act_pts,
        "feedback": f"Actividad reciente detectada ({len(act)} elementos). Mantener publicaciones o comentarios semanales."
    })
    total_score += act_pts

    # Calificación base para elementos estáticos visuales (Banner, Foto, Contacto, Recomendaciones)
    results.append({"id": "banner_photo_contact", "max_points": 28, "score": 20, "feedback": "Revisar periódicamente imagen de perfil (60% encuadre cara), banner personalizado y datos de contacto."})
    total_score += 20

    # Priorización Fix-First
    fix_first = [r for r in results if r["score"] < r["max_points"]]
    fix_first.sort(key=lambda r: (r["max_points"] - r["score"]), reverse=True)

    return {
        "total_score": min(100, total_score),
        "verdict": "OPTIMIZADO" if total_score >= 80 else ("MEJORABLE" if total_score >= 50 else "CRÍTICO"),
        "fix_first_priority": fix_first[:4],
        "rubric_breakdown": results
    }


def generate_comment_options(post_text: str, comment_type: Optional[int] = None, author_name: Optional[str] = None) -> dict:
    """
    Genera 2 propuestas de comentarios de alto valor a partir de los 9 arquetipos profesionales de LinkedIn.
    Prohíbe comentarios vacíos tipo '¡Gran post!'.
    """
    author = author_name or "el autor"
    types_meta = {
        1: {"name": "Añadir un dato", "shape": "Apoya la afirmación con un número o métrica concreta propia."},
        2: {"name": "Caso faltante", "shape": "Señala la condición límite: 'Esto se cumple hasta que {condición}...'"},
        3: {"name": "Desacuerdo respetuoso", "shape": "Concede la parte cierta primero y luego expone la bifurcación argumental."},
        4: {"name": "Extender una línea", "shape": "Cita una frase clave del post y profundiza en su impacto real."},
        5: {"name": "Pregunta incisiva", "shape": "Pregunta por la parte difícil omitida, sin clichés tipo 'curioso por saber'."},
        6: {"name": "El recibo / prueba", "shape": "Relata en 2 frases lo que ocurrió cuando implementaste eso mismo."},
        7: {"name": "La corrección constructiva", "shape": "Puntualiza un matiz técnico con precisión y amabilidad."},
        8: {"name": "El reencuadre", "shape": "Propone otra perspectiva para interpretar los mismos hechos."},
        9: {"name": "Frase contundente", "shape": "Menos de 12 palabras, memorable y certera."}
    }

    t1 = comment_type if (comment_type and comment_type in types_meta) else 6
    t2 = 3 if t1 != 3 else 2

    return {
        "target_author": author,
        "guidelines": [
            "Extensión estricta: entre 2 y 4 oraciones.",
            "Prohibido abrir con 'Gran post', 'Totalmente de acuerdo' o emojis de aplauso/fuego.",
            "Una sola idea por comentario; no redactar un artículo en la respuesta.",
            "Todo comentario debe pasar por el humanizador anti-IA."
        ],
        "option_1": {
            "type_id": t1,
            "type_name": types_meta[t1]["name"],
            "strategy": types_meta[t1]["shape"]
        },
        "option_2": {
            "type_id": t2,
            "type_name": types_meta[t2]["name"],
            "strategy": types_meta[t2]["shape"]
        }
    }


def triage_inbox_conversations(conversations: List[dict]) -> dict:
    """
    Clasifica las conversaciones de la bandeja de entrada en:
    LEAD, RECRUITER, PEER, ASK, SPAM (detectando secuencias automatizadas de prospección).
    """
    buckets = {
        "LEAD": [],
        "RECRUITER": [],
        "PEER": [],
        "ASK": [],
        "SPAM": []
    }

    spam_sequence_patterns = [
        re.compile(r"(?i)\bpregunta r[aá]pida\b"),
        re.compile(r"(?i)\bquick question\b"),
        re.compile(r"(?i)calendly\.com|savvycal\.com|hubspot\.com/meetings"),
        re.compile(r"(?i)\bgenerar m[aá]s reuniones\b"),
        re.compile(r"(?i)\bagenda una llamada\b"),
        re.compile(r"(?i)\bnoticed you're in\b|\bvi que est[aá]s en el sector\b")
    ]

    recruiter_patterns = [
        re.compile(r"(?i)\boferta de empleo\b|\bproceso de selecci[oó]n\b|\bvacante\b|\brole\b|\bhiring\b|\brango salarial\b|\bpresupuesto\b")
    ]

    lead_patterns = [
        re.compile(r"(?i)\bpresupuesto\b|\bcu[aá]nto cuesta\b|\binteresado en tus servicios\b|\bnecesitamos ayuda con\b|\bcontratar\b|\bdemo\b")
    ]

    ask_patterns = [
        re.compile(r"(?i)\bconsejo\b|\buna duda\b|\bopini[oó]n sobre\b|\bpuedo preguntarte\b|\bfeedback\b")
    ]

    for c in conversations:
        text = (c.get("last_message", "") + " " + c.get("summary", "")).strip()
        participant = c.get("participant_name", "Desconocido")
        thread_id = c.get("thread_id", "")

        is_spam = any(p.search(text) for p in spam_sequence_patterns)
        if is_spam:
            buckets["SPAM"].append({
                "participant": participant,
                "thread_id": thread_id,
                "reason": "Patrón de prospección automatizada en frío / enlace a calendario.",
                "snippet": text[:120]
            })
            continue

        if any(p.search(text) for p in lead_patterns):
            buckets["LEAD"].append({
                "participant": participant,
                "thread_id": thread_id,
                "action": "Responder hoy mismo con valor gratuito y una puerta abierta al final.",
                "snippet": text[:120]
            })
        elif any(p.search(text) for p in recruiter_patterns):
            buckets["RECRUITER"].append({
                "participant": participant,
                "thread_id": thread_id,
                "action": "Pedir los 3 datos clave ausentes: banda salarial, nivel y modalidad remota/presencial.",
                "snippet": text[:120]
            })
        elif any(p.search(text) for p in ask_patterns):
            buckets["ASK"].append({
                "participant": participant,
                "thread_id": thread_id,
                "action": "Responder brevemente si toma menos de 10 minutos; declinar con cortesía si requiere llamada.",
                "snippet": text[:120]
            })
        else:
            buckets["PEER"].append({
                "participant": participant,
                "thread_id": thread_id,
                "action": "Mantener conversación natural de networking sin prisa.",
                "snippet": text[:120]
            })

    counts = {k: len(v) for k, v in buckets.items()}
    return {
        "total_analyzed": len(conversations),
        "counts": counts,
        "summary": f"{counts['LEAD']} LEADS, {counts['RECRUITER']} RECRUITERS, {counts['PEER']} PEERS, {counts['ASK']} ASKS, {counts['SPAM']} SPAM",
        "buckets": buckets
    }


def triage_post_replies(comments: List[dict]) -> dict:
    """
    Clasifica los comentarios bajo un post propio en 5 niveles:
    LEAD, SUBSTANCE, PEER, SUPPORT, NOISE.
    """
    classified = {
        "LEAD": [],
        "SUBSTANCE": [],
        "PEER": [],
        "SUPPORT": [],
        "NOISE": []
    }

    for item in comments:
        text = item.get("text", "")
        author = item.get("author", "Usuario")
        t_lower = text.lower()

        if len(text) < 80 and any(w in t_lower for w in ["gran post", "totalmente", "buena reflexión", "👏", "🔥", "interesante", "totalmente de acuerdo"]):
            classified["SUPPORT"].append({"author": author, "text": text, "recommendation": "Dar 'Recomendar' y respuesta cordial de 3-5 palabras."})
        elif any(w in t_lower for w in ["cuánto", "precio", "tenemos el mismo problema", "cómo lo contratamos", "podemos hablar", "ayuda"]):
            classified["LEAD"].append({"author": author, "text": text, "recommendation": "Responder en público en detalle; la puerta abierta al final debe ser una oferta de ayuda."})
        elif len(text) > 80 or any(c.isdigit() for c in text) or "discrepo" in t_lower or "sin embargo" in t_lower:
            classified["SUBSTANCE"].append({"author": author, "text": text, "recommendation": "La respuesta más larga y fundamentada del hilo. Multiplica el dwell time."})
        elif any(w in t_lower for w in ["bit.ly", "t.me", "crypto", "visita mi perfil", "te ofrezco"]):
            classified["NOISE"].append({"author": author, "text": text, "recommendation": "Ignorar o borrar. Responder da visibilidad al spam."})
        else:
            classified["PEER"].append({"author": author, "text": text, "recommendation": "Aportar valor recíproco sin alargar en exceso."})

    return {
        "counts": {k: len(v) for k, v in classified.items()},
        "classified_replies": classified
    }


def plan_carousel_deck(topic: str, num_slides: int = 10) -> dict:
    """
    Genera la arquitectura de diapositivas para un post documental (carrusel PDF 1080x1350 px, 4:5).
    """
    slides_count = max(8, min(12, num_slides))
    slides = [
        {"slide": 1, "role": "PORTADA (Cover)", "guideline": "Gancho demoledor en 6 palabras o menos + 1 línea de promesa."},
        {"slide": 2, "role": "EL PROBLEMA (The Stake)", "guideline": "Por qué este problema le cuesta dinero, tiempo o foco al lector, en 1 oración."},
    ]
    for i in range(3, slides_count):
        slides.append({
            "slide": i,
            "role": f"PASO {i-2} (1 Sola Idea)",
            "guideline": "Titular de 3 a 7 palabras y como máximo 25 palabras debajo. Cero parrafadas."
        })
    slides.append({
        "slide": slides_count,
        "role": "RECAPITULACIÓN (Recap)",
        "guideline": "Lista resumen autosuficiente. Es la diapositiva que los usuarios guardan y capturan."
    })
    slides.append({
        "slide": slides_count + 1,
        "role": "LLAMADA A LA ACCIÓN (CTA)",
        "guideline": "Una única acción: seguir el perfil, dejar un comentario clave o acceder al recurso."
    })

    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ size: 1080px 1350px; margin: 0; }}
  body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f8fafc; }}
  .slide {{ width: 1080px; height: 1350px; box-sizing: border-box; padding: 120px 90px; page-break-after: always; display: flex; flex-direction: column; justify-content: space-between; position: relative; }}
  h1 {{ font-size: 64px; line-height: 1.15; font-weight: 800; color: #38bdf8; margin: 0; }}
  h2 {{ font-size: 48px; line-height: 1.2; font-weight: 700; margin: 0 0 24px 0; }}
  p {{ font-size: 32px; line-height: 1.45; color: #cbd5e1; margin: 0; }}
  .footer {{ display: flex; justify-content: space-between; font-size: 24px; color: #64748b; border-top: 2px solid #1e293b; padding-top: 30px; }}
</style>
</head>
<body>
<!-- Generar diapositivas como <div class="slide">...</div> -->
</body>
</html>"""

    return {
        "topic": topic,
        "recommended_slides_count": len(slides),
        "dimensions": "1080x1350 px (Ratio 4:5 vertical)",
        "slides_architecture": slides,
        "html_css_boilerplate": html_template
    }


def repurpose_asset(source_text: str) -> dict:
    """
    Desglosa un activo largo (artículo, vídeo, transcripción) en elementos atómicos:
    afirmaciones contundentes, números, historias, mecanismos, errores y frases memorables.
    """
    claims = []
    numbers = []
    stories = []
    mechanisms = []
    mistakes = []
    quotables = []

    lines = [l.strip() for l in source_text.split("\n") if l.strip()]
    for l in lines:
        if NUMBERS.search(l) and len(l) < 140:
            numbers.append(l)
        if any(w in l.lower() for w in ["error", "costó", "perdí", "falló", "equivoc"]):
            mistakes.append(l)
        if any(w in l.lower() for w in ["la forma en que funciona", "el sistema", "el mecanismo", "paso 1", "primero"]):
            mechanisms.append(l)
        if any(w in l.lower() for w in ["dijo", "le contesté", "recuerdo cuando", "cliente"]):
            stories.append(l)
        if len(l) < 90 and any(w in l.lower() for w in ["nunca", "siempre", "es mentira", "no es cierto", "deja de"]):
            claims.append(l)
        elif len(l) < 80:
            quotables.append(l)

    return {
        "extracted_elements": {
            "claims": claims[:4],
            "numbers": numbers[:5],
            "stories": stories[:3],
            "mechanisms": mechanisms[:4],
            "mistakes": mistakes[:3],
            "quotable_lines": quotables[:5]
        },
        "weekly_distribution_suggestion": [
            {"day": "Martes", "formula": "#1 Contrarian Take", "type": "Afirmación que desafía el consenso"},
            {"day": "Miércoles", "formula": "#17 Time Anchor", "type": "Optimización o cifra antes/después"},
            {"day": "Jueves", "formula": "#3 Mistake Confession", "type": "Error cometido y lección pagada"},
            {"day": "Viernes", "formula": "#21 Direct Value", "type": "Mecanismo o plantilla lista para aplicar"}
        ]
    }


def generate_dm_sequence(name: str, hook_reason: str, offer_goal: str) -> dict:
    """
    Genera la secuencia de 4 pasos de mensajería directa en LinkedIn:
    - Nota de invitación (estrictamente <= 200 caracteres, sin petición).
    - Primer mensaje (+1 día tras aceptar).
    - Seguimiento 1 (+4 días, aportando algo nuevo).
    - Seguimiento 2 (+10 días, cierre de ciclo sin presión).
    """
    # 1. Nota de invitación <= 200 car
    note = f"Hola {name.split()[0]}, vi tu publicación sobre {hook_reason[:45]}. Implementamos algo similar en producción y me gustaría seguir tus avances."
    if len(note) > 200:
        note = note[:197] + "..."

    msg1 = (
        f"Hola {name.split()[0]}, gracias por conectar.\n\n"
        f"A raíz de lo que comentabas sobre {hook_reason}, medimos que al eliminar pasos intermedios "
        f"se redujo el tiempo un 35%. Si te es de utilidad, te comparto el desglose técnico breve. "
        f"¿Tiene sentido para lo que estáis montando?"
    )

    fu1 = (
        f"Hola {name.split()[0]}, por si te aporta contexto extra, acabamos de documentar "
        f"un caso práctico con la arquitectura exacta que solventa ese cuello de botella. "
        f"Te lo dejo por aquí sin ningún compromiso."
    )

    fu2 = (
        f"Hola {name.split()[0]}, imagino que vas a tope con las prioridades del trimestre. "
        f"Cierro el hilo por aquí para no saturar tu bandeja. Un placer haber conectado y seguimos en contacto por el feed."
    )

    return {
        "recipient": name,
        "invite_note_200_chars": {
            "text": note,
            "character_count": len(note),
            "valid_under_200": len(note) <= 200
        },
        "first_message_day_1": msg1,
        "follow_up_1_day_4": fu1,
        "follow_up_2_day_10": fu2
    }
