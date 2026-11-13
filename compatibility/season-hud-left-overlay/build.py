"""Build the HUD overlay from a local Dynamic Seasons 7.1.4 or 7.1.5 JAR."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
HUD = "Common/UI/Custom/Hud/SeasonsHUD.ui"
OLD_ANCHOR = b"Anchor: (Width: 96, Height: 320, Right: 0, Bottom: 250);"
NEW_ANCHOR = b"Anchor: (Width: 96, Height: 320, Left: 12, Bottom: 250);"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dynamic_seasons", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/SeasonHUD-LeftOverlay-1.0.0.zip")
    args = parser.parse_args()
    with ZipFile(args.dynamic_seasons) as upstream:
        manifest = json.loads(upstream.read("manifest.json"))
        if manifest.get("Group") != "BlueOrbit" or manifest.get("Name") != "DynamicSeasons":
            parser.error("Expected the Dynamic Seasons mod archive")
        if manifest.get("Version") not in {"7.1.4", "7.1.5"}:
            parser.error("Use a reviewed version of Dynamic Seasons, 7.1.4 or 7.1.5")
        hud = upstream.read(HUD)
        if hud.count(OLD_ANCHOR) != 1:
            parser.error("Could not find exactly one matching HUD anchor")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "x", compression=ZIP_DEFLATED) as overlay:
        overlay.write(ROOT / "manifest.json", "manifest.json")
        overlay.writestr(HUD, hud.replace(OLD_ANCHOR, NEW_ANCHOR))
    print(args.output)


if __name__ == "__main__":
    main()
