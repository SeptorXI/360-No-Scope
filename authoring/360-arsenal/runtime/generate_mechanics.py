"""Generate native Hytale sniper interactions and root-item merge templates."""

from pathlib import Path
from copy import deepcopy
import json
import math
import shutil
from legendary_abilities import generate_ability
from audio_orchestration import reload_branch, sound_effects


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "generated" / "mechanics"
SPEC = ROOT.parent / "content" / "arsenal-spec.json"

# Only visual presentation is local. Damage, ammunition, ballistics, scope,
# movement and cadence come from the canonical progression source.
VISUAL_PROFILES = {}

INPUT_BLOCKERS = [
    "Primary", "Ability1", "Ability2", "Ability3", "Ability4", "Use", "Pick",
    "SwapFrom", "SwapTo",
]


def write_json(relative_path, value):
    path = OUTPUT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def damage_calculator(amount):
    return {
        "Type": "Absolute",
        "BaseDamage": {"Projectile": amount},
        "RandomPercentageModifier": 0,
    }


def load_profiles(spec_path):
    spec=json.loads(Path(spec_path).read_text(encoding="utf-8-sig"))
    tiers=spec["tiers"]
    ammo={a["id"]:a for a in spec["ammo"]}
    assert len(tiers)==45 and len(ammo)==45
    for tier in tiers:
        slug=tier["id"].removeprefix("Weapon_Crossbow_")
        idx=tier["artIndex"]
        VISUAL_PROFILES[slug]=("beam" if idx in (5,6) else "charged" if idx in (4,7,8) else "ballistic",
           "luminia" if idx==6 else "cyan" if idx in (5,8) else "fear" if idx==7 else "purple" if idx==4 else None)
        a=ammo[tier["ammo"]]
        assert a["compatibleWeapon"]==tier["id"]
        assert abs(tier["receiverDamage"]+a["stats"]["damage"]-tier["damage"])<.00001
        assert abs(tier["receiverHeadDamage"]+a["stats"]["headDamage"]-tier["headDamage"])<.00001
        assert 1<=tier["reload"]["capacity"]<=40 and tier["cycleSeconds"]>.12
        assert tier["falloff"]["metric"]=="traveledPath"
    return tiers,ammo


def idle_glow(slug):
    # Reuse the immutable original source-theme particle assets. New gun models
    # provide Energy_Core; no baseline asset is regenerated or overwritten.
    if slug not in {"Deepworks_Railspike", "Luminia_Dawnpiercer"}: return {}
    particles=[{"SystemId":f"RS_{slug}_Idle","TargetEntityPart":"PrimaryItem",
                "TargetNodeName":"Energy_Core","Scale":1}]
    return {"Particles":particles,"FirstPersonParticles":particles,
            "Light":{"Color":"#fc8" if slug=="Deepworks_Railspike" else "#def","Radius":1}}


