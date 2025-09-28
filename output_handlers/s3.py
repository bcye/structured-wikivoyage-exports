"""Handler that writes asynchronously."""
from .base_handler import BaseHandler
import json
from minio import Minio
# making async calls to minio requires some wrapping
import concurrent.futures
import asyncio
from io import BytesIO
import urllib3


class S3Handler(BaseHandler):
    """
    Handler that writes files to an S3 bucket asynchronously.
    """
    def __init__(self, url: str, access_key: str, secret_key: str, bucket_name: str, **kwargs):
        """
        Initializes the Handler with the specified S3 endpoint and bucket name.

        Args:
            **kwargs: Additional keyword arguments for the BaseHandler.
        """
        super().__init__(**kwargs)

        self.bucket_name = bucket_name

        # minio uses urllib3 so we need to set the connection pool limit according to max_concurrent
        max_concurrent = kwargs.get("max_concurrent")
        # usually 0 is used to indicate no concurrence - in this setup that corresponds to a single worker
        max_concurrent = max(1, max_concurrent)

        http_client = urllib3.PoolManager(num_pools=max_concurrent)

        self.s3_client = Minio(
            url,
            access_key = access_key,
            secret_key = secret_key,
            secure = True,
            http_client = http_client
        )

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent)
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
            # put requires an object that implements read
            entry_json = json.dumps(entry).encode("utf-8")
            size = len(entry_json) # size in bytes
            entry_bytes = BytesIO(entry_json)
            result = self.s3_client.put_object(
                bucket_name = self.bucket_name,
                object_name = f"{uid}.json",
                data = entry_bytes,
                length = size,
                content_type = "application/json"
            )
            self.logger.debug(f"Got result {result}")
            return result

        # run the put operation in a thread pool to avoid blocking the event loop
        try:
            result = await loop.run_in_executor(self.executor, sync_put)
            if not result:
                raise Exception("Minio operation failed without exception.")
            self.logger.debug(f"Successfully wrote entry with UID {uid} to bucket {self.bucket_name}.")
            return True
        except Exception as e:
            self.logger.error(f"Error writing entry with UID {uid} to bucket {self.bucket_name}: {e}")
            return False

    async def close(self):
        self.executor.shutdown(wait=True)
        self.logger.info("Executor shut down.")
