# Structured Wikivoyage Exports

Small utility to convert the wikitext data from the Wikivoyage dumps into a structured format. The goal is to make it easier to work with the data and extract useful information programmatically.

## Usage

### Docker

This script is intended to be run with docker. A docker image is [available from the GitHub registry](https://github.com/bcye/structured-wikivoyage-exports/pkgs/container/structured-wikivoyage-exports). For example, you may run it using the filesystem handler with `docker run -e HANDLER=filesystem -e HANDLER_FILESYSTEM_OUTPUT_DIR=/output -v ./output:/output --ulimit nofile=65536:65536 ghcr.io/bcye/structured-wikivoyage-exports`. For all the different options, refer to [the docs](docs).

### Types

TypeScript types for consuming the json output are available, you may install them from the [@bcye/structured-wikivoyage-types](https://www.npmjs.com/package/@bcye/structured-wikivoyage-types) npm package. Refer to the included docstrings in [types/index.d.ts](types/index.d.ts) for reference.

## Documentation

See [docs](docs) for more information on how to use this utility.

## Testing

Run `PYTHONPATH=src pytest` from inside the venv, or directly call `PYTHONPATH=src uv run -- pytest`.

## License

### Code

(c) 2025 bcye and moll-re

All code and documentation unless otherwise stated is licensed under the AGPLv3 license, refer to [LICENSE](LICENSE) for the full license text. The types package and all its code is [licensed under MIT](types/LICENSE).

### Examples

Files in the `docs/example` and `tests/fixtures` are copies (.txt) or derivatives (.json) of the Boston Article on Wikivoyage and licensed under CC BY-SA 4.0. A [list of contributors is available on the original article](https://en.wikivoyage.org/w/index.php?title=Boston&action=history).