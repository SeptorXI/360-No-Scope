"""Generate native Hytale sniper interactions and root-item merge templates."""

from pathlib import Path
import json
import math
from legendary_abilities import generate_ability
from audio_orchestration import reload_branch, sound_effects


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "generated"
SPEC = ROOT.parent / "research" / "progression-spec.json"

# Only visual presentation is local. Damage, ammunition, ballistics, scope,
# movement and cadence come from the canonical progression source.
VISUAL_PROFILES = {
    "Wildwood_Surveyor": ("ballistic", None),
    "Dunewatch_Longshot": ("ballistic", None),
    "Frostline_Sentinel": ("ballistic", None),
    "Mournhollow_Epitaph": ("charged", "purple"),
    "Deepworks_Railspike": ("beam", "cyan"),
    "Luminia_Dawnpiercer": ("beam", "luminia"),
    "Nameless_Covenant": ("charged", "fear"),
    "Labyrinth_Threadkeeper": ("charged", "cyan"),
    "Skybound_Farwatch": ("ballistic", None),
}

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
    """Resolve fixed, mandatory receiver/ammo pairs before writing assets."""
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8-sig"))
    tiers = spec["tiers"]
    ammo = {entry["id"]: entry for entry in spec["ammo"]}
    expected = {f"Weapon_Crossbow_{slug}" for slug in VISUAL_PROFILES}
    assert {tier["id"] for tier in tiers} == expected, "Unexpected receiver roster"
    assert len(tiers) == len(expected) == len(ammo) == len(spec["ammo"]), "Expected nine unique ammo profiles"
    assert len({tier["ammo"] for tier in tiers}) == len(tiers), "Ammo must be unique per rifle"
    for tier in tiers:
        profile = ammo[tier["ammo"]]
        assert profile["compatibleWeapon"] == tier["id"], "Ammo receiver mismatch"
        stats = profile["stats"]
        for key in ("damage", "headDamage", "speed", "gravity", "range"):
            value = stats[key]
            assert isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), f"Invalid ammo {key}"
        assert stats["damage"] > 0 and stats["headDamage"] > 0
        assert stats["speed"] > 0 and stats["range"] > 0 and stats["gravity"] >= 0
        assert tier["receiverDamage"] >= 0 and tier["receiverHeadDamage"] >= 0
        assert tier["receiverDamage"] + stats["damage"] == tier["damage"], "Body total differs from receiver + ammo"
        assert tier["receiverHeadDamage"] + stats["headDamage"] == tier["headDamage"], "Head total differs from receiver + ammo"
        assert tier["range"] == stats["range"], "Tier range differs from ammo physics"
        assert tier["scope"] > 0 and tier["cycleSeconds"] > 0.12
        assert 0 < tier["adsMoveMultiplier"] <= 1
        reload = tier["reload"]
        assert reload["capacity"] == (2 if "ability" in tier else 1)
        assert 0 < reload["durationSeconds"] <= tier["cycleSeconds"]
        assert reload["interactionType"] == "Ability4", "Current native reload uses Ability4"
        for action in ("Fire", "Empty", "ReloadOpen", "ReloadInsert", "ReloadClose", "Ready"):
            sound_effects(tier["audio"], action)
        falloff = tier["falloff"]
        assert falloff["metric"] == "traveledPath"
        points = falloff["points"]
        assert len(points) >= 2 and points[0] == {"distance": 0, "multiplier": 1}
        assert all(math.isfinite(p["distance"]) and math.isfinite(p["multiplier"])
                   and p["distance"] >= 0 and 0 < p["multiplier"] <= 1 for p in points)
        assert all(a["distance"] < b["distance"] and a["multiplier"] >= b["multiplier"]
                   for a, b in zip(points, points[1:]))
    assert all(tier["falloff"] == tiers[0]["falloff"] for tier in tiers), "Shared falloff must preserve role balance"
    return tiers, ammo


