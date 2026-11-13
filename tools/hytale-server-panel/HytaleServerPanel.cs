using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Management;
using System.Net.NetworkInformation;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

internal sealed class HytaleServerPanel : Form
{
    private const string LocalAddress = "localhost:5520";
    private const int ServerPort = 5520;
    private const int BacklogRefreshMs = 125;
    private const int VisibleRefreshMs = 250;
    private const int BackgroundRefreshMs = 1000;
    private const int RecentLogLimit = 105000;
    private static readonly Color Background = CyberpunkTheme.Background;
    private static readonly Color Ink = CyberpunkTheme.Ink;
    private static readonly Color Muted = CyberpunkTheme.Muted;
    private static readonly Color Warning = CyberpunkTheme.Warning;
    private static readonly Regex ConsoleColor = new Regex(@"\x1B\[[0-?]*[ -/]*[@-~]");
    private static readonly Regex ServerShutdown = new Regex(@"\[HytaleServer(?:\|[^\]]+)?\]\s+Shutdown completed?\b", RegexOptions.IgnoreCase);

    private readonly string serverRoot;
    private readonly BackgroundAppPriority backgroundPriority;
    private readonly Button start;
    private readonly Button stop;
    private readonly Button signIn;
    private readonly Button copyAddress;
    private readonly Button hostingMode;
    private readonly Button addFriend;
    private readonly TabControl tabs;
    private readonly TabPage settingsTab;
    private readonly TabPage modsTab;
    private readonly ServerSettingsPage settingsPage;
    private readonly ServerModsPage modsPage;
    private readonly TextBox friend;
    private readonly Label status;
    private readonly Label detail;
    private readonly Label friendFeedback;
    private readonly Label whitelistHeading;
    private readonly ListBox friendList;
    private readonly ServerWhitelist whitelist;
    private readonly RichTextBox log;
    private readonly System.Windows.Forms.Timer timer;
    private readonly NotifyIcon trayIcon;
    private readonly ToolStripMenuItem trayStop;
    private readonly StringBuilder hiddenLog = new StringBuilder();
    private ServerRun run;
    private bool ready;
    private bool closeAfterStop;
    private bool inTray;
    private bool hideWhenReady;
    private bool modsWereRunning;
    private bool modsPortWasBusy;
    private DateTime stopAt;
    private DateTime nextPortCheck;
    private DateTime nextFriendRefresh;
    private DateTime nextPriorityCheck;
    private DateTime copiedUntil;
    private string offlineDetail = "Start the server when you are ready to play.";

