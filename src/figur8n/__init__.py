"""
figur8n - data-first configuration with auto-save and hot-reload.

Features:
- Data-first: define settings in JSON, generate Python classes
- Direct attribute access with IDE autocomplete
- Auto-saves on change
- Auto-deletes user config when back to defaults
- Hot-reloads if file changes externally
- Type validation and optional constraints (min/max)
- Layered config (defaults -> user -> workspace)

Usage (Data-first - recommended):
    # 1. Create defaults/my_config.json:
    #    {"port": 8080, "debug": false}
    #
    # 2. Generate Python class:
    #    python -m figur8n generate defaults/my_config.json
    #
    # 3. Use with autocomplete:
    #    from my_config_settings import MyConfigSettings
    #    config = MyConfigSettings()
    #    config.port = 3000  # Auto-saves with validation!

Usage (Code-first - for simple cases):
    from figur8n import Settings

    class MyConfig(Settings):
        def __init__(self):
            super().__init__('my_config')
            self.port: int = None
            self.debug: bool = None

    config = MyConfig()
    config.port = 8080  # Auto-saves!
"""

__version__ = '0.1.0'
__author__ = 'Eric Werner'

from .base import Settings

__all__ = ['Settings', '__version__']
