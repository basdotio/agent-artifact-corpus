"""
Serveur MCP local pour Microsoft Outlook (Windows COM / pywin32)
Permet d'interagir avec l'application Outlook bureau ouverte sur Windows.
"""

import datetime
import json
import os
import re
import sys
import threading
import urllib.parse
import winreg
from typing import List, Optional

# --- Sécurisation de l'encodage des flux standards (Windows / cp1252) ---------
# Évite les crashs "UnicodeEncodeError: 'charmap' codec can't encode..." lorsque
# du texte contenant des espaces insécables, des devises ou des emojis est écrit
# sur stdout/stderr (logs, exécution manuelle du script, etc.).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from mcp.server.fastmcp import FastMCP
import pythoncom
import win32com.client

# Initialisation du serveur FastMCP
mcp = FastMCP("Outlook-Local")

# Constantes Outlook
OL_FOLDER_SENT = 5
OL_FOLDER_INBOX = 6
OL_FOLDER_CALENDAR = 9
OL_MAIL_ITEM_CLASS = 43
OL_ATTACH_BY_REFERENCE = 4
OL_ATTACH_EMBEDDED_ITEM = 5

# Propriétés MAPI utilisées pour détecter les pièces jointes "inline" (logos de signature, images intégrées)
PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
PR_ATTACHMENT_HIDDEN = "http://schemas.microsoft.com/mapi/proptag/0x7FFE000B"

MAX_SUBFOLDERS_SCANNED = 300
SEPARATOR = "----------------------------------------"

# Espaces typographiques remplacés par une espace standard
_SPACE_TRANSLATION = {
    0x00A0: " ",  # espace insécable
    0x2007: " ",  # figure space
    0x202F: " ",  # espace fine insécable
    0x2009: " ",  # espace fine
    0x200B: "",   # zero width space
    0xFEFF: "",   # BOM / zero width no-break space
}
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# =============================================================================
# Helpers
# =============================================================================

