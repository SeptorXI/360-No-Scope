"""Generate additive native barter trades for the installed embedded Patchwork.

Usage: python generate_shop_patches.py config.json output-directory
The output is a Server/Patchwork/Patches tree, never a vendor inventory override.
"""
from pathlib import Path, PurePosixPath
import argparse
import json
import re


def item_stack(value):
    if not isinstance(value, dict) or set(value) - {"ItemId", "Quantity"}:
        raise ValueError("Item stacks require only ItemId and Quantity")
    item_id, quantity = value.get("ItemId"), value.get("Quantity", 1)
    if not isinstance(item_id, str) or not re.fullmatch(r"[A-Za-z0-9_]+", item_id):
        raise ValueError(f"Invalid item ID {item_id!r}")
    if type(quantity) is not int or quantity < 1:
        raise ValueError(f"Quantity must be a positive integer: {quantity!r}")
    return {"ItemId": item_id, "Quantity": quantity}


def generate(config, output):
    report = []
    seen_ids = set()
    for shop in config["Shops"]:
        patch_id, target = shop["PatchId"], shop["Target"]
        if not re.fullmatch(r"[A-Za-z0-9_]+", patch_id) or patch_id in seen_ids:
            raise ValueError(f"PatchId must be a unique stable asset ID: {patch_id!r}")
        seen_ids.add(patch_id)
        path = PurePosixPath(target)
        if not target.startswith("Server/BarterShops/") or path.suffix != ".json" or ".." in path.parts:
            raise ValueError(f"Expected an existing native BarterShops JSON target: {target!r}")
        operations = []
        for index, trade in enumerate(shop["Trades"], 1):
            native_trade = {
                "Output": item_stack(trade["Output"]),
                "Input": [item_stack(stack) for stack in trade["Input"]],
                "Stock": trade.get("Stock", 1),
            }
            if not native_trade["Input"]:
                raise ValueError("A sale must have at least one input")
            if type(native_trade["Stock"]) is not int or native_trade["Stock"] < 1:
                raise ValueError("Stock must be a positive integer")
            operations.append({
                "Id": trade.get("OperationId", f"append-sale-{index:02}"),
                "Op": "Add", "Path": "/TradeSlots/-",
                "Value": {"Type": "Fixed", "Trade": native_trade},
            })
        if not operations:
            raise ValueError("Each shop patch must contain a trade")
        patch = {
            "Id": patch_id, "Target": target,
            "When": {"TargetExists": True},
            "Operations": operations,
        }
        destination = output / "Server" / "Patchwork" / "Patches" / f"{patch_id}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(patch, indent=2) + "\n", encoding="utf-8")
        report.append({"id": patch_id, "target": target, "appended_fixed_slots": len(operations),
                       "output": destination.as_posix()})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = generate(json.loads(args.config.read_text(encoding="utf-8-sig")), args.output)
    print(json.dumps(result, indent=2))
