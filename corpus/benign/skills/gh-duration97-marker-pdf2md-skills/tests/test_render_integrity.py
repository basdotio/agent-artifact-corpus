"""Authored, public regression examples; no excerpts from user documents."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from content_signals import output_integrity, structure_risks, table_content_risks, table_stage_risks
from convert_pdf import main, table_options
from reading_copy import layout_risks
from run_diagnostics import diagnose, install_lock_observer
from table_signals import table_shape_risks, table_grids
from test_quality import make_pdf


class RenderIntegrityTests(unittest.TestCase):
    def test_autolink_footnote_is_present(self):
        page = {'blocks': [{'type': 'Footnote', 'text': '⑤ Source: https://example.org/data?a=5&b=6 .'}]}
        self.assertEqual(layout_risks('<sup>⑤</sup> Source: <https://example.org/data?a=5&b=6> .', page), [])

    def test_inline_link_and_entity_are_present(self):
        page = {'blocks': [{'type': 'Footnote', 'text': '⑥ Source: https://example.org/data_set?a=1&b=2 .'}]}
        self.assertEqual(layout_risks('<sup>⑥</sup> Source: [https://example.org/data\\_set?a=1&amp;b=2](https://example.org/data_set?a=1&b=2) .', page), [])

    def test_wrapped_url_is_content_even_if_link_syntax_is_invalid(self):
        page = {'blocks': [{'type': 'Footnote', 'text': '① Source: https://example.org/abc def.html .'}]}
        self.assertEqual(layout_risks('① Source: <https://example.org/abc def.html> .', page), [])
        self.assertTrue(layout_risks('① Source: <https://example.org/abc> .', page))

    def test_missing_footnote_tail_is_detected(self):
        page = {'blocks': [{'type': 'Footnote', 'text': '⑦ This complete note has a significant ending.'}]}
        self.assertTrue(layout_risks('⑦ This complete note has', page))
        self.assertTrue(layout_risks('Some unrelated paragraph.', page))

    def test_short_note_with_formatting_still_compares(self):
        page = {'blocks': [{'type': 'Footnote', 'text': '① A short authored source note.'}]}
        self.assertEqual(layout_risks('① **A short authored source note.**', page), [])
        self.assertTrue(layout_risks('Other prose', {'blocks': [{'type': 'Footnote', 'text': '①略。'}]}))

    def test_ignored_note_is_not_treated_as_render_loss(self):
        self.assertEqual(layout_risks('', {'blocks': [{'type': 'Footnote', 'text': 'Ignored long note', 'ignored': True}]}), [])

    def test_value_missing_from_table_is_not_hidden_by_prose(self):
        page = {'blocks': [{'type': 'Table', 'text': 'Item 0.031 0.008'}]}
        body = '| Item | Estimate |\n|---|---|\n| A | 0.031 |\n\nProse mentions 0.008.'
        self.assertTrue(any('0.008' in flag for flag in table_content_risks(body, page)))

    def test_numeric_multiplicity_is_checked(self):
        page = {'blocks': [{'type': 'Table', 'text': 'A 0.008 B 0.008'}]}
        body = '| A | B |\n|---|---|\n| 0.008 | |'
        self.assertTrue(any('0.008×1' in flag for flag in table_content_risks(body, page)))

    def test_equal_width_shifted_cells_are_detected_from_html(self):
        source = '<table><tr><td>A</td><td>0.031</td><td>0.008</td></tr></table>'
        output = '| 0.031 | A | 0.008 |\n|---|---|---|'
        page = {'blocks': [{'type': 'Table', 'html': source, 'text': 'A 0.031 0.008'}]}
        self.assertTrue(any('位置/内容不同' in flag for flag in table_content_risks(output, page)))

    def test_merged_html_preserves_all_numbers_and_positions(self):
        source = '<table><tr><th rowspan="2">Item</th><th colspan="2">Model</th></tr><tr><th>Estimate</th><th>SE</th></tr><tr><td>A</td><td>0.031</td><td>0.008</td></tr></table>'
        page = {'blocks': [{'type': 'Table', 'html': source}]}
        flags = table_content_risks(source, page)
        self.assertFalse(any('不足' in flag or '位置/内容不同' in flag for flag in flags))
        self.assertEqual(table_shape_risks(source), [])

    def test_markdown_ragged_table_is_detected(self):
        self.assertTrue(table_shape_risks('| A | B |\n|---|---|\n| x | y | z |'))

    def test_escaped_and_code_pipes_are_not_columns(self):
        self.assertEqual(table_shape_risks('| A | B |\n|---|---|\n| x\\|y | `a|b` |'), [])

    def test_fenced_table_example_is_ignored(self):
        self.assertEqual(table_shape_risks('```text\n| A | B |\n|---|---|\n| x | y | z |\n```'), [])

    def test_unclosed_html_and_invalid_spans_are_detected(self):
        for source in ['<table><tr><td>A', '<table><tr><td rowspan="4">A</td></tr></table>', '<table><tr><td colspan="bad">A</td></tr></table>']:
            self.assertTrue(table_shape_risks(source))

    def test_rowspan_overlap_is_detected(self):
        source = '<table><tr><td>A</td><td rowspan="2">B</td></tr><tr><td colspan="2">C</td></tr></table>'
        self.assertTrue(any('重叠' in flag for flag in table_shape_risks(source)))

    def test_html_and_grid_equivalence(self):
        self.assertEqual(table_grids('<table><tr><td>A</td><td>2</td></tr></table>'), table_grids('| A | 2 |\n|---|---|'))

    def test_regular_papers_default_to_html_when_supported(self):
        self.assertEqual(table_options(' --html_tables_in_markdown BOOLEAN')[0], ['--html_tables_in_markdown', 'true'])
        self.assertEqual(table_options(' --html_tables_in_markdown', 'markdown')[0], [])
        self.assertTrue(table_options('old CLI')[2])
        with self.assertRaises(RuntimeError):
            table_options('old CLI', 'html')

    def test_integrity_checks_allow_asset_relocation_but_reject_numeric_loss(self):
        self.assertEqual(output_integrity('Text ![](old.png) 0.008', 'Text ![](images/new.png) 0.008'), [])
        self.assertTrue(output_integrity('Text 0.008', 'Text'))
        self.assertEqual(output_integrity('![Authored caption](<old image(1).png>)', '![Authored caption](images/new.png)'), [])
        self.assertTrue(output_integrity('![Authored caption](old.png)', '![](new.png)'))

    def test_heading_inconsistency_and_duplicate_list_number_are_only_signals(self):
        pages = [(1, '## 一、First\n1. 1.Authored reference'), (2, '#### 二、Second')]
        flags = structure_risks(pages)
        self.assertTrue(any('层级' in flag for item in flags for flag in item['risks']))
        self.assertTrue(any('重复编号' in flag for item in flags for flag in item['risks']))
        self.assertEqual(pages[0][1], '## 一、First\n1. 1.Authored reference')

    def test_error_classification_prioritizes_specific_cause(self):
        cases = [
            ('filelock._error.Timeout: The file lock llamacpp_server.lock could not be acquired.', 'cache_lock_timeout'),
            ('PermissionError [WinError 5] cache/llamacpp_server.lock', 'permission_denied'),
            ('[WinError 32] sharing violation', 'cache_lock_timeout'),
            ('llama-server not found', 'engine_missing'),
            ('ModuleNotFoundError: No module named filelock', 'dependency_error'),
            ('TimeoutExpired: conversion interrupted', 'conversion_timeout'),
        ]
        for text, expected in cases:
            self.assertEqual(diagnose(text)['code'], expected)

    def test_processing_loss_is_separate_from_render_loss(self):
        stages = [{'before_table_processing': [{'pdf_page': 4, 'blocks': [{'html': '<table><tr><td>0.008</td></tr></table>'}]}],
                   'after_table_processing': [{'pdf_page': 4, 'blocks': [{'html': '<table><tr><td></td></tr></table>'}]}]}]
        self.assertIn('0.008', table_stage_risks(stages)[0]['risks'][0])

    def test_duplicate_number_in_two_tables_cannot_hide_loss(self):
        page = {'blocks': [{'type': 'Table', 'text': 'A 0.008'}, {'type': 'Table', 'text': 'B 0.008'}]}
        body = '| A | SE |\n|---|---|\n| x | |\n\n| B | SE |\n|---|---|\n| y | 0.008 |\n| z | 0.008 |'
        self.assertTrue(any('第1个' in flag and '0.008' in flag for flag in table_content_risks(body, page)))

    def test_missing_layout_table_is_reported(self):
        self.assertTrue(any('数量不同' in flag for flag in table_content_risks('Prose only', {'blocks': [{'type': 'Table', 'text': 'A 0.008'}]})))

    def test_lock_observer_keeps_acquire_release_semantics(self):
        class Lock:
            is_locked = False
            calls = 0
            def acquire(self, *args, **kwargs):
                self.calls += 1
                self.is_locked = True
                return self
            def release(self, *args, **kwargs):
                self.calls += 1
                self.is_locked = False
        lock = Lock()
        with patch.dict(sys.modules, {'filelock': SimpleNamespace(BaseFileLock=Lock)}), contextlib.redirect_stderr(io.StringIO()):
            install_lock_observer()
            self.assertIs(lock.acquire(timeout=1), lock)
            self.assertTrue(lock.is_locked)
            lock.release()
            self.assertFalse(lock.is_locked)
            self.assertEqual(lock.calls, 2)

    def test_full_wrapper_keeps_raw_pages_and_independent_review_status(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); pdf = folder/'authored.pdf'; output = folder/'result'
            make_pdf(pdf, [{'text': 'First page of an authored document.'}, {'text': 'Second page of an authored document.'}])
            raw_text = '{0}' + '-'*48 + '\n\nText 1\n\n{1}' + '-'*48 + '\n\nText 2\n'
            def engine(command, dest, timeout):
                raw = dest/'raw/authored'; raw.mkdir()
                (raw/'authored.md').write_text(raw_text, encoding='utf-8')
                (raw/'authored_meta.json').write_text(json.dumps({'page_stats': [{'page_id': 0}, {'page_id': 1}]}), encoding='utf-8')
                return subprocess.CompletedProcess(command, 0, '', '')
            help_text = '--output_dir --output_format --paginate_output --mode --html_tables_in_markdown'
            with patch('convert_pdf.marker_help', return_value=(['fake-marker'], help_text, 'test')), patch('convert_pdf.configure_backend', return_value={}), patch('convert_pdf.run_logged', side_effect=engine), patch.object(sys, 'argv', ['convert_pdf', str(pdf), '--reading', '--output', str(output)]), contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                # Test doubles must not change a subsequent invocation's environment.
                with patch.dict('os.environ', {}):
                    self.assertEqual(main(), 0)
            self.assertEqual((output/'raw/authored/authored.md').read_text(encoding='utf-8'), raw_text)
            text = (output/'authored.md').read_text(encoding='utf-8')
            self.assertIn('pdf-page-000002', text)
            q = json.loads((output/'quality_report.json').read_text(encoding='utf-8'))
            self.assertTrue(q['page_boundaries_verified'])
            self.assertEqual(q['layout_comparison_status'], 'unavailable')
            self.assertEqual(q['review_status']['tables'], 'unreviewed')
            self.assertFalse(q['printed_page_mapping_complete'])
            self.assertEqual(q['ocr_text_status'], 'unreviewed')


if __name__ == '__main__':
    unittest.main()
