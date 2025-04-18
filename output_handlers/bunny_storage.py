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
    ):
        super().__init__(fail_on_error=fail_on_error)
        self.region = region
        self.base_path = base_path
        self.api_key = api_key

        # no explicit 'limit'; use the default (100)
        self._connector = aiohttp.TCPConnector(
            keepalive_timeout=keepalive_timeout
        )
        self._session = aiohttp.ClientSession(connector=self._connector)

    async def _write_entry(self, entry: dict, uid: str) -> bool:
        url = f"https://{self.region}.bunnycdn.com/{self.base_path}/{uid}.json"
        headers = {
            "AccessKey": self.api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        }
        payload = json.dumps(entry).encode("utf-8")

        try:
            async with self._session.put(url, data=payload, headers=headers) as resp:
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