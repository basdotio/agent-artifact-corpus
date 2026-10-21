"""The Chinese README.md and README_en.md are maintained by hand in parallel.

Readers check alignment by the version in SKILL.md, the README titles and the Release tag,
and they copy install commands from whichever README they read. A release that bumps one
README but not the other, or a command fixed in one language only, must fail here.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
READMES = {"README.md": "中文", "README_en.md": "English"}


def text(name):
    return (ROOT / name).read_text(encoding="utf-8")


def commands(markdown):
    """Shell code blocks with comment lines dropped: comments are translated, commands are not."""
    blocks = re.findall(r"```sh\n(.*?)```", markdown, re.S)
    return [[line for line in block.splitlines() if line.strip() and not line.lstrip().startswith("#")]
            for block in blocks]


class ReadmeSyncTests(unittest.TestCase):
    def test_every_readme_title_carries_the_skill_version(self):
        version = re.search(r'^\s+version:\s*"([^"]+)"', text("SKILL.md"), re.M)[1]
        for name in READMES:
            with self.subTest(readme=name):
                self.assertRegex(text(name), r"(?m)^# Buffett & Munger Evidence Skill v" + re.escape(version) + r"$")

    def test_each_readme_marks_its_language_and_links_the_others(self):
        for name, label in READMES.items():
            with self.subTest(readme=name):
                bar = text(name).split("\n", 1)[0]
                self.assertIn(f"<b>{label}</b>", bar)
                for other, other_label in READMES.items():
                    if other != name:
                        self.assertIn(f'<a href="{other}">{other_label}</a>', bar)

    def test_install_and_test_commands_are_identical_in_every_language(self):
        reference = commands(text("README.md"))
        self.assertTrue(reference)
        for name in READMES:
            with self.subTest(readme=name):
                self.assertEqual(commands(text(name)), reference)


if __name__ == "__main__":
    unittest.main()
