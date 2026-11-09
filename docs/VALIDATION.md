# Repository import validation

Validated on 2026-11-09 using JDK 25.0.5, the local Hytale server API and SimpleEnchantments 1.2.1.

Both modules compiled successfully from the canonical repository sources. Every rebuilt archive entry matched the corresponding accepted release entry byte-for-byte: 2,698 resource files and 28 classes for weapons; 36 resource files and 13 classes for displays. No entries were missing, extra or changed. Rebuilding twice produced identical archive hashes with the portable builder's fixed ZIP metadata.

| Output | Rebuilt SHA-256 |
| --- | --- |
| `360-No-Scope-2.0.5.jar` | `253f5bea886c4c8af06297fb653654826560132033cb82de3b03bcc223835bdf` |
| `Armor-Displays-0.1.0.jar` | `ff95e318ce4e54175b4c278fb88c0484f82184307833c47c7da57e4965245134` |

The offline publication audit verified all 54 weapons, 54 active ammunition types, six displays, 533 mono 48 kHz sound clips, 292 sound events, icons, descriptions, damage-falloff curves, owner-return mappings and the complete canonical source/resource inventory. The indexed files were also checked for forbidden publication paths, raw audio banks, dependency binaries and common credential formats.

Re-run `python tools/audit_publication.py` after staging intended changes. Re-run `python tools/build.py --component all` with the external SDK paths to reproduce the build checks. The accepted release fingerprints are recorded separately in `publication-manifest.json`.

These import checks did not launch or modify the production server and did not add a new multiplayer or client playtest. See [installation and baseline test scope](INSTALL.md) for the earlier native fixture coverage and remaining in-game checks.
