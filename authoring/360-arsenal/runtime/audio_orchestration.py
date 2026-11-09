"""Native cancellable sound cues alongside one uninterrupted reload animation."""
from copy import deepcopy

FPS = 60


def sound_effects(profile, action):
    pair = profile["events"][action]
    assert isinstance(pair["Local"], str) and pair["Local"]
    assert isinstance(pair["World"], str) and pair["World"]
    return {"LocalSoundEventId": pair["Local"], "WorldSoundEventId": pair["World"]}


def reload_branch(write, tier, variant, animation_id, rules):
    """First Parallel child uses the SAME context/TOKEN; only cues are forked.

    Native pushRoot changes the chain's active root, so the main child repeats
    the reload rules. The cue fork has no ammo/commit operation and finishes
    before the main animation. Native cancelChains recursively cancels it.
    """
    slug = tier["id"].removeprefix("Weapon_Crossbow_")
    prefix = f"Root_RS_{slug}_Reload_{variant.title()}"
    main_root, cue_root = prefix + "_Main", prefix + "_Cues"
    profile = tier["audio"]
    duration = tier["reload"]["durationSeconds"]
    frames = round(duration * FPS)
    assert frames / FPS == duration
    entries = profile["reloadTimelines"][variant]
    assert entries and [entry["phase"] for entry in entries] == sorted(entry["phase"] for entry in entries)
    timeline, cues = [], []
    previous_frame = 0
    for entry in entries:
        phase, action = entry["phase"], entry["event"]
        assert 0 <= phase < 1 and action != "Ready"
        frame = round(phase * frames)
        assert previous_frame <= frame < frames
        if frame > previous_frame:
            timeline.append({"Type": "Simple", "RunTime": round((frame - previous_frame) / FPS, 9)})
        cue_index = len(timeline)
        timeline.append({"Type": "Simple", "RunTime": 0, "Effects": sound_effects(profile, action)})
        cues.append({
            "action": action, "phase": phase, "frame": frame,
            "delay_seconds": round(frame / FPS, 9),
            "event_ids": deepcopy(profile["events"][action]),
            "root_id": cue_root,
            "runtime_path": f"Server/Item/RootInteractions/RangerSnipers/{cue_root}.json#/Interactions/{cue_index}/Effects",
        })
        previous_frame = frame
    write(f"Server/Item/RootInteractions/RangerSnipers/{main_root}.json", {
        "RequireNewClick": False,
        "Rules": deepcopy(rules),
        "Interactions": [{
            "Type": "Simple", "RunTime": duration, "HorizontalSpeedMultiplier": 0.6,
            "Effects": {"ItemAnimationId": animation_id, "ClearAnimationOnFinish": True,
                        "MovementEffects": {"DisableSprint": True}},
            "Next": {
                "Type": "RSChamber", "Operation": "CommitReload", "WeaponId": tier["id"],
                "Failed": f"RS_{slug}_Empty",
                "Next": {"Type": "Simple", "RunTime": 0, "Effects": sound_effects(profile, "Ready")},
            },
        }],
    })
    write(f"Server/Item/RootInteractions/RangerSnipers/{cue_root}.json", {
        "RequireNewClick": False,
        "Rules": {"BlockedBy": [], "Blocking": [], "InterruptedBy": ["SwapFrom", "SwapTo", "Death"]},
        "Interactions": timeline,
    })
    return {"Type": "Parallel", "Interactions": [main_root, cue_root]}, {
        "item_id": tier["id"], "variant": variant, "animation_id": animation_id,
        "duration_seconds": duration, "duration_frames": frames, "fps": FPS,
        "parallel_main_index": 0, "parallel_audio_index": 1,
        "main_root_id": main_root, "audio_root_id": cue_root,
        "main_context_token_preserved": True, "audio_branch_has_commit": False,
        "main_runtime_path": f"Server/Item/RootInteractions/RangerSnipers/{main_root}.json#/Interactions/0",
        "commit_runtime_path": f"Server/Item/RootInteractions/RangerSnipers/{main_root}.json#/Interactions/0/Next",
        "cues": cues,
        "ready": {"action": "Ready", "delay_seconds": duration,
                  "condition": "successful_reload_commit_only", "event_ids": deepcopy(profile["events"]["Ready"]),
                  "runtime_path": f"Server/Item/RootInteractions/RangerSnipers/{main_root}.json#/Interactions/0/Next/Next/Effects"},
    }
