#!/usr/bin/env python3
"""Offline publication audit for the curated 360 No Scope repository.

The default audit reads only indexed files, and refuses unstaged changes to those
files so that the bytes audited are the bytes about to be committed. Use
--working-tree while assembling a new checkout before its first git add.
No external services, credentials, game installation, or third-party SDKs are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path, PurePosixPath


MAX_FILE_BYTES = 50 * 1024 * 1024
BLOCKED_COMPONENTS = {
    ".aws", ".ssh", ".gnupg", ".codex", ".agents", ".grok",
    "worlds", "players", "backups", "snapshots", "deployments",
    "test-server", "test_server", "node_modules", "__pycache__",
    "browser-profiles", "browser_profiles", "raw-samples", "raw_samples",
    "sample-banks", "sample_banks", "credentials", "logs", "evidence",
}
BLOCKED_NAMES = {
    "auth.json", "auth.enc", "credentials.json", "credentials.toml",
    ".env", ".netrc", ".npmrc", "server-config.json", "config.toml",
    "requirements.toml", "id_rsa", "id_ed25519",
}
BLOCKED_SUFFIXES = {
    ".jar", ".class", ".exe", ".dll", ".zip", ".7z", ".rar", ".tar",
    ".gz", ".wav", ".mp3", ".flac", ".aiff", ".aif", ".blend1",
    ".pyc", ".pyd", ".so", ".dmp", ".log", ".sqlite", ".db",
}
TEXT_SUFFIXES = {
    ".py", ".java", ".json", ".md", ".txt", ".ps1", ".yml", ".yaml",
    ".toml", ".lang", ".blockymodel", ".blockyanim", ".bbmodel", ".xml",
    ".sh", ".bat", ".cmd", ".ini", ".csv", ".gitattributes", ".gitignore",
}
SECRET_RULES = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "provider_api_key": re.compile(r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{32,}|xox[baprs]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{35})\b"),
    "credential_url": re.compile(r"https?://[^\s/@:]+:[^\s/@]+@", re.I),
}
DISPLAY_IDS = {
    "AD_Armor_Stand_Wood", "AD_Armor_Stand_Metal", "AD_Wall_Holder_Wood",
    "AD_Wall_Holder_Metal", "AD_Wall_Rack_Wood", "AD_Wall_Rack_Metal",
}


class Audit:
    def __init__(self, root: Path):
        self.root = root
        self.errors: list[str] = []
        self.checks = 0
        self.paths: set[str] = set()
        self.json_docs: dict[str, object] = {}

    def check(self, condition: bool, message: str) -> bool:
        self.checks += 1
        if not condition:
            self.errors.append(message)
        return condition

    def git(self, *args: str) -> bytes:
        p = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True)
        if p.returncode:
            raise ValueError("Git could not inspect this repository; initialize its own Git root first.")
        return p.stdout

    def inventory(self, working_tree: bool) -> None:
        if working_tree:
            def walk(directory: Path):
                for child in sorted(directory.iterdir()):
                    relative = child.relative_to(self.root).as_posix()
                    if relative in {".git", ".build", "dist"} or child.name == "__pycache__":
                        continue
                    if child.is_symlink() or child.is_file():
                        yield relative
                    elif child.is_dir():
                        yield from walk(child)
            candidates = list(walk(self.root))
        else:
            actual_root = Path(self.git("rev-parse", "--show-toplevel").decode().strip()).resolve()
            if actual_root != self.root:
                raise ValueError("Refusing the parent workspace: this folder needs its own Git root.")
            entries = self.git("ls-files", "--stage", "-z").split(b"\0")
            candidates = []
            for entry in entries:
                if not entry:
                    continue
                meta, raw_path = entry.split(b"\t", 1)
                mode, _, stage = meta.split()
                relative = raw_path.decode("utf-8")
                self.check(mode in {b"100644", b"100755"}, f"Unsupported Git file mode: {relative}")
                self.check(stage == b"0", f"Unresolved index entry: {relative}")
                candidates.append(relative)
            if self.git("diff", "--no-ext-diff", "--name-only", "-z"):
                raise ValueError("Indexed files have unstaged changes. Stage the final bytes before auditing.")
        self.check(bool(candidates), "No publication files found.")
        for relative in candidates:
            pure = PurePosixPath(relative)
            path = self.root / relative
            safe = not pure.is_absolute() and ".." not in pure.parts
            safe = safe and not any(part.lower() in BLOCKED_COMPONENTS for part in pure.parts)
            safe = safe and pure.name.lower() not in BLOCKED_NAMES
            safe = safe and pure.suffix.lower() not in BLOCKED_SUFFIXES
            if not self.check(safe, f"Forbidden publication path: {relative}"):
                continue  # Never open a file rejected by its path.
            if not self.check(not path.is_symlink(), f"Symlink cannot be published: {relative}"):
                continue
            if not self.check(path.is_file(), f"Missing indexed file: {relative}"):
                continue
            if not self.check(path.stat().st_size <= MAX_FILE_BYTES, f"File exceeds 50 MiB: {relative}"):
                continue
            if not self.check(path.resolve().is_relative_to(self.root), f"Path escapes repository: {relative}"):
                continue
            self.paths.add(relative)

    def scan(self) -> None:
        for relative in sorted(self.paths):
            path = self.root / relative
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".gitignore", ".gitattributes", "LICENSE", "NOTICE"}:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeError:
                self.check(False, f"Invalid UTF-8 text: {relative}")
                continue
            for rule, pattern in SECRET_RULES.items():
                match = pattern.search(text)
                if match:
                    line = text.count("\n", 0, match.start()) + 1
                    self.check(False, f"Potential secret ({rule}) in {relative}:{line}; value withheld.")
                else:
                    self.check(True, "")
            if path.suffix.lower() == ".json":
                try:
                    self.json_docs[relative] = json.loads(text)
                    self.check(True, "")
                except json.JSONDecodeError as exc:
                    self.check(False, f"Invalid JSON: {relative}:{exc.lineno}")

    def load(self, relative: str) -> dict:
        value = self.json_docs.get(relative)
        self.check(isinstance(value, dict), f"Missing or invalid JSON object: {relative}")
        return value if isinstance(value, dict) else {}

    def fingerprints(self) -> None:
        manifest = self.load("publication-manifest.json")
        records: list[tuple[str, str]] = []
        for item in manifest.get("files", []) + manifest.get("sources", []):
            if isinstance(item, dict):
                records.append((str(item.get("path", "")), str(item.get("sha256", ""))))
        modules = manifest.get("modules", {})
        if isinstance(modules, list):
            modules = {str(item.get("name", i)): item for i, item in enumerate(modules) if isinstance(item, dict)}
        for module in modules.values() if isinstance(modules, dict) else []:
            if not isinstance(module, dict):
                continue
            base = str(module.get("resource_root", "")).rstrip("/")
            for item in module.get("files", []):
                if isinstance(item, dict):
                    relative = str(item.get("path", ""))
                    records.append((f"{base}/{relative}" if base else relative, str(item.get("sha256", ""))))
        self.check(bool(records), "Publication manifest has no file fingerprints.")
        covered = set()
        for relative, expected in records:
            if not self.check(relative in self.paths, f"Fingerprint refers to an unpublished file: {relative}"):
                continue
            covered.add(relative)
            if not self.check(bool(re.fullmatch(r"[a-fA-F0-9]{64}", expected)), f"Invalid SHA256 fingerprint: {relative}"):
                continue
            actual = hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
            self.check(actual == expected.lower(), f"Fingerprint mismatch: {relative}")
        resources = {p for p in self.paths if re.match(r"modules/(?:weapons|displays)/resources/", p)}
        self.check(resources <= covered, f"Publication manifest misses {len(resources - covered)} resource fingerprint(s).")
        java_sources = {p for p in self.paths if re.match(r"modules/(?:weapons|displays)/src/java/", p) and p.endswith(".java")}
        self.check(java_sources <= covered, f"Publication manifest misses {len(java_sources - covered)} Java source fingerprint(s).")

    def module(self, name: str, group: str, plugin: str, main: str, version: str) -> str:
        base = f"modules/{name}/resources/"
        manifest = self.load(base + "manifest.json")
        for key, expected in {"Group": group, "Name": plugin, "Main": main, "Version": version, "IncludesAssetPack": True}.items():
            self.check(manifest.get(key) == expected, f"Unexpected {name} manifest {key}.")
        java_file = f"modules/{name}/src/java/{main.replace('.', '/')}.java"
        self.check(java_file in self.paths, f"Missing plugin Java entry point: {java_file}")
        return base

    def content(self) -> None:
        weapons = self.module("weapons", "Steven", "360 No Scope", "steven.rangersnipers.RangerSnipersPlugin", "2.0.5")
        displays = self.module("displays", "Steven", "Armor Displays", "steven.armordisplays.ArmorDisplaysPlugin", "0.1.0")
        profile_doc = self.load(weapons + "ranger-snipers-reload-profiles.json")
        profiles = profile_doc.get("Profiles", [])
        self.check(isinstance(profiles, list) and len(profiles) == 54, "Expected 54 gun reload/falloff profiles.")
        profiles = [p for p in profiles if isinstance(p, dict)] if isinstance(profiles, list) else []
        guns = {str(p.get("WeaponId", "")) for p in profiles}
        ammo = {str(p.get("AmmoId", "")) for p in profiles}
        self.check(len(guns) == 54 and "" not in guns, "Gun profiles must identify 54 distinct weapons.")
        self.check(len(ammo) == 54 and "" not in ammo, "Gun profiles must identify 54 distinct active ammunition items.")
        items = {PurePosixPath(p).stem: p for p in self.paths if p.startswith(weapons + "Server/Item/Items/") and p.endswith(".json")}
        language_path = weapons + "Server/Languages/en-US/server.lang"
        language = {}
        if self.check(language_path in self.paths, "Missing English item names/descriptions."):
            for line in (self.root / language_path).read_text(encoding="utf-8-sig").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    language[key.strip()] = value.strip()
        for item_id in sorted(guns | ammo):
            if not self.check(item_id in items, f"Profile item is absent: {item_id}"):
                continue
            item = self.load(items[item_id])
            translations = item.get("TranslationProperties", {})
            for key in ["Name", "Description"]:
                ref = translations.get(key, "") if isinstance(translations, dict) else ""
                lang_key = ref.removeprefix("server.")
                self.check(bool(language.get(lang_key)), f"Missing {key.lower()} translation for {item_id}.")
            for key in ["Icon", "Model", "Texture"]:
                ref = item.get(key, "")
                self.check(isinstance(ref, str) and weapons + "Common/" + ref in self.paths, f"Missing {key.lower()} asset for {item_id}.")
        for profile in profiles:
            weapon_id = str(profile.get("WeaponId", ""))
            self.check(isinstance(profile.get("Capacity"), int) and profile["Capacity"] > 0, f"Invalid magazine capacity: {weapon_id}")
            self.check(profile.get("FalloffMetric") == "traveledPath", f"Missing traveled-path damage falloff: {weapon_id}")
            points = profile.get("FalloffPoints", [])
            valid = isinstance(points, list) and len(points) >= 2
            if valid:
                try:
                    distances = [float(p["Distance"]) for p in points]
                    factors = [float(p["Multiplier"]) for p in points]
                    valid = distances == sorted(set(distances)) and distances[0] == 0 and all(0 < v <= 1 for v in factors) and factors == sorted(factors, reverse=True)
                except (KeyError, TypeError, ValueError):
                    valid = False
            self.check(valid, f"Invalid distance damage curve: {weapon_id}")
        owner = self.load(weapons + "ranger-snipers-owner-tail-profiles.json").get("Profiles", [])
        owner_guns = {p.get("WeaponId") for p in owner if isinstance(p, dict)} if isinstance(owner, list) else set()
        self.check(owner_guns == guns and len(owner) == 54, "Owner-tail profiles must cover each gun exactly once.")
        events = {PurePosixPath(p).stem: p for p in self.paths if p.startswith(weapons + "Server/Audio/SoundEvents/") and p.endswith(".json")}
        clips = {p for p in self.paths if p.startswith(weapons + "Common/") and p.endswith(".ogg")}
        self.check(len(events) == 292, f"Expected 292 sound events, found {len(events)}.")
        self.check(len(clips) == 533, f"Expected 533 incorporated audio clips, found {len(clips)}.")
        for entry in owner if isinstance(owner, list) else []:
            if isinstance(entry, dict):
                for key in ["PrimaryEventId", "AbilityEventId"]:
                    if key == "PrimaryEventId" or key in entry:
                        self.check(entry.get(key) in events, f"Missing owner-tail event for {entry.get('WeaponId', '?')} ({key}).")
        for event_id, path in sorted(events.items()):
            event = self.load(path)
            layers = event.get("Layers", [])
            for layer in layers if isinstance(layers, list) else []:
                for clip in layer.get("Files", []) if isinstance(layer, dict) else []:
                    self.check(weapons + "Common/" + str(clip) in clips, f"Sound event refers to missing clip: {event_id}")
        for path in sorted(clips):
            data = (self.root / path).read_bytes()
            marker = data.find(b"\x01vorbis")
            valid = data.startswith(b"OggS") and marker >= 0 and len(data) >= marker + 16
            self.check(valid, f"Invalid OGG/Vorbis clip: {path}")
            if valid:
                channels = data[marker + 11]
                sample_rate = struct.unpack_from("<I", data, marker + 12)[0]
                self.check(channels == 1 and sample_rate == 48000, f"Clip must be mono 48 kHz: {path}")
        display_items = {PurePosixPath(p).stem: p for p in self.paths if p.startswith(displays + "Server/Item/Items/") and p.endswith(".json")}
        self.check(set(display_items) == DISPLAY_IDS, "Expected exactly six supported armor stand/weapon display items.")
        for item_id, path in sorted(display_items.items()):
            item = self.load(path)
            block = item.get("BlockType", {})
            self.check(isinstance(block, dict), f"Missing display block definition: {item_id}")
            if not isinstance(block, dict):
                continue
            refs = {"icon": item.get("Icon", ""), "model": block.get("CustomModel", "")}
            textures = block.get("CustomModelTexture", [])
            refs.update({f"texture {i}": texture.get("Texture", "") for i, texture in enumerate(textures) if isinstance(texture, dict)})
            self.check(bool(textures), f"Missing display texture definitions: {item_id}")
            for key, ref in refs.items():
                self.check(isinstance(ref, str) and displays + "Common/" + ref in self.paths, f"Missing display {key} asset: {item_id}")
            components = block.get("BlockEntity", {}).get("Components", {})
            expected_capacity = 6 if "Armor_Stand" in item_id else 3 if "Wall_Rack" in item_id else 1
            self.check(components.get("ItemContainerBlock", {}).get("Capacity") == expected_capacity, f"Invalid native display container capacity: {item_id}")
            self.check("ADDisplay" in components, f"Missing display visual persistence component: {item_id}")
        self.check(weapons + "Server/Item/Items/RangerSnipers/Bench/RS_Gunsmith_Bench.json" in self.paths, "Missing Gunsmith's Bench item.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--working-tree", action="store_true", help="Audit curated files before initial git add; skips .git/.build/dist.")
    args = parser.parse_args()
    audit = Audit(args.root.resolve())
    try:
        audit.inventory(args.working_tree)
        audit.scan()
        audit.fingerprints()
        audit.content()
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        audit.check(False, str(exc))
    if audit.errors:
        print(f"FAIL: {len(audit.errors)} issue(s), {audit.checks:,} checks, {len(audit.paths):,} files.")
        for error in audit.errors:
            print(" - " + error)
        return 1
    print(f"PASS: {audit.checks:,} checks; {len(audit.paths):,} files; 54 guns, 54 active ammo, 6 displays, 533 clips, 292 events.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
