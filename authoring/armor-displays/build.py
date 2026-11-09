"""Build this isolated furniture plugin without modifying other mods or servers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "pack"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def build():
    spec = read(ROOT / "content/display-spec.json")
    contract = read(ROOT / "art/art-contract.json")
    art = {entry["id"]: entry for entry in contract["assets"]}
    if len(art) != 6 or set(art) != {entry["id"] for entry in spec["items"]}:
        raise ValueError("Art and gameplay item IDs must match exactly")
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "runtime/build.ps1")], check=True)
    if PACK.resolve().parent != ROOT.resolve() or PACK.name != "pack":
        raise RuntimeError("Refusing unexpected generated pack path")
    if PACK.exists():
        shutil.rmtree(PACK)
    PACK.mkdir()
    shutil.copytree(ROOT / "art/Common", PACK / "Common")
    shutil.copytree(ROOT / "art/Server", PACK / "Server")
    language = ["interactionHints.ADOpen = Open equipment display"]
    for entry in spec["items"]:
        visual = art[entry["id"]]
        hitbox_id = visual.get("hitboxType", entry["id"])
        write(PACK / f"Server/Item/Block/Hitboxes/ArmorDisplays/{hitbox_id}.json", visual["hitbox"])
        metal = entry["style"] == "Metal"
        block = {
            "Material": "Solid", "DrawType": "Model", "Opacity": "Transparent",
            "CustomModel": visual["model"],
            "CustomModelTexture": [{"Texture": visual["texture"], "Weight": 1}],
            "VariantRotation": "NESW", "HitboxType": hitbox_id,
            "Gathering": {"Breaking": {"GatherType": "Metals" if metal else "Woods"}},
            "Support": {"Down" if entry["kind"] == "Stand" else "South": [{"FaceType": "Full"}]},
            "BlockEntity": {"Components": {
                "ItemContainerBlock": {"Capacity": entry["capacity"]},
                "ADDisplay": {"Kind": entry["kind"], "Style": entry["style"]},
            }},
            "Interactions": {"Use": "Open_Container"},
            "InteractionHint": "server.interactionHints.ADOpen",
            "BlockParticleSetId": "Stone" if metal else "Wood",
            "BlockSoundSetId": "Metal" if metal else "Wood",
            "PhysicalMaterialId": "Metal" if metal else "Wood",
            "ParticleColor": "#495966" if metal else "#755238",
        }
        item = {
            "TranslationProperties": {"Name": f"server.items.{entry['id']}.name", "Description": f"server.items.{entry['id']}.description"},
            "Categories": ["Furniture.Containers"],
            "Icon": visual["icon"], "MaxStack": 25,
            "PlayerAnimationsId": "Block", "ItemSoundSetId": "ISS_Blocks_Wood",
            "Tags": {"Type": ["Furniture"], "Family": ["ArmorDisplays"]},
            "Recipe": {
                "Input": entry["ingredients"],
                "BenchRequirement": [spec["crafting"]["bench"]],
                "KnowledgeRequired": spec["crafting"]["knowledgeRequired"],
                "TimeSeconds": spec["crafting"]["timeSeconds"],
                "OutputQuantity": 1,
            },
            "BlockType": block,
        }
        if visual.get("iconProperties"):
            item["IconProperties"] = visual["iconProperties"]
        write(PACK / f"Server/Item/Items/ArmorDisplays/{entry['id']}.json", item)
        language += [f"items.{entry['id']}.name = {entry['name']}", f"items.{entry['id']}.description = {entry['description']}"]
    lang_path = PACK / "Server/Languages/en-US/server.lang"
    lang_path.parent.mkdir(parents=True, exist_ok=True)
    lang_path.write_text("\n".join(language) + "\n", encoding="utf-8")
    write(PACK / "manifest.json", {
        "Group": "Steven", "Name": spec["name"], "Version": spec["version"],
        "Main": spec["main"], "Description": "Armor stands and wall weapon displays in timber/iron and steel styles. Native persistent item containers with equipment visuals.",
        "Authors": [{"Name": "Steven"}], "ServerVersion": ">=0.7.5 <0.8.0",
        "Dependencies": {"Hytale:ItemModule": "*", "Hytale:InteractionModule": "*"},
        "IncludesAssetPack": True,
    })
    write(PACK / "armor-displays-art-contract.json", contract)
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    output = release / spec["artifact"]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as jar:
        for path in sorted(PACK.rglob("*")):
            if path.is_file():
                jar.write(path, path.relative_to(PACK).as_posix())
        with zipfile.ZipFile(ROOT / "runtime/ArmorDisplaysRuntime.jar") as runtime:
            for name in runtime.namelist():
                if not name.endswith("/") and not name.startswith("META-INF/"):
                    jar.writestr(name, runtime.read(name))
    receipt = {
        "artifact": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "size": output.stat().st_size, "items": spec["items"], "status": "Built; native QA required",
    }
    write(release / "build-receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("artifact", "sha256", "size", "status")}, indent=2))
    return output


if __name__ == "__main__":
    build()
