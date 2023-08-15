import os
import shutil
from typing import Any, Dict
import yaml

class Config():
    '''
    Access a configuration as a YAML file backed by a default config.

    Typically, you would git ignore the actual config file, and commit the default config.
    '''
    filepath: str
    default_filepath: str
    cached_data: str
    last_modified: float

    def __init__(self, filepath: str, default_filepath: str, **kwargs):
        super().__init__(**kwargs)
        self.filepath = filepath
        self.default_filepath = default_filepath
        self.cached_data = None
        self.last_modified = 0

        # Copy from default if actual config doesn't exist
        if not os.path.exists(self.filepath):
            shutil.copy(self.default_filepath, self.filepath)

    def merge_configs(self, default: Dict[str, Any], actual: Dict[str, Any]):
        merged = default.copy()
        for key, value in actual.items():
            if key in merged and isinstance(merged[key], dict):
                merged[key] = self.merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged

    def load_config(self):
        # If the default config is newer, merge them
        default_timestamp = os.path.getmtime(self.default_filepath)
        if default_timestamp > self.last_modified or self.cached_data is None:
            with open(self.default_filepath, 'r') as f:
                default_config = yaml.safe_load(f.read()) or {}

            with open(self.filepath, 'r') as f:
                actual_config = yaml.safe_load(f.read()) or {}

            config = self.merge_configs(default_config, actual_config)

            self.cached_data = yaml.dump(config)
            self.last_modified = os.path.getmtime(self.filepath)

        else:
            config = yaml.safe_load(self.cached_data) or {}

        return config

    def save_config(self, config: Dict[str, Any]):
        with open(self.filepath, 'w') as f:
            yaml_data = yaml.dump(config)
            f.write(yaml_data)
            self.cached_data = yaml_data
            self.last_modified = os.path.getmtime(self.filepath)

    def get(self, key: str):
        'get config value'
        config = self.load_config()
        keys = key.split('.')
        value = config
        for k in keys:
            value = value[k]
        return value

    def set(self, key: str, value: Any):
        'set config value'
        config = self.load_config()
        keys = key.split('.')
        d = config
        for k in keys[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self.save_config(config)

    def delete(self, key: str):
        'delete config value'
        config = self.load_config()
        keys = key.split('.')
        d = config
        for k in keys[:-1]:
            if k not in d:
                return  # If any part of the key is not present, return
            d = d[k]
        if keys[-1] in d:
            del d[keys[-1]]
            self.save_config(config)

