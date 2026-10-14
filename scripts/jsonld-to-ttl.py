"""Convert RO-Crate JSON-LD metadata to Turtle for Apache Jena TDB2."""

import argparse
from pathlib import Path
from urllib.parse import urlsplit

from rdflib import Graph


DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "ro-crate-metadata.json"


def convert_to_turtle(source: Path, destination: Path, base_iri: str | None = None) -> int:
    """Expand JSON-LD and write UTF-8 Turtle with absolute resource identifiers."""
    source = source.resolve()
    if source == destination.resolve():
        raise ValueError("Input and output must be different files")
    if base_iri is not None and not urlsplit(base_iri).scheme:
        raise ValueError("The base IRI must be absolute, for example https://example.org/crate/")

    graph = Graph()
    # Using the metadata document as the base resolves './', paths, and '#...' IDs.
    # RDFLib also fetches remote JSON-LD contexts declared by the metadata.
    graph.parse(source=source, format="json-ld", publicID=base_iri or source.as_uri())
    graph.serialize(destination=destination, format="turtle", encoding="utf-8")
    return len(graph)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", nargs="?", type=Path, default=DEFAULT_INPUT,
        help="RO-Crate metadata file (default: ro-crate-metadata.json in the project root)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Turtle output file (default: input filename with .ttl extension)",
    )
    parser.add_argument(
        "--base", dest="base_iri",
        help="Absolute metadata document IRI used to resolve relative IDs; "
             "use a repository-specific base for repository records; "
             "defaults to the input file URI (absolute IDs are unchanged)",
    )
    args = parser.parse_args()
    destination = args.output if args.output is not None else args.input.with_suffix(".ttl")
    try:
        count = convert_to_turtle(args.input, destination, args.base_iri)
    except Exception as exc:
        parser.exit(1, f"Conversion failed: {exc}\n")
    print(f"Wrote {count} RDF triples to {destination}")


if __name__ == "__main__":
    main()
