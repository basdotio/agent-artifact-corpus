"""Extract plain text from a .docx file without a python-docx dependency.

A .docx is a zip archive; the document body lives in word/document.xml. Each
run of visible text sits in a <w:t> element nested inside a <w:p> paragraph
(including paragraphs inside table cells). Uses only the standard library.

A .docx is attacker-shaped input, so extraction is bounded three ways that do
not overlap: per-member zip METADATA screens before anything is decompressed,
a refusal of word/document.xml if it declares a DTD, and a cap on the
accumulated visible text as it is built.

The DTD refusal is scoped to word/document.xml because that is the only member
this module ever decompresses or parses. A DTD in any other member is inert --
never screened, but never reached either. If a future change starts parsing a
second member, that member needs its own screen, and the row named
test_a_dtd_in_an_unparsed_member_is_inert is what will say so.
"""

import xml.etree.ElementTree as ET
import xml.parsers.expat
import zipfile
import zlib

# Transitional and Strict WordprocessingML use the same element names under
# different namespace URIs. Any other namespace is refused, not read as empty.
_WML_NAMESPACES = (
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
)
_MC_NS = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


def _wml_name(tag):
    """The local name of a WordprocessingML element in either namespace, or
    None for anything else (another namespace, or no namespace at all)."""
    if not isinstance(tag, str) or not tag.startswith("{"):
        return None
    namespace, _, local = tag[1:].partition("}")
    return local if namespace in _WML_NAMESPACES else None


def _children_to_read(node):
    """Children to visit. mc:AlternateContent holds the SAME content in
    alternative renderings (Choice for newer consumers, Fallback for older
    ones), so exactly one branch is read: the first Choice, or the first
    Fallback when there is no Choice."""
    if node.tag != _MC_NS + "AlternateContent":
        return list(node)
    for wanted in ("Choice", "Fallback"):
        for child in node:
            if child.tag == _MC_NS + wanted:
                return [child]
    return []

# Run children that stand for a character but carry no <w:t> text. w:sym is
# left out on purpose: its glyph is a font-specific code with no plain-text
# equivalent.
_RUN_SEPARATORS = {
    "tab": "\t",
    "ptab": "\t",
    "br": "\n",
    "cr": "\n",
    "noBreakHyphen": "-",
}


DEFAULT_MAX_BYTES = 384000
DEFAULT_MAX_RATIO = 100
DEFAULT_MAX_TEXT_CHARS = 384000
_ALLOWED_COMPRESSION = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)


def _assert_within_cap(payload, name, max_bytes):
    """Reject a member whose ACTUAL decompressed size exceeds the cap.

    Defense-in-depth, deliberately kept even though it is unreachable through
    stdlib zipfile: ZipExtFile slices every read to the member's declared
    remaining length (it seeds _left from zinfo.file_size and does
    data = data[:self._left] before the CRC is even updated). Do NOT restate
    this guarantee in terms of a Bad CRC-32 error -- the CRC field is
    attacker-controlled, and an attacker who understates file_size can simply
    supply the CRC of the truncated prefix.

    Note the limit of the slice as well: it bounds output at the DECLARED
    size, which is itself attacker-controlled central-directory data. It is no
    defense against a member declaring an enormous size -- that is what the
    max_bytes and max_ratio metadata screens are for.
    """
    if len(payload) > max_bytes:
        raise ValueError(
            "docx member %s expanded past the %d byte cap (declared size "
            "understated the real payload)" % (name, max_bytes))


