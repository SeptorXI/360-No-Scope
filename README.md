# 360 No Scope

A themed Hytale armory: **54 guns**, matching ammunition, reload animations, cinematic audio, a five-tier Gunsmith's Bench, armor stands and wall weapon displays.

The arsenal starts with solid-projectile weapons and progresses into mechanical and energy designs tied to the world's regions and dungeons. Legendary weapons have distinct specials and handling tradeoffs. Damage depends on projectile travel, with individual weapon profiles defining the falloff.

This repository contains two independently installable server plugins:

| Module | Version | Includes |
| --- | --- | --- |
| 360 No Scope | 2.0.5 | Nine snipers and nine each of handguns, SMGs, semi-auto rifles, automatic rifles and shotguns; 54 dedicated ammunition types; crafting, trading and enchantment integration |
| Armor Displays | 0.1.0 | Wood-and-iron and metal armor stands, single wall holders and three-weapon wall racks |

**Primary fires, secondary aims, F reloads, and Q activates a Legendary special when available. H remains available for class abilities.** Magazines belong to individual item stacks. Displays store the actual equipment, including its durability, enchantments and loaded-ammunition metadata.

- [Build, dependencies and installation](docs/INSTALL.md)
- [Weapon handling, acquisition and audio](docs/WEAPONS.md)
- [Crafting and using armor stands and racks](docs/DISPLAYS.md)
- [Editable art and asset regeneration](docs/AUTHORING.md)
- [Third-party credits and resource terms](THIRD_PARTY_NOTICES.md)

Runtime Java and pack-ready game resources live under `modules/`. Curated editable art and historical generation tools live under `authoring/`. The normal build packages the committed resources and compiles Java; asset regeneration is a separate workflow.

Build with Python 3, JDK 25 and a locally supplied Hytale server API JAR. The weapons module also needs the SimpleEnchantments 1.2.1 JAR for compilation:

```powershell
python tools/build.py --component all --server-jar 'C:\path\to\HytaleServer.jar' --enchant-jar 'C:\path\to\SimpleEnchantments-1.2.1.jar' --java-home 'C:\path\to\jdk-25'
```

The source and resources are imported from the accepted 2.0.5 weapons and 0.1.0 displays baselines. A fresh source build has its own checksum and validation status. Automated checks do not replace an in-game playtest of aiming, multiplayer behavior, display alignment or audio. Creating or building this repository does not change a server installation.

No blanket open-source license is granted for original project code, art or designs by this repository. Third-party resources retain their own terms and attribution; see the notices above.
