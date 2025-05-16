from logging import getLogger
import zlib
import re
import aiohttp

logger = getLogger(__name__)

async def fetch_mappings() -> dict[str, str]:
    """
    Download and gunzip the page_props SQL dump, extract
    page→wikibase_item mappings.
    """
    sql_url = (
        "https://dumps.wikimedia.org/"
        "enwikivoyage/latest/"
        "enwikivoyage-latest-page_props.sql.gz"
    )
    # decompress gzip
    decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)
    # regex for tuples: (page,'prop','value',NULL_or_number)
    tuple_re = re.compile(r"\((\d+),'([^']+)','([^']+)',(NULL|[\d\.]+)\)")
    buffer = ""
    mappings: dict[str, str] = {}

    async with aiohttp.ClientSession() as session:
        async with session.get(sql_url) as resp:
            resp.raise_for_status()
            async for chunk in resp.content.iter_chunked(1024 * 1024):
                data = decomp.decompress(chunk)
                if not data:
                    continue
                text = data.decode("utf-8", errors="ignore")
                buffer += text
                for m in tuple_re.finditer(buffer):
                    page_id, prop, value = m.group(1), m.group(2), m.group(3)
                    if prop == "wikibase_item":
                        logger.debug(f"Found mapping {page_id} -> {value}")
                        mappings[page_id] = value
                # keep tail to handle split tuples
                if len(buffer) > 1000:
                    buffer = buffer[-1000:]
    return mappings
