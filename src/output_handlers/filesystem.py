"""Handler that writes files to the filesystem."""
from pathlib import Path
import aiofiles
from .base_handler import BaseHandler
import json

class FilesystemHandler(BaseHandler):
    """
    Handler that writes files to the filesystem.
    """
    output_dir: Path

    @classmethod
    async def create(cls, output_dir: str, **kwargs) -> "FilesystemHandler":
        """
        Initializes the FileSystemHandler with the specified output directory.

        Args:
            output_dir (str): The directory where files will be written.
            **kwargs: Additional keyword arguments for the BaseHandler.
        """
        obj = await super().create(**kwargs)
        obj.output_dir = Path(output_dir)
        # Ensure the target directory exists
        obj.output_dir.mkdir(parents=True, exist_ok=True)
        obj.logger.info(f"Output directory set to {obj.output_dir}")
        return obj


    async def _write_entry(self, entry: dict, uid: str) -> bool:
        """
        Asynchronously writes a single entry to the filesystem.

        Args:
            entry (dict): The entry to write (will be JSON-encoded).
            uid (str): The unique identifier for the entry.

        Returns:
            bool: True if the entry was written successfully, False otherwise.
        """
        try:
            file_path = self.output_dir / f"{uid}.json"
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(entry))
            return True
        except IOError as e:
            self.logger.error(f"Error writing entry {uid}: {e}")
            return False
