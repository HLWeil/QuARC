"""Delete a repository's named graph, or explicitly clear the entire Fuseki /ds dataset."""

import argparse
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--graph",
        help="Repository graph IRI to delete (for example, its GitLab URL)",
    )
    target.add_argument(
        "--all", action="store_true",
        help="Delete all RDF data in /ds, including every repository graph",
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
        if args.graph is not None and (not urlsplit(args.graph).scheme or any(
                char.isspace() or char in '<>"{}|^`\\' for char in args.graph)):
            parser.error("--graph must be an absolute IRI, such as a repository URL")
    except ValueError as exc:
        parser.error(str(exc))
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.path or parsed.query or parsed.fragment):
        parser.error("--host must be a host:port or HTTP(S) URL without a path")

    try:
        if args.graph is not None:
            endpoint = f"{host}/ds/data?{urlencode({'graph': args.graph})}"
            request = Request(endpoint, method="DELETE")
        else:
            request = Request(
                f"{host}/ds/update", data=b"DROP ALL", method="POST",
                headers={"Content-Type": "application/sparql-update"},
            )
        with urlopen(request, timeout=60) as response:
            response.read()
    except HTTPError as exc:
        # Deleting an already absent repository graph is a successful no-op.
        if args.graph is not None and exc.code == 404:
            exc.close()
            print(f"Graph {args.graph} is already absent from {host}/ds")
            return
        detail = exc.read().decode("utf-8", errors="replace").strip()
        parser.exit(1, f"Reset failed: HTTP {exc.code} {exc.reason}\n{detail}\n")
    except (OSError, URLError, ValueError) as exc:
        parser.exit(1, f"Reset failed: {exc}\n")
    if args.graph is not None:
        print(f"Deleted graph {args.graph} from {host}/ds")
    else:
        print(f"Deleted all RDF data from {host}/ds")


if __name__ == "__main__":
    main()
