# Armor Displays

Armor Displays adds an armor stand, a single wall weapon holder and a three-weapon wall rack in two styles: wood with forged iron, and metal. It is a separate plugin in this repository and works with native weapons as well as compatible modded guns. Installing the gun plugin is optional.

## Craft and place

Craft the displays at the **Furniture Workbench, Storage tab, tier 1**. Each recipe makes one display in two seconds and has no knowledge unlock requirement. Wood costs accept the native `Wood_Trunk` resource type.

| Display | Item ID | Ingredients |
| --- | --- | --- |
| Wood-and-Iron Armor Stand | `AD_Armor_Stand_Wood` | 8 wood trunks, 2 iron bars |
| Metal Armor Stand | `AD_Armor_Stand_Metal` | 8 iron bars, 2 copper bars |
| Wood-and-Iron Wall Weapon Holder | `AD_Wall_Holder_Wood` | 3 wood trunks, 1 iron bar |
| Metal Wall Weapon Holder | `AD_Wall_Holder_Metal` | 3 iron bars, 1 copper bar |
| Wood-and-Iron Wall Weapon Rack | `AD_Wall_Rack_Wood` | 8 wood trunks, 3 iron bars |
| Metal Wall Gun Rack | `AD_Wall_Rack_Metal` | 8 iron bars, 2 copper bars |

Place armor stands on a solid floor. Mount holders and racks on a solid wall. Placement supports the four cardinal rotations. Use the player's configured **Use** binding to open a display's native inventory; this plugin does not assign a replacement key.

## Inventory order

| Display | Slots, from left to right in the inventory |
| --- | --- |
| Armor stand | Head, Chest, Hands, Legs, Main hand, Off hand |
| Wall holder | Weapon |
| Wall rack | Bottom weapon, Middle weapon, Top weapon |

Armor slots accept the corresponding native armor type. Weapon slots accept compatible weapon items, including modded guns. Each slot holds one item. Weapons display horizontally on holders and racks, with their models fitted to the available space.

## Storage and persistence

The native `ItemContainerBlock` holds the actual equipment. Complete ItemStacks retain their item ID, quantity, durability, maximum durability and metadata, including enchantment data and the guns' loaded-ammunition data. The plugin does not rebuild stored equipment from an item ID alone.

Visible equipment is a transient, non-pickup representation of that inventory. It is rebuilt after a restart and is never a second collectible copy. Breaking or removing a display follows native container handling. The saved `ADDisplay` component and the six item IDs above are compatibility identifiers and should remain stable.

The wooden and metal styles have the same storage behavior. The furniture art contains no example weapon or armor meshes; the runtime displays the equipment placed inside it.

## Source and build

The repository keeps runtime Java under `modules/displays/src/java/`, pack-ready assets under `modules/displays/resources/`, and the display design specification under `modules/displays/design/`. Curated editable art and its historical authoring tools are under `authoring/armor-displays/`.

The normal build compiles Java 25 and packages the committed resources. It needs Python 3 and a locally supplied Hytale server API JAR; it does not need Pillow or Blender. See [installation and build instructions](INSTALL.md).

The original furniture geometry and pixel atlases are authored assets. The invisible equipment actor preserves native Mannequin bone names and pivots for attachment compatibility, with every visible mesh removed and a transparent replacement texture. Optional historical art regeneration requires a local Hytale `Assets.zip`; that archive is not distributed in this repository.

## Accepted validation

The imported baseline is `Armor-Displays-0.1.0.jar`, 137,395 bytes, SHA-256:

```text
e5265db3dc846180d4965266044bc36379cb898aab6910f132bf406c516ce7dc
```

It passed **3,929 static checks and 7,261 isolated native checks, with zero recorded fixture failures**. Native tests covered a vanilla setup and a copied full mod stack with the 54-gun arsenal, including a graceful process restart in each setup. They checked all six assets and recipes, inventory filters and transfers, full ItemStack BSON persistence, placement and cardinal anchors, transient visual reconstruction and cleanup, and native container removal returning the stored fixture items.

Those tests used disposable loopback servers, copied QA terrain and synthetic item metadata. They did not simulate real client input or PlayerRef interaction. In-game equipment pose/alignment, inventory usability, simultaneous player access and protection-mod behavior still need a client playtest. The accepted server API JAR was pinned to SHA-256 `fb80f84b1079643ee370fec1d9139438eefc34e071143ebd7ac0ff0be1e16871`.

The baseline hash identifies the previously validated artifact. A fresh source build has its own hash and validation status. Creating this repository and its documentation does not install anything or change the running server.