def _clean(value) -> str:
    """Convertit une valeur en texte UTF-8 sûr (sans surrogates isolés ni caractères de contrôle)."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    text = text.translate(_SPACE_TRANSLATION)
    text = _CONTROL_CHARS_RE.sub("", text)
    # Supprime/remplace les surrogates isolés que COM peut renvoyer (emojis tronqués...)
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def _safe_get(obj, attr: str, default=""):
    """getattr tolérant aux erreurs COM."""
    try:
        value = getattr(obj, attr)
        return default if value is None else value
    except Exception:
        return default


def _fmt_date(value) -> str:
    """Formate une date COM (pywintypes.datetime) en 'AAAA-MM-JJ HH:MM'."""
    if not value:
        return ""
    try:
        return value.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return _clean(value)


def _sort_key(value) -> float:
    try:
        return value.timestamp()
    except Exception:
        return 0.0


def _snippet(item, length: int) -> str:
    body = _clean(_safe_get(item, "Body", ""))
    return re.sub(r"\s+", " ", body[:length * 2]).strip()[:length]


_com_cache = threading.local()


def _get_outlook_app():
    """
    Récupère l'instance COM Outlook.Application avec initialisation COM sécurisée.
    Fournit un message d'erreur clair si Outlook bureau n'est pas installé sur le système.
    """
    try:
        pythoncom.CoInitialize()
    except Exception:
        pass
    try:
        return win32com.client.Dispatch("Outlook.Application")
    except Exception as e:
        raise RuntimeError(
            "Impossible d'interagir avec Microsoft Outlook. "
            "Assurez-vous que l'application de bureau Outlook (version classique / Office 365) "
            "est bien installée et configurée avec un compte e-mail sur ce PC Windows. "
            f"(Détail COM : {e})"
        )


def _get_mapi_namespace():
    """
    Helper pour se connecter au namespace MAPI d'Outlook.
    La connexion COM initiale est mise en cache par thread et revalidée à chaque appel.
    """
    mapi = getattr(_com_cache, "mapi", None)
    if mapi is not None:
        try:
            _ = mapi.Folders.Count  # Vérifie que la session est toujours valide
            return mapi
        except Exception:
            _com_cache.mapi = None
    outlook = _get_outlook_app()
    mapi = outlook.GetNamespace("MAPI")
    _com_cache.mapi = mapi
    return mapi


def _open_item(mapi, entry_id: str, store_id: Optional[str] = None):
    """
    Ouvre un élément Outlook à partir de son EntryID.
    1. Avec le StoreID fourni (méthode la plus fiable).
    2. Sans StoreID (store par défaut).
    3. En essayant chaque store (boîte partagée, archive, compte secondaire...).
    """
    entry_id = (entry_id or "").strip()
    store_id = (store_id or "").strip() or None
    errors = []

    if store_id:
        try:
            return mapi.GetItemFromID(entry_id, store_id)
        except Exception as e:
            errors.append(f"avec StoreID: {e}")

    try:
        return mapi.GetItemFromID(entry_id)
    except Exception as e:
        errors.append(f"store par défaut: {e}")

    try:
        for store in mapi.Stores:
            sid = _safe_get(store, "StoreID", "")
            if not sid or sid == store_id:
                continue
            try:
                return mapi.GetItemFromID(entry_id, sid)
            except Exception:
                continue
    except Exception as e:
        errors.append(f"parcours des stores: {e}")

    raise RuntimeError("Impossible d'ouvrir l'élément (" + " | ".join(errors) + ")")


def _format_size(size_bytes) -> str:
    try:
        size = float(size_bytes)
    except Exception:
        return "?"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} Ko"
    return f"{size / (1024 * 1024):.2f} Mo"


def _is_inline_attachment(att) -> bool:
    """Détecte les images intégrées (logos de signature, images dans le corps HTML)."""
    try:
        pa = att.PropertyAccessor
    except Exception:
        return False
    try:
        if pa.GetProperty(PR_ATTACHMENT_HIDDEN):
            return True
    except Exception:
        pass
    try:
        cid = pa.GetProperty(PR_ATTACH_CONTENT_ID)
        if cid:
            name = str(_safe_get(att, "FileName", "")).lower()
            return name.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".emz", ".wmz"))
    except Exception:
        pass
    return False


def _attachment_name(att, index: int) -> str:
    name = _clean(_safe_get(att, "FileName", "")) or _clean(_safe_get(att, "DisplayName", ""))
    if not name:
        name = f"piece_jointe_{index}"
    if _safe_get(att, "Type", 1) == OL_ATTACH_EMBEDDED_ITEM and not name.lower().endswith(".msg"):
        name += ".msg"
    return name


def _sanitize_filename(name: str, max_len: int = 150) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(".")
    if not name:
        name = "piece_jointe"
    if len(name) > max_len:
        stem, ext = os.path.splitext(name)
        name = stem[: max_len - len(ext)] + ext
    return name


def _unique_path(directory: str, filename: str) -> str:
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(filename)
    i = 1
    while True:
        candidate = os.path.join(directory, f"{stem} ({i}){ext}")
        if not os.path.exists(candidate):
            return candidate
        i += 1


def _iter_folders(root, include_subfolders: bool, budget: List[int]):
    """Itère sur un dossier et (optionnellement) ses sous-dossiers, avec un plafond global."""
    if budget[0] <= 0:
        return
    budget[0] -= 1
    yield root
    if not include_subfolders:
        return
    try:
        for sub in root.Folders:
            yield from _iter_folders(sub, True, budget)
    except Exception:
        return


def _dasl_escape(text: str) -> str:
    """Échappe une valeur pour une clause LIKE DASL."""
    return text.replace("'", "''")


def _build_search_filter(query: str, search_body: bool, use_index: bool = False) -> str:
    """
    Construit le filtre DASL. Les champs d'en-tête utilisent LIKE '%...%' (rapide).
    Pour le corps, LIKE impose un scan complet (~3 s / dossier) : si l'index Instant Search
    du store est actif, on utilise ci_phrasematch (recherche plein texte indexée, ~0,3 s),
    qui trouve les mots/expressions entiers.
    """
    q = _dasl_escape(query)
    fields = [
        "urn:schemas:httpmail:subject",
        "urn:schemas:httpmail:fromname",
        "urn:schemas:httpmail:displayto",
        "http://schemas.microsoft.com/mapi/proptag/0x0C1F001F",  # PR_SENDER_EMAIL_ADDRESS
    ]
    clauses = [f"\"{f}\" LIKE '%{q}%'" for f in fields]
    if search_body:
        body_field = "urn:schemas:httpmail:textdescription"
        if use_index:
            clauses.append(f"\"{body_field}\" ci_phrasematch '{q}'")
        else:
            clauses.append(f"\"{body_field}\" LIKE '%{q}%'")
    return "@SQL=(" + " OR ".join(clauses) + ")"


def _store_is_indexed(folder, cache: dict) -> bool:
    """Indique si l'index Instant Search est actif sur le store du dossier (mis en cache par StoreID)."""
    sid = _safe_get(folder, "StoreID", "")
    if sid not in cache:
        try:
            cache[sid] = bool(folder.Store.IsInstantSearchEnabled)
        except Exception:
            cache[sid] = False
    return cache[sid]


def _format_mail_summary(item, store_id: str, folder_name: str, snippet_len: int = 200,
                         show_status: bool = False) -> str:
    sender = _clean(_safe_get(item, "SenderName", "Inconnu"))
    sender_email = _clean(_safe_get(item, "SenderEmailAddress", ""))
    subject = _clean(_safe_get(item, "Subject", "")) or "(Sans objet)"
    date = _fmt_date(_safe_get(item, "ReceivedTime", None) or _safe_get(item, "SentOn", None))
    entry_id = _clean(_safe_get(item, "EntryID", ""))
    n_att = 0
    try:
        n_att = item.Attachments.Count
    except Exception:
        pass

    lines = [f"ID: {entry_id}", f"StoreID: {store_id}", f"Dossier: {folder_name}"]
    if show_status:
        lines.append("Statut: " + ("[NON LU]" if _safe_get(item, "UnRead", False) else "[LU]"))
    lines += [
        f"De: {sender} <{sender_email}>",
        f"Date: {date}",
        f"Objet: {subject}",
    ]
    if n_att:
        lines.append(f"Pièces jointes: {n_att}")
    if snippet_len > 0:
        lines.append(f"Aperçu: {_snippet(item, snippet_len)}...")
    lines.append(SEPARATOR)
    return "\n".join(lines)


