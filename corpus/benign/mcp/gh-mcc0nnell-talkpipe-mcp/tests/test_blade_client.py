"""Protocol tests use a fake local Blade socket, not fabricated signing claims."""
import os
import pathlib
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from blade_local_client import BladeBlocked, health, status, talkpipe_run, host_inspect, process_list, git_inspect, file_create, process_probe
import windanvil_commander_mcp


class BladeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.socket_path = pathlib.Path(self.tmp.name) / "blade.sock"
        self.env = patch.dict(os.environ, {"WINDANVIL_LOCAL_SOCKET": str(self.socket_path)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def once(self, reply):
        listening = socket.socket(socket.AF_UNIX)
        listening.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o600)
        listening.listen(1)
        messages = []

        def serve():
            try:
                conn, _ = listening.accept()
                with conn:
                    chunks = []
                    while chunk := conn.recv(4096):
                        chunks.append(chunk)
                    messages.append(b"".join(chunks).decode())
                    conn.sendall(reply)
            finally:
                listening.close()

        task = threading.Thread(target=serve, daemon=True)
        task.start()
        return task, messages

    def test_absent_socket_blocks(self):
        with self.assertRaisesRegex(BladeBlocked, "socket_unavailable"):
            health()
        self.assertEqual(windanvil_commander_mcp.commander_health()["outcome"], "BLOCKED")

    def test_status_exchange(self):
        task, messages = self.once(b"OK\tgrant=active\n")
        self.assertEqual(status(), "grant=active\n")
        task.join(timeout=2)
        self.assertEqual(messages, ["STATUS\n"])

    def test_execute_only_fixed_capability(self):
        task, messages = self.once(b"OK\texecuted\n")
        digest = "a" * 64
        self.assertEqual(talkpipe_run("normalize", digest), "executed\n")
        task.join(timeout=2)
        self.assertEqual(messages, ["EXEC\ttalkpipe.run\tschema=windanvil.blade.talkpipe-exec/v1;pipeline=normalize;pipeline_sha256=" + digest + "\n"])

    def test_reject_invalid_pipeline_and_hash_without_socket(self):
        for name in ("../etc", "some;command", "white space", ""):
            with self.assertRaisesRegex(BladeBlocked, "pipeline_name_invalid"):
                talkpipe_run(name, "a"*64)
        with self.assertRaisesRegex(BladeBlocked, "pipeline_digest_invalid"):
            talkpipe_run("normalize", "b"*63)

    def test_host_inspection_envelope(self):
        task, messages = self.once(b"OK\nscoped data")
        self.assertEqual(host_inspect("file.read", "README.md"), "scoped data")
        task.join(timeout=2)
        self.assertEqual(messages, ["EXEC\thost.inspect\tschema=windanvil.blade.host-inspect/v1;operation=file.read;path=README.md\n"])

    def test_host_inspection_invalid_paths_are_denied(self):
        for candidate in ("../etc", ".secret", "some//file", "a;bad", "/etc", "dir/.git/config"):
            with self.assertRaisesRegex(BladeBlocked, "path_denied"):
                host_inspect("file.read", candidate)
        with self.assertRaisesRegex(BladeBlocked, "operation_denied"):
            host_inspect("shell.run", "file")

    def test_search_envelope_and_needle_restrictions(self):
        task, messages = self.once(b"OK\ninside.txt:4\n")
        result = host_inspect("content.search", "sub", "token")
        self.assertEqual(result, "inside.txt:4\n")
        task.join(timeout=2)
        self.assertEqual(messages, ["EXEC\thost.inspect\tschema=windanvil.blade.host-inspect/v1;operation=content.search;path=sub;needle=token\n"])
        for candidate in ("", "hello world", "a;path=/etc", "a\nEXEC"):
            with self.assertRaisesRegex(BladeBlocked, "needle_denied"):
                host_inspect("content.search", "", candidate)
        with self.assertRaisesRegex(BladeBlocked, "needle_denied"):
            host_inspect("file.read", "inside.txt", "unexpected")

    def test_process_list_exact_capability(self):
        task, messages = self.once(b"OK\n1234 python\n")
        self.assertEqual(process_list(), "1234 python\n")
        task.join(timeout=2)
        self.assertEqual(messages, [
            "EXEC\tprocess.inspect\t"
            "schema=windanvil.blade.process-inspect/v1;operation=process.list\n"
        ])

    def test_git_inspection_exact_allowlist(self):
        task, messages = self.once(b"OK\nbranch=main\n")
        self.assertEqual(git_inspect("git.status"), "branch=main\n")
        task.join(timeout=2)
        self.assertEqual(messages, [
            "EXEC\tgit.inspect\t"
            "schema=windanvil.blade.git-inspect/v1;operation=git.status\n"
        ])
        for op in ("git.push", "git.diff", "git.status;command=run", ""):
            with self.assertRaisesRegex(BladeBlocked, "git_inspection_operation_denied"):
                git_inspect(op)

    def test_file_create_strict_envelope(self):
        task, messages = self.once(b"OK\ncreated=notes.txt\nbytes=2\n")
        self.assertIn("created=notes.txt", file_create("notes.txt", "hi"))
        task.join(timeout=2)
        self.assertEqual(messages, [
            "EXEC\tfile.create\t"
            "schema=windanvil.blade.file-create/v1;path=notes.txt;hex=6869\n"
        ])
        for path in ("../hi", ".hidden", "a//file", "/absolute", "a;bad", "a/../other"):
            with self.assertRaisesRegex(BladeBlocked, "file_create_path_denied"):
                file_create(path, "test")
        with self.assertRaisesRegex(BladeBlocked, "file_create_payload_too_large"):
            file_create("notes.txt", "x"*2049)

    def test_process_probe_fixed_allowlist(self):
        task, messages = self.once(b"OK\nLinux x86_64\n")
        self.assertIn("Linux", process_probe("kernel"))
        task.join(timeout=2)
        self.assertEqual(messages, [
            "EXEC\tprocess.probe\t"
            "schema=windanvil.blade.process-probe/v1;probe=kernel\n"
        ])
        for probe in ("sh", "python", "kernel;cmd=sh", "/bin/sh", ""):
            with self.assertRaisesRegex(BladeBlocked, "process_probe_not_allowlisted"):
                process_probe(probe)

    def test_reject_blade_denial(self):
        task, _ = self.once(b"ERR\tbad grant\n")
        with self.assertRaisesRegex(BladeBlocked, "blade_rejected_operation"):
            health()
        task.join(timeout=2)

    def test_reject_bad_socket_permissions(self):
        task, _ = self.once(b"OK\n")
        os.chmod(self.socket_path, 0o666)
        with self.assertRaisesRegex(BladeBlocked, "identity_or_permissions"):
            status()
        # Close listener without waiting for a nonexistent client.
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(self.socket_path))
            client.shutdown(socket.SHUT_WR)
            client.recv(4096)
        task.join(timeout=2)

    def test_reject_invalid_wire_response(self):
        task, _ = self.once(b"garbage")
        with self.assertRaisesRegex(BladeBlocked, "protocol_invalid"):
            health()
        task.join(timeout=2)

    def test_no_direct_talkpipe_fallback(self):
        result = windanvil_commander_mcp.commander_talkpipe_run("normalize", "a"*64)
        self.assertEqual(result["outcome"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
