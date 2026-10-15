"""ui.py's contract: what it refuses, and what it never sends to a device."""
import os
import sqlite3
import subprocess
import sys
import unittest

from harness import Case, PKG, UI

HEAD = "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n<hierarchy rotation=\"0\">"
TAIL = "</hierarchy>"


def node(cls, bounds, text="", desc="", clickable="false", children=""):
    x1, y1, x2, y2 = bounds
    return (f'<node index="0" text="{text}" resource-id="" class="{cls}" package="{PKG}" '
            f'content-desc="{desc}" checkable="false" checked="false" clickable="{clickable}" '
            f'enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" '
            f'password="false" selected="false" bounds="[{x1},{y1}][{x2},{y2}]">{children}</node>')


def row(title, y, label="Delete"):
    """A list item with its own title and its own Delete — the shape that makes a selector ambiguous."""
    inner = (node("android.widget.TextView", (20, y + 20, 500, y + 180), text=title)
             + node("android.widget.TextView", (900, y + 20, 1060, y + 180), text=label))
    return node("android.view.View", (0, y, 1080, y + 200), clickable="true", children=inner)


TWO_ROWS = HEAD + node("android.widget.FrameLayout", (0, 0, 1080, 2400),
                       children=row("QA_Item1", 200) + row("QA_Item2", 500)) + TAIL

# One control, its label repeated inside it: a chip and a title that say the same word.
ONE_CONTROL_TWICE = HEAD + node(
    "android.widget.FrameLayout", (0, 0, 1080, 2400),
    children=node("android.view.View", (0, 200, 1080, 400), clickable="true",
                  children=node("android.widget.TextView", (20, 220, 500, 380), text="Partial")
                  + node("android.widget.TextView", (600, 220, 800, 380), text="Partial"))) + TAIL


class Selectors(Case):
    def test_a_selector_that_is_two_different_controls_is_refused(self):
        r = self.run_ui("tap", "text=Delete", STUB_DUMP=self.with_dump(TWO_ROWS))
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "refusing")
        self.assertSaid(r, "2 different controls")
        self.assertNoInput()

    def test_index_names_one_of_them(self):
        r = self.run_ui("tap", "text=Delete", "--index", "1", STUB_DUMP=self.with_dump(TWO_ROWS))
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("shell input tap 540 600", self.adb_calls())   # the second row, not the first

    def test_any_takes_the_first_and_says_it_did(self):
        r = self.run_ui("tap", "text=Delete", "--any", STUB_DUMP=self.with_dump(TWO_ROWS))
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertSaid(r, "--any took the first")
        self.assertIn("shell input tap 540 300", self.adb_calls())

    def test_the_same_control_matched_twice_is_not_ambiguous(self):
        r = self.run_ui("tap", "text=Partial", STUB_DUMP=self.with_dump(ONE_CONTROL_TWICE))
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertSaid(r, "first of 2 matches")
        self.assertEqual(1, len([c for c in self.adb_calls() if "input tap" in c]))

    def test_in_takes_the_control_of_the_item_it_names(self):
        r = self.run_ui("tap", "text=Delete", "--in", "text=QA_Item2", STUB_DUMP=self.with_dump(TWO_ROWS))
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertEqual(["shell input tap 540 600"], [c for c in self.adb_calls() if "input tap" in c],
                         "the Delete of QA_Item2, and no other")

    def test_assert_exits_one_when_it_is_wrong_in_either_direction(self):
        dump = self.with_dump(TWO_ROWS)
        present = self.run_ui("assert", "text=QA_Item1", "--absent", STUB_DUMP=dump)
        self.assertEqual(1, present.returncode)
        self.assertSaid(present, "ASSERT FAILED")
        missing = self.run_ui("assert", "text=Publish", STUB_DUMP=dump)
        self.assertEqual(1, missing.returncode)
        self.assertEqual(0, self.run_ui("assert", "text=Publish", "--absent", STUB_DUMP=dump).returncode)

    def test_find_with_no_match_is_not_exit_zero(self):
        r = self.run_ui("find", "text=Publish", STUB_DUMP=self.with_dump(TWO_ROWS))
        self.assertNotEqual(0, r.returncode, "a wait loop gating on `find` must stop on nothing found")
        self.assertSaid(r, "no match")

    def test_a_selector_that_matches_nothing_fails_and_says_what_is_there(self):
        r = self.run_ui("tap", "text=Publish", STUB_DUMP=self.with_dump(TWO_ROWS))
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "NOT found")
        self.assertSaid(r, "QA_Item1")
        self.assertNoInput()


