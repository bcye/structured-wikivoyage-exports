## Documentation

### Overview
The tool performs three main tasks:
1. It downloads the latest Wikivoyage dump from Wikimedia.
2. It parses the dump and produces structured data in JSON format.
3. It outputs the structured data to a specified target.


### Configuration
Configuration is handled through environment variables. The following variables are available:

- general setup
    - `DEBUG`: Increases the verbosity of the output if set. If unset, the program will run in normal mode.
    - `MAX_CONCURRENT`: The maximum number of concurrent operations to perform. This is useful for limiting the number of concurrent requests to the various APIs. By default, this is set to 0, which means no limit.

- output handler setup
    - `HANDLER`: The output handler to use. The available handlers are defined in the `output_handler` module. Use their file name as the value (currently implemented: `filesystem` or `bunny_storage`).
    - Different handlers may have different configuration options. Specify them through `HANDLER_<handler_name>_<option>`:
        - `HANDLER_FILESYSTEM_OUTPUT_DIR`: The directory to output the structured data to.
        - `HANDLER_FILESYSTEM_FAIL_ON_ERROR`: By default the handler will fail if a particular write operation fails. If this is set to `false`, the handler will skip the erronous writes and continue with the next one.
        - `HANDLER_BUNNY_STORAGE_API_KEY`: The API key for Bunny Storage.
        - `HANDLER_BUNNY_STORAGE_ENDPOINT`: The endpoint for Bunny Storage.
        - `HANDLER_BUNNY_STORAGE_BASE_PATH`: The base path to output the structured data to. 
        - `HANDLER_BUNNY_STORAGE_FAIL_ON_ERROR`: By default the handler will fail if a particular write operation fails. If this is set to `false`, the handler will skip the erronous writes and continue with the next one.

Environment files can be specified through as an `.env` file. Sample files are provided: see [filesystem.env](filesystems.env) and [bunny_storage.env](bunny_storage.env).


### Fetching
TBD

### Parsing
The result of the parsing is a JSON object, see an example under [example](example).

#### Output
TBD

### Output
According to the output handler, the structured data is written to a file or uploaded to a storage service. The handlers are kept modular and we encourage you to implement your own handler, contributions are welcome. The only design constraint we have is that the outputs to individual files.
