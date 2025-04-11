"""Handler that writes files to the filesystem."""
from pathlib import Path
import aiofiles
from .base_handler import BaseHandler

class FileSystemHandler(BaseHandler):
    """
    Handler that writes files to the filesystem.
    """
    def __init__(self, output_dir: str, **kwargs):
        """
        Initializes the FileSystemHandler with the specified output directory.

        Args:
            output_dir (str): The directory where files will be written.
            **kwargs: Additional keyword arguments for the BaseHandler.
        """
        super().__init__(**kwargs)
        self.output_dir = Path(output_dir)
        # Ensure the target directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directory set to {self.output_dir}")


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
                await f.write(entry)
            return True
        except IOError as e:
            self.logger.error(f"Error writing entry {uid}: {e}")
            return False