class Guards(Case):
    def test_a_device_that_is_not_on_the_allow_list_is_refused(self):
        r = self.run_ui("dump", STUB_SERIAL="RFCRB0XRA7R")
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "refusing RFCRB0XRA7R")
        self.assertEqual([], [c for c in self.adb_calls() if c.startswith("shell")],
                         "nothing may be asked of a device the campaign was not given")

    def test_without_a_configuration_nothing_is_touched(self):
        os.remove(self.config_path)          # and nothing above the temp folder has one either
        env = self.env()
        del env["QA_CONFIG"]
        r = subprocess.run(["python3", UI, "dump"], capture_output=True, text=True, cwd=self.dir, env=env)
        self.assertNotEqual(0, r.returncode)
        self.assertIn("qa.config.json", r.stdout + r.stderr)
        self.assertEqual([], self.adb_calls(), "the refusal must come before the first adb call")

    def test_input_is_refused_when_another_app_is_in_front(self):
        r = self.run_ui("tap", "text=Delete", "--index", "0",
                        STUB_DUMP=self.with_dump(TWO_ROWS), STUB_FRONT="com.android.chrome")
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "com.android.chrome is in front")
        self.assertNoInput()

    def test_a_managed_device_is_not_rotated(self):
        self.write_config(managedDevices=["phone"])
        r = self.run_ui("rotate", "1")
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "managedDevices")
        self.assertEqual([], [c for c in self.adb_calls() if "user-rotation" in c],
                         "a device that is not the campaign's to alter must not be asked to rotate")

    def test_a_device_another_campaign_is_driving_is_refused_until_released(self):
        self.write_config(campaign="campaign A")
        self.assertEqual(0, self.run_ui("claim").returncode)
        self.write_config(campaign="campaign B")
        r = self.run_ui("tap", "text=Delete", "--index", "0", STUB_DUMP=self.with_dump(TWO_ROWS))
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "in use by another campaign: campaign A")
        self.assertNoInput()
        self.assertSaid(self.run_ui("release"), "left alone")         # B cannot free A's claim…
        self.write_config(campaign="campaign A")
        self.assertSaid(self.run_ui("release"), "released")           # …A can
        self.write_config(campaign="campaign B")
        self.assertEqual(0, self.run_ui("claim").returncode)

    def test_text_the_device_would_drop_is_refused_not_typed(self):
        r = self.run_ui("type", "Grüße")
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "non-ASCII")
        self.assertNoInput("`input text` drops it, and \"typed\" would be a lie")

    def test_a_dump_that_never_answers_is_not_an_empty_screen(self):
        r = self.run_ui("dump")                     # no STUB_DUMP: uiautomator keeps failing
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "did not answer")


class Measurements(Case):
    """The harness never replaces a measurement it could not take with a plausible number."""

    def test_an_unreadable_density_is_unproven_not_420(self):
        r = self.run_ui("a11y", STUB_DUMP=self.with_dump(TWO_ROWS), STUB_DENSITY="")
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "UNPROVEN")
        self.assertNotIn("420", r.stdout)

    def test_an_unreadable_screen_size_is_unproven_not_1080x2400(self):
        flat = HEAD + node("android.widget.FrameLayout", (0, 0, 0, 0),
                           children=row("QA_Item1", 200)) + TAIL
        r = self.run_ui("tap", "text=Delete", STUB_DUMP=self.with_dump(flat),
                        STUB_DISPLAYS="", STUB_WM_SIZE="")
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "UNPROVEN")
        self.assertNoInput("a tap needs coordinates, and there were none to read")