# =============================================================================
# Outils MCP - Lecture
# =============================================================================

@mcp.tool()
def get_recent_emails(count: int = 10, unread_only: bool = False) -> str:
    """
    Récupère les derniers e-mails de la boîte de réception Outlook locale.
    Chaque résultat inclut l'ID (EntryID) et le StoreID à passer à get_email_details,
    list_attachments et save_attachments.

    Args:
        count: Nombre maximal d'e-mails à récupérer (par défaut 10).
        unread_only: Si True, ne récupère que les messages non lus.
    """
    try:
        mapi = _get_mapi_namespace()
        inbox = mapi.GetDefaultFolder(OL_FOLDER_INBOX)
        store_id = _safe_get(inbox, "StoreID", "")
        folder_name = _clean(_safe_get(inbox, "Name", "Inbox"))

        items = inbox.Items
        if unread_only:
            items = items.Restrict("[UnRead] = true")
        items.Sort("[ReceivedTime]", True)  # Décroissant (plus récents en premier)

        results = []
        item = items.GetFirst()
        while item is not None and len(results) < count:
            if _safe_get(item, "Class", None) == OL_MAIL_ITEM_CLASS:
                results.append(_format_mail_summary(item, store_id, folder_name, 250, show_status=True))
            item = items.GetNext()

        if not results:
            return "Aucun e-mail trouvé."

        return _clean(f"--- {len(results)} derniers e-mails ---\n\n" + "\n\n".join(results))
    except Exception as e:
        return _clean(f"Erreur lors de la récupération des e-mails: {e}")


@mcp.tool()
def search_emails(
    query: str,
    max_results: int = 10,
    include_sent: bool = True,
    include_subfolders: bool = False,
    search_body: bool = False,
    all_stores: bool = False,
) -> str:
    """
    Recherche rapide (filtre natif Outlook DASL/Restrict) des e-mails dont l'objet,
    l'expéditeur ou les destinataires contiennent le terme recherché.
    Les résultats sont triés du plus récent au plus ancien et incluent l'ID (EntryID)
    et le StoreID à passer à get_email_details, list_attachments et save_attachments.

    Args:
        query: Le mot-clé ou texte à rechercher (insensible à la casse).
        max_results: Nombre maximal de résultats (par défaut 10).
        include_sent: Inclure aussi le dossier Éléments envoyés (par défaut True).
        include_subfolders: Inclure les sous-dossiers de la boîte de réception / des éléments envoyés (par défaut False).
        search_body: Rechercher aussi dans le corps du message (par défaut False). Utilise l'index Instant Search (mots entiers, rapide) si disponible, sinon un scan complet (lent).
        all_stores: Rechercher dans tous les comptes / boîtes aux lettres ouverts dans Outlook (par défaut False).
    """
    try:
        query = (query or "").strip()
        if not query:
            return "Erreur: le paramètre 'query' est vide."
        max_results = max(1, int(max_results))

        mapi = _get_mapi_namespace()
        filters = {
            False: _build_search_filter(query, search_body, use_index=False),
            True: _build_search_filter(query, search_body, use_index=True),
        }
        index_cache = {}

        # Dossiers racines à inspecter
        roots = []
        if all_stores:
            for store in mapi.Stores:
                for folder_type in ([OL_FOLDER_INBOX, OL_FOLDER_SENT] if include_sent else [OL_FOLDER_INBOX]):
                    try:
                        roots.append(store.GetDefaultFolder(folder_type))
                    except Exception:
                        continue  # Store sans ce dossier (archive PST, dossiers publics...)
        else:
            roots.append(mapi.GetDefaultFolder(OL_FOLDER_INBOX))
            if include_sent:
                roots.append(mapi.GetDefaultFolder(OL_FOLDER_SENT))

        candidates = []  # (timestamp, résumé formaté)
        seen = set()
        budget = [MAX_SUBFOLDERS_SCANNED]
        folder_errors = []

        for root in roots:
            for folder in _iter_folders(root, include_subfolders, budget):
                try:
                    use_index = search_body and _store_is_indexed(folder, index_cache)
                    restricted = folder.Items.Restrict(filters[use_index])
                    if restricted.Count == 0:
                        continue
                    restricted.Sort("[ReceivedTime]", True)
                    store_id = _safe_get(folder, "StoreID", "")
                    folder_name = _clean(_safe_get(folder, "FolderPath", "") or _safe_get(folder, "Name", ""))

                    taken = 0
                    item = restricted.GetFirst()
                    while item is not None and taken < max_results:
                        if _safe_get(item, "Class", None) == OL_MAIL_ITEM_CLASS:
                            entry_id = _safe_get(item, "EntryID", "")
                            if entry_id not in seen:
                                seen.add(entry_id)
                                date = _safe_get(item, "ReceivedTime", None) or _safe_get(item, "SentOn", None)
                                candidates.append((_sort_key(date), item, store_id, folder_name))
                                taken += 1
                        item = restricted.GetNext()
                except Exception as e:
                    folder_errors.append(f"{_clean(_safe_get(folder, 'Name', '?'))}: {e}")

        candidates.sort(key=lambda c: c[0], reverse=True)
        results = [
            _format_mail_summary(item, store_id, folder_name, 200)
            for _, item, store_id, folder_name in candidates[:max_results]
        ]

        if not results:
            msg = f"Aucun e-mail correspondant à la recherche '{query}'."
            if folder_errors:
                msg += "\nErreurs: " + "; ".join(folder_errors[:5])
            return _clean(msg)

        out = f"--- {len(results)} résultats pour '{query}' ---\n\n" + "\n\n".join(results)
        if folder_errors:
            out += "\n\n(Dossiers ignorés suite à une erreur: " + "; ".join(folder_errors[:5]) + ")"
        return _clean(out)
    except Exception as e:
        return _clean(f"Erreur lors de la recherche: {e}")


