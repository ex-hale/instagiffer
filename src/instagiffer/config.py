import figur8n


class Config(figur8n.Settings):
    """General Instagiffer Configuration."""
    last_source_directory: str
    """Last directory the user was getting source data from."""


class UiSettings(figur8n.Settings):
    win_width: int
    win_height: int
    win_maximized: int
    win_x: int
    win_y: int
    splitter_size: int
