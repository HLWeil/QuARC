# QuARC
ARC Quadstore DB

## Requirements: 
- Docker
- Python
- UV


## Setup:

### Setup Fuseki Server

```
Download https://repo1.maven.org/maven2/org/apache/jena/jena-fuseki-docker/6.2.0/jena-fuseki-docker-6.2.0.zip, unzip and copy the contents to a folder named `jena-fuseki-docker-6.2.0` in the project root.

```

```powershell
cd .\jena-fuseki-docker-6.2.0\
docker-compose build --build-arg JENA_VERSION=6.2.0 
docker-compose run --rm --service-ports fuseki --tdb2 --update --loc databases /ds                                     
```

### Setup Python environment

```powershell
python -m venv .venv
uv install -r requirements.txt
```

### Fill the database from ARC IDs

With Fuseki running and updates enabled, process the `arc_ids` list in
`scripts/fill-db.py`:

```powershell
uv run .\scripts\fill-db.py
```

For each ARC, the script downloads its RO-Crate JSON-LD, runs `jsonld-to-ttl.py`,
and runs `load-ttl.py` to replace the named graph `https://git.nfdi4plants.org/<arc_id>`.
Relative RDF identifiers use this graph URL followed by `/ro-crate-metadata.json`
as their base. JSON-LD and Turtle files are kept in the current directory.
Progress is printed for each step; failed ARCs are reported and the remaining
ARCs are still processed. The exit code is 1 if any ARC fails.

To override the IDs, Fuseki host, or output directory:

```powershell
uv run .\scripts\fill-db.py 1040 122 --host localhost:3030 --output-dir .\tmp\crates
```

### Convert RO-Crate metadata to Turtle

Download e.g. https://git.nfdi4plants.org/brilator/Facultative-CAM-in-Talinum/-/package_files/89873/download, copy into this folder and rename to `ro-crate-metadata.json`. Then run:

```powershell
uv run .\scripts\jsonld-to-ttl.py
```

Run this command from the project root. By default, the script reads
`ro-crate-metadata.json` from the project root and writes
`ro-crate-metadata.ttl` alongside it, regardless of your working directory.
Explicit input and output paths are relative to your working directory.

RDFLib reads the JSON-LD context and
preserves RDF types, links, literals, and the inline vocabulary extensions.
Internet access is needed to retrieve remote contexts such as the RO-Crate 1.1
context used by the example metadata.

For portable resource identifiers, specify the metadata document's absolute IRI:

```powershell
uv run .\scripts\jsonld-to-ttl.py ro-crate-metadata.json -o crate.ttl --base https://example.org/crate/ro-crate-metadata.json
```

Relative IDs such as `./`, file paths, and `#fragment` are resolved against this
IRI. Without `--base`, they use the input file's absolute `file:` URI. Turtle is
written as UTF-8 with absolute resource identifiers.

### Load the Turtle into Apache Jena Fuseki

#### Python

With Fuseki running and updates enabled, run from the project root:

```powershell
uv run scripts/load-ttl.py
```

This adds the project-root `ro-crate-metadata.ttl` to the default graph at
`http://localhost:3030/ds/data?default`. Existing data is preserved.

To use another host or another Turtle file:

```powershell
uv run scripts/load-ttl.py --host 192.168.1.10:3030
uv run scripts/load-ttl.py .\crate.ttl --host https://fuseki.example.org
```

Explicit file paths are relative to your working directory. The uploader uses
Python's standard library and reports file, connection, and HTTP errors.

#### Curl

```powershell
curl.exe --fail-with-body -X POST `
  -H "Content-Type: text/turtle" `
  --data-binary "@.\ro-crate-metadata.ttl" `
  "http://localhost:3030/ds/data?default"
```


#### TBD2

Load the Turtle into Apache Jena TDB2 using the Jena binary distribution:

```powershell
tdb2_tdbloader --loc DB ro-crate-metadata.ttl
```

On Linux/macOS the command is `tdb2.tdbloader`. To load into a named graph,
add `--graph=https://example.org/graph`. See the
[Jena TDB2 command-line documentation](https://jena.apache.org/documentation/tdb2/tdb2_cmds.html).


### Reset the RDF store

With Fuseki running and updates enabled, run from the project root:

```powershell
uv run scripts/drop-db.py
```

To reset a dataset on another host:

```powershell
uv run scripts/drop-db.py --host 192.168.1.10:3030
```

This sends `DROP ALL` to `/ds/update`, deleting all RDF data in `/ds`, including
named graphs. It keeps the dataset configuration and database files. The reset
persists for TDB2 databases. The default host is `localhost:3030`; HTTP(S) URLs
are also accepted. You can load fresh data with `scripts/load-ttl.py` afterward.

### Query the RDF store

```powershell
curl.exe --fail-with-body -H "Accept: application/sparql-results+json" --data-urlencode "query=SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"  "http://localhost:3030/ds/query"
```

### Named graphs

`fill-db.py` loads each ARC into a named graph. Use `GRAPH ?g` to search all
ARC graphs and include the graph IRI in each result. A pattern without `GRAPH`
searches the default graph, which is empty when only ARC named graphs are loaded.

```powershell
curl.exe --fail-with-body -H "Accept: application/sparql-results+json" --data-urlencode "query=SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?s ?p ?o } } LIMIT 10" "http://localhost:3030/ds/query"
```