    [STAThread]
    private static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        using (var instance = new Mutex(false, @"Local\HytaleServerPanel"))
        {
            bool acquired;
            try { acquired = instance.WaitOne(0); }
            catch (AbandonedMutexException) { acquired = true; }
            if (!acquired)
            {
                MessageBox.Show("The server panel is already open. If it is minimized, look for its icon by the clock or under the ^ arrow.",
                    "Hytale Server Panel");
                return;
            }
            try
            {
                string settings = Path.Combine(Application.StartupPath, "PanelSettings");
                string server = args.Length > 0 ? Path.GetFullPath(args[0]) : Application.StartupPath;
                Application.Run(new HytaleServerPanel(server, settings));
            }
            finally { instance.ReleaseMutex(); }
        }
    }

    public HytaleServerPanel(string serverRoot, string settingsDirectory)
    {
        this.serverRoot = serverRoot;
        whitelist = new ServerWhitelist(serverRoot);
        backgroundPriority = new BackgroundAppPriority(settingsDirectory);
        Text = "Hytale Server Panel";
        Font = CyberpunkTheme.BodyFont();
        CyberpunkTheme.StyleWindow(this);
        MinimumSize = new Size(825, 635);
        ClientSize = new Size(960, 710);
        StartPosition = FormStartPosition.CenterScreen;
        AutoScaleMode = AutoScaleMode.Font;

        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(22, 15, 22, 18), ColumnCount = 1, RowCount = 3 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 83));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 126));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        Controls.Add(layout);

        var header = new CyberpunkBanner();
        header.Controls.Add(LabelAt("CONTROL INTERFACE  /  DEDICATED SERVER", 0, 6, 10, CyberpunkTheme.Red, true));
        header.Controls.Add(LabelAt("HYTALE SERVER PANEL", -2, 23, 30, CyberpunkTheme.Accent, true));
        var endpoint = new Panel { Dock = DockStyle.Right, Width = 175, BackColor = Color.Transparent };
        endpoint.Controls.Add(LabelAt("LOCAL CONNECTION  //  UDP", 8, 21, 9, Muted, true));
        endpoint.Controls.Add(LabelAt(LocalAddress, 7, 39, 14, CyberpunkTheme.Cyan, true));
        header.Controls.Add(endpoint);
        layout.Controls.Add(header, 0, 0);

        var serverCard = new CyberpunkCard(CyberpunkTheme.Red) { Margin = new Padding(0, 0, 0, 12) };
        serverCard.Controls.Add(LabelAt("SERVER STATUS", 16, 9, 9, CyberpunkTheme.Red, true));
        status = LabelAt("Stopped", 15, 24, 17, Muted, true);
        status.Name = "ServerStatus";
        detail = LabelAt(offlineDetail, 16, 50, 10, Muted);
        detail.AutoSize = false;
        detail.AutoEllipsis = true;
        detail.SetBounds(16, 50, serverCard.ClientSize.Width - 32, 20);
        detail.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        start = ButtonAt("Start server", "StartButton", 16, 72, 109, true);
        stop = ButtonAt("Stop server", "StopButton", 133, 72, 105);
        copyAddress = ButtonAt("Copy local address", "CopyAddressButton", 246, 72, 149);
        signIn = ButtonAt("Sign in to Hytale", "SignInButton", 403, 72, 139);
        hostingMode = ButtonAt("Hosting mode", "HostingModeButton", 550, 72, 125);
        serverCard.Controls.AddRange(new Control[] { status, detail, start, stop, copyAddress, signIn, hostingMode });
        layout.Controls.Add(serverCard, 0, 1);

        tabs = new CyberpunkTabs { Name = "MainTabs", Dock = DockStyle.Fill, Margin = Padding.Empty };
        var overview = new TabPage("Overview") { BackColor = Background, Padding = new Padding(0, 12, 0, 0) };
        settingsTab = new TabPage("Settings") { BackColor = Background };
        modsTab = new TabPage("Mods") { BackColor = Background };
        settingsPage = new ServerSettingsPage(serverRoot, CanSaveSettings) { Dock = DockStyle.Fill };
        modsPage = new ServerModsPage(serverRoot) { Dock = DockStyle.Fill };
        settingsTab.Controls.Add(settingsPage);
        modsTab.Controls.Add(modsPage);
        tabs.TabPages.AddRange(new[] { overview, settingsTab, modsTab });
        layout.Controls.Add(tabs, 0, 2);

        var overviewLayout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 1 };
        overviewLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 66));
        overviewLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 34));
        overviewLayout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        overview.Controls.Add(overviewLayout);

        var friendsCard = new CyberpunkCard(CyberpunkTheme.Red) { Margin = Padding.Empty };
        var accessLayout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 8, Padding = new Padding(15, 14, 15, 14), BackColor = Color.Transparent };
        foreach (int height in new[] { 19, 32, 22, 33, 40, 48, 24 })
            accessLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
        accessLayout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        accessLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        accessLayout.Controls.Add(LabelAt("ACCESS CONTROL", 0, 0, 9, CyberpunkTheme.Red, true), 0, 0);
        accessLayout.Controls.Add(LabelAt("Friend access", 0, 0, 17, Ink, true), 0, 1);
        accessLayout.Controls.Add(LabelAt("Hytale username", 0, 0, 10, Ink), 0, 2);
        friend = new TextBox {
            Name = "FriendName", AccessibleName = "Hytale username", Dock = DockStyle.Top, Margin = Padding.Empty,
            MaxLength = 32, Font = CyberpunkTheme.BodyFont(11),
            BackColor = CyberpunkTheme.Input, ForeColor = Ink, BorderStyle = BorderStyle.FixedSingle
        };
        addFriend = ButtonAt("Add friend", "AddFriendButton", 0, 0, 120);
        addFriend.Margin = Padding.Empty;
        friendFeedback = new Label {
            Text = "Enter a friend's Hytale username once the server is running.",
            ForeColor = Muted, Dock = DockStyle.Fill, Margin = Padding.Empty
        };
        whitelistHeading = LabelAt("Whitelisted friends", 0, 0, 10, CyberpunkTheme.Cyan, true);
        whitelistHeading.Name = "WhitelistHeading";
        friendList = new ListBox {
            Name = "WhitelistedFriends", AccessibleName = "Whitelisted friends", Dock = DockStyle.Fill, Margin = Padding.Empty,
            BackColor = CyberpunkTheme.Input, ForeColor = Ink, BorderStyle = BorderStyle.FixedSingle,
            IntegralHeight = false, HorizontalScrollbar = true
        };
        accessLayout.Controls.Add(friend, 0, 3);
        accessLayout.Controls.Add(addFriend, 0, 4);
        accessLayout.Controls.Add(friendFeedback, 0, 5);
        accessLayout.Controls.Add(whitelistHeading, 0, 6);
        accessLayout.Controls.Add(friendList, 0, 7);
        friendsCard.Controls.Add(accessLayout);
        overviewLayout.Controls.Add(friendsCard, 1, 0);

        var console = new CyberpunkCard(CyberpunkTheme.Cyan) { Margin = new Padding(0, 0, 11, 0) };
        var consoleLayout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(15, 14, 15, 15), RowCount = 3, ColumnCount = 1, BackColor = Color.Transparent };
        consoleLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        consoleLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, 19));
        consoleLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, 33));
        consoleLayout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        consoleLayout.Controls.Add(LabelAt("LIVE FEED", 0, 0, 9, CyberpunkTheme.Cyan, true), 0, 0);
        consoleLayout.Controls.Add(LabelAt("Server log", 0, 0, 17, Ink, true), 0, 1);
        log = new RichTextBox {
            Name = "ServerLog", AccessibleName = "Live server log", Dock = DockStyle.Fill,
            ReadOnly = true, WordWrap = false, DetectUrls = true, BorderStyle = BorderStyle.None,
            BackColor = CyberpunkTheme.Input, ForeColor = Ink, Font = new Font("Consolas", 10), Margin = Padding.Empty
        };
        consoleLayout.Controls.Add(log, 0, 2);
        console.Controls.Add(consoleLayout);
        overviewLayout.Controls.Add(console, 0, 0);

        start.Click += (sender, args) => StartServer();
        stop.Click += (sender, args) => RequestStop();
        signIn.Click += (sender, args) => {
            if (SendCommand("/auth login device"))
                WriteLog("[Panel] Follow the sign-in instructions in the log.");
        };
        log.LinkClicked += (sender, args) => OpenSignInLink(args.LinkText);
        addFriend.Click += (sender, args) => AddFriend();
        friend.KeyDown += (sender, args) => {
            if (args.KeyCode == Keys.Enter) { args.SuppressKeyPress = true; AddFriend(); }
        };
        copyAddress.Click += (sender, args) => CopyAddress();
        hostingMode.Click += (sender, args) => EditHostingMode();
        tabs.SelectedIndexChanged += (sender, args) => RefreshSelectedPage();

        var trayMenu = new ContextMenuStrip { BackColor = CyberpunkTheme.Surface, ForeColor = Ink, ShowImageMargin = false };
        trayMenu.Items.Add("Open Hytale Server Panel", null, (sender, args) => BeginInvoke(new Action(RestoreFromTray)));
        trayStop = new ToolStripMenuItem("Stop server", null, (sender, args) => RequestStop());
        trayMenu.Items.Add(trayStop);
        trayMenu.Items.Add(new ToolStripSeparator());
        trayMenu.Items.Add("Exit panel", null, (sender, args) => BeginInvoke(new Action(() => {
            RestoreFromTray();
            Close();
        })));
        trayIcon = new NotifyIcon { Icon = SystemIcons.Application, ContextMenuStrip = trayMenu, Text = Text };
        trayIcon.DoubleClick += (sender, args) => BeginInvoke(new Action(RestoreFromTray));

        timer = new System.Windows.Forms.Timer { Interval = BackgroundRefreshMs };
        timer.Tick += (sender, args) => RefreshServer();
        Resize += (sender, args) => {
            if (WindowState == FormWindowState.Minimized) MoveToTray();
        };
        FormClosing += ClosePanel;
        timer.Start();
        WriteLog("[Panel] Server folder: " + serverRoot);
        ShowOfflineStatus();
        RefreshFriends();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            if (timer != null) timer.Dispose();
            if (backgroundPriority != null) backgroundPriority.Dispose();
            if (trayIcon != null)
            {
                var trayMenu = trayIcon.ContextMenuStrip;
                trayIcon.Dispose();
                if (trayMenu != null) trayMenu.Dispose();
            }
        }
        base.Dispose(disposing);
    }

    private static Label LabelAt(string text, int x, int y, float size, Color color, bool heading = false)
    {
        return new Label {
            Text = text, Location = new Point(x, y), Font = heading ? CyberpunkTheme.HeadingFont(size) : CyberpunkTheme.BodyFont(size),
            ForeColor = color, AutoSize = true, Margin = Padding.Empty
        };
    }

    private static Button ButtonAt(string text, string name, int x, int y, int width, bool primary = false)
    {
        var button = new Button {
            Text = text, Name = name, Location = new Point(x, y), Size = new Size(width, 33),
            Font = CyberpunkTheme.BodyFont(10, FontStyle.Bold)
        };
        CyberpunkTheme.StyleButton(button, primary);
        return button;
    }

    private void EditHostingMode()
    {
        int[] groups = { BackgroundAppPriority.Steam, BackgroundAppPriority.Epic, BackgroundAppPriority.Razer,
            BackgroundAppPriority.Discord, BackgroundAppPriority.Browsers };
        string[] labels = { "Steam web helpers", "Epic Games web helpers", "Razer Cortex", "Discord", "Web browsers" };

        using (var dialog = new Form())
        {
            dialog.Text = "Hosting mode";
            dialog.Font = Font;
            CyberpunkTheme.StyleWindow(dialog);
            dialog.ClientSize = new Size(465, 329);
            dialog.StartPosition = FormStartPosition.CenterParent;
            dialog.FormBorderStyle = FormBorderStyle.FixedDialog;
            dialog.ShowInTaskbar = false;
            dialog.MaximizeBox = false;
            dialog.MinimizeBox = false;
            var description = new Label {
                Text = "Save energy in selected background apps while Hytale or your server runs. Their previous settings return afterward.",
                Location = new Point(16, 15), Size = new Size(432, 44)
            };
            var choices = new CheckedListBox {
                Name = "HostingApps", AccessibleName = "Apps to give lower CPU priority", Location = new Point(16, 65),
                Size = new Size(432, 128), IntegralHeight = false, CheckOnClick = true,
                BackColor = CyberpunkTheme.Input, ForeColor = Ink, BorderStyle = BorderStyle.FixedSingle
            };
            for (int index = 0; index < groups.Length; index++)
                choices.Items.Add(labels[index], (backgroundPriority.Selection & groups[index]) != 0);

            var hint = new Label {
                Text = "Uses Windows energy-saving controls and lower CPU priority. Discord voice stays outside this mode. Uncheck an app to restore it; clear all boxes to turn this off.",
                Location = new Point(16, 200), Size = new Size(432, 70), ForeColor = Muted
            };
            var save = new Button { Text = "Save", DialogResult = DialogResult.OK, Location = new Point(269, 283), Size = new Size(84, 30) };
            var cancel = new Button { Text = "Cancel", DialogResult = DialogResult.Cancel, Location = new Point(364, 283), Size = new Size(84, 30) };
            CyberpunkTheme.StyleButton(save, true);
            CyberpunkTheme.StyleButton(cancel);
            dialog.Controls.AddRange(new Control[] { description, choices, hint, save, cancel });
            dialog.AcceptButton = save;
            dialog.CancelButton = cancel;
            if (dialog.ShowDialog(this) != DialogResult.OK) return;

            int selection = 0;
            for (int index = 0; index < groups.Length; index++)
                if (choices.GetItemChecked(index)) selection |= groups[index];
            if (!backgroundPriority.SaveSelection(selection))
                MessageBox.Show(this, "Windows could not save the hosting preferences.", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            else
            {
                nextPriorityCheck = DateTime.MinValue;
                RefreshHostingMode(DateTime.UtcNow);
            }
        }
    }

    private void StartServer()
    {
        if (run != null) return;
        if (PortInUse() || HytaleProcessExists())
        {
            offlineDetail = "Close the other server or free UDP port 5520 before starting here.";
            WriteLog("[Panel] A Hytale process or a UDP 5520 listener is already active.");
            ShowOfflineStatus();
            return;
        }
        if (settingsPage.HasUnsavedChanges && MessageBox.Show(this,
            "Start the server with the last saved settings? Your edits are still open in Settings.", Text,
            MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;

        foreach (string file in new[] { "Run-Server.bat", @"Server\HytaleServer.jar", "Assets.zip" })
        {
            if (File.Exists(Path.Combine(serverRoot, file))) continue;
            offlineDetail = "Missing " + file + " in the server folder.";
            WriteLog("[Panel] " + offlineDetail);
            ShowOfflineStatus();
            return;
        }

        var candidate = new ServerRun(serverRoot);
        try
        {
            if (!candidate.Process.Start()) throw new InvalidOperationException("Windows did not start the launcher.");
        }
        catch (Exception error)
        {
            candidate.Process.Dispose();
            offlineDetail = "The launcher could not start. See the log below.";
            WriteLog("[Panel] " + error.Message);
            ShowOfflineStatus();
            return;
        }

        run = candidate;
        ready = false;
        hideWhenReady = true;
        stopAt = DateTime.MinValue;
        nextPriorityCheck = DateTime.MinValue;
        friendFeedback.Text = "Enter a friend's Hytale username once the server is running.";
        friendFeedback.ForeColor = Muted;
        SetStatus("Starting", Warning, "Loading the world. The panel will move to the system tray when ready.");
        UpdateRefreshRate();
        WriteLog("[Panel] Starting Hytale through Run-Server.bat.");
        candidate.Process.BeginOutputReadLine();
        candidate.Process.BeginErrorReadLine();
    }

    private static bool PortInUse()
    {
        try
        {
            foreach (var endpoint in IPGlobalProperties.GetIPGlobalProperties().GetActiveUdpListeners())
                if (endpoint.Port == ServerPort) return true;
        }
        catch (NetworkInformationException) { }
        return false;
    }

    private bool CanSaveSettings()
    {
        return run == null && !PortInUse() && !HytaleProcessExists();
    }

    private static bool HytaleProcessExists()
    {
        try
        {
            const string query = "SELECT ProcessId FROM Win32_Process WHERE " +
                "(Name = 'java.exe' OR Name = 'javaw.exe') AND CommandLine LIKE '%HytaleServer.jar%'";
            using (var searcher = new ManagementObjectSearcher(query))
            using (var processes = searcher.Get())
                return processes.Count > 0;
        }
        catch (ManagementException) { return false; }
        catch (UnauthorizedAccessException) { return false; }
    }

    private void RefreshServer()
    {
        var now = DateTime.UtcNow;
        RefreshHostingMode(now);
        if (!inTray && tabs.SelectedIndex == 0 && now >= nextFriendRefresh) RefreshFriends();
        if (copiedUntil != DateTime.MinValue && now >= copiedUntil)
        {
            copyAddress.Text = "Copy local address";
            copiedUntil = DateTime.MinValue;
        }

        if (run == null)
        {
            if (now >= nextPortCheck) ShowOfflineStatus();
            return;
        }

        StringBuilder lines = null;
        bool minimizeAfterRefresh = false;
        string line;
        for (int count = 0; count < 350 && run.Lines.TryDequeue(out line); count++)
        {
            if (lines == null) lines = new StringBuilder();
            line = ConsoleColor.Replace(line, "");
            lines.AppendLine(line);
            if (stopAt != DateTime.MinValue) continue;
            if (line.IndexOf("Hytale Server Booted! [Multiplayer]", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                ready = true;
                SetStatus("Running", CyberpunkTheme.Cyan, "Join from this PC at " + LocalAddress + ".");
                if (hideWhenReady)
                {
                    hideWhenReady = false;
                    minimizeAfterRefresh = true;
                }
            }
            else if (ready && ServerShutdown.IsMatch(line))
            {
                ready = false;
                SetStatus("Launcher active", Warning, "Waiting for the launcher to finish or restart the server.");
            }
        }
        if (lines != null) WriteLog(lines.ToString().TrimEnd('\r', '\n'));

        if (run.Process.HasExited)
        {
            if (run.ExitedAt == DateTime.MinValue) run.ExitedAt = now;
            if ((!run.OutputClosed || !run.ErrorClosed || !run.Lines.IsEmpty) && now < run.ExitedAt.AddSeconds(3)) return;
            int exitCode = run.Process.ExitCode;
            run.Process.Dispose();
            run = null;
            nextPriorityCheck = DateTime.MinValue;
            RefreshHostingMode(now);
            ready = false;
            hideWhenReady = false;
            stopAt = DateTime.MinValue;
            offlineDetail = exitCode == 0 ? "The server is stopped." : "The launcher exited with code " + exitCode + ". See the log below.";
            WriteLog("[Panel] " + offlineDetail);
            ShowOfflineStatus();
            UpdateRefreshRate();
            if (closeAfterStop) Close();
        }
        else
        {
            if (ready && minimizeAfterRefresh) MoveToTray();
            if (stopAt != DateTime.MinValue && now >= stopAt.AddSeconds(45) && !stop.Enabled)
            {
                detail.Text = "Still waiting for shutdown. Check the log or try Stop server again.";
                stop.Enabled = true;
                trayStop.Enabled = true;
            }
            UpdateRefreshRate();
        }
    }

    private void RefreshHostingMode(DateTime now)
    {
        if (now < nextPriorityCheck) return;
        nextPriorityCheck = now.AddSeconds(20);
        bool active = run != null || HytaleActivity.IsActive();
        if (!active)
        {
            backgroundPriority.Restore();
            return;
        }
        int adjusted = backgroundPriority.Apply();
        if (adjusted > 0) WriteLog("[Panel] Hosting mode applied energy-saving settings to " + adjusted +
            (adjusted == 1 ? " background process." : " background processes."));
    }

    private void MoveToTray()
    {
        if (inTray) return;
        inTray = true;
        trayIcon.Visible = true;
        Hide();
        UpdateRefreshRate();
    }

    private void RestoreFromTray()
    {
        // Keep Resize from sending the form back to the tray while Show restores its native state.
        inTray = true;
        Show();
        if (WindowState == FormWindowState.Minimized) WindowState = FormWindowState.Normal;
        inTray = false;
        if (WindowState == FormWindowState.Normal) KeepTitleBarOnScreen();

        // The shell may retain keyboard focus as the menu closes. Raise the window without pinning it.
        if (!TopMost)
        {
            TopMost = true;
            TopMost = false;
        }
        BringToFront();
        Activate();
        trayIcon.Visible = false;
        if (hiddenLog.Length > 0)
        {
            WriteLog(hiddenLog.ToString().TrimEnd('\r', '\n'));
            hiddenLog.Clear();
        }
        RefreshSelectedPage();
        UpdateRefreshRate();
    }

    private void RefreshSelectedPage()
    {
        if (tabs.SelectedIndex == 0) RefreshFriends();
        else if (tabs.SelectedTab == settingsTab) settingsPage.RefreshFromDisk();
        else if (tabs.SelectedTab == modsTab)
            modsPage.RefreshFromDisk(ready || (run == null && PortInUse() && HytaleProcessExists()));
    }

    private void RefreshFriends()
    {
        nextFriendRefresh = DateTime.UtcNow.AddSeconds(3);
        List<string> names;
        int unnamed;
        if (!whitelist.TryRead(out names, out unnamed))
        {
            whitelistHeading.Text = "Whitelisted friends";
            names.Add("Could not read the whitelist.");
        }
        else
        {
            int count = names.Count + unnamed;
            whitelistHeading.Text = "Whitelisted friends (" + count + ")";
            if (count == 0) names.Add("No friends added yet.");
            if (unnamed > 0) names.Add(unnamed + (unnamed == 1 ? " name unavailable" : " names unavailable"));
        }
        if (friendList.Items.Cast<string>().SequenceEqual(names)) return;

        string selected = friendList.SelectedItem as string;
        friendList.BeginUpdate();
        try
        {
            friendList.Items.Clear();
            friendList.Items.AddRange(names.ToArray());
            if (selected != null) friendList.SelectedIndex = friendList.Items.IndexOf(selected);
        }
        finally { friendList.EndUpdate(); }
    }

    private void KeepTitleBarOnScreen()
    {
        var titleBar = new Rectangle(Left, Top, Math.Min(Width, 200), SystemInformation.CaptionHeight);
        foreach (var screen in Screen.AllScreens)
        {
            var visible = Rectangle.Intersect(titleBar, screen.WorkingArea);
            if (visible.Width >= 60 && visible.Height >= titleBar.Height / 2) return;
        }

        var workArea = Screen.FromPoint(Cursor.Position).WorkingArea;
        Location = new Point(workArea.Left + Math.Max(0, (workArea.Width - Width) / 2),
            workArea.Top + Math.Max(0, (workArea.Height - Height) / 2));
    }

    private void UpdateRefreshRate()
    {
        int interval = inTray || run == null ? BackgroundRefreshMs : VisibleRefreshMs;
        if (run != null && !run.Lines.IsEmpty) interval = BacklogRefreshMs;
        if (timer.Interval != interval) timer.Interval = interval;
    }

    private void ShowOfflineStatus()
    {
        nextPortCheck = DateTime.UtcNow.AddSeconds(2);
        if (PortInUse())
        {
            SetStatus("Port 5520 in use", Warning, "A server or another application is already using the Hytale port.", true);
            start.Enabled = false;
        }
        else SetStatus("Stopped", Muted, offlineDetail);
    }

    private void SetStatus(string heading, Color color, string description, bool portBusy = false)
    {
        status.Text = heading;
        status.ForeColor = color;
        detail.Text = description;
        start.Enabled = run == null;
        hostingMode.Enabled = true;
        stop.Enabled = run != null && stopAt == DateTime.MinValue;
        trayStop.Enabled = stop.Enabled;
        trayIcon.Text = "Hytale Server Panel - " + heading;
        bool canSend = ready && stopAt == DateTime.MinValue;
        friend.Enabled = canSend;
        addFriend.Enabled = canSend;
        signIn.Enabled = canSend;
        settingsPage.SetServerRunning(run != null || portBusy);
        if (modsWereRunning != ready || modsPortWasBusy != portBusy)
        {
            modsWereRunning = ready;
            modsPortWasBusy = portBusy;
            if (!inTray && tabs.SelectedTab == modsTab) RefreshSelectedPage();
        }
    }

    private bool SendCommand(string command)
    {
        try
        {
            if (run == null || run.Process.HasExited) return false;
            run.Process.StandardInput.WriteLine(command);
            run.Process.StandardInput.Flush();
            return true;
        }
        catch (IOException error) { WriteLog("[Panel] Could not send the command: " + error.Message); }
        catch (InvalidOperationException error) { WriteLog("[Panel] Could not send the command: " + error.Message); }
        return false;
    }

    private void RequestStop()
    {
        if (!SendCommand("/stop"))
        {
            closeAfterStop = false;
            detail.Text = "Could not request shutdown. Check the log below.";
            return;
        }
        stopAt = DateTime.UtcNow;
        SetStatus("Stopping", Warning, "Waiting for Hytale to save the world and shut down.");
        WriteLog("[Panel] Graceful shutdown requested.");
    }

    private void ClosePanel(object sender, FormClosingEventArgs args)
    {
        if (run == null || args.CloseReason == CloseReason.WindowsShutDown) return;
        args.Cancel = true;
        if (closeAfterStop) return;
        if (MessageBox.Show(this, "Stop the server and close the panel?", Text,
            MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        closeAfterStop = true;
        if (stopAt == DateTime.MinValue) RequestStop();
    }

    private void AddFriend()
    {
        if (!addFriend.Enabled) return;
        string username = friend.Text.Trim();
        if (!ServerWhitelist.Username.IsMatch(username))
        {
            friendFeedback.Text = "Enter a Hytale username using letters, numbers, or underscores.";
            friendFeedback.ForeColor = Warning;
            friend.Focus();
            return;
        }
        if (!SendCommand("/whitelist add " + username)) return;
        friend.Clear();
        friendFeedback.Text = "Sent the request for " + username + ". See the server log for the result.";
        friendFeedback.ForeColor = CyberpunkTheme.Cyan;
    }

    private void CopyAddress()
    {
        try
        {
            Clipboard.SetText(LocalAddress);
            copyAddress.Text = "Copied!";
            copiedUntil = DateTime.UtcNow.AddSeconds(2);
        }
        catch (System.Runtime.InteropServices.ExternalException)
        {
            WriteLog("[Panel] Clipboard unavailable. The local address is " + LocalAddress + ".");
        }
    }

    private void OpenSignInLink(string link)
    {
        Uri address;
        if (!Uri.TryCreate(link, UriKind.Absolute, out address) || address.Scheme != Uri.UriSchemeHttps ||
            !String.Equals(address.Host, "accounts.hytale.com", StringComparison.OrdinalIgnoreCase)) return;
        try { Process.Start(new ProcessStartInfo(address.AbsoluteUri) { UseShellExecute = true }); }
        catch (System.ComponentModel.Win32Exception) { WriteLog("[Panel] Open the Hytale sign-in link in your browser."); }
    }

    private void WriteLog(string text)
    {
        if (inTray)
        {
            hiddenLog.AppendLine(text);
            if (hiddenLog.Length > RecentLogLimit) hiddenLog.Remove(0, hiddenLog.Length - RecentLogLimit);
            return;
        }
        int selection = log.SelectionStart;
        int selectedLength = log.SelectionLength;
        log.AppendText(text + Environment.NewLine);
        int removed = 0;
        if (log.TextLength > 140000)
        {
            string contents = log.Text;
            removed = contents.IndexOf('\n', contents.Length - RecentLogLimit) + 1;
            if (removed == 0) removed = contents.Length - RecentLogLimit;
            log.Select(0, removed);
            log.SelectedText = String.Empty;
        }
        if (selectedLength > 0 && selection >= removed) log.Select(selection - removed, selectedLength);
        else { log.Select(log.TextLength, 0); log.ScrollToCaret(); }
    }

    private sealed class ServerRun
    {
        internal readonly Process Process;
        internal readonly ConcurrentQueue<string> Lines = new ConcurrentQueue<string>();
        internal volatile bool OutputClosed;
        internal volatile bool ErrorClosed;
        internal DateTime ExitedAt;

        internal ServerRun(string root)
        {
            Process = new Process {
                StartInfo = new ProcessStartInfo {
                    FileName = Path.Combine(Environment.SystemDirectory, "cmd.exe"),
                    Arguments = "/d /c Run-Server.bat", WorkingDirectory = root,
                    UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true,
                    RedirectStandardOutput = true, RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
                }
            };
            Process.OutputDataReceived += (sender, args) => {
                if (args.Data == null) OutputClosed = true;
                else Lines.Enqueue(args.Data);
            };
            Process.ErrorDataReceived += (sender, args) => {
                if (args.Data == null) ErrorClosed = true;
                else Lines.Enqueue(args.Data);
            };
        }
    }
}
