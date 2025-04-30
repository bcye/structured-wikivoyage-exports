#!/usr/bin/env python3
import os
import sys
import re
import zlib
import bz2
import asyncio
import logging
import importlib
import xml.sax
from pathlib import Path
from dotenv import load_dotenv
import aiohttp
from parser import WikivoyageParser

logger = logging.getLogger(__name__)

def gather_handler_kwargs(handler_name: str) -> dict:
    """
    Find all ENV vars starting with HANDLER_<NAME>_ and turn them into kwargs.
    E.g. HANDLER_SFTP_HOST=foo → {"host": "foo"}, HANDLER_SFTP_PORT=2222 → {"port": 2222}
    """
    prefix = f"HANDLER_{handler_name.upper()}_"
    kwargs = {}

    for env_key, val in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        param = env_key.replace(prefix, "").lower()
        # cast ints
        if val.isdigit():
            val = int(val)
        # cast bools
        elif val.lower() in ("true", "false"):
            val = val.lower() == "true"
        kwargs[param] = val
    logger.debug(f"Handler kwargs: {kwargs}")
    return kwargs

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
                        mappings[page_id] = value
                # keep tail to handle split tuples
                if len(buffer) > 1000:
                    buffer = buffer[-1000:]
    return mappings

class WikiDumpHandler(xml.sax.ContentHandler):
    """
    SAX handler that, for each <page> whose <id> is in mappings,
    collects the <text> and schedules an async task to parse
    and write via the user‐supplied handler.
    """

    def __init__(self, mappings, handler, max_concurrent):
        super().__init__()
        self.mappings = mappings
        self.handler = handler
        self.sem = (
            asyncio.Semaphore(max_concurrent) if max_concurrent > 0 else None
        )
        self.tasks: list[asyncio.Task] = []

        self.currentTag: str | None = None
        self.inPage = False
        self.inRevision = False
        self.inText = False
        self.currentPageId: str | None = None
        self.currentText: list[str] = []

    def startElement(self, name, attrs):
        self.currentTag = name
        if name == "page":
            self.inPage = True
            self.currentPageId = None
            self.currentText = []
        elif name == "revision":
            self.inRevision = True
        elif name == "text" and self.inRevision:
            self.inText = True

    def endElement(self, name):
        if name == "page":
            pid = self.currentPageId
            if pid and pid in self.mappings:
                wd_id = self.mappings[pid]
                text = "".join(self.currentText)
                # schedule processing
                if self.sem:
                    task = asyncio.create_task(self._bounded_process(text, wd_id))
                else:
                    task = asyncio.create_task(self._process(text, wd_id))
                self.tasks.append(task)
            # reset
            self.inPage = self.inRevision = self.inText = False
            self.currentPageId = None
            self.currentText = []
        elif name == "revision":
            self.inRevision = False
        elif name == "text":
            self.inText = False
        self.currentTag = None

    def characters(self, content):
        # Only filter whitespace for ID fields, preserve all content for text
        if (
            self.currentTag == "id"
            and self.inPage
            and not self.inRevision
            and not self.currentPageId
        ):
            content_stripped = content.strip()
            if content_stripped:  # Only process non-empty ID content
                self.currentPageId = content_stripped
        elif self.inText:
            # Always append text content, even if it's just whitespace or newlines
            self.currentText.append(content)

    async def _process(self, text: str, uid: str):
        parser = WikivoyageParser()
        entry = parser.parse(text)
        await self.handler.write_entry(entry, uid)

    async def _bounded_process(self, text: str, uid: str):
        # Only run N at once
        async with self.sem:
            await self._process(text, uid)

async def process_dump(
    mappings: dict[str, str], handler, max_concurrent: int
):
    """
    Stream-download the bzip2-compressed XML dump and feed to SAX.
    """
    xml_url = (
        "https://dumps.wikimedia.org/"
        "enwikivoyage/latest/"
        "enwikivoyage-latest-pages-articles.xml.bz2"
    )
    decomp = bz2.BZ2Decompressor()
    sax_parser = xml.sax.make_parser()
    dump_handler = WikiDumpHandler(mappings, handler, max_concurrent)
    sax_parser.setContentHandler(dump_handler)

    async with aiohttp.ClientSession() as session:
        async with session.get(xml_url) as resp:
            resp.raise_for_status()
            async for chunk in resp.content.iter_chunked(1024 * 1024):
                data = decomp.decompress(chunk)
                if not data:
                    continue
                text = data.decode("utf-8", errors="ignore")
                sax_parser.feed(text)
    sax_parser.close()
    if dump_handler.tasks:
        await asyncio.gather(*dump_handler.tasks)

async def main():
    # 1. Which handler to load?
    handler_name = os.getenv("HANDLER")
    if not handler_name:
        logger.error("Error: set ENV HANDLER (e.g. 'filesystem')")
        sys.exit(1)

    # 2. Dynamic import
    module_path = f"output_handlers.{handler_name}"
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        logger.error(f"Error loading handler module {module_path}: {e}")
        sys.exit(1)

    # 3. Find the class: e.g. "sftp" → "SftpHandler"
    class_name = handler_name.title().replace("_", "") + "Handler"
    if not hasattr(mod, class_name):
        logger.error(f"{module_path} defines no class {class_name}")
        sys.exit(1)
    HandlerCls = getattr(mod, class_name)

    logger.info(f"Using handler from {module_path}")

    # 4. Build kwargs from ENV
    handler_kwargs = gather_handler_kwargs(handler_name)

    # 5. Instantiate
    handler = HandlerCls(**handler_kwargs)

    # 6. read concurrency setting
    try:
        max_conc = int(os.getenv("MAX_CONCURRENT", "0"))
    except ValueError:
        raise ValueError("MAX_CONCURRENT must be an integer")

    if max_conc < 0:
        raise ValueError("MAX_CONCURRENT must be >= 0")


    # 7. Fetch mappings
    logger.info("Fetching mappings from SQL dump…")
    mappings = await fetch_mappings()
    logger.info(f"Got {len(mappings)} wikibase_item mappings.")

    # 8. Stream & split the XML dump
    logger.info("Processing XML dump…")
    await process_dump(mappings, handler, max_conc)

    # 5. Finish up
    await handler.close()
    logger.info("All done.")


if __name__ == "__main__":
    load_dotenv()
    if os.getenv("DEBUG"):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    asyncio.run(main())
