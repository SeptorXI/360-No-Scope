using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal sealed class ServerSettingsPage : UserControl
{
    private static readonly string[] WorldKeys = { "IsPvpEnabled", "IsFallDamageEnabled", "IsSpawningNPC", "IsGameTimePaused" };
    private static readonly bool[] WorldDefaults = { false, true, true, false };

    private readonly string serverRoot;
    private readonly string serverDirectory;
    private readonly string worldDirectory;
    private readonly Func<bool> canSave;
    private readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = Int32.MaxValue };
    private readonly TextBox serverName = TextField("ServerNameSetting", "Server name");
    private readonly TextBox motd = TextField("MotdSetting", "Message of the day");
    private readonly NumericUpDown maxPlayers = NumberField("MaxPlayersSetting", "Maximum players", 0, Int32.MaxValue);
    private readonly NumericUpDown viewDistance = NumberField("ViewDistanceSetting", "View distance in chunks", 1, 32);
    private readonly ComboBox defaultWorld = WorldPicker("DefaultWorldSetting", "Default world");
    private readonly ComboBox gameMode = WorldPicker("DefaultGameModeSetting", "Default game mode");
    private readonly ComboBox world = WorldPicker("WorldSetting", "World to edit");
    private readonly CheckBox[] worldFlags = {
        CheckField("PvpSetting", "Player vs. player combat"), CheckField("FallDamageSetting", "Fall damage"),
        CheckField("NpcSpawningSetting", "NPC spawning"), CheckField("PauseTimeSetting", "Pause the day and night cycle")
    };
    private readonly Label status = new Label {
        Dock = DockStyle.Fill, ForeColor = CyberpunkTheme.Muted, TextAlign = ContentAlignment.MiddleLeft,
        Padding = new Padding(10, 0, 0, 0)
    };
    private readonly Label serverMessage = MessageLabel();
    private readonly Label worldMessage = MessageLabel();
    private readonly Button saveServer = ActionButton("Save server settings", "SaveServerSettings", true);
    private readonly Button saveWorld = ActionButton("Save world settings", "SaveWorldSettings", true);
    private Snapshot savedServer;
    private Snapshot savedWorld;
    private string loadedWorld;
    private bool loading;
    private bool running;

    internal ServerSettingsPage(string serverRoot, Func<bool> canSave)
    {
        this.serverRoot = Path.GetFullPath(serverRoot).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        this.canSave = canSave;
        serverDirectory = Path.Combine(this.serverRoot, "Server");
        worldDirectory = Path.Combine(serverDirectory, "universe", "worlds");
        BackColor = CyberpunkTheme.Background;
        ForeColor = CyberpunkTheme.Ink;
        Font = CyberpunkTheme.BodyFont();
        Dock = DockStyle.Fill;

        var scroll = new Panel { Dock = DockStyle.Fill, AutoScroll = true };
        var layout = new TableLayoutPanel {
            Dock = DockStyle.Top, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink,
            ColumnCount = 2, RowCount = 3, Padding = new Padding(10, 6, 10, 8)
        };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        scroll.Controls.Add(layout);
        Controls.Add(scroll);

        var title = new Label {
            Text = "Server & world settings", UseMnemonic = false, Font = CyberpunkTheme.HeadingFont(16),
            AutoSize = true, ForeColor = CyberpunkTheme.Ink, Margin = new Padding(4, 0, 4, 8)
        };
        layout.Controls.Add(title, 0, 0);
        layout.SetColumnSpan(title, 2);

        var toolbar = new TableLayoutPanel {
            Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 2, Margin = new Padding(4, 0, 4, 8),
            Padding = new Padding(0, 2, 4, 2), BackColor = CyberpunkTheme.Surface
        };
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        var reload = ActionButton("Reload from disk", "ReloadServerSettings");
        toolbar.Controls.Add(status, 0, 0);
        toolbar.Controls.Add(reload, 1, 0);
        layout.Controls.Add(toolbar, 0, 1);
        layout.SetColumnSpan(toolbar, 2);

        var serverCard = AddCard(layout, 0, "Server settings", CyberpunkTheme.Accent);
        motd.Multiline = true;
        motd.AcceptsReturn = true;
        motd.ScrollBars = ScrollBars.Vertical;
        motd.MinimumSize = new Size(0, 50);
        AddField(serverCard, "Server name", serverName, 0);
        AddField(serverCard, "Message of the day", motd, 1);
        AddField(serverCard, "Maximum players", maxPlayers, 2);
        AddField(serverCard, "View distance (chunks)", viewDistance, 3);
        AddField(serverCard, "Default world", defaultWorld, 4);
        AddField(serverCard, "Default game mode", gameMode, 5);
        AddWide(serverCard, saveServer, 6);
        AddWide(serverCard, serverMessage, 7);

        var worldCard = AddCard(layout, 1, "World settings", CyberpunkTheme.Cyan);
        AddField(worldCard, "World to edit", world, 0);
        for (int i = 0; i < worldFlags.Length; i++) AddWide(worldCard, worldFlags[i], i + 1);
        AddWide(worldCard, saveWorld, 5);
        AddWide(worldCard, worldMessage, 6);

        serverName.TextChanged += (sender, args) => UpdateControls();
        motd.TextChanged += (sender, args) => UpdateControls();
        maxPlayers.TextChanged += (sender, args) => UpdateControls();
        viewDistance.TextChanged += (sender, args) => UpdateControls();
        maxPlayers.ValueChanged += (sender, args) => UpdateControls();
        viewDistance.ValueChanged += (sender, args) => UpdateControls();
        defaultWorld.SelectedIndexChanged += (sender, args) => UpdateControls();
        gameMode.SelectedIndexChanged += (sender, args) => UpdateControls();
        foreach (var flag in worldFlags) flag.CheckedChanged += (sender, args) => UpdateControls();
        world.SelectedIndexChanged += (sender, args) => SwitchWorld();
        saveServer.Click += (sender, args) => Save(false);
        saveWorld.Click += (sender, args) => Save(true);
        reload.Click += (sender, args) => {
            if (HasUnsavedChanges && !ConfirmDiscard()) return;
            LoadSettings(true);
        };
        UpdateControls();
    }

    internal bool HasUnsavedChanges { get { return ServerChanged() || WorldChanged(); } }

    internal void RefreshFromDisk()
    {
        LoadSettings(false);
    }

    internal void SetServerRunning(bool value)
    {
        if (running == value) return;
        running = value;
        if (!running && Visible) RefreshFromDisk();
        UpdateControls();
    }

    private static TextBox TextField(string name, string accessibleName)
    {
        return new TextBox {
            Name = name, AccessibleName = accessibleName, BackColor = CyberpunkTheme.Input,
            ForeColor = CyberpunkTheme.Ink, BorderStyle = BorderStyle.FixedSingle, Dock = DockStyle.Fill,
            Margin = new Padding(3, 4, 3, 4)
        };
    }

    private static NumericUpDown NumberField(string name, string accessibleName, int min, int max)
    {
        return new NumericUpDown {
            Name = name, AccessibleName = accessibleName, Minimum = min, Maximum = max,
            BackColor = CyberpunkTheme.Input, ForeColor = CyberpunkTheme.Ink, BorderStyle = BorderStyle.FixedSingle,
            Dock = DockStyle.Fill, Margin = new Padding(3, 4, 3, 4)
        };
    }

    private static ComboBox WorldPicker(string name, string accessibleName)
    {
        var picker = new ComboBox {
            Name = name, AccessibleName = accessibleName, DropDownStyle = ComboBoxStyle.DropDownList,
            BackColor = CyberpunkTheme.Input, ForeColor = CyberpunkTheme.Ink, Dock = DockStyle.Fill,
            FlatStyle = FlatStyle.Flat, DrawMode = DrawMode.OwnerDrawFixed, Margin = new Padding(3, 4, 3, 4)
        };
        picker.DrawItem += (sender, args) => {
            bool selected = (args.State & DrawItemState.Selected) != 0 && (args.State & DrawItemState.ComboBoxEdit) == 0;
            using (var fill = new SolidBrush(selected ? CyberpunkTheme.RedSurface : CyberpunkTheme.Input))
                args.Graphics.FillRectangle(fill, args.Bounds);
            if (args.Index < 0) return;
            Color color = picker.Enabled ? CyberpunkTheme.Ink : CyberpunkTheme.Muted;
            TextRenderer.DrawText(args.Graphics, picker.GetItemText(picker.Items[args.Index]), picker.Font,
                Rectangle.Inflate(args.Bounds, -3, 0), color, TextFormatFlags.VerticalCenter | TextFormatFlags.SingleLine |
                TextFormatFlags.EndEllipsis | TextFormatFlags.NoPrefix);
            args.DrawFocusRectangle();
        };
        return picker;
    }

    private static CheckBox CheckField(string name, string label)
    {
        var check = new CheckBox {
            Name = name, Text = label, AutoSize = true, ForeColor = CyberpunkTheme.Ink,
            FlatStyle = FlatStyle.Flat, Margin = new Padding(3, 7, 3, 7)
        };
        check.FlatAppearance.BorderColor = CyberpunkTheme.Cyan;
        check.FlatAppearance.CheckedBackColor = CyberpunkTheme.Cyan;
        return check;
    }

    private static Label MessageLabel()
    {
        return new Label {
            Dock = DockStyle.Fill, MinimumSize = new Size(0, 54), ForeColor = CyberpunkTheme.Muted,
            TextAlign = ContentAlignment.TopLeft, Margin = new Padding(3, 6, 3, 0)
        };
    }

    private static Button ActionButton(string caption, string name, bool primary = false)
    {
        var button = new Button {
            Name = name, Text = caption, AutoSize = true, MinimumSize = new Size(145, 34), Anchor = AnchorStyles.Left,
            Margin = new Padding(3, 6, 3, 3), Padding = new Padding(6, 0, 6, 0)
        };
        CyberpunkTheme.StyleButton(button, primary);
        return button;
    }

    private static TableLayoutPanel AddCard(TableLayoutPanel layout, int column, string caption, Color accent)
    {
        var group = new TableLayoutPanel {
            AccessibleRole = AccessibleRole.Grouping, AccessibleName = caption,
            Dock = DockStyle.Fill, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink,
            Padding = new Padding(13, 12, 13, 12), Margin = new Padding(4), BackColor = CyberpunkTheme.Surface,
            ColumnCount = 1, RowCount = 2
        };
        group.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        group.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        group.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        group.Paint += (sender, args) => {
            int right = group.ClientSize.Width - 1;
            int bottom = group.ClientSize.Height - 1;
            const int cut = 12;
            if (right <= cut || bottom <= cut) return;
            var bevel = new[] { new Point(right - cut, 0), new Point(right, 0), new Point(right, cut) };
            using (var corner = new SolidBrush(CyberpunkTheme.Background)) args.Graphics.FillPolygon(corner, bevel);
            using (var border = new Pen(CyberpunkTheme.Border)) args.Graphics.DrawLines(border, new[] {
                new Point(0, 0), bevel[0], bevel[2], new Point(right, bottom), new Point(0, bottom), new Point(0, 0)
            });
            using (var rail = new SolidBrush(accent)) args.Graphics.FillRectangle(rail, 0, 0, 3, 33);
        };
        group.SizeChanged += (sender, args) => group.Invalidate();
        var header = new Label {
            Text = caption, AutoSize = true, Font = CyberpunkTheme.HeadingFont(12),
            ForeColor = accent, Margin = new Padding(3, 0, 3, 8)
        };
        group.Controls.Add(header, 0, 0);
        var card = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 2 };
        card.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        card.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        group.Controls.Add(card, 0, 1);
        layout.Controls.Add(group, column, 2);
        return card;
    }

    private static void AddField(TableLayoutPanel card, string caption, Control input, int row)
    {
        var label = new Label {
            Text = caption, AutoSize = true, Anchor = AnchorStyles.Left, ForeColor = CyberpunkTheme.Ink,
            Margin = new Padding(3, 5, 8, 5)
        };
        card.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        card.Controls.Add(label, 0, row);
        card.Controls.Add(input, 1, row);
    }

    private static void AddWide(TableLayoutPanel card, Control control, int row)
    {
        card.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        card.Controls.Add(control, 0, row);
        card.SetColumnSpan(control, 2);
    }

    private void LoadSettings(bool discard)
    {
        bool loadServer = discard || !ServerChanged();
        bool loadWorld = discard || !WorldChanged();
        if (!loadServer && !loadWorld) return;

        loading = true;
        try
        {
            if (loadServer)
            {
                savedServer = null;
                try
                {
                    var snapshot = ReadConfig(Path.Combine(serverDirectory, "config.json"));
                    serverName.Text = ReadValue(snapshot.Values, "ServerName", "Hytale Server");
                    motd.Text = ReadValue(snapshot.Values, "MOTD", "");
                    LoadNumber(maxPlayers, ReadValue(snapshot.Values, "MaxPlayers", 100), 0, Int32.MaxValue);
                    LoadNumber(viewDistance, ReadValue(snapshot.Values, "MaxViewRadius", 32), 1, 32);
                    string currentDefault = DefaultWorld(snapshot);
                    FillWorlds(defaultWorld);
                    SelectCurrent(defaultWorld, currentDefault);
                    gameMode.Items.Clear();
                    gameMode.Items.AddRange(new object[] { "Adventure", "Creative" });
                    SelectCurrent(gameMode, ReadDefault(snapshot, "GameMode", "Adventure"));
                    savedServer = snapshot;
                    Feedback(serverMessage, "Changes apply the next time the server starts.", CyberpunkTheme.Muted);
                }
                catch (Exception error)
                {
                    if (!IsConfigError(error)) throw;
                    Feedback(serverMessage, "Cannot load server settings. " + error.Message, CyberpunkTheme.Warning);
                }
            }

            if (loadWorld)
            {
                savedWorld = null;
                try
                {
                    string previous = loadedWorld;
                    FillWorlds(world);
                    string preferred = savedServer == null ? "default" : DefaultWorld(savedServer);
                    if (previous != null && world.FindStringExact(previous) >= 0) world.SelectedIndex = world.FindStringExact(previous);
                    else if (world.FindStringExact(preferred) >= 0) world.SelectedIndex = world.FindStringExact(preferred);
                    else if (world.Items.Count > 0) world.SelectedIndex = 0;
                    LoadSelectedWorld();
                }
                catch (Exception error)
                {
                    if (!IsConfigError(error)) throw;
                    Feedback(worldMessage, "Cannot load world settings. " + error.Message, CyberpunkTheme.Warning);
                }
            }
        }
        finally
        {
            loading = false;
            UpdateControls();
        }
    }

    private void FillWorlds(ComboBox picker)
    {
        picker.Items.Clear();
        if (!Directory.Exists(worldDirectory)) return;
        EnsureLocalPath(worldDirectory);
        var worlds = new List<string>();
        foreach (string folder in Directory.GetDirectories(worldDirectory))
        {
            string file = Path.Combine(folder, "config.json");
            if (!IsLink(folder) && File.Exists(file) && !IsLink(file)) worlds.Add(Path.GetFileName(folder));
        }
        worlds.Sort(StringComparer.OrdinalIgnoreCase);
        picker.Items.AddRange(worlds.ToArray());
    }

    private static void SelectCurrent(ComboBox picker, string current)
    {
        int index = picker.FindStringExact(current);
        picker.SelectedIndex = index >= 0 ? index : picker.Items.Add(current);
    }

    private void SwitchWorld()
    {
        if (loading) return;
        loading = true;
        try
        {
            if (WorldChanged() && !ConfirmDiscard())
            {
                world.SelectedItem = loadedWorld;
                return;
            }
            LoadSelectedWorld();
        }
        finally
        {
            loading = false;
            UpdateControls();
        }
    }

    private void LoadSelectedWorld()
    {
        loadedWorld = world.SelectedItem as string;
        savedWorld = null;
        if (loadedWorld == null)
        {
            Feedback(worldMessage, "No saved worlds were found.", CyberpunkTheme.Muted);
            return;
        }
        try
        {
            var snapshot = ReadConfig(WorldPath(loadedWorld));
            for (int i = 0; i < worldFlags.Length; i++)
                worldFlags[i].Checked = ReadValue(snapshot.Values, WorldKeys[i], WorldDefaults[i]);
            savedWorld = snapshot;
            Feedback(worldMessage, "These changes apply only to the selected world.", CyberpunkTheme.Muted);
        }
        catch (Exception error)
        {
            if (!IsConfigError(error)) throw;
            Feedback(worldMessage, "Cannot load this world. " + error.Message, CyberpunkTheme.Warning);
        }
    }

    private bool ConfirmDiscard()
    {
        return MessageBox.Show(this, "Discard the unsaved settings?", "Hytale Server Panel",
            MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) == DialogResult.Yes;
    }

    private static string DefaultWorld(Snapshot snapshot)
    {
        return ReadDefault(snapshot, "World", "default");
    }

    private static string ReadDefault(Snapshot snapshot, string key, string fallback)
    {
        var defaults = ReadValue<Dictionary<string, object>>(snapshot.Values, "Defaults", null);
        return defaults == null ? fallback : ReadValue(defaults, key, fallback);
    }

    private bool ServerChanged()
    {
        if (savedServer == null) return false;
        var data = savedServer.Values;
        return serverName.Text != ReadValue(data, "ServerName", "Hytale Server") || motd.Text != ReadValue(data, "MOTD", "") ||
            NumberChanged(maxPlayers, ReadValue(data, "MaxPlayers", 100)) || NumberChanged(viewDistance, ReadValue(data, "MaxViewRadius", 32)) ||
            !String.Equals(defaultWorld.SelectedItem as string, DefaultWorld(savedServer), StringComparison.OrdinalIgnoreCase) ||
            !String.Equals(gameMode.SelectedItem as string, ReadDefault(savedServer, "GameMode", "Adventure"), StringComparison.OrdinalIgnoreCase);
    }

    private bool WorldChanged()
    {
        if (savedWorld == null) return false;
        for (int i = 0; i < worldFlags.Length; i++)
            if (worldFlags[i].Checked != ReadValue(savedWorld.Values, WorldKeys[i], WorldDefaults[i])) return true;
        return false;
    }

    private static bool NumberChanged(NumericUpDown control, int original)
    {
        int entered;
        return !Int32.TryParse(control.Text, NumberStyles.Integer, CultureInfo.CurrentCulture, out entered) || entered != original;
    }

    private void UpdateControls()
    {
        if (loading) return;
        status.Text = running ? "Stop the server to save settings." : "Server is stopped. Save changes before starting it again.";
        status.ForeColor = running ? CyberpunkTheme.Warning : CyberpunkTheme.Muted;
        bool serverEditable = !running && savedServer != null;
        serverName.ReadOnly = motd.ReadOnly = !serverEditable;
        maxPlayers.Enabled = viewDistance.Enabled = defaultWorld.Enabled = gameMode.Enabled = serverEditable;
        foreach (var flag in worldFlags) flag.Enabled = !running && savedWorld != null;
        saveServer.Enabled = serverEditable && ServerChanged();
        saveWorld.Enabled = !running && WorldChanged();
    }

    private void Save(bool isWorld)
    {
        var snapshot = isWorld ? savedWorld : savedServer;
        var message = isWorld ? worldMessage : serverMessage;
        if (snapshot == null) return;
        try
        {
            if (running || !canSave()) throw new InvalidOperationException("Stop the server before saving settings.");
            var changes = new Dictionary<string, object>();
            if (isWorld)
            {
                for (int i = 0; i < worldFlags.Length; i++)
                    SetChanged(changes, snapshot.Values, WorldKeys[i], worldFlags[i].Checked, WorldDefaults[i]);
            }
            else
            {
                if (String.IsNullOrWhiteSpace(serverName.Text) && serverName.Text != ReadValue(snapshot.Values, "ServerName", "Hytale Server"))
                    throw new InvalidOperationException("Enter a server name.");
                SetChanged(changes, snapshot.Values, "ServerName", serverName.Text, "Hytale Server");
                SetChanged(changes, snapshot.Values, "MOTD", motd.Text, "");
                SetNumber(changes, snapshot.Values, "MaxPlayers", maxPlayers, 100, 0, Int32.MaxValue);
                SetNumber(changes, snapshot.Values, "MaxViewRadius", viewDistance, 32, 1, 32);
                string selection = defaultWorld.SelectedItem as string;
                bool worldChanged = !String.Equals(selection, DefaultWorld(snapshot), StringComparison.OrdinalIgnoreCase);
                string mode = gameMode.SelectedItem as string;
                bool modeChanged = !String.Equals(mode, ReadDefault(snapshot, "GameMode", "Adventure"), StringComparison.OrdinalIgnoreCase);
                if (worldChanged || modeChanged)
                {
                    var previous = ReadValue<Dictionary<string, object>>(snapshot.Values, "Defaults", null);
                    var defaults = previous == null ? new Dictionary<string, object>() : new Dictionary<string, object>(previous);
                    if (worldChanged)
                    {
                        EnsureLocalPath(WorldPath(selection));
                        defaults["World"] = selection;
                    }
                    if (modeChanged) defaults["GameMode"] = mode;
                    changes["Defaults"] = defaults;
                }
            }
            if (changes.Count == 0) return;

            var updated = new Dictionary<string, object>(snapshot.Values);
            foreach (var item in changes) updated[item.Key] = item.Value;
            string output = FormatJson(json.Serialize(updated));
            ReplaceConfig(snapshot, output);
            var refreshed = new Snapshot(snapshot.Path, output, updated);
            if (isWorld) savedWorld = refreshed;
            else savedServer = refreshed;
            Feedback(message, "Saved. A backup of the previous settings was kept.", CyberpunkTheme.Cyan);
        }
        catch (Exception error)
        {
            if (!IsConfigError(error)) throw;
            Feedback(message, error.Message, CyberpunkTheme.Warning);
        }
        finally { UpdateControls(); }
    }

    private static void SetChanged<T>(Dictionary<string, object> changes, Dictionary<string, object> original, string key, T value, T fallback)
    {
        if (!EqualityComparer<T>.Default.Equals(ReadValue(original, key, fallback), value)) changes[key] = value;
    }

    private Snapshot ReadConfig(string path)
    {
        EnsureLocalPath(path);
        string contents = File.ReadAllText(path);
        var values = json.DeserializeObject(contents) as Dictionary<string, object>;
        if (values == null) throw new InvalidDataException("The configuration must be a JSON object.");
        return new Snapshot(path, contents, values);
    }

    private void ReplaceConfig(Snapshot original, string output)
    {
        string backup = original.Path + ".panel-backup";
        string temp = Path.Combine(Path.GetDirectoryName(original.Path), ".panel-" + Guid.NewGuid().ToString("N") + ".tmp");
        try
        {
            EnsureLocalPath(original.Path);
            using (var stream = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
            {
                writer.Write(output);
                writer.Flush();
                stream.Flush(true);
            }
            if (running || !canSave()) throw new InvalidOperationException("Stop the server before saving settings.");
            EnsureLocalPath(original.Path);
            if (File.Exists(backup)) EnsureLocalPath(backup);
            using (var stream = new FileStream(original.Path, FileMode.Open, FileAccess.Read, FileShare.Read | FileShare.Delete))
            using (var reader = new StreamReader(stream))
            {
                if (!String.Equals(reader.ReadToEnd(), original.Contents, StringComparison.Ordinal))
                    throw new InvalidOperationException("Settings changed on disk. Reload before saving.");
                File.Replace(temp, original.Path, backup);
            }
        }
        finally
        {
            try { File.Delete(temp); }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
    }

    private string WorldPath(string name)
    {
        if (String.IsNullOrEmpty(name) || name == "." || name == ".." || name.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
            throw new InvalidOperationException("Choose an existing world.");
        return Path.Combine(worldDirectory, name, "config.json");
    }

    private void EnsureLocalPath(string path)
    {
        path = Path.GetFullPath(path);
        string prefix = serverRoot + Path.DirectorySeparatorChar;
        if (!path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("The settings path is outside the server folder.");
        while (!String.Equals(path, serverRoot, StringComparison.OrdinalIgnoreCase))
        {
            if (IsLink(path)) throw new InvalidOperationException("The settings path contains a linked file or folder.");
            path = Path.GetDirectoryName(path);
        }
        if (IsLink(serverRoot)) throw new InvalidOperationException("The server folder is a link.");
    }

    private static bool IsLink(string path)
    {
        return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;
    }

    private static T ReadValue<T>(Dictionary<string, object> values, string key, T fallback)
    {
        object value;
        if (!values.TryGetValue(key, out value) || value == null) return fallback;
        if (value is T) return (T)value;
        throw new InvalidDataException(key + " has an unexpected value.");
    }

    private static void LoadNumber(NumericUpDown control, int value, int min, int max)
    {
        control.Minimum = Math.Min(min, value);
        control.Maximum = Math.Max(max, value);
        control.Value = value;
    }

    private static void SetNumber(Dictionary<string, object> changes, Dictionary<string, object> original,
        string key, NumericUpDown control, int fallback, int min, int max)
    {
        int value = (int)control.Value;
        if (value == ReadValue(original, key, fallback)) return;
        if (value < min || value > max)
            throw new InvalidOperationException(String.Format("{0} must be between {1} and {2}.", control.AccessibleName, min, max));
        changes[key] = value;
    }

    private static bool IsConfigError(Exception error)
    {
        return error is IOException || error is InvalidDataException || error is UnauthorizedAccessException ||
            error is ArgumentException || error is InvalidOperationException;
    }

    private static void Feedback(Label label, string message, Color color)
    {
        label.Text = message;
        label.ForeColor = color;
    }

    private static string FormatJson(string compact)
    {
        var result = new StringBuilder(compact.Length);
        int depth = 0;
        bool quoted = false;
        bool escaped = false;
        for (int i = 0; i < compact.Length; i++)
        {
            char value = compact[i];
            if (quoted)
            {
                result.Append(value);
                if (escaped) escaped = false;
                else if (value == '\\') escaped = true;
                else if (value == '"') quoted = false;
                continue;
            }
            switch (value)
            {
                case '"': quoted = true; result.Append(value); break;
                case '{':
                case '[':
                    result.Append(value);
                    depth++;
                    if (compact[i + 1] != '}' && compact[i + 1] != ']') result.Append('\n').Append(' ', depth * 2);
                    break;
                case '}':
                case ']':
                    depth--;
                    if (compact[i - 1] != '{' && compact[i - 1] != '[') result.Append('\n').Append(' ', depth * 2);
                    result.Append(value);
                    break;
                case ',': result.Append(",\n").Append(' ', depth * 2); break;
                case ':': result.Append(": "); break;
                default: result.Append(value); break;
            }
        }
        return result.Append('\n').ToString();
    }

    private sealed class Snapshot
    {
        internal readonly string Path;
        internal readonly string Contents;
        internal readonly Dictionary<string, object> Values;

        internal Snapshot(string path, string contents, Dictionary<string, object> values)
        {
            Path = path;
            Contents = contents;
            Values = values;
        }
    }
}
