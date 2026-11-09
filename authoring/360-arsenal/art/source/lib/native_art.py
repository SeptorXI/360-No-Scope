"""Original Ranger sniper art. Run with Python 3 + Pillow; no external art inputs.

Authoring coordinates: -X muzzle, +Y up, Z width. One unit is one texture pixel.
The native attachment transforms below are interface/alignment data only.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
from pathlib import Path
import random
import uuid

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = dict(x=0, y=0, z=0, w=1)
HANDLE_Q = dict(x=0.18301, y=0.68301, z=0.18301, w=0.68301)
FACE_DIMS = {
    "front": (0, 1), "back": (0, 1), "left": (2, 1),
    "right": (2, 1), "top": (0, 2), "bottom": (0, 2),
}
BB_FACE = {"front": "north", "back": "south", "left": "west", "right": "east", "top": "up", "bottom": "down"}


def vec(v):
    return dict(zip("xyz", v))


def quaternion(axis="z", degrees=0):
    q = dict(IDENTITY)
    q[axis] = round(math.sin(math.radians(degrees / 2)), 8)
    q["w"] = round(math.cos(math.radians(degrees / 2)), 8)
    return q


def uid(value):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "original-ranger-snipers/" + value))


THEMES = [
    dict(id="Tier01", name="Wildwood Surveyor", zone="Emerald Wilds", family="Ballistic", seed=101,
         colors=dict(steel="#3b4950", edge="#788a8b", dark="#182329", wood="#71462d", woodlight="#b07944", trim="#bc7543", cloth="#52633b", pale="#a3a77c", glass="#73c5aa", glow="#72d9a6", rubber="#292824", warning="#dcaf57")),
    dict(id="Tier02", name="Dunewatch Longshot", zone="Howling Sands", family="Ballistic", seed=202,
         colors=dict(steel="#5d5b50", edge="#aaa180", dark="#282c2e", wood="#7f6139", woodlight="#be9b5d", trim="#c2954e", cloth="#c3af7b", pale="#e5d6aa", glass="#59c8c0", glow="#a4e6dd", rubber="#453e32", warning="#df8741")),
    dict(id="Tier03", name="Frostline Sentinel", zone="Whisperfrost", family="Ballistic", seed=303,
         colors=dict(steel="#315f87", edge="#70a5bf", dark="#14273b", wood="#53717c", woodlight="#99b9bc", trim="#809ca8", cloth="#b0c5ce", pale="#e5eff0", glass="#66d9f1", glow="#a1f2fc", rubber="#334754", warning="#efaf5c")),
    dict(id="Tier04", name="Mournhollow Epitaph", zone="Mournhollow", family="Energized ballistic", seed=404,
         colors=dict(steel="#343141", edge="#8f929d", dark="#171b29", wood="#4d3547", woodlight="#8a6178", trim="#b6b7ba", cloth="#514a67", pale="#ddd5d1", glass="#c5a8e6", glow="#b48ae5", rubber="#24212f", warning="#a470cd")),
    dict(id="Tier05", name="Gobliterator's Requiem", item_id="Weapon_Crossbow_Deepworks_Railspike", zone="Deepworks", family="Rail", seed=505,
         colors=dict(steel="#454b4d", edge="#7d8587", dark="#20282a", wood="#58452f", woodlight="#9b7b4b", trim="#bd7d4d", cloth="#7d764b", pale="#c2c3a4", glass="#f5bd63", glow="#f3a34b", railglow="#63d9ea", rubber="#313939", warning="#e6b949")),
    dict(id="Tier06", name="Dawnpiercer, Last Light of Luminia", item_id="Weapon_Crossbow_Luminia_Dawnpiercer", zone="Luminia", family="Laser", seed=606,
         colors=dict(steel="#bfcfd8", edge="#f2e7c2", dark="#283249", wood="#66548b", woodlight="#ac86e1", trim="#c8a35e", cloth="#688299", pale="#f0f0e3", glass="#b0e4ff", glow="#99edff", rubber="#414359", warning="#d9bbff")),
    dict(id="Tier07", name="Nameless Covenant", zone="Major Dungeons variant", family="Relic rifle", seed=707, variant=True,
         colors=dict(steel="#373d46", edge="#7d8794", dark="#17212a", wood="#382b48", woodlight="#8e6ab6", trim="#b3b8c3", cloth="#52475e", pale="#d2d3d3", glass="#b899e5", glow="#a479e2", rubber="#272832", warning="#8e3e52")),
    dict(id="Tier08", name="Labyrinth Threadkeeper", zone="Fullmetal variant", family="Crystal marksman", seed=808, variant=True,
         colors=dict(steel="#505963", edge="#b4c0c8", dark="#1e2832", wood="#37424d", woodlight="#72869a", trim="#8596a6", cloth="#3d4750", pale="#d8e4e7", glass="#77e1fa", glow="#39cde9", rubber="#29323a", warning="#8de8f5")),
    dict(id="Tier09", name="Skybound Farwatch", zone="Tritale Airshop variant", family="Artifact scout", seed=909, variant=True,
         colors=dict(steel="#547d9b", edge="#86a9c2", dark="#283e4c", wood="#493a30", woodlight="#816040", trim="#bc9858", cloth="#9c4439", pale="#d2cbb0", glass="#83ce7a", glow="#70c974", rubber="#3d302b", warning="#d2b466")),
]


class Rifle:
    def __init__(self, theme):
        self.theme, self.parts = theme, []

    def box(self, name, center, size, material="steel", rotation=(0, 0, 0), detail=""):
        assert all(v > 0 and int(v) == v for v in size), (name, size)
        self.parts.append(dict(name=name, center=list(center), size=list(size), material=material,
                               rotation=list(rotation), detail=detail))

    def paired(self, name, center, size, material, separation, rotation=(0, 0, 0), detail=""):
        for side in (-1, 1):
            c = list(center); c[2] += side * separation
            self.box(name + ("_L" if side < 0 else "_R"), c, size, material, rotation, detail)

    def scope(self, x=-2, y=14, length=25, size=7, trim="trim", tech=False):
        self.box("Scope_Rail", (x, 7, 0), (length - 2, 2, 5), "dark")
        for n, dx in enumerate((-length * .28, length * .28)):
            self.box("Scope_Mount_"+str(n), (x+dx, 10, 0), (3, 6, 5), trim)
        self.box("Scope_Tube", (x, y, 0), (length, size-2, size), "dark")
        self.box("Scope_Tube_Crown", (x, y, 0), (length, size, size-2), "steel")
        for n, dx in enumerate((-length/2+1, length/2-1)):
            self.box("Scope_Rim_"+str(n), (x+dx, y, 0), (3, size+2, size), trim)
            self.box("Scope_Rim_Crown_"+str(n), (x+dx, y, 0), (3, size, size+2), trim)
        for n, dx in enumerate((-length/2-.55, length/2+.55)):
            self.box("Scope_Lens_"+str(n), (x+dx, y, 0), (1, size-2, size-2), "glass", detail="lens")
        self.box("Scope_Elevation", (x, y+size/2+1, 0), (5, 3, 5), trim)
        self.box("Scope_Windage", (x+2, y, -size/2-1), (4, 4, 3), "dark")
        if tech:
            self.paired("Scope_Status", (x-3, y, 0), (4, 2, 1), "glow", size/2+.05, detail="energy")

    def trigger(self):
        self.box("Trigger_Guard_Front", (2, -11, 0), (2, 7, 4), "dark", (0, 0, -12))
        self.box("Trigger_Guard_Bow", (6, -14, 0), (9, 2, 4), "dark")
        self.box("Trigger", (5, -9, 0), (1, 4, 2), "trim", (0, 0, 15))

    def muzzle(self, x, y=2, width=7, length=5, material="trim", open_core=False):
        self.box("Muzzle_Housing", (x, y, 0), (length, width-2, width), material)
        self.box("Muzzle_Housing_Crown", (x, y, 0), (length, width, width-2), material)
        self.box("Muzzle_Bore", (x-length/2-.03, y, 0), (1, width-4, width-4), "glow" if open_core else "dark", detail="energy" if open_core else "bore")


def make_rifle(t):
    r = Rifle(t); i = int(t["id"][-2:])
    r.trigger()
    if i == 1:
        r.box("Walnut_Receiver", (0, 0, 0), (25, 9, 8), "wood", detail="wood")
        r.box("Steel_Bolt_Receiver", (-1, 4, 0), (26, 4, 7), "steel")
        r.box("Long_Barrel", (-37, 2, 0), (48, 4, 4), "steel")
        r.box("Walnut_Forestock", (-22, -2, 0), (24, 7, 7), "woodlight", detail="wood")
        r.box("Forestock_Nose", (-35, -1, 0), (4, 8, 8), "trim")
        for x in (-29, -19): r.box("Leather_Band_"+str(x), (x, -1, 0), (3, 8, 8), "cloth", detail="cloth")
        r.box("Stock_Neck", (17, -1, 0), (17, 7, 6), "wood", (0, 0, -13), "wood")
        r.box("Stock_Body", (30, -4, 0), (20, 12, 7), "wood", detail="wood")
        r.box("Stock_Comb", (28, 2, 0), (16, 3, 6), "woodlight", detail="wood")
        r.box("Recoil_Pad", (40, -5, 0), (3, 14, 8), "rubber", (0, 0, -5))
        r.paired("Stock_Green_Inlay", (29, -2, 0), (12, 4, 1), "cloth", 3.6, detail="inlay")
        r.box("Copper_Bolt", (6, 3, -6), (3, 3, 6), "trim")
        r.box("Bolt_Knob", (6, 1, -9), (4, 5, 4), "dark")
        r.scope(x=-1, y=14, length=25, size=7)
        r.muzzle(-61, width=7, length=5)
        r.box("Sling_Front", (-27, -7, 0), (3, 3, 3), "trim")
        r.box("Sling_Rear", (31, -12, 0), (3, 3, 3), "trim")
    elif i == 2:
        r.box("Bronze_Receiver", (0, 0, 0), (28, 11, 9), "steel")
        r.paired("Receiver_Plates", (-1, 1, 0), (24, 7, 1), "trim", 4.6, detail="panel")
        r.box("Long_Desert_Barrel", (-42, 2, 0), (53, 5, 5), "dark")
        r.box("Vented_Forestock", (-27, -1, 0), (28, 8, 8), "trim")
        for k in range(6):
            r.paired("Heat_Vent_"+str(k), (-38+k*4, 1, 0), (2, 4, 1), "dark", 4.1)
        for x in (-26,-17): r.box("Sand_Cloth_"+str(x), (x,-2,0), (4,9,9), "cloth", (0,0,-3), "cloth")
        r.box("Stock_Spine", (26, 2, 0), (29, 4, 6), "trim", (0,0,-3))
        r.box("Stock_Lower", (28, -7, 0), (25, 3, 5), "steel", (0,0,12))
        r.box("Stock_Butt", (42, -3, 0), (5, 17, 8), "rubber", (0,0,-5))
        r.box("Stock_Cheek_Cloth", (30, 4, 0), (16, 4, 7), "cloth", detail="cloth")
        r.box("Magazine", (-7, -11, 0), (9, 12, 6), "steel", (0,0,-5))
        r.box("Magazine_Base", (-7.5,-17,0), (11,3,7), "trim")
        r.paired("Folded_Bipod", (-33,-7,0), (19,3,2), "steel", 4.7, (0,0,-5))
        r.scope(x=-4,y=15,length=28,size=8,trim="trim")
        r.muzzle(-69,width=9,length=9)
        r.paired("Brake_Ports", (-70,2,0), (4,3,1), "dark", 4.6)
        r.box("Bolt_Lug", (9,3,-7), (6,3,6), "trim")
    elif i == 3:
        r.box("Cobalt_Receiver", (0,0,0), (29,10,9), "steel")
        r.paired("White_Receiver_Plates", (-1,1,0), (24,6,1), "pale",4.6,detail="panel")
        r.box("Barrel", (-44,2,0), (56,5,5), "dark")
        r.box("Snow_Shroud", (-27,0,0), (29,9,8), "pale")
        for k in range(5): r.paired("Cobalt_Vent_"+str(k), (-38+k*5,2,0), (3,3,1),"steel",4.15)
        r.box("Forehand_Cloth", (-26,-4,0), (18,4,9),"cloth",detail="cloth")
        r.box("Stock_Top_Spine", (27,3,0), (30,5,6), "steel")
        r.box("Stock_Lower_Arm", (26,-7,0), (27,4,6), "steel", (0,0,13))
        r.box("Stock_Cheek_Pad", (30,6,0), (18,4,7), "pale", detail="panel")
        r.box("Adjustable_Butt", (43,-2,0), (4,18,8), "dark")
        r.box("Butt_White_Outer", (45,-2,0), (2,16,9), "pale")
        r.box("Magazine", (-5,-10,0), (10,10,6),"dark")
        r.paired("Magazine_Inlay",(-5,-10,0),(6,5,1),"steel",3.1)
        r.box("Bolt_Housing",(7,4,-6),(6,4,4),"steel")
        r.box("Bolt_Pull",(9,1,-8),(3,7,3),"pale")
        r.scope(x=-3,y=16,length=31,size=8,trim="pale")
        r.box("Suppressor",(-69,2,0),(17,8,8),"steel")
        r.box("Suppressor_Band",(-67,2,0),(3,9,9),"pale")
        r.muzzle(-78,width=8,length=3,material="pale")
        r.paired("Folded_Snow_Bipod",(-34,-7,0),(22,3,2),"steel",5,(0,0,-7))
    elif i == 4:
        r.box("Blackiron_Receiver", (0,0,0),(30,12,10),"dark")
        r.paired("Reliquary_Frame",(-2,1,0),(26,9,1),"trim",5.15)
        r.paired("Reliquary_Recess",(-2,1,0),(21,6,1),"wood",5.75)
        r.paired("Reliquary_Core",(-2,1,0),(10,4,1),"glow",6.3,detail="energy")
        for k,x in enumerate((-13,-7,6,11)):
            r.paired("Silver_Rib_"+str(k),(x,1,0),(2,10,1),"trim",6.9)
        r.box("Rifled_Energized_Barrel",(-45,2,0),(58,5,5),"steel")
        r.box("Cathedral_Forestock",(-28,-2,0),(30,8,9),"dark")
        r.paired("Barrel_Light_Rail",(-30,2,0),(31,2,1),"glow",4.8,detail="energy")
        for k,x in enumerate((-41,-32,-23)):
            r.box("Barrel_Silver_Brace_"+str(k),(x,1,0),(3,11,11),"trim")
            r.box("Brace_Crest_"+str(k),(x,8,0),(3,5,4),"steel",(0,0,-12))
        r.box("Stock_Spine",(27,1,0),(28,6,6),"steel")
        r.box("Stock_Cowl",(31,-2,0),(19,12,8),"dark")
        r.paired("Stock_Silver_Inlay",(30,-1,0),(14,6,1),"trim",4.1,detail="inlay")
        r.paired("Stock_Seal",(31,-1,0),(5,5,1),"woodlight",4.7,(0,0,45))
        r.box("Stock_Heel",(43,-4,0),(4,18,9),"trim",(0,0,-8))
        r.box("Reliquary_Magazine",(-5,-12,0),(12,13,7),"steel")
        r.paired("Magazine_Seals",(-5,-12,0),(6,6,1),"glow",3.7,detail="energy")
        r.scope(x=-2,y=18,length=32,size=8,trim="trim",tech=True)
        r.muzzle(-76,width=11,length=8,material="trim")
        r.box("Muzzle_Crown",(-76,9,0),(5,5,5),"dark",(0,0,45))
        r.box("Bolt_Handle",(9,2,-9),(4,5,7),"trim")
    elif i == 5:
        r.box("Industrial_Receiver", (1,0,0),(31,14,12),"steel")
        r.paired("Armored_Receiver_Plate",(0,2,0),(28,10,1),"trim",6.1,detail="panel")
        r.paired("Receiver_Hazard",(-4,-1,0),(12,5,1),"warning",6.7,detail="hazard")
        r.box("Rail_Core",(-43,2,0),(58,4,4),"railglow",detail="energy")
        r.paired("Split_Acceleration_Rail",(-45,2,0),(61,5,4),"dark",5)
        r.paired("Rail_Outer_Stripe",(-45,2,0),(55,2,1),"trim",7.1)
        for k,x in enumerate((-24,-35,-46,-57)):
            r.box("Coil_Bridge_"+str(k),(x,2,0),(4,12,15),"trim")
            r.box("Coil_Insulator_"+str(k),(x,2,0),(2,13,13),"steel")
            r.paired("Coil_Windings_"+str(k),(x,2,0),(4,8,1),"glow",7.6,detail="energy")
        r.box("Underbarrel_Grip",(-24,-10,0),(14,10,8),"rubber",(0,0,-8))
        r.box("Rail_Muzzle_Collar",(-77,2,0),(7,11,16),"steel")
        r.paired("Muzzle_Split_Jaw",(-83,2,0),(10,6,4),"trim",5)
        r.box("Stock_Spine",(30,3,0),(31,7,8),"steel")
        r.box("Stock_Piston",(30,-6,0),(26,4,4),"trim",(0,0,8))
        r.box("Stock_Industrial_Butt",(47,-1,0),(6,22,11),"dark",(0,0,-6))
        r.box("Cheek_Pad",(31,8,0),(20,4,9),"rubber")
        r.box("Battery_Box",(-2,-15,0),(15,16,9),"dark")
        r.paired("Battery_Cage",(-2,-15,0),(11,10,1),"steel",4.6,detail="panel")
        r.paired("Battery_Hazard",(-2,-16,0),(8,4,1),"warning",5.2,detail="hazard")
        r.box("Pressure_Tank",(14,0,-10),(8,10,6),"steel")
        r.box("Tank_Cap",(14,6,-10),(6,2,5),"trim")
        r.scope(x=-1,y=20,length=29,size=10,trim="dark",tech=True)
        r.box("Scope_Rangefinder",(-8,25,0),(12,4,8),"steel")
        r.box("Rangefinder_Lens",(-14.5,25,0),(1,2,4),"glass",detail="lens")
    elif i == 6:
        r.box("Void_Receiver",(0,0,0),(30,10,10),"dark")
        r.paired("Pale_Receiver_Shell",(-1,2,0),(25,6,1),"pale",5.1,detail="panel")
        r.paired("Receiver_Void_Inlay",(-2,2,0),(14,2,1),"glow",5.7,detail="energy")
        r.box("Emitter_Core",(-44,2,0),(58,4,4),"glow",detail="energy")
        r.paired("Emitter_Prongs",(-48,2,0),(66,6,4),"steel",5.5)
        r.paired("Prong_Pale_Armor",(-42,3,0),(42,4,1),"pale",7.65)
        r.paired("Prong_Energy_Channels",(-48,2,0),(61,2,1),"glow",3.35,detail="energy")
        for k,x in enumerate((-22,-45,-67)):
            r.box("Emitter_Collar_"+str(k),(x,2,0),(4,11,15),"trim")
            r.box("Emitter_Collar_Dark_"+str(k),(x-.1,2,0),(2,9,16),"dark")
        r.paired("Muzzle_Crown_Prongs",(-83,3,0),(14,7,4),"pale",5.5,(0,0,-10))
        r.box("Muzzle_Focusing_Crystal",(-80,2,0),(9,4,4),"woodlight",(45,0,0),"energy")
        r.box("Forehand_Bridge",(-27,-6,0),(26,6,8),"steel")
        r.box("Forehand_Inlay",(-27,-9,0),(18,2,6),"pale")
        r.box("Stock_Top_Arc",(29,5,0),(32,5,7),"pale",(0,0,-5))
        r.box("Stock_Lower_Arc",(29,-5,0),(31,4,6),"steel",(0,0,15))
        r.box("Stock_Fork_Butt",(47,-1,0),(5,19,9),"dark",(0,0,-7))
        r.box("Stock_Heel_Cap",(49,-8,0),(5,6,10),"pale")
        r.box("Stock_Top_Cap",(48,7,0),(6,4,9),"pale")
        r.box("Power_Cell",(-2,-13,0),(12,14,8),"steel",(0,0,-8))
        r.paired("Cell_Crystal",(-2,-12,0),(6,8,1),"woodlight",4.4,(0,0,-8),"energy")
        r.box("Cell_End_Cap",(-3,-20,0),(13,3,9),"pale",(0,0,-8))
        r.scope(x=0,y=18,length=32,size=8,trim="pale",tech=True)
        r.box("Scope_Void_Crown",(-5,24,0),(18,3,4),"steel")
        r.paired("Scope_Crown_Inlay",(-5,24,0),(12,1,1),"glow",2.1,detail="energy")
    elif i == 7:
        # A narrow cathedral rifle: the hollow arched receiver and prayer skull
        # are original geometry inspired by the installed dark-silver/altar motifs.
        r.box("Blackiron_Breech", (1,-2,0), (30,7,9), "dark")
        r.box("Receiver_Altar_Floor", (-1,-7,0), (30,3,12), "steel")
        r.box("Receiver_Arch_Left", (-12,1,0), (4,15,11), "steel", (0,0,-11))
        r.box("Receiver_Arch_Right", (11,1,0), (4,15,11), "steel", (0,0,11))
        r.box("Receiver_Arch_Crown_L", (-7,8,0), (15,4,11), "dark", (0,0,24))
        r.box("Receiver_Arch_Crown_R", (5,8,0), (15,4,11), "dark", (0,0,-24))
        r.box("Receiver_Crown_Mark", (-1,11,0), (3,3,2), "warning", (0,0,45))
        r.paired("Caged_Violet_Eye", (-1,1,0), (11,7,1), "glow", 5.7, detail="eye")
        r.paired("Silver_Eye_Lintel", (-1,5,0), (13,2,1), "trim", 6.35)
        r.paired("Silver_Eye_Sill", (-1,-3,0), (13,2,1), "trim", 6.35)
        for k,x in enumerate((-6,4)):
            r.paired("Silver_Cage_Bar_"+str(k),(x,1,0),(2,10,1),"trim",6.4)
        r.box("Cathedral_Barrel",(-40,1,0),(55,5,5),"dark")
        r.box("Barrel_Silver_Spine",(-41,4,0),(53,2,4),"trim")
        r.box("Cedar_Understock",(-29,-4,0),(32,5,7),"wood")
        for k,x in enumerate((-24,-41,-57)):
            r.box("Barrel_Dark_Column_"+str(k),(x,1,0),(4,10,9),"steel")
            r.box("Barrel_Column_Cap_"+str(k),(x,6,0),(6,2,10),"trim")
        r.muzzle(-69,y=1,width=9,length=8,material="trim")
        r.paired("Muzzle_Hooked_Wing",(-69,5,0),(7,3,2),"steel",4,(0,0,-25))
        r.box("Stock_Neck",(21,-2,0),(18,6,7),"steel",(0,0,-8))
        r.box("Stock_Relic_Frame",(31,-4,0),(18,13,8),"dark")
        r.paired("Stock_Prayer_Plate",(31,-3,0),(11,9,1),"trim",4.15,detail="skull")
        r.box("Stock_Curved_Heel",(41,-7,0),(4,18,9),"steel",(0,0,-14))
        r.box("Stock_Silver_Comb",(31,4,0),(17,3,7),"trim")
        r.box("Reliquary_Magazine",(-3,-13,0),(10,10,6),"steel")
        r.paired("Magazine_Seal",(-3,-13,0),(6,6,1),"woodlight",3.2,(0,0,45))
        # A short framed optic gives this rifle a different upper silhouette.
        r.box("Relic_Optic_Rail",(-6,9,0),(24,2,5),"trim")
        r.box("Relic_Optic_Tube",(-6,14,0),(24,5,6),"dark")
        for k,x in enumerate((-17,5)):
            r.box("Relic_Optic_Hood_"+str(k),(x,14,0),(3,9,8),"trim")
            r.box("Relic_Optic_Lens_"+str(k),(x+(-1.6 if k==0 else 1.6),14,0),(1,5,5),"glass",detail="lens")
        r.box("Relic_Optic_Peak",(-6,18,0),(15,3,4),"steel")
        r.box("Relic_Optic_Seal",(-6,21,0),(3,4,3),"trim",(0,0,45))
        r.box("Bolt_Prayer_Lever",(10,1,-8),(4,6,7),"trim")
    elif i == 8:
        # Fullmetal: a machined bullpup chassis, faceted cyan inserts, and original
        # maze etching. No vendor geometry or texture pixels are used.
        r.box("Fullmetal_Chassis",(0,0,0),(33,11,10),"dark")
        r.paired("Chrome_Maze_Plate",(-2,1,0),(29,8,1),"steel",5.2,detail="maze")
        r.box("Receiver_Angled_Nose",(-18,1,0),(10,9,9),"steel",(0,0,-19))
        r.box("Crystal_Breech",(-5,3,0),(16,5,6),"glow",(0,0,-10),"crystal")
        r.paired("Receiver_Chrome_Cheek",(-3,6,0),(23,2,2),"edge",4.5)
        r.box("Thread_Barrel",(-43,2,0),(51,4,4),"dark")
        r.box("Barrel_Upper_Shroud",(-32,5,0),(29,4,8),"steel")
        r.box("Barrel_Lower_Shroud",(-33,-2,0),(31,4,8),"dark")
        r.paired("Shroud_Crystal_Insert",(-33,2,0),(25,3,1),"glow",4.35,detail="crystal")
        r.paired("Shroud_Faceted_Edge",(-45,3,0),(12,3,2),"edge",4,(0,0,-17))
        for k,x in enumerate((-24,-31,-38)):
            r.paired("Shroud_Cooling_Notch_"+str(k),(x,6,0),(3,2,1),"dark",4.15)
        r.box("Barrel_Exposed_Flute",(-59,2,0),(19,5,5),"steel")
        r.paired("Chrome_Barrel_Flutes",(-60,2,0),(17,2,1),"edge",2.65)
        r.box("Crystal_Muzzle_Case",(-71,2,0),(8,8,8),"dark",(45,0,0))
        r.box("Crystal_Muzzle_Facet",(-75,2,0),(3,6,6),"edge",(45,0,0))
        r.box("Crystal_Muzzle_Bore",(-77,2,0),(1,3,3),"dark",detail="bore")
        r.box("Fullmetal_Stock_Block",(27,0,0),(25,12,8),"steel")
        r.box("Stock_Upper_Slope",(27,7,0),(23,4,8),"dark",(0,0,-8))
        r.box("Stock_Butt",(42,-2,0),(4,18,10),"rubber",(0,0,-6))
        r.paired("Stock_Maze_Engraving",(28,1,0),(17,7,1),"steel",4.25,detail="maze")
        r.paired("Stock_Cyan_Corner",(36,-3,0),(6,2,1),"glow",4.8,(0,0,22),"energy")
        r.box("Bullpup_Magazine",(26,-13,0),(10,16,6),"dark",(0,0,-9))
        r.box("Magazine_Chrome_Foot",(25,-21,0),(12,3,7),"edge",(0,0,-9))
        r.box("Forehand_Angled_Grip",(-23,-10,0),(9,12,7),"rubber",(0,0,-24))
        r.box("Forehand_Chrome_Cap",(-25,-15,0),(7,3,8),"steel",(0,0,-24))
        r.scope(x=-7,y=15,length=23,size=7,trim="edge",tech=True)
        r.box("Scope_Crystal_Rangefinder",(-8,20,0),(11,3,4),"glow",detail="crystal")
    else:
        # Tritale-inspired materials: dark wood, red wraps, blue steel tips and an
        # ivory/green carved artifact. The actual rifle geometry is new.
        r.box("Darkwood_Receiver",(0,0,0),(26,10,9),"wood",detail="wood")
        r.box("Blue_Steel_Breech",(-2,5,0),(27,3,8),"steel")
        r.box("Blue_Steel_Barrel",(-39,2,0),(54,4,4),"steel")
        r.box("Carved_Darkwood_Forestock",(-26,-2,0),(27,7,8),"wood",detail="wood")
        for k,x in enumerate((-36,-26,-16)):
            r.box("Red_Forestock_Wrap_"+str(k),(x,-1,0),(4,9,9),"cloth",(0,0,4),"cloth")
        r.box("Forestock_Blue_Nose",(-42,-1,0),(5,9,8),"steel")
        r.box("Narrow_Blue_Muzzle",(-67,2,0),(6,7,7),"steel")
        r.box("Muzzle_Dark_Bore",(-70.6,2,0),(1,3,3),"dark",detail="bore")
        r.paired("Muzzle_Swept_Tips",(-63,5,0),(12,3,2),"edge",3.3,(0,0,15))
        r.box("Stock_Carved_Neck",(19,0,0),(19,7,6),"wood",(0,0,-14),"wood")
        r.box("Stock_Bow_Upper",(29,1,0),(21,6,7),"wood",(0,0,-12),"wood")
        r.box("Stock_Bow_Lower",(31,-8,0),(18,5,6),"wood",(0,0,23),"wood")
        r.box("Stock_Bow_Heel",(42,-3,0),(5,18,8),"steel",(0,0,-9))
        for k,x in enumerate((24,29,34)):
            r.box("Red_Stock_Binding_"+str(k),(x,0,0),(3,8,8),"cloth",(0,0,-10),"cloth")
        r.box("Stock_Blue_Heel_Cap",(43,5,0),(7,4,9),"edge",(0,0,-9))
        r.box("Artifact_Receiver_Frame",(-1,1,-5),(14,10,2),"pale",detail="carved")
        r.box("Artifact_Carved_Head",(-1,4,-6.4),(8,7,2),"pale",detail="carved")
        r.box("Artifact_Green_Eye",(-1,4,-7.6),(5,5,1),"glow",(0,0,45),"crystal")
        r.box("Artifact_Gold_Brow",(-1,8,-6.8),(8,2,2),"trim")
        r.paired("Artifact_Pale_Flanges",(-1,-1,0),(10,3,1),"pale",5.8,(0,0,10))
        r.box("Green_Life_Chamber",(-3,-9,0),(10,8,6),"wood")
        r.paired("Life_Chamber_Leaf",(-3,-9,0),(6,5,1),"glow",3.2,(0,0,35),"crystal")
        r.box("Bolt_Red_Lever",(9,2,-8),(4,5,6),"cloth")
        r.scope(x=-1,y=15,length=27,size=7,trim="steel")
        r.box("Scope_Wood_Casing",(-1,15,0),(19,4,8),"wood",detail="wood")
        r.box("Scope_Artifact_Crest",(-1,20,0),(7,3,5),"pale",detail="carved")
        r.box("Scope_Crest_Green_Core",(-1,22,0),(3,3,3),"glow",(0,0,45),"crystal")
    return r


class Atlas:
    def __init__(self, theme):
        self.image = Image.new("RGBA", (512, 512), (0,0,0,0))
        self.theme = theme; self.cache = {}; self.x = self.y = 1; self.row = 0

    def face(self, material, w, h, detail, face):
        key = (material,w,h,detail,face)
        if key in self.cache: return self.cache[key]
        if self.x+w+1 > 512: self.x=1; self.y += self.row+2; self.row=0
        if self.y+h+1 > 512: raise ValueError("Atlas overflow")
        x,y = self.x,self.y; self.x += w+2; self.row=max(self.row,h)
        base = tuple(bytes.fromhex(self.theme["colors"][material][1:]))
        seed = int.from_bytes(hashlib.sha256((str(self.theme['seed'])+str(key)).encode()).digest()[:8],"little")
        rng=random.Random(seed)
        tile=Image.new("RGBA",(w,h)); pix=tile.load()
        shade={"top":1.13,"bottom":.75,"front":1.0,"back":.92,"left":.90,"right":1.04}[face]
        for py in range(h):
            for px in range(w):
                d=rng.choice([-5,-3,-1,0,0,2,3,5])
                if detail=="wood": d+=int(7*math.sin(py*.95 + math.sin(px*.13)*1.3))
                if detail=="cloth": d+=3 if (px+py)%3==0 else -2
                if detail in ("energy","lens"): d+=int(8*(1-py/max(1,h-1)))
                if detail=="hazard" and ((px+py)//3)%2==0:
                    c=(42,47,44)
                else: c=tuple(max(0,min(255,int(v*shade+d))) for v in base)
                pix[px,py]=(*c,255)
        draw=ImageDraw.Draw(tile)
        light=tuple(min(255,int(v*shade+22)) for v in base)+(255,)
        dark=tuple(max(0,int(v*shade-23)) for v in base)+(255,)
        if w>=3 and h>=3:
            draw.line((0,0,w-1,0), fill=light)
            draw.line((0,0,0,h-1), fill=light)
            draw.line((0,h-1,w-1,h-1), fill=dark)
            draw.line((w-1,1,w-1,h-1), fill=dark)
        if detail=="panel" and w>7 and h>4:
            draw.rectangle((2,2,w-3,h-3),outline=dark)
            for px in (2,w-3):
                for py in (1,h-2): draw.point((px,py),fill=light)
        if detail=="inlay" and w>4 and h>2:
            draw.line((2,h//2,w-3,h//2),fill=light)
        if detail=="lens":
            draw.rectangle((0,0,w-1,h-1),outline=dark)
            if w>3 and h>3:
                draw.line((1,1,w-2,1),fill=(206,248,251,255))
                draw.point((1,2),fill=(206,248,251,255))
        if detail=="maze" and w>=8 and h>=5:
            ink=(79,190,207,255)
            draw.line((1,1,w-2,1,w-2,h-2,2,h-2,2,3,w-5,3),fill=ink,width=1)
            if w>=15:
                for mx in range(7,w-5,7):draw.line((mx,1,mx,3,mx+3,3,mx+3,h-2),fill=dark,width=1)
        if detail=="eye" and w>=7 and h>=5:
            draw.polygon([(1,h//2),(3,1),(w-4,1),(w-2,h//2),(w-4,h-2),(3,h-2)],fill=light)
            draw.line((w//2,1,w//2,h-2),fill=(29,19,44,255),width=2)
        if detail=="skull" and w>=7 and h>=7:
            draw.rectangle((2,1,w-3,h-3),fill=light)
            draw.rectangle((2,3,3,4),fill=(35,37,45,255))
            draw.rectangle((w-4,3,w-3,4),fill=(35,37,45,255))
            draw.point((w//2,5),fill=dark)
            draw.line((3,h-2,w-4,h-2),fill=dark)
        if detail=="carved" and w>=4 and h>=3:
            draw.line((1,1,w-2,1,w-2,h-2,1,h-2),fill=dark)
            if w>=7:draw.line((w//2,1,w//2,h-2),fill=light)
        if detail=="crystal" and w>=3 and h>=3:
            draw.line((1,h-2,max(1,w//2),1,w-2,h-2),fill=light,width=1)
        if detail=="bore":
            draw.rectangle((0,0,w-1,h-1),fill=(11,17,21,255))
            if w>=3 and h>=3: draw.rectangle((0,0,w-1,h-1),outline=dark)
        self.image.paste(tile,(x,y)); self.cache[key]=(x,y)
        return x,y


def shape_none():
    return dict(type="none",offset=vec((0,0,0)),stretch=vec((1,1,1)),settings=dict(isPiece=True),textureLayout={},unwrapMode="custom",visible=True,doubleSided=False,shadingMode="flat")


def save_rifle(r):
    t=r.theme; ident=t['id']; atlas=Atlas(t)
    # Keep all variants inside the native prototype's visible Base-coordinate envelope.
    corners=[]
    for p in r.parts:
        rot=p['rotation']; angle=next((v for v in rot if v),0); axis=next((a for a,v in enumerate(rot) if v),2)
        c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
        for a in (-.5,.5):
            for b in (-.5,.5):
                for d in (-.5,.5):
                    xyz=[a*p['size'][0],b*p['size'][1],d*p['size'][2]]
                    j,k=((1,2),(2,0),(0,1))[axis]
                    xyz[j],xyz[k]=c*xyz[j]-s*xyz[k],s*xyz[j]+c*xyz[k]
                    corners.append([xyz[n]+p['center'][n] for n in range(3)])
    lo=[min(c[a] for c in corners) for a in range(3)]; hi=[max(c[a] for c in corners) for a in range(3)]
    scale=[min(49.5/abs(lo[0]),30.2/hi[0]),min(25/abs(lo[1]),14.2/hi[1]),4.7/max(abs(lo[2]),abs(hi[2]))]
    # Grip is a separately anchored piece, as in the native Rifle animation rig.
    grip=dict(name="Handle",center=[11.098076,-13.222432,0],size=[4,14,6],material="wood" if ident=="Tier01" else "cloth" if ident=="Tier09" else "rubber",rotation=[0,0,30],detail="wood" if ident=="Tier01" else "cloth" if ident=="Tier09" else "")
    parts=[grip]+r.parts
    legendary=ident in ('Tier05','Tier06')
    if legendary:
        for p in parts:
            luminous=p['material'] in ('glow','glass','railglow') or (ident=='Tier06' and p['name'] in ('Muzzle_Focusing_Crystal','Cell_Crystal_L','Cell_Crystal_R'))
            p['shading_mode']='fullbright' if luminous else 'flat'
    nodes=[]; bb=[]; render=[]
    for index,p in enumerate(parts):
        size=p['size']; layout={}; faces={}; render_uv={}
        for face,(a,b) in FACE_DIMS.items():
            w,h=size[a],size[b]
            u,v=atlas.face(p['material'],w,h,p['detail'],face)
            layout[face]=dict(offset=dict(x=u,y=v),mirror=dict(x=False,y=False),angle=0)
            faces[BB_FACE[face]]=dict(uv=[u,v,u+w,v+h],texture=0)
            render_uv[face]=[u,v,u+w,v+h]
        q=IDENTITY.copy()
        axes=[(axis,angle) for axis,angle in zip("xyz",p['rotation']) if angle]
        assert len(axes)<=1
        if axes:q=quaternion(*axes[0])
        center=p['center']
        # Scale the complete model on axis, including any rotated part; native nodes
        # cannot shear, so apply the fit before the small decorative rotations.
        fit=[1,1,1] if index==0 else scale
        center=[center[a]*fit[a] for a in range(3)]
        actual_size=[size[a]*fit[a] for a in range(3)]
        shape=dict(type="box",offset=vec((0,0,0)),stretch=vec(fit),settings=dict(isPiece=False,size=vec(size)),textureLayout=layout,unwrapMode="custom",visible=True,doubleSided=False,shadingMode=p.get('shading_mode','flat'))
        n=dict(id=str(index+4),name=p['name'],position=vec(center),orientation=q,shape=shape)
        if index==0:
            n.update(id="2",position=vec((0,0,0)),orientation=HANDLE_Q)
            n['shape']['offset']=vec((0,-1,0))
            n['shape']['stretch']=vec((1,1.1,.975))
            actual_size=[size[0],size[1]*1.1,size[2]*.975]
            handle=n
        else:
            n['position']=vec(center)
            nodes.append(n)
        cube=dict(name=p['name'],from_=[center[a]-actual_size[a]/2 for a in range(3)],to=[center[a]+actual_size[a]/2 for a in range(3)],autouv=0,color=index%8,origin=center,rotation=p['rotation'],faces=faces,type="cube",uuid=uid(ident+"/"+p['name']))
        cube['from']=cube.pop('from_'); bb.append(cube)
        if legendary:
            # Official Hytale Blockbench exporter reads CubeHytale.shading_mode.
            cube['shading_mode']=p['shading_mode']
            cube['double_sided']=False
            cube['shade']=p['shading_mode']!='fullbright'
        render.append(dict(p,center=center,size=actual_size,uv=render_uv))
    anchors=[]
    if legendary:
        positions={'Energy_Core':(-24,2,0),'Muzzle':(-88 if ident=='Tier05' else -91,2,0)}
        for offset,(name,position) in enumerate(positions.items()):
            location=[position[a]*scale[a] for a in range(3)]
            nodes.append(dict(id=str(len(parts)+4+offset),name=name,position=vec(location),orientation=IDENTITY,shape=shape_none(),children=[]))
            anchors.append(dict(name=name,position=location))
    base=dict(id="3",name="Base",position=vec((-3,16,0)),orientation=quaternion("z",-30),shape=shape_none(),children=nodes)
    handle['children']=[base]
    attach=dict(id="1",name="R-Attachment",position=vec((0,18,-20)),orientation=IDENTITY,shape=shape_none(),children=[handle])
    model=dict(nodes=[attach],format="character",lod="auto")
    folder=ROOT/'Common'/'Items'/'RangerSnipers'/ident
    folder.mkdir(parents=True,exist_ok=True)
    stem="Ranger_Sniper_"+ident
    model_path=folder/(stem+'.blockymodel'); texture_path=folder/(stem+'.png')
    model_path.write_text(json.dumps(model,indent=2)+'\n',encoding='utf-8')
    atlas.image.save(texture_path)
    encoded=base64.b64encode(texture_path.read_bytes()).decode()
    project=dict(meta=dict(format_version="4.10",model_format="free",box_uv=False),name=t['name'],model_identifier=stem,visible_box=[0,0,0],variable_placeholders="",resolution=dict(width=512,height=512),elements=bb,outliner=[dict(name=t['name'],origin=[0,0,0],uuid=uid(ident+"/group"),children=[x['uuid'] for x in bb])],textures=[dict(path=str(texture_path),name=texture_path.name,folder="",namespace="",id="0",particle=False,render_mode="default",render_sides="auto",frame_time=1,frame_order_type="loop",frame_order="",frame_interpolate=False,visible=True,internal=True,saved=True,uuid=uid(ident+"/texture"),source="data:image/png;base64,"+encoded,uv_width=512,uv_height=512,width=512,height=512)])
    if legendary:
        for anchor in anchors:
            project['outliner'][0]['children'].append(dict(name=anchor['name'],origin=anchor['position'],uuid=uid(ident+'/'+anchor['name']),children=[]))
    source_path=ROOT/'source'/(stem+'.bbmodel')
    source_path.write_text(json.dumps(project,indent=2)+'\n',encoding='utf-8')
    spec_path=ROOT/'source'/(stem+'.scene.json')
    spec=dict(theme=t,texture=str(texture_path),parts=render)
    if legendary:spec['anchors']=anchors
    spec_path.write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    result=dict(tier=int(ident[-2:]),name=t['name'],item_id=t.get('item_id','Weapon_Crossbow_'+t['name'].replace(' ','_')),zone=t['zone'],family=t['family'],model=str(model_path.relative_to(ROOT/'Common')).replace('\\','/'),texture=str(texture_path.relative_to(ROOT/'Common')).replace('\\','/'),icon=f"Icons/ItemsGenerated/{stem}.png",blockbench=str(source_path.relative_to(ROOT)).replace('\\','/'),scene=str(spec_path.relative_to(ROOT)).replace('\\','/'),cube_count=len(parts),texture_size=[512,512],body_fit_scale=scale)
    if legendary:
        result['energy_anchors']=anchors
        result['fullbright_parts']=[p['name'] for p in parts if p['shading_mode']=='fullbright']
    if t.get('variant'):result['acquisition_variant']=True
    return result


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/'Common'/'Icons'/'ItemsGenerated').mkdir(parents=True,exist_ok=True)
    catalog=[save_rifle(make_rifle(t)) for t in THEMES]
    (ROOT/'artcatalog.json').write_text(json.dumps(dict(version=1,original_art=True,authoring_units="1 model unit = 1 texture pixel",animation_parent="Rifle",attachment_root="R-Attachment",handle_node="Handle",muzzle_axis="Base local -X",assets=catalog),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(generated=len(catalog),cube_counts=[c['cube_count'] for c in catalog],catalog=str(ROOT/'artcatalog.json'))))


if __name__ == '__main__': main()
