# FastMCP Demo - Project Structure & Asset Organization

## 📁 Directory Structure

```
fastmcp_demo/
├── 📄 README.md                    # Main documentation
├── 📄 LICENSE                      # MIT License
├── 📄 pyproject.toml              # Project configuration
├── 📄 requirements.txt            # Production dependencies
├── 📄 requirements-dev.txt        # Development dependencies
├── 📄 demo.py                     # Main FastMCP server entry point
├── 📄 claude_desktop_config.json  # Claude Desktop configuration
├── 📄 server-info.json           # Generated server inspection report
├── 📄 test_claude_integration.py  # Integration test script
├── 📄 verify_setup.py             # Setup verification script
├── 📄 publish.bat                 # Windows publishing script
├── 📄 publish.sh                  # Unix publishing script
├──
├── 🔧 tools/                      # Tools package
│   ├── 📄 __init__.py            # Package initialization
│   ├── 📄 math_tools.py          # Mathematical operations
│   └── 📄 text_tools.py          # Text processing tools
├──
├── 🧪 tests/                      # Comprehensive test suite
│   ├── 📄 __init__.py            # Test package initialization
│   ├── 📄 README.md              # Test documentation
│   ├── 📄 run_tests.py           # Test runner script
│   ├── 📄 test_math_tools.py     # Math tools tests
│   ├── 📄 test_text_tools.py     # Text tools tests
│   ├── 📄 test_integration.py    # Integration tests
│   └── 📄 test_security.py       # Security validation tests
├──
├── 📚 docs/                       # Documentation directory
│   ├── 📄 PROJECT_STRUCTURE.md   # This file - project organization
│   ├── 📄 API_REFERENCE.md       # API documentation (future)
│   └── 📄 DEPLOYMENT_GUIDE.md    # Deployment instructions (future)
├──
├── 🖼️ images/                     # Project images directory
│   ├── � README.md              # Image organization guide
│   ├── 🖼️ claude-1.png           # Claude tools availability screenshot
│   ├── 🖼️ claude-2.png           # Claude calculator demo screenshot
│   ├── 🖼️ banner.png             # Project banner/hero image (future)
│   ├── 🖼️ logo.png               # Project logo (future)
│   └── 🖼️ architecture.png       # System architecture diagram (future)
├──
├── 🔧 .venv/                      # Virtual environment (created locally)
└── 🗂️ __pycache__/               # Python cache (auto-generated)
```

## 🖼️ Image Organization Guidelines

### Single Images Directory (`/images/`)
We use a single `images/` directory for all project visual assets to keep the structure simple and maintainable:

#### Current Images:
- **`claude-1.png`** - Claude Desktop tools availability screenshot
- **`claude-2.png`** - Claude Desktop calculator demo screenshot
- **`README.md`** - Image organization and guidelines

#### Recommended Future Images:
- **`banner.png`** - Hero banner for README header (recommended: 1200x400px)
- **`logo.png`** - Project logo (recommended: 256x256px, transparent background)
- **`architecture.png`** - System architecture diagram
- **`workflow.png`** - Development workflow diagram

## 📝 Image Usage in Markdown

### Current Usage in README
```markdown
![Claude prompt and response about tools](images/claude-1.png)
![Claude prompt and response when asking to calculate](images/claude-2.png)
```

### Recommended Future Usage

#### README Header
```markdown
![FastMCP Demo Banner](images/banner.png)

# FastMCP Demo
```

#### Features Section
```markdown
## 🚀 Features
![Features Overview](images/features.png)
```

#### Architecture Documentation
```markdown
## Architecture
![System Architecture](images/architecture.png)
```

## 🎨 Image Specifications

### Recommended Formats
- **PNG** - For logos, diagrams, screenshots (supports transparency)
- **JPG** - For photos, complex images (smaller file size)
- **SVG** - For vector graphics, simple diagrams (scalable)

### Size Guidelines
- **Banner/Hero**: 1200x400px (3:1 ratio)
- **Logo**: 256x256px (square, transparent background)
- **Screenshots**: 1024x768px or 1280x720px (4:3 or 16:9 ratio)
- **Diagrams**: 800x600px minimum for readability

### File Naming Convention
- Use lowercase with hyphens: `claude-demo.png`
- Be descriptive: `architecture-diagram.png`
- Include version if needed: `logo-v2.png`

## 🔗 Asset Management

### Version Control
- Add images to Git repository
- Use `.gitignore` for large temporary image files
- Consider using Git LFS for large assets

### Optimization
- Compress images for web (use tools like TinyPNG)
- Provide retina/@2x versions for high-DPI displays
- Consider WebP format for modern browsers

### Accessibility
- Add meaningful alt text for all images
- Ensure good contrast for text overlays
- Provide text alternatives for complex diagrams
