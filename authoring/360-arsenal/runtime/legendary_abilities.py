"""Native legendary weapon abilities; called by the main asset generator."""
from audio_orchestration import sound_effects


SHOT_COOLDOWN = "RangerSniperCycle"
ABILITY_COOLDOWN = "RS_LegendaryAbility"


def generate_ability(write, slug, projectile_model, recoil, damage_calculator,
                     ammo_profile, ability_profile, audio_profile, empty_id,
                     flight_marker, falloff_profile):
    if ability_profile is None:
        return None
    reactor = ability_profile["kind"] == "stagger"
    assert ability_profile is not None, "Legendary ability source is required"
    name = ability_profile["name"]
    prefix = f"RS_{slug}_Ability"
    root = f"Root_{prefix}1"
    commit = f"{prefix}_Commit"
    launch = f"{prefix}_Launch"
    impact = f"{prefix}_Impact"
    falloff_id = f"{prefix}_Falloff"
    projectile = f"{prefix}_Projectile"
    abort = f"{prefix}_Abort" if reactor else None
    recovery = ability_profile["shotRecoverySeconds"]
    # Q is a utility-specific absolute override, NOT receiver + two payloads.
    # Its two-round cost never silently doubles the normal ammo damage.
    body, head = ability_profile["bodyDamage"], ability_profile["headDamage"]
    stats = ammo_profile["stats"]
    speed, gravity, reach = stats["speed"], stats["gravity"], stats["range"]
    ammo_id, ammo_cost = ammo_profile["id"], ability_profile["ammoPerUse"]
    cooldown, charge = ability_profile["cooldownSeconds"], ability_profile["chargeSeconds"]
    assert ability_profile["sharedCooldownId"] == ABILITY_COOLDOWN
    assert ammo_profile["compatibleWeapon"] == f"Weapon_Crossbow_{slug}"
    assert ammo_cost == 2 and recovery > 0.12 and cooldown > 0
    assert (charge > 0) == reactor
    effect = prefix+"_Stagger" if reactor else prefix+"_Mark"

    def guard(next_interaction):
        return {"Type": "CooldownCondition", "Id": SHOT_COOLDOWN,
                "Next": {"Type": "CooldownCondition", "Id": ABILITY_COOLDOWN,
                         "Next": next_interaction}}

    def trigger(cooldown, duration, next_interaction):
        return {"Type": "TriggerCooldown", "Cooldown": {"Id": cooldown, "Cooldown": duration},
                "Next": next_interaction}

    enter = f"{prefix}_Charge" if reactor else commit
    write(f"Server/Item/RootInteractions/RangerSnipers/{root}.json", {
        "RequireNewClick": True,
        # Root checks the shared Q timer without charging it before a real shot.
        "Cooldown": {"Id": ABILITY_COOLDOWN, "Cooldown": cooldown, "SkipCooldownReset": True},
        "Rules": {"BlockedBy": ["Primary", "Ability1", "Ability2", "Ability3", "Ability4",
                                "Use", "Pick", "SwapFrom", "SwapTo"]},
        "Tags": {"Attack": ["Ranged"]},
        "Interactions": [guard({"Type": "DurabilityCondition", "Threshold": 0,
                                "Operator": "GreaterThan", "Next": enter})],
    })
    if reactor:
        write(f"Server/Item/Interactions/RangerSnipers/{prefix}_Charge.json", {
            "Type": "Charging", "AllowIndefiniteHold": False,
            "CancelOnOtherClick": True, "HorizontalSpeedMultiplier": 0.25,
            "Effects": {"ItemAnimationId": "ShootFlintlockCharging", "ClearAnimationOnFinish": True,
                        **sound_effects(audio_profile, "SpecialCharge"), "ClearSoundEventOnFinish": True,
                        "MovementEffects": {"DisableSprint": True}},
            "Next": {"0": abort, f"{charge:g}": commit}, "Failed": abort,
        })
        write(f"Server/Item/Interactions/RangerSnipers/{abort}.json", {
            "Type": "Simple", "RunTime": 0, "Effects": sound_effects(audio_profile, "SpecialAbort"),
        })
    # Recheck both timers after a charge. No cells or cooldown are committed on
    # early release, damage/input cancellation, an item swap, or missing ammo.
    write(f"Server/Item/Interactions/RangerSnipers/{commit}.json", guard({
        "Type": "DurabilityCondition", "Threshold": 0, "Operator": "GreaterThan",
        "Next": {
            "Type": "RSChamber", "Operation": "Consume", "WeaponId": f"Weapon_Crossbow_{slug}", "Cost": ammo_cost,
            "Next": trigger(ABILITY_COOLDOWN, cooldown, trigger(SHOT_COOLDOWN, recovery, launch)),
            "Failed": empty_id,
        },
    }))
    write(f"Server/Item/Interactions/RangerSnipers/{launch}.json", {
        "Type": "Projectile", "Config": projectile, "Lifetime": round(reach/speed, 4), "RunTime": 0.12,
        "Effects": {"ItemAnimationId": "Shoot", "CameraEffect": recoil},
    })
    effects = {"Type": "ApplyEffect", "EffectId": effect, "Entity": "Target", "Next": "RS_Despawn"}
    if not reactor:
        effects["Next"] = {"Type": "ApplyEffect", "EffectId": prefix+"_Slow", "Entity": "Target",
                           "Next": "RS_Despawn"}
    write(f"Server/Item/Interactions/RangerSnipers/{falloff_id}.json", {
        "Type": "RSFalloff", "WeaponId": f"Weapon_Crossbow_{slug}",
        "Next": impact, "Failed": "RS_Despawn",
    })
    write(f"Server/Item/Interactions/RangerSnipers/{impact}.json", {
        "Parent": "DamageEntityParent", "DamageCalculator": damage_calculator(body),
        "DamageAttribute": "RS_DistanceDamage",
        "DamageEffects": {"WorldParticles": [{"SystemId": "Impact_Critical", "Scale": 0.65}]},
        "TargetedDamage": {"Head": {"DamageCalculator": damage_calculator(head)}},
        # DamageEntity only follows success Next for non-canceled/unblocked
        # damage, and each effect also rejects every Player entity.
        "Next": effects, "Failed": "RS_Despawn", "Blocked": "RS_Despawn",
    })
    write(f"Server/ProjectileConfigs/RangerSnipers/{projectile}.json", {
        "Model": projectile_model, "UseModelScale": True, "LaunchForce": speed,
        "SpawnOffset": {"X": 0, "Y": 0, "Z": 0}, "SpawnRotationOffset": {"Pitch": 0, "Yaw": 0, "Roll": 0},
        "Physics": {"Type": "Standard", "Gravity": gravity, "TerminalVelocityAir": speed,
                    "TerminalVelocityWater": 30, "RotationMode": "VelocityDamped", "Bounciness": 0,
                    "SticksVertically": False},
        "LaunchLocalSoundEventId": audio_profile["events"]["SpecialFire"]["Local"],
        "LaunchWorldSoundEventId": audio_profile["events"]["SpecialFire"]["World"],
        "Interactions": {"ProjectileSpawn": flight_marker,
                         "ProjectileHit": {"Interactions": [falloff_id]},
                         "ProjectileMiss": {"Interactions": ["RS_Despawn"]}},
    })
    npc_only = {"Id": "IsPlayer", "Inverse": True}
    if reactor:
        write(f"Server/Entity/Effects/RangerSnipers/{effect}.json", {
            "ApplyConditions": [npc_only, {"Id": "HasEffect", "EffectId": "Immunity_Freeze", "Inverse": True},
                                {"Id": "HasEffect", "EffectId": "Hit_Interrupt_Enraged", "Inverse": True}],
            "Duration": ability_profile["staggerSeconds"], "OverlapBehavior": "Overwrite", "Debuff": True,
            "ApplicationEffects": {"HorizontalSpeedMultiplier": 0,
                                   "EntityTopTint": "#ffc176", "EntityBottomTint": "#b57a3f",
                                   "AbilityEffects": {"Disabled": ["Primary", "Ability1", "Ability2", "Ability3", "Ability4"]}},
        })
    else:
        write(f"Server/Entity/Effects/RangerSnipers/{effect}.json", {
            "ApplyConditions": [npc_only], "Duration": ability_profile["markSeconds"], "OverlapBehavior": "Overwrite", "Debuff": True,
            "ApplicationEffects": {"EntityTopTint": "#fff0bd", "EntityBottomTint": "#8df6ff",
                                   "Particles": [{"SystemId": "RS_Luminia_Dawnpiercer_Idle", "TargetEntityPart": "Entity",
                                                  "PositionOffset": {"Y": 0.8}, "Scale": 0.7,
                                                  "ClearParticlesOnRemove": True}]},
        })
        write(f"Server/Entity/Effects/RangerSnipers/{prefix}_Slow.json", {
            "ApplyConditions": [npc_only, {"Id": "HasEffect", "EffectId": "Immunity_Slow", "Inverse": True}],
            "Duration": ability_profile["slowSeconds"], "OverlapBehavior": "Overwrite", "Debuff": True,
            "StatusEffectIcon": "UI/StatusEffects/Icon_Slow.png",
            "ApplicationEffects": {"HorizontalSpeedMultiplier": ability_profile["speedMultiplier"]},
        })
    return {
        "item_id": f"Weapon_Crossbow_{slug}", "name": name, "root_id": root,
        "commit_id": commit, "launch_id": launch, "impact_id": impact, "projectile_id": projectile,
        "flight_marker_root_id": flight_marker, "falloff_interaction_id": falloff_id,
        "damage_attribute": "RS_DistanceDamage", "falloff": falloff_profile,
        "charge_id": f"{prefix}_Charge" if reactor else None,
        "charge_seconds": charge, "body_damage": body, "head_damage": head,
        "charge_audio_ids": audio_profile["events"].get("SpecialCharge") if reactor else None,
        "special_fire_audio_ids": audio_profile["events"]["SpecialFire"],
        "abort_audio_ids": audio_profile["events"].get("SpecialAbort") if reactor else None,
        "abort_id": abort,
        "damage_mode": "fixed_ability_override",
        "ammo_damage_added_to_ability": False,
        "ammo_id": ammo_id, "compatible_ammo_ids": [ammo_id], "ammo_per_shot": ammo_cost,
        "ammo_paid_at": "manual_reload_commit",
        "ammo_consumed_from": "ItemStack.RS_Chamber",
        "ammo_stats": stats,
        "speed_blocks_per_second": speed, "gravity": gravity, "nominal_range_blocks": reach,
        "ability_cooldown_id": ABILITY_COOLDOWN, "ability_cooldown_seconds": cooldown,
        "shot_cooldown_id": SHOT_COOLDOWN, "shot_recovery_seconds": recovery,
        "effect_ids": [effect] if reactor else [effect, prefix+"_Slow"],
        "effect_duration_seconds": ability_profile["staggerSeconds"] if reactor else ability_profile["markSeconds"],
        "slow_duration_seconds": 0 if reactor else ability_profile["slowSeconds"],
        "effect_horizontal_speed_multiplier": 0 if reactor else ability_profile["speedMultiplier"],
        "player_targets_receive_effects": False,
        "canceled_or_blocked_damage_runs_effects": False,
        "single_damage_event": True,
        "cleanup_id": "RS_Despawn",
        "cleanup_on_failed_blocked_and_effect_skip": True,
    }
