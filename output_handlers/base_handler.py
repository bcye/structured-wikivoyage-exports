"""Reference handler for output handlers."""
from abc import ABC, abstractmethod
import logging



class BaseHandler(ABC):
    """
    Abstract base class for output handlers. Defines the standardized interface that all output handlers must implement.
    In particular, it requires the implementation of an asynchronous ("private") method `_write_entry` to write a single entry to the output.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, fail_on_error: bool = True, **kwargs):
        """
        Initializes the BaseHandler with optional parameters.

        Args:
            fail_on_error (bool): If True, the handler will raise an exception on error. Defaults to True.
            **kwargs: Additional keyword arguments for specific handler implementations.
        """
        self.fail_on_error = fail_on_error


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
        success = await self._write_entry(entry, uid)
        if success:
            self.logger.debug(f"Successfully wrote entry with UID {uid}")
        else:
            self.logger.error(f"Failed to write entry with UID {uid}")
            if self.fail_on_error:
                raise Exception(f"Failed to write entry with UID {uid}")
