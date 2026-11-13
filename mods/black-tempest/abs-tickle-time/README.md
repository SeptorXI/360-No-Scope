# AB’s Tickle Time

Legendary gauntlets that channel lightning from bare hands and unleash Storm of Torment.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 0.4.5 | `>=0.7.7 <0.8.0` | `Steven:ABTickleTime` |

## Dependencies

- `Airijko:EndlessLevelingCore` `>=14.4.0 <15.0.0`
- `Ziggfreed:MMOSkillTree` `=1.7.4`
- `org.herolias:SimpleEnchantments` `=1.2.1`
- `BlueOrbit:DynamicSeasons` `=7.1.5`
- `Config:Endgame&QoL` `=6.1.4`

## Build

From the collection root, use Python and JDK 25. Supply your own Hytale server JAR and any compile dependencies below.

```powershell
python build.py mods/black-tempest/abs-tickle-time --server-jar PATH_TO_SERVER_JAR --dependency endless-leveling=PATH_TO_JAR --dependency mmo-skill-tree=PATH_TO_JAR --dependency simple-enchantments=PATH_TO_JAR
```

The output is `dist/ABs-Tickle-Time-0.4.5.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).
