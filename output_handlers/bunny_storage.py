import json
import aiohttp
from .base_handler import BaseHandler

class BunnyStorageHandler(BaseHandler):
    def __init__(
        self,
        region: str,
        base_path: str,
        api_key: str,
        fail_on_error: bool = True,
        keepalive_timeout: int = 75,
        **kwargs,
    ):
        super().__init__(fail_on_error=fail_on_error, **kwargs)
        self.base_url = f"https://{region}.bunnycdn.com/{base_path}"
        self.headers = {
            "AccessKey": api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        }

        # initialized later, in a guaranteed async context
        self._connector = None
        self._session = None
        self._keepalive_timeout = keepalive_timeout

    async def setup_connector(self):
        if self._session is None:
            self._connector = aiohttp.TCPConnector(
                # limit is implicitly set to 100
                keepalive_timeout = self._keepalive_timeout,
            )
            self._session = aiohttp.ClientSession(connector=self._connector)

    async def _write_entry(self, entry: dict, uid: str) -> bool:
        await self.setup_connector()
        payload = json.dumps(entry).encode("utf-8")
        url = f"{self.base_url}/{uid}.json"

        try:
            async with self._session.put(url, data=payload, headers=self.headers) as resp:
                if resp.status in (200, 201, 204):
                    return True
                body = await resp.text()
                self.logger.error(f"Upload failed UID={uid} status={resp.status} body={body}")
                return False

        except Exception:
            self.logger.exception(f"Exception while uploading UID={uid}")
            return False

    async def close(self):
        await self._session.close()
        await self._connector.close()
        await super().close()
