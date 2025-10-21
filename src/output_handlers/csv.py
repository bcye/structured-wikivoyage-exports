"""CSV output handler for writing entries to a single CSV file with ID and title."""
from pathlib import Path
import aiofiles
from .base_handler import BaseHandler


class CsvHandler(BaseHandler):
    """
    Handler for writing entries to a single CSV file.
    This handler extracts only the ID and title (from properties.title)
    rather than writing the entire JSON document.
    """

    file_writer: any # I believe aiofiles doesn't expose a type for this

    @classmethod
    async def create(
        cls,
        output_path: Path,
        **kwargs,
    ) -> "CsvHandler":
        """
        Initializes the CSVHandler.

        Args:
            output_path (str): Path to the CSV file to write to.
            **kwargs: Additional keyword arguments.
        """
        obj = await super().create(**kwargs)
        output_path = Path(output_path)

        # Create the containging directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file with header if it doesn't exist
        if not output_path.exists():
            async with aiofiles.open(output_path, mode='w', encoding='utf-8') as file:
                await file.write('"id","title"\n')

        # open the file and keep it open for appending
        obj.file_writer = await aiofiles.open(output_path, mode='a', encoding='utf-8')

        return obj


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
            title = entry.get("properties", {}).get("title", "")

            # Escape quotes in title
            title = str(title).replace('"', '""')

            await self.file_writer.write(f'"{uid}","{title}"\n')

            return True
        except Exception as e:
            self.logger.exception(f"Error writing entry {uid} to CSV.")
            return False


    async def close(self):
        """
        Performs cleanup and logs statistics.
        """
        await self.file_writer.close()
        await super().close()
