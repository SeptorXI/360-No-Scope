import os
"""Audit packaged furniture, recipes, native references and authored geometry."""
from pathlib import Path
import hashlib
import json
import math
import zipfile
from PIL import Image
import io

ROOT = Path(__file__).resolve().parent


def main():
    spec = json.loads((ROOT / "content/display-spec.json").read_text())
    path = ROOT / "release" / spec["artifact"]
    checks = 0

    def check(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            raise AssertionError(message)

    with zipfile.ZipFile(path) as jar, zipfile.ZipFile(os.environ['HYTALE_ASSETS_ZIP']) as native:
        names = jar.namelist()
        native_names = set(native.namelist())
        check(len(names) == len(set(names)), "Duplicate JAR entries")
        check(not any("probe" in n.lower() or n.startswith("local/") for n in names), "QA code leaked into release")
        manifest = json.loads(jar.read("manifest.json"))
        check(manifest["Main"].replace(".", "/") + ".class" in names, "Missing plugin entrypoint")
        check(manifest["IncludesAssetPack"], "Asset pack flag missing")
        contract = json.loads(jar.read("armor-displays-art-contract.json"))
        art = {e["id"]: e for e in contract["assets"]}
        language = jar.read("Server/Languages/en-US/server.lang").decode()
        for name in names:
            if name.startswith("Server/Models/") and name.endswith(".json"):
                entity_model = json.loads(jar.read(name))
                for key in ("Model", "Texture"):
                    value = entity_model[key]
                    check(value.startswith(("Characters/", "NPC/", "Items/", "VFX/")), "Entity model uses unsupported native asset root")
                    check("Common/" + value in names, "Entity model asset missing: " + value)
        for entry in spec["items"]:
            item = json.loads(jar.read(f"Server/Item/Items/ArmorDisplays/{entry['id']}.json"))
            block = item["BlockType"]
            components = block["BlockEntity"]["Components"]
            check(components["ADDisplay"] == {"Kind": entry["kind"], "Style": entry["style"]}, "Wrong display component")
            check(components["ItemContainerBlock"]["Capacity"] == entry["capacity"], "Wrong capacity")
            check(block["Interactions"]["Use"] == "Open_Container", "Native container interaction missing")
            check(item["Recipe"]["Input"] == entry["ingredients"], "Recipe costs differ from source")
            check(item["Recipe"]["BenchRequirement"][0]["Id"] == "Furniture_Bench", "Recipe bench mismatch")
            check(block["VariantRotation"] == "NESW", "Cardinal rotation missing")
            check(len(block["Support"]) == 1, "Support missing")
            check(("Down" in block["Support"]) == (entry["kind"] == "Stand"), "Wrong support class")
            for key in ("name", "description"):
                check(f"items.{entry['id']}.{key} = " in language, "Missing translation")
            for key, native_prefix in (("BlockSoundSetId", "Server/Item/Block/Sounds/"), ("PhysicalMaterialId", "Server/Item/Block/PhysicalMaterials/"), ("BlockParticleSetId", "Server/Particles/Block/")):
                if key != "BlockParticleSetId":
                    check(native_prefix + block[key] + ".json" in native_names, "Missing native reference " + block[key])
            visual = art[entry["id"]]
            for key in ("model", "texture", "icon"):
                check("Common/" + visual[key] in names, "Missing packaged art " + visual[key])
            icon = Image.open(io.BytesIO(jar.read("Common/" + visual["icon"])))
            check(icon.size == (64, 64) and icon.mode == "RGBA", "Inventory icons require 64x64 RGBA")
            check(icon.getchannel("A").getbbox() is not None, "Empty inventory icon")
            texture = Image.open(io.BytesIO(jar.read("Common/" + visual["texture"])))
            model = json.loads(jar.read("Common/" + visual["model"]))
            ids = set()

            def node(n):
                check(n["id"] not in ids, "Duplicate model node ID")
                ids.add(n["id"])
                q = n.get("orientation", {"x": 0, "y": 0, "z": 0, "w": 1})
                check(abs(sum(v * v for v in q.values()) - 1) < 0.001, "Unnormalized quaternion")
                shape = n.get("shape")
                if shape and shape.get("type") != "none" and shape.get("visible", True):
                    check(shape["type"] in ("box", "quad"), "Unsupported primitive")
                    for v in shape["settings"]["size"].values():
                        check(v > 0 and math.isfinite(v), "Invalid primitive size")
                    for face in shape.get("textureLayout", {}).values():
                        offset = face["offset"]
                        check(0 <= offset["x"] < texture.width and 0 <= offset["y"] < texture.height, "UV outside texture")
                for child in n.get("children", []):
                    node(child)

            for n in model["nodes"]:
                node(n)
            check(len(ids) >= 5, "Furniture geometry unexpectedly empty")
            hitbox_id = visual.get("hitboxType", entry["id"])
            hitbox = json.loads(jar.read(f"Server/Item/Block/Hitboxes/ArmorDisplays/{hitbox_id}.json"))
            for box in hitbox["Boxes"]:
                check(all(box["Min"][axis] < box["Max"][axis] for axis in "XYZ"), "Invalid collision box")
        item_assets = [n for n in names if n.startswith("Server/Item/Items/")]
        check(len(item_assets) == 6, "Exactly six furniture item assets required")
    result = {"artifact": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "checks": checks, "failures": 0, "scope": "Static packaging, source contract, geometry, icons and native reference checks"}
    (ROOT / "release/static-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
