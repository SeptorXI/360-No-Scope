"""Author the original 45-weapon 360 No Scope arsenal from verified local gates.

Only this directory is written. Source sniper specifications are read as a
material, theme and integration contract; their weapon assets are never edited.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "baseline"

FAMILIES = {
    "handgun": {
        "token": "Handgun", "label": "Handguns", "category": "AS_Gunsmith_Handguns",
        "body": [8,11,15,20,27,18,19,21,14],
        "head": [12,17,23,30,34,45,30,32,24],
        "cycles": [.78,.78,.82,.85,.9,.9,.87,.95,.78],
        "capacity": [8,8,9,8,8,8,7,10,8], "reload": [1.65,1.7,1.8,1.95,2.1,2.1,1.9,2.05,1.7],
        "ranges": [45,52,62,70,65,90,62,78,68], "full": 14, "minimum": .35,
        "spread": [1.6,1.4,1.1,1.25,1.8,.8,1.15,1,1.1],
        "scope": 1.5, "move": .8, "automatic": False, "pellets": 1,
        "ammoWord": "Pistol Cartridges", "output": 48, "recipeScale": .7,
        "role": "Mobile close-to-mid-range sidearm with measured follow-up shots.",
        "names": ["Wildwood Trailwarden", "Dunewatch Sandbound Oath", "Frostline Pale Marshal", "Mournhollow Last Confession", "Gutter Saint, Mercy of the Deepworks", "Vesper, the Dawn Unspent", "Black Sacrament", "Labyrinth Quiet Equation", "Skybound Windward Promise"],
        "slugs": ["Trailwarden", "Sandbound_Oath", "Pale_Marshal", "Last_Confession", "Gutter_Saint", "Vesper", "Absolver", "Quiet_Equation", "Windward_Promise"],
        "specialNames": ["Absolution Hammer", "Evening Benediction"],
        "specialDamage": [(42,53),(10,18)],
    },
    "smg": {
        "token": "SMG", "label": "Submachine Guns", "category": "AS_Gunsmith_SMGs",
        "body": [2.5,3.5,4.5,6,8,5.5,5.75,6.5,4.25],
        "head": [3.5,5,6.5,8.5,10,13.5,8.5,9.5,6.5],
        "cycles": [.22,.22,.23,.24,.26,.26,.24,.27,.23],
        "capacity": [20,22,24,22,24,24,24,26,22], "reload": [2.2,2.3,2.4,2.55,2.9,2.9,2.65,2.85,2.35],
        "ranges": [35,42,48,55,50,72,52,60,54], "full": 10, "minimum": .25,
        "spread": [3,2.8,2.4,2.6,3.2,2,2.6,2.3,2.4],
        "scope": 1.3, "move": .75, "automatic": True, "pellets": 1,
        "ammoWord": "Compact Rounds", "output": 96, "recipeScale": .9,
        "role": "Short-range automatic pressure; steep travel falloff and frequent reloads.",
        "names": ["Wildwood Brushfire", "Dunewatch Dust Choir", "Frostline Sleetweaver", "Mournhollow Funeral Procession", "Grindhymn, the Gobliterator's Encore", "Starling, Chorus of First Light", "Choir of the Damned", "Labyrinth Threadstorm", "Skybound Kestrel"],
        "slugs": ["Brushfire", "Dust_Choir", "Sleetweaver", "Funeral_Procession", "Grindhymn", "Starling", "Many_Whispers", "Threadstorm", "Kestrel"],
        "specialNames": ["Grinding Halt", "Firstlight Refrain"],
        "specialDamage": [(18,23),(6,10)],
    },
    "semiauto": {
        "token": "SemiAuto", "label": "Semi-Auto Rifles", "category": "AS_Gunsmith_SemiAuto",
        "body": [10,14,19,25,34,23,25,27,18],
        "head": [16,22,30,40,43,59,40,44,30],
        "cycles": [1.05,1.05,1.1,1.15,1.25,1.25,1.15,1.2,1.05],
        "capacity": [6,7,8,8,8,8,7,9,8], "reload": [2.1,2.2,2.35,2.55,2.9,2.9,2.5,2.7,2.2],
        "ranges": [80,95,112,130,120,175,125,145,130], "full": 25, "minimum": .5,
        "spread": [.7,.65,.5,.6,.8,.35,.55,.4,.5],
        "scope": 3, "move": .5, "automatic": False, "pellets": 1,
        "ammoWord": "Marksman Cartridges", "output": 32, "recipeScale": .95,
        "role": "Deliberate precision follow-ups between a sidearm and a bolt-action sniper.",
        "names": ["Wildwood Waymark", "Dunewatch Dune Canticle", "Frostline White Vigil", "Mournhollow Tollkeeper", "Iron Testament, Voice of the Deepworks", "Aurora's Witness, Oath of Luminia", "The Heretic's Verdict", "Labyrinth Proofkeeper", "Skybound Highroad"],
        "slugs": ["Waymark", "Dune_Canticle", "White_Vigil", "Tollkeeper", "Iron_Testament", "Auroras_Witness", "Last_Deposition", "Proofkeeper", "Highroad"],
        "specialNames": ["Iron Verdict", "Witness Mark"],
        "specialDamage": [(54,68),(15,25)],
    },
    "automatic": {
        "token": "Automatic", "label": "Full-Auto Rifles", "category": "AS_Gunsmith_Automatic",
        "body": [3,4.25,5.5,7.5,10,7,7.25,8,5.25],
        "head": [4.5,6.5,8.5,11.5,12.5,17.5,11,12.5,8.5],
        "cycles": [.28,.28,.3,.31,.34,.34,.32,.35,.3],
        "capacity": [20,22,24,24,26,26,24,28,24], "reload": [2.5,2.6,2.7,2.9,3.2,3.2,2.95,3.15,2.6],
        "ranges": [65,78,90,105,95,140,100,120,105], "full": 20, "minimum": .35,
        "spread": [2,1.8,1.5,1.6,2.1,1.2,1.6,1.4,1.5],
        "scope": 2, "move": .5, "automatic": True, "pellets": 1,
        "ammoWord": "Assault Cartridges", "output": 64, "recipeScale": 1.05,
        "role": "Sustained mid-range automatic fire balanced by recoil, reload cost and travel falloff.",
        "names": ["Wildwood Briar March", "Dunewatch Scorchwind", "Frostline Winter Standard", "Mournhollow Dirge Engine", "Crown of Rivets, the Unbroken March", "Helios Refrain, Light Beyond the Siege", "Legion of Ruin", "Labyrinth Patternbreaker", "Skybound Gale Banner"],
        "slugs": ["Briar_March", "Scorchwind", "Winter_Standard", "Dirge_Engine", "Crown_Of_Rivets", "Helios_Refrain", "Hollow_Regiment", "Patternbreaker", "Gale_Banner"],
        "specialNames": ["Rivetbreaker", "Helios Brand"],
        "specialDamage": [(24,30),(8,14)],
    },
    "shotgun": {
        "token": "Shotgun", "label": "Shotguns", "category": "AS_Gunsmith_Shotguns",
        "body": [3,4.25,5.5,7.5,10,7,7,8,5.25],
        "head": [3.5,5,6.5,9,11.5,14,9,10,6.5],
        "cycles": [1.65,1.65,1.75,1.85,2,2,1.85,1.95,1.7],
        "capacity": [4,4,5,5,6,6,5,6,5], "reload": [2.7,2.8,3,3.2,3.5,3.5,3.2,3.45,2.9],
        "ranges": [28,32,38,44,40,58,42,50,42], "full": 7, "minimum": .15,
        "spread": [7,6.5,6,6.5,8,4.5,6.8,5.5,5.8],
        "scope": 1.2, "move": .6, "automatic": False, "pellets": 6,
        "ammoWord": "Scatter Shells", "output": 16, "recipeScale": .95,
        "role": "Six-projectile close-range shell; pellet budget is shared across the spread.",
        "names": ["Wildwood Hollowbark", "Dunewatch Sandbreaker", "Frostline Hearthguard", "Mournhollow Bellwether", "Gatecrasher, the Gobliterator's Wake", "Solstice, Seven Lamps of Luminia", "Hellmaw, Devourer of Souls", "Labyrinth Doorwarden", "Skybound Cloudburst"],
        "slugs": ["Hollowbark", "Sandbreaker", "Hearthguard", "Bellwether", "Gatecrasher", "Solstice", "Grave_Tithe", "Doorwarden", "Cloudburst"],
        "specialNames": ["Breach Bell", "Solstice Beacon"],
        "specialDamage": [(82,98),(22,36)],
    },
}

THEME_TEXT = [
    ("Waytrail", "Oak panels and peened copper recall the Emerald Wilds' trail stations. Its maker cut a fresh notch for every traveler brought home."),
    ("Sirocco", "Sand-colored wraps cover a thorium-sealed action. In the Howling Sands, the watch keeps its oath long after its banners disappear beneath the dunes."),
    ("Rimeglass", "Silver tracery runs through cold-worked cobalt. Whisperfrost wardens kept this pattern beside the hearth, ready when the white fields moved."),
    ("Gravelight", "A Mournhollow reliquary key seats behind a violet chamber. Its inscriptions are names, each left unfinished until the living return."),
    ("Cindercoil", "The Gobliterator's broken heart turns within an amber lattice. Deepworks smiths listened to the wreckage and forged its stubborn rhythm into a weapon. Cyan rails flare between battered iron ribs; every discharge is followed by the scrape and sigh of machinery forced to remember its purpose."),
    ("Vesperglass", "Three fragments of Luminia's fallen seals lie aligned within a pale prism. White-gold channels awake around a violet star, casting the small light once kept above the sanctum doors. Its bearer inherits an unfinished vigil: guide the faithful through the dark, and spend the dawn with care."),
    ("Penance", "Dark silver and a silver skull frame the Nameless God's compact covenant. A red oath-mark hides beneath each violet-lit plate; no maker's name survives."),
    ("Threadline", "Fullmetal ribs bind a cyan focus in a measured lattice. Labyrinth artificers left one thread unclosed, an invitation to find the next way through."),
    ("Skyglass", "Windworn brass guards sky-blue steel and a green sight-stone. The Airshop's couriers prefer a light pack and one promise kept above the clouds."),
]

SPECIAL_TIMING = {
    # Charge/stagger are the heavy sidegrade. Mark, slow, multiplier are the
    # precision sidegrade; each family offers a different control window.
    "handgun": {"charge": .35, "stagger": .2, "mark": 8, "slow": 2, "speed": .9},
    "smg": {"charge": .8, "stagger": .55, "mark": 2, "slow": 1, "speed": .65},
    "semiauto": {"charge": 1.1, "stagger": .5, "mark": 8, "slow": 5, "speed": .9},
    "automatic": {"charge": .65, "stagger": .3, "mark": 5, "slow": 2, "speed": .75},
    "shotgun": {"charge": 1.2, "stagger": .75, "mark": 3, "slow": 1.25, "speed": .6},
}


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def quarter(value):
    return round(value * 4) / 4


def main():
    source_path = BASE / "sniper-spec.json"
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    acquisition = json.loads((BASE / "acquisition-spec.json").read_text(encoding="utf-8-sig"))
    exclusives = json.loads((ROOT / "nameless-exclusives.json").read_text(encoding="utf-8"))
    exclusive_by_id = {row["id"]: row for row in exclusives["weapons"]}
    assert exclusives["schemaVersion"] == 1 and len(exclusive_by_id) == 6
    assert {row["family"] for row in exclusives["weapons"]} == {"sniper", *FAMILIES}
    original_ammo = {a["id"]: a for a in source["ammo"]}
    spec = {
        "schemaVersion": 1, "modName": "360 No Scope", "version": "2.0.5",
        "artifactStem": "360-No-Scope", "pluginId": "Steven:360 No Scope",
        "sourceVersions": source["sourceVersions"], "classification": source["classification"],
        "baseSpecSHA256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "designRules": [
            "45 new independent weapon acquisitions: 40 Gunsmith recipes and 5 exclusive Nameless God's Barter recipes; nine regional designs for each family, with no previous weapon consumed.",
            "Six existing Nameless guns, including the sniper, are sold only by The Nameless God's Barter through DarkCoinShop_Weapons Tier 2; neither Gunsmith nor Devil Merchant sells these guns. Ammunition access is unchanged.",
            "Exactly one exclusive ammunition ID per new weapon; receiver plus ammunition equals the selected native base calculator exactly.",
            "Semi-auto requires a new click. SMGs and full-auto rifles repeat only while primary is held and are bounded by their server cadence.",
            "Distance means accumulated 3D projectile travel; each family has its own shared curve, while role pairs preserve identical multipliers at shared distances.",
            "One ammo payment per trigger discharge. A shotgun's six projectile damages partition one shell budget; Eternal Shot refunds once per shell, not per pellet.",
            "Loaded ammunition belongs to each ItemStack; manual native R/Ability4 reload commits matching ammunition only on completion, with no cancellation or swap duplication.",
            "Automatic fire uses one native damage event per bullet. ShotgunLedger aggregates each shell's contacts per target into one damage/proc event; neither receives an extra ammo damage proc.",
            "A player's compatible native enchantments, metadata, durability and ordinary class/skill integration are retained.",
            "All ten new Legendary specials consume two loaded rounds and share the existing RS_LegendaryAbility twelve-second lock, including the original sniper pair.",
            "Heavy Legendary designs favor body damage and control; Luminia designs sacrifice body damage for precision, mobility and range.",
            "Base DPS does not bound flat per-hit class procs. Automatic weapons and the per-shell shotgun aggregator require installed-proc combat testing; preserve native immunity and no global balance edits.",
            "All original models, pixel textures, icons, reload assets and sources remain reproducible; only energy parts use fullbright.",
        ],
        "families": [], "tiers": [], "ammo": [], "shops": [],
        "namelessExclusives": {"contract": "content/nameless-exclusives.json", "seller": exclusives["seller"], "weaponIds": list(exclusive_by_id)},
        "limits": [
            "Numerical DPS below is pre-class, pre-enchantment and pre-armor, assumes every projectile hits and excludes specials.",
            "A nominal range is not a promise to damage targets in unloaded chunks.",
            "Names describe visual themes; elemental damage, armor penetration and piercing are not implied.",
        ],
    }
    rows = []
    for family, settings in FAMILIES.items():
        category_id = "AS_Gunsmith_" + family
        spec["families"].append({"id": family, "name": settings["label"], "category": category_id, "role": settings["role"]})
        for index, original in enumerate(source["tiers"]):
            theme_number = index + 1
            token = settings["token"]
            stem = settings["slugs"][index]
            weapon_id = f"Weapon_Crossbow_AS_{token}_{stem}"
            ammo_id = f"AS_Ammo_{token}_{stem}"
            legacy_ammo = original_ammo[original["ammo"]]
            body, head = settings["body"][index], settings["head"][index]
            pellets = settings["pellets"]
            energy = index in (4,5)
            charged = energy or index in (3,6,7)
            cycle = settings["cycles"][index]
            capacity = settings["capacity"][index]
            reload_time = settings["reload"][index]
            reach = settings["ranges"][index]
            body_ammo = max(.25, quarter(body * .25))
            head_ammo = max(.25, quarter(head * .25))
            ammo_name = f"{THEME_TEXT[index][0]} {settings['ammoWord']}"
            if energy:
                ammo_name = f"{THEME_TEXT[index][0]} {token if token != 'SemiAuto' else 'Marksman'} Cells"
            material_scale = settings["recipeScale"]
            ingredients = {}
            for item, amount in original["ingredients"].items():
                # Never scale away the trophy/currency or dungeon key gate.
                gate = amount == 1 or any(word in item for word in ("Seal_Fragment", "Gobliterator_Core", "Skull", "Reliquary_Key", "Rupee", "Dark_Coin", "Bag_Essence", "Silent_Princess"))
                ingredients[item] = amount if gate else max(1, math.ceil(amount * material_scale))
            bench = deepcopy(original["bench"])
            bench["Categories"] = [category_id]
            audio = deepcopy(original["audio"])
            audio["events"]["Fire"] = {
                "Local": f"AS_Audio_AS_{token}_{stem}_Fire_Local",
                "World": f"AS_Audio_AS_{token}_{stem}_Fire_World",
            }
            move = settings["move"]
            if index == 4:
                move *= .8
            elif index == 5:
                move = min(.9, move * 1.15)
            style = "energy-cell" if energy else ("shell-tube" if family == "shotgun" else "magazine")
            tier = {
                "id": weapon_id, "name": exclusive_by_id.get(weapon_id,{}).get("name",settings["names"][index]), "family": family,
                "tier": original["tier"], "artIndex": theme_number, "quality": original["quality"],
                "itemLevel": original["itemLevel"], "region": original["region"],
                "sourceThemeWeapon": original["id"], "description": THEME_TEXT[index][1] + " " + settings["role"],
                "projectile": "laser-styled projectile" if energy else ("charged cartridge" if charged else "solid cartridge"),
                "damage": body, "headDamage": head, "receiverDamage": body - body_ammo,
                "receiverHeadDamage": head - head_ammo, "ammo": ammo_id,
                "pellets": pellets, "damagePerShell": body * pellets, "headDamagePerShell": head * pellets,
                "automatic": settings["automatic"], "fireMode": "automatic" if settings["automatic"] else "semiautomatic",
                "cycleSeconds": cycle, "roundsPerMinute": round(60 / cycle, 2),
                "spreadDegrees": settings["spread"][index], "range": reach, "scope": settings["scope"],
                "adsMoveMultiplier": round(move, 3), "role": settings["role"],
                "reload": {"capacity": capacity, "durationSeconds": reload_time, "style": style,
                           "animationId": "Reload", "playerAnimationsId": f"AS_AS_{token}_{stem}_Player", "interactionType": "Ability4"},
                "falloff": {"metric": "traveledPath", "points": [{"distance": 0, "multiplier": 1}, {"distance": settings["full"], "multiplier": 1}, {"distance": max(settings["ranges"]), "multiplier": settings["minimum"]}], "appliesTo": ["NormalBody", "NormalHead", "SpecialBody", "SpecialHead"]},
                "bench": bench, "ingredients": ingredients, "requiredMemoriesLevel": 1,
                "audio": audio,
                "tradeoffs": ["Shorter effective reach and lower per-trigger impact than a comparable sniper", "Frequent reloads interrupt sustained damage"],
            }
            if original.get("progressionNote"):
                tier["progressionNote"] = original["progressionNote"]
            if energy:
                legendary_index = index - 4
                heavy = index == 4
                special_body, special_head = settings["specialDamage"][legendary_index]
                timing = SPECIAL_TIMING[family]
                ability = {
                    "name": settings["specialNames"][legendary_index], "kind": "stagger" if heavy else "markSlow",
                    "effectKind": "stagger" if heavy else "markSlow",
                    "input": "Ability1", "chargeSeconds": timing["charge"] if heavy else 0,
                    "bodyDamage": special_body, "headDamage": special_head,
                    "pellets": 1, "ammoPerUse": 2, "cooldownSeconds": 12,
                    "sharedCooldownId": "RS_LegendaryAbility",
                    "shotRecoverySeconds": max(1.6, cycle * (2.8 if heavy else 1.5)),
                    "npcOnly": True, "respectsImmunity": "Immunity_Freeze" if heavy else "Immunity_Slow",
                }
                if heavy:
                    ability["staggerSeconds"] = timing["stagger"]
                    tier["tradeoffs"] = ["Higher body damage and body-shot ammunition efficiency", "Wider spread and shorter range than the Luminia counterpart", "Heavier aimed movement", "Control shot requires charging and a longer firing recovery"]
                    tier["glowTheme"] = "Amber coil ribs, small cyan rails and restrained warm light."
                else:
                    ability.update({"markSeconds": timing["mark"], "slowSeconds": timing["slow"], "speedMultiplier": timing["speed"]})
                    tier["tradeoffs"] = ["Lower body damage than the Deepworks counterpart", "Better headshot ceiling, narrower spread and longer reach", "Lighter aimed movement", "Two-round mark sacrifices immediate damage; NPC slow immunity remains respected"]
                    tier["glowTheme"] = "White-gold channels, cyan prism faces and restrained violet motes."
                if family == "shotgun":
                    ability["note"] = "Special replaces the entire six-pellet shell with one focused slug; listed special damage is its TOTAL."
                if heavy:
                    ability["description"] = (
                        f"Hold Q for {ability['chargeSeconds']:g}s to fire one focused shot; "
                        f"eligible NPCs stagger for {ability['staggerSeconds']:g}s. "
                        f"Freeze immunity and enraged interrupt immunity prevent the stagger. "
                        f"The shot commits two loaded rounds and locks firing for {ability['shotRecoverySeconds']:g}s. "
                        "Releasing before the charge completes cancels without spending rounds or starting the special cooldown."
                    )
                else:
                    ability["description"] = (
                        f"Press Q for a low-damage setup shot that visibly marks NPCs for {ability['markSeconds']:g}s "
                        f"and slows eligible NPCs by {(1-ability['speedMultiplier'])*100:g}% for {ability['slowSeconds']:g}s. "
                        "Slow-immune NPCs retain only the visual mark. "
                        f"The shot commits two loaded rounds and locks firing for {ability['shotRecoverySeconds']:g}s."
                    )
                if family == "shotgun":
                    ability["description"] += " This special replaces the six-pellet fan with one focused slug; its listed damage is the whole shot."
                tier["ability"] = ability
            stats = {
                "damage": body_ammo, "headDamage": head_ammo,
                "speed": round(legacy_ammo["stats"]["speed"] * (.75 if family in ("handgun", "smg", "shotgun") else .9)),
                "gravity": 0 if energy else legacy_ammo["stats"]["gravity"], "range": reach,
            }
            ammo_bench = deepcopy(legacy_ammo["bench"])
            ammo_bench["Categories"] = ["RS_Gunsmith_Ammunition"]
            ammo_bench["RequiredTierLevel"] = bench["RequiredTierLevel"]
            cartridge = {
                "id": ammo_id, "name": ammo_name, "description": f"Dedicated {'six-projectile shell' if pellets > 1 else 'cartridge'} for {tier['name']}. " + ("A prism cell supplies the visible energy discharge." if energy else "Its shaped case fits only this receiver."),
                "quality": original["quality"], "compatibleWeapon": weapon_id, "family": family,
                "artIndex": theme_number, "stats": stats, "output": settings["output"],
                "ingredients": deepcopy(legacy_ammo["ingredients"]), "bench": ammo_bench,
                "requiredMemoriesLevel": 1, "pelletsPerRound": pellets,
                "damageBudget": {"unit": "perPellet" if pellets > 1 else "perProjectile", "bodyPerRound": body_ammo * pellets, "headPerRound": head_ammo * pellets},
            }
            if weapon_id in exclusive_by_id:
                exclusive = exclusive_by_id[weapon_id]
                assert exclusive["name"] == tier["name"] and exclusive["family"] == family
                tier["vendorOnly"] = True
                tier["ingredients"] = deepcopy(exclusive["ingredients"])
                tier["bench"] = deepcopy(exclusive["bench"])
                tier["acquisition"] = {
                    "type": "exclusiveBarter", "sellerId": exclusives["seller"]["itemId"],
                    "sellerName": exclusives["seller"]["name"], "recipeId": exclusive["recipeId"],
                    "benchId": exclusives["seller"]["benchId"], "categoryId": exclusives["seller"]["categoryIds"][0],
                    "requiredTierLevel": exclusives["seller"]["requiredTierLevel"], "outputQuantity": exclusive["outputQuantity"],
                }
                tier["description"] += " Sold exclusively through The Nameless God's Barter: Weapons, Tier 2."
            spec["tiers"].append(tier)
            spec["ammo"].append(cartridge)
            # Sustained cycle measures a full magazine and a complete manual reload.
            magazine_seconds = max(0, capacity - 1) * cycle + reload_time
            sustained = capacity * body * pellets / magazine_seconds
            sustained_head = capacity * head * pellets / magazine_seconds
            rows.append({"id": weapon_id, "name": tier["name"], "family": family, "quality": tier["quality"], "perProjectileBody": body, "perProjectileHead": head,
                         "pellets": pellets, "bodyPerDischarge": body * pellets, "headPerDischarge": head * pellets,
                         "instantBodyDPS": round(body * pellets / cycle, 3), "sustainedBodyDPS": round(sustained, 3), "sustainedHeadDPS": round(sustained_head, 3),
                         "cycleSeconds": cycle, "magazine": capacity, "reloadSeconds": reload_time,
                         "nativeProcEventsPerSecondPerTarget": round(1 / cycle, 3), "flatFiveDamageProcAddedInstantDPSPerTarget": round(5 / cycle, 3),
                         "procContract": "ShotgunLedger aggregates same-shell pellet contacts into one damage/proc event per target." if pellets > 1 else "One native damage/proc event per bullet contact."})
    # Additive trades follow the already verified source merchant/currency pairs.
    old_to_new = {}
    for tier in spec["tiers"]:
        old_to_new.setdefault(tier["sourceThemeWeapon"], []).append(tier)
    ammo_to_theme = {a["id"]: a["compatibleWeapon"] for a in source["ammo"]}
    for shop in acquisition["Shops"]:
        trades = []
        for trade in shop["Trades"]:
            output = trade["Output"]["ItemId"]
            source_weapon = output if output in old_to_new else ammo_to_theme.get(output)
            for tier in old_to_new.get(source_weapon, []):
                item_id = tier["id"] if output == source_weapon else tier["ammo"]
                if item_id in exclusive_by_id:
                    continue
                new_trade = deepcopy(trade)
                new_trade["OperationId"] = "AS_sale_" + item_id
                new_trade["Output"]["ItemId"] = item_id
                if output != source_weapon:
                    new_trade["Output"]["Quantity"] = next(a["output"] for a in spec["ammo"] if a["id"] == item_id)
                trades.append(new_trade)
        spec["shops"].append({"PatchId": shop["PatchId"], "Target": shop["Target"], "Trades": trades})
    check_spec(spec)
    write_json(ROOT / "arsenal-spec.json", spec)
    report = {"weaponCount": len(spec["tiers"]), "ammoCount": len(spec["ammo"]), "families": {f: sum(t["family"] == f for t in spec["tiers"]) for f in FAMILIES},
              "interpretation": "Damage is pre-class, pre-enchantment, pre-armor and before traveled-path falloff. Sustained calculation: capacity*damagePerDischarge/((capacity-1)*cycle+reload). It assumes a full-magazine burst and an immediate complete reload.",
              "nativeProcWarning": "Flat per-hit effects scale with event rate. Shotguns require ShotgunLedger per-shell per-target aggregation, so the flat-five sensitivity uses one event per discharge per target rather than six pellet events. A hypothetical +5 damage per event is tabulated, not claimed to be the installed mod's exact proc. Real class/enchantment combat requires a playtest.",
              "rows": rows}
    write_json(ROOT / "balance-report.json", report)
    make_notes(spec, rows)
    print(f"Authored {len(spec['tiers'])} weapons / {len(spec['ammo'])} exclusive ammunition types / {sum(len(s['Trades']) for s in spec['shops'])} additive merchant trades.")


def check_spec(spec):
    tiers, ammo = spec["tiers"], {a["id"]: a for a in spec["ammo"]}
    assert len(tiers) == len(ammo) == 45
    assert len({t["id"] for t in tiers}) == len(tiers)
    assert len({t["name"] for t in tiers}) == len(tiers)
    assert len({a["name"] for a in spec["ammo"]}) == len(ammo)
    exclusives = json.loads((ROOT / "nameless-exclusives.json").read_text(encoding="utf-8"))
    exclusive_by_id = {row["id"]: row for row in exclusives["weapons"]}
    assert sum(bool(t.get("vendorOnly")) for t in tiers) == 5
    for t in tiers:
        a = ammo[t["ammo"]]
        assert a["compatibleWeapon"] == t["id"]
        assert re.fullmatch(r"[A-Za-z0-9_]+", t["id"])
        assert t["receiverDamage"] + a["stats"]["damage"] == t["damage"]
        assert t["receiverHeadDamage"] + a["stats"]["headDamage"] == t["headDamage"]
        assert t["cycleSeconds"] > .12 and t["damage"] > 0 and t["headDamage"] >= t["damage"]
        assert t["damagePerShell"] == t["pellets"] * t["damage"]
        assert t["headDamagePerShell"] == t["pellets"] * t["headDamage"]
        assert t["reload"]["capacity"] >= 2 and t["reload"]["interactionType"] == "Ability4"
        if t["id"] in exclusive_by_id:
            contract = exclusive_by_id[t["id"]]
            assert t.get("vendorOnly") and t["bench"] == contract["bench"]
            assert t["ingredients"] == contract["ingredients"]
            assert t["acquisition"]["recipeId"] == contract["recipeId"]
            assert t["acquisition"]["sellerId"] == "Bench_DarkCoinShop"
        else:
            assert not t.get("vendorOnly")
            assert t["bench"]["Id"] == "RS_Gunsmith" and 1 <= t["bench"]["RequiredTierLevel"] <= 5
        assert a["bench"]["Id"] == "RS_Gunsmith"
        points = t["falloff"]["points"]
        assert all(x["distance"] < y["distance"] and x["multiplier"] >= y["multiplier"] for x,y in zip(points, points[1:]))
        assert (t["family"] in ("smg", "automatic")) == t["automatic"]
        if "ability" in t:
            assert t["quality"] == "Legendary" and t["ability"]["ammoPerUse"] == 2
            assert t["ability"]["sharedCooldownId"] == "RS_LegendaryAbility"
    for family in FAMILIES:
        pair = [t for t in tiers if t["family"] == family and t["quality"] == "Legendary"]
        heavy, precision = pair
        assert heavy["cycleSeconds"] == precision["cycleSeconds"]
        assert heavy["falloff"] == precision["falloff"]
        assert heavy["damage"] > precision["damage"] and heavy["headDamage"] < precision["headDamage"]
        assert heavy["range"] < precision["range"] and heavy["adsMoveMultiplier"] < precision["adsMoveMultiplier"]
    assert not any(trade["Output"]["ItemId"] in exclusive_by_id for shop in spec["shops"] for trade in shop["Trades"])


def make_notes(spec, rows):
    report = {r["id"]: r for r in rows}
    lines = ["# 360 No Scope â€” Arsenal content contract", "", "45 original weapons, nine designs per family: 40 new Gunsmith recipes and 5 new exclusive Nameless God's Barter acquisitions. The existing Nameless barter sniper joins those five exclusives. Gunsmith recipes preserve their material/trophy gates; no acquisition consumes a previous weapon. All 45 matching ammunition recipes remain at the Gunsmith, and existing ammunition sellers remain available.", "", "Damage below is the complete loaded discharge before bonuses, armor and distance falloff. Shotguns divide that budget across six pellets. Listed sustained DPS includes a full-magazine reload, assumes every projectile hits, and excludes special attacks.", ""]
    for f in spec["families"]:
        lines += ["## " + f["name"], "", f["role"], "", "| Weapon | Rarity | Body/head per discharge | Magazine | Cycle | Reload | Nominal reach | Sustained body DPS |", "|---|---|---:|---:|---:|---:|---:|---:|"]
        for t in spec["tiers"]:
            if t["family"] != f["id"]: continue
            row = report[t["id"]]
            lines.append(f"| {t['name']} | {t['quality']} | {t['damagePerShell']:g}/{t['headDamagePerShell']:g} | {t['reload']['capacity']} | {t['cycleSeconds']:g}s | {t['reload']['durationSeconds']:g}s | {t['range']} | {row['sustainedBodyDPS']:g} |")
        lines += [""]
    exclusives = json.loads((ROOT / "nameless-exclusives.json").read_text(encoding="utf-8"))
    lines += ["## Nameless God exclusives", "", "Only The Nameless God's Barter sells these six guns: Weapons, Tier 2. Each costs 40 Dark Coins and 1 Silver Skull, produces one gun, and has no crafting/barter stock limit. This is the native DarkCoinShop station; the Devil Merchant NPC is a separate seller and does not sell these guns. Their ammunition remains available at the Gunsmith and its existing sellers.", "", "| Weapon family | Exclusive gun |", "|---|---|"]
    for weapon in exclusives["weapons"]:
        lines.append(f"| {weapon['family']} | {weapon['name']} |")
    lines += ["", "## Legendary decisions", "", "Each family has a heavy Deepworks sidegrade and a precision Luminia sidegrade. Equal family cadence and the same traveled-path multiplier preserve their body-versus-weak-point tradeoff. Deepworks favors body damage and a charged NPC stagger; Luminia trades immediate damage for a visual mark and immunity-respecting NPC slow. All ten specials share the original twelve-second Legendary cooldown, consume two loaded rounds, and use one focused projectile. Shotgun specials replace the entire pellet fan with that slug.", "", "| Family | Heavy charge / stagger | Precision mark / slow |", "|---|---|---|"]
    for f in spec["families"]:
        timing = SPECIAL_TIMING[f["id"]]
        lines.append(f"| {f['name']} | {timing['charge']:g}s / {timing['stagger']:g}s | {timing['mark']:g}s mark; {(1-timing['speed'])*100:g}% slow for {timing['slow']:g}s |")
    lines += ["", "The sidearm gives a quick, brief interruption and a long spotting mark. The SMG commits a longer charge for stronger interruption or a short pursuit-control burst. The semi-auto rifle needs a deliberate charge but gives a longer precision setup window. The automatic rifle sits between those control timings. The shotgun offers the strongest short interruption or strongest brief slow, with long charge/recovery and a focused slug replacing the spread.", "", "## Integration and remaining evidence", "", "Exclusive ammo uses native ranged/Arrow-compatible integration without broad ammo matching. Reloads must preserve per-ItemStack enchantments and chamber state; refunds must occur once per committed bullet or shotgun shell. Inventory and held appearance require client review.", "", "Automatic bullets can amplify flat per-contact class/enchantment procs. ShotgunLedger must aggregate same-shell pellet contacts into one damage/proc event per target; the report uses that contract, not six independent flat bonuses. balance-report.json exposes event rates and a hypothetical flat-five sensitivity calculation. No claim of final multiplayer balance is made from the pre-modifier numbers alone. Preserve native mod behavior and verify actual class/enchantment builds in combat before live deployment.", "", "All original rifles and their IDs remain outside this content generator's write scope. Current source materials and merchant contracts came from the locally installed sniper specification; no external weapon geometry, texture or copyrighted recording is included here.", ""]
    (ROOT / "CONTENT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
