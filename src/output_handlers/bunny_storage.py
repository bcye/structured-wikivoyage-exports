import json
import aiohttp
from .base_handler import BaseHandler

class BunnyStorageHandler(BaseHandler):

    base_url: str
    headers: dict
    _session: aiohttp.ClientSession
    _connector: aiohttp.TCPConnector

    @classmethod
    async def create(
        cls,
        region: str,
        base_path: str,
        api_key: str,
        keepalive_timeout: int = 75,
        **kwargs,
    ) -> "BunnyStorageHandler":
        obj = await super().create(**kwargs)
        obj.base_url = f"https://{region}.bunnycdn.com/{base_path}"
        obj.headers = {
            "AccessKey": api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        }

        # setup the aiohttp session and connector
        obj._connector = aiohttp.TCPConnector(
            # limit is implicitly set to 100
            keepalive_timeout = keepalive_timeout,
        )
        obj._session = aiohttp.ClientSession(connector=obj._connector)
        return obj


    async def _write_entry(self, entry: dict, uid: str) -> bool:
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
