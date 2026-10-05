#!/usr/bin/env python3
"""Standalone smoke-test script for config conversion. À lancer depuis la
racine du dépôt : uv run --no-project scripts/test_conversion.py"""

import sys
from pathlib import Path

# Racine du dépôt (scripts/ est un niveau sous la racine) : pour importer revelation
RACINE = Path(__file__).parent.parent
sys.path.insert(0, str(RACINE))

from revelation.convert_config import convert_config

if __name__ == '__main__':
    python_file = RACINE / 'example_slides/config.py'
    output_file = RACINE / 'example_slides/config_test.toml'

    print(f"Converting {python_file} to {output_file}...")

    if convert_config(python_file, output_file, force=True):
        print("\n✓ Conversion successful!")
        print("\nGenerated TOML content:")
        print("=" * 60)
        print(output_file.read_text())
        print("=" * 60)
    else:
        print("\n✗ Conversion failed")
        sys.exit(1)
