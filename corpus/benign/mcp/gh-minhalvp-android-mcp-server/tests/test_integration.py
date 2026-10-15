"""
Integration tests for the complete server initialization flow
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

from adbdevicemanager import AdbDeviceManager

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestServerIntegration:
    """Test complete server initialization scenarios"""

    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.yaml")

    def _simulate_server_initialization(self, config_file_path):
        """
        Simulate the complete server initialization process
        Returns: (device_manager, messages)
        """
        import yaml

        messages = []
        config = {}
        device_name = None

        if os.path.exists(config_file_path):
            try:
                with open(config_file_path) as f:
                    config = yaml.safe_load(f.read()) or {}
                device_config = config.get("device", {})
                configured_device_name = device_config.get(
                    "name") if device_config else None

                if configured_device_name and configured_device_name.strip():
                    device_name = configured_device_name.strip()
                    messages.append(f"Loaded config from {config_file_path}")
                    messages.append(f"Configured device: {device_name}")
                else:
                    messages.append(f"Loaded config from {config_file_path}")
                    messages.append(
                        "No device specified in config, will auto-select if only one device connected")
            except Exception as e:
                messages.append(
                    f"Error loading config file {config_file_path}: {e}")
                raise
        else:
            messages.append(
                f"Config file {config_file_path} not found, using auto-selection for device")

        # Initialize device manager (with mocked dependencies)
        device_manager = AdbDeviceManager(device_name, exit_on_error=False)

        return device_manager, messages

    @patch('adbdevicemanager.AdbDeviceManager.check_adb_installed')
    @patch('adbdevicemanager.AdbDeviceManager.get_available_devices')
    @patch('adbdevicemanager.AdbClient')
    def test_no_config_auto_selection_success(self, mock_adb_client, mock_get_devices, mock_check_adb):
        """Test successful server start with no config file and single device"""
        # Setup mocks
        mock_check_adb.return_value = True
        mock_get_devices.return_value = ["device123"]
        mock_device = MagicMock()
        mock_adb_client.return_value.device.return_value = mock_device

        # Use non-existent config file
        non_existent_config = os.path.join(self.temp_dir, "non_existent.yaml")

        with patch('builtins.print') as mock_print:
            device_manager, messages = self._simulate_server_initialization(
                non_existent_config)

        # Verify results
        assert device_manager.device == mock_device
        assert any("not found" in msg for msg in messages)
        assert any("auto-selection" in msg for msg in messages)
        mock_print.assert_called_with(
            "No device specified, automatically selected: device123")

    @patch('adbdevicemanager.AdbDeviceManager.check_adb_installed')
    @patch('adbdevicemanager.AdbDeviceManager.get_available_devices')
    @patch('adbdevicemanager.AdbClient')
    def test_config_with_null_device_auto_selection(self, mock_adb_client, mock_get_devices, mock_check_adb):
        """Test server start with config file containing name: null"""
        # Setup mocks
        mock_check_adb.return_value = True
        mock_get_devices.return_value = ["device456"]
        mock_device = MagicMock()
        mock_adb_client.return_value.device.return_value = mock_device

        # Create config with null device name
        config_content = """
device:
  name: null
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        with patch('builtins.print') as mock_print:
            device_manager, messages = self._simulate_server_initialization(
                self.config_file)

        # Verify results
        assert device_manager.device == mock_device
        assert any("Loaded config" in msg for msg in messages)
        assert any("auto-select" in msg for msg in messages)
        mock_print.assert_called_with(
            "No device specified, automatically selected: device456")

    @patch('adbdevicemanager.AdbDeviceManager.check_adb_installed')
    @patch('adbdevicemanager.AdbDeviceManager.get_available_devices')
    @patch('adbdevicemanager.AdbClient')
    def test_config_with_specific_device(self, mock_adb_client, mock_get_devices, mock_check_adb):
        """Test server start with config file specifying a device"""
        # Setup mocks
        mock_check_adb.return_value = True
        mock_get_devices.return_value = ["device123", "device456"]
        mock_device = MagicMock()
        mock_adb_client.return_value.device.return_value = mock_device

        # Create config with specific device name
        config_content = """
device:
  name: "device456"
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        device_manager, messages = self._simulate_server_initialization(
            self.config_file)

        # Verify results
        assert device_manager.device == mock_device
        mock_adb_client.return_value.device.assert_called_once_with(
            "device456")
        assert any("Configured device: device456" in msg for msg in messages)

    @patch('adbdevicemanager.AdbDeviceManager.check_adb_installed')
    @patch('adbdevicemanager.AdbDeviceManager.get_available_devices')
    def test_multiple_devices_no_config_error(self, mock_get_devices, mock_check_adb):
        """Test server initialization fails with multiple devices and no config"""
        # Setup mocks
        mock_check_adb.return_value = True
        mock_get_devices.return_value = ["device123", "device456"]

        # Use non-existent config file
        non_existent_config = os.path.join(self.temp_dir, "non_existent.yaml")

        try:
            device_manager, messages = self._simulate_server_initialization(
                non_existent_config)
            assert False, "Should have raised an exception"
        except RuntimeError as e:
            assert "Multiple devices connected" in str(e)
            assert "device123" in str(e)
            assert "device456" in str(e)

    @patch('adbdevicemanager.AdbDeviceManager.check_adb_installed')
    @patch('adbdevicemanager.AdbDeviceManager.get_available_devices')
    def test_device_not_found_error(self, mock_get_devices, mock_check_adb):
        """Test server initialization fails when specified device is not found"""
        # Setup mocks
        mock_check_adb.return_value = True
        mock_get_devices.return_value = ["device123"]

        # Create config with non-existent device name
        config_content = """
device:
  name: "non-existent-device"
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        try:
            device_manager, messages = self._simulate_server_initialization(
                self.config_file)
            assert False, "Should have raised an exception"
        except RuntimeError as e:
            assert "Device non-existent-device not found" in str(e)
            assert "Available devices" in str(e)

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
