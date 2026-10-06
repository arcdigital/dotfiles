#!/usr/bin/env python3
"""Patch licensed fonts without putting originals or glyph assets in public Git."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text())


def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def clean(value):
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\n\r\0"):
        raise ValueError("Expected a nonempty, single-line font name")
    return value


def font_tables(data):
    if data[:4] not in (b"OTTO", b"\x00\x01\x00\x00") or len(data) < 12:
        raise ValueError("Expected an OpenType or TrueType font")
    tables = {}
    count = struct.unpack_from(">H", data, 4)[0]
    if len(data) < 12 + 16 * count:
        raise ValueError("Truncated font table directory")
    for index in range(count):
        tag, _, offset, length = struct.unpack_from(">4sIII", data, 12 + 16 * index)
        if offset + length > len(data) or tag in tables:
            raise ValueError("Font table extends beyond the file")
        tables[tag] = data[offset:offset + length]
    return tables


def font_names(data):
    """Read sfnt name records using the standard library (TTF/OTF, not collections)."""
    tables = font_tables(data)
    names = {}
    for tag, table in tables.items():
        if tag != b"name":
            continue
        _, records, storage = struct.unpack_from(">HHH", table)
        for i in range(records):
            platform_id, _, language, name_id, size, start = struct.unpack_from(">HHHHHH", table, 6 + 12 * i)
            raw = table[storage + start:storage + start + size]
            text = raw.decode("utf-16-be" if platform_id in (0, 3) else "mac_roman").strip()
            # Prefer Unicode/English names over localized alternatives.
            priority = (platform_id in (0, 3), language in (0, 0x409))
            if text and (name_id not in names or priority > names[name_id][0]):
                names[name_id] = (priority, text)
    return {key: value[1] for key, value in names.items()}


def font_metadata(data):
    names = font_names(data)
    family = names.get(16, names.get(1, ""))
    style = names.get(17, names.get(2, ""))
    if not family or not style:
        raise ValueError("Font lacks usable family/style metadata")
    return {"family": family, "style": style}


def font_version(data):
    match = re.search(r"\bVersion\s+(\d+(?:\.\d+)+)\b", font_names(data).get(5, ""), re.IGNORECASE)
    return match.group(1) if match else None


def collection_version(files):
    versions = {font_version(data) for data in files}
    if len(versions) != 1:
        raise ValueError("Do not mix font releases within a collection")
    return versions.pop()


def import_zip(source, destination):
    """Import unchanged licensed fonts privately; never extract arbitrary ZIP paths."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("Licensed fonts belong outside the public repository.")
    if destination.exists() and any(p.name != ".gitkeep" for p in destination.iterdir()):
        raise ValueError("Import into an empty collection directory.")
    files = {}
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            if Path(entry.filename).suffix.lower() not in (".ttf", ".otf") or entry.filename.startswith("__MACOSX/"):
                continue
            name = Path(entry.filename).name
            if name in files:
                raise ValueError("Duplicate font filenames in ZIP")
            files[name] = archive.read(entry)
    if not files:
        raise ValueError("No TTF or OTF font files in ZIP")
    outputs = [{"file": name, "sha256": hashlib.sha256(data).hexdigest(), "metadata": font_metadata(data)} for name, data in sorted(files.items())]
    families = {r["metadata"]["family"] for r in outputs}
    variable = {b"fvar" in font_tables(data) for data in files.values()}
    if len(families) != 1 or len(variable) != 1 or len({r["metadata"]["style"] for r in outputs}) != len(outputs):
        raise ValueError("Expected one family, one format, and distinct styles per collection")
    manifest = {"kind": "variable" if variable.pop() else "static", "font_version": collection_version(files.values()), "family": families.pop(),
                "source_archive": source.name, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "outputs": outputs}
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (destination / name).write_bytes(data)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Imported", len(files), "unchanged fonts:", manifest["family"])


