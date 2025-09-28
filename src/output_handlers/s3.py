"""Handler that writes asynchronously."""
from .base_handler import BaseHandler
import json
from minio import Minio
# making async calls to minio requires some wrapping
import concurrent.futures
import asyncio


class S3Handler(BaseHandler):
    """
    Handler that writes files to an S3 bucket asynchronously.
    """
    def __init__(self, s3_url: str, s3_access_key: str, s3_secret_key: str, s3_bucket_name: str, **kwargs):
        """
        Initializes the Handler with the specified S3 endpoint and bucket name.

        Args:
            **kwargs: Additional keyword arguments for the BaseHandler.
        """
        super().__init__(**kwargs)

        self.s3_client = Minio(
            s3_url,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
            secure=True
        )
        self.bucket_name = s3_bucket_name

        self.executor = concurrent.futures.ThreadPoolExecutor()
        self._ensure_bucket_exists()


    def _ensure_bucket_exists(self):
        """
        Ensures that the specified S3 bucket exists, tries to create it if it does not.
        """
        if not self.s3_client.bucket_exists(self.bucket_name):
            try:
                self.s3_client.make_bucket(self.bucket_name)
                self.logger.info(f"Created bucket: {self.bucket_name}")
            except Exception as e:
                self.logger.error(f"Error creating bucket {self.bucket_name}: {e}")
                raise
        else:
            self.logger.debug(f"Bucket {self.bucket_name} already exists.")


    async def _write_entry(self, entry: dict, uid: str) -> bool:
        """
        Asynchronously writes a single entry to the bucket.

        Args:
            entry (dict): The entry to write (will be JSON-encoded).
            uid (str): The unique identifier for the entry.

        Returns:
            bool: True if the entry was written successfully, False otherwise.
        """

        loop = asyncio.get_running_loop()


        def sync_put():
            entry_json = json.dumps(entry).encode('utf-8')
            self.s3_client.put_object(
                bucket_name = self.bucket_name,
                object_name = f"{uid}.json",
                data = entry_json,
                length = len(entry_json),
                content_type = 'application/json'
            )

        # rub the put operation in a thread pool to avoid blocking the event loop
        try:
            result = await loop.run_in_executor(self.executor, sync_put)
            if not result:
                raise Exception("Minio operation failed without exception.")
            self.logger.debug(f"Successfully wrote entry with UID {uid} to bucket {self.bucket_name}.")
            return True
        except Exception as e:
            self.logger.error(f"Error writing entry with UID {uid} to bucket {self.bucket_name}: {e}")
            return False
