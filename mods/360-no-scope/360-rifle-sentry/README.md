# 360 Rifle Sentry

Turns the MMOSkillTree Archery sentry into a pulse rifle turret that tracks hostile targets and scales with its owner's combat stats.

| Version | Hytale server range | Mod identifier |
| --- | --- | --- |
| 0.2.9 | `>=0.7.0 <0.8.0` | `Steven:360 Rifle Sentry` |

## Dependencies

- `Ziggfreed:MMOSkillTree` `=1.7.4`
- `Airijko:EndlessLevelingCore` `=14.5.6`

## Build

Run the original builder from this folder with Python and JDK 25 on Windows. Supply Hytale’s `Assets.zip` and the dependency JARs separately. The builder creates the modified spawner and base-model data locally.

```powershell
python build.py --server-jar PATH_TO_SERVER_JAR --assets PATH_TO_ASSETS_ZIP --mmo PATH_TO_MMO_JAR --endless-leveling PATH_TO_ENDLESS_JAR --java-home PATH_TO_JDK_25
```

The output is `dist/360-Rifle-Sentry-0.2.9.jar` under this project. The locally archived server build and its SHA-256 are listed in [project.json](project.json).

[Audio credits](CREDITS.md).
