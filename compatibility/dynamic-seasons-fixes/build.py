"""Carry the reviewed Dynamic Seasons fixes forward to 7.1.5."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent
VERSION_715_SHA256 = "861daa1f6d76be1f98377ee737bea884b15179622cbfd3f50a16e81b40b36dc1"
CHANGED_CLASSES = {
    "DynamicSeasons/content/interaction/ChangeBlockOptionsInteraction.class",
    "DynamicSeasons/SeasonPlugin.class",
    "DynamicSeasons/system/SeasonWeatherSystem.class",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_714", type=Path)
    parser.add_argument("original_715", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--server-jar", type=Path, required=True, help="Hytale server SDK JAR for verification")
    parser.add_argument("--java", default="java", help="JDK 25 java executable")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path")
    if hashlib.sha256(args.original_715.read_bytes()).hexdigest() != VERSION_715_SHA256:
        parser.error("Use the exact reviewed original Dynamic Seasons 7.1.5 archive")

    with TemporaryDirectory(prefix="seasons-fixes-") as scratch:
        planting = Path(scratch) / "planting.jar"
        patched = Path(scratch) / "weather.jar"
        server = args.server_jar.resolve(strict=True)
        for transform, source, output in (
            ("FixSeasonBlockOptions.java", args.original_714, planting),
            ("FixSeasonOwnership.java", planting, patched),
        ):
            classpath = os.pathsep.join(map(str, (source.resolve(), server)))
            subprocess.run([args.java, "-cp", classpath, str(ROOT / transform), str(source), str(output)], check=True)
        with ZipFile(args.original_714) as previous, ZipFile(args.original_715) as current, ZipFile(patched) as fixes:
            if any(previous.read(name) != current.read(name) for name in CHANGED_CLASSES):
                parser.error("Upstream changed one or more classes targeted by these fixes")
            with ZipFile(args.output, "x") as result:
                for entry in current.infolist():
                    source = fixes if entry.filename in CHANGED_CLASSES else current
                    result.writestr(entry, source.read(entry.filename))
    print(args.output)


if __name__ == "__main__":
    main()
