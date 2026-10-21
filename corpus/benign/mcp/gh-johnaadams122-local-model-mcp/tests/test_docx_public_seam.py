r"""The DEPLOYED seam: the MCP file tools' .docx read path.

Every other DOCX row in this repo tests local_llm.docx_text in isolation.
These rows exercise the path a user actually reaches: the public MCP file
tools reading a .docx. BOTH public tools get a clean-DOCX control:
summarize_file and extract_json_file reach _read_text on separate call
paths, and a refusal row proves nothing about a tool that refuses
everything.

SELF-CONTAINED by design: builds its own bomb rather than importing helpers
from tests/test_docx_text.py, so the two files can be edited independently.
"""
import os
import tempfile
import unittest
import zipfile
import zlib
from unittest import mock

from local_llm import file_tools, ollama_client

_BOMB_XML = (
    '<?xml version="1.0"?>\n'
    '<!DOCTYPE d [\n'
    '  <!ENTITY a "AAAAAAAAAA">\n'
    '  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">\n'
    '  <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">\n'
    ']>\n'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/'
    'wordprocessingml/2006/main">'
    '<w:body><w:p><w:r><w:t>&c;</w:t></w:r></w:p></w:body></w:document>'
)
_CLEAN_XML = (
    '<?xml version="1.0"?>\n'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/'
    'wordprocessingml/2006/main">'
    '<w:body><w:p><w:r><w:t>hello from a real document</w:t></w:r>'
    '</w:p></w:body></w:document>'
)


def _response(text):
    handle = mock.Mock()
    handle.status_code = 200
    handle.json.return_value = {"response": text}
    return handle


