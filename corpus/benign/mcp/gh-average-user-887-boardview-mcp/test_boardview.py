import tempfile
import unittest
from pathlib import Path

from boardview import Library, page, parse

FIXTURE = b'''$HEADER
GENCAD 1.4
UNITS MM
$ENDHEADER
$SHAPES
SHAPE resistor
PIN 1 pad -1 0 TOP 0 0
PIN 2 pad 1 0 TOP 0 0
$ENDSHAPES
$COMPONENTS
COMPONENT R1
PLACE 10 20
LAYER BOTTOM
ROTATION 90
SHAPE resistor MIRRORY FLIP
DEVICE "10k resistor"
COMPONENT R2
PLACE 13 24
LAYER TOP
ROTATION 0
SHAPE resistor 0 0
DEVICE "10k resistor"
$ENDCOMPONENTS
$DEVICES
DEVICE "10k resistor"
PART "10k ohm"
$ENDDEVICES
$SIGNALS
SIGNAL "+1.8V S5"
NODE R1 2
NODE R2 1
SIGNAL GND
NODE R1 1
$ENDSIGNALS
'''


class ParserTests(unittest.TestCase):
    def test_declared_connectivity_and_raw_geometry(self):
        b = parse(Path('fixture.cad'), FIXTURE)
        self.assertEqual(b.pins('R1')[1]['net'], '+1.8V S5')
        self.assertEqual(b.pins('R1')[1]['local_x'], 1)
        self.assertEqual(b.component('R1')['side'], 'BOTTOM')
        self.assertEqual(b.component('R1')['device_fields']['part'], '10k ohm')
        self.assertEqual(b.pins('R2')[1]['connectivity_status'], 'not_declared')
        self.assertIsNone(b.pins('R2')[1]['net'])
        self.assertEqual(len(b.nets['+1.8V S5']), 2)
        self.assertGreater(b.pins('R1')[1]['signal_line'], 1)

    def test_fail_closed(self):
        for bad in [b'binary', FIXTURE.replace(b'$ENDSIGNALS', b''),
                    FIXTURE.replace(b'NODE R2 1', b'NODE R3 1'),
                    FIXTURE.replace(b'NODE R2 1', b'NODE R2 9'),
                    FIXTURE.replace(b'NODE R2 1', b'NODE R1 2'),
                    FIXTURE.replace(b'PLACE 10 20', b'PLACE nan 20'),
                    FIXTURE.replace(b'SHAPE resistor MIRRORY FLIP', b'SHAPE missing 0 0'),
                    FIXTURE.replace(b'$ENDSIGNALS', b'$ENDSHAPES')]:
            with self.subTest(bad=bad[-60:]), self.assertRaises(ValueError):
                parse(Path('bad.cad'), bad)

    def test_paths_and_fresh_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'boards'
            root.mkdir()
            board = root / 'board.cad'
            board.write_bytes(FIXTURE)
            outside = Path(d) / 'outside.cad'
            outside.write_bytes(FIXTURE)
            (root / 'escape.cad').symlink_to(outside)
            lib = Library([root])
            a = lib.load('board.cad')
            board.write_bytes(FIXTURE.replace(b'+1.8V S5', b'+3.3V S5'))
            b = lib.load('board.cad')
            self.assertNotEqual(a.sha256, b.sha256)
            self.assertEqual(b.pins('R1')[1]['net'], '+3.3V S5')
            for path in ['../outside.cad', 'escape.cad', str(outside)]:
                with self.assertRaises(ValueError):
                    lib.load(path)
            self.assertEqual(lib.catalog()['total'], 1)

    def test_pagination(self):
        self.assertEqual(page([1, 2, 3], 0, 2)['next_offset'], 2)
        self.assertIsNone(page([1, 2, 3], 2, 2)['next_offset'])
        for offset, limit in [(-1, 1), (0, 0), (0, 101)]:
            with self.assertRaises(ValueError):
                page([], offset, limit)


if __name__ == '__main__':
    unittest.main()
