# Hytale Quiet Mode

A Windows helper that adjusts configured background app priorities while Hytale is active. It restores the priorities when the game or server stops. The Server Panel already includes the same manager, so this standalone helper is mainly for setups without the panel.

From the collection root, run `& ./tools/Build-WindowsTools.ps1` in PowerShell on Windows with .NET Framework installed. The build writes `tools/dist/Hytale Quiet Mode.exe`. The helper uses a local `PanelSettings` folder beside the executable.