class WhichApp(Case):
    """R8: what the tree says is only evidence if it belongs to the app under test."""

    def test_a_prefix_that_matches_two_installed_apps_is_refused(self):
        self.write_config(android={"package": PKG, "packagePrefix": "com.example"})
        r = self.run_ui("dump", STUB_DUMP=self.with_dump(TWO_ROWS),
                        STUB_PACKAGES="com.example.app,com.example.other")
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "matches 2 installed packages")
        self.assertSaid(r, "packagePrefix")

    def test_an_explicit_list_of_packages_is_taken_as_given(self):
        self.write_config(android={"package": PKG, "packagePrefix": [PKG, PKG + ".debug"]})
        r = self.run_ui("tap", "text=Delete", "--index", "0", STUB_DUMP=self.with_dump(TWO_ROWS),
                        STUB_PACKAGES="com.example.app,com.example.other")
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertEqual([], [c for c in self.adb_calls() if "pm list packages" in c],
                         "a list needs no guessing, so the device is not asked")


    def test_input_reaches_any_package_on_the_list(self):
        # The list exists to "count several variants as one app": the debug variant in front is the app.
        self.write_config(android={"package": PKG, "packagePrefix": [PKG, PKG + ".debug"]})
        r = self.run_ui("tap", "text=Delete", "--index", "0", STUB_DUMP=self.with_dump(TWO_ROWS),
                        STUB_FRONT=PKG + ".debug")
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("shell input tap 540 300", self.adb_calls())

    def test_a_crash_of_a_listed_variant_is_the_apps_crash(self):
        # R8: "0 crashes" over a crash of the variant the config counts as the app is a silent all-clear.
        self.write_config(android={"package": PKG, "packagePrefix": [PKG, PKG + ".debug"]})
        crash = ("09-24 10:00:00.000  1234  1234 E AndroidRuntime: FATAL EXCEPTION: main\n"
                 f"09-24 10:00:00.000  1234  1234 E AndroidRuntime: Process: {PKG}.debug, PID: 1234\n"
                 "09-24 10:00:00.000  1234  1234 E AndroidRuntime: java.lang.IllegalStateException: boom")
        r = self.run_ui("crashes", STUB_CRASHES=crash)
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertSaid(r, "IllegalStateException")

    def test_a_crash_of_another_app_is_still_not_the_apps(self):
        # The other direction (R8): the list must not turn every crash on the device into the app's.
        self.write_config(android={"package": PKG, "packagePrefix": [PKG, PKG + ".debug"]})
        crash = ("09-24 10:00:00.000  1234  1234 E AndroidRuntime: FATAL EXCEPTION: main\n"
                 "09-24 10:00:00.000  1234  1234 E AndroidRuntime: Process: com.example.other, PID: 1234")
        r = self.run_ui("crashes", STUB_CRASHES=crash)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertSaid(r, "0 crashes")


class Secrets(Case):
    """R11: the STORE and LOG oracles never print a credential."""

    def test_secret_looking_values_are_hidden_and_the_rest_is_not(self):
        text = 'password=hunter2\n"pins": {"a": "1234"}\nuser=ana\ntoken=abc.def.ghi\n'
        code = ("import sys; sys.path.insert(0, %r); import ui; "
                "sys.stdout.write(ui.hide_secrets_in_text(sys.stdin.read()))"
                % os.path.dirname(UI))
        r = subprocess.run([sys.executable, "-c", code], input=text, capture_output=True, text=True,
                           env=self.env())
        self.assertEqual(0, r.returncode, r.stderr)
        for secret in ("hunter2", "1234", "abc.def.ghi"):
            self.assertNotIn(secret, r.stdout)
        self.assertIn("ana", r.stdout)


