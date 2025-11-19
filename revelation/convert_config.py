"""Utility to convert Python config files to TOML format"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def python_value_to_toml(value: Any, indent: int = 0) -> str:
    """
    Convert Python value to TOML representation

    Args:
        value: Python value to convert
        indent: Indentation level for nested structures

    Returns:
        TOML-formatted string
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Escape quotes and backslashes
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    elif value is None:
        return '""'
    elif isinstance(value, dict):
        # This shouldn't happen in direct conversion
        # Dicts should be handled as tables
        return "{}"
    elif isinstance(value, (list, tuple)):
        items = [python_value_to_toml(item) for item in value]
        return f"[{', '.join(items)}]"
    else:
        # Fallback for unknown types
        return f'"{str(value)}"'


def extract_config_from_python(python_file: Path) -> Dict[str, Any]:
    """
    Parse Python config file and extract configuration values

    Args:
        python_file: Path to Python config file

    Returns:
        Dictionary of configuration values

    Raises:
        SyntaxError: If Python file has syntax errors
        ValueError: If file contains invalid constructs
    """
    content = python_file.read_text(encoding='utf-8')

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        raise SyntaxError(f"Invalid Python syntax in {python_file}: {e}")

    config = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            # Handle simple assignments like: REVEAL_THEME = "black"
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    key = target.id
                    try:
                        value = ast.literal_eval(node.value)
                        config[key] = value
                    except (ValueError, TypeError):
                        print(
                            f"Warning: Could not evaluate value for {key}, skipping",
                            file=sys.stderr
                        )

    return config


def config_to_toml(config: Dict[str, Any]) -> str:
    """
    Convert configuration dictionary to TOML format

    Args:
        config: Configuration dictionary

    Returns:
        TOML-formatted string
    """
    lines = []
    lines.append("# Revelation presentation configuration")
    lines.append("# Converted from Python config format")
    lines.append("")

    # Separate simple values from dict values
    simple_values = {}
    dict_values = {}

    for key, value in config.items():
        if isinstance(value, dict):
            dict_values[key] = value
        else:
            simple_values[key] = value

    # Write metadata section first if present
    if 'REVEAL_META' in dict_values:
        lines.append("# Presentation metadata")
        lines.append("[reveal_meta]")
        for k, v in dict_values['REVEAL_META'].items():
            lines.append(f"{k} = {python_value_to_toml(v)}")
        lines.append("")
        del dict_values['REVEAL_META']

    # Write simple configuration values
    if simple_values:
        lines.append("# Basic configuration")
        for key, value in sorted(simple_values.items()):
            toml_key = key.lower()
            toml_value = python_value_to_toml(value)
            lines.append(f"{toml_key} = {toml_value}")
        lines.append("")

    # Write reveal_config section if present
    if 'REVEAL_CONFIG' in dict_values:
        lines.append("# Reveal.js configuration options")
        lines.append("[reveal_config]")

        config_dict = dict_values['REVEAL_CONFIG']
        # Group related options with comments
        display_keys = ['controls', 'progress', 'slideNumber', 'center']
        nav_keys = ['history', 'keyboard', 'overview', 'touch', 'mouseWheel']
        transition_keys = ['transition', 'transitionSpeed', 'backgroundTransition']
        advanced_keys = ['loop', 'rtl', 'fragments', 'embedded', 'help', 'showNotes',
                        'autoSlide', 'autoSlideStoppable', 'hideAddressBar', 'previewLinks',
                        'viewDistance']

        def write_group(keys, title):
            found = False
            for k in keys:
                if k in config_dict:
                    if not found and title:
                        lines.append(f"\n# {title}")
                        found = True
                    v = config_dict[k]
                    lines.append(f"{k} = {python_value_to_toml(v)}")

        # Handle width/height first
        if 'width' in config_dict or 'height' in config_dict:
            lines.append("\n# Presentation size")
            if 'width' in config_dict:
                lines.append(f"width = {config_dict['width']}")
            if 'height' in config_dict:
                lines.append(f"height = {config_dict['height']}")

        write_group(display_keys, "Display options")
        write_group(nav_keys, "Navigation")
        write_group(transition_keys, "Transitions")

        # Parallax options
        parallax_keys = [k for k in config_dict if k.startswith('parallax')]
        if parallax_keys:
            lines.append("\n# Parallax background")
            for k in parallax_keys:
                lines.append(f"{k} = {python_value_to_toml(config_dict[k])}")

        # Write any remaining keys
        written_keys = (
            display_keys + nav_keys + transition_keys + parallax_keys +
            ['width', 'height']
        )
        remaining = {k: v for k, v in config_dict.items() if k not in written_keys}
        if remaining:
            lines.append("\n# Other options")
            for k, v in sorted(remaining.items()):
                lines.append(f"{k} = {python_value_to_toml(v)}")

        lines.append("")
        del dict_values['REVEAL_CONFIG']

    # Write any other dict sections
    for key, value in dict_values.items():
        if isinstance(value, dict):
            lines.append(f"[{key.lower()}]")
            for k, v in value.items():
                lines.append(f"{k} = {python_value_to_toml(v)}")
            lines.append("")

    return "\n".join(lines)


def convert_config(
    python_file: Path,
    output_file: Optional[Path] = None,
    force: bool = False
) -> bool:
    """
    Convert Python config file to TOML format

    Args:
        python_file: Path to Python config file
        output_file: Path to output TOML file (default: same name with .toml)
        force: Overwrite existing output file

    Returns:
        True if conversion successful, False otherwise
    """
    if not python_file.exists():
        print(f"Error: File not found: {python_file}", file=sys.stderr)
        return False

    if not python_file.suffix == '.py':
        print(f"Warning: File does not have .py extension: {python_file}", file=sys.stderr)

    # Determine output file
    if output_file is None:
        output_file = python_file.with_suffix('.toml')

    if output_file.exists() and not force:
        print(f"Error: Output file already exists: {output_file}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        return False

    try:
        # Parse Python config
        print(f"Reading {python_file}...")
        config = extract_config_from_python(python_file)

        if not config:
            print("Warning: No configuration found in Python file", file=sys.stderr)
            return False

        print(f"Found {len(config)} configuration values")

        # Convert to TOML
        toml_content = config_to_toml(config)

        # Write output
        print(f"Writing {output_file}...")
        output_file.write_text(toml_content, encoding='utf-8')

        print(f"\n✓ Successfully converted to {output_file}")
        print(f"\nNext steps:")
        print(f"1. Review the generated TOML file")
        print(f"2. Test with: revelation start /path/to/presentation --config {output_file.name}")
        print(f"3. Once verified, you can remove {python_file.name}")

        return True

    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main():
    """CLI entry point for config conversion"""
    parser = argparse.ArgumentParser(
        description="Convert Revelation Python config files to secure TOML format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert config.py to config.toml
  python -m revelation.convert_config config.py

  # Specify output file
  python -m revelation.convert_config config.py -o my_config.toml

  # Overwrite existing file
  python -m revelation.convert_config config.py --force

For more information, see MIGRATION_GUIDE.md
        """
    )

    parser.add_argument(
        'python_file',
        type=Path,
        help='Python config file to convert'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output TOML file (default: same name with .toml extension)'
    )

    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Overwrite output file if it exists'
    )

    args = parser.parse_args()

    success = convert_config(args.python_file, args.output, args.force)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
