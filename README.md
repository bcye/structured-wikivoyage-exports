# Structured Wikivoyage Exports

Small utility to convert the wikitext data from the Wikivoyage dumps into a structured format. The goal is to make it easier to work with the data and extract useful information programmatically.

## Usage

### Docker

This script is intended to be run with docker. A docker image is [available from the GitHub registry](). For example, you may run it using the filesystem handler with `docker run -e HANDLER=filesystem -e HANDLER_FILESYSTEM_OUTPUT_DIR=/output -v ./output:/output ghcr.io/bcye/structured-wikivoyage-exports`. For all the different options, refer to [the docs](docs).

### Types

TypeScript types for consuming the json output are available, you may install them from the [@bcye/structured-wikivoyage-types]() npm package. Refer to the included docstrings in [types/index.d.ts](types/index.d.ts) for reference.

## Documentation

See [docs](docs) for more information on how to use this utility.
