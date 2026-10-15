### license="Apache-2.0",
### author="Todd Wolven",
### author_email="twolven@neotitanllc.com",

from setuptools import setup, find_packages

setup(
    name="mcp-server-puppeteer",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "playwright>=1.40.0",
        "mcp-server>=0.1.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-server-puppeteer=mcp_server_puppeteer.server:main",
        ],
    },
    python_requires=">=3.8",
)
