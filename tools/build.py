#!/usr/bin/env python3
"""Compile and package the curated modules without accessing a live server."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = {
    "weapons": "360-No-Scope",
    "displays": "Armor-Displays",
}
ZIP_DATE = (1980, 1, 1, 0, 0, 0)


class BuildError(RuntimeError):
    pass


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def file_input(value: str | None, label: str) -> Path:
    if not value:
        raise BuildError(f"Provide {label}; external SDK/dependency binaries are not bundled.")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise BuildError(f"{label} is not a file: {path}")
    return path


def find_javac(java_home: str | None) -> Path:
    name = "javac.exe" if os.name == "nt" else "javac"
    if java_home:
        candidate = Path(java_home).expanduser().resolve() / "bin" / name
        if not candidate.is_file():
            raise BuildError(f"No {name} under the supplied Java home: {candidate}")
        return candidate
    discovered = shutil.which("javac")
    if discovered:
        return Path(discovered).resolve()
    raise BuildError("Provide --java-home, set JAVA_HOME, or put JDK 25+ javac on PATH.")


def files_under(directory: Path) -> list[Path]:
    if not directory.is_dir() or directory.is_symlink():
        raise BuildError(f"Missing directory or unsupported symbolic link: {directory}")
    files = []
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise BuildError(f"Symbolic links are not supported in build inputs: {path}")
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(directory).as_posix())


def check_inventory(expected: dict[str, str], actual: dict[str, str], label: str):
    if expected != actual:
        missing = len(expected.keys() - actual.keys())
        extra = len(actual.keys() - expected.keys())
        changed = sum(actual.get(name) != digest for name, digest in expected.items() if name in actual)
        raise BuildError(f"{label} inventory mismatch: {missing} missing, {extra} extra, {changed} changed. Update the reviewed publication inventory for intentional edits.")


def check_publication(module: Path, files: list[Path], sources: list[Path]):
    inventory_path = ROOT / "publication-manifest.json"
    if not inventory_path.is_file():
        return
    inventory = read_json(inventory_path)
    if inventory.get("schema_version") != 1:
        raise BuildError("Unsupported publication manifest schema.")
    record = inventory["modules"][module.name]
    resources = module / "resources"
    if record["resource_root"] != resources.relative_to(ROOT).as_posix():
        raise BuildError(f"Unexpected {module.name} resource_root in publication manifest.")
    expected = {entry["path"]: entry["sha256"].lower() for entry in record["files"]}
    actual = {path.relative_to(resources).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    check_inventory(expected, actual, f"{module.name} resources")
    prefix = (module / "src" / "java").relative_to(ROOT).as_posix() + "/"
    expected_sources = {entry["path"]: entry["sha256"].lower() for entry in inventory["sources"] if entry["path"].startswith(prefix)}
    actual_sources = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    check_inventory(expected_sources, actual_sources, f"{module.name} Java sources")


def validate_resources(module: Path) -> tuple[list[Path], str]:
    resources = module / "resources"
    files = files_under(resources)
    manifest_path = resources / "manifest.json"
    if manifest_path not in files:
        raise BuildError(f"Missing module manifest: {manifest_path}")
    manifest = read_json(manifest_path)
    version = manifest.get("Version", "")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", version):
        raise BuildError(f"Invalid manifest Version in {manifest_path}")
    for path in files:
        relative = path.relative_to(resources)
        if path.suffix.lower() in {".class", ".jar"} or relative.parts[0].upper() == "META-INF":
            raise BuildError(f"Resources must contain assets, not stale runtime classes or dependency archives: {relative}")
    # The root-level runtime profiles are packaged resources, not generated from
    # historical authoring scripts. Both are needed by the current weapons code.
    if module.name == "weapons":
        for name in ("ranger-snipers-reload-profiles.json", "ranger-snipers-owner-tail-profiles.json"):
            if not (resources / name).is_file():
                raise BuildError(f"Required current weapons runtime resource is missing: {name}")
        profiles = read_json(resources / "ranger-snipers-reload-profiles.json")
        if len(profiles.get("Profiles", [])) != 54:
            raise BuildError("Weapons reload profiles must cover all 54 guns.")
    # Curation can pin resource hashes independently of the tool. This optional
    # manifest is strict when present, so missing and unexpected files both fail.
    inventory_path = module / "design" / "resource-manifest.json"
    if inventory_path.is_file():
        inventory = read_json(inventory_path)
        expected = {entry["path"]: entry["sha256"].lower() for entry in inventory["files"]}
        actual = {path.relative_to(resources).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
        check_inventory(expected, actual, f"{module.name} resources")
    return files, version


def fresh_classes(component: str) -> Path:
    # Only this exact repository-local generated directory may be deleted.
    target = ROOT / ".build" / component / "classes"
    for path in (ROOT / ".build", ROOT / ".build" / component, target):
        if path.is_symlink():
            raise BuildError(f"Refusing generated output through a symbolic link: {path}")
    if not target.resolve().is_relative_to(ROOT / ".build"):
        raise BuildError("Generated class output escaped the repository build directory.")
    if target.exists():
        if not target.is_dir():
            raise BuildError(f"Generated class output is not a directory: {target}")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    return target


def write_entry(jar: zipfile.ZipFile, name: str, content: bytes):
    info = zipfile.ZipInfo(name, ZIP_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    jar.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(component: str, javac: Path, server_jar: Path, enchant_jar: Path | None) -> Path:
    module = ROOT / "modules" / component
    resources = module / "resources"
    assets, version = validate_resources(module)
    source_dir = module / "src" / "java"
    sources = [path for path in files_under(source_dir) if path.suffix == ".java"]
    if not sources:
        raise BuildError(f"No Java sources in {source_dir}")
    check_publication(module, assets, sources)
    classes = fresh_classes(component)
    dependencies = [server_jar]
    if component == "weapons":
        if enchant_jar is None:
            raise BuildError("Weapons compilation requires --enchant-jar or SIMPLE_ENCHANTMENTS_JAR.")
        dependencies.append(enchant_jar)
    command = [str(javac), "--release", "25", "-encoding", "UTF-8", "-proc:none",
               "-classpath", os.pathsep.join(map(str, dependencies)), "-d", str(classes), *map(str, sources)]
    print(f"Compiling {component}: {len(sources)} Java sources", flush=True)
    subprocess.run(command, check=True, cwd=ROOT)
    class_files = files_under(classes)
    entries = {path.relative_to(resources).as_posix(): path for path in assets}
    for path in class_files:
        relative = path.relative_to(classes).as_posix()
        if relative in entries:
            raise BuildError(f"Compiled runtime collides with a resource: {relative}")
        entries[relative] = path
    dist = ROOT / "dist"
    if dist.is_symlink():
        raise BuildError("Refusing a symbolic-link dist directory.")
    dist.mkdir(exist_ok=True)
    output = dist / f"{COMPONENTS[component]}-{version}.jar"
    temporary = output.with_suffix(".jar.tmp")
    try:
        with zipfile.ZipFile(temporary, "w") as jar:
            for relative, path in sorted(entries.items()):
                write_entry(jar, relative, path.read_bytes())
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"Built {output.relative_to(ROOT)} ({len(assets)} resources; {len(class_files)} runtime files)")
    print(f"SHA256 {digest}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", choices=("all", *COMPONENTS), default="all")
    parser.add_argument("--server-jar", default=os.environ.get("HYTALE_SERVER_JAR"), help="External HytaleServer.jar (or HYTALE_SERVER_JAR)")
    parser.add_argument("--enchant-jar", default=os.environ.get("SIMPLE_ENCHANTMENTS_JAR"), help="External Simple Enchantments JAR (or SIMPLE_ENCHANTMENTS_JAR); weapons only")
    parser.add_argument("--java-home", default=os.environ.get("JAVA_HOME"), help="JDK 25+ root (or JAVA_HOME); otherwise javac on PATH")
    args = parser.parse_args()
    try:
        selected = list(COMPONENTS) if args.component == "all" else [args.component]
        server_jar = file_input(args.server_jar, "--server-jar / HYTALE_SERVER_JAR")
        enchant_jar = file_input(args.enchant_jar, "--enchant-jar / SIMPLE_ENCHANTMENTS_JAR") if "weapons" in selected else None
        javac = find_javac(args.java_home)
        subprocess.run([str(javac), "-version"], check=True, cwd=ROOT)
        for component in selected:
            build(component, javac, server_jar, enchant_jar)
    except (BuildError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
