using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal sealed class ServerModsPage : UserControl
{
    private static readonly Color SelectedRow = Color.FromArgb(36, 49, 55);
    private const TextFormatFlags TableTextFlags = TextFormatFlags.Left | TextFormatFlags.VerticalCenter |
        TextFormatFlags.SingleLine | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPrefix |
        TextFormatFlags.PreserveGraphicsClipping;
    private static readonly Regex LogName = new Regex(@"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_server\.log$");
    private static readonly Regex LogLine = new Regex(@"^\[[^\]]+\]\s+\[(PluginManager|AssetModule(?:\|P)?|HytaleServer)\]\s+(.*)$");
    private const int ManifestLimit = 256 * 1024;

    private readonly string modsPath;
    private readonly string logsPath;
    private readonly string gameModsPath;
    private readonly ListView modList;
    private readonly Label status;
    private bool running;

    internal ServerModsPage(string serverRoot)
    {
        modsPath = Path.Combine(serverRoot, "Server", "mods");
        logsPath = Path.Combine(serverRoot, "Server", "logs");
        gameModsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Hytale", "UserData", "Mods");
        BackColor = CyberpunkTheme.Background;
        ForeColor = CyberpunkTheme.Ink;
        Font = CyberpunkTheme.BodyFont();
        Dock = DockStyle.Fill;

        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(16, 12, 16, 12), ColumnCount = 1, RowCount = 6 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 20));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 30));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 43));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 54));
        Controls.Add(layout);

        layout.Controls.Add(new Label {
            Text = "03 // ASSET INVENTORY", Font = CyberpunkTheme.HeadingFont(9),
            ForeColor = CyberpunkTheme.Cyan, Dock = DockStyle.Fill, Margin = Padding.Empty
        }, 0, 0);
        layout.Controls.Add(new Label {
            Text = "Dedicated server mods", Font = CyberpunkTheme.HeadingFont(21),
            ForeColor = CyberpunkTheme.Accent, Dock = DockStyle.Fill, Margin = Padding.Empty
        }, 0, 1);
        layout.Controls.Add(new Label {
            Text = "Mods downloaded in Hytale's main menu stay in the game's library. The dedicated server uses its own mods folder.",
            ForeColor = CyberpunkTheme.Muted, Dock = DockStyle.Fill, Margin = Padding.Empty
        }, 0, 2);

        var actions = new FlowLayoutPanel { Dock = DockStyle.Fill, Margin = Padding.Empty, WrapContents = false };
        actions.Controls.Add(ActionButton("RefreshModsButton", "Refresh", 100, () => RefreshFromDisk(running), true));
        actions.Controls.Add(ActionButton("OpenModsFolderButton", "Open server mods folder", 185, () => OpenFolder(modsPath)));
        actions.Controls.Add(ActionButton("OpenGameModsFolderButton", "Open game mods folder", 180, () => OpenFolder(gameModsPath)));
        layout.Controls.Add(actions, 0, 3);

        modList = new ListView {
            Name = "ServerModsList", AccessibleName = "Dedicated server mods", View = View.Details,
            FullRowSelect = true, MultiSelect = false, HideSelection = false, OwnerDraw = true,
            HeaderStyle = ColumnHeaderStyle.Nonclickable, Dock = DockStyle.Fill, BorderStyle = BorderStyle.None,
            BackColor = CyberpunkTheme.Input, ForeColor = CyberpunkTheme.Ink, Font = CyberpunkTheme.BodyFont(10.5f)
        };
        modList.Columns.Add("Mod", 214);
        modList.Columns.Add("Status", 137);
        modList.Columns.Add("Version on disk", 128);
        modList.Columns.Add("Server package", 205);
        modList.DrawColumnHeader += DrawColumnHeader;
        modList.DrawSubItem += DrawCell;
        modList.ClientSizeChanged += FitPackageColumn;

        var tableFrame = new Panel { Dock = DockStyle.Fill, Margin = Padding.Empty, Padding = new Padding(1), BackColor = CyberpunkTheme.Border };
        tableFrame.Controls.Add(modList);
        layout.Controls.Add(tableFrame, 0, 4);

        status = new Label {
            Name = "ServerModsStatus", ForeColor = CyberpunkTheme.Muted, BackColor = CyberpunkTheme.Surface,
            Dock = DockStyle.Fill, Padding = new Padding(10, 4, 10, 4), Margin = new Padding(0, 8, 0, 0),
            TextAlign = ContentAlignment.MiddleLeft
        };
        layout.Controls.Add(status, 0, 5);
    }

    private static void FitPackageColumn(object sender, EventArgs e)
    {
        var list = (ListView)sender;
        int leadingColumns = list.Columns[0].Width + list.Columns[1].Width + list.Columns[2].Width;
        int width = Math.Max(205, list.ClientSize.Width - leadingColumns - 1);
        if (list.Columns[3].Width != width) list.Columns[3].Width = width;
    }

    private static void DrawColumnHeader(object sender, DrawListViewColumnHeaderEventArgs e)
    {
        using (var background = new SolidBrush(CyberpunkTheme.Surface))
            e.Graphics.FillRectangle(background, e.Bounds);
        using (var line = new Pen(CyberpunkTheme.Border))
        {
            e.Graphics.DrawLine(line, e.Bounds.Right - 1, e.Bounds.Top, e.Bounds.Right - 1, e.Bounds.Bottom - 1);
            e.Graphics.DrawLine(line, e.Bounds.Left, e.Bounds.Bottom - 1, e.Bounds.Right - 1, e.Bounds.Bottom - 1);
        }
        if (e.Bounds.Width > 16)
            TextRenderer.DrawText(e.Graphics, e.Header.Text, e.Font, Rectangle.Inflate(e.Bounds, -8, 0),
                CyberpunkTheme.Cyan, TableTextFlags);
    }

    private static void DrawCell(object sender, DrawListViewSubItemEventArgs e)
    {
        bool selected = e.Item.Selected;
        Color background = selected ? SelectedRow : (e.ItemIndex % 2 == 0 ? CyberpunkTheme.Input : CyberpunkTheme.Surface);
        using (var fill = new SolidBrush(background))
            e.Graphics.FillRectangle(fill, e.Bounds);

        if (selected && e.ColumnIndex == 0)
            using (var stripe = new SolidBrush(CyberpunkTheme.Cyan))
                e.Graphics.FillRectangle(stripe, e.Bounds.Left, e.Bounds.Top, 3, e.Bounds.Height);
        if (e.Bounds.Width <= 16) return;

        Color ink = e.ColumnIndex == 0 ? CyberpunkTheme.Ink : CyberpunkTheme.Muted;
        if (e.ColumnIndex == 1)
        {
            if (e.SubItem.Text == "Active (logged)") ink = CyberpunkTheme.Cyan;
            else if (e.SubItem.Text == "Manifest unavailable" || e.SubItem.Text == "Disabled (logged)") ink = CyberpunkTheme.Warning;
        }
        TextRenderer.DrawText(e.Graphics, e.SubItem.Text, e.Item.Font, Rectangle.Inflate(e.Bounds, -8, 0), ink, TableTextFlags);
        if (e.ColumnIndex == 0 && e.Item.Focused && ((ListView)sender).Focused)
            ControlPaint.DrawFocusRectangle(e.Graphics, Rectangle.Inflate(e.Bounds, -4, -2), CyberpunkTheme.Cyan, background);
    }

    internal void RefreshFromDisk(bool running)
    {
        this.running = running;
        var packages = new List<Package>();
        var log = new ServerLog();
        string scanError = null;
        try
        {
            if (Directory.Exists(modsPath))
                foreach (string path in Directory.GetFileSystemEntries(modsPath).OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase))
                {
                    var attributes = File.GetAttributes(path);
                    if ((attributes & FileAttributes.ReparsePoint) != 0) continue;
                    bool folder = (attributes & FileAttributes.Directory) != 0;
                    string extension = Path.GetExtension(path);
                    if (folder ? File.Exists(Path.Combine(path, "manifest.json")) :
                        extension.Equals(".jar", StringComparison.OrdinalIgnoreCase) || extension.Equals(".zip", StringComparison.OrdinalIgnoreCase))
                        packages.Add(ReadPackage(path, folder, extension));
                }
        }
        catch (IOException) { scanError = "The server mods folder could not be fully read."; }
        catch (UnauthorizedAccessException) { scanError = "The server mods folder could not be fully read."; }

        try { ReadLatestLog(logsPath, log); }
        catch (IOException) { scanError = "The latest server log could not be read."; log = new ServerLog(); }
        catch (UnauthorizedAccessException) { scanError = "The latest server log could not be read."; log = new ServerLog(); }

        string loadedStatus = running && !log.Stopped ? "Active (logged)" : "Last loaded";
        var jarCounts = packages.Where(package => package.IsJar && package.Id != null).GroupBy(package => package.Id)
            .ToDictionary(group => group.Key, group => group.Count());
        var represented = new HashSet<string>(StringComparer.Ordinal);
        modList.BeginUpdate();
        try
        {
            modList.Items.Clear();
            foreach (var package in packages)
            {
                LogMod observation;
                string state = package.Id == null ? "Manifest unavailable" : "Installed only";
                if (log.Booted && package.Id != null && log.Mods.TryGetValue(package.Id, out observation))
                {
                    bool packLoaded = observation.PackLoaded && MatchesPackage(observation.PackFile, package.File);
                    bool pluginLoaded = package.IsJar && !observation.BuiltIn && observation.PluginEnabled &&
                        (observation.PluginFile != null ? MatchesPackage(observation.PluginFile, package.File) :
                            jarCounts[package.Id] == 1 && !package.Id.StartsWith("Hytale:", StringComparison.OrdinalIgnoreCase));
                    if (packLoaded || pluginLoaded)
                    {
                        state = loadedStatus;
                        represented.Add(package.Id);
                    }
                    else if (observation.Disabled && !observation.IsLoaded) state = "Disabled (logged)";
                }
                AddRow(package.Id ?? package.File, state, package.Version, package.File);
            }
            if (log.Booted)
                foreach (var entry in log.Mods.OrderBy(mod => mod.Key, StringComparer.OrdinalIgnoreCase))
                    if (entry.Value.IsLoaded && (entry.Value.PackFile != null || entry.Value.PluginFile != null) && !represented.Contains(entry.Key))
                        AddRow(entry.Key, loadedStatus, "", entry.Value.PackFile ?? entry.Value.PluginFile);
        }
        finally { modList.EndUpdate(); }

        string summary = modList.Items.Count == 0 ? "No third-party server mods found." : "Only third-party server mods are listed.";
        string source = log.Booted ? "Load status comes from the latest server log. Use /plugin manage in game to confirm live plugin changes." :
            "Load status appears after the server finishes starting.";
        status.Text = scanError ?? (summary + Environment.NewLine + source);
    }

    private void AddRow(string id, string state, string version, string file)
    {
        modList.Items.Add(new ListViewItem(new[] { id, state, version ?? "", file }));
    }

    private static Button ActionButton(string name, string text, int width, Action action, bool primary = false)
    {
        var button = new Button {
            Name = name, Text = text, Width = width, Height = 34, Margin = new Padding(0, 2, 8, 2)
        };
        CyberpunkTheme.StyleButton(button, primary);
        button.Click += (sender, args) => action();
        return button;
    }

    private void OpenFolder(string path)
    {
        if (!Directory.Exists(path))
        {
            status.Text = "This mods folder has not been created yet.";
            return;
        }
        try { Process.Start(new ProcessStartInfo(path) { UseShellExecute = true }); }
        catch (System.ComponentModel.Win32Exception) { status.Text = "Windows could not open the mods folder."; }
    }

    private static Package ReadPackage(string path, bool folder, string extension)
    {
        var package = new Package { File = Path.GetFileName(path), IsJar = !folder && extension.Equals(".jar", StringComparison.OrdinalIgnoreCase) };
        try
        {
            if (folder)
            {
                string manifestPath = Path.Combine(path, "manifest.json");
                if ((File.GetAttributes(manifestPath) & FileAttributes.ReparsePoint) == 0)
                    using (var stream = OpenReadShared(manifestPath))
                        if (stream.Length <= ManifestLimit) ReadManifest(stream, package);
            }
            else
                using (var stream = OpenReadShared(path))
                using (var archive = new ZipArchive(stream, ZipArchiveMode.Read))
                {
                    var manifest = archive.GetEntry("manifest.json");
                    if (manifest != null && manifest.Length <= ManifestLimit)
                        using (var contents = manifest.Open()) ReadManifest(contents, package);
                }
        }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
        catch (InvalidDataException) { }
        catch (ArgumentException) { }
        catch (InvalidOperationException) { }
        catch (NotSupportedException) { }
        return package;
    }

    private static void ReadManifest(Stream stream, Package package)
    {
        using (var reader = new StreamReader(stream))
        {
            var buffer = new char[ManifestLimit + 1];
            int length = reader.ReadBlock(buffer, 0, buffer.Length);
            if (length > ManifestLimit) return;
            var data = new JavaScriptSerializer { MaxJsonLength = ManifestLimit, RecursionLimit = 32 }
                .DeserializeObject(new string(buffer, 0, length)) as Dictionary<string, object>;
            if (data == null) return;
            string group = TextField(data, "Group");
            string name = TextField(data, "Name");
            if (!IsIdPart(group) || !IsIdPart(name)) return;
            package.Id = group + ":" + name;
            string version = TextField(data, "Version");
            if (version != null && version.Length <= 100 && !version.Any(Char.IsControl)) package.Version = version;
        }
    }

    private static string TextField(Dictionary<string, object> data, string key)
    {
        object value;
        return data.TryGetValue(key, out value) ? value as string : null;
    }

    private static bool IsIdPart(string part)
    {
        return !String.IsNullOrWhiteSpace(part) && part.Length <= 120 && part.IndexOf(':') < 0 && !part.Any(Char.IsControl);
    }

    private static bool MatchesPackage(string reported, string installed)
    {
        return reported == null || String.Equals(reported, installed, StringComparison.OrdinalIgnoreCase);
    }

    private static FileStream OpenReadShared(string path)
    {
        return new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
    }

    private static void ReadLatestLog(string path, ServerLog log)
    {
        if (!Directory.Exists(path)) return;
        string latest = Directory.EnumerateFiles(path, "*_server.log").Where(file => LogName.IsMatch(Path.GetFileName(file)))
            .OrderByDescending(Path.GetFileName, StringComparer.Ordinal).FirstOrDefault();
        if (latest == null) return;
        const string loadedPack = "Loaded pack: ";
        const string skippedPack = "Skipped disabled pack: ";
        using (var reader = new StreamReader(OpenReadShared(latest)))
        {
            string line;
            while ((line = reader.ReadLine()) != null)
            {
                var entry = LogLine.Match(line);
                if (!entry.Success) continue;
                string logger = entry.Groups[1].Value;
                string message = entry.Groups[2].Value;
                if (logger == "HytaleServer")
                {
                    if (message.StartsWith("Hytale Server Booted! [Multiplayer]", StringComparison.Ordinal)) log.Booted = true;
                    if (message.IndexOf("Shutdown complete", StringComparison.OrdinalIgnoreCase) >= 0) log.Stopped = true;
                }
                else if (logger == "PluginManager") ReadPluginLine(log, message);
                else if (message.StartsWith(loadedPack, StringComparison.Ordinal))
                {
                    string id;
                    string file;
                    if (SplitOrigin(message.Substring(loadedPack.Length), " from ", out id, out file) && !(id == "Hytale:Hytale" && file == "Assets.zip"))
                    {
                        var mod = log.GetMod(id);
                        mod.PackFile = file;
                        mod.PackLoaded = true;
                    }
                }
                else if (message.StartsWith(skippedPack, StringComparison.Ordinal))
                {
                    string id = message.Substring(skippedPack.Length);
                    if (IsId(id)) log.GetMod(id).Disabled = true;
                }
            }
        }
    }

    private static void ReadPluginLine(ServerLog log, string message)
    {
        const string enabled = "Enabled plugin ";
        const string skipped = "Skipping mod ";
        const string disabledReason = " (Disabled by server config)";
        if (message.StartsWith("- ", StringComparison.Ordinal))
        {
            string value = message.Substring(2);
            string id;
            string file;
            if (SplitOrigin(value, " from path ", out id, out file)) log.GetMod(id).PluginFile = file;
            else if (IsId(value)) log.GetMod(value).BuiltIn = true;
        }
        else if (message.StartsWith(enabled, StringComparison.Ordinal))
        {
            string id = message.Substring(enabled.Length);
            if (IsId(id)) log.GetMod(id).PluginEnabled = true;
        }
        else if (message.StartsWith(skipped, StringComparison.Ordinal) && message.EndsWith(disabledReason, StringComparison.Ordinal))
        {
            string id = message.Substring(skipped.Length, message.Length - skipped.Length - disabledReason.Length);
            if (IsId(id)) log.GetMod(id).Disabled = true;
        }
    }

    private static bool SplitOrigin(string value, string delimiter, out string id, out string file)
    {
        id = null;
        file = null;
        int split = value.IndexOf(delimiter, StringComparison.Ordinal);
        if (split < 0) return false;
        id = value.Substring(0, split);
        string name = value.Substring(split + delimiter.Length);
        if (!IsId(id) || String.IsNullOrWhiteSpace(name) || name.Any(Char.IsControl)) return false;
        int slash = name.LastIndexOfAny(new[] { '/', '\\' });
        file = name.Substring(slash + 1);
        return file.Length > 0;
    }

    private static bool IsId(string id)
    {
        int separator = id.IndexOf(':');
        return separator > 0 && IsIdPart(id.Substring(0, separator)) && IsIdPart(id.Substring(separator + 1));
    }

    private sealed class Package
    {
        internal string Id, Version, File;
        internal bool IsJar;
    }

    private sealed class LogMod
    {
        internal string PluginFile, PackFile;
        internal bool BuiltIn, PluginEnabled, PackLoaded, Disabled;
        internal bool IsLoaded { get { return PackLoaded || (!BuiltIn && PluginEnabled); } }
    }

    private sealed class ServerLog
    {
        internal readonly Dictionary<string, LogMod> Mods = new Dictionary<string, LogMod>(StringComparer.Ordinal);
        internal bool Booted, Stopped;

        internal LogMod GetMod(string id)
        {
            LogMod mod;
            if (!Mods.TryGetValue(id, out mod)) Mods.Add(id, mod = new LogMod());
            return mod;
        }
    }
}