class DocxPublicSeam(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self._allow(self.root)

    def _allow(self, directory):
        """Patch whichever containment mechanism file_tools exposes.

        The current module keeps its allowlist in _ROOTS. Older versions
        exposed a single ALLOWLIST_ROOT instead. Binding to whichever name is
        present keeps this suite focused on the DOCX seam it exists to prove,
        rather than failing for a containment-API reason unrelated to it.
        """
        real = os.path.realpath(directory)
        if hasattr(file_tools, "_ROOTS"):
            patcher = mock.patch.object(file_tools, "_ROOTS", [real])
        else:
            patcher = mock.patch.object(file_tools, "ALLOWLIST_ROOT", real)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _docx(self, document_xml, name="doc.docx"):
        path = os.path.join(self.root, name)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document_xml)
        return path

    def _docx_declaring_size(self, declared, name="big.docx"):
        """A clean archive plus a member whose DECLARED size is past the cap.

        The metadata is FORGED rather than written, and that is load-bearing.
        `_docx` above writes ZIP_STORED, so a genuinely over-cap member
        produces a file of the same size -- which file_tools rejects on its
        OWN 384 KB file cap, with a different message, before `extract_text`
        is ever reached. The row would then pass for a reason that has nothing
        to do with the member screen it exists to prove. Forging keeps the
        archive tiny and puts the ONLY violation in the central directory.
        This matters MORE at the boundary value the callers pass
        (384,001 = cap+1): a real member of that size is within a byte of
        file_tools' own cap, so writing it rather than forging it would land
        the row on whichever cap fires first.

        compress_size is declared//2, so the ratio is 2.0 and cannot trip the
        ratio branch -- this fixture isolates the declared-size branch.
        """
        path = self._docx(_CLEAN_XML, name)
        forged = zipfile.ZipInfo("word/big.xml")
        forged.file_size, forged.compress_size = declared, declared // 2
        real_infolist = zipfile.ZipFile.infolist

        def infolist_with_forged(self_archive):
            return list(real_infolist(self_archive)) + [forged]

        return path, mock.patch.object(
            zipfile.ZipFile, "infolist", infolist_with_forged)

    def _docx_over_ratio(self, name="ratio.docx"):
        """The ratio twin of the helper above, isolating the OTHER branch.

        file_size 200,000 is comfortably UNDER the 384,000 declared-size cap,
        so the declared-size branch cannot fire first. If both screens were
        tripped at once the row could not tell which one refused it -- the
        single-branch-isolation rule this suite applies throughout.

        The ratio sits just past the limit on purpose. A compress_size of
        1,000 would make the ratio 200:1 against a 100:1 limit -- FAR outside
        the boundary, so the row could not distinguish the shipped 100:1
        contract from a seam wired at anything up to 199:1. Both refuse a
        200:1 member. Measured: at 200000/1980 the ratio is 101.0101:1, which
        the correct seam refuses and a seam wired at 199:1 ACCEPTS -- so the
        row fails against exactly the mis-wiring it exists to exclude. A
        fixture far past the limit cannot pin WHERE the limit is.
        """
        path = self._docx(_CLEAN_XML, name)
        forged = zipfile.ZipInfo("word/ratio.xml")
        forged.file_size, forged.compress_size = 200000, 1980
        real_infolist = zipfile.ZipFile.infolist

        def infolist_with_forged(self_archive):
            return list(real_infolist(self_archive)) + [forged]

        return path, mock.patch.object(
            zipfile.ZipFile, "infolist", infolist_with_forged)

    @mock.patch.object(ollama_client.requests, "post")
    def test_a_clean_docx_STILL_READS_through_summarize_file(self, mock_post):
        # CONTROL for summarize_file, and it is load-bearing. Without it the
        # rows below would all pass just as well if the .docx read path were
        # broken outright, which would prove nothing about the screens.
        mock_post.return_value = _response("a fine summary")
        out = file_tools.summarize_file(self._docx(_CLEAN_XML), max_words=20)
        self.assertEqual(out["summary"], "a fine summary")

    @mock.patch.object(ollama_client.requests, "post")
    def test_a_clean_docx_EXTRACTS_through_extract_json_file(self, mock_post):
        # CONTROL for the OTHER public tool, and it is not symmetry for its own
        # sake. Without it extract_json_file appears in this file exactly once,
        # in a refusal row -- so an implementation that refuses EVERY .docx
        # through it, with a ValueError whose message happens to name a DTD,
        # passes the whole file. summarize_file's control cannot cover that:
        # the two tools reach _read_text on separate call paths.
        #
        # It is also the DATAFLOW row for this tool. extract_json_file NULLS any
        # scalar not present verbatim (normalized) in the source text, so a read
        # path that returns "" or the wrong bytes cannot produce a populated
        # field with an EMPTY unverified_fields. Asserting the value, the empty
        # unverified_fields and the prompt together measures the read path
        # rather than the mock. The asserted string is the literal text of
        # _CLEAN_XML, which is what makes the verbatim check pass.
        mock_post.return_value = _response(
            '{"greeting": "hello from a real document"}')
        out = file_tools.extract_json_file(self._docx(_CLEAN_XML),
                                           {"greeting": "string"})
        self.assertEqual(out["fields"]["greeting"],
                         "hello from a real document")
        self.assertEqual(out["unverified_fields"], [])
        prompt = mock_post.call_args[1]["json"]["prompt"]
        self.assertIn("hello from a real document", prompt,
                      "the .docx text never reached the model call")

    def _docx_compressed(self, document_xml, compression, name):
        """`_docx` always writes ZIP_STORED. This writes the compression the
        caller asks for, which is the whole point of the row below."""
        path = os.path.join(self.root, name)
        with zipfile.ZipFile(path, "w", compression) as archive:
            archive.writestr("word/document.xml", document_xml)
        return path

    @mock.patch.object(ollama_client.requests, "post")
    def test_a_clean_DEFLATED_docx_SUCCEEDS_through_BOTH_public_tools(
            self, mock_post):
        """**Every other public success control in this file writes
        ZIP_STORED**, because `_docx` does, and the only other ZIP_DEFLATED
        archives at this seam are the corrupt ones -- where any exception is
        accepted. Without this row, a seam that rejects every valid DEFLATED
        `.docx`, in either tool, would pass the rest of the suite.

        That matters because **real Word documents are DEFLATED**; STORED is
        the artificial case this file's own fixtures happen to produce. The
        failure this excludes is the worst kind: not a bomb getting through,
        but every genuine user document being refused.

        Measured, the same body under both compressions:
            ZIP_STORED    declared 193, compressed 193, ratio 1.00
            ZIP_DEFLATED  declared 193, compressed 138, ratio 1.40
        Both extract to 'hello from a real document'. Note the ratio is 1.40,
        nowhere near the 100:1 limit -- this row is an ACCEPTANCE control and
        must not be confused with the ratio-screen rows.
        """
        path = self._docx_compressed(_CLEAN_XML, zipfile.ZIP_DEFLATED,
                                     "clean-deflated.docx")

        mock_post.return_value = _response("a fine summary")
        out = file_tools.summarize_file(path, max_words=20)
        self.assertEqual(out["summary"], "a fine summary",
                         "summarize_file refused a valid DEFLATED .docx")

        mock_post.return_value = _response(
            '{"greeting": "hello from a real document"}')
        out = file_tools.extract_json_file(path, {"greeting": "string"})
        self.assertEqual(out["fields"]["greeting"],
                         "hello from a real document",
                         "extract_json_file refused a valid DEFLATED .docx")
        self.assertEqual(out["unverified_fields"], [])

    @mock.patch.object(ollama_client.requests, "post")
    def test_a_docx_with_NO_document_xml_reaches_NO_MODEL(self, mock_post):
        """**Every other public-seam fixture in this file contains
        `word/document.xml`.** The library tests cover the absent member
        only by calling `extract_text` directly, so a `_read_text` wrapper
        that catches `KeyError` and returns `""` would leave every other test
        green while both public tools send an EMPTY digest to the model --
        the user gets a confident summary of nothing.

        Measured, identical on the path and BytesIO routes:
            KeyError: "There is no item named 'word/document.xml' in the
                       archive"

        `archive.getinfo` raises KeyError and `extract_text` now converts it to
        ValueError. The assertion still admits KeyError so this row keeps
        guarding the "no empty digest" property on its own.
        """
        path = os.path.join(self.root, "no-document.docx")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/styles.xml", "<styles/>")
            archive.writestr("[Content_Types].xml", "<Types/>")

        with self.assertRaises((KeyError, ValueError)):
            file_tools.summarize_file(path)
        with self.assertRaises((KeyError, ValueError)):
            file_tools.extract_json_file(path, {"total": "string"})

        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_entity_bomb_is_refused_through_summarize_file(self, mock_post):
        with self.assertRaisesRegex(ValueError, "declares a DTD"):
            file_tools.summarize_file(self._docx(_BOMB_XML))
        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_entity_bomb_is_refused_through_extract_json_file(self, mock_post):
        with self.assertRaisesRegex(ValueError, "declares a DTD"):
            file_tools.extract_json_file(self._docx(_BOMB_XML),
                                         {"total": "string"})
        mock_post.assert_not_called()

    def _corrupt_docx(self, compression, name):
        """A VALID archive with one byte flipped inside the member data.

        The central directory is untouched, so the archive OPENS cleanly and
        only the read fails -- which is the whole point: a whole-file
        truncation fails at open() and proves nothing about this seam.
        Measured at this file's fixture size (document.xml 1314 B):
        offset 97 lands inside the member data for BOTH compressions, and
        `open()` succeeds while `namelist()` returns word/document.xml.

        The archive is written HERE rather than through `self._docx`, and
        that is load-bearing: `_docx` always writes ZIP_STORED, so routing
        this through it would have produced a STORED archive for both loop
        iterations -- the deflate/`zlib.error` half would never have run and
        the row would have claimed coverage it did not have.
        """
        good = os.path.join(self.root, "good-" + name)
        with zipfile.ZipFile(good, "w", compression) as archive:
            archive.writestr("word/document.xml", _CLEAN_XML)
        raw = bytearray(open(good, "rb").read())
        raw[30 + len("word/document.xml") + 50] ^= 0xFF
        path = os.path.join(self.root, name)
        with open(path, "wb") as out:
            out.write(bytes(raw))
        return path

    @mock.patch.object(ollama_client.requests, "post")
    def test_MID_READ_corruption_reaches_NO_MODEL_through_both_public_tools(
            self, mock_post):
        """Mid-read corruption at the public entry points.

        The library tests drive mid-read corruption by calling
        `extract_text` DIRECTLY. Every other no-model row at this seam covers
        DTD, declared size and ratio -- all of which fail BEFORE any
        decompression. **This is the row that covers a failure arriving
        DURING `member.read()` at a public entry point.** Without it, an
        implementation that wraps the read in
        `except (zipfile.BadZipFile, zlib.error): return ""` would pass the
        rest of the suite and then hand the model an empty or partial digest
        of a corrupt document -- silent data loss presented to the user as a
        summary.

        Measured, both modes, both routes, all identical:
            ZIP_STORED   -> zipfile.BadZipFile: Bad CRC-32 for file
                            'word/document.xml'
            ZIP_DEFLATED -> zlib.error: Error -3 while decompressing data:
                            invalid distance too far back
        `open()` SUCCEEDS in both cases; the failure arrives at `read()`.

        NEITHER IS A ValueError, so a caller catching only `ValueError`
        does not catch these -- which is exactly why both are driven here
        rather than assumed to behave alike.
        """
        for compression, name in ((zipfile.ZIP_STORED, "crc.docx"),
                                  (zipfile.ZIP_DEFLATED, "deflate.docx")):
            path = self._corrupt_docx(compression, name)

            with self.assertRaises(
                    (ValueError, zipfile.BadZipFile, zlib.error),
                    msg="%s: summarize_file RETURNED for a corrupt archive "
                        "instead of raising" % name):
                file_tools.summarize_file(path)

            with self.assertRaises(
                    (ValueError, zipfile.BadZipFile, zlib.error),
                    msg="%s: extract_json_file RETURNED for a corrupt "
                        "archive instead of raising" % name):
                file_tools.extract_json_file(path, {"total": "string"})

        # THE LOAD-BEARING ASSERTION. Raising is not enough on its own --
        # what must never happen is a truncated digest reaching the model.
        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_an_OVERSIZED_member_is_refused_through_summarize_file(self, mock_post):
        # Without this row and the one below, the seam battery would cover
        # clean input, the DTD refusal and nested-paragraph traversal ONLY --
        # no METADATA-expansion rejection would reach the deployed path at
        # all. A file_tools seam wired with permissive max_bytes/max_ratio
        # would pass every other row here while letting a member that is
        # merely LARGE, or merely high-ratio, reach the model. Those are the
        # two metadata screens docx_text provides, and the deployed route
        # through file_tools._read_text is where they must be asserted.
        #
        # The declared size is what is screened, so the member must DECLARE past
        # the cap -- this uses the same forged-metadata helper the library rows
        # use, not a genuinely huge fixture (which would be slow and would trip
        # the ratio screen first, proving the wrong thing).
        #
        # The declared size is cap+1 on purpose. A value far past the 384,000
        # cap (say 400,000) would also be refused by a seam wired at anything
        # up to 399,999, so the row could not pin WHERE the cap is. Measured:
        # the correct seam refuses 384,001 and a 399,999-wired seam ACCEPTS
        # it, so the row fails against exactly that mis-wiring. compress_size
        # stays declared//2 (ratio 2.0), so the branch isolation is unchanged.
        path, forged = self._docx_declaring_size(384001)
        with forged:
            with self.assertRaisesRegex(ValueError, "declared size"):
                file_tools.summarize_file(path)
        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_an_OVER_RATIO_member_is_refused_through_extract_json_file(self, mock_post):
        # The ratio twin of the row above, through the OTHER public tool, so
        # neither screen nor either entry point is left unasserted on the
        # deployed path. Ratio and declared size are separate branches in
        # `_screen_member`; an implementation can lose one and keep the other.
        path, forged = self._docx_over_ratio()
        with forged:
            with self.assertRaisesRegex(ValueError, "compression ratio"):
                file_tools.extract_json_file(path, {"total": "string"})
        mock_post.assert_not_called()
    @mock.patch.object(ollama_client.requests, "post")
    def test_an_OVER_RATIO_member_is_refused_through_summarize_file(self, mock_post):
        # The two rows above are not a matrix on their own: summarize_file is
        # tested for declared size and extract_json_file for ratio.
        # ASYMMETRIC permissive wiring -- unbounded ratio for summarize_file,
        # unbounded bytes for extract_json_file -- would keep both rows green
        # along with every clean and DTD control, while each tool lost one
        # screen. This row and the next complete the tool-by-screen matrix so
        # both screens are asserted on both deployed entry points.
        path, forged = self._docx_over_ratio(name="ratio-summ.docx")
        with forged:
            with self.assertRaisesRegex(ValueError, "compression ratio"):
                file_tools.summarize_file(path)
        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_an_OVERSIZED_member_is_refused_through_extract_json_file(self, mock_post):
        # The fourth cell of the matrix: declared size through the OTHER tool.
        # cap+1, not a value far past the cap -- see the summarize_file twin.
        path, forged = self._docx_declaring_size(384001, name="big-extract.docx")
        with forged:
            with self.assertRaisesRegex(ValueError, "declared size"):
                file_tools.extract_json_file(path, {"total": "string"})
        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_NESTED_paragraphs_are_not_duplicated_through_summarize_file(
            self, mock_post):
        # The SECOND bound, through the public tool -- but see the note below:
        # this asserts NON-duplication, not that the cap fires.
        # DEPTH AND RUN LENGTH ARE LOAD-BEARING -- do not scale them up.
        # Correct traversal emits one run per paragraph: 20 markers, 600 chars.
        # Descendant-joining re-emits every descendant: 20*21/2 = 210 markers,
        # 6,300 chars. BOTH must stay under file_tools' 12,000-char chunk
        # threshold, or _read_text chunks and the assertion below reads a
        # reduce-stage prompt containing no markers at all -- and both must stay
        # under docx_text's 384,000-char text cap, or extract_text raises
        # ValueError before any model call and there is no prompt to inspect.
        #
        # (Depth 80 with 130-char runs, for example, gives 3,240 markers /
        # 421,279 chars on the descendant-joining traversal -- ABOVE the
        # 384,000 cap. That traversal would then raise ValueError instead of
        # producing a duplicated marker count, so the row could never fail
        # the way it is meant to.)
        mock_post.return_value = _response("a fine summary")
        body = ""
        for level in range(20, 0, -1):
            body = ('<w:p><w:r><w:t>%s</w:t></w:r>%s</w:p>'
                    % ("X" * 30, body))
        nested = (
            '<?xml version="1.0"?>\n'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            'wordprocessingml/2006/main"><w:body>' + body +
            '</w:body></w:document>')
        out = file_tools.summarize_file(self._docx(nested), max_words=20)
        self.assertEqual(out["summary"], "a fine summary")
        # 20 paragraphs, each owning its OWN run and no descendant's.
        prompt = mock_post.call_args[1]["json"]["prompt"]
        self.assertEqual(
            prompt.count("X" * 30), 20,
            "nested paragraphs were emitted once per ANCESTOR: the "
            "descendant-joining traversal is back")

    _STRICT_XML = _CLEAN_XML.replace(
        "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "http://purl.oclc.org/ooxml/wordprocessingml/main")
    _EMPTY_XML = _CLEAN_XML.replace(
        "<w:r><w:t>hello from a real document</w:t></w:r>", "")
    _UNKNOWN_NS_XML = _CLEAN_XML.replace(
        "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "urn:example:not-word")

    @mock.patch.object(ollama_client.requests, "post")
    def test_a_STRICT_ooxml_docx_reaches_the_model_through_BOTH_tools(
            self, mock_post):
        path = self._docx(self._STRICT_XML)
        mock_post.return_value = _response("a fine summary")
        out = file_tools.summarize_file(path, max_words=20)
        self.assertEqual(out["lines"], 1)
        self.assertIn("hello from a real document",
                      mock_post.call_args[1]["json"]["prompt"])
        mock_post.return_value = _response(
            '{"greeting": "hello from a real document"}')
        out = file_tools.extract_json_file(path, {"greeting": "string"})
        self.assertEqual(out["fields"]["greeting"],
                         "hello from a real document")

    @mock.patch.object(ollama_client.requests, "post")
    def test_a_docx_with_no_extractable_text_is_REFUSED_not_FULL_coverage(
            self, mock_post):
        # Used to return lines=0, coverage FULL and ask the model to summarize
        # nothing. An empty extraction from a .docx is not a read of content.
        path = self._docx(self._EMPTY_XML)
        with self.assertRaisesRegex(ValueError, "no extractable text"):
            file_tools.summarize_file(path)
        with self.assertRaisesRegex(ValueError, "no extractable text"):
            file_tools.extract_json_file(path, {"greeting": "string"})
        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_an_unsupported_namespace_docx_is_refused_by_BOTH_tools(
            self, mock_post):
        path = self._docx(self._UNKNOWN_NS_XML)
        with self.assertRaisesRegex(
                ValueError, "unsupported WordprocessingML namespace"):
            file_tools.summarize_file(path)
        with self.assertRaisesRegex(
                ValueError, "unsupported WordprocessingML namespace"):
            file_tools.extract_json_file(path, {"greeting": "string"})
        mock_post.assert_not_called()

    @mock.patch.object(ollama_client.requests, "post")
    def test_an_empty_PLAIN_TEXT_file_is_unchanged(self, mock_post):
        # The refusal is specific to .docx: an empty .txt really is empty.
        path = os.path.join(self.root, "empty.txt")
        open(path, "w").close()
        mock_post.return_value = _response("nothing to summarize")
        out = file_tools.summarize_file(path)
        self.assertEqual((out["lines"], out["coverage"]), (0, "FULL"))
