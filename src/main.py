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
    mappings: dict[str, str], handlers
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
    dump_handler = WikiDumpHandler(mappings, handlers)
    sax_parser.setContentHandler(dump_handler)
    timeout = aiohttp.ClientTimeout(total = 5000)
    async with aiohttp.ClientSession(timeout=timeout) as session:
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
    # 1. Which handler(s) to load?
    handler_names = os.getenv("HANDLER", "").split(",")
    if not handler_names or not handler_names[0]:
        logger.error("Error: set ENV HANDLER (e.g. 'filesystem' or 'filesystem,sftp')")
        sys.exit(1)

    # 2. Read concurrency setting
    try:
        max_conc = int(os.getenv("MAX_CONCURRENT", "0"))
    except ValueError:
        raise ValueError("MAX_CONCURRENT must be an integer")

    if max_conc < 0:
        raise ValueError("MAX_CONCURRENT must be >= 0")

    handlers = []

    # 3. Load each handler
    for handler_name in handler_names:
        handler_name = handler_name.strip()
        if not handler_name:
            continue

        # Dynamic import
        module_path = f"output_handlers.{handler_name}"
        try:
            mod = importlib.import_module(module_path)
        except ImportError as e:
            logger.error(f"Error loading handler module {module_path}: {e}")
            sys.exit(1)

        # Find the class: e.g. "sftp" → "SftpHandler"
        class_name = handler_name.title().replace("_", "") + "Handler"
        if not hasattr(mod, class_name):
            logger.error(f"{module_path} defines no class {class_name}")
            sys.exit(1)
        HandlerCls = getattr(mod, class_name)

        logger.info(f"Using handler from {module_path}")

        # Build kwargs from ENV
        handler_kwargs = gather_handler_kwargs(handler_name)

        # Add max_concurrent to kwargs
        handler_kwargs["max_concurrent"] = max_conc

        # Instantiate
        handler = await HandlerCls.create(**handler_kwargs)
        handlers.append(handler)

    # 4. Fetch mappings
    logger.info("Fetching mappings from SQL dump…")
    mappings = await fetch_mappings()
    logger.info(f"Got {len(mappings)} wikibase_item mappings.")

    # 5. Stream & split the XML dump
    logger.info("Processing XML dump…")
    await process_dump(mappings, handlers)  # Pass 0 as max_concurrent since handlers handle it

    # 6. Finish up
    await asyncio.gather(*[handler.close() for handler in handlers])
    logger.info("All done.")


if __name__ == "__main__":
    load_dotenv()
    if os.getenv("DEBUG"):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    asyncio.run(main())
