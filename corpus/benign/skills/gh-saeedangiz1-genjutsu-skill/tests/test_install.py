"""Installer and command contracts use temporary fixtures; no provider/package calls."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location('genjutsu_' + name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load_script('install')
runtime = load_script('runtime')


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='genjutsu test with spaces ')
        self.base = Path(self.temporary.name)
        self.source = self.base / 'source skill'
        self.source.mkdir()
        for name in installer.REQUIRED:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('pass\n', encoding='utf-8')
        (self.source / 'SKILL.md').write_text('---\nname: genjutsu-video-workflow\ndescription: Test fixture.\n---\n', encoding='utf-8')
        self.target = self.base / 'installed skill with spaces'

    def tearDown(self):
        self.temporary.cleanup()

    def test_install_path_spaces_and_idempotent(self):
        destination, count = installer.install(self.source, self.target)
        self.assertEqual(destination, self.target)
        self.assertEqual(count, len(installer.REQUIRED))
        self.assertEqual(installer.install(self.source, self.target)[1], 0)
        self.assertTrue((self.target / installer.MANIFEST).is_file())

    def test_private_runtime_data_never_copied(self):
        private_names = ('assets/workflow/.env', 'assets/workflow/.env.production', 'assets/workflow/runs/a/file.json',
                         'assets/workflow/.venv/Scripts/python.exe', 'outputs/test.mp4', 'private/notes.md',
                         '.git/config', '__pycache__/private.pyc', 'assets/workflow/.runtime-webhook.json', 'secret-key.txt')
        for name in private_names:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('PRIVATE_TEST_DATA', encoding='utf-8')
        example = self.source / 'assets/workflow/.env.example'
        example.write_text('API_KEY=replace_me\n', encoding='utf-8')
        installer.install(self.source, self.target)
        for name in private_names:
            self.assertFalse((self.target / name).exists(), name)
        self.assertEqual((self.target / 'assets/workflow/.env.example').read_text(), 'API_KEY=replace_me\n')

    def test_changed_target_requires_replace_and_preserves_local_data(self):
        installer.install(self.source, self.target)
        local = self.target / 'assets/workflow/.env'
        local.write_text('DO_NOT_OVERWRITE', encoding='utf-8')
        unrelated = self.target / 'my-notes.txt'
        unrelated.write_text('KEEP_ME', encoding='utf-8')
        (self.source / 'scripts/runtime.py').write_text('print("updated")\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '--replace'):
            installer.install(self.source, self.target)
        installer.install(self.source, self.target, replace=True)
        self.assertEqual(local.read_text(), 'DO_NOT_OVERWRITE')
        self.assertEqual(unrelated.read_text(), 'KEEP_ME')
        self.assertEqual((self.target / 'scripts/runtime.py').read_text(), 'print("updated")\n')

    def test_unmanaged_existing_target_never_overwritten(self):
        self.target.mkdir()
        (self.target / 'important.txt').write_text('KEEP', encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.install(self.source, self.target, replace=True)
        self.assertEqual((self.target / 'important.txt').read_text(), 'KEEP')

    def test_unmanaged_collision_rejected_even_with_replace(self):
        installer.install(self.source, self.target)
        (self.target / 'new-resource.txt').write_text('LOCAL', encoding='utf-8')
        (self.source / 'new-resource.txt').write_text('PUBLISHED', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unmanaged'):
            installer.install(self.source, self.target, replace=True)
        self.assertEqual((self.target / 'new-resource.txt').read_text(), 'LOCAL')

    def test_nesting_and_root_targets_rejected(self):
        for target in (self.source, self.source / 'inside', self.base, Path(self.base.anchor), Path.home()):
            with self.assertRaises(ValueError, msg=str(target)):
                installer.install(self.source, target)

    def test_missing_or_wrong_skill_rejected(self):
        (self.source / 'scripts/runtime.py').unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            installer.install(self.source, self.target)
        (self.source / 'SKILL.md').write_text('---\nname: other-skill\ndescription: fixture\n---\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Expected skill'):
            installer.install(self.source, self.target)

    def test_manifest_traversal_rejected(self):
        installer.install(self.source, self.target)
        data = json.loads((self.target / installer.MANIFEST).read_text())
        data['files']['../outside.txt'] = 'a' * 64
        (self.target / installer.MANIFEST).write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unsafe path'):
            installer.install(self.source, self.target, replace=True)

    def test_published_symlink_rejected(self):
        link = self.source / 'linked.txt'
        try:
            link.symlink_to(self.source / 'SKILL.md')
        except (OSError, NotImplementedError):
            self.skipTest('Host does not permit symbolic links.')
        with self.assertRaisesRegex(ValueError, 'regular file'):
            installer.install(self.source, self.target)

    def test_installer_cli_help_and_target_invocation(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--target', result.stdout)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), '--source', str(self.source), '--target', str(self.target)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target / 'SKILL.md').is_file())


class RuntimeTests(unittest.TestCase):
    def test_arguments_preserved_without_shell(self):
        with tempfile.TemporaryDirectory(prefix='runtime spaces ') as directory:
            workflow = Path(directory)
            (workflow / 'workflow.py').write_text('pass\n')
            worker = workflow / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            worker.parent.mkdir(parents=True)
            worker.write_text('mock worker')
            args = ['clip with spaces.mp4', '--subject', 'person; echo unsafe', '--mode', 'depth']
            with mock.patch.object(runtime, 'WORKFLOW', workflow):
                command = runtime.command_argv('prepare', args)
                self.assertEqual(command, [str(worker), str(workflow / 'workflow.py'), 'prepare'] + args)
                with mock.patch.object(runtime.subprocess, 'run', return_value=mock.Mock(returncode=7)) as launch:
                    self.assertEqual(runtime.main(['prepare'] + args), 7)
                    launch.assert_called_once_with(command, check=False)

    def test_help_works_without_runtime_dependencies(self):
        for arguments in (['--help'], ['prepare', '--help'], ['doctor', '--help']):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/runtime.py')] + arguments, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('usage:', result.stdout)

    def test_missing_runtime_has_actionable_platform_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = Path(directory)
            (workflow / 'workflow.py').write_text('pass')
            with mock.patch.object(runtime, 'WORKFLOW', workflow):
                with self.assertRaisesRegex(ValueError, 'WSL2' if os.name == 'nt' else 'setup.sh'):
                    runtime.command_argv('prepare', ['clip.mp4'])

    def test_offline_doctor_uses_current_python_without_venv(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = Path(directory)
            (workflow / 'doctor.py').write_text('pass')
            with mock.patch.object(runtime, 'WORKFLOW', workflow):
                self.assertEqual(runtime.command_argv('doctor', ['--mesh']), [sys.executable, str(workflow / 'doctor.py'), '--mesh'])


class PreparationCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow_path = str(ROOT / 'assets/workflow')
        sys.path.insert(0, cls.workflow_path)
        spec = importlib.util.spec_from_file_location('genjutsu_workflow_cli', ROOT / 'assets/workflow/workflow.py')
        cls.workflow = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.workflow)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(cls.workflow_path)

    def test_resume_preserves_saved_recipe_and_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'upload.mp4').write_bytes(b'test source')
            (folder / 'workflow-mode.json').write_text(json.dumps({'mode': 'depth_mesh', 'subject': 'person in blue', 'provider': 'replicate-chenxwh'}))
            args = mock.Mock(mode=None, subject=None, provider=None)
            with mock.patch.object(self.workflow, 'prepare_folder') as prepare, contextlib.redirect_stdout(io.StringIO()):
                self.workflow.resume_preparation(folder, args)
            prepare.assert_called_once_with(folder, 'depth_mesh', 'person in blue', 'replicate-chenxwh')

    def test_preparation_status_success_and_failure_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            fake = mock.Mock()
            fake.run.side_effect = lambda src, job, subject, provider, status: status('Preparing test fixture')
            with mock.patch.dict(sys.modules, {'pipeline': fake}), contextlib.redirect_stdout(io.StringIO()):
                self.workflow.prepare_folder(folder, 'depth', 'person', 'replicate')
            self.assertEqual(json.loads((folder / 'status.json').read_text())['state'], 'done')
            fake.run.side_effect = RuntimeError('TEST ERROR')
            with mock.patch.dict(sys.modules, {'pipeline': fake}), self.assertRaises(RuntimeError):
                self.workflow.prepare_folder(folder, 'depth', 'person', 'replicate')
            status = json.loads((folder / 'status.json').read_text())
            self.assertEqual(status['state'], 'error')
            self.assertEqual(status['error_type'], 'RuntimeError')
            self.assertNotIn('TEST ERROR', json.dumps(status))

    def test_submitted_job_is_not_reprepared(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / '.submission-seedance-draft.json').write_text('{}')
            fake = mock.Mock()
            with mock.patch.dict(sys.modules, {'pipeline': fake}), self.assertRaisesRegex(ValueError, 'intent'):
                self.workflow.prepare_folder(folder, 'depth', 'person', 'replicate')
            fake.run.assert_not_called()

    def test_missing_source_leaves_recoverable_error_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(self.workflow, 'ROOT', root), mock.patch.object(self.workflow.uuid, 'uuid4', return_value=mock.Mock(hex='a' * 32)), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(OSError):
                self.workflow.main(['prepare', str(root / 'missing.mp4'), '--mode', 'depth_mesh'])
            folder = root / 'runs' / ('a' * 32)
            self.assertEqual(json.loads((folder / 'status.json').read_text())['state'], 'error')
            self.assertEqual(json.loads((folder / 'workflow-mode.json').read_text())['mode'], 'depth_mesh')

    def test_doctor_checks_cv2_without_printing_keys(self):
        spec = importlib.util.spec_from_file_location('genjutsu_doctor', ROOT / 'assets/workflow/doctor.py')
        doctor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(doctor)
        output = io.StringIO()
        with mock.patch.object(doctor.importlib, 'import_module') as imports, mock.patch.object(doctor.shutil, 'which', return_value='/mock/rubberband'), mock.patch.object(doctor, 'setting', side_effect=lambda key, default='': 'tmpfiles' if key == 'MEDIA_HOST' else 'PRIVATE_TEST_KEY'), contextlib.redirect_stdout(output):
            self.assertEqual(doctor.main([]), 0)
        imports.assert_any_call('cv2')
        self.assertNotIn('PRIVATE_TEST_KEY', output.getvalue())
        self.assertIn('not verified remotely', output.getvalue())

    def test_free_threaded_doctor_fails_before_native_imports(self):
        spec=importlib.util.spec_from_file_location('genjutsu_doctor_free_threaded',ROOT/'assets/workflow/doctor.py')
        doctor=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(doctor)
        output=io.StringIO()
        with mock.patch.object(doctor.sysconfig,'get_config_var',return_value=1),mock.patch.object(doctor.importlib,'import_module') as imports,contextlib.redirect_stdout(output):
            self.assertEqual(doctor.main([]),1)
        imports.assert_not_called()
        self.assertIn('regular CPython',output.getvalue())


if __name__ == '__main__':
    unittest.main()
