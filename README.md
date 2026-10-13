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

### Convert RO-Crate metadata to Turtle

Download e.g. https://git.nfdi4plants.org/brilator/Facultative-CAM-in-Talinum/-/package_files/89873/download, copy into this folder and rename to `ro-crate-metadata.json`. Then run:

```
uv run .\rdf-tools.py
```

This writes `ro-crate-metadata.ttl`. RDFLib reads the JSON-LD context and
preserves RDF types, links, literals, and the inline vocabulary extensions.
Internet access is needed to retrieve remote contexts such as the RO-Crate 1.1
context used by the example metadata.

For portable resource identifiers, specify the metadata document's absolute IRI:

```powershell
uv run rdf-tools.py ro-crate-metadata.json -o crate.ttl --base https://example.org/crate/ro-crate-metadata.json
```

Relative IDs such as `./`, file paths, and `#fragment` are resolved against this
IRI. Without `--base`, they use the input file's absolute `file:` URI. Turtle is
written as UTF-8 with absolute resource identifiers.

### Load the Turtle into Apache Jena Fuseki

Load the Turtle into Apache Jena TDB2 using the Jena binary distribution:

```powershell
tdb2_tdbloader --loc DB ro-crate-metadata.ttl
```

On Linux/macOS the command is `tdb2.tdbloader`. To load into a named graph,
add `--graph=https://example.org/graph`. See the
[Jena TDB2 command-line documentation](https://jena.apache.org/documentation/tdb2/tdb2_cmds.html).
