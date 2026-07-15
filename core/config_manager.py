# core/config_manager.py
"""Centralized configuration manager for Dat Dai Desktop App."""
import json
import os
import sys

# Support PyInstaller frozen bundles
if getattr(sys, 'frozen', False):
    _APP_DIR = sys._MEIPASS
    _USER_DIR = os.path.join(os.path.expanduser("~"), ".dat_dai_desktop")
else:
    _APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _USER_DIR = _APP_DIR

os.makedirs(_USER_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(_USER_DIR, "config.json")

_DEFAULTS = {
    "gemini_api_key": "",
    "mistral_api_key": "",
    "ocr_mode": "gemini",        # "gemini" | "mistral" | "lmstudio"
    "lmstudio_url": "http://localhost:1234",
    "lmstudio_model": "local-model",
    "output_dir": os.path.join(_USER_DIR, "data", "output"),
    "db_path": os.path.join(_USER_DIR, "data", "dat_dai.db"),
    "app_theme": "dark",
    "app_language": "vi",
    "last_open_dir": "",
}

_config: dict = {}

def load():
    global _config
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _config = {**_DEFAULTS, **json.load(f)}
        except Exception:
            _config = dict(_DEFAULTS)
    else:
        _config = dict(_DEFAULTS)

    for key in ("output_dir", "db_path"):
        if not os.path.isabs(_config[key]):
            _config[key] = os.path.join(_USER_DIR, _config[key])

    os.makedirs(_config["output_dir"], exist_ok=True)
    os.makedirs(os.path.dirname(_config["db_path"]), exist_ok=True)

def get(key: str, default=None):
    if not _config:
        load()
    return _config.get(key, default)

def set(key: str, value):
    if not _config:
        load()
    _config[key] = value

def save():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_config, f, ensure_ascii=False, indent=2)

# Auto-load on import
load()
