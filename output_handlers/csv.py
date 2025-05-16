"""CSV output handler for writing entries to a single CSV file with ID and title."""
import os
import aiofiles
import logging
from .base_handler import BaseHandler


class CsvHandler(BaseHandler):
    """
    Handler for writing entries to a single CSV file.
    This handler extracts only the ID and title (from properties.title)
    rather than writing the entire JSON document.
    """

    def __init__(
        self,
        output_path: str,
        fail_on_error: bool = True,
        **kwargs
    ):
        """
        Initializes the CSVHandler.

        Args:
            output_path (str): Path to the CSV file to write to.
            fail_on_error (bool): If True, the handler will raise an exception on error.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(fail_on_error=fail_on_error, **kwargs)
        self.output_path = output_path
        self.logger = logging.getLogger(__name__)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
        # Create file with header if it doesn't exist
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write("id,title\n")

    async def _write_entry(self, entry: dict, uid: str) -> bool:
        """
        Asynchronously writes a single entry to the CSV file.

        Args:
            entry (dict): The entry to write.
            uid (str): The unique identifier for the entry.
        
        Returns:
            bool: True if the entry was written successfully, False otherwise.
        """
        try:
            # Extract title from properties.title
            title = ""
            if "properties" in entry and "title" in entry["properties"]:
                title = entry["properties"]["title"]
            
            # Escape quotes in title
            title = str(title).replace('"', '""')
            
            # Open file in append mode for each write
            async with aiofiles.open(self.output_path, mode='a', encoding='utf-8') as file:
                # Write the row
                await file.write(f'"{uid}","{title}"\n')
            
            return True
        except Exception as e:
            self.logger.error(f"Error writing entry {uid} to CSV: {str(e)}")
            return False

    async def close(self):
        """
        Performs cleanup and logs statistics.
        """
        await super().close() 