@mcp.tool()
def get_email_details(entry_id: str, store_id: Optional[str] = None) -> str:
    """
    Affiche le contenu complet d'un e-mail spécifique à partir de son EntryID.
    Fournir le StoreID (renvoyé par search_emails / get_recent_emails) rend l'ouverture
    fiable, notamment pour les sous-dossiers, boîtes partagées et comptes secondaires.

    Args:
        entry_id: L'identifiant unique (EntryID) de l'e-mail.
        store_id: Le StoreID du magasin contenant l'e-mail (optionnel mais recommandé).
    """
    try:
        mapi = _get_mapi_namespace()
        item = _open_item(mapi, entry_id, store_id)

        sender = _clean(_safe_get(item, "SenderName", "Inconnu"))
        sender_email = _clean(_safe_get(item, "SenderEmailAddress", ""))
        to = _clean(_safe_get(item, "To", ""))
        cc = _clean(_safe_get(item, "CC", ""))
        subject = _clean(_safe_get(item, "Subject", "")) or "(Sans objet)"
        received = _fmt_date(_safe_get(item, "ReceivedTime", None) or _safe_get(item, "SentOn", None))
        body = _clean(_safe_get(item, "Body", ""))
        folder = _clean(_safe_get(_safe_get(item, "Parent", None), "FolderPath", ""))

        att_lines = []
        try:
            atts = item.Attachments
            for i in range(1, atts.Count + 1):
                att = atts.Item(i)
                tag = " [inline]" if _is_inline_attachment(att) else ""
                att_lines.append(f"  [{i}] {_attachment_name(att, i)} ({_format_size(_safe_get(att, 'Size', 0))}){tag}")
        except Exception:
            pass

        header = (
            f"DE: {sender} <{sender_email}>\n"
            f"À: {to}\n"
            f"CC: {cc}\n"
            f"DATE: {received}\n"
            f"OBJET: {subject}\n"
            f"DOSSIER: {folder}\n"
        )
        if att_lines:
            header += f"PIÈCES JOINTES ({len(att_lines)}):\n" + "\n".join(att_lines) + "\n"
        return _clean(header + "========================================\n" + body)
    except Exception as e:
        return _clean(f"Erreur lors de la lecture du message ({entry_id}): {e}")


# =============================================================================
# Outils MCP - Pièces jointes
# =============================================================================

@mcp.tool()
def list_attachments(entry_id: str, store_id: Optional[str] = None) -> str:
    """
    Liste les pièces jointes d'un e-mail (index, nom du fichier, taille).
    Les index retournés (à partir de 1) s'utilisent avec save_attachments.
    Les images intégrées (logos de signature...) sont signalées par [inline].

    Args:
        entry_id: L'identifiant unique (EntryID) de l'e-mail.
        store_id: Le StoreID du magasin contenant l'e-mail (optionnel mais recommandé).
    """
    try:
        mapi = _get_mapi_namespace()
        item = _open_item(mapi, entry_id, store_id)
        subject = _clean(_safe_get(item, "Subject", "")) or "(Sans objet)"
        atts = item.Attachments
        count = atts.Count
        if count == 0:
            return _clean(f"Aucune pièce jointe dans l'e-mail « {subject} ».")

        lines = []
        for i in range(1, count + 1):
            att = atts.Item(i)
            tags = []
            if _is_inline_attachment(att):
                tags.append("inline")
            att_type = _safe_get(att, "Type", 1)
            if att_type == OL_ATTACH_EMBEDDED_ITEM:
                tags.append("e-mail joint")
            elif att_type == OL_ATTACH_BY_REFERENCE:
                tags.append("lien/référence")
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"[{i}] {_attachment_name(att, i)} — {_format_size(_safe_get(att, 'Size', 0))}{tag_str}")

        return _clean(f"--- {count} pièce(s) jointe(s) — « {subject} » ---\n" + "\n".join(lines))
    except Exception as e:
        return _clean(f"Erreur lors du listage des pièces jointes ({entry_id}): {e}")


