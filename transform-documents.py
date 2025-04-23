import os
from pathlib import Path
import sys
import asyncio
import importlib
import logging
from dotenv import load_dotenv

from parser import WikivoyageParser

async def process_file(
    input_file: Path,
    handler,
) -> None:
    """
    Parse one wiki file and hand the resulting entry off to our handler.
    Uses the filename (sans suffix) as the unique UID.
    """
    
    text = input_file.read_text(encoding="utf-8")
    parser = WikivoyageParser()
    entry = parser.parse(text)  # assume returns a dict
    uid = input_file.stem

    await handler.write_entry(entry, uid)

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
    print(f"Handler kwargs: {kwargs}")
    return kwargs

async def main():

    # 1. Which handler to load?
    handler_name = os.getenv("HANDLER")
    if not handler_name:
        print("Error: set ENV HANDLER (e.g. 'filesystem')")
        sys.exit(1)

    # 2. Dynamic import
    module_path = f"output_handlers.{handler_name}"
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error loading handler module {module_path}: {e}")
        sys.exit(1)

    # 3. Find the class: e.g. "sftp" → "SftpHandler"
    class_name = handler_name.title().replace("_", "") + "Handler"
    if not hasattr(mod, class_name):
        print(f"{module_path} defines no class {class_name}")
        sys.exit(1)
    HandlerCls = getattr(mod, class_name)

    # 4. Build kwargs from ENV
    handler_kwargs = gather_handler_kwargs(handler_name)

    # 5. Instantiate
    handler = HandlerCls(**handler_kwargs)

    # 6. Which dir to walk?
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    txt_files = list(input_dir.rglob("*.txt"))

    if not txt_files:
        print(f"No .txt files found under {input_dir}")
        sys.exit(1)

    # 7. read concurrency setting
    try:
        max_conc = int(os.getenv("MAX_CONCURRENT", "0"))
    except ValueError:
        print("Error: MAX_CONCURRENT must be an integer")
        sys.exit(1)

    if max_conc < 0:
        print("Error: MAX_CONCURRENT must be >= 0")
        sys.exit(1)

    # 8. schedule tasks
    if max_conc == 0:
        # unbounded
        tasks = [
            asyncio.create_task(process_file(txt, handler))
            for txt in txt_files
        ]
    else:
        # bounded by semaphore
        sem = asyncio.Semaphore(max_conc)

        async def bounded(txt):
            async with sem:
                return await process_file(txt, handler)

        tasks = [
            asyncio.create_task(bounded(txt))
            for txt in txt_files
        ]

    # 9. run them all
    await asyncio.gather(*tasks)
    await handler.close()


    print("All done.")


if __name__ == "__main__":
    load_dotenv()
    if os.getenv("DEBUG"):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    asyncio.run(main())