def idle_glow(slug):
    """Small held-item effects, using native item and particle schemas.

    Fullbright is authored only on the art's energy shapes. This adds local
    illumination and four/five particles a second at the agreed Energy_Core
    model anchor, not a whole-model shader or any combat interaction.
    """
    if slug not in {"Deepworks_Railspike", "Luminia_Dawnpiercer"}:
        return {}
    prefix = f"RS_{slug}_Idle"
    is_goblin = slug == "Deepworks_Railspike"
    emitters = [
        ("AmberSparks", "Particles/Textures/Basic/Spark.png", 3, 6,
         (0.20, 0.40), (0.018, 0.028), "#ffe7ae", "#ff9c32"),
        ("CoilArc", "Particles/Textures/Rnd/LightningArch.png", 1, 2,
         (0.12, 0.22), (0.12, 0.18), "#fff1bd", "#ffbc52"),
    ] if is_goblin else [
        ("GoldCyanMotes", "Particles/Textures/Basic/Ball2.png", 3, 6,
         (0.40, 0.75), (0.018, 0.030), "#fff4d3", "#80faff"),
        ("VioletMotes", "Particles/Textures/Basic/Ball3.png", 2, 4,
         (0.45, 0.80), (0.025, 0.040), "#e4c4ff", "#a66cff"),
    ]
    system_spawners = []
    for suffix, texture, rate, maximum, life, scale, bright, fade in emitters:
        name = f"{prefix}_{suffix}"
        is_arc = suffix == "CoilArc"
        particle = {
            "Texture": texture,
            "ScaleRatioConstraint": "None" if is_arc else "OneToOne",
            "SoftParticles": "Disable",
            "UVOption": "FlipV" if is_arc else "RandomFlipUV",
            "Animation": {
                "0": {"Opacity": 0.85 if is_arc else 1, "Color": bright},
                "35": {"Opacity": 0.15 if is_arc else 0.9, "Color": fade},
                "55": {"Opacity": 0.7, "Color": bright},
                "100": {"Opacity": 0, "Color": fade},
            },
            "InitialAnimationFrame": {
                "Scale": {"X": {"Min": scale[0], "Max": scale[1]}},
                "Opacity": 1,
            },
            # Unlike environmental motes, the held weapon sits near the camera.
            "CameraNearFadeStartDistance": 0.03,
            "CameraNearFadeEndDistance": 0.08,
        }
        if is_arc:
            particle["FrameSize"] = {"Width": 128, "Height": 128}
            particle["InitialAnimationFrame"].update({
                "FrameIndex": {"Min": 0, "Max": 2},
                "Rotation": {"X": {"Min": 80, "Max": 100},
                             "Z": {"Min": -30, "Max": 30}},
            })
            particle["InitialAnimationFrame"]["Scale"]["Y"] = {"Min": 0.04, "Max": 0.07}
        spawner = {
            "RenderMode": "Erosion" if is_arc else "BlendAdd",
            "ParticleRotationInfluence": "Billboard",
            "MaxConcurrentParticles": maximum,
            "ParticleLifeSpan": {"Min": life[0], "Max": life[1]},
            "SpawnRate": {"Min": rate, "Max": rate},
            "Particle": particle,
            "Shape": "Cube",
            "EmitOffset": {axis: {"Min": -0.025, "Max": 0.025} for axis in "XYZ"},
            "InitialVelocity": {
                "Speed": {"Min": 0.02 if is_arc else 0.06, "Max": 0.04 if is_arc else 0.12},
                "Yaw": {"Min": 0, "Max": 360},
                "Pitch": {"Min": -90, "Max": 90},
            },
            "TrailSpawnerPositionMultiplier": 1,
            "TrailSpawnerRotationMultiplier": 1,
            "ParticleRotateWithSpawner": True,
            "LightInfluence": 0,
        }
        write_json(f"Server/Particles/RangerSnipers/Idle/Spawners/{name}.particlespawner", spawner)
        system_spawners.append({"SpawnerId": name})
    write_json(f"Server/Particles/RangerSnipers/Idle/{prefix}.particlesystem", {
        "Spawners": system_spawners, "CullDistance": 32,
    })
    particles = [{"SystemId": prefix, "TargetEntityPart": "PrimaryItem",
                  "TargetNodeName": "Energy_Core", "Scale": 1}]
    return {
        "Particles": particles,
        "FirstPersonParticles": particles,
        "Light": {"Color": "#fc8" if is_goblin else "#def", "Radius": 1},
    }


