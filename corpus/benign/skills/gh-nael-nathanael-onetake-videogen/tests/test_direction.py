import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from direction import HOOKS, STRUCTURES, pick


class DirectionTest(unittest.TestCase):
    def test_same_seed_gives_the_same_direction(self):
        self.assertEqual(pick(7, "explainer", []), pick(7, "explainer", []))

    def test_each_mode_picks_from_its_own_structures(self):
        for mode, structures in STRUCTURES.items():
            self.assertIn(pick(1, mode, [])["structure"], structures)

    def test_recent_picks_are_not_repeated(self):
        for mode in STRUCTURES:
            used = []
            for seed in range(5):
                d = pick(seed, mode, used)
                self.assertNotIn(d["structure"], [u["structure"] for u in used])
                self.assertNotIn(d["hook"], [u["hook"] for u in used])
                used.append(d)

    def test_when_everything_is_used_it_still_picks(self):
        avoid = [{"structure": s, "hook": h} for s in STRUCTURES["illustrated"] for h in HOOKS]
        self.assertIn(pick(3, "illustrated", avoid)["hook"], HOOKS)


if __name__ == "__main__":
    unittest.main()
