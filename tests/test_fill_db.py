"""Exercise the batch with offline JSON-LD and a local Graph Store HTTP endpoint."""

import asyncio
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

from datahub_client.py.Models.errors import NotFoundError
from rdflib import Graph, Literal, URIRef


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fill-db.py"
spec = importlib.util.spec_from_file_location("fill_db", SCRIPT)
fill_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fill_db)

CRATE = json.dumps({
    "@context": {"name": "http://schema.org/name"},
    "@graph": [{"@id": "./", "name": "Test crate ä"}],
}, ensure_ascii=False)


class GraphStoreHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.download_requests.append(self.path)
        if self.path.startswith("/api/v4/projects/"):
            self.send_response(302)
            self.send_header("Location", "/redirected-ro-crate")
            self.end_headers()
        elif self.path == "/redirected-ro-crate":
            body = CRATE.encode("utf-8")
            self.send_response(self.server.download_status)
            self.send_header("Content-Type", "application/ld+json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        graph = parse_qs(urlsplit(self.path).query)["graph"][0]
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.uploads.append((self.path, graph, self.headers["Content-Type"], body))
        self.send_response(503 if graph == self.server.reject_graph else 204)
        self.end_headers()

    def log_message(self, *args):
        pass


class FillDbTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output_dir = Path(self.directory.name)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), GraphStoreHandler)
        self.server.uploads = []
        self.server.reject_graph = None
        self.server.download_requests = []
        self.server.download_status = 200
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.host = f"127.0.0.1:{self.server.server_port}"

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_batch(self, downloads):
        output = io.StringIO()
        download = AsyncMock(side_effect=downloads)
        client = SimpleNamespace(Packages=SimpleNamespace(DownloadROCrateAsync=download))
        with patch.object(fill_db, "dc", client), redirect_stdout(output):
            status = asyncio.run(fill_db.main([1040, 122], self.host, self.output_dir))
        self.assertEqual([call.args[0] for call in download.await_args_list], [1040, 122])
        return status, output.getvalue()

    def test_download_convert_and_upload_separate_named_graphs(self):
        status, output = self.run_batch([CRATE, CRATE])
        self.assertEqual(status, 0)
        self.assertIn("2 succeeded, 0 failed", output)
        self.assertEqual(len(self.server.uploads), 2)
        for arc_id, (path, graph_iri, content_type, body) in zip([1040, 122], self.server.uploads):
            expected_iri = f"{fill_db.base_url.rstrip('/')}/{arc_id}"
            self.assertEqual(urlsplit(path).path, "/ds/data")
            self.assertEqual(graph_iri, expected_iri)
            self.assertEqual(content_type, "text/turtle")
            graph = Graph().parse(data=body.decode("utf-8"), format="turtle")
            self.assertIn((
                URIRef(f"{expected_iri}/"), URIRef("http://schema.org/name"),
                Literal("Test crate ä"),
            ), graph)
            self.assertEqual((self.output_dir / f"ro-crate-metadata-{arc_id}.json").read_text(
                encoding="utf-8",
            ), CRATE)
            self.assertTrue((self.output_dir / f"ro-crate-metadata-{arc_id}.ttl").is_file())
            self.assertIn(f"ARC {arc_id}] 3/3", output)

    def test_download_failure_skips_conversion_and_continues(self):
        status, output = self.run_batch([RuntimeError("Download unavailable"), CRATE])
        self.assertEqual(status, 1)
        self.assertIn("FAILED during download: Download unavailable", output)
        self.assertIn("1 succeeded, 1 failed", output)
        self.assertFalse((self.output_dir / "ro-crate-metadata-1040.json").exists())
        self.assertEqual([upload[1] for upload in self.server.uploads], [
            f"{fill_db.base_url.rstrip('/')}/122",
        ])

    def test_conversion_failure_skips_upload_and_continues(self):
        status, output = self.run_batch(["invalid JSON", CRATE])
        self.assertEqual(status, 1)
        self.assertIn("FAILED during conversion", output)
        self.assertIn("Failed ARC IDs: 1040", output)
        self.assertEqual([upload[1] for upload in self.server.uploads], [
            f"{fill_db.base_url.rstrip('/')}/122",
        ])

    def test_upload_failure_is_reported_and_next_arc_is_loaded(self):
        self.server.reject_graph = f"{fill_db.base_url.rstrip('/')}/1040"
        status, output = self.run_batch([CRATE, CRATE])
        self.assertEqual(status, 1)
        self.assertIn("FAILED during upload", output)
        self.assertIn("1 succeeded, 1 failed", output)
        self.assertEqual(len(self.server.uploads), 2)

    def redirect_client(self):
        client = fill_db.DataHubClient(f"http://{self.host}", fill_db.Authentication.Anonymous())
        client.Http = fill_db.RedirectHttpClient()
        return client

    def test_real_datahub_client_follows_302_and_finishes_batch(self):
        output = io.StringIO()
        with patch.object(fill_db, "dc", self.redirect_client()), redirect_stdout(output):
            status = asyncio.run(fill_db.main([1040], self.host, self.output_dir))
        self.assertEqual(status, 0, output.getvalue())
        self.assertIn("1 succeeded, 0 failed", output.getvalue())
        self.assertEqual(self.server.download_requests, [
            "/api/v4/projects/1040/packages/generic/isa_arc_json/0.0.1/arc-ro-crate-metadata.json",
            "/redirected-ro-crate",
        ])
        self.assertEqual((self.output_dir / "ro-crate-metadata-1040.json").read_text(
            encoding="utf-8",
        ), CRATE)
        self.assertEqual(len(self.server.uploads), 1)

    def test_error_after_redirect_is_reported_without_saving_file(self):
        self.server.download_status = 404
        destination = self.output_dir / "failed.json"
        with patch.object(fill_db, "dc", self.redirect_client()):
            with self.assertRaises(NotFoundError) as error:
                asyncio.run(fill_db.download_ro_crate(1040, destination))
        self.assertEqual(error.exception.StatusCode, 404)
        self.assertEqual(len(self.server.download_requests), 2)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
