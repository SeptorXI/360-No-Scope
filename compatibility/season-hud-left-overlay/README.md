# Season HUD Left Overlay

Moves the Dynamic Seasons HUD left to clear the quest tracker and party panel.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 1.0.0 | `>=0.7.0 <0.8.0` | `Steven:SeasonHUDLeftOverlay` |

## Dependencies

- `BlueOrbit:DynamicSeasons` `>=7.1.4`

## Build

Run `python build.py PATH_TO_DYNAMIC_SEASONS_JAR` from this folder. The reviewed versions are 7.1.4 and 7.1.5. The script applies the anchor change to your own copy of the upstream HUD and writes the overlay to `dist/`.

The output is `dist/SeasonHUD-LeftOverlay-1.0.0.zip` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).
