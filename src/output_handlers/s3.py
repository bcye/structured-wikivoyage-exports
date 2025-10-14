"""Handler that writes asynchronously."""
from .base_handler import BaseHandler
import json
from aiobotocore.session import AioSession
from contextlib import AsyncExitStack

class S3Handler(BaseHandler):
    """
    Handler that writes files to an S3 bucket asynchronously.
    """
    @classmethod
    async def create(cls, url: str, access_key: str, secret_key: str, bucket_name: str, **kwargs) -> "S3Handler":
        """
        Initializes the Handler with the specified S3 endpoint and bucket name.

        Args:
            **kwargs: Additional keyword arguments for the BaseHandler.
        """
        self = await super().create(**kwargs)
        self.bucket_name = bucket_name

        self.exit_stack = AsyncExitStack()

        session = AioSession()
        self.client = await self.exit_stack.enter_async_context(
            session.create_client(
                service_name = 's3',
                # region_name='us-west-2',
                aws_secret_access_key = secret_key,
                aws_access_key_id = access_key,
                endpoint_url = url,
            )
        )

        await self._ensure_bucket_exists()
        return self


    async def _ensure_bucket_exists(self):
        """
        Ensures that the specified S3 bucket exists, but does not create it if it doesn't.
        """
        # this will raise an error if the bucket does not exist
        await self.client.head_bucket(Bucket=self.bucket_name)


    async def _write_entry(self, entry: dict, uid: str) -> bool:
        """
        Asynchronously writes a single entry to the bucket.
        """
        data = json.dumps(entry).encode('utf-8')
        try:
            response = await self.client.put_object(
                Bucket = self.bucket_name,
                Key = f"{uid}.json",
                Body = data
            )

            if response['ResponseMetadata']['HTTPStatusCode'] not in (200, 201):
                raise Exception(f"Response: {response}")
            return True

        except:
            self.logger.exception(f"Failed to write entry {uid} to bucket {self.bucket_name}.")
            return False


    async def close(self):
        await self.client.close()
        await self.exit_stack.__aexit__(None, None, None)
        await super().close()
