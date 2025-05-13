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
from transformers import fetch_mappings, WikiDumpHandler, WikivoyageParser


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
