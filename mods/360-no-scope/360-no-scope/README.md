# 360 No Scope

59 themed guns with matching ammunition, saved magazines, a Gunsmith's Bench, Legendary abilities and positional audio.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 2.4.28 | `>=0.7.5 <0.8.0` | `Steven:360 No Scope` |

## Dependencies

- `Airijko:EndlessLevelingCore` `>=14.4.0 <15.0.0`
- `Config:Endgame&QoL` `>=6.1.4 <7.0.0`
- `Ziggfreed:MMOSkillTree` `>=1.7.4 <2.0.0`
- `org.herolias:SimpleEnchantments` `=1.2.1`
- `Alechilles:Alec's Tamework!` `>=5.9.0 <6.0.0`
- `MAJOR76:MajorDungeons` `>=0.4.15 <0.5.0`

## Build

From the collection root, use Python and JDK 25. Supply your own Hytale server JAR and any compile dependencies below.

```powershell
python build.py mods/360-no-scope/360-no-scope --server-jar PATH_TO_SERVER_JAR --dependency simple-enchantments=PATH_TO_JAR
```

The output is `dist/360-No-Scope-2.4.28.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).

[Third-party notices](THIRD_PARTY_NOTICES.md) · [Collection catalog](../../../README.md).