@mcp.tool()
def save_attachments(
    entry_id: str,
    target_dir: str,
    attachment_indices: Optional[List[int]] = None,
    store_id: Optional[str] = None,
    include_inline: bool = False,
) -> str:
    """
    Enregistre les pièces jointes d'un e-mail dans un répertoire local et renvoie
    les chemins absolus des fichiers créés. Le répertoire est créé s'il n'existe pas ;
    un fichier existant n'est jamais écrasé (suffixe « (1) », « (2) »... ajouté).

    Args:
        entry_id: L'identifiant unique (EntryID) de l'e-mail.
        target_dir: Répertoire local de destination (chemin absolu recommandé).
        attachment_indices: Index (à partir de 1, cf. list_attachments) des pièces jointes à enregistrer. Par défaut : toutes.
        store_id: Le StoreID du magasin contenant l'e-mail (optionnel mais recommandé).
        include_inline: Si aucun index n'est fourni, inclure aussi les images intégrées (logos de signature). Par défaut False.
    """
    try:
        mapi = _get_mapi_namespace()
        item = _open_item(mapi, entry_id, store_id)
        atts = item.Attachments
        count = atts.Count
        if count == 0:
            return "Aucune pièce jointe à enregistrer."

        target_dir = os.path.abspath(os.path.expandvars(os.path.expanduser(target_dir)))
        os.makedirs(target_dir, exist_ok=True)

        explicit = attachment_indices is not None and len(attachment_indices) > 0
        indices = list(dict.fromkeys(int(i) for i in attachment_indices)) if explicit else list(range(1, count + 1))

        saved, skipped, errors = [], [], []
        for idx in indices:
            if idx < 1 or idx > count:
                errors.append(f"[{idx}] index invalide (1 à {count})")
                continue
            att = atts.Item(idx)
            name = _attachment_name(att, idx)
            if not explicit and not include_inline and _is_inline_attachment(att):
                skipped.append(f"[{idx}] {name} (image intégrée)")
                continue
            if _safe_get(att, "Type", 1) == OL_ATTACH_BY_REFERENCE:
                errors.append(f"[{idx}] {name}: pièce jointe par référence (lien), non enregistrable")
                continue
            path = _unique_path(target_dir, _sanitize_filename(name))
            try:
                att.SaveAsFile(path)
                size = os.path.getsize(path) if os.path.exists(path) else 0
                saved.append(f"[{idx}] {path} ({_format_size(size)})")
            except Exception as e:
                errors.append(f"[{idx}] {name}: {e}")

        out = [f"{len(saved)} fichier(s) enregistré(s) dans {target_dir}"]
        if saved:
            out += saved
        if skipped:
            out.append("Ignorés (utiliser include_inline=True ou des index explicites pour les inclure):")
            out += [f"  {s}" for s in skipped]
        if errors:
            out.append("Erreurs:")
            out += [f"  {e}" for e in errors]
        return _clean("\n".join(out))
    except Exception as e:
        return _clean(f"Erreur lors de l'enregistrement des pièces jointes ({entry_id}): {e}")


# =============================================================================
# Outils MCP - Envoi / Brouillons
# =============================================================================

def _get_default_signature_name(account_email: Optional[str] = None) -> str:
    """
    Détecte automatiquement le nom de la signature par défaut configurée dans l'application Outlook.
    Recherche dans les configurations Windows et Office :
    1. Variable d'environnement OUTLOOK_SIGNATURE_NAME (prioritaire si définie).
    2. Microsoft 365 Cloud Roaming Signatures (HKCU\\Software\\Microsoft\\Office\\Outlook\\Settings\\Data).
    3. Profils Outlook Classic MAPI (HKCU\\Software\\Microsoft\\Office\\16.0\\Outlook\\Profiles\\...\\New Signature).
    4. Paramètres Office généraux (HKCU\\Software\\Microsoft\\Office\\<ver>\\Common\\MailSettings\\NewSignature).
    """
    # 1. Variable d'environnement (permet de forcer une signature si souhaité)
    env_sig = os.environ.get("OUTLOOK_SIGNATURE_NAME", "").strip()
    if env_sig:
        return env_sig

    # 2. Microsoft 365 Roaming Signatures (stocké en JSON par compte)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Office\Outlook\Settings\Data") as key:
            candidates = {}
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(key, i)
                    name_lower = name.lower()
                    if "roaming_new_signature" in name_lower and isinstance(val, str):
                        try:
                            data = json.loads(val)
                            sig_val = data.get("value")
                            if sig_val:
                                email_prefix = name.split("_roaming_new_signature")[0].strip().lower()
                                candidates[email_prefix] = sig_val
                        except Exception:
                            pass
                    i += 1
                except OSError:
                    break

            if account_email and account_email.lower() in candidates:
                return candidates[account_email.lower()]
            if candidates:
                return next(iter(candidates.values()))
    except Exception:
        pass

    # 3. Profils Outlook Classic (Office 16.0 / 2016 / 2019 / 2021 / 2024)
    for ver in ["16.0", "15.0"]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Office\{ver}\Outlook\Profiles") as prof_key:
                try:
                    default_profile = winreg.QueryValueEx(prof_key, "DefaultProfile")[0]
                except Exception:
                    default_profile = "Outlook"

                acc_path = rf"Software\Microsoft\Office\{ver}\Outlook\Profiles\{default_profile}\9375CFF0413111d3B88A00104B2A6676"
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, acc_path) as acc_key:
                        j = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(acc_key, j)
                                with winreg.OpenKey(acc_key, subkey_name) as sub:
                                    try:
                                        val, _ = winreg.QueryValueEx(sub, "New Signature")
                                        if isinstance(val, bytes):
                                            val = val.decode("utf-16le", errors="ignore").rstrip("\x00")
                                        if val and str(val).strip():
                                            return str(val).strip()
                                    except Exception:
                                        pass
                                j += 1
                            except OSError:
                                break
                except Exception:
                    pass
        except Exception:
            pass

    # 4. Paramètres généraux WordMail / Common
    for ver in ["16.0", "15.0", "14.0"]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Office\{ver}\Common\MailSettings") as key:
                val, _ = winreg.QueryValueEx(key, "NewSignature")
                if val and str(val).strip():
                    return str(val).strip()
        except Exception:
            pass

    return ""


