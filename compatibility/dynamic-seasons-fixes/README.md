# Dynamic Seasons Planting and Weather Fixes

The planting fix routes block-option changes through the correct interaction. The weather fix checks entity-store ownership before updating player weather and season HUD state.

The Java transforms were authored for the reviewed upstream 7.1.4 archive. The 7.1.5 build script checks that the affected classes are identical before carrying those fixes forward. Supply the original archives separately and choose a new output path.

```powershell
python build.py PATH_TO_ORIGINAL_7_1_4_JAR PATH_TO_ORIGINAL_7_1_5_JAR PATH_TO_OUTPUT_JAR --server-jar PATH_TO_SERVER_JAR
```

The build uses JDK 25 and writes a local patched archive for the administrator. Use that output in place of the corresponding original Dynamic Seasons JAR.
