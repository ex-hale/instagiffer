"""
CLI tool for figur8n code generation.

Usage:
    python -m figur8n generate <schema.json>
    python -m figur8n generate <schema.json> --output <output.py>
    python -m figur8n generate <schema.json> --class-name MySettings
"""

import argparse
import sys
from pathlib import Path

from figur8n.generator import generate


def main():
    parser = argparse.ArgumentParser(
        prog='figur8n',
        description='figur8n settings code generator'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Generate command
    gen_parser = subparsers.add_parser(
        'generate',
        help='Generate Python settings class from JSON Schema'
    )
    gen_parser.add_argument(
        'schema',
        type=Path,
        help='Path to JSON Schema file (e.g., defaults/video.schema.json)'
    )
    gen_parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output Python file path (default: <schema>_settings.py)'
    )
    gen_parser.add_argument(
        '-c', '--class-name',
        type=str,
        help='Class name for generated settings (default: derived from filename)'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == 'generate':
        schema_path = args.schema

        if not schema_path.exists():
            print(f'Error: Schema file not found: {schema_path}', file=sys.stderr)
            return 1

        if not schema_path.suffix == '.json':
            print(f'Error: Schema file must be a .json file: {schema_path}', file=sys.stderr)
            return 1

        try:
            code, defaults_dict = generate(
                schema_path,
                output_path=args.output,
                class_name=args.class_name,
            )

            config_name = schema_path.stem.replace('.schema', '')
            output_path = args.output or schema_path.parent / f'{config_name}_settings.py'
            defaults_path = schema_path.parent / f'{config_name}.json'

            print(f'Generated Python class: {output_path}')
            print(f'Generated defaults JSON: {defaults_path}')

            return 0

        except Exception as e:
            print(f'Error generating code: {e}', file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
