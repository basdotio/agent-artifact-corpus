"""
Setup script for Brightspace MCP Server
"""

import subprocess
import sys
import os


def create_virtual_environment():

    """Create virtual environment for the project"""
    print("Creating virtual environment...")
    
    # Try Python 3.12 first (more compatible with Playwright)
    python_versions = ["python3.12", "python3.11", "python3"]
    python_executable = None
    
    for python_cmd in python_versions:
        try:
            result = subprocess.run([python_cmd, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Using {python_cmd}: {result.stdout.strip()}")
                python_executable = python_cmd
                break
        except FileNotFoundError:
            continue
    
    if not python_executable:
        print("Error: No compatible Python version found. Please install Python 3.11 or 3.12")
        sys.exit(1)
    
    subprocess.check_call([python_executable, "-m", "venv", "venv"])
    print("✓ Virtual environment created")
    
    # Determine the correct activation script path and Python executable
    if os.name == 'nt':  # Windows
        activate_script = os.path.join("venv", "Scripts", "activate.bat")
        venv_python_executable = os.path.join("venv", "Scripts", "python.exe")
    else:  # Unix/Linux/macOS
        activate_script = os.path.join("venv", "bin", "activate")
        venv_python_executable = os.path.join("venv", "bin", "python")
    
    print(f"✓ Virtual environment created at: {os.path.abspath('venv')}")
    print(f"✓ To activate: source {activate_script}" if os.name != 'nt' else f"✓ To activate: {activate_script}")
    
    return venv_python_executable


def install_requirements(python_executable=None):
    """Install required Python packages"""
    if python_executable is None:
        python_executable = sys.executable
        
    print("Installing Python requirements...")
    subprocess.check_call([python_executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([python_executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✓ Python requirements installed")


def install_playwright_browsers(python_executable=None):
    """Install Playwright browsers"""
    if python_executable is None:
        python_executable = sys.executable
        
    print("Installing Playwright browsers...")
    subprocess.check_call([python_executable, "-m", "playwright", "install", "chromium"])
    print("✓ Playwright browsers installed")


def create_env_file():
    """Create .env file template"""
    env_content = """# Purdue Brightspace Credentials
PURDUE_USERNAME=your_purdue_username
PURDUE_PASSWORD=your_purdue_password

# Scraping Configuration
HEADLESS=False
TIMEOUT=30000
"""
    
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write(env_content)
        print("✓ Created .env file template")
    else:
        print("✓ .env file already exists")


def main():
    """Run setup"""
    print("Setting up Brightspace MCP Server...")
    
    try:
        # Create virtual environment
        python_executable = create_virtual_environment()
        
        # Install requirements in the virtual environment
        install_requirements(python_executable)
        install_playwright_browsers(python_executable)
        create_env_file()
        
        print("\n🎉 Setup complete!")
        print("\nNext steps:")
        print("1. Activate the virtual environment:")
        if os.name == 'nt':  # Windows
            print("   venv\\Scripts\\activate")
        else:  # Unix/Linux/macOS
            print("   source venv/bin/activate")
        print("2. Edit .env file with your Purdue credentials")
        print("3. Run: python testing/playwright_trial.py")
        print("4. Run: python brightspace_api.py")
        
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
