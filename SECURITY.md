# Security Improvements

This document outlines the security enhancements made to Revelation to address critical vulnerabilities.

## Summary of Changes

### 🔒 Critical Security Fixes

#### 1. **TOML Configuration Format (CVE Prevention)**

**Problem**: Python configuration files used `exec()` to execute arbitrary code, allowing malicious config files to:
- Execute system commands
- Access sensitive files
- Install malware
- Exfiltrate data

**Solution**:
- Implemented secure TOML configuration format
- TOML is pure data and cannot execute code
- Added configuration key whitelist
- Added type validation
- Python configs now sandboxed with restricted builtins

**Impact**: Eliminates arbitrary code execution vulnerability

**Files Modified**:
- `revelation/config.py`: Added TOML support with validation
- `revelation/convert_config.py`: Automatic conversion utility

#### 2. **Path Traversal Protection**

**Problem**: Media, theme, and style paths were not validated, allowing:
- Access to files outside presentation directory
- Reading sensitive system files (e.g., `/etc/passwd`)
- Potential information disclosure

**Solution**:
- Added `_validate_path()` method with security checks
- Detects and blocks `..` path traversal attempts
- Validates file/directory existence and type
- Converts all paths to absolute paths
- Uses `pathlib.Path` for safer path operations

**Impact**: Prevents unauthorized file system access

**Files Modified**:
- `revelation/app.py`: Added path validation to `Revelation.__init__()`

#### 3. **Dependency Updates**

**Problem**: Critical vulnerabilities in outdated dependencies:
- Jinja2 2.10.3 (2019) → Multiple CVE vulnerabilities
- Werkzeug 0.16.0 (2019) → Security issues
- Python 3.6-3.8 → End of life

**Solution**:
- Updated to Jinja2 >=3.1.4 (patched)
- Updated to Werkzeug >=3.0.4 (patched)
- Minimum Python version: 3.10
- Added `tomli` for TOML support on Python < 3.11

**Impact**: Removes known CVE vulnerabilities

**Files Modified**:
- `pyproject.toml`: Updated all dependencies

## Security Features

### Configuration Security

1. **Whitelisted Keys**:
   - Only allow known configuration keys
   - Unknown keys generate warnings
   - Prevents configuration injection

2. **Type Validation**:
   - Enforce expected types for each key
   - `reveal_meta` must be dict
   - `reveal_theme` must be string
   - Invalid types are rejected

3. **Sandboxed Python Configs** (deprecated):
   - Restricted `__builtins__`
   - No access to `import`, `open`, `eval`, etc.
   - Only safe types: `str`, `int`, `bool`, `list`, `dict`

### File System Security

1. **Path Validation**:
   - All paths resolved to absolute
   - Path traversal (`..*`) blocked
   - Existence and type checking
   - Symlinks resolved safely

2. **Type Enforcement**:
   - Media/theme must be directories
   - Style must be a file
   - Validation happens before use

### User Warnings

1. **Deprecation Warnings**:
   - Python config files show deprecation warning
   - Suggests migration to TOML
   - Provides conversion command

2. **Interactive Conversion**:
   - `revelation start` offers to convert Python configs
   - One-click migration to TOML
   - Preserves original file

## Migration Guide

Users with existing Python config files should:

1. **Run conversion utility**:
   ```bash
   revelation convertconfig config.py
   ```

2. **Or convert manually** (see `MIGRATION_GUIDE.md`)

3. **Test TOML config**:
   ```bash
   revelation start presentation --config config.toml
   ```

4. **Remove Python config** once verified

## Security Best Practices

### For Users

1. ✅ **Use TOML configs** for all new presentations
2. ✅ **Migrate existing Python configs** to TOML
3. ✅ **Review config files** from untrusted sources
4. ✅ **Keep Revelation updated** to get security patches
5. ❌ **Never run presentations** with untrusted config files without review

### For Developers

1. ✅ **Validate all user inputs**
2. ✅ **Use whitelists** instead of blacklists
3. ✅ **Prefer data formats** over code execution
4. ✅ **Keep dependencies updated**
5. ✅ **Use type hints** for better validation

## Vulnerability Disclosure

If you discover a security vulnerability in Revelation:

1. **Do NOT** open a public issue
2. Email security details to: humrochagf@gmail.com
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (optional)

We will respond within 48 hours and work on a fix.

## Security Checklist

Before running a presentation:

- [ ] Using TOML config format (or trusted Python config)
- [ ] Config file reviewed for suspicious content
- [ ] Presentation files from trusted source
- [ ] Revelation and dependencies up to date
- [ ] Running on latest Python version (3.10+)

## Version History

### v0.2.0 (Current)
- ✅ Added TOML configuration support
- ✅ Added path traversal protection
- ✅ Updated all critical dependencies
- ✅ Added automatic conversion utility
- ✅ Sandboxed Python config execution
- ✅ Added comprehensive validation

### v0.1.0 (Previous)
- ❌ Vulnerable `exec()` in config loading
- ❌ No path validation
- ❌ Outdated dependencies with CVEs
- ❌ No input validation

## Additional Resources

- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - How to migrate to TOML
- [CLAUDE.md](CLAUDE.md) - Development guidelines
- [README.md](README.md) - Usage documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Web security risks

## Credits

Security improvements implemented by Claude Code based on security audit findings.

## License

MIT License - See LICENSE file for details
