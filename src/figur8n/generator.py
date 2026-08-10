"""
Code generator for figur8n settings - Schema-first approach.

Generates Python classes with properties and clean defaults JSON from JSON Schema files.
"""

import json
from pathlib import Path
from typing import Any

# JSON Schema type to Python type mapping
TYPE_MAP = {
    'integer': 'int',
    'number': 'float',
    'string': 'str',
    'boolean': 'bool',
}


# Template for property getter
PROPERTY_GETTER_TEMPLATE = '''
    @property
    def {name}(self) -> {type}:
        """
        {docstring}
        """
        return self._get_value('{name}')
'''

# Template for property setter
PROPERTY_SETTER_TEMPLATE = """
    @{name}.setter
    def {name}(self, value: {type}) -> None:
        self._set_value('{name}', value)
"""

# Template for complete class file
CLASS_FILE_TEMPLATE = '''# Auto-generated from {config_name}.schema.json - DO NOT EDIT
# To regenerate: python -m figur8n generate {defaults_dir}/{config_name}.schema.json

from figur8n import Settings


class {class_name}(Settings):
    """
    {class_doc}
    """
{properties}
{constraints}
    def __init__(self, user_config_dir=None):
        super().__init__(
            '{config_name}',
            defaults_dir=r'{defaults_dir}',
            user_config_dir=user_config_dir
        )
'''

# Template for constraints dict
CONSTRAINTS_TEMPLATE = """
    _constraints = {{
{constraints_entries}
    }}
"""


