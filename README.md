# Hytale Mod Collection

Steven's Hytale projects in one collection. Browse the themed sets to find gear and matching furniture, or go directly to the spell, building and server tools. The version column identifies the selected baseline for each project.

## 360 No Scope

| Project | Version | Description |
| --- | --- | --- |
| [360 No Scope](mods/360-no-scope/360-no-scope/) | 2.4.28 | 59 themed guns with matching ammunition, saved magazines, a Gunsmith's Bench, Legendary abilities and positional audio. |
| [360 Rifle Sentry](mods/360-no-scope/360-rifle-sentry/) | 0.2.9 | Turns the MMOSkillTree Archery sentry into a pulse rifle turret that tracks hostile targets and scales with its owner's combat stats. |
| [Armor Displays](mods/360-no-scope/armor-displays/) | 0.1.10 | Armor stands, single wall holders and vertical gun racks with native inventory storage that preserves equipment metadata. |
| [Arsenal Relics](mods/360-no-scope/arsenal-decor/) | 0.1.4 | Eleven home decorations based on the weapon families, regions and lore of 360 No Scope. |

## Pale Rider

| Project | Version | Description |
| --- | --- | --- |
| [Death Reaper](mods/pale-rider/death-reaper/) | 0.1.11 | The Harbinger of the Pale Rider scythe and four Legendary Reaper armor pieces with primary Necromancer affinities. |
| [Death Lore Decor](mods/pale-rider/death-lore-decor/) | 0.1.4 | Four furnishings inspired by Darksiders II, including a Reaper statue, Well of Souls, Tree of Death and Book of the Dead lectern. |

## Crimson Brotherhood

| Project | Version | Description |
| --- | --- | --- |
| [Oblivion's Tithe](mods/crimson-brotherhood/oblivions-tithe/) | 0.1.5 | Adds The Diddlers, a pair of Legendary reverse-grip daggers with crimson slashes and stacking Daedric Venom. |
| [Crimson Brotherhood Armor](mods/crimson-brotherhood/crimson-brotherhood/) | 0.1.1 | Four Legendary Assassin armor pieces, each with its own attribute bonuses and a design that matches The Diddlers. |
| [Brotherhood Sanctuary Relics](mods/crimson-brotherhood/crimson-brotherhood-decor/) | 0.1.4 | Four furnishings for a Brotherhood sanctuary, including an effigy, altar, banner and reliquary. |

## Black Tempest

| Project | Version | Description |
| --- | --- | --- |
| [AB's Tickle Time](mods/black-tempest/abs-tickle-time/) | 0.4.5 | Legendary gauntlets that channel lightning from bare hands and unleash Storm of Torment. |
| [Vestments of the Black Tempest](mods/black-tempest/black-tempest-armor/) | 0.1.2 | Three Legendary Mage armor pieces with distinct affinities that complete the storm set. |
| [Relics of the Black Tempest](mods/black-tempest/tempest-decor/) | 0.1.5 | A Storm Tyrant monument, Captive Storm Holocron and throne that players can sit on. |

## Spells and building

| Project | Version | Description |
| --- | --- | --- |
| [Charged Meteor](mods/utility/charged-meteor/) | 0.1.7 | A socketed Meteor upgrade that opens a crimson sky vortex and delivers a charged fire impact. |
| [Clear Glass](mods/utility/clear-glass/) | 0.1.2 | Craft clear glass blocks directly from sand and turn them into connecting panes at the Builder's Workbench. |

## Compatibility helpers

These helpers address specific upstream versions. See each project's dependency manifest and build notes before using it on another server.

| Project | Version | Description |
| --- | --- | --- |
| [Endless Leveling Copper Skeleton Fix](compatibility/endless-copper-skeleton/) | 1.0.1 | Restores the melee damage interaction for the Copper Skeleton summon in Endless Leveling. |
| [Endless Menu Acknowledgements](compatibility/endless-menu-acknowledgements/) | 1.0.2 | Handles the tooltip close acknowledgement for the reviewed Endless Leveling menu. |
| [Healing Aura Timing](compatibility/healing-aura-timing/) | 1.0.1 | Repairs Endless Leveling's party healing pulse timing. |
| [Season HUD Left Overlay](compatibility/season-hud-left-overlay/) | 1.0.0 | Moves the Dynamic Seasons HUD left to clear the quest tracker and party panel. |

| Local patch source | Description |
| --- | --- |
| [Dynamic Seasons Planting and Weather Fixes](compatibility/dynamic-seasons-fixes/) | Fixes block-option updates and checks world ownership before applying seasonal weather. |
| [EyeSpy Container Preview Fix](compatibility/eyespy-container-preview/) | Uses the item’s default quality for container previews to avoid an unsupported quality override. |

## Windows server tools

| Project | Description |
| --- | --- |
| [Hytale Server Panel](tools/hytale-server-panel/) | Windows desktop controls for server operation, mods, settings and allowlist management. |
| [Hytale Quiet Mode](tools/hytale-quiet-mode/) | Windows utility that adjusts configured background app priorities while Hytale is active and restores them afterward. |

## Building and installing

Use each project folder for source, assets and build instructions. A project may require a locally supplied Hytale server API, game asset archive or dependency mod. Match those versions to the project's manifest. Server plugins build as JARs and asset packs as ZIPs. The Windows tools run separately from the server's mod loader.

Before installing, back up the server and shut it down normally. Install one version of each selected mod with its dependencies. Restart and rejoin to load the asset packs.

## Source and credits

Each project retains its installed Hytale manifest identifier. [catalog.json](catalog.json) lists the selected versions, dependencies and archive fingerprints. The local release archive copies are ignored by Git. Use [SHA256SUMS](SHA256SUMS) to verify those copies.

This repository started as 360 No Scope. The current weapons and equipment displays are grouped with Rifle Sentry and Arsenal Relics. The original 360 No Scope source and documentation remain in Git history. [Original 360 No Scope snapshot](https://github.com/SeptorXI/Hytale-Mod-Collection/tree/3c62f05e6deaab0ccd5d22327b091271318a686a)

Original project source and assets retain their existing ownership. Third-party dependencies and credited audio keep their own terms. Use original project notices for attribution and obtain external inputs from their respective publishers. Keep raw third-party recordings, vendor archives, server worlds, credentials and local server configuration outside the collection.

## Verification

All 18 mod and helper packages rebuilt with the same archive entry names and file contents as the versions installed on November 13, 2026. Repacked archive checksums can differ because ZIP metadata is regenerated. The two local vendor transforms reproduced the installed patched contents from separately supplied upstream JARs. Both Windows utilities compiled. This verification covers packaging and compilation. It did not include a fresh in-game test.
