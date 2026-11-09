# Build and install

This repository contains two separately loadable plugins:

| Component | Build output | Purpose |
| --- | --- | --- |
| Weapons | `dist/360-No-Scope-2.0.5.jar` | 54 guns, dedicated ammunition, persistent magazines and Gunsmith crafting |
| Displays | `dist/Armor-Displays-0.1.0.jar` | Armor stands, wall weapon holders and wall racks |

Install either component or both. Armor Displays can display native weapons without the weapons component. Keep the two JARs separate: each has its own plugin entry point, and merging their ZIP contents does not initialize both plugins.

## Build from source

Use **Python 3 and JDK 25**. Supply your own legally obtained Hytale server API JAR. Building weapons also requires a local **SimpleEnchantments 1.2.1** JAR. These SDK/dependency binaries are external inputs and are not included in the repository.

From the repository root, set the local paths and build both components:

```powershell
$env:HYTALE_SERVER_JAR = 'C:\path\to\HytaleServer.jar'
$env:SIMPLE_ENCHANTMENTS_JAR = 'C:\path\to\SimpleEnchantments-1.2.1.jar'
$env:JAVA_HOME = 'C:\path\to\jdk-25'
python tools/build.py --component all
```

The equivalent explicit options are:

```powershell
python tools/build.py --component all --server-jar 'C:\path\to\HytaleServer.jar' --enchant-jar 'C:\path\to\SimpleEnchantments-1.2.1.jar' --java-home 'C:\path\to\jdk-25'
```

Use `--component weapons` or `--component displays` to build one plugin. A displays-only build does not require the enchantment JAR.

Normal packaging uses Python's standard library, compiles the Java source and packages committed resource files. It does not require Pillow, Blender, FFmpeg, downloaded raw audio packs or historical authoring workspaces. Optional asset regeneration has separate authoring requirements. Compiling does not require a server login, authentication files, player data or production configuration.

## Server requirements

Both manifests declare Hytale server compatibility **`>=0.7.5 <0.8.0`** and require the native Item and Interaction modules. Use a compatible server build and validate against your actual installed dependency versions.

The weapons manifest additionally requires:

| Plugin | Version range |
| --- | --- |
| Endless Leveling Core | `>=14.4.0 <15.0.0` |
| Endgame & QoL | `>=6.1.4 <7.0.0` |
| MMO Skill Tree | `>=1.7.4 <2.0.0` |
| SimpleEnchantments | exactly `1.2.1` |
| Alec's Tamework! | `>=5.9.0 <6.0.0` |
| MajorDungeons | `>=0.4.15 <0.5.0` |

The weapons content also uses **Fullmetal Labyrinth `>=1.11.4 <2.0.0`** and **Tritale - Echoes of Hyrule `>=1.0.8 <2.0.0`** for materials, benches and merchants. Install their required dependencies too. These content packs are listed separately from Java plugin dependencies in `ranger-snipers-content-requirements.json`; they remain necessary to the authored progression.

Armor Displays has no dependency on these third-party mods or on the weapons plugin.

## Install on a server

1. Schedule a normal shutdown and back up the server's worlds, player data, mods and configuration.
2. With the server stopped, copy the selected installable JAR or JARs from `dist/` into that server's `mods/` directory. Install the weapons dependencies if selecting that component.
3. Replace older copies of the same plugin so only one version of each is installed. Do not install build intermediates or QA probe JARs.
4. Start the server and check its log for successful plugin and asset loading. Rejoin so the client receives the selected asset packs.
5. For displays, craft at **Furniture Workbench → Storage** and use the configured native Use binding. See [Armor Displays](DISPLAYS.md) for placement and slot order. For weapons, use the Gunsmith progression and the corresponding ammunition. **F reloads**, secondary aims, and **Q** uses an available Legendary special; **H** remains available for class abilities. See [weapon handling](WEAPONS.md).

These are installation instructions, not an installer. Repository creation and source builds leave the current running server unchanged.

## Baseline identity and test scope

The repository imports these accepted source/resource baselines:

| Artifact | SHA-256 |
| --- | --- |
| `360-No-Scope-2.0.5.jar` | `cc2399a1d298729bbbad1edc49e14223465da87ec242b727949eb4419b22fe9d` |
| `Armor-Displays-0.1.0.jar` | `e5265db3dc846180d4965266044bc36379cb898aab6910f132bf406c516ce7dc` |

Baseline hashes identify the imported artifacts; they are not a promise that a fresh compilation will be byte-identical. Read the validation reports for the artifact actually built or installed. The imported weapons baseline passed 15,124 native checks and 33 owner-return launch/packet checks; these do not establish client aiming, multiplayer handling or headphone listening quality. Armor Displays' baseline passed 3,929 static and 7,261 isolated native checks with zero recorded fixture failures; real client interaction and multiplayer behavior remain outside that test scope. Building both components together also does not establish that every future server or third-party mod version is compatible.

Keep native server/game archives, dependency JARs, authentication files, copied production configurations, player data and test worlds outside the public repository. No credentials or live server configuration are required to build these plugins.