class Store(Case):
    """R11, through the commands a campaign actually runs: `db` and `file` against the app's data folder."""

    def setUp(self):
        super().setUp()
        self.data = os.path.join(self.dir, "appdata")
        os.makedirs(os.path.join(self.data, "databases"))
        os.makedirs(os.path.join(self.data, "files"))
        con = sqlite3.connect(os.path.join(self.data, "databases", "app.db"))
        con.execute("create table session (id integer, username text, auth_token text)")
        con.execute("insert into session values (1, 'ana', 'QAtok-123')")
        con.execute("create table settings (key text, value text)")
        con.executemany("insert into settings values (?, ?)", [("password", "hunter2"), ("theme", "dark")])
        con.commit()
        con.close()
        with open(os.path.join(self.data, "files", "session.pb"), "wb") as fh:
            fh.write(b"\x0a\x08QAsecret")                       # a Proto DataStore: valid UTF-8, binary
        self.write_config(android={"package": PKG, "databases": {"main": "app.db"},
                                   "files": {"session": "files/session.pb"}})

    def test_db_hides_a_secret_column_and_prints_the_rest(self):
        r = self.run_ui("db", "main", "select username, auth_token from session", STUB_DATA=self.data)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("ana | <hidden>", r.stdout)
        self.assertNotIn("QAtok-123", r.stdout + r.stderr)

    def test_db_hides_the_value_of_a_row_whose_key_is_secret(self):
        r = self.run_ui("db", "main", "select key, value from settings", STUB_DATA=self.data)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertNotIn("hunter2", r.stdout + r.stderr)
        self.assertIn("theme | dark", r.stdout)

    def test_a_binary_store_is_never_printed(self):
        r = self.run_ui("file", "session", STUB_DATA=self.data)
        self.assertNotEqual(0, r.returncode)
        self.assertSaid(r, "is binary")
        self.assertNotIn("QAsecret", r.stdout + r.stderr)


def raw(cls, bounds, text="", children="", **attrs):
    """A node with any attribute set — focused fields, checkboxes, password fields."""
    x1, y1, x2, y2 = bounds
    base = {"index": "0", "text": text, "resource-id": "", "class": cls, "package": PKG, "content-desc": "",
            "checkable": "false", "checked": "false", "clickable": "false", "enabled": "true",
            "focusable": "true", "focused": "false", "scrollable": "false", "long-clickable": "false",
            "password": "false", "selected": "false"}
    base.update({k.replace("_", "-"): v for k, v in attrs.items()})
    body = " ".join(f'{k}="{v}"' for k, v in base.items())
    return f'<node {body} bounds="[{x1},{y1}][{x2},{y2}]">{children}</node>'


def screen(*children):
    return HEAD + node("android.widget.FrameLayout", (0, 0, 1080, 2400), children="".join(children)) + TAIL


# A login form whose whole surface is one clickable (it clears focus), and a label that is not.
REMEMBER_ME = screen(raw("android.view.View", (0, 0, 1080, 2400), clickable="true", children=(
    raw("android.widget.CheckBox", (40, 1000, 120, 1080), checkable="true", clickable="true")
    + raw("android.widget.TextView", (140, 1010, 420, 1070), text="Remember me"))))


def one_field(text, focused="true", password="false"):
    return screen(raw("android.widget.EditText", (40, 400, 1040, 520), text=text, clickable="true",
                      focused=focused, password=password),
                  raw("android.widget.EditText", (40, 600, 1040, 720), text="Notes", clickable="true"))


