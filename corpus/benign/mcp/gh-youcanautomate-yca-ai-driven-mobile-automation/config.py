"""Configuration management for mobile automation."""
import os
from typing import Dict, Any, Optional


class BedrockConfig:
    """AWS Bedrock configuration."""
    
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
        self.anthropic_version = os.getenv("BEDROCK_ANTHROPIC_VERSION", "bedrock-2023-06-01")
        self.max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "2000"))


class AppiumConfig:
    """Appium configuration."""
    
    def __init__(self, platform: str = "ios"):
        self.platform = platform
        
        if platform == "ios":
            self.device_name = os.getenv("IOS_DEVICE_NAME", "iPhone 14")
            self.bundle_id = os.getenv("IOS_BUNDLE_ID", "com.example.app")
            self.simulator_udid = os.getenv("IOS_SIMULATOR_UDID", "")
        else:
            self.device_id = os.getenv("ANDROID_DEVICE_ID", "emulator-5554")
            self.app_package = os.getenv("ANDROID_APP_PACKAGE", "com.example.app")
            self.app_activity = os.getenv("ANDROID_APP_ACTIVITY", ".MainActivity")


class AutomationConfig:
    """Automation configuration."""
    
    def __init__(self):
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.timeout_seconds = int(os.getenv("AUTOMATION_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.screenshots_dir = os.getenv("SCREENSHOTS_DIR", "./screenshots")
        self.appium_url = os.getenv("APPIUM_URL", "http://localhost:4723")


class Config:
    """Unified configuration manager."""
    
    def __init__(self, platform: str = "ios"):
        self.platform = platform
        self.bedrock = BedrockConfig()
        self.appium = AppiumConfig(platform)
        self.automation = AutomationConfig()
    
    def validate(self) -> bool:
        """Validate configuration."""
        # Check AWS credentials
        if not os.getenv("AWS_ACCESS_KEY_ID"):
            print("⚠ Warning: AWS_ACCESS_KEY_ID not set")
        
        if not os.getenv("AWS_SECRET_ACCESS_KEY"):
            print("⚠ Warning: AWS_SECRET_ACCESS_KEY not set")
        
        return True
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get device info for orchestrator."""
        info = {
            "platform": self.platform
        }
        
        if self.platform == "ios":
            info["device_name"] = self.appium.device_name
            info["bundle_id"] = self.appium.bundle_id
            if self.appium.simulator_udid:
                info["simulator_udid"] = self.appium.simulator_udid
        else:
            info["device_id"] = self.appium.device_id
            info["app_package"] = self.appium.app_package
            info["app_activity"] = self.appium.app_activity
        
        return info
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "platform": self.platform,
            "bedrock": {
                "region": self.bedrock.region,
                "model_id": self.bedrock.model_id,
                "anthropic_version": self.bedrock.anthropic_version,
                "max_tokens": self.bedrock.max_tokens
            },
            "appium": {
                "platform": self.appium.platform,
                "device_id": getattr(self.appium, "device_id", None),
                "device_name": getattr(self.appium, "device_name", None),
                "bundle_id": getattr(self.appium, "bundle_id", None)
            },
            "automation": {
                "debug": self.automation.debug,
                "timeout_seconds": self.automation.timeout_seconds,
                "max_retries": self.automation.max_retries,
                "appium_url": self.automation.appium_url
            }
        }
