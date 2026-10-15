"""
Tests for configuration loading logic
"""

import os
import tempfile
from unittest.mock import mock_open, patch

import pytest
import yaml


class TestConfigLoading:
    """Test configuration loading scenarios"""

    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.yaml")

    def _load_config_logic(self, config_file_path):
        """
        Simulate the config loading logic from server.py
        Returns: (device_name, messages)
        """
        messages = []
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

        return device_name, messages

    def test_no_config_file(self):
        """Test behavior when config file doesn't exist"""
        non_existent_file = os.path.join(self.temp_dir, "non_existent.yaml")

        device_name, messages = self._load_config_logic(non_existent_file)

        assert device_name is None
        assert any("not found" in msg for msg in messages)
        assert any("auto-selection" in msg for msg in messages)

    def test_config_with_null_name(self):
        """Test config with name: null"""
        config_content = """
device:
  name: null
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        device_name, messages = self._load_config_logic(self.config_file)

        assert device_name is None
        assert any("Loaded config" in msg for msg in messages)
        assert any("auto-select" in msg for msg in messages)

    def test_config_with_empty_string_name(self):
        """Test config with name: ''"""
        config_content = """
device:
  name: ""
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        device_name, messages = self._load_config_logic(self.config_file)

        assert device_name is None
        assert any("auto-select" in msg for msg in messages)

    def test_config_with_whitespace_name(self):
        """Test config with name containing only whitespace"""
        config_content = """
device:
  name: "   \t  \n  "
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        device_name, messages = self._load_config_logic(self.config_file)

        assert device_name is None
        assert any("auto-select" in msg for msg in messages)

    def test_config_without_name_field(self):
        """Test config with device section but no name field"""
        config_content = """
device:
  # name field is missing
  other_setting: value
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        device_name, messages = self._load_config_logic(self.config_file)

        assert device_name is None
        assert any("auto-select" in msg for msg in messages)

    def test_config_without_device_section(self):
        """Test config without device section"""
        config_content = """
# No device section
other_config: value
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        device_name, messages = self._load_config_logic(self.config_file)

        assert device_name is None
        assert any("auto-select" in msg for msg in messages)

    def test_config_with_valid_device_name(self):
        """Test config with valid device name"""
        config_content = """
device:
  name: "test-device-123"
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        device_name, messages = self._load_config_logic(self.config_file)

        assert device_name == "test-device-123"
        assert any(
            "Configured device: test-device-123" in msg for msg in messages)

    def test_config_with_device_name_with_whitespace(self):
        """Test config with device name that has surrounding whitespace"""
        config_content = """
device:
  name: "  test-device-123  "
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        device_name, messages = self._load_config_logic(self.config_file)

        assert device_name == "test-device-123"  # Should be trimmed
        assert any(
            "Configured device: test-device-123" in msg for msg in messages)

    def test_invalid_yaml_config(self):
        """Test behavior with invalid YAML"""
        config_content = """
device:
  name: "test-device
  # Missing closing quote - invalid YAML
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        with pytest.raises(Exception):
            self._load_config_logic(self.config_file)

    def test_empty_config_file(self):
        """Test behavior with empty config file"""
        with open(self.config_file, 'w') as f:
            f.write("")

        device_name, messages = self._load_config_logic(self.config_file)

        assert device_name is None
        assert any("auto-select" in msg for msg in messages)

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
