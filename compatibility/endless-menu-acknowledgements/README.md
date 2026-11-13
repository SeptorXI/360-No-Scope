# Endless Menu Acknowledgements

Handles the tooltip close acknowledgement for the reviewed Endless Leveling menu.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 1.0.2 | `>=0.7.7 <0.7.8` | `Local:EndlessMenuAcknowledgements` |

## Dependencies

- `Airijko:EndlessLevelingCore` `=14.5.6`

## Build

From the collection root, use Python and JDK 25. Supply your own Hytale server JAR and any compile dependencies below.

```powershell
python build.py compatibility/endless-menu-acknowledgements --server-jar PATH_TO_SERVER_JAR --dependency endless-leveling=PATH_TO_JAR
```

The output is `dist/Endless-Menu-Acknowledgements-1.0.2.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).