def generate(spec_path=SPEC):
    tiers, ammo_profiles = load_profiles(spec_path)
    # Only this reproducible output tree is owned. Retiring an unreleased slug
    # must not leave stale native roots/configs/items in the next combined JAR.
    expected = (ROOT.parent / "generated" / "mechanics").resolve()
    target = OUTPUT.resolve()
    if target != expected or not target.is_relative_to(ROOT.parent.resolve()):
        raise RuntimeError("Refusing to clean an unexpected mechanics output directory")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    catalog = []
    abilities = []
    audio_reloads, audio_shots = [], []
    (OUTPUT / "Server/Item/Interactions/RangerSnipers/RS_Empty.json").unlink(missing_ok=True)
    (OUTPUT / "Server/Item/Interactions/RangerSnipers/RS_Ability_Abort.json").unlink(missing_ok=True)
    write_json("Server/Item/Interactions/RangerSnipers/RS_Despawn.json", {
        "Type": "RemoveEntity", "Entity": "User",
    })

    for tier in tiers:
        item_id = tier["id"]
        slug = item_id.removeprefix("Weapon_Crossbow_")
        mode, palette = VISUAL_PROFILES[slug]
        ammo = tier["ammo"]
        ammo_profile = ammo_profiles[ammo]
        stats = ammo_profile["stats"]
        # Compile the paired contributions into ONE native damage event. The
        # consumed ammo ID is fixed; no second ammo proc/damage event is added.
        body = tier["receiverDamage"] + stats["damage"]
        head = tier["receiverHeadDamage"] + stats["headDamage"]
        cycle, zoom = tier["cycleSeconds"], tier["scope"]
        speed, gravity, reach = stats["speed"], stats["gravity"], stats["range"]
        prefix = f"RS_{slug}"
        primary = f"Root_{prefix}_Primary"
        ads = f"Root_{prefix}_ADS"
        impact = f"{prefix}_Impact"
        launch = f"{prefix}_Launch"
        projectile = f"{prefix}_Projectile"
        model = f"{prefix}_ProjectileModel"
        recoil = f"{prefix}_Recoil"
        empty_id = f"{prefix}_Empty"
        reload_root = f"Root_{prefix}_Reload"
        sync_root = f"Root_{prefix}_ChamberHUD"
        flight_marker = f"Root_{prefix}_FlightOrigin"
        falloff_id = f"{prefix}_Falloff"
        reload_profile = tier["reload"]
        is_energy = mode == "beam"
        is_charged = mode in {"charged", "beam"}
        audio_profile = tier["audio"]
        write_json(f"Server/Item/Interactions/RangerSnipers/{empty_id}.json", {
            "Type": "Simple", "RunTime": 0.2, "Effects": sound_effects(audio_profile, "Empty"),
        })

        # A single shared cooldown namespace applies to every tier. Both a fresh
        # click and an expired native cooldown are required for every shot.
        write_json(f"Server/Item/RootInteractions/RangerSnipers/{primary}.json", {
            "RequireNewClick": not tier["automatic"],
            "Cooldown": {"Id": "RangerSniperCycle", "Cooldown": cycle, "SkipCooldownReset": True},
            "Rules": {"BlockedBy": INPUT_BLOCKERS},
            "Tags": {"Attack": ["Ranged"]},
            "Interactions": [{
                "Type": "CooldownCondition", "Id": "RangerSniperCycle",
                "Next": {
                    "Type": "DurabilityCondition", "Threshold": 0, "Operator": "GreaterThan",
                    "Next": {
                        "Type": "RSChamber", "Operation": "Consume", "WeaponId": item_id, "Cost": 1,
                        "Next": {"Type": "TriggerCooldown", "Cooldown": {"Id": "RangerSniperCycle", "Cooldown": cycle},
                                 "Next": launch},
                        "Failed": empty_id,
                    },
                },
            }],
        })

        write_json(f"Server/Item/RootInteractions/RangerSnipers/{ads}.json", {
            "Rules": {"BlockedBy": [
                "Secondary", "Ability1", "Ability2", "Ability3", "Ability4",
                "Use", "Pick", "SwapFrom", "SwapTo",
            ], "InterruptedBy": ["Ability4", "SwapFrom", "SwapTo"]},
            "Interactions": [{
                "Type": "Wielding",
                "HorizontalSpeedMultiplier": tier["adsMoveMultiplier"],
                "CancelOnOtherClick": False,
                "Effects": {
                    "MovementEffects": {"DisableSprint": True},
                    "HideFirstPersonHeldItem": tier["family"] == "semiauto",
                    "Zoom": {
                        "MagnificationMultiplier": zoom,
                        "MouseSensitivityMultiplier": min(1, round(1.5 / zoom, 3)),
                        **({"OverlayTexture": "ScreenEffects/Sniper.png"} if tier["family"] == "semiauto" else {}),
                        "DepthOfField": False,
                        "ForcePerspective": "FirstPerson",
                        "InLerp": 0.18,
                        "OutLerp": 0.25,
                        "OverlayFade": True,
                        "OverlayFadePerSecond": 8,
                    },
                },
            }],
        })

        # Ability4 is the current native reload action (0.7.5 crossbow template).
        # The client shows its actual binding through this native HUD label.
        # R leaves ADS, blocks firing/Q/re-entering ADS, and swap/death cancel it.
        reload_rules = {
            "BlockedBy": ["Primary", "Ability1", "Ability2", "Ability3", "Use", "Pick"],
            "Blocking": ["Primary", "Secondary", "Ability1", "Ability2", "Ability3", "Ability4", "Use", "Pick"],
            "Interrupting": ["Secondary"],
            "InterruptedBy": ["SwapFrom", "SwapTo", "Death"],
        }
        single_animation = reload_profile["animationId"]
        single_branch, single_audio = reload_branch(write_json, tier, "single", single_animation, reload_rules)
        audio_reloads.append(single_audio)
        reload_next = single_branch
        if reload_profile["style"] == "shell-tube":
            reload_next = empty_id
            for count in range(reload_profile["capacity"], 0, -1):
                counted = deepcopy(tier)
                variant = f"count{count}"
                counted["audio"]["reloadTimelines"][variant] = ([{"phase": .18, "event": "ReloadOpen"}]
                    + [{"phase": round(.25 + .45 * (index + 1) / count, 6), "event": "ReloadInsert"}
                       for index in range(count)]
                    + [{"phase": .89, "event": "ReloadClose"}])
                branch, timeline = reload_branch(write_json, counted, variant, f"Reload{count}", reload_rules)
                timeline["planned_transfer"] = count
                audio_reloads.append(timeline)
                reload_next = {"Type": "RSChamber", "Operation": "ReloadCountCondition", "WeaponId": item_id,
                    "Cost": count, "Next": branch, "Failed": reload_next}
        write_json(f"Server/Item/RootInteractions/RangerSnipers/{reload_root}.json", {
            "RequireNewClick": True,
            "HudInputBindingEntry": "server.hud.inputBinding.reload",
            "Rules": reload_rules,
            "Interactions": [{
                "Type": "RSChamber", "Operation": "BeginReload", "WeaponId": item_id,
                "Failed": empty_id,
                "Next": reload_next,
            }],
        })
        write_json(f"Server/Item/RootInteractions/RangerSnipers/{sync_root}.json", {
            "RequireNewClick": False,
            "Interactions": [{"Type": "Simple", "RunTime": 0.1,
                              "Next": {"Type": "RSChamber", "Operation": "Sync", "WeaponId": item_id}}],
        })

        # Lifetime is a native Projectile interaction field, measured in seconds.
        # It caps travel time. Gravity makes ballistic path length differ slightly
        # from the catalog's nominal horizontal range.
        write_json(f"Server/Item/Interactions/RangerSnipers/{launch}.json", {
            "Type": "ASScatter",
            "Config": projectile,
            "Pellets": tier["pellets"], "SpreadDegrees": tier["spreadDegrees"],
            "BodyDamage": body, "HeadDamage": head, "Range": reach,
            "Lifetime": round(reach / speed, 4),
            "RunTime": 0.12,
            "Effects": {
                "ItemAnimationId": "Shoot",
                "CameraEffect": recoil, **sound_effects(audio_profile, "Fire"),
            },
        })
        # Remove the previously generated automatic chamber animation asset.
        (OUTPUT / f"Server/Item/Interactions/RangerSnipers/{prefix}_Cycle.json").unlink(missing_ok=True)
        # The marker identifies our completed projectile holder before physics;
        # capture does not depend on this no-op root being executed later.
        write_json(f"Server/Item/RootInteractions/RangerSnipers/{flight_marker}.json", {
            "Interactions": [{"Type": "Simple", "RunTime": 0}],
        })
        write_json(f"Server/Item/Interactions/RangerSnipers/{falloff_id}.json", {
            "Type": "RSFalloff", "WeaponId": item_id,
            "Next": impact, "Failed": "RS_Despawn",
        })
        write_json(f"Server/Item/Interactions/RangerSnipers/{impact}.json", {
            "Parent": "DamageEntityParent",
            "DamageAttribute": "RS_DistanceDamage",
            "DamageCalculator": damage_calculator(1 if tier["pellets"]>1 else body),
            "DamageEffects": {
                "WorldParticles": [{"SystemId": "Impact_Sword_Basic", "Scale": 0.6}],
            },
            "TargetedDamage": {} if tier["pellets"]>1 else {
                "Head": {
                    "DamageCalculator": damage_calculator(head),
                    "DamageEffects": {
                        "WorldParticles": [{"SystemId": "Impact_Critical", "Scale": 0.8}],
                    },
                },
            },
            "Next": "RS_Despawn", "Failed": "RS_Despawn", "Blocked": "RS_Despawn",
        })
        write_json(f"Server/ProjectileConfigs/RangerSnipers/{projectile}.json", {
            "Model": model,
            "UseModelScale": True,
            "LaunchForce": speed,
            "SpawnOffset": {"X": 0, "Y": 0, "Z": 0},
            "SpawnRotationOffset": {"Pitch": 0, "Yaw": 0, "Roll": 0},
            "Physics": {
                "Type": "Standard",
                "Gravity": gravity,
                "TerminalVelocityAir": speed,
                "TerminalVelocityWater": 30,
                "RotationMode": "VelocityDamped",
                "Bounciness": 0,
                "SticksVertically": False,
            },
            "Interactions": {
                "ProjectileSpawn": flight_marker,
                "ProjectileHit": {"Interactions": [falloff_id]},
                "ProjectileMiss": {"Interactions": ["RS_Despawn"]},
            },
        })

        if tier["pellets"]>1:
            write_json(f"Server/Item/Interactions/RangerSnipers/{falloff_id}.json", {
                "Type":"ASScatterHit","Operation":"Record","WeaponId":item_id,
                "Next":{"Type":"Simple","RunTime":0.1,"Next":{
                    "Type":"ASScatterHit","Operation":"Commit","WeaponId":item_id,
                    "Next":impact,"Failed":"RS_Despawn"}},"Failed":"RS_Despawn"})
        model_data = {
            "Parent": "Bullet_Blunderbuss",
            "MinScale": 0.7,
            "MaxScale": 0.7,
            "HitBox": {
                "Min": {"X": -0.025, "Y": -0.025, "Z": -0.025},
                "Max": {"X": 0.025, "Y": 0.025, "Z": 0.025},
            },
        }
        if is_charged:
            trail = f"{prefix}_Trail"
            cross_trail = f"{prefix}_TrailViolet" if palette == "luminia" else trail
            model_data["Trails"] = [
                {"TargetNodeName": "Origin_Projectile", "TrailId": trail},
                {"TargetNodeName": "Origin_Projectile", "TrailId": cross_trail,
                 "RotationOffset": {"Yaw": 90}},
            ]
            colors = {
                "purple": ("#b98affff", "#7d31d300"),
                "cyan": ("#80f8ffff", "#4c9fff00"),
                "luminia": ("#fff2c8ff", "#81faff00"),
                "fear": ("#c292ffff", "#a3216800"),
            }
            color, fade = colors[palette]
            write_json(f"Server/Entity/Trails/RangerSnipers/{trail}.json", {
                "Parent": "Ability_ChargedShot_Ribbon",
                # Native Trail LifeSpan uses the integer codec, not fractional seconds.
                # Match the vanilla charged-shot ribbon instead of a fractional
                # Projectile lifetime (which is a different field).
                "LifeSpan": 4,
                "Start": {"Width": 0.035, "Color": color},
                "End": {"Width": 0.015, "Color": fade},
            })
            if palette == "luminia":
                write_json(f"Server/Entity/Trails/RangerSnipers/{cross_trail}.json", {
                    "Parent": "Ability_ChargedShot_Ribbon",
                    "LifeSpan": 4,
                    "Start": {"Width": 0.035, "Color": "#81faffff"},
                    "End": {"Width": 0.015, "Color": "#b77eff00"},
                })
        write_json(f"Server/Models/Projectiles/RangerSnipers/{model}.json", model_data)

        write_json(f"Server/Camera/CameraEffect/RangerSnipers/{recoil}.json", {
            "Type": "CameraShake", "CameraShake": recoil,
            "Intensity": {"Value": 1},
        })
        write_json(f"Server/Camera/CameraShake/RangerSnipers/{recoil}.json", {
            "FirstPerson": {
                "Duration": 0,
                "EaseIn": {"Time": 0.01, "Type": "Linear"},
                "EaseOut": {"Time": 0.22, "Type": "Linear"},
                "Offset": {"X": [], "Y": [], "Z": []},
                "Rotation": {
                    "Pitch": [{"Frequency": 8, "Amplitude": 0.8 if is_energy else 1.2,
                               "Type": "Sin"}],
                    "Yaw": [], "Roll": [],
                },
            },
            "ThirdPerson": {
                "Duration": 0,
                "EaseIn": {"Time": 0.01, "Type": "Linear"},
                "EaseOut": {"Time": 0.22, "Type": "Linear"},
                "Offset": {"X": [], "Y": [], "Z": []},
                "Rotation": {
                    "Pitch": [{"Frequency": 8, "Amplitude": 0.4 if is_energy else 0.6,
                               "Type": "Sin"}],
                    "Yaw": [], "Roll": [],
                },
            },
        })

        # Merge this into the authored item. No parent means no inherited crossbow
        # signature or rapid-fire rifle input can enter through another button.
        template = {
            "Categories": ["Items.Weapons"],
            "MaxStack": 1,
            "Weapon": {
                "EntityStatsToClear": ["Ammo"],
                "StatModifiers": {"Ammo": [{"Amount": reload_profile["capacity"], "CalculationType": "Additive"}]},
            },
            "DisplayEntityStatsHUD": ["Ammo"],
            "Tags": {
                "Type": ["Weapon"],
                "Family": ["Crossbow"],
                "MMO_Weapon_Type": ["ARCHERY"],
            },
            "PlayerAnimationsId": reload_profile["playerAnimationsId"],
            "Interactions": {"Primary": primary, "Secondary": ads,
                             reload_profile["interactionType"]: reload_root, "SwapTo": sync_root},
            "Reticle": "DefaultMelee",
        }
        source_slug = [None,"Wildwood_Surveyor","Dunewatch_Longshot","Frostline_Sentinel","Mournhollow_Epitaph","Deepworks_Railspike","Luminia_Dawnpiercer","Nameless_Covenant","Labyrinth_Threadkeeper","Skybound_Farwatch"][tier["artIndex"]]
        if tier["quality"]=="Legendary": template.update(idle_glow(source_slug))
        ability = generate_ability(write_json, slug, model, recoil, damage_calculator,
                                   ammo_profile, tier.get("ability"), audio_profile, empty_id,
                                   flight_marker, tier["falloff"])
        if ability:
            template["Interactions"]["Ability1"] = ability["root_id"]
            abilities.append(ability)
        write_json(f"item-templates/{item_id}.json", template)
        catalog.append({
            "item_id": item_id,
            "template": f"item-templates/{item_id}.json",
            "family": tier["family"], "automatic": tier["automatic"],
            "pellets": tier["pellets"], "spread_degrees": tier["spreadDegrees"],
            "body_damage": body,
            "head_damage": head,
            "receiver_body_damage": tier["receiverDamage"],
            "receiver_head_damage": tier["receiverHeadDamage"],
            "ammo_body_damage": stats["damage"],
            "ammo_head_damage": stats["headDamage"],
            "damage_composition": "sum_of_real_pellet_receiver_plus_ammo_contacts_once_per_target" if tier["pellets"] > 1 else "receiver_plus_ammo_single_event",
            "compatible_ammo_ids": [ammo],
            "ammo_stats": stats,
            "primary_root_id": primary,
            "launch_id": launch,
            "impact_id": impact,
            "projectile_id": projectile,
            "flight_marker_root_id": flight_marker,
            "falloff_interaction_id": falloff_id,
            "damage_attribute": "RS_DistanceDamage",
            "falloff": tier["falloff"],
            "falloff_applied_to": "selected_native_body_or_head_base_damage_once",
            "cycle_seconds": cycle,
            "body_damage_per_discharge": body * tier["pellets"],
            "head_damage_per_discharge": head * tier["pellets"],
            "base_body_dps": round(body * tier["pellets"] / cycle, 2),
            "native_damage_events_per_target_per_discharge": 1,
            "scatter_aggregation_seconds": .1 if tier["pellets"] > 1 else 0,
            "launch_wait": "Client",
            "speed_blocks_per_second": speed,
            "gravity": gravity,
            "nominal_range_blocks": reach,
            "scope_magnification": zoom,
            "ads_speed_multiplier": tier["adsMoveMultiplier"],
            "ammo_id": ammo,
            "ammo_per_shot": 1,
            "reload_root_id": reload_root,
            "reload_interaction_type": reload_profile["interactionType"],
            "chamber_capacity": reload_profile["capacity"],
            "reload_duration_seconds": reload_profile["durationSeconds"],
            "reload_animation_id": reload_profile["animationId"],
            "reload_single_animation_id": reload_profile["animationId"],
            "reload_count_locked_before_animation": True,
            "player_animations_id": reload_profile["playerAnimationsId"],
            "ammo_paid_at": "manual_reload_commit",
            "cooldown_triggered_after_chamber_consume": True,
            "empty_fire_starts_cooldown": False,
            "loaded_state_authority": "ItemStack.RS_Chamber",
            "hud_mirror_stat": "Ammo",
            "hud_sync_root_id": sync_root,
            "empty_interaction_id": empty_id,
            "primary_fire_audio_ids": audio_profile["events"]["Fire"],
            "mode": mode,
            "shot_type": "fast beam projectile" if is_energy else "ballistic projectile",
        })
        audio_shots.append({"item_id": item_id, "action": "Fire", "delay_seconds": 0,
                            "condition": "committed_native_cone_launch_once_per_discharge",
                            "event_ids": audio_profile["events"]["Fire"],
                            "runtime_path": f"Server/Item/Interactions/RangerSnipers/{launch}.json#/Effects",
                            "empty_event_ids": audio_profile["events"]["Empty"],
                            "empty_interaction_id": empty_id})

    write_json("mechanics-catalog.json", {
        "tiers": catalog,
        "legendary_abilities": abilities,
        "audio_timeline_catalog": "audio-timeline-catalog.json",
        "shared_cooldown_id": "RangerSniperCycle",
        "limitations": [
            "Beam shots use native projectiles with travel time.",
            "Server-authoritative spread cone applies while aimed or hip firing; scope does not remove spread.",
            "Base projectile damage follows the shared server-tracked 3D traveled-path falloff curve; lifetime remains an independent travel-time cap.",
            "Native class/enchantment flat damage, percentage-health procs and other downstream effects retain their own behavior.",
            "Ability4 (native reload/default R) manually reloads this item; clients can remap that action.",
            "Actual ammo transfers only when a reload animation completes; chamber state persists in this ItemStack metadata.",
            "Each gun selects one exclusive ammo profile. Shotguns aggregate their physical pellet contacts for100ms into one native damage event per target per shell, avoiding multiplied native on-hit procs. Later contacts to an already committed target are discarded.",
            "Legendary Q uses its explicit ability damage override and the same compatible ammo physics; ammo damage is not added again.",
            "Reload audio uses short frame-aligned native cues in a cancelable child chain; an already-played one-shot can retain its natural short tail.",
            "Shared cooldown verified against the native CooldownHandler API; live input and animations still need a client check.",
        ],
    })
    write_json("audio-timeline-catalog.json", {
        "fps": 60, "reloads": audio_reloads, "shots": audio_shots,
        "legendary_abilities": [{key: value for key, value in ability.items() if key in {
            "item_id", "name", "charge_seconds", "charge_id", "launch_id", "projectile_id",
            "charge_audio_ids", "special_fire_audio_ids", "abort_audio_ids", "abort_id"}}
            for ability in abilities],
        "native_ownership": "first Parallel root executes on original context; only cue root forks",
        "future_cues_canceled_with_parent": True,
        "audio_branch_commits_ammo": False,
        "sample_accurate_client_timing_verified": False,
    })


if __name__ == "__main__":
    generate()
    print(f"Generated {len(VISUAL_PROFILES)} weapon mechanics under {OUTPUT}")