def _get_default_signature_html(account_email: Optional[str] = None) -> str:
    """
    Récupère le contenu HTML de la signature configurée par défaut dans Outlook.
    Résout le nom de la signature depuis les paramètres Outlook puis lit le fichier .htm
    correspondant dans %APPDATA%\\Microsoft\\Signatures.
    """
    sig_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Signatures")
    if not os.path.exists(sig_dir):
        return ""

    htm_files = [f for f in os.listdir(sig_dir) if f.lower().endswith(".htm")]
    if not htm_files:
        return ""

    target_sig = _get_default_signature_name(account_email)
    matched_file = None

    if target_sig:
        target_lower = target_sig.lower()
        # 1. Correspondance exacte sur le nom de fichier (sans extension)
        for f in htm_files:
            if os.path.splitext(f)[0].lower() == target_lower:
                matched_file = f
                break
        # 2. Correspondance si le fichier commence par le nom de la signature (ex: "Nom (compte).htm")
        if not matched_file:
            for f in htm_files:
                if os.path.splitext(f)[0].lower().startswith(target_lower):
                    matched_file = f
                    break
        # 3. Correspondance par sous-chaîne
        if not matched_file:
            for f in htm_files:
                if target_lower in f.lower():
                    matched_file = f
                    break

    # Repli sur le premier fichier .htm si aucune signature n'a été spécifiée dans les paramètres
    if not matched_file:
        matched_file = htm_files[0]

    try:
        with open(os.path.join(sig_dir, matched_file), "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _apply_body_and_default_signature(mail, body: str) -> None:
    """
    Insère le texte au format Arial 10pt dans le corps du message suivi de la signature par défaut d'Outlook.
    """
    formatted_lines = body.replace("\r\n", "\n").replace("\n", "<br>")
    html_snippet = f"""<div style="font-family: Arial, sans-serif; font-size: 10pt; color: #000000; line-height: 1.35;">
{formatted_lines}
</div><br>"""

    sender_email = _clean(_safe_get(mail, "SenderEmailAddress", ""))
    sig = _get_default_signature_html(sender_email)
    if sig:
        mail.HTMLBody = html_snippet + "<br>" + sig
    else:
        mail.HTMLBody = html_snippet


def _normalize_recipients(recipients: Optional[str]) -> str:
    """Assure que les adresses e-mails sont bien au format obligatoire <adresse@domaine.com>."""
    if not recipients:
        return ""
    parts = [p.strip() for p in re.split(r"[,;]+", recipients) if p.strip()]
    formatted = []
    for p in parts:
        if "<" in p and ">" in p:
            formatted.append(p)
        else:
            formatted.append(f"<{p}>")
    return "; ".join(formatted)


def _add_attachments(mail, attachment_paths: Optional[List[str]]) -> List[str]:
    """
    Ajoute des pièces jointes à un MailItem Outlook.
    Résout les chemins absolus / relatifs / variables d'environnement.
    Retourne la liste des noms de fichiers attachés.
    """
    if not attachment_paths:
        return []
    attached = []
    for raw_p in attachment_paths:
        if not raw_p or not str(raw_p).strip():
            continue
        p = os.path.abspath(os.path.expandvars(os.path.expanduser(str(raw_p).strip())))
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Fichier introuvable pour pièce jointe : '{p}'")
        mail.Attachments.Add(Source=p)
        attached.append(os.path.basename(p))
    return attached


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    attachment_paths: Optional[List[str]] = None
) -> str:
    """
    Envoie un e-mail directement via Outlook avec mise en forme HTML (Arial 10pt), signature automatique et pièces jointes optionnelles.
    RÈGLE STRICTE : Les adresses de destinataires doivent impérativement être formatées sous la forme <adresse@domaine.com>.
    
    Args:
        to: Destinataire(s) impérativement sous la forme <adresse@domaine.com> (ex: <destinataire@example.com>). Séparer par point-virgule si plusieurs.
        subject: Objet de l'e-mail.
        body: Corps du message.
        cc: Destinataire(s) en copie au format <adresse@domaine.com> (optionnel).
        bcc: Destinataire(s) en copie cachée au format <adresse@domaine.com> (optionnel).
        attachment_paths: Liste des chemins absolus ou relatifs des fichiers locaux à joindre à l'e-mail (optionnel).
    """
    try:
        outlook = _get_outlook_app()
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        clean_to = _normalize_recipients(to)
        clean_cc = _normalize_recipients(cc)
        clean_bcc = _normalize_recipients(bcc)

        mail.To = clean_to
        if clean_cc:
            mail.CC = clean_cc
        if clean_bcc:
            mail.BCC = clean_bcc
        mail.Subject = subject

        _apply_body_and_default_signature(mail, body)
        attached = _add_attachments(mail, attachment_paths)

        mail.Send()
        msg = f"E-mail envoyé avec succès à {clean_to}"
        if clean_cc:
            msg += f" (CC: {clean_cc})"
        if attached:
            msg += f" (Pièces jointes: {', '.join(attached)})"
        return _clean(msg + ".")
    except Exception as e:
        return _clean(f"Erreur lors de l'envoi de l'e-mail: {str(e)}")