def generate(spec_path=SPEC):
    tiers, ammo_profiles = load_profiles(spec_path)
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
            "RequireNewClick": True,
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
                    "HideFirstPersonHeldItem": True,
                    "Zoom": {
                        "MagnificationMultiplier": zoom,
                        "MouseSensitivityMultiplier": round(1.5 / zoom, 3),
                        "OverlayTexture": "ScreenEffects/Sniper.png",
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
        single_animation = "ReloadSingle" if reload_profile["capacity"] == 2 else reload_profile["animationId"]
        single_branch, single_audio = reload_branch(write_json, tier, "single", single_animation, reload_rules)
        audio_reloads.append(single_audio)
        reload_next = single_branch
        if reload_profile["capacity"] == 2:
            full_branch, full_audio = reload_branch(write_json, tier, "double", reload_profile["animationId"], reload_rules)
            audio_reloads.append(full_audio)
            reload_next = {
                "Type": "RSChamber", "Operation": "DoubleReloadCondition", "WeaponId": item_id,
                "Next": full_branch, "Failed": single_branch,
            }
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
            "Type": "Projectile",
            "Config": projectile,
            "Lifetime": round(reach / speed, 4),
            "RunTime": 0.12,
            "Effects": {
                "ItemAnimationId": "Shoot",
                "CameraEffect": recoil,
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
            "DamageCalculator": damage_calculator(body),
            "DamageEffects": {
                "WorldParticles": [{"SystemId": "Impact_Sword_Basic", "Scale": 0.6}],
            },
            "TargetedDamage": {
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
            "LaunchLocalSoundEventId": audio_profile["events"]["Fire"]["Local"],
            "LaunchWorldSoundEventId": audio_profile["events"]["Fire"]["World"],
            "Interactions": {
                "ProjectileSpawn": flight_marker,
                "ProjectileHit": {"Interactions": [falloff_id]},
                "ProjectileMiss": {"Interactions": ["RS_Despawn"]},
            },
        })

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
        template.update(idle_glow(slug))
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
            "body_damage": body,
            "head_damage": head,
            "receiver_body_damage": tier["receiverDamage"],
            "receiver_head_damage": tier["receiverHeadDamage"],
            "ammo_body_damage": stats["damage"],
            "ammo_head_damage": stats["headDamage"],
            "damage_composition": "receiver_plus_ammo_single_event",
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
            "base_body_dps": round(body / cycle, 2),
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
            "reload_single_animation_id": "ReloadSingle" if reload_profile["capacity"] == 2 else reload_profile["animationId"],
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
                            "condition": "committed_native_projectile_launch",
                            "event_ids": audio_profile["events"]["Fire"],
                            "runtime_path": f"Server/ProjectileConfigs/RangerSnipers/{projectile}.json",
                            "empty_event_ids": audio_profile["events"]["Empty"],
                            "empty_interaction_id": empty_id})

    write_json("mechanics-catalog.json", {
        "tiers": catalog,
        "legendary_abilities": abilities,
        "audio_timeline_catalog": "audio-timeline-catalog.json",
        "shared_cooldown_id": "RangerSniperCycle",
        "limitations": [
            "Beam shots use native projectiles with travel time.",
            "Scope and hip fire use the same precise trajectory.",
            "Base projectile damage follows the shared server-tracked 3D traveled-path falloff curve; lifetime remains an independent travel-time cap.",
            "Native class/enchantment flat damage, percentage-health procs and other downstream effects retain their own behavior.",
            "Ability4 (native reload/default R) manually reloads this item; clients can remap that action.",
            "Actual ammo transfers only when a reload animation completes; chamber state persists in this ItemStack metadata.",
            "Each rifle requires its own fixed ammo profile; receiver + ammo damage and ammo physics compile into one owned native projectile event.",
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
