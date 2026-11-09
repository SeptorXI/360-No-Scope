"""Build only the owned Gunsmith bench, calibration kits, art and language keys.

Usage: python bench/generate_bench.py [packRoot]
The main pack builder owns rifle/ammunition recipe migration and cleanup.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parent
PROJECT = SOURCE.parent


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_child(root: Path, relative: str) -> Path:
    value = (root / relative).resolve()
    if not value.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes its owned root: {relative}")
    return value


def recipe(entry: dict) -> dict:
    inputs = entry.get("input")
    if inputs is None:
        inputs = [{"ItemId": item, "Quantity": count} for item, count in entry["ingredients"].items()]
    return {
        "TimeSeconds": entry["timeSeconds"],
        "Input": inputs,
        "OutputQuantity": entry["output"],
        "BenchRequirement": [entry["bench"]],
        "RequiredMemoriesLevel": entry["requiredMemoriesLevel"],
        "KnowledgeRequired": False,
    }


def main(pack_root: Path) -> dict:
    pack_root = pack_root.resolve()
    if not pack_root.is_relative_to(PROJECT):
        raise ValueError("Gunsmith generation is limited to this isolated project")
    spec = read_json(SOURCE / "bench-spec.json")
    art = read_json(safe_child(PROJECT, spec["artContract"]))
    common_source = safe_child(PROJECT, spec["artCommonRoot"])
    if len(spec["tiers"]) != spec["tierCount"] or spec["tiers"][-1].get("upgradeKit"):
        raise ValueError("Bench must have five ordered tiers and no upgrade beyond its final tier")
    for index, tier in enumerate(spec["tiers"], 1):
        if tier["level"] != index:
            raise ValueError("Bench tier indices must be consecutive and one-based")
    for key in ("model", "texture", "icon"):
        if not safe_child(common_source, art[key]).is_file():
            raise FileNotFoundError(f"Gunsmith art missing: Common/{art[key]}")
    if not art["hitboxPath"].startswith("Server/Item/Block/Hitboxes/"):
        raise ValueError("Unexpected Gunsmith hitbox output path")

    copied_art = []
    for source in sorted(common_source.rglob("*")):
        if not source.is_file():
            continue
        if not source.resolve().is_relative_to(common_source.resolve()):
            raise ValueError(f"Art source escapes Common: {source}")
        relative = source.relative_to(common_source)
        destination = safe_child(pack_root / "Common", relative.as_posix())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        copied_art.append({"path": "Common/" + relative.as_posix(), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    write_json(safe_child(pack_root, art["hitboxPath"]), art["hitbox"])

    lang = {
        f"items.{spec['itemId']}.name": spec["name"],
        f"items.{spec['itemId']}.description": spec["description"],
    }
    native_categories = []
    for category in spec["categories"]:
        # Native BenchCategory's path validator requires this namespace even
        # when an existing item image is reused without any pixel changes.
        if not category["icon"].startswith("Icons/CraftingCategories/"):
            raise ValueError("Bench category icon must be under Icons/CraftingCategories/")
        category_source = safe_child(pack_root / "Common", category["sourceIcon"])
        category_destination = safe_child(pack_root / "Common", category["icon"])
        if not category_source.is_file():
            raise FileNotFoundError(f"Build original item icons before the Gunsmith generator: {category['sourceIcon']}")
        category_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(category_source, category_destination)
        copied_art.append({"path": "Common/" + category["icon"], "source": "Common/" + category["sourceIcon"], "sha256": hashlib.sha256(category_source.read_bytes()).hexdigest()})
        key = "benchCategories." + category["id"]
        lang[key] = category["name"]
        native_categories.append({"Id": category["id"], "Icon": category["icon"], "Name": "server." + key})

    tiers = []
    for tier in spec["tiers"]:
        native = {"CraftingTimeReductionModifier": tier["craftingTimeReductionModifier"]}
        if "upgradeKit" in tier:
            native["UpgradeRequirement"] = {"Material": [{"ItemId": tier["upgradeKit"], "Quantity": 1}], "TimeSeconds": tier["upgradeSeconds"]}
        tiers.append(native)

    bench = {
        "TranslationProperties": {"Name": f"server.items.{spec['itemId']}.name", "Description": f"server.items.{spec['itemId']}.description"},
        "Icon": art["icon"],
        "Categories": ["Furniture.Benches"],
        "MaxStack": 1,
        "ItemLevel": 2,
        "Recipe": recipe(spec["baseRecipe"]),
        "BlockType": {
            "Material": "Solid",
            "DrawType": "Model",
            "Opacity": "Transparent",
            "CustomModel": art["model"],
            "CustomModelTexture": [{"Texture": art["texture"], "Weight": 1}],
            "VariantRotation": "NESW",
            "HitboxType": art["hitboxType"],
            "BlockEntity": {"Components": {"BenchBlock": {"TierLevel": spec["initialTier"]}}},
            "Gathering": {"Breaking": {"GatherType": "Benches"}},
            "Bench": {
                "Type": spec["benchType"], "Id": spec["benchId"], "Categories": native_categories,
                "LocalOpenSoundEventId": "SFX_Weapon_Bench_Open",
                "LocalCloseSoundEventId": "SFX_Weapon_Bench_Close",
                "CompletedSoundEventId": "SFX_Weapon_Bench_Craft",
                "FailedSoundEventId": "SFX_Generic_Crafting_Failed",
                "BenchUpgradeSoundEventId": "SFX_Workbench_Upgrade_Start_Default",
                "BenchUpgradeCompletedSoundEventId": "SFX_Workbench_Upgrade_Complete_Default",
                "TierLevels": tiers,
            },
            "BlockParticleSetId": "Stone", "ParticleColor": "#655342",
            "Support": {"Down": [{"FaceType": "Full"}]},
            "BlockSoundSetId": "Stone", "PhysicalMaterialId": "Stone",
        },
        "PlayerAnimationsId": "Block",
        "Tags": {"Type": ["Bench"]},
        "ItemSoundSetId": "ISS_Blocks_Wood",
    }
    if art.get("iconProperties"):
        bench["IconProperties"] = art["iconProperties"]
    item_root = pack_root / "Server/Item/Items/RangerSnipers/Bench"
    write_json(item_root / (spec["itemId"] + ".json"), bench)

    calibrations = []
    visual = spec["kitVisual"]
    for kit in spec["calibrations"]:
        lang[f"items.{kit['id']}.name"] = kit["name"]
        lang[f"items.{kit['id']}.description"] = kit["description"]
        item = {
            "TranslationProperties": {"Name": f"server.items.{kit['id']}.name", "Description": f"server.items.{kit['id']}.description"},
            "Icon": visual["icon"], "Model": visual["model"], "Texture": visual["texture"],
            "Quality": kit["quality"], "Categories": ["Items.Materials"], "MaxStack": 25,
            "PlayerAnimationsId": "Item", "Recipe": recipe(kit),
            "Tags": {"Type": ["Ingredient"], "Family": ["Tooling"]},
            "ItemSoundSetId": "ISS_Items_Ingots",
        }
        write_json(item_root / (kit["id"] + ".json"), item)
        calibrations.append({k: kit[k] for k in ("id", "name", "bench", "ingredients", "output", "timeSeconds", "requiredMemoriesLevel", "unlocksTier")})

    language_path = pack_root / "Server/Languages/en-US/server.lang"
    if not language_path.is_file():
        raise FileNotFoundError("The main builder must write server.lang before the Gunsmith generator runs")
    existing = language_path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in existing if line.split("=", 1)[0].strip() not in lang]
    while kept and not kept[-1].strip():
        kept.pop()
    language_path.write_text("\n".join(kept) + "\n\n" + "\n".join(key + "=" + value for key, value in sorted(lang.items())) + "\n", encoding="utf-8")

    base_recipe = dict(spec["baseRecipe"])
    base_recipe["ingredients"] = {entry.get("ItemId", "resource:" + entry.get("ResourceTypeId", "")): entry["Quantity"] for entry in base_recipe["input"]}
    catalog = {
        "schemaVersion": 1, "version": spec["version"], "name": spec["name"],
        "itemId": spec["itemId"], "benchId": spec["benchId"], "benchType": spec["benchType"],
        "model": art["model"], "texture": art["texture"], "icon": art["icon"],
        "hitboxType": art["hitboxType"], "hitboxPath": art["hitboxPath"], "hitbox": art["hitbox"],
        "baseRecipe": base_recipe, "calibrations": calibrations,
        "tierCount": spec["tierCount"], "initialTier": spec["initialTier"] , "tiers": spec["tiers"],
        "tabs": spec["categories"], "categories": native_categories,
        "recipeCount": 1 + len(calibrations), "languageKeys": sorted(lang), "art": copied_art,
        "explicitVisualTierStates": [], "staticModel": True,
        "migration": spec["recipeMigration"],
    }
    write_json(SOURCE / "catalog.json", catalog)
    print(f"Gunsmith generated: {catalog['recipeCount']} recipes, {catalog['tierCount']} tiers, {len(copied_art)} Common files")
    return catalog


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "pack")