@mcp.tool()
def create_draft(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    attachment_paths: Optional[List[str]] = None,
    open_window: bool = False
) -> str:
    """
    Crée un brouillon d'e-mail dans Outlook avec mise en forme HTML (Arial 10pt), signature automatique et pièces jointes optionnelles.
    Par défaut, le brouillon est enregistré en arrière-plan sans ouvrir de fenêtre.
    RÈGLE STRICTE : Les adresses de destinataires doivent impérativement être formatées sous la forme <adresse@domaine.com>.
    
    Args:
        to: Destinataire(s) principal(aux) impérativement sous la forme <adresse@domaine.com> (ex: <destinataire@example.com>). Séparer par point-virgule si plusieurs.
        subject: Objet du brouillon.
        body: Contenu du message.
        cc: Destinataire(s) en copie au format <adresse@domaine.com> (optionnel).
        bcc: Destinataire(s) en copie cachée au format <adresse@domaine.com> (optionnel).
        attachment_paths: Liste des chemins absolus ou relatifs des fichiers locaux à joindre au brouillon (optionnel).
        open_window: Si True, affiche la fenêtre de composition dans Outlook (par défaut False).
    """
    try:
        outlook = _get_outlook_app()
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        clean_to = _normalize_recipients(to)
        clean_cc = _normalize_recipients(cc)
        clean_bcc = _normalize_recipients(bcc)

        mail.To = clean_to
        if clean_cc:
            mail.CC = clean_cc
        if clean_bcc:
            mail.BCC = clean_bcc
        mail.Subject = subject

        _apply_body_and_default_signature(mail, body)
        attached = _add_attachments(mail, attachment_paths)

        if open_window:
            mail.Display()

        mail.Save()
        
        msg = f"Brouillon enregistré dans Outlook pour {clean_to}"
        if open_window:
            msg += " (fenêtre affichée)"
        if clean_cc:
            msg += f" (CC: {clean_cc})"
        if attached:
            msg += f" (Pièces jointes: {', '.join(attached)})"
        return _clean(msg + ".")
    except Exception as e:
        return _clean(f"Erreur lors de la création du brouillon: {str(e)}")


@mcp.tool()
def create_reply_draft(
    entry_id: str,
    body: str,
    reply_all: bool = False,
    attachment_paths: Optional[List[str]] = None,
    store_id: Optional[str] = None,
    open_window: bool = False
) -> str:
    """
    Crée un brouillon de réponse à un e-mail existant dans Outlook (conserve le fil de discussion et l'historique).
    Par défaut, le brouillon est enregistré en arrière-plan sans ouvrir de fenêtre.

    Args:
        entry_id: L'identifiant unique (EntryID) de l'e-mail auquel répondre.
        body: Le texte de votre réponse (sera inséré en haut, au format Arial 10pt).
        reply_all: Si True, répond à tous les participants (expéditeur et personnes en copie). Par défaut False.
        attachment_paths: Liste des chemins absolus ou relatifs des fichiers locaux à joindre à la réponse (optionnel).
        store_id: Le StoreID du magasin contenant l'e-mail (optionnel mais recommandé).
        open_window: Si True, affiche la fenêtre de composition dans Outlook (par défaut False).
    """
    try:
        mapi = _get_mapi_namespace()
        item = _open_item(mapi, entry_id, store_id)
        reply = item.ReplyAll() if reply_all else item.Reply()

        formatted_lines = body.replace("\r\n", "\n").replace("\n", "<br>")
        html_snippet = f"""<div style="font-family: Arial, sans-serif; font-size: 10pt; color: #000000; line-height: 1.35;">
{formatted_lines}
</div><br>"""

        # Insère la réponse au-dessus de l'historique et de la signature de réponse
        reply.HTMLBody = html_snippet + reply.HTMLBody
        attached = _add_attachments(reply, attachment_paths)

        if open_window:
            reply.Display()

        reply.Save()

        target_str = _clean(_safe_get(reply, "To", "l'expéditeur"))
        msg = f"Brouillon de réponse enregistré dans Outlook pour {target_str}"
        if open_window:
            msg += " (fenêtre affichée)"
        if attached:
            msg += f" (Pièces jointes: {', '.join(attached)})"
        return _clean(msg + ".")
    except Exception as e:
        return _clean(f"Erreur lors de la création du brouillon de réponse: {str(e)}")


