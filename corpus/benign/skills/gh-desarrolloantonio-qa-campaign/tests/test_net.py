"""net.sh's contract: a network state is only reported when it was proved, and from the app's side."""
import unittest

from harness import Case


class Reach(Case):
    def test_an_open_port_that_answers_no_http_is_not_a_server(self):
        # Measured on API 37: a dangling `adb reverse` takes the connection and exits 0.
        r = self.run_net("reach", STUB_NC_EXIT=0, STUB_HTTP="")
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "answers no HTTP")

    def test_the_http_status_is_reported_whatever_it_is(self):
        r = self.run_net("reach", STUB_NC_EXIT=0, STUB_HTTP="HTTP/1.0 401 Unauthorized")
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertSaid(r, "HTTP 401 from the server")

    def test_a_refused_connection_says_the_computer_proves_nothing(self):
        r = self.run_net("reach", STUB_NC_EXIT=1)
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "cannot connect")
        self.assertSaid(r, "The computer reaching it proves nothing")

    def test_without_nc_it_says_it_could_not_check(self):
        r = self.run_net("reach", STUB_NC="no")
        self.assertEqual(2, r.returncode, "2 is 'could not check', not 'unreachable'")
        self.assertSaid(r, "not the same as unreachable")


class BlamingTheApp(Case):
    """R8: "I could not check" must never be reported as "the app cannot reach it"."""

    def test_a_runas_context_that_resolves_nothing_is_not_proven(self):
        # Measured on an API 37 emulator: `run-as` resolved no name at all — a control name failed
        # exactly like the test server — while the app was talking to the server the whole time.
        r = self.run_net("reach", STUB_NC_APP=1, STUB_NC_APP_ERR="nc: bad address 'qa.example.com': "
                                                                 "No address associated with hostname",
                         STUB_NC_CONTROL=1, STUB_NC_EXIT=0, STUB_HTTP="HTTP/1.1 200 OK")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertSaid(r, "NOT PROVEN as the app")
        self.assertSaid(r, "the device's shell user")

    def test_an_app_that_really_is_blocked_is_still_reported(self):
        r = self.run_net("reach", STUB_NC_APP=1, STUB_NC_APP_ERR="nc: bad address 'qa.example.com': "
                                                                 "No address associated with hostname",
                         STUB_NC_CONTROL=0, STUB_NC_EXIT=0)
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "block that address")


class Offline(Case):
    def test_offline_is_proved_from_the_apps_side_too(self):
        r = self.run_net("off", STUB_AIRPLANE=1, STUB_VALIDATED="no", STUB_NC_EXIT=1)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertSaid(r, "offline (airplane_mode_on=1)")
        self.assertSaid(r, "cannot reach 10.0.2.2:18099")

    def test_a_server_the_app_still_reaches_is_not_offline(self):
        self.write_config(server={"url": "http://192.168.1.50:8085"})
        r = self.run_net("off", STUB_AIRPLANE=1, STUB_VALIDATED="no", STUB_NC_EXIT=0)
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "NOT offline for the app")

    def test_a_fake_server_on_this_computer_is_named_not_refused(self):
        self.write_config(server={"url": "http://127.0.0.1:18099"})
        r = self.run_net("off", STUB_AIRPLANE=1, STUB_VALIDATED="no", STUB_NC_EXIT=0)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertSaid(r, "relay or the fake server on this computer")

    def test_adb_losing_the_device_is_not_offline(self):
        r = self.run_net("off", STUB_VALIDATED="no", STUB_SETTINGS_LOST=1)
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "adb lost the device")

    def test_something_else_taking_the_network_down_is_not_offline(self):
        r = self.run_net("off", STUB_AIRPLANE=0, STUB_VALIDATED="no")
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "something else took the network down")


class Guards(Case):
    def test_a_device_that_is_not_on_the_allow_list_is_refused(self):
        r = self.run_net("status", STUB_SERIAL="RFCRB0XRA7R")
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "refusing RFCRB0XRA7R")

    def test_a_throttle_the_emulator_refused_is_not_a_throttle(self):
        r = self.run_net("slow", "edge", STUB_EMU="KO: unknown network speed")
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "the emulator refused")

    def test_an_adb_that_is_not_a_file_is_refused_not_replaced(self):
        # ui.py refuses a mistyped $ADB; net.sh fell through to whatever adb was on PATH — a different
        # adb than the one the project named, and nothing said so.
        import os
        r = self.run_net("status", ADB=os.path.join(self.dir, "no-such-adb"),
                         PATH=self.dir + os.pathsep + os.environ["PATH"])
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "not a file")
        self.assertEqual([], self.adb_calls(), "the adb on PATH must not be asked instead")

    def test_an_alias_that_is_not_in_devices_is_refused(self):
        r = self.run_net("status", "--device", "tablet")
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "unknown device alias")
        self.assertEqual([], [c for c in self.adb_calls() if c.startswith("shell")])

    def test_no_device_at_all_exits_one(self):
        r = self.run_net("status", STUB_STATE="none")
        self.assertEqual(1, r.returncode)
        self.assertSaid(r, "no device reachable")


if __name__ == "__main__":
    unittest.main()
