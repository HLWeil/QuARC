"""Replace a repository's named graph in Fuseki /ds with a Turtle snapshot."""

import argparse
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "ro-crate-metadata.ttl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", nargs="?", type=Path, default=DEFAULT_INPUT,
        help="Turtle file (default: ro-crate-metadata.ttl in the project root)",
    )
    parser.add_argument(
        "--graph", required=True,
        help="Repository graph IRI (for example, its GitLab URL); replaces only this graph",
    )
    parser.add_argument(
        "--host", default="localhost:3030",
        help="Fuseki host:port or HTTP(S) URL (default: localhost:3030)",
    )
    args = parser.parse_args()
    host = args.host.rstrip("/")
    if "://" not in host:
        host = f"http://{host}"
    try:
        parsed = urlsplit(host)
        parsed.port  # Validate the port when supplied.
        if not urlsplit(args.graph).scheme or any(
                char.isspace() or char in '<>"{}|^`\\' for char in args.graph):
            parser.error("--graph must be an absolute IRI, such as a repository URL")
    except ValueError as exc:
        parser.error(str(exc))
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.path or parsed.query or parsed.fragment):
        parser.error("--host must be a host:port or HTTP(S) URL without a path")
    endpoint = f"{host}/ds/data?{urlencode({'graph': args.graph})}"

    try:
        request = Request(
            endpoint, data=args.input.read_bytes(), method="PUT",
            headers={"Content-Type": "text/turtle"},
        )
        with urlopen(request, timeout=60) as response:
            response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        parser.exit(1, f"Upload failed: HTTP {exc.code} {exc.reason}\n{detail}\n")
    except (OSError, URLError, ValueError) as exc:
        parser.exit(1, f"Upload failed: {exc}\n")
    print(f"Replaced graph {args.graph} at {host}/ds with {args.input}")


if __name__ == "__main__":
    main()
