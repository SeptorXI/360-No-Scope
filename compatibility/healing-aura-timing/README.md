# Healing Aura Timing

Repairs Endless Leveling's party healing pulse timing.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 1.0.1 | `>=0.7.0 <0.8.0` | `Local:HealingAuraTiming` |

## Dependencies

- `Airijko:EndlessLevelingCore` `=14.5.6`

## Build

From the collection root, use Python and JDK 25. Supply your own Hytale server JAR and any compile dependencies below.

```powershell
python build.py compatibility/healing-aura-timing --server-jar PATH_TO_SERVER_JAR --dependency endless-leveling=PATH_TO_JAR
```

The output is `dist/HealingAuraTiming-1.0.1.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).