def _assert_no_dtd(payload, name):
    """Refuse word/document.xml if it declares a DTD, BEFORE it is parsed.

    This function's ONLY call site is word/document.xml, the only member this
    module ever decompresses, so what it delivers is a MEMBER-level guarantee
    and not an archive-level one. No other member needs a DTD screen because
    no other member is ever decompressed or parsed: a DTD sitting in
    word/styles.xml is inert because it is never reached, NOT because it was
    screened. Those are different claims and only the second one is true here,
    so this docstring states the narrower one precisely.

    An internal DTD general entity is the one XML construct that makes visible
    text arbitrarily larger than the bytes that carried it, and every other
    guard in this module is a BYTE guard that runs before the expansion
    happens. Measured: a 358-byte archive whose word/document.xml declares
    468 bytes at 2.07:1 passes the declared-size screen, the ratio screen and
    the bounded raw read, and then expands to 500,000 characters.

    STRUCTURAL, not textual. A raw-bytes search for the ASCII literal
    "<!DOCTYPE" is bypassed by any encoding whose bytes are not
    ASCII-compatible -- measured, a UTF-16 word/document.xml expanded to 50,000
    characters while `b"<!DOCTYPE" in payload` was False, in both the BOM and
    the raw UTF-16-LE form. expat decodes the declared encoding itself, so
    asking it is encoding-independent. It is also free of the false rejection a
    byte search carries: CDATA content containing "<!DOCTYPE" is character
    data, and expat classifies it as such.

    It must use xml.parsers.expat directly. The C-accelerated
    xml.etree.ElementTree.XMLParser (the CPython default) has NO .parser
    attribute, so StartDoctypeDeclHandler cannot be installed through
    ElementTree.

    The handler fires on the <!DOCTYPE token, before the internal subset is
    read, so nothing has been expanded on the way to the refusal.

    ECMA-376 Part 2 (OPC) forbids DTD declarations in package parts, so a real
    Word document never carries one and this cannot false-reject genuine Word
    output. That is the basis for the no-false-rejection claim. The test
    fixtures are generated synthetically rather than taken from real Word
    files, so the claim rests on the OPC prohibition rather than on a
    measurement of real documents.

    This is a SEPARATE parse from the one that builds the tree. Measured cost:
    1.1 ms on a 425,058-byte document (4.0 ms -> 5.1 ms).
    """
    parser = xml.parsers.expat.ParserCreate()

    def _refuse(*_args):
        raise ValueError(
            "docx member %s declares a DTD (DOCTYPE). DTD entity expansion "
            "can make visible text arbitrarily larger than the bytes that "
            "carried it, defeating every byte-level cap, so a DTD is refused "
            "outright. OPC package parts may not declare one." % name)

    parser.StartDoctypeDeclHandler = _refuse
    try:
        parser.Parse(payload, True)
    except (xml.parsers.expat.ExpatError, LookupError) as exc:
        # LookupError: a declared encoding expat does not know.
        raise ValueError(
            "docx member %s is not well-formed XML: %s" % (name, exc))


def _visible_text(root, max_text_chars, name):
    """Join paragraph text, bounding the ACCUMULATED total as it is built.

    EACH <w:t> BELONGS TO ITS NEAREST ENCLOSING <w:p>, AND TO NO OTHER. That is
    not a refinement -- it is the difference between correct output and both a
    correctness bug and an expansion vector, because <w:p> elements NEST in
    real Word output: a text box embeds a whole paragraph inside a run via
    <w:txbxContent>.

    Element.iter() yields self plus ALL descendants, so the obvious
    implementation (for each <w:p>, join every descendant <w:t>) emits nested
    text once per ANCESTOR paragraph. Measured:

      - Correctness: a text-box document extracted as
        ['Paragraph before the box.TEXT INSIDE THE BOX', 'TEXT INSIDE THE BOX',
        'Paragraph after the box.'] -- the box's text duplicated AND glued onto
        the preceding paragraph, in a tool whose contract is a
        verbatim-grounded digest.
      - Expansion: with NO DTD anywhere, a 452-byte archive whose member is
        9,488 bytes at 29.7:1 passed every metadata screen and the DTD refusal
        and produced 164,039 characters (17.3x the member); at depth 80 a
        596-byte archive produced 648,079 (34.5x). Growth is quadratic in
        nesting depth. With nearest-paragraph ownership the same documents
        produce 8,039 and 16,079 -- under 1x the member.

    So max_text_chars is NOT merely belt-and-braces. Do not describe it as
    unreachable by a legitimate document, and do not "simplify" this back to
    paragraph.iter().

    State the residual honestly: this bounds what is RETURNED, not what the
    parser allocated. By the time it runs, ET.fromstring has already built the
    tree. The byte cap on the input is what bounds parse-time memory. The
    guarantee is "no DTD, nearest-paragraph ownership, and bounded output", not
    "the parser is safe".
    """
    # ONE ITERATIVE PRE-ORDER PASS, carrying the nearest enclosing <w:p> DOWN.
    # This replaced a parent-map plus a walk-UP from every <w:t>. That walk
    # was QUADRATIC in nesting depth against a document that stays inside
    # every cap: <w:t> nodes at increasing depth beneath NON-paragraph
    # wrappers (w:sdt, w:hyperlink) each walk their whole ancestor chain.
    # Measured, one paragraph, n runs at depths 1..n, ancestor steps and wall
    # clock:
    #
    #     n=200   20,500 steps  0.003s      n=1600  1,284,000 steps  0.183s
    #     n=400   81,000 steps  0.011s      n=3200  5,128,000 steps  0.716s
    #     n=800  322,000 steps  0.045s      n=6400 20,496,000 steps  3.703s
    #
    # At n=6400 the input is 243,379 bytes -- UNDER the 384,000 cap -- and the
    # output is 6,400 characters. So 243 KB of legitimate-looking XML yielding
    # 6 KB of text cost 3.7 seconds inside summarize_file. The byte and
    # character caps do not bound it, because neither bytes nor characters are
    # what grows.
    #
    # This pass visits each node once: 0.0013s / 0.0026s / 0.0057s / 0.0110s /
    # 0.0229s for n = 800 / 1600 / 3200 / 6400 / 12800 -- linear, and 336x
    # faster than the walk-up at n=6400.
    #
    # ITERATIVE, NOT RECURSIVE, deliberately: a recursive pass is simpler and
    # marginally faster, but depth is attacker-controlled and it raises
    # RecursionError on exactly the documents this exists to survive. Verified
    # at depth 5000 with sys.setrecursionlimit(1000).
    #
    # Ownership semantics are UNCHANGED -- verified identical on all eight
    # shapes that matter: flat runs, deep non-paragraph wrappers, a text box
    # (<w:p> inside <w:p>), two sibling paragraphs, an empty <w:t/>, a
    # hyperlink wrapper, a <w:t> outside any paragraph, and document order.
    #
    # The ORPHAN shape (the `owner is None` branch below) is covered by the
    # fixture of test_word_text_box_paragraph_is_not_duplicated, which
    # includes a <w:t> outside every <w:p>. Correct ownership drops the
    # orphan, so the expected list is unchanged, while a traversal that
    # attaches orphan text to the last-seen paragraph returns
    # 'TEXT INSIDE THE BOXORPHAN OUTSIDE EVERY PARAGRAPH' and fails that test.
    #
    # SEPARATORS. A tab, a soft break or a carriage return inside a run carries
    # no <w:t>, so ignoring it glued "12", a tab and "34" into "1234". They are
    # emitted from _RUN_SEPARATORS, but ONLY as a child of a run (w:r): a
    # <w:tab> inside <w:tabs> in paragraph properties defines a tab STOP and is
    # not a character. The flag travels down with the owner, one level only.
    owned, order = {}, []
    stack = [(root, None, False)]
    while stack:
        node, owner, in_run = stack.pop()
        name = _wml_name(node.tag)
        if name == "p":
            owner = node
            if id(owner) not in owned:
                owned[id(owner)] = []
                order.append(owner)
        elif owner is not None:
            if name == "t":
                owned[id(owner)].append(node.text or "")
            elif in_run and name in _RUN_SEPARATORS:
                owned[id(owner)].append(_RUN_SEPARATORS[name])
        is_run = name == "r"
        for child in reversed(_children_to_read(node)):
            stack.append((child, owner, is_run))

    lines, total = [], 0
    for paragraph in order:
        text = "".join(owned.get(id(paragraph), [])).strip()
        if not text:
            continue
        total += len(text) + (1 if lines else 0)
        if total > max_text_chars:
            raise ValueError(
                "docx member %s visible text exceeded the %d character cap "
                "(reached %d). Documents past the cap are REJECTED, not "
                "truncated -- split the document or extract a section."
                % (name, max_text_chars, total))
        lines.append(text)
    return "\n".join(lines)


