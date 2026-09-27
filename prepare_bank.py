"""Verify and unpack the included vocal-bank packs locally; no downloads."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
import zipfile


DEFAULT_BANK = Path(__file__).resolve().parent / "vocal-bank"


def _digest(stream):
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        result.update(chunk)
    return result.hexdigest()


def _file_digest(path):
    with path.open("rb") as stream:
        return _digest(stream)


def _check_destination(root, destination):
    current = root
    for part in destination.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Refusing a symbolic-link destination: {current}")
        if current.exists() and current != destination and not current.is_dir():
            raise ValueError(f"A sample directory is occupied by a file: {current}")


def _target(root, pack_name, item):
    name = item.filename
    parts = name.rstrip("/").split("/")
    if (not name or "\\" in name or "\x00" in name or
            any(part in ("", ".", "..") or ":" in part for part in parts) or
            parts[:2] != ["samples", pack_name] or
            (not item.is_dir() and len(parts) < 3)):
        raise ValueError(f"Unsafe sample archive path: {name!r}")
    file_type = stat.S_IFMT(item.external_attr >> 16)
    if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ValueError(f"Unsupported archive member type (including symlinks): {name}")
    if file_type == stat.S_IFDIR and not item.is_dir():
        raise ValueError(f"Invalid archive directory: {name}")
    if item.is_dir() and item.file_size:
        raise ValueError(f"Archive directory contains data: {name}")
    return root.joinpath(*parts)


def prepare_bank(bank_root=DEFAULT_BANK):
    """Extract missing samples after all packs and existing files pass validation.

    Existing matching samples are left untouched. A changed sample raises an
    error instead of overwriting it. Returns counts for extracted/verified files.
    """
    root = Path(bank_root).resolve()
    manifest = json.loads((root / "packs" / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or type(manifest.get("version")) is not int or manifest["version"] != 1:
        raise ValueError("Unsupported vocal-bank pack manifest version.")
    packs = manifest.get("packs")
    if not isinstance(packs, list) or not packs:
        raise ValueError("The vocal-bank manifest must list its sample packs.")
    pending = []
    seen_packs = set()
    verified = 0
    with ExitStack() as stack:
        for pack in packs:
            if not isinstance(pack, dict):
                raise ValueError("Invalid vocal-bank pack entry.")
            filename = pack.get("file", "")
            if not isinstance(filename, str) or not re.fullmatch(r"[fm][1-9][0-9]*\.zip", filename):
                raise ValueError(f"Invalid sample pack filename: {filename!r}")
            if filename in seen_packs:
                raise ValueError(f"Duplicate sample pack: {filename}")
            seen_packs.add(filename)
            if any(type(pack.get(key)) is not int or pack[key] < 0 for key in ("size", "files", "unpacked_size")):
                raise ValueError(f"Invalid size/count declarations for {filename}")
            checksum = pack.get("sha256", "")
            if not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum):
                raise ValueError(f"Invalid SHA-256 declaration for {filename}")
            archive_path = root / "packs" / filename
            raw = stack.enter_context(archive_path.open("rb"))
            if archive_path.stat().st_size != pack["size"] or _digest(raw) != checksum:
                raise ValueError(f"Sample pack size or SHA-256 mismatch: {filename}")
            raw.seek(0)
            archive = stack.enter_context(zipfile.ZipFile(raw))
            members = archive.infolist()
            files = [item for item in members if not item.is_dir()]
            if len(files) != pack["files"] or sum(item.file_size for item in members) != pack["unpacked_size"]:
                raise ValueError(f"Sample pack file count or unpacked size mismatch: {filename}")
            seen_members = set()
            for item in members:
                destination = _target(root, Path(filename).stem, item)
                # Case folding also protects extraction on Windows filesystems.
                key = str(destination.relative_to(root)).casefold()
                if key in seen_members:
                    raise ValueError(f"Duplicate sample archive member: {item.filename}")
                seen_members.add(key)
                _check_destination(root, destination)
                if item.is_dir():
                    if destination.exists() and not destination.is_dir():
                        raise ValueError(f"Sample directory is occupied: {destination}")
                    continue
                # Reading the complete member validates its ZIP CRC as well.
                with archive.open(item) as stream:
                    digest = _digest(stream)
                if destination.exists():
                    if not destination.is_file() or destination.stat().st_size != item.file_size or _file_digest(destination) != digest:
                        raise ValueError(f"Existing sample differs; preserving your file: {destination}")
                    verified += 1
                else:
                    pending.append((archive, item, destination, digest))
        extracted = 0
        for archive, item, destination, digest in pending:
            _check_destination(root, destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                output = destination.open("xb")
            except FileExistsError:
                # A matching file created after preflight also needs no rewrite.
                if destination.is_file() and _file_digest(destination) == digest:
                    verified += 1
                    continue
                raise ValueError(f"Existing sample differs; preserving your file: {destination}") from None
            try:
                with output, archive.open(item) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        output.write(chunk)
                if _file_digest(destination) != digest:
                    raise ValueError(f"Extracted sample failed verification: {destination}")
            except BaseException:
                destination.unlink(missing_ok=True)
                raise
            extracted += 1
    return {"packs": len(packs), "extracted": extracted, "verified": verified}


def main():
    try:
        result = prepare_bank()
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        print(f"Cannot prepare the recorded vocal bank: {error}", file=sys.stderr)
        return 1
    print(f"Recorded vocal bank ready: {result['extracted']} extracted, "
          f"{result['verified']} verified across {result['packs']} packs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