def parse_json_schema(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Parse JSON Schema into normalized field information.

    Args:
        schema: JSON Schema dict

    Returns:
        Dict mapping field names to field info:
        {
            "fps": {
                "type": "float",
                "default": 15.0,
                "description": "Frames per second",
                "constraints": {"min": 1.0, "max": 60.0},  # optional
                "readOnly": False  # optional
            }
        }
    """
    properties = schema.get('properties', {})
    fields = {}

    for name, prop in properties.items():
        # Get JSON Schema type
        json_type = prop.get('type')
        py_type = TYPE_MAP.get(json_type)

        # Skip unsupported types (array, object, etc.)
        if py_type not in ('int', 'float', 'str', 'bool'):
            print(f"Warning: Skipping '{name}': type '{json_type}' not supported (primitives only)")
            continue

        # Build field info
        field = {
            'type': py_type,
            'default': prop.get('default'),
            'description': prop.get('description', ''),
            'readOnly': prop.get('readOnly', False),
        }

        # Validate default exists
        if field['default'] is None:
            print(f"Warning: Skipping '{name}': no default value specified")
            continue

        # Extract constraints (minimum/maximum)
        if 'minimum' in prop or 'maximum' in prop:
            field['constraints'] = {}
            if 'minimum' in prop:
                field['constraints']['min'] = prop['minimum']
            if 'maximum' in prop:
                field['constraints']['max'] = prop['maximum']

        fields[name] = field

    return fields


def build_docstring(field: dict[str, Any]) -> str:
    """
    Build docstring from field information.

    Args:
        field: Field info dict

    Returns:
        Formatted docstring content
    """
    doc_lines = []

    if field['description']:
        doc_lines.append(field['description'])

    # Add constraint info
    if 'constraints' in field:
        c = field['constraints']
        if 'min' in c and 'max' in c:
            doc_lines.append(f'Range: {c["min"]} - {c["max"]}')
        elif 'min' in c:
            doc_lines.append(f'Minimum: {c["min"]}')
        elif 'max' in c:
            doc_lines.append(f'Maximum: {c["max"]}')

    doc_lines.append(f'Default: {field["default"]}')

    return '\n        '.join(doc_lines)


def generate_property(name: str, field: dict[str, Any]) -> str:
    """
    Generate a Python property with getter, optional setter, and docstring.

    Args:
        name: Property name
        field: Field info dict

    Returns:
        Python property code
    """
    docstring = build_docstring(field)

    # Generate getter
    code = PROPERTY_GETTER_TEMPLATE.format(name=name, type=field['type'], docstring=docstring)

    # Add setter only if not readOnly
    if not field.get('readOnly'):
        code += PROPERTY_SETTER_TEMPLATE.format(name=name, type=field['type'])

    return code


def build_constraints_code(fields: dict[str, dict[str, Any]]) -> str:
    """
    Build constraints dict code if any fields have constraints.

    Args:
        fields: Parsed field information

    Returns:
        Constraints dict code or empty string
    """
    has_constraints = any('constraints' in f for f in fields.values())
    if not has_constraints:
        return ''

    # Build constraint entries
    entries = []
    for field_name, field_info in fields.items():
        if 'constraints' in field_info:
            entries.append(f"        '{field_name}': {field_info['constraints']}")

    constraints_entries = ',\n'.join(entries)
    return CONSTRAINTS_TEMPLATE.format(constraints_entries=constraints_entries)


def generate_class_code(
    class_name: str,
    config_name: str,
    fields: dict[str, dict[str, Any]],
    defaults_dir: str,
    schema_title: str = '',
) -> str:
    """
    Generate complete Python class code with properties.

    Args:
        class_name: Class name (e.g., VideoSettings)
        config_name: Config name for file loading (e.g., video)
        fields: Parsed field information
        defaults_dir: Path to defaults directory
        schema_title: Optional schema title for class docstring

    Returns:
        Complete Python class code
    """
    # Generate all properties
    properties = ''.join(generate_property(name, info) for name, info in fields.items())

    # Generate constraints dict if needed
    constraints = build_constraints_code(fields)

    # Build class docstring
    class_doc = schema_title if schema_title else f'Auto-generated settings class for {config_name}.'

    # Build complete class using template
    return CLASS_FILE_TEMPLATE.format(
        config_name=config_name,
        defaults_dir=defaults_dir,
        class_name=class_name,
        class_doc=class_doc,
        properties=properties,
        constraints=constraints,
    )


def generate_defaults_json(fields: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Extract clean defaults JSON from field information.

    Args:
        fields: Parsed field information

    Returns:
        Dict of default values (clean JSON, no metadata)
    """
    return {name: field['default'] for name, field in fields.items()}


def generate(
    schema_path: Path,
    output_path: Path | None = None,
    class_name: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Generate Python class and defaults JSON from a JSON Schema file.

    Args:
        schema_path: Path to the JSON Schema file
        output_path: Optional path for generated .py file
        class_name: Optional name for generated class

    Returns:
        Tuple of (generated_code, defaults_dict)
    """
    # Read JSON Schema
    with open(schema_path, encoding='utf-8') as f:
        schema = json.load(f)

    # Parse schema
    fields = parse_json_schema(schema)

    if not fields:
        raise ValueError('No valid fields found in schema (primitives only: int, float, str, bool)')

    # Determine names and paths
    config_name = schema_path.stem.replace('.schema', '')
    if class_name is None:
        # Convert snake_case to PascalCase
        class_name = ''.join(word.capitalize() for word in config_name.split('_'))
        if not class_name.endswith('Settings'):
            class_name += 'Settings'

    if output_path is None:
        # Put generated file next to schema (remove .schema from name)
        output_path = schema_path.parent / f'{config_name}_settings.py'

    # Use absolute path for defaults_dir
    defaults_dir = str(schema_path.parent.absolute())

    # Get schema title for docstring
    schema_title = schema.get('title', schema.get('description', ''))

    # Generate Python class
    code = generate_class_code(class_name, config_name, fields, defaults_dir, schema_title)

    # Write Python file
    output_path.write_text(code)

    # Generate and write clean defaults JSON
    defaults_dict = generate_defaults_json(fields)
    defaults_json_path = schema_path.parent / f'{config_name}.json'
    with open(defaults_json_path, 'w', encoding='utf-8') as f:
        json.dump(defaults_dict, f, indent=2, sort_keys=True)

    print(f'Generated defaults: {defaults_json_path}')

    return code, defaults_dict
