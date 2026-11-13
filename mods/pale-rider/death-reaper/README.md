# Death Reaper

The Harbinger of the Pale Rider scythe and four Legendary Reaper armor pieces with primary Necromancer affinities.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 0.1.11 | `>=0.7.5 <0.8.0` | `Steven:DeathReaper` |

## Dependencies

- `Airijko:EndlessLevelingCore` `>=14.4.0 <15.0.0`
- `Config:Endgame&QoL` `=6.1.4`

## Build

From the collection root, use Python and JDK 25. Supply your own Hytale server JAR and any compile dependencies below.

```powershell
python build.py mods/pale-rider/death-reaper --server-jar PATH_TO_SERVER_JAR --dependency endless-leveling=PATH_TO_JAR
```

The output is `dist/Death-Reaper-0.1.11.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).

[Audio credits](CREDITS.md).
