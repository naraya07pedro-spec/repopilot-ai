"""Verify reference boot media on D:. Does not install, extract, execute or boot it.

Only --download permits network/payload writes. Existing files are never overwritten;
an interrupted/corrupt download is retained under its unique .partial filename.
This is NOT a worker image builder or a signature/boot attestation.
"""

import argparse
import hashlib
import json
import os
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path("D:/Projects/repopilot-local/hyperv-worker/media")
NAME = "alpine-virt-3.24.3-x86_64.iso"
SIZE = 70254592
SHA256 = "cdc1bc0efc64d8d611bf3733f54868172a545888dfd726f518bf279bcb0ff1af"
URL = "https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/x86_64/" + NAME


class SameOrigin(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith("https://dl-cdn.alpinelinux.org/alpine/"):
            raise ValueError("media_redirect_origin_changed")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def checked_root() -> Path:
    if os.name != "nt":
        raise ValueError("windows_D_drive_required")
    for part in (ROOT, *ROOT.parents):
        if (part.exists() and part.is_junction()) or part.is_symlink():
            raise ValueError("media_path_reparse_point")
    if ROOT.resolve() != ROOT:
        raise ValueError("media_path_changed")
    return ROOT


def verify(path: Path) -> dict:
    if path.stat().st_size != SIZE:
        raise ValueError("reference_media_size_mismatch")
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != SHA256:
        raise ValueError("reference_media_sha256_mismatch")
    return {
        "path": str(path),
        "bytes": SIZE,
        "sha256": actual,
        "publisher_url": URL,
        "integrity": "matches_pinned_publisher_SHA256_not_PGP_signature_verification",
        "worker_image_built": False,
        "boot_tested": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = checked_root()
    final = root / NAME
    if final.exists():
        print(json.dumps(verify(final)))
        return
    if not args.download:
        print(json.dumps({"status": "absent", "downloaded": False, "url": URL}))
        return
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), SameOrigin())
    with opener.open(URL + ".sha256", timeout=10) as response:
        checksum = response.read(4097).decode("ascii").strip()
    if checksum.split() != [SHA256, NAME]:
        raise ValueError("publisher_checksum_changed")
    root.mkdir(parents=True, exist_ok=True)
    existing_bytes = sum(p.stat().st_size for p in root.iterdir() if p.is_file())
    if existing_bytes + SIZE > 192 * 1048576:
        raise ValueError("media_directory_budget_exceeded_preserve_existing_files")
    partial = root / (NAME + "." + uuid.uuid4().hex + ".partial")
    started = time.monotonic()
    # Exclusive output, socket timeout, elapsed bound, exact byte cap; no retries/deletion.
    with partial.open("xb") as output, opener.open(URL, timeout=10) as response:
        if int(response.headers.get("Content-Length", "-1")) != SIZE:
            raise ValueError("media_content_length_changed")
        count = 0
        while block := response.read(262144):
            count += len(block)
            if count > SIZE or time.monotonic() - started > 600:
                raise ValueError("media_download_budget_exceeded")
            output.write(block)
        output.flush()
        os.fsync(output.fileno())
    verify(partial)
    partial.rename(final)  # Windows rename refuses an existing destination.
    result = verify(final)
    result["publisher_checksum_rechecked"] = True
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
