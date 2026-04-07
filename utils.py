"""
Utility functions
"""

import os
from typing import Dict, Any, Optional

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    if not os.path.exists(config_path):
        return get_default_config()

    if HAS_RUAMEL:
        yaml = YAML()
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f)
            # Convert CommentedMap to dict
            return dict(config) if config else get_default_config()
    else:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            try:
                return yaml.safe_load(f) or get_default_config()
            except Exception:
                return get_default_config()


def save_config(config: Dict[str, Any], config_path: str = "config.yaml") -> None:
    """
    Save configuration to YAML file (preserves comments if ruamel.yaml is available)

    Args:
        config: Configuration dictionary
        config_path: Path to config file
    """
    if HAS_RUAMEL:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.load(f)

            if isinstance(existing_data, CommentedMap):
                for key, value in config.items():
                    existing_data[key] = value
                data_to_save = existing_data
            else:
                data_to_save = CommentedMap()
                for key, value in config.items():
                    data_to_save[key] = value
        else:
            data_to_save = CommentedMap()
            for key, value in config.items():
                data_to_save[key] = value

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data_to_save, f)
    else:
        import yaml
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_default_config() -> Dict[str, Any]:
    """Get default configuration"""
    return {
        "llm": {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "",
            "base_url": "",
            "temperature": 0.3,
            "max_tokens": 4096,
            "timeout": 300.0
        },
        "llm_presets": [],
        "proofreading": {
            "mode": "comments",
            "chunk_mode": "paragraph",
            "chunk_size": 500,
            "chunk_overlap": 50,
            "batch_size": 5,
            "preserve_formatting": True,
            "cn_font": "宋体",
            "en_font": "Times New Roman"
        },
        "prompt": {
            "system": "你是一位专业的中文编辑，负责文档校对和润色。",
            "detail_level": "standard"
        },
        "ui": {
            "title": "AI 文档智能审校系统",
            "page_width": "wide",
            "cache_ttl": 3600
        }
    }


def format_number(num: int) -> str:
    """Format large numbers with commas"""
    return "{:,}".format(num)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_filename(filename: str) -> str:
    """
    Sanitize filename for safe filesystem usage

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    invalid_chars = '<>:"/\\|?*\x00-\x1f'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext

    return filename


def get_prompts_config(prompts_path: str = "prompts.json") -> Dict[str, Any]:
    """
    Load custom prompts configuration from JSON file

    Args:
        prompts_path: Path to prompts config file

    Returns:
        Prompts configuration dictionary (empty dict if file doesn't exist)
    """
    import json
    if not os.path.exists(prompts_path):
        # Fallback to check yaml if json doesn't exist, just in case
        if os.path.exists("prompts.yaml"):
            prompts_path = "prompts.yaml"
        else:
            return {}

    if prompts_path.endswith('.json'):
        with open(prompts_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    
    if HAS_RUAMEL:
        yaml = YAML()
        with open(prompts_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f)
            return dict(config) if config else {}
    else:
        import yaml
        with open(prompts_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}


def reset_prompts_config(prompts_path: str = "prompts.json") -> None:
    """
    Remove custom prompts configuration file

    Args:
        prompts_path: Path to prompts config file
    """
    if os.path.exists(prompts_path):
        os.remove(prompts_path)
    if os.path.exists("prompts.yaml"):
        os.remove("prompts.yaml")
