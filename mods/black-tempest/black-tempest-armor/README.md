# Vestments of the Black Tempest

Three Legendary Mage armor pieces with distinct affinities that complete the storm set.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 0.1.2 | `>=0.7.7 <0.8.0` | `Steven:BlackTempestArmor` |

## Dependencies

- `Airijko:EndlessLevelingCore` `>=14.4.0 <15.0.0`
- `Steven:ABTickleTime` `>=0.4.2 <0.5.0`
- `Config:Endgame&QoL` `=6.1.4`

## Build

From the collection root, use Python and JDK 25. Supply your own Hytale server JAR and any compile dependencies below.

```powershell
python build.py mods/black-tempest/black-tempest-armor --server-jar PATH_TO_SERVER_JAR --dependency endless-leveling=PATH_TO_JAR --dependency abs-tickle-time=PATH_TO_JAR
```

The output is `dist/Black-Tempest-Armor-0.1.2.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).
