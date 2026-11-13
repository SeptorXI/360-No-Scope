# Charged Meteor

A socketed Meteor upgrade that opens a crimson sky vortex and delivers a charged fire impact.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 0.1.7 | `>=0.7.7 <0.8.0` | `Steven:ChargedMeteor` |

## Dependencies

- `Config:Endgame&QoL` `=6.1.4`
- `Alechilles:Alec's Tamework!` `>=5.9.0 <6.0.0`

## Build

From the collection root, use Python and JDK 25. Supply your own Hytale server JAR and any compile dependencies below.

```powershell
python build.py mods/utility/charged-meteor --server-jar PATH_TO_SERVER_JAR --dependency endgame-qol=PATH_TO_JAR --dependency alecs-tamework=PATH_TO_JAR
```

The output is `dist/Charged-Meteor-0.1.7.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).
