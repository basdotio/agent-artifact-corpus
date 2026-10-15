import asyncio
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
import fastmcp_server as server
from printer_client import MockPrinter

STEPS = [{'axis': 'x', 'distance_mm': 50}, {'axis': 'x', 'distance_mm': -50}]


class MCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.printer = MockPrinter()
        guard = patch.object(server, 'printer', self.printer)
        guard.start()
        self.addCleanup(guard.stop)
        server.pending.clear()

    async def test_z_dictionary_preview_execution_and_rejection(self):
        async with Client(server.mcp) as client:
            steps = [{'axis': 'z', 'distance_mm': 5}, {'axis': 'x', 'distance_mm': 5},
                     {'axis': 'z', 'distance_mm': -2}]
            preview = (await client.call_tool('preview_sequence', {'steps': steps, 'z_speed_mm_s': 1})).data
            self.assertEqual(preview['z_bounds'], [0, 235])
            self.assertEqual(preview['step_speeds_mm_s'], [1, 20, 1])
            result = (await client.call_tool('execute_sequence', {'token': preview['token'], 'operator_confirmed': True})).data
            self.assertEqual(result['reported_position'], [105, 100, 8])
            self.assertIn('G1 Z10.000 F60.000000', self.printer.submitted_scripts[0])
            for request in ({'steps': [{'axis': 'z', 'distance_mm': -9}]},
                            {'steps': steps, 'z_speed_mm_s': 3}):
                rejected = await client.call_tool('preview_sequence', request, raise_on_error=False)
                self.assertTrue(rejected.is_error)
            self.assertEqual(len(self.printer.submitted_scripts), 1)

    async def test_dictionary_tools_roundtrip_and_single_use_token(self):
        async with Client(server.mcp) as client:
            tools = {t.name for t in await client.list_tools()}
            self.assertEqual(tools, {'printer_status', 'preview_sequence', 'execute_sequence', 'emergency_stop'})
            status = (await client.call_tool('printer_status')).data
            self.assertTrue(status['simulated'])
            preview = (await client.call_tool('preview_sequence', {'steps': STEPS})).data
            self.assertEqual(len(preview['targets']), 2)
            self.assertEqual(preview['startup_zero_window_seconds'], 0.5)
            self.assertEqual(self.printer.submitted_scripts, [])
            request = {'token': preview['token'], 'operator_confirmed': True}
            result = (await client.call_tool('execute_sequence', request)).data
            self.assertTrue(result['ok'])
            again = await client.call_tool('execute_sequence', request, raise_on_error=False)
            self.assertTrue(again.is_error)
            self.assertEqual(len(self.printer.submitted_scripts), 1)
            self.assertTrue((await client.call_tool('emergency_stop')).data['stop_confirmed'])

    async def test_real_mode_disabled_without_local_enable(self):
        self.printer.simulated = False
        prepared = server.preview_impl(STEPS, 20)
        with patch.dict(os.environ, {'PRINTER_ALLOW_MOTION': '0'}):
            with self.assertRaisesRegex(ValueError, 'disabled'):
                server.execute_impl(prepared['token'], True)
        self.assertEqual(self.printer.submitted_scripts, [])

    async def test_unconfirmed_expired_and_changed_position_reject(self):
        prepared = server.preview_impl(STEPS, 20)
        with self.assertRaisesRegex(ValueError, 'confirmation'):
            server.execute_impl(prepared['token'], False)
        server.pending[prepared['token']]['expires'] = 0
        with self.assertRaisesRegex(ValueError, 'expired'):
            server.execute_impl(prepared['token'], True)
        prepared = server.preview_impl(STEPS, 20)
        for obj, field in (('toolhead', 'position'), ('motion_report', 'live_position'), ('gcode_move', 'position'), ('gcode_move', 'gcode_position')):
            self.printer.state[obj][field][0] += 1
        with self.assertRaisesRegex(ValueError, 'changed'):
            server.execute_impl(prepared['token'], True)
        self.assertEqual(self.printer.submitted_scripts, [])

    async def test_emergency_stop_is_responsive_during_execution(self):
        entered, release = threading.Event(), threading.Event()
        original = self.printer.request
        def request(message):
            if message['action'] == 'run':
                entered.set()
                release.wait(3)
            return original(message)
        async with Client(server.mcp) as client:
            token = (await client.call_tool('preview_sequence', {'steps': STEPS})).data['token']
            with patch.object(self.printer, 'request', side_effect=request):
                running = asyncio.create_task(client.call_tool('execute_sequence', {'token': token, 'operator_confirmed': True}, raise_on_error=False))
                try:
                    self.assertTrue(await asyncio.to_thread(entered.wait, 2))
                    stopped = await asyncio.wait_for(client.call_tool('emergency_stop'), 1)
                    self.assertTrue(stopped.data['stop_confirmed'])
                finally:
                    release.set()
                self.assertTrue((await running).is_error)

    async def test_stdio_subprocess_outside_project_directory(self):
        transport = PythonStdioTransport(Path(server.__file__), python_cmd=sys.executable,
                                          env={'PRINTER_MODE': 'mock', 'PRINTER_ALLOW_MOTION': '0'}, cwd='/tmp')
        async with Client(transport) as client:
            preview = (await client.call_tool('preview_sequence', {'steps': STEPS})).data
            result = (await client.call_tool('execute_sequence', {'token': preview['token'], 'operator_confirmed': True})).data
            self.assertTrue(result['simulated'])
            self.assertEqual(result['reported_position'], [100, 100, 5])


if __name__ == '__main__':
    unittest.main()
