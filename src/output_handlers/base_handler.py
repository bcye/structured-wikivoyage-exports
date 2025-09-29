"""Reference handler for output handlers."""
from abc import ABC, abstractmethod
import logging
import asyncio



class BaseHandler(ABC):
    """
    Abstract base class for output handlers. Defines the standardized interface that all output handlers must implement.
    In particular, it requires the implementation of an asynchronous ("private") method `_write_entry` to write a single entry to the output.
    """

    logger = logging.getLogger(__name__)
    _successful_writes = 0
    _failed_writes = 0

    def __init__(self, fail_on_error: bool = True, max_concurrent=0, **kwargs):
        """
        Initializes the BaseHandler with optional parameters.

        Args:
            fail_on_error (bool): If True, the handler will raise an exception on error. Defaults to True.
            max_concurrent: Maximum number of concurrent write operations.
                            0 means unlimited concurrency.
            **kwargs: Additional keyword arguments for specific handler implementations.
        """
        self.fail_on_error = fail_on_error
        self.semaphore = None
        if max_concurrent > 0:
            self.semaphore = asyncio.Semaphore(max_concurrent)


    @abstractmethod
    async def _write_entry(self, entry: dict, uid: str) -> bool:
        """
        Asynchronously writes a single entry to the output. This method should gracefully handle any exceptions that may occur during the writing process and simply return False if an error occurs.

        Args:
            entry (dict): The entry to write (will be JSON-encoded).
            uid (str): The unique identifier for the entry. The default id provided by wikivoyage is recommended. 
        Returns:
            bool: True if the entry was written successfully, False otherwise.
        """
        pass


    async def write_entry(self, entry: dict, uid: str):
        """
        Public method to write an entry to the output. It handles exceptions and logs errors.

        Args:
            entry (dict): The entry to write (will be JSON-encoded).
            uid (str): The unique identifier for the entry. The default id provided by wikivoyage is recommended. 
        """
        if self.semaphore:
            async with self.semaphore:
                success = await self._write_entry(entry, uid)
        else:
            success = await self._write_entry(entry, uid)
        if success:
            self.logger.debug(f"Successfully wrote entry with UID {uid}")
            self._successful_writes += 1
        else:
            self.logger.error(f"Failed to write entry with UID {uid}")
            self._failed_writes += 1
            if self.fail_on_error:
                raise Exception(f"Failed to write entry with UID {uid}")


    async def close(self):
        """
        Closes the handler. This method should be overridden by subclasses if they need to perform any cleanup operations.
        """
        self.logger.info(f"Wrote {self._successful_writes+self._failed_writes} entries: {self._successful_writes} successful, {self._failed_writes} failed.")
