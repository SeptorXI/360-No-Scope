# Oblivion’s Tithe

Adds The Diddlers, a pair of Legendary reverse-grip daggers with crimson slashes and stacking Daedric Venom.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 0.1.5 | `>=0.7.5 <0.8.0` | `Steven:OblivionsTithe` |

## Dependencies

- `Airijko:EndlessLevelingCore` `>=14.4.0 <15.0.0`
- `Ziggfreed:MMOSkillTree` `=1.7.4`
- `org.herolias:SimpleEnchantments` `=1.2.1`
- `Config:Endgame&QoL` `>=6.1.4 <7.0.0`

## Build

From the collection root, use Python and JDK 25. Supply your own Hytale server JAR and any compile dependencies below.

```powershell
python build.py mods/crimson-brotherhood/oblivions-tithe --server-jar PATH_TO_SERVER_JAR --dependency mmo-skill-tree=PATH_TO_JAR
```

The output is `dist/Oblivions-Tithe-0.1.5.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).
