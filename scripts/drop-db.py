"""Delete all RDF data in the Fuseki /ds dataset using DROP ALL."""

import argparse
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
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
    except ValueError as exc:
        parser.error(str(exc))
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.path or parsed.query or parsed.fragment):
        parser.error("--host must be a host:port or HTTP(S) URL without a path")
    endpoint = f"{host}/ds/update"

    try:
        request = Request(
            endpoint, data=b"DROP ALL", method="POST",
            headers={"Content-Type": "application/sparql-update"},
        )
        with urlopen(request, timeout=60) as response:
            response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        parser.exit(1, f"Reset failed: HTTP {exc.code} {exc.reason}\n{detail}\n")
    except (OSError, URLError, ValueError) as exc:
        parser.exit(1, f"Reset failed: {exc}\n")
    print(f"Deleted all RDF data from {host}/ds")


if __name__ == "__main__":
    main()
