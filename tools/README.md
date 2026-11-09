# Build tools

`build.py` compiles the Java runtime and packages the committed game resources for each module. It uses Python 3.10+ and JDK 25+, without downloading dependencies or accessing a running server.

Supply your own Hytale server SDK and Simple Enchantments JAR. These third-party binaries are not distributed in this repository. The weapons runtime uses the Simple Enchantments API; the display runtime only needs the Hytale SDK.

```powershell
python tools/build.py --component all `
  --java-home "C:\path\to\jdk-25" `
  --server-jar "C:\path\to\HytaleServer.jar" `
  --enchant-jar "C:\path\to\SimpleEnchantments.jar"
```

The same inputs can be supplied through `JAVA_HOME`, `HYTALE_SERVER_JAR`, and `SIMPLE_ENCHANTMENTS_JAR`. With no Java-home setting, the builder uses `javac` on `PATH`. Use `--component weapons` or `--component displays` to build one module. Display-only builds do not require the enchantment JAR.

Output names come from the committed module manifests: `dist/360-No-Scope-<version>.jar` and `dist/Armor-Displays-<version>.jar`. Generated classes stay under `.build/`. Packaging retains every resource byte, including both weapons runtime profile files, and adds freshly compiled runtime classes. It does not run the historical asset-authoring scripts or use release-JAR bootstraps.

Archive entry order, timestamps, and permissions are fixed. With identical sources, resources, external dependencies, Python/zlib, and JDK, repeated builds produce identical JARs. A rebuild can have a different archive hash from an earlier accepted release that used different ZIP metadata; compare resource bytes and runtime behavior when validating that transition.

The repository's `publication-manifest.json` pins every canonical resource and Java source by SHA-256. The builder checks the selected module's complete file lists and hashes before compilation. Update that reviewed inventory after intentional edits. A module-local `design/resource-manifest.json`, if present, adds a second resource inventory check using a `files` array of `path` and `sha256` records.
