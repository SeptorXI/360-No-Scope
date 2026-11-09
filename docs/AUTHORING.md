# Editing and regeneration

`modules/weapons` and `modules/displays` are the canonical build inputs. Edit Java in `src/java` and game assets in `resources`; `python tools/build.py` builds those inputs directly. The two module manifests keep their original plugin identities and versions.

`publication-manifest.json` records the accepted source artifact hashes and every imported resource and Java source hash. After intentionally changing canonical inputs, review the changes and update their manifest entries. Run `python tools/audit_publication.py` before publishing.

## Editable art

`authoring/ranger-snipers` contains the nine original sniper models, ammunition, Gunsmith's Bench, procedural geometry and reload animation generators. `authoring/360-arsenal` contains the 45 expansion guns and matching ammunition. `authoring/armor-displays` contains the six furniture models. Editable `.bbmodel` and `.scene.json` files are provided alongside original pixel atlases and native exported models/animations; displays also include Blender files. The sniper `reload-baselines` directory preserves the original unrigged models needed by the reload generator.

Open the Blockbench files directly and relink textures from their adjacent `Common` tree if needed. Authoring scripts use Python with Pillow and, for some animation/audio operations, NumPy. Render scripts additionally require Blender. Generated exports must be reviewed and deliberately copied into the corresponding canonical module resources; running an authoring script does not update the canonical module automatically.

## Historical generation tools

The original generation scripts and design specifications are retained for design provenance and further development. They preserve the original sibling project layout under `authoring/`. Some older end-to-end scripts expect earlier release archives, local game assets or research fixtures that are deliberately external to this repository. They are not the supported clean-checkout packaging entry point. Use `tools/build.py` to rebuild the current complete mod without those historical inputs.

Acquisition specifications contain only this project's trade additions and recipes. Third-party merchant inventories and game archives are not bundled. The accepted resources already include the reviewed append patches, Nameless-only merchant routing and current F reload controls.

## Audio

The complete mod resources include the final game-integrated sound clips and their attribution. Audio authoring code and source metadata describe the recorded firearm foundations, mechanical accents and spatial returns. Raw source banks and standalone modified sample packs are excluded. Obtain any required recordings separately from their credited sources and comply with their individual terms. See [third-party notices](../THIRD_PARTY_NOTICES.md).

Optional audio regeneration requires NumPy and FFmpeg plus the hash-matching local inputs described by the source manifests. Paths in publication metadata are relative references to the authoring workspace; recreate those local inputs before using a historical mixer. The default build uses the final committed game clips and requires no recordings or FFmpeg.

Set `FFMPEG` and `FFPROBE` to your installed executables, or place them on `PATH`. Art tools that inspect native attachment interfaces use `HYTALE_ASSETS_ZIP`; the historical material-label resolver also uses `HYTALE_MODS_DIR`. These are local inputs, never repository uploads. Some optional preview render scripts retain Windows font and Blender defaults that you may need to adapt on another platform.
