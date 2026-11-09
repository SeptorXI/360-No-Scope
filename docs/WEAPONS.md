# Weapons and ammunition

360 No Scope 2.0.5 contains 54 guns: nine snipers plus nine each of handguns, SMGs, semi-auto rifles, automatic rifles and shotguns. Every gun has its own matching ammunition type. Three older ammunition IDs remain for compatibility; they are not additional active weapon families.

## Controls

| Action | Control |
| --- | --- |
| Fire handgun, sniper, semi-auto rifle or shotgun | Primary attack |
| Fire SMG or automatic rifle | Hold primary attack |
| Aim | Secondary attack |
| Reload manually | **F** |
| Use a Legendary special, when available | **Q** |
| Class abilities | **H remains available** |

Use ammunition that names the gun it fits. Ballistic designs load cartridges, magazines or shells; energy designs replace or recharge a cell. Reload cues and animations follow the weapon's existing loading schedule. Ammunition transfers only when the reload completes, so a cancelled reload does not grant rounds. Loaded ammunition is saved on the particular weapon stack.

Shotguns discharge six physical pellets for one shell. The pellets share that shell's base damage budget; contacts with one target are combined into one native damage event per shell. The Eternal Shot enchantment can refund at most one matching round per discharge, and manual reloading remains necessary.

## Damage and tradeoffs

Damage falloff uses the projectile's actual three-dimensional travel distance. It is not simply the distance between the player and target when the trigger is pressed. Each weapon profile sets its own travel and damage curve. Automatic weapons have shorter range and steeper falloff than the long-range designs.

Displayed damage is before class bonuses, enchantments and target armor. A high per-shot number does not include reload time, firing cadence, ammunition cost or special-ability limitations. Legendary weapons retain distinct mechanics and tradeoffs rather than sharing one superior stat line.

The guns integrate with SimpleEnchantments where an enchantment applies. Exact enchantment behavior still depends on the installed dependency version and the action being used.

## Crafting and trading

The five-tier **Gunsmith's Bench** provides the arsenal's crafting progression, including dedicated ammunition and weapon-family categories. Ordinary recipes do not consume an existing gun. Regional acquisition and material requirements remain part of progression.

These six guns are exclusive to **The Nameless God's Barter → Weapons → Tier 2**, costing **40 Dark Coins and 1 Silver Skull each**:

| Family | Weapon |
| --- | --- |
| Sniper | Malediction, the Unblinking Eye |
| Handgun | Black Sacrament |
| SMG | Choir of the Damned |
| Semi-auto rifle | The Heretic's Verdict |
| Automatic rifle | Legion of Ruin |
| Shotgun | Hellmaw, Devourer of Souls |

They have no ordinary crafting recipe or alternative seller. Matching ammunition keeps its authored crafting and trade routes. Other regional trades retain their prices and ammunition offers.

## Audio

The 2.0.5 palette covers all 54 guns. Recorded firearm attacks, weapon handling and industrial metal provide the physical foundation; separately licensed Bluezone accents give mechanical and energy designs their themes. Source credits and licenses are included with the resources. No film/game recordings or Suno exports are selected for this release.

Direct reports remain immediate. Native positional events provide remote reports and outdoor returns. The shooter's return is emitted once per paid shot from the captured muzzle origin; a shotgun receives one return across its pellets. That origin stays fixed as the player or projectile moves.

Outdoor returns are authored decays. They do not adapt to room geometry, terrain or weather. Automated asset, headroom, timing and native packet checks do not establish human listening quality or a networked client audio test.

See [installation](INSTALL.md) for required mods and version ranges. Keep one version of the plugin installed at a time.
