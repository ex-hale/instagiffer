"""
figur8n - configuration with auto-save and hot-reload.
"""
import json
import os
import typing
from pathlib import Path


class Settings:
    """
    figur8n main Settings class.
    - Auto-saves when you change a value
    - Auto-deletes user config when value returns to default
    - Hot-reloads if file changes externally
    - Simple attribute access

    Usage:
        class MyConfig(Settings):
            def __init__(self):
                super().__init__('my_config')
                self.port: int = None
                self.debug: bool = None

        config = MyConfig()
        config.port = 8080  # Auto-saves!
        config.port = 3000  # Original default -> auto-deletes user config!
    """

    _builtins: typing.ClassVar[tuple[str, ...]] = ()
    _initialized = False

    def __init__(
        self,
        name: str | None,
        defaults_dir: Path | str | None = None,
        user_config_dir: Path | str | None = None,
    ):
        """
        Initialize settings.

        Args:
            name: Config name (e.g., 'general', 'navigation')
            defaults_dir: Directory containing {name}.json defaults
            user_config_dir: Directory for user config files
        """
        self._name = name if name is not None else self.__class__.__name__.lower()

        self._defaults: dict[str, typing.Any] = {}
        self._defaults_dir = Path(defaults_dir) if defaults_dir else self._get_defaults_dir()
        self._user_config_dir = (
            Path(user_config_dir) if user_config_dir else self._get_user_config_dir()
        )

        # Load defaults from JSON
        defaults_path = self._defaults_dir / f'{self._name}.json'
        if not defaults_path.is_file():
            raise FileNotFoundError(
                f'Defaults file not found: {defaults_path}\n'
                f'Create {defaults_path} with your default settings.'
            )

        with open(defaults_path, encoding='utf-8') as f:
            raw_defaults = json.load(f)

        # Parse extended format: {"key": {"default": value, ...}} -> {"key": value}
        for key, value in raw_defaults.items():
            if isinstance(value, dict) and 'default' in value:
                # Extended format - extract just the default value
                self._defaults[key] = value['default']
            else:
                # Simple format - use value as-is
                self._defaults[key] = value

        # User config
        self._user_config_path = self._user_config_dir / f'{self._name}.json'
        self._user_data: dict[str, typing.Any] = {}
        self._user_file_time: float = 0

        # Track builtin attributes (everything before user attributes)
        if not Settings._builtins:
            Settings._builtins = tuple(list(self.__dict__)[:7] + list(Settings.__dict__))

        # Load user data
        self._load_user_data()
        self._initialized = True

    def _get_defaults_dir(self) -> Path:
        """Get default directory for defaults - override in subclass if needed."""
        # By default, look for 'defaults' folder next to the module
        if self._defaults_dir is not None:
            return self._defaults_dir

        import inspect

        module = inspect.getmodule(inspect.stack()[2][0])
        if module and module.__file__:
            return Path(module.__file__).parent / 'defaults'
        return Path.cwd() / 'defaults'

    @staticmethod
    def _get_user_config_dir() -> Path:
        """Get platform-appropriate user config directory."""
        if os.name == 'nt':
            # Windows: %LOCALAPPDATA%
            base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        else:
            # Unix: ~/.config
            base = Path.home() / '.config'

        # Use calling module's name as subdirectory
        import inspect

        module = inspect.getmodule(inspect.stack()[2][0])
        if module and hasattr(module, '__name__'):
            app_name = module.__name__.split('.')[0]
        else:
            app_name = 'figur8n_app'

        config_dir = base / app_name
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _has_user_config(self) -> bool:
        """Check if user config file exists."""
        return self._user_config_path.is_file()

    def _load_user_data(self) -> None:
        """Load user configuration from file."""
        if not self._has_user_config():
            return

        with open(self._user_config_path, encoding='utf-8') as f:
            self._user_data.clear()
            self._user_data.update(json.load(f))

        super().__setattr__('_user_file_time', self._get_user_file_time())

    def _get_user_file_time(self) -> float:
        """Get modification time of user config file."""
        if self._has_user_config():
            return os.path.getmtime(self._user_config_path)
        return 0

    def _save_user_data(self) -> None:
        """Save user configuration to file."""
        if not self._user_data:
            # No user data - delete file if it exists
            if self._has_user_config():
                self._user_config_path.unlink()
            return

        # Ensure directory exists
        self._user_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Save with nice formatting
        with open(self._user_config_path, 'w', encoding='utf-8') as f:
            json.dump(self._user_data, f, indent=2, sort_keys=True)

        super().__setattr__('_user_file_time', self._get_user_file_time())

    def __getattribute__(self, name: str) -> typing.Any:
        """
        Magic attribute getter with hot-reload.

        - Returns user value if set
        - Otherwise returns default
        - Reloads from file if changed externally
        """
        try:
            member = super().__getattribute__(name)
        except AttributeError:
            member = None

        if name == '_defaults' or self._defaults is None or name not in self._defaults:
            return member

        if self._user_file_time < self._get_user_file_time():
            self._load_user_data()

        if name in self._user_data:
            member = self._user_data[name]
        elif member is None:
            member = self._defaults[name]

        super().__setattr__(name, member)
        return member

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """
        Set attributes with auto-save and validation.

        - Validates type matches default
        - Checks constraints (min/max) if defined
        - If value == default: removes from user data
        - If user data becomes empty: deletes user config file
        - Otherwise: saves to user config
        """
        # Internal attributes
        if not self._initialized:
            super().__setattr__(name, value)
            return

        # Check if this is a settings attribute
        if name not in self._defaults:
            raise AttributeError(f'Unable to set "{name}"! No such attribute!!')

        # Type validation
        default_value = self._defaults[name]
        expected_type = type(default_value)
        if not isinstance(value, expected_type):
            raise TypeError(f'{name} expects {expected_type.__name__}, got {type(value).__name__}')

        self._validate(name, value)

        # Check if value equals default
        if value == default_value:
            # Remove from user data
            if name in self._user_data:
                del self._user_data[name]
            self._save_user_data()
        else:
            # Update user data
            self._user_data[name] = value
            self._save_user_data()

        # Update cached value
        super().__setattr__(name, value)

    def _get_value(self, name: str) -> typing.Any:
        """
        Get setting value with hot-reload check.
        Used by generated property getters.

        Args:
            name: Setting name

        Returns:
            Current value (from user data or defaults)
        """
        # Check for external file changes (hot reload)
        if self._user_file_time < self._get_user_file_time():
            self._load_user_data()

        # Return user value if set, otherwise default
        if name in self._user_data:
            return self._user_data[name]
        return self._defaults[name]

    def _set_value(self, name: str, value: typing.Any) -> None:
        """
        Set setting value with validation and auto-save.
        Used by generated property setters.

        Args:
            name: Setting name
            value: New value to set
        """
        # Type validation
        default_value = self._defaults[name]
        expected_type = type(default_value)
        if not isinstance(value, expected_type):
            raise TypeError(f'{name} expects {expected_type.__name__}, got {type(value).__name__}')

        self._validate(name, value)

        # Check if value equals default
        if value == default_value:
            # Remove from user data
            if name in self._user_data:
                del self._user_data[name]
            self._save_user_data()
        else:
            # Update user data
            self._user_data[name] = value
            self._save_user_data()

    def reset(self) -> None:
        """Reset all settings to defaults (deletes user config)."""
        self._user_data.clear()
        self._save_user_data()

        # Reset cached values
        for key in self._defaults:
            if hasattr(self, key):
                super().__setattr__(key, self._defaults[key])

    def get_user_overrides(self) -> dict[str, typing.Any]:
        """Get dictionary of user's custom settings."""
        return self._user_data.copy()

    def has_user_overrides(self) -> bool:
        """Check if user has any custom settings."""
        return bool(self._user_data)

    def _validate(self, name: str, value: int | float):
        """Constraint validation (if _constraints defined)."""
        if not hasattr(self.__class__, '_constraints'):
            return

        if not isinstance(self.__class__._constraints, dict):
            return

        if name not in self.__class__._constraints:
            return

        constraints = self.__class__._constraints[name]
        if not isinstance(constraints, dict):
            return

        if 'min' in constraints and value < constraints['min']:
            raise ValueError(f'{name} must be >= {constraints["min"]}, got {value}')
        if 'max' in constraints and value > constraints['max']:
            raise ValueError(f'{name} must be <= {constraints["max"]}, got {value}')

    def __iter__(self) -> typing.Iterator[str]:
        yield from self._defaults

    def __repr__(self) -> str:
        """String representation showing current values."""
        attrs = {k: getattr(self, k) for k in self._defaults or ()}
        return f'{self.__class__.__name__}({attrs})'
