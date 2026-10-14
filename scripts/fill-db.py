"""Download ARC RO-Crates, convert to Turtle, and replace their Fuseki named graphs."""

import argparse
import asyncio
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import httpx
from datahub_client import DataHubClient, Authentication
from datahub_client.py.Http.http_request import HttpRequest
from datahub_client.py.Http.http_response import HttpResponse
from fable_library.async_ import await_task
from fable_library.async_builder import Async, singleton


class RedirectHttpClient:
    """Adapt redirect-enabled HTTPX requests to DataHubClient's Fable async API."""

    def SendAsync(self, request: HttpRequest) -> Async[HttpResponse]:
        async def send() -> HttpResponse:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
                response = await client.request(
                    request.Method, request.Url,
                    headers=request.Headers, content=request.Body,
                )
                return HttpResponse(
                    status_code=response.status_code, body=response.text,
                    headers=list(response.headers.items()),
                )

        # SendAsync must return a Fable computation, rather than a Python coroutine.
        return singleton.Delay(lambda: await_task(send()))


db_host = "localhost:3030"
base_url = "https://git.nfdi4plants.org/"
arc_ids = [1040, 122, 3507, 4020]
dc = DataHubClient(base_url, Authentication.Anonymous())
dc.Http = RedirectHttpClient()

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "tmp"


async def download_ro_crate(arc_id: int, destination: Path) -> None:
    pkg = await dc.Packages.DownloadROCrateAsync(arc_id)
    destination.write_text(pkg, encoding="utf-8")


def run_script(script: str, *args: str) -> None:
    # Reuse the current environment and show the child script's output immediately.
    subprocess.run(
        [sys.executable, "-u", str(SCRIPT_DIR / script), *args], check=True,
    )


async def main(
    ids: list[int], host: str = db_host, output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> int:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    failed = []
    print(f"Processing {len(ids)} ARC(s) into Fuseki at {host}/ds", flush=True)

    for index, arc_id in enumerate(ids, start=1):
        prefix = f"[{index}/{len(ids)} ARC {arc_id}]"
        graph_iri = f"{base_url.rstrip('/')}/{arc_id}"
        json_path = output_dir / f"ro-crate-metadata-{arc_id}.json"
        ttl_path = json_path.with_suffix(".ttl")
        arc_started = perf_counter()
        step = "download"
        try:
            print(f"{prefix} 1/3 Downloading RO-Crate...", flush=True)
            await download_ro_crate(arc_id, json_path)
            print(f"{prefix} Saved JSON-LD to {json_path}", flush=True)

            step = "conversion"
            print(f"{prefix} 2/3 Converting JSON-LD to Turtle...", flush=True)
            run_script(
                "jsonld-to-ttl.py", str(json_path), "--output", str(ttl_path),
                "--base", f"{graph_iri}/ro-crate-metadata.json",
            )

            step = "upload"
            print(f"{prefix} 3/3 Loading Turtle into graph {graph_iri}...", flush=True)
            run_script(
                "load-ttl.py", str(ttl_path), "--graph", graph_iri, "--host", host,
            )
        except Exception as exc:
            failed.append(arc_id)
            print(f"{prefix} FAILED during {step}: {exc}", flush=True)
            continue

        print(f"{prefix} Done in {perf_counter() - arc_started:.1f}s", flush=True)

    print(
        f"Finished in {perf_counter() - started:.1f}s: "
        f"{len(ids) - len(failed)} succeeded, {len(failed)} failed.",
        flush=True,
    )
    if failed:
        print(f"Failed ARC IDs: {', '.join(map(str, failed))}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "arc_ids", nargs="*", type=int, default=arc_ids,
        help="ARC IDs to process (default: the arc_ids list in this script)",
    )
    parser.add_argument("--host", default=db_host, help="Fuseki host:port or HTTP(S) URL")
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="Directory for downloaded JSON-LD and Turtle files (default: project-root tmp directory)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.arc_ids, args.host, args.output_dir)))