def _screen_member(info, max_bytes, max_ratio):
    """Metadata-only screen of one archive member. Pure function of the
    central-directory entry -- it never decompresses anything, so calling it
    twice on the same member is free and idempotent."""
    # BZIP2 and LZMA decompress whole blocks BEFORE ZipExtFile slices the
    # result to the declared size, so a small declared size does not bound
    # their allocation. Real Word output is STORED or DEFLATED only.
    if info.compress_type not in _ALLOWED_COMPRESSION:
        raise ValueError(
            "docx member %s uses compression method %d; only STORED and "
            "DEFLATED are accepted" % (info.filename, info.compress_type))
    if info.file_size > max_bytes:
        raise ValueError(
            "docx member %s declared size %d exceeds the %d byte cap"
            % (info.filename, info.file_size, max_bytes))
    if info.file_size > 0 and info.compress_size == 0:
        raise ValueError(
            "docx member %s compression ratio is infinite "
            "(declared size %d, compressed size 0)"
            % (info.filename, info.file_size))
    if info.compress_size > 0:
        ratio = info.file_size / info.compress_size
        if ratio > max_ratio:
            raise ValueError(
                "docx member %s compression ratio %.1f:1 exceeds the "
                "%d:1 limit" % (info.filename, ratio, max_ratio))


