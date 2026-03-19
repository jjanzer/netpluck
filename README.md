# NetPluck

NetPluck is a tool allows you to remotely extract assets, typically files, from local and remote archives, such as a zip, without fetching or opening the entire archive. NetPluck was specifically designed to be used for very large .zip files that were stored in remote locations such as buckets on Backblaze and CDNs. It is extremely useful if you want to fetch the list of files or extract specific files of very large remote files.

If you intend to fetch and extract all the contents of the archive or your files are very small you don't need this library.

There are three key features of NetPluck:

1. Works very efficiently on large files
1. Can tell you what's in the file without reading the entire thing
1. Extracts specific files without reading the entire thing

NetPluck provides a CLI tool via `netpluck` and the core python libraries.

## Formats Supported

1. zip
1. zip64

## Protocols Supported

1. Local Files
1. Remote Files over HTTP or HTTPS that support range
1. Backblaze B2

## CLI Usage

### Retrieving the List of Files in the Archive
```
netpluck --path sample_data.zip --toc
empty.txt
lava.png
message.txt
nova.bmp
triangles.png
```

### Extracting Files
You can pass regular expressions using `--filter` to extract files. If you do not specify the `--out` argument it will default to `./output/`
```
netpluck --path sample_data.zip --filter="\.*bmp" --out ./output/
[1/1] 100.00% nova.bmp => ./output/nova.bmp
```

You can also use the `--flatten` flag if you want to strip all directories from the resulting output, this will dump all extracted matches into your output folder with no hierarchy.

### Getting Statistics
You can enable the `--stats` flag to see data about bytes and lookups made.
```
netpluck --path sample_data.zip --stats --filter="\.*txt" --out ./output/
[1/2]  50.00% empty.txt => ./output/empty.txt
[2/2] 100.00% message.txt => ./output/message.txt

File size: 1.52MB
Cache hits: 7 size: 1.37KB
Uncached reads: 3 size: 64.10KB
Bytes saved: 1.46MB 95.88%
```
In this instance we read 64kb of the 1556kb file while extracting the two txt files.


## Extending

### Adding New Protocols and Archives

Protocols in NetPluck are handled by a prefix like: `https://` or `b2://` to add new ones you must modify the `netpluck.py` main class and `ProtocolType` enum. Make sure you modify the `_guess_protocol` method so it can automatically determine the appropriate one.

Archive types can be extended by adding your own handler to `netpluck/virtual_archive` and subclassing the `VirtualArchive`. Be sure to implement all interfaces exposed by `VirtualArchive`. See the existing zip archive handler for an example. Typically this means you implement `__init__` and `_read_uncached_range`. See `netpluck/virtual_file/local.py` or `netpluck/virtual_file/http.py` for a simple example.

You may also need to add a new virtual file type depending on how your data is queried which can be done just like `VirtualArchive` but with `VirtualFile`.
