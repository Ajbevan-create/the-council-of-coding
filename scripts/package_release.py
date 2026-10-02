#!/usr/bin/env python3
"""Create portable source/upload ZIPs and their checksum manifests."""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile
import zipfile
from install import VERSION

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {".git", "__pycache__", "target", ".venv", "build", "team-runs",
                 "bridge-inputs", "model-downloads", "skill-backups", "runtime-backups"}
EXCLUDED_FILES = {"SHA256SUMS", "runtime.json", "mcp-config.json", "install-receipt.json", ".DS_Store", "Thumbs.db"}


def sources(root):
    result = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS or part.startswith((".astra-install-", ".runtime-install-")) for part in relative.parts):
            continue
        if path.name in EXCLUDED_FILES or path.suffix in {".pyc", ".pyo", ".gguf", ".part", ".zip", ".exe"}:
            continue
        if path.is_symlink():
            raise ValueError(f"Source symlinks are not packaged: {relative}")
        if path.is_file():
            result.append(path)
    return result


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_manifest(root):
    files = sources(root)
    manifest = root / "SHA256SUMS"
    manifest.write_text("".join(sha256(path) + "  " + path.relative_to(root).as_posix() + "\n" for path in files), encoding="utf-8")
    return files + [manifest]


def write_archive(destination, files, root, prefix=""):
    with tempfile.TemporaryDirectory(prefix=".council-package-", dir=destination.parent) as temporary:
        staged = Path(temporary) / destination.name
        with zipfile.ZipFile(staged, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, prefix + path.relative_to(root).as_posix())
        with zipfile.ZipFile(staged) as archive:
            if archive.testzip() is not None:
                raise ValueError("Archive integrity check failed.")
        os.replace(staged, destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checksums-only", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    options = parser.parse_args(argv)
    if not options.checksums_only and options.output_dir is None:
        parser.error("Choose --checksums-only or supply --output-dir outside the source tree.")
    if options.output_dir is not None and options.output_dir.resolve().is_relative_to(ROOT):
        parser.error("Release output must be outside the source tree.")
    files = write_manifest(ROOT)
    print(f"Checksum manifest: {len(files) - 1} source files")
    if options.checksums_only:
        return 0
    output = options.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    full = output / f"the-council-of-coding-{VERSION}.zip"
    upload = output / "the-council-of-coding-perplexity.zip"
    write_archive(full, files, ROOT, "the-council-of-coding/")
    upload_files = [ROOT / name for name in ["SKILL.md", "references/runtime.md", "references/compatibility.md", "LICENSE", "THIRD_PARTY_NOTICES.md"]]
    write_archive(upload, upload_files, ROOT)
    if upload.stat().st_size >= 10_000_000:
        raise ValueError("Perplexity upload exceeds 10 MB.")
    (output / "SHA256SUMS.txt").write_text("".join(sha256(path) + "  " + path.name + "\n" for path in [full, upload]), encoding="utf-8")
    for archive in [full, upload]:
        print(f"Created {archive.name}: {archive.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        parser_message = f"Packaging stopped: {error}"
        raise SystemExit(parser_message)
