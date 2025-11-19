# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Revelation is a CLI tool that makes reveal.js presentations easy by using markdown files and serving them locally. It provides presentation boilerplate creation, custom CSS theming, static HTML export, and browser live-reload on markdown changes.

## Development Commands

### Installation & Setup
```bash
# Install development dependencies
make install.hack

# Install reveal.js (required before running presentations)
revelation installreveal
```

### Testing
```bash
# Run all tests
make test

# Run tests with coverage
make cover

# Run specific test file
nosetests tests/test_app.py
```

### Linting & Formatting
```bash
# Lint code with flake8
make lint

# Format code with black and isort
make format
```

### Building & Publishing
```bash
# Build package for distribution
make build

# Publish to PyPI (requires twine)
make publish

# Clean build artifacts
make clean
```

### Running Presentations
```bash
# Start presentation server (default port 4000)
revelation start PRESENTATION_PATH

# Start with custom port and hostname
revelation start PRESENTATION_PATH --port 5000 --hostname 0.0.0.0

# Start with debug mode
revelation start PRESENTATION_PATH --debug

# Create new presentation boilerplate
revelation mkpresentation my_presentation

# Export to static HTML
revelation mkstatic PRESENTATION_PATH --output-folder output
```

## Architecture

### Core Components

**CLI Layer (`revelation/cli.py`)**
- Entry point for all commands using Click framework
- Commands: `start`, `mkpresentation`, `mkstatic`, `installreveal`, `installrevealplugin`
- Handles command-line arguments and invokes core application logic
- Automatically installs reveal.js if missing before running presentations

**Application Layer (`revelation/app.py`)**
- `Revelation` class: Main WSGI application that renders presentations
- Uses Jinja2 templates to generate HTML from markdown slides
- Implements `SharedDataMiddleware` for serving static files, media, and themes
- `load_slides()`: Parses markdown files using configured separators (horizontal: `---`, vertical: `--`)
- Supports multiple markdown files in a directory (loads all `*.md` files in sorted order)

**Live Reload System (`revelation/app.py`)**
- `PresentationReloader`: WebSocket application for live reload
- `PresentationReloadWebSocketSendEvent`: File system watcher using `watchdog`
- Watches for changes to `.md` and `.css` files and triggers browser reload

**Configuration (`revelation/config.py`)**
- `Config` class: Dictionary-based configuration handler
- Loads defaults from `default_config.py`
- Merges with user's `config.py` (if present in presentation directory)
- All uppercase variables are loaded as config keys

**Utilities (`revelation/utils.py`)**
- `download_reveal()`: Downloads reveal.js from GitHub
- `extract_file()`: Handles tar.gz and zip extraction
- `make_presentation()`: Creates boilerplate presentation structure
- `move_and_replace()`: Utility for moving/replacing files
- `normalize_newlines()`: Converts line endings to Unix format
- `install_reveal_plugin()`: Plugin installation logic

### Data Flow

1. **Starting a Presentation**: CLI validates presentation path → checks for reveal.js → initializes `Revelation` app → starts WebSocket server with reloader
2. **Rendering**: Request arrives → `dispatch_request()` loads config → loads slides from markdown → renders Jinja2 template → returns HTML response
3. **Live Reload**: File watcher detects changes → WebSocket sends reload message → browser refreshes presentation

### Presentation Structure

```
presentation_name/
├── slides.md          # Main markdown file (or multiple *.md files)
├── config.py          # Optional: Override default config
├── media/             # Optional: Images and media files
└── theme/             # Optional: Custom CSS themes
```

### Configuration System

Configuration supports two formats:
- **TOML** (recommended, secure): `config.toml`
- **Python** (deprecated, security risk): `config.py`

**Security Note**: Python config files use `exec()` and are deprecated. Use TOML format for new presentations. See `MIGRATION_GUIDE.md` for migration instructions.

Configuration options (both formats):
- `reveal_meta`: Title, author, description metadata (TOML table / Python dict)
- `reveal_theme`: Theme name (beige, black, blood, league, moon, night, etc.) or custom theme path
- `reveal_theme_logo`: Custom logo selection (e.g., "master", "ggt")
- `reveal_licence`: Creative Commons license (e.g., "by-sa", "by-nc-nd")
- `reveal_template`: Template file to use (e.g., "presentation.html", "myPresentation.html")
- `reveal_slide_separator`: Horizontal slide separator (default: `---`)
- `reveal_vertical_slide_separator`: Vertical slide separator (default: `--`)
- `reveal_config`: Reveal.js configuration (controls, progress, transitions, etc.)

**TOML Config Security**: Only whitelisted keys are allowed. Unknown keys generate warnings. Type validation prevents configuration errors.

**Python Config Security**: Restricted builtins sandbox limits damage from malicious configs, but migration to TOML is strongly recommended.

### Template System

Templates in `revelation/templates/` use Jinja2 and receive:
- `meta`: Presentation metadata
- `slides`: Nested list of slide content (horizontal → vertical)
- `config`: reveal.js configuration dictionary
- `theme`: Theme CSS path
- `style`: Custom style override path
- `reloader`: Boolean for WebSocket reload script
- `logo`: Logo selection
- `licence`: Creative Commons license

## Testing Notes

- Tests use `nose` test runner
- Mock library used for simulating external dependencies
- Coverage target tracked via coveralls
- All test files in `tests/` directory follow `test_*.py` naming
