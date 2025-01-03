import os
from pathlib import Path
import asyncio
import logging
from typing import Dict, Union, Set
from watchfiles import awatch
from agi_green.dispatcher import Protocol

logger = logging.getLogger(__name__)

class FileProtocol(Protocol):
    """Protocol for monitoring file changes"""
    protocol_id: str = 'file'

    def __init__(self, parent: Protocol):
        super().__init__(parent)
        self.monitored_paths: Dict[str, Set[str]] = {}
        self.watch_tasks: Dict[str, asyncio.Task] = {}

    def _normalize_path(self, path: Union[str, Path]) -> Path:
        """Convert string or Path to normalized Path"""
        return Path(path).resolve()

    async def _watch_directory(self, dir_path: str):
        """Watch a directory for changes"""
        try:
            async for changes in awatch(dir_path):
                for _, path_str in changes:
                    path_str = str(Path(path_str).resolve())
                    # Check all channels for matching paths
                    for channel, paths in self.monitored_paths.items():
                        if path_str in paths:
                            await self.handle_mesg(channel, path=path_str)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error watching directory {dir_path}: {e}")

    def monitor(self, channel: str, path: Union[str, Path]):
        """Set up file monitoring for the given channel and path"""
        path = self._normalize_path(path)
        path_str = str(path)
        dir_path = str(path.parent)

        # Initialize channel set if needed
        if channel not in self.monitored_paths:
            self.monitored_paths[channel] = set()

        # Add path to monitored set
        self.monitored_paths[channel].add(path_str)

        # Set up directory watching if not already watched
        if dir_path not in self.watch_tasks:
            try:
                task = self.add_task(self._watch_directory(dir_path))
                self.watch_tasks[dir_path] = task
                logger.info(f"Monitoring directory: {dir_path}")
            except Exception as e:
                logger.error(f"Failed to monitor directory {dir_path}: {e}")

        logger.info(f"Monitoring file {path_str} on channel {channel}")

    def unmonitor(self, channel: str, path: Union[str, Path] = None):
        """Stop monitoring file(s) for the given channel"""
        if channel not in self.monitored_paths:
            return

        if path is None:
            # Remove all monitored paths for this channel
            self.monitored_paths[channel].clear()
        else:
            # Remove specific path
            path_str = str(self._normalize_path(path))
            self.monitored_paths[channel].discard(path_str)

        # If channel has no more monitored paths, remove it
        if not self.monitored_paths[channel]:
            del self.monitored_paths[channel]

        # Clean up any directories that are no longer needed
        needed_dirs = {str(Path(p).parent) for paths in self.monitored_paths.values() for p in paths}
        for dir_path in list(self.watch_tasks.keys()):
            if dir_path not in needed_dirs:
                self.watch_tasks[dir_path].cancel()
                del self.watch_tasks[dir_path]

    async def close(self):
        """Clean up resources"""
        for task in self.watch_tasks.values():
            task.cancel()
        await super().close()
