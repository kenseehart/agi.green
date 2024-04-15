from .dict_namespace import DictNamespace, hash_mutable
import yaml
import os
import shutil
import asyncio
import aiofiles
import yaml
import weakref

async def load_yaml(file_path) -> dict:
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
    try:
        r = yaml.safe_load(content)
    except:
        r = None
    return r

async def save_yaml(file_path, data:dict):
    async with aiofiles.open(file_path, 'w') as f:
        yaml_str = yaml.safe_dump(data)
        await f.write(yaml_str)

def multiline_str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    'because we like pretty multiline strings in our yaml config files'
    if isinstance(data, str) and '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, multiline_str_representer)

class ConfigNamespace(DictNamespace):
    'Configuration namespace asynchonously mirrored to yaml'
    def __init__(self, filepath:str, default_filepath:str=None, depth=0, delay:float=0.1, writeable=False, **kwargs):
        '''filepath: path to yaml file or env var if prefixed with $
        default_filepath: path to copy to filepath if it doesn't exist
        delay: time to wait between checking for changes to the yaml file
        '''
        super().__init__(depth, **kwargs)
        self._filepath = os.path.expandvars(filepath)
        self._delay = delay
        self._writeable = writeable

        if not os.path.exists(self._filepath):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self._filepath), exist_ok=True)

            # Copy from default if actual config doesn't exist
            if default_filepath:
                shutil.copy(default_filepath, self._filepath)
            else:
                # Create empty file if no default
                with open(self._filepath, 'w') as f:
                    f.write('{}')

        self._yaml_timestamp = 0 # last time the yaml file was read or written
        self._changed('yaml') # clear the change flag
        asyncio.create_task(self._sync_yaml_loop())

    def _yaml_changed(self):
        'return True if the yaml file has changed since last read'
        r = self._yaml_timestamp < os.path.getmtime(self._filepath)
        self._yaml_timestamp = os.path.getmtime(self._filepath)
        return r

    async def _sync_yaml(self):
        'sync yaml file to data and data to yaml file if changed. You may need to await this manually if you want to force a sync.'
        data_changed = self._writeable and self._changed('yaml')
        file_changed = self._yaml_changed()

        if file_changed:
            data = await load_yaml(self._filepath)
            if data is not None:
                if self == {}:
                    data_changed = False
                    self.clear()

                self._deep_update(data) # _deep_update ensures that DictNamespace objects are applied to depth

                self._changed('yaml') # clear the change

        if data_changed:
            await save_yaml(self._filepath, self)

    async def _sync_yaml_loop(self):
        'sync data to yaml file forever'
        self._ensure_finalization() # ensure task ends when we are garbage collected

        while not self._dead:
            await self._sync_yaml()
            await asyncio.sleep(self._delay)




