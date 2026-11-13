"""Build the rifle sentry asset pack against the installed Hytale and MMO assets."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


HERE = Path(__file__).resolve().parent
ART = "Common/Items/Deployables/AS_Rifle_Sentry/"
MODEL_PATH = "Server/Models/Deployables/AS_Rifle_Sentry.json"
STOCK_MODEL = "Server/Models/Deployables/Crossbow_Turret.json"
SPAWNER_PATH = "Server/DeployableSpawners/MMO_Sentry_Turret.json"
ABILITY_PATH = "Server/MMOSkillTree/Abilities/Archery/Sentry_Turret.json"
FIRE_EVENT = "AS_Rifle_Sentry_Fire"
FIRE_PATH = f"Server/Audio/SoundEvents/Arsenal/{FIRE_EVENT}.json"
PARTICLE_DIR = "Server/Particles/Arsenal/RifleSentry"
PULSE_CLIPS = [f"Sounds/Arsenal/AS_Rifle_Sentry/PulseReport_{number:02d}.ogg" for number in range(1, 6)]
VERSION = "0.2.9"
ENDLESS_VERSION = "14.5.6"
MODEL_SCALE = 2.0
INTERVAL = 1.968
DAMAGE = 12.0
FIRE_GAIN_DB = 2.020599913279624
ANIMATIONS = {
    "Deploy": ("Deploy", 0.64, False),
    "Loop": ("Idle", 1.0, True),
    "Shoot": ("Shoot", 2.0, False),
}


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def read(archive, path):
    return json.loads(archive.read(path))


def asset_pack(mmo, game, endless):
    assert read(mmo, "manifest.json")["Version"] == "1.7.4"
    assert read(endless, "manifest.json")["Version"] == ENDLESS_VERSION

    ability = read(mmo, ABILITY_PATH)
    assert ability["Cooldown"]["Ms"] == 30_000
    assert ability["Cost"] == {"Stat": "STAMINA", "Amount": 20}
    assert ability["Casting"]["HeldWeaponCategories"] == ["ARCHERY"]
    assert ability["Body"]["Interactions"] == [{
        "Type": "MmoDeployable", "SpawnerId": "MMO_Sentry_Turret",
        "SpawnFace": "UP", "Turret": True,
    }]

    spawner = read(mmo, SPAWNER_PATH)
    config = spawner["Config"]
    assert (config["Type"], config["Id"], config["Model"]) == ("Turret", "mmo_sentry_turret", "Crossbow_Turret")
    assert config["ShotInterval"] == config["BurstCooldown"] == 1 and config["ProjectileDamage"] == 6
    config.update(Type="RifleSentryHostileTurret", Model="AS_Rifle_Sentry", ModelScale=MODEL_SCALE,
                  ShotInterval=INTERVAL, BurstCooldown=INTERVAL,
                  DeployDelay=1.25, DetectionRadius=18, TrackableRadius=20,
                  ProjectileDamage=DAMAGE, ProjectileHitLocalSoundEventId="SFX_Blunderbuss_Hit",
                  ProjectileHitWorldSoundEventId="SFX_Blunderbuss_Hit")
    config["ProjectileSpawnOffsets"]["UP"]["Y"] = MODEL_SCALE * 33 / 32
    bullet = config["ProjectileConfig"]
    bullet.update(Model="Bullet_Blunderbuss", LaunchForce=100, LaunchWorldSoundEventId=FIRE_EVENT)
    bullet["Physics"]["SticksVertically"] = False
    assert config["BurstCount"] == 1 and config["MaxLiveCount"] == 1
    assert config["DoLineOfSightTest"] and config["RespectTeams"] and not config["CanShootOwner"]
    assert config["Stats"]["Health"] == {"Initial": 25, "Max": 25}

    model = read(game, STOCK_MODEL)
    model["Model"] = f"{ART.removeprefix('Common/')}AS_Rifle_Sentry.blockymodel"
    model["Texture"] = f"{ART.removeprefix('Common/')}AS_Rifle_Sentry.png"
    for key, (clip, speed, looping) in ANIMATIONS.items():
        path = f"{ART.removeprefix('Common/')}AS_Rifle_Sentry_{clip}.blockyanim"
        model["AnimationSets"][key] = {"Animations": [{
            "Animation": path, "Speed": speed, "Looping": looping,
        }]}

    fire = {
        "AudioCategory": "AudioCat_Weapons",
        "Volume": FIRE_GAIN_DB,
        "SpatialBlend": 1,
        "StartAttenuationDistance": 4,
        "MaxDistance": 72,
        "MaxInstance": 16,
        "PreventSoundInterruption": False,
        "Layers": [{
            "Files": PULSE_CLIPS,
            "Volume": 0,
            "StartDelay": 0,
            "Looping": False,
            "RoundRobinHistorySize": 1,
        }],
    }

    manifest = {
        "Group": "Steven",
        "Name": "360 Rifle Sentry",
        "Version": VERSION,
        "Description": "A pulse rifle sentry that scales with its owner's class and combat stats.",
        "ServerVersion": ">=0.7.0 <0.8.0",
        "Dependencies": {
            "Hytale:Deployables": "*",
            "Ziggfreed:MMOSkillTree": "=1.7.4",
            "Airijko:EndlessLevelingCore": f"={ENDLESS_VERSION}",
        },
        "Main": "steven.riflesentry.RifleSentryPlugin",
        "IncludesAssetPack": True,
    }
    files = {
        "manifest.json": encode(manifest),
        SPAWNER_PATH: encode(spawner),
        MODEL_PATH: encode(model),
        FIRE_PATH: encode(fire),
    }
    art_paths = [model["Model"], model["Texture"]]
    art_paths.extend(group["Animations"][0]["Animation"] for group in model["AnimationSets"].values())
    for path in art_paths + PULSE_CLIPS:
        asset = f"Common/{path}"
        files[asset] = (HERE / "resources" / asset).read_bytes()
    resources = HERE / "resources"
    particles = resources / PARTICLE_DIR
    system = particles / "AS_Rifle_Sentry_PlasmaFlash.particlesystem"
    if not system.is_file():
        raise FileNotFoundError(system)
    for path in sorted(particles.rglob("*")):
        if path.suffix not in {".particlesystem", ".particlespawner"}:
            continue
        files[path.relative_to(resources).as_posix()] = path.read_bytes()
    return files


def compile_runtime(java_home, server_jar, endless_jar, mmo_jar):
    sources = sorted((HERE / "src").rglob("*.java"))
    if not sources:
        raise ValueError("Rifle Sentry runtime sources are missing")
    with TemporaryDirectory(prefix="rifle-sentry-classes-") as scratch:
        classes = Path(scratch)
        subprocess.run([
            str(java_home / "bin/javac.exe"), "--release", "25", "-encoding", "UTF-8", "-proc:none",
            "-classpath", ";".join(str(path.resolve()) for path in (server_jar, endless_jar, mmo_jar)),
            "-d", str(classes), *map(str, sources),
        ], check=True)
        return {path.relative_to(classes).as_posix(): path.read_bytes() for path in classes.rglob("*.class")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mmo", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--endless-leveling", type=Path, required=True)
    parser.add_argument("--server-jar", type=Path, required=True)
    parser.add_argument("--java-home", type=Path, default=Path("C:/Tools/Java/jdk-25.0.5+8"))
    args = parser.parse_args()
    with ZipFile(args.mmo) as mmo, ZipFile(args.assets) as game, ZipFile(args.endless_leveling) as endless:
        files = asset_pack(mmo, game, endless)
    files.update(compile_runtime(args.java_home, args.server_jar, args.endless_leveling, args.mmo))

    dist = HERE / "dist"
    dist.mkdir(exist_ok=True)
    output = dist / f"360-Rifle-Sentry-{VERSION}.jar"
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data in sorted(files.items()):
            info = ZipInfo(path, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, data)
    with ZipFile(output) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == files.keys()
    print(f"Built {output.name}, {len(files)} entries, SHA256 {sha256(output.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
