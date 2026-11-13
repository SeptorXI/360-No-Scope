# Hytale Server Panel

A Windows desktop app for starting and stopping a local Hytale server, reading its console, managing its mod list and editing settings and the allowlist.

From the collection root, run `& ./tools/Build-WindowsTools.ps1` in PowerShell on Windows with .NET Framework installed. The build writes `tools/dist/Hytale Server Panel.exe`.

Start the app with the path to a Hytale server installation that contains `Run-Server.bat`, `Server/HytaleServer.jar` and `Assets.zip`. For example, from the collection root run `& 'tools/dist/Hytale Server Panel.exe' 'D:\Games\HytaleServer'`. With no argument, the panel looks for the server beside the executable.
