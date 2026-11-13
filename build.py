"""Build a curated Hytale mod from its source and separately supplied dependencies."""

import argparse
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parent


def build(project, server_jar, dependencies, javac):
    record = json.loads((project / "project.json").read_text(encoding="utf-8"))
    resources = project / "resources"
    with (resources / "manifest.json").open(encoding="utf-8-sig") as stream:
        manifest = json.load(stream)
    if manifest["Version"] != record["version"]:
        raise ValueError("Project and mod manifest versions differ")

    assets = {
        path.relative_to(resources).as_posix(): path
        for path in resources.rglob("*") if path.is_file()
    }
    sources = sorted((project / "src").rglob("*.java"))
    with TemporaryDirectory(prefix="hytale-build-") as scratch:
        classes = Path(scratch) / "classes"
        classes.mkdir()
        if manifest.get("Main"):
            expected = record["compile_dependencies"]
            missing = set(expected) - dependencies.keys()
            if not server_jar or missing or not sources:
                raise ValueError(f"This plugin needs Java sources, --server-jar and these missing dependencies: {sorted(missing)}")
            classpath = [server_jar.resolve(strict=True)]
            classpath.extend(dependencies[key].resolve(strict=True) for key in expected)
            subprocess.run([
                javac, "--release", "25", "-encoding", "UTF-8", "-proc:none",
                "-cp", os.pathsep.join(map(str, classpath)), "-d", str(classes),
                *map(str, sources),
            ], check=True)
            for path in classes.rglob("*.class"):
                name = path.relative_to(classes).as_posix()
                if name in assets:
                    raise ValueError(f"Class path collides with a resource: {name}")
                assets[name] = path

        output = project / "dist" / record["artifact"]
        output.parent.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=output.parent, prefix="build-") as staging:
            candidate = Path(staging) / output.name
            with ZipFile(candidate, "x", compression=ZIP_DEFLATED, compresslevel=9) as archive:
                for name, path in sorted(assets.items()):
                    entry = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    archive.writestr(entry, path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
            with ZipFile(candidate) as archive:
                if archive.testzip() is not None:
                    raise ValueError("Archive integrity check failed")
            candidate.replace(output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Project folder relative to the collection root")
    parser.add_argument("--server-jar", type=Path, help="Hytale server SDK JAR")
    parser.add_argument("--dependency", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--javac", default="javac", help="JDK 25 compiler")
    args = parser.parse_args()
    project = (ROOT / args.project).resolve()
    if not project.is_relative_to(ROOT) or not (project / "project.json").is_file():
        parser.error("Select a project folder inside the collection")
    dependencies = {}
    for definition in args.dependency:
        name, separator, path = definition.partition("=")
        if not separator or not name or not path or name in dependencies:
            parser.error(f"Expected a unique NAME=PATH dependency: {definition}")
        dependencies[name] = Path(path)
    try:
        print(build(project, args.server_jar, dependencies, args.javac))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Build failed: {error}\n")


if __name__ == "__main__":
    main()