def patch(source, destination, jobs=4):
    if not isinstance(jobs, int) or isinstance(jobs, bool) or jobs < 1:
        raise ValueError("--jobs must be a positive integer.")
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_dir():
        raise ValueError("Input must be a directory containing original .otf or .ttf faces.")
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("Use separate, non-nested input and output directories.")
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("Patched font binaries belong outside the public repository.")
    # A .gitkeep-only destination is allowed for the private repo scaffold.
    if destination.exists() and any(p.name != ".gitkeep" for p in destination.iterdir()):
        raise ValueError("Output must be empty. Regenerate into a new directory, then review/import it.")
    files = sorted(p for p in source.iterdir() if p.suffix.lower() in (".otf", ".ttf") and p.is_file())
    if not files:
        raise ValueError("No .otf or .ttf fonts found in the input directory.")
    if any(b"fvar" in font_tables(p.read_bytes()) for p in files):
        raise ValueError("Variable fonts must not be patched with FontForge. Use the static collection.")
    inputs = [{"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "metadata": font_metadata(p.read_bytes())} for p in files]
    source_version = collection_version(p.read_bytes() for p in files)
    styles = [r["metadata"]["style"] for r in inputs]
    if len(set(styles)) != len(styles) or len({r["metadata"]["family"] for r in inputs}) != 1:
        raise ValueError("Provide one font family, one file per style; choose OTF or TTF, not both.")
    if not shutil.which("docker"):
        raise ValueError("Docker Desktop must be running to regenerate fonts; prepatched font installation does not need Docker.")
    config = read_json(ROOT / "scripts/font-patcher.json")
    requested_image = config["image"]
    run(["docker", "pull", requested_image])
    image = run(["docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", requested_image], stdout=subprocess.PIPE, text=True).stdout.strip()
    if not re.fullmatch(r"nerdfonts/patcher@sha256:[0-9a-f]{64}", image):
        raise ValueError("Docker did not report a usable digest for the official patcher image")
    version = run(["docker", "run", "--rm", "--network=none", "--entrypoint", "fontforge", image, "-script", "/nerd/font-patcher", "--version"], stdout=subprocess.PIPE, text=True).stdout.strip()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.mkdtemp(prefix=".patch-font-", dir=destination.parent)
    try:
        stage = Path(temporary)
        incoming, outgoing = stage / "in", stage / "out"
        incoming.mkdir()
        outgoing.mkdir()
        # Mount only selected inputs, never an entire personal directory.
        for p in files:
            shutil.copy2(p, incoming / p.name)
            (incoming / p.name).chmod(0o600)
        adapter = ROOT / "scripts/font_patcher_names.py"
        parallelism = min(jobs, len(files))
        print(f"Patching {len(files)} faces with {parallelism} parallel jobs. Working files: {stage}", flush=True)
        # The official engine opens inputs r+b for its metrics pass. Only disposable
        # copies are writable; the original collection is never mounted.
        terminal = sys.stdout.isatty()
        command = ('find /in -type f \\( -iname "*.ttf" -o -iname "*.otf" \\) -print0 | '
                   'parallel --null --jobs "$PN" --halt soon,fail=1 ' + ('--bar ' if terminal else '') +
                   '--joblog /out/jobs.tsv fontforge -script /font_patcher_names.py '
                   '--outputdir /out --quiet "$@" {}')
        run(["docker", "run"] + (["-t"] if terminal else []) + ["--rm", "--network=none", "--user", str(os.getuid()) + ":" + str(os.getgid()),
             "-e", "HOME=/tmp", "-e", f"PN={parallelism}", "-v", str(incoming) + ":/in",
             "-v", str(outgoing) + ":/out", "-v", str(adapter) + ":/font_patcher_names.py:ro",
             "--entrypoint", "/bin/sh", image, "-c", command, "patch-font"] + config["flags"])
        generated = sorted(p for p in outgoing.iterdir() if p.suffix.lower() in (".ttf", ".otf") and p.is_file())
        outputs = [{"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "metadata": font_metadata(p.read_bytes())} for p in generated]
        families = {r["metadata"]["family"] for r in outputs}
        if len(outputs) != len(inputs) or sorted(r["metadata"]["style"] for r in outputs) != sorted(styles) or len(families) != 1:
            raise ValueError("Patching did not produce exactly one valid face for every input style.")
        family = families.pop()
        if family == inputs[0]["metadata"]["family"]:
            raise ValueError("Patched family must have a distinct name to coexist with the original")
        if any(b"fvar" in font_tables(p.read_bytes()) for p in generated):
            raise ValueError("Patched output must be static")
        manifest = {"kind": "static-patched", "font_version": source_version, "image_requested": requested_image, "image": image, "patcher_version": version, "flags": config["flags"],
                    "naming_adapter_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(), "jobs": parallelism,
                    "family": family, "inputs": inputs, "outputs": outputs}
        (outgoing / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        # Publish only verified fonts and their manifest. No logs or temporary files.
        destination.mkdir(exist_ok=True)
        for p in generated + [outgoing / "manifest.json"]:
            shutil.copy2(p, destination / p.name)
    except BaseException:
        print("Font patching failed. Working files and job log are preserved at: " + temporary, file=sys.stderr)
        raise
    else:
        shutil.rmtree(temporary)
    print("Patched family:", manifest["family"])
    print("Verified fonts and manifest:", destination)


def validate_fonts(directory):
    manifest = read_json(directory / "manifest.json")
    if "collections" in manifest:
        collections, outputs, pending, filenames, styles, seen = {}, [], [], set(), set(), set()
        for collection in manifest["collections"]:
            name = collection["id"]
            if not re.fullmatch(r"[a-z][a-z0-9-]*", name) or name in seen:
                raise ValueError("Invalid or duplicated font collection id")
            seen.add(name)
            child = directory / name
            if not (child / "manifest.json").is_file() and collection.get("optional"):
                pending.append(name)
                continue
            item = validate_fonts(child)
            collections[name] = item
            for record in item["outputs"]:
                if record["file"] in filenames or (item["family"], record["metadata"]["style"]) in styles:
                    raise ValueError("Installed font names/styles collide across collections")
                filenames.add(record["file"])
                styles.add((item["family"], record["metadata"]["style"]))
                outputs.append(dict(record, source=name + "/" + record["file"]))
        if manifest["default"] not in collections:
            raise ValueError("Default font collection must be present")
        preferred = collections[manifest["default"]]
        return {"family": preferred["family"], "kind": preferred.get("kind", "static"), "outputs": outputs, "pending": pending}
    if not manifest.get("outputs"):
        raise ValueError("The font manifest has no outputs.")
    if manifest.get("kind", "static") not in ("static", "variable", "static-patched"):
        raise ValueError("Unknown font collection kind")
    clean(manifest["family"])
    filenames, styles = set(), set()
    for record in manifest["outputs"]:
        name = record["file"]
        if Path(name).name != name or Path(name).suffix.lower() not in (".otf", ".ttf"):
            raise ValueError("Invalid font filename in manifest")
        data = (directory / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Font checksum mismatch: " + name)
        meta = font_metadata(data)
        if manifest.get("font_version") and manifest.get("kind") != "static-patched" and font_version(data) != manifest["font_version"]:
            raise ValueError("Font release differs from manifest: " + name)
        if meta["family"] != manifest["family"] or meta != record["metadata"]:
            raise ValueError("Font metadata differs from manifest: " + name)
        if name in filenames or meta["style"] in styles:
            raise ValueError("Duplicate font filenames or styles")
        filenames.add(name)
        styles.add(meta["style"])
        if "kind" in manifest and (b"fvar" in font_tables(data)) != (manifest["kind"] == "variable"):
            raise ValueError("Font variation tables do not match the collection kind")
    return manifest


def register_fonts(paths):
    """Make installed files available persistently to macOS applications."""
    if sys.platform != "darwin":
        return
    script = '''ObjC.import('CoreText');
function run(paths) {
    for (var i = 0; i < paths.length; i++) {
        var error = Ref();
        // Scope 2 is persistent registration for the current user.
        if (!$.CTFontManagerRegisterFontsForURL($.NSURL.fileURLWithPath(paths[i]), 2, error)) {
            var code = Number($.CFErrorGetCode(error[0]));
            // Already registered is a successful rerun.
            if (code !== 105) {
                throw new Error('Font registration failed (' + code + '): ' + paths[i]);
            }
        }
    }
}
'''
    run(["/usr/bin/osascript", "-l", "JavaScript", "-", *paths], input=script, text=True)


def install(directory):
    """Explicit font installation; ordinary dotfile linking does not invoke Python."""
    directory = Path(directory).resolve()
    manifest = validate_fonts(directory)
    target_dir = Path.home() / "Library/Fonts"
    for parent in [target_dir, *target_dir.parents]:
        if parent == Path.home():
            break
        if parent.is_symlink():
            raise ValueError("Resolve symlinked font directory first: " + str(parent))
    target_dir.mkdir(parents=True, exist_ok=True)
    for record in manifest["outputs"]:
        source = directory / record.get("source", record["file"])
        target = target_dir / record["file"]
        if target.is_file() and not target.is_symlink() and target.read_bytes() == source.read_bytes():
            continue
        if target.is_dir() and not target.is_symlink():
            raise ValueError("Expected a font file: " + str(target))
        if target.exists() or target.is_symlink():
            from datetime import datetime, timezone
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            backup = target.with_name(target.name + ".dotbot-backup." + stamp)
            target.rename(backup)
            print("Font backup:", backup)
        shutil.copy2(source, target)
    # Register unchanged files too, so a rerun repairs missing font activation.
    register_fonts([target_dir / record["file"] for record in manifest["outputs"]])
    print("Installed", len(manifest["outputs"]), "fonts. Optional pending:", ", ".join(manifest.get("pending", [])) or "none")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--import-zip", action="store_true", help="Import originals unchanged")
    parser.add_argument("--jobs", type=int, help="Parallel font patching jobs (default: 4)")
    parser.add_argument("--install", type=Path, help="Validate/copy private fonts into ~/Library/Fonts")
    args = parser.parse_args()
    try:
        if args.install:
            if args.input or args.output or args.import_zip or args.jobs is not None:
                parser.error("Use --install separately")
            install(args.install)
        else:
            if not args.input or not args.output:
                parser.error("--input and --output are required")
            if args.import_zip:
                if args.jobs is not None:
                    parser.error("--jobs applies only to patching")
                import_zip(args.input, args.output)
            else:
                patch(args.input, args.output, jobs=4 if args.jobs is None else args.jobs)
    except (ValueError, OSError, struct.error, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        parser.exit(1, "Font operation failed: " + str(error) + "\n")


if __name__ == "__main__":
    main()
