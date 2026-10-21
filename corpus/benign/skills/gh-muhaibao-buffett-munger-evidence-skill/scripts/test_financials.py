import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from collect_financials import discover, choose_child, stage_one


class FinancialDiscoveryTests(unittest.TestCase):
    def test_table_period_does_not_depend_on_old_filename(self):
        raw = b'''<table><tr><td>1999</td><td><a href="qtrly/links99.html">x</a></td>
        <td><a href="qtrly/links2stqtr99.html">x</a></td><td></td>
        <td><a href="1999ar/impnote99.html">x</a></td></tr></table>'''
        items = discover(raw)
        self.assertEqual([(i['year'],i['period']) for i in items],[(1999,'Q1'),(1999,'Q2'),(1999,'annual')])

    def test_empty_and_ambiguous_index_are_not_silent_success(self):
        with self.assertRaises(ValueError):
            discover(b'<html>Access denied</html>')
        with self.assertRaises(ValueError):
            discover(b'<tr><td>2024</td><td><a href="qtrly/a.pdf">a</a><a href="qtrly/b.pdf">b</a></td><td></td><td></td><td></td></tr>')

    def test_annual_selects_complete_report_not_related_essay(self):
        raw = b'<a href="2004ar.pdf">2004 Annual Report *</a><a href="/letters/options.pdf">op-ed piece</a>'
        self.assertEqual(choose_child(raw,'https://www.berkshirehathaway.com/2004ar/impnote04.html',{'year':2004,'period':'annual'}),'https://www.berkshirehathaway.com/2004ar/2004ar.pdf')

    def test_quarterly_links_keep_correct_period(self):
        raw = b'<a href="2ndqtr26.pdf">Report</a><a href="3rdqtr26.pdf">Other</a>'
        self.assertTrue(choose_child(raw,'https://www.berkshirehathaway.com/qtrly/links2ndqtr26.html',{'year':2026,'period':'Q2'}).endswith('/2ndqtr26.pdf'))

    def test_amended_quarterly_filename_is_observed_not_guessed(self):
        raw=b'<a href="web1101.html">Buffett letter</a><a href="3rdqtr01a.pdf">2001 Third Quarter Report PDF Version</a>'
        self.assertTrue(choose_child(raw,'https://www.berkshirehathaway.com/qtrly/links3rdqtr01.html',{'year':2001,'period':'Q3'}).endswith('/3rdqtr01a.pdf'))

    def test_shell_page_not_accepted_as_full_report(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory)
            def fake(url,folder,label):
                path=folder/(label+'.html');raw=b'<html><p>Choose a format</p></html>';path.write_bytes(raw)
                return raw,url,path
            with patch('collect_financials.save_download',side_effect=fake):
                with self.assertRaises(ValueError):
                    stage_one({'year':2024,'period':'annual','url':'https://www.berkshirehathaway.com/report.html'},stage,set())
            self.assertFalse((stage/'2024-annual'/'ready.json').exists())


if __name__=='__main__':
    unittest.main()