class TapTarget(Case):
    def test_a_label_inside_a_full_screen_clickable_is_refused_not_tapped_at_the_centre(self):
        # Measured: `tap "text=Remember me"` pressed (540,1200), said "tap:", toggled nothing.
        r = self.run_ui("tap", "text=Remember me", STUB_DUMP=self.with_dump(REMEMBER_ME))
        self.assertNotEqual(0, r.returncode, r.stdout)
        self.assertSaid(r, "refusing")
        self.assertNoInput()

    def test_a_label_inside_its_own_row_is_still_tapped(self):
        r = self.run_ui("tap", "text=QA_Item1", STUB_DUMP=self.with_dump(TWO_ROWS))
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("shell input tap 540 300", self.adb_calls())


class Typing(Case):
    def test_text_that_did_not_land_as_sent_fails(self):
        # Measured: the first character was dropped, and `type` printed "typed: 'A_R8_Place'".
        r = self.run_ui("type", "A_R8_Place", STUB_DUMP=self.with_dump(one_field("_R8_Place")))
        self.assertNotEqual(0, r.returncode, r.stdout)
        self.assertSaid(r, "the field reads '_R8_Place'")

    def test_text_that_landed_passes(self):
        r = self.run_ui("type", "A_R8_Place", STUB_DUMP=self.with_dump(one_field("A_R8_Place")))
        self.assertEqual(0, r.returncode, r.stderr)

    def test_a_password_field_is_not_read_back(self):
        r = self.run_ui("type", "QAsecret", STUB_DUMP=self.with_dump(one_field("••••••••", password="true")))
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertNotIn("QAsecret", r.stdout + r.stderr)

    def test_into_a_field_that_is_not_there_types_nothing(self):
        # Measured: a refused tap, then `type` wrote into whichever field still had focus.
        r = self.run_ui("type", "A_R8_Place", "--into", "text=Title", STUB_DUMP=self.with_dump(one_field("")))
        self.assertNotEqual(0, r.returncode)
        self.assertNoInput()

    def test_into_taps_the_field_then_types(self):
        r = self.run_ui("type", "A_R8_Place", "--into", "text=A_R8_Place",
                        STUB_DUMP=self.with_dump(one_field("A_R8_Place")))
        self.assertEqual(0, r.returncode, r.stderr)
        calls = [c for c in self.adb_calls() if "input" in c]
        self.assertEqual("shell input tap 540 460", calls[0])
        self.assertTrue(calls[1].startswith("shell input text"), calls)


# A checklist row: two checkboxes with no label of their own, and one text beside them.
CHECKLIST = screen(raw("android.view.View", (0, 300, 1080, 420), children=(
    raw("android.widget.CheckBox", (20, 320, 100, 400), checkable="true", clickable="true")
    + raw("android.widget.TextView", (120, 320, 600, 400), text="item one")
    + raw("android.widget.CheckBox", (980, 320, 1060, 400), checkable="true", clickable="true"))))


class DumpLabels(Case):
    def test_a_neighbours_label_is_marked_as_a_neighbours(self):
        # Measured: both unlabeled checkboxes printed `off ("item one")`, as if the app named them so.
        r = self.run_ui("dump", STUB_DUMP=self.with_dump(CHECKLIST))
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertNotIn('off ("item one")', r.stdout)
        self.assertEqual(2, r.stdout.count('off (no label; beside "item one")'), r.stdout)


class Screenshots(Case):
    def test_a_name_already_taken_is_refused(self):
        # Measured: a reused name, and the gate's old screenshot was read as the new build's.
        shots = os.path.join(self.dir, "shots")
        os.makedirs(shots)
        old = os.path.join(shots, "home.png")
        with open(old, "wb") as fh:
            fh.write(b"old")
        r = self.run_ui("shot", "home", "--dir", shots)
        self.assertNotEqual(0, r.returncode, r.stdout)
        self.assertSaid(r, "already exists")
        with open(old, "rb") as fh:
            self.assertEqual(b"old", fh.read())


if __name__ == "__main__":
    unittest.main()
