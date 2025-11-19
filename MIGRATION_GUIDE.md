# Migration Guide: Python to TOML Configuration

## Overview

Starting with version 0.2.0, Revelation introduces **TOML configuration format** as the secure, recommended way to configure presentations. Python configuration files (`.py`) are now **deprecated** due to security concerns with arbitrary code execution.

## Why Migrate?

- **Security**: TOML files cannot execute arbitrary code
- **Simplicity**: Cleaner syntax, easier to read and write
- **Safety**: Type validation and key whitelisting prevent configuration errors
- **Standard**: TOML is a widely-used configuration format

## Quick Migration

### Before (config.py)
```python
REVEAL_META = {
    "title": "My Presentation",
    "author": "John Doe",
    "description": "An awesome presentation"
}

REVEAL_SLIDE_SEPARATOR = "---"
REVEAL_VERTICAL_SLIDE_SEPARATOR = "--"

REVEAL_THEME = "black"

REVEAL_CONFIG = {
    "controls": True,
    "progress": True,
    "slideNumber": "c/t",
    "transition": "slide"
}
```

### After (config.toml)
```toml
reveal_slide_separator = "---"
reveal_vertical_slide_separator = "--"
reveal_theme = "black"

[reveal_meta]
title = "My Presentation"
author = "John Doe"
description = "An awesome presentation"

[reveal_config]
controls = true
progress = true
slideNumber = "c/t"
transition = "slide"
```

## Detailed Migration Steps

### Step 1: Create config.toml

Create a new file `config.toml` in your presentation directory.

### Step 2: Convert Metadata

Python dictionary becomes a TOML table:

```python
# OLD
REVEAL_META = {
    "title": "My Title",
    "author": "Author Name"
}
```

```toml
# NEW
[reveal_meta]
title = "My Title"
author = "Author Name"
```

### Step 3: Convert Simple Values

Uppercase Python constants become lowercase TOML keys:

```python
# OLD
REVEAL_THEME = "night"
REVEAL_SLIDE_SEPARATOR = "---"
```

```toml
# NEW
reveal_theme = "night"
reveal_slide_separator = "---"
```

### Step 4: Convert reveal_config

Python dictionary becomes a TOML table:

```python
# OLD
REVEAL_CONFIG = {
    "controls": True,
    "progress": False,
    "slideNumber": "c/t"
}
```

```toml
# NEW
[reveal_config]
controls = true
progress = false
slideNumber = "c/t"
```

### Step 5: Test Your Configuration

```bash
# Test with TOML config
revelation start /path/to/presentation --config config.toml
```

### Step 6: Remove Python Config (Optional)

Once verified, you can remove your old `config.py` file.

## Type Conversion Reference

| Python | TOML | Example |
|--------|------|---------|
| `True` | `true` | `controls = true` |
| `False` | `false` | `progress = false` |
| `None` | (omit or empty string) | `parallaxBackgroundImage = ""` |
| `"string"` | `"string"` | `theme = "black"` |
| `123` | `123` | `width = 1920` |
| `{"key": "value"}` | `[section]`<br>`key = "value"` | See tables below |

## Complete Example

### Full config.py
```python
REVEAL_META = {
    "title": "Advanced Python",
    "author": "Jane Smith",
    "description": "Deep dive into Python"
}

REVEAL_SLIDE_SEPARATOR = "---"
REVEAL_VERTICAL_SLIDE_SEPARATOR = "--"
REVEAL_THEME = "moon"
REVEAL_THEME_LOGO = "ggt"
REVEAL_LICENCE = "by-sa"
REVEAL_TEMPLATE = "myPresentation.html"

REVEAL_CONFIG = {
    "width": 1920,
    "height": 1080,
    "controls": True,
    "progress": True,
    "slideNumber": "c/t",
    "history": True,
    "center": True,
    "transition": "slide",
    "transitionSpeed": "default"
}
```

### Equivalent config.toml
```toml
# Presentation metadata
[reveal_meta]
title = "Advanced Python"
author = "Jane Smith"
description = "Deep dive into Python"

# Basic configuration
reveal_slide_separator = "---"
reveal_vertical_slide_separator = "--"
reveal_theme = "moon"
reveal_theme_logo = "ggt"
reveal_licence = "by-sa"
reveal_template = "myPresentation.html"

# Reveal.js options
[reveal_config]
width = 1920
height = 1080
controls = true
progress = true
slideNumber = "c/t"
history = true
center = true
transition = "slide"
transitionSpeed = "default"
```

## Allowed Configuration Keys

For security, only these configuration keys are allowed:

- `reveal_meta` (table)
- `reveal_slide_separator` (string)
- `reveal_vertical_slide_separator` (string)
- `reveal_theme` (string)
- `reveal_theme_logo` (string)
- `reveal_licence` (string)
- `reveal_template` (string)
- `reveal_config` (table)

Unknown keys will generate warnings and be ignored.

## Troubleshooting

### "TOML support requires 'tomli' package"

For Python < 3.11, install tomli:
```bash
pip install tomli
```

For Python >= 3.11, tomllib is built-in.

### "Unknown configuration key"

Check the spelling and case. TOML keys are case-insensitive and will be converted to uppercase internally, but should be lowercase in your file for consistency.

### "Invalid type for configuration key"

Ensure your value types match expectations:
- Strings use quotes: `"value"`
- Booleans are lowercase: `true`, `false`
- Numbers have no quotes: `1920`
- Tables use `[section_name]`

### Still Using Python Config?

Python config files still work but generate a deprecation warning. They will be removed in a future version. The Python config execution is now sandboxed with restricted builtins for safety, but **migration to TOML is strongly recommended**.

## Benefits of TOML

1. **No Code Execution**: TOML is pure data, cannot run arbitrary code
2. **Validation**: Automatic type checking and key validation
3. **Comments**: Use `#` for comments
4. **Readable**: Clean, INI-like syntax
5. **Standard**: Used by many Python projects (pyproject.toml, etc.)

## Need Help?

- See `example_slides/config.toml` for a complete example
- Check the README for configuration options
- Report issues at https://github.com/humrochagf/revelation/issues