@mcp.tool()
def reply_email(
    entry_id: str,
    body: str,
    reply_all: bool = False,
    attachment_paths: Optional[List[str]] = None,
    store_id: Optional[str] = None
) -> str:
    """
    Répond et envoie directement un e-mail dans le fil de discussion existant via Outlook.

    Args:
        entry_id: L'identifiant unique (EntryID) de l'e-mail auquel répondre.
        body: Le texte de votre réponse (sera inséré en haut, au format Arial 10pt).
        reply_all: Si True, répond à tous les participants (expéditeur et personnes en copie). Par défaut False.
        attachment_paths: Liste des chemins absolus ou relatifs des fichiers locaux à joindre à la réponse (optionnel).
        store_id: Le StoreID du magasin contenant l'e-mail (optionnel mais recommandé).
    """
    try:
        mapi = _get_mapi_namespace()
        item = _open_item(mapi, entry_id, store_id)
        reply = item.ReplyAll() if reply_all else item.Reply()

        formatted_lines = body.replace("\r\n", "\n").replace("\n", "<br>")
        html_snippet = f"""<div style="font-family: Arial, sans-serif; font-size: 10pt; color: #000000; line-height: 1.35;">
{formatted_lines}
</div><br>"""

        reply.HTMLBody = html_snippet + reply.HTMLBody
        attached = _add_attachments(reply, attachment_paths)

        reply.Send()

        target_str = _clean(_safe_get(reply, "To", "destinataires"))
        msg = f"Réponse envoyée avec succès à {target_str}"
        if attached:
            msg += f" (Pièces jointes: {', '.join(attached)})"
        return _clean(msg + ".")
    except Exception as e:
        return _clean(f"Erreur lors de l'envoi de la réponse: {str(e)}")


# =============================================================================
# Outils MCP - Calendrier
# =============================================================================

@mcp.tool()
def get_calendar_events(days_ahead: int = 7) -> str:
    """
    Récupère les événements du calendrier Outlook pour les N prochains jours.
    
    Args:
        days_ahead: Nombre de jours à venir à inclure (par défaut 7).
    """
    try:
        mapi = _get_mapi_namespace()
        calendar = mapi.GetDefaultFolder(OL_FOLDER_CALENDAR)
        items = calendar.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")
        
        now = datetime.datetime.now()
        end_date = now + datetime.timedelta(days=days_ahead)
        
        # Formater les dates pour la restriction Restrict d'Outlook
        start_str = now.strftime("%d/%m/%Y %H:%M")
        end_str = end_date.strftime("%d/%m/%Y %H:%M")
        
        # Restreindre la plage de dates
        restriction = f"[Start] >= '{start_str}' AND [End] <= '{end_str}'"
        try:
            restricted_items = items.Restrict(restriction)
        except Exception:
            restricted_items = items  # Fallback en cas d'erreur de formatage régional
            
        results = []
        for item in restricted_items:
            start_time = getattr(item, "Start", None)
            if start_time and (now.date() <= start_time.date() <= end_date.date()):
                subject = _clean(_safe_get(item, "Subject", "(Sans titre)"))
                location = _clean(_safe_get(item, "Location", "Non spécifié"))
                organizer = _clean(_safe_get(item, "Organizer", ""))
                
                results.append(
                    f"Début: {start_time}\n"
                    f"Fin: {getattr(item, 'End', '')}\n"
                    f"Événement: {subject}\n"
                    f"Lieu: {location}\n"
                    f"Organisateur: {organizer}\n"
                    "----------------------------------------"
                )
                if len(results) >= 20:
                    break
                    
        if not results:
            return f"Aucun événement trouvé dans les {days_ahead} prochains jours."
            
        return _clean(f"--- Calendrier ({len(results)} événements) ---\n\n" + "\n\n".join(results))
    except Exception as e:
        return _clean(f"Erreur lors de la lecture du calendrier: {str(e)}")


if __name__ == "__main__":
    # Préchauffage de la connexion COM (évite ~2-3 s sur le premier appel d'outil).
    # Les outils synchrones FastMCP s'exécutent dans ce même thread : le cache est réutilisé.
    try:
        _get_mapi_namespace()
    except Exception as _e:
        print(f"[outlook-local] Préconnexion Outlook impossible: {_e}", file=sys.stderr)
    mcp.run()