def extract_text(path, max_bytes=DEFAULT_MAX_BYTES,
                 max_ratio=DEFAULT_MAX_RATIO,
                 max_text_chars=DEFAULT_MAX_TEXT_CHARS) -> str:
    """Return the visible text of a .docx, one paragraph per line.

    `path` is a file path, an already-open binary handle, or a BytesIO -- the
    non-path forms let file_tools validate containment and identity ONCE and
    hand the already-bounded bytes down, instead of this function re-opening
    by name.

    Containment, in order: every member whose name ends in ".xml" or ".rels"
    is screened on METADATA before anything is decompressed (a compression
    method other than STORED or DEFLATED, declared file_size
    over the cap, or a compression ratio over max_ratio, or a positive declared
    size with zero compressed size = infinite ratio) -- and word/document.xml
    is screened again immediately before it is opened, so that what is opened
    is always screened BY CONSTRUCTION; word/document.xml is then read BOUNDED;
    its actual length is re-checked; it is refused if it declares a DTD; and
    the visible text accumulated from it is capped.

    Members carrying neither suffix -- media parts, in practice -- are NOT
    metadata-screened. That is deliberate: the requirement is "cap any member
    this module parses or decompresses", not "any member". Screening every
    member would reject a legitimate Word document whose embedded image
    exceeds max_bytes even though no image is ever parsed. An XML part
    carrying some other filename is therefore unscreened -- it is also never
    opened, which is what bounds the risk. If this module ever opens a second
    member, that design decision must be revisited BEFORE the change lands.

    Screening is PER MEMBER, not cumulative: each member is judged against
    max_bytes on its own, and an archive of many valid members is not refused
    for their sum. That is sufficient here because only word/document.xml is
    ever decompressed; a caller that decompressed every member would need a
    running total as well.

    The defaults accept real Word output with room to spare: a measured Word
    document carried 26 members, a largest member of 46,187 bytes, and a
    worst compression ratio of 20.8:1.

    Malformed XML raises ValueError (from the DTD prescreen), not the
    ElementTree ParseError this module used to surface. An archive zipfile
    cannot read (not a zip, no word/document.xml, bad CRC, encrypted member)
    is also a ValueError, never an empty string.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                # ".rels" parts ARE XML -- the OPC relationship parts
                # (_rels/.rels, word/_rels/document.xml.rels) carry XML but do not
                # end in ".xml". Screening only ".xml" left every relationship part
                # uncapped, and _rels/.rels is the FIRST member of a real Word file.
                # The intent is to cap any XML member, so both suffixes are
                # screened.
                if not info.filename.lower().endswith((".xml", ".rels")):
                    continue
                _screen_member(info, max_bytes, max_ratio)
            # DESIGN DECISION. The sweep above identifies XML by SUFFIX, so an XML
            # part carrying some other filename is not capped by it. Widening the
            # sweep to EVERY member was considered and rejected: it would reject a
            # legitimate Word file whose media part exceeds max_bytes, even though
            # no media part is ever parsed. Reading [Content_Types].xml to classify
            # members was also rejected -- it means parsing a member in order to
            # decide how to guard members.
            #
            # The guarantee is therefore "cap any member this module parses or
            # decompresses", not "cap any XML member". It is made STRUCTURAL here
            # rather than asserted: screening happens on the way to the open, so
            # "what we open, we screened" holds by construction. An `if target
            # not in screened: raise` guard would be the weaker choice --
            # word/document.xml ends in ".xml" and is therefore always swept, so
            # that branch could never fire and would read as coverage while
            # testing nothing.
            #
            # getinfo raises KeyError for an absent member exactly as archive.open
            # did, so an archive with no word/document.xml is unchanged. Screening
            # the target a second time is idempotent and decompresses nothing.
            target = archive.getinfo("word/document.xml")
            _screen_member(target, max_bytes, max_ratio)
            with archive.open(target) as member:
                document_xml = member.read(max_bytes + 1)
    except (zipfile.BadZipFile, KeyError, zlib.error, EOFError,
            RuntimeError, NotImplementedError) as exc:
        # zipfile reports an unreadable archive, an absent word/document.xml,
        # a bad CRC, an encrypted member and an unsupported method with its
        # own exception types. Every other refusal here is a ValueError, so
        # these are converted: a caller catches one type, and none of them
        # can come back as empty text.
        raise ValueError(
            "docx archive could not be read as a zip archive: %s: %s"
            % (type(exc).__name__, exc)) from exc
    _assert_within_cap(document_xml, "word/document.xml", max_bytes)
    _assert_no_dtd(document_xml, "word/document.xml")

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        # The prescreen creates its expat parser WITHOUT namespace
        # processing, so an undeclared namespace prefix is well-formed to
        # expat and reaches HERE, where ElementTree rejects it with
        # ParseError -- a SyntaxError subclass, not the ValueError this module
        # promises every caller. Wrapping the prescreen alone would leave
        # this seam leaking a different exception type.
        raise ValueError(
            "docx member word/document.xml could not be parsed: %s" % exc)
    if _wml_name(root.tag) != "document":
        raise ValueError(
            "docx member word/document.xml has an unsupported WordprocessingML "
            "namespace or root element (%s); only Transitional and Strict "
            "WordprocessingML documents are read" % root.tag)
    return _visible_text(root, max_text_chars, "word/document.xml")
