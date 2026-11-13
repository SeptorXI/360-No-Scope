using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Management;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using Microsoft.Win32.SafeHandles;

internal sealed class BackgroundAppPriority : IDisposable
{
    internal const int Steam = 1;
    internal const int Epic = 2;
    internal const int Razer = 4;
    internal const int Discord = 8;
    internal const int Browsers = 16;
    private const int All = Steam | Epic | Razer | Discord | Browsers;
    private const uint ExecutionSpeed = 1;
    private const string JournalHeader = "HytaleBackgroundEfficiency|2";
    private const int ProcessPowerThrottling = 4;
    private static readonly object LeaseLock = new object();
    private static readonly HashSet<int> LeasedSessions = new HashSet<int>();

    private static readonly Dictionary<string, int> AppGroups = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase) {
        // The main Steam/Epic launchers are excluded: children can inherit their CPU priority.
        { "steamwebhelper", Steam }, { "EpicWebHelper", Epic }, { "RazerCortex", Razer },
        { "Discord", Discord }, { "chrome", Browsers }, { "msedge", Browsers }, { "firefox", Browsers },
        { "brave", Browsers }, { "opera", Browsers }
    };

    private readonly string selectionPath;
    private readonly string journalPath;
    private readonly string bridgeJournalPath;
    private readonly int sessionId;
    private readonly Dictionary<int, Change> changes = new Dictionary<int, Change>();
    private bool journalReadable;
    private bool recovering;
    private Mutex lease;
    private bool ownsLease;
    private bool disposed;

    internal int Selection { get; private set; }
    internal int ActiveCount { get { return ownsLease ? changes.Count : 0; } }

    internal BackgroundAppPriority(string settingsDirectory)
        : this(settingsDirectory, "restore-priority-") { }

    internal BackgroundAppPriority(string settingsDirectory, string journalPrefix)
    {
        if (String.IsNullOrEmpty(journalPrefix) || !Regex.IsMatch(journalPrefix, @"\A[A-Za-z0-9_-]{1,64}\z"))
            throw new ArgumentException("Use a simple journal filename prefix.", "journalPrefix");
        using (var current = Process.GetCurrentProcess()) sessionId = current.SessionId;
        selectionPath = Path.Combine(settingsDirectory, "background-apps.txt");
        journalPath = Path.Combine(settingsDirectory, journalPrefix + sessionId.ToString(CultureInfo.InvariantCulture) + ".txt");
        if (journalPrefix == "restore-priority-")
            bridgeJournalPath = Path.Combine(settingsDirectory, "live-efficiency-" + sessionId.ToString(CultureInfo.InvariantCulture) + ".txt");
        int selection;
        Selection = TryReadSelection(out selection) ? selection : (File.Exists(selectionPath) ? 0 : Steam | Epic);
        // Load recovery records only after acquiring the shared session lease.
        journalReadable = true;
    }

    internal bool SaveSelection(int selection)
    {
        selection &= All;
        if (!WriteAtomically(selectionPath, selection.ToString(CultureInfo.InvariantCulture))) return false;
        Selection = selection;
        return true;
    }

    internal int Apply()
    {
        Process[] processes;
        try { processes = Process.GetProcesses(); }
        catch (Win32Exception) { return 0; }
        try { return ApplyCandidates(processes); }
        finally { foreach (var process in processes) process.Dispose(); }
    }

    // A bounded inventory lets regression checks exercise child handles without touching other apps.
    private int ApplyCandidates(Process[] processes)
    {
        if (disposed || !journalReadable || !AcquireLease()) return 0;
        int selection;
        if (TryReadSelection(out selection)) Selection = selection;
        if (recovering)
        {
            RestoreChanges(true);
            recovering = false;
        }
        RestoreChanges(false);
        if (Selection == 0) return 0;

        var pending = new List<KeyValuePair<Process, Change>>();
        foreach (var process in processes)
        {
            var change = FindChange(process);
            if (change == null) continue;
            changes.Add(change.ProcessId, change);
            pending.Add(new KeyValuePair<Process, Change>(process, change));
        }
        if (pending.Count == 0) return 0;

        // Commit originals before either change. Recovery only undoes values that still match ours.
        if (!WriteJournal())
        {
            foreach (var item in pending) changes.Remove(item.Value.ProcessId);
            return 0;
        }
        int adjusted = 0;
        foreach (var item in pending)
        {
            ApplyChange(item.Key, item.Value);
            if (item.Value.PriorityChanged || item.Value.PowerChanged) adjusted++;
            else changes.Remove(item.Value.ProcessId);
        }
        WriteJournal();
        return adjusted;
    }

    private Change FindChange(Process process)
    {
        try
        {
            int group;
            string name = process.ProcessName;
            if (!AppGroups.TryGetValue(name, out group) || (Selection & group) == 0 ||
                changes.ContainsKey(process.Id)) return null;
            using (var opened = OpenCandidate(process.Id, true))
            {
                if (opened.IsInvalid) return null;
                var handle = opened.DangerousGetHandle();
                long started;
                if (!TryIdentity(handle, process.Id, name, out started)) return null;
                var priority = GetPriorityClass(handle);
                bool renderer = group == Discord && IsDiscordRenderer(process.Id);
                if (group == Discord && !renderer) return null;
                bool elevatedRenderer = renderer && (priority == ProcessPriorityClass.AboveNormal || priority == ProcessPriorityClass.High);
                if (priority != ProcessPriorityClass.Normal && priority != ProcessPriorityClass.BelowNormal &&
                    priority != ProcessPriorityClass.Idle && !elevatedRenderer) return null;
                if (HasExited(handle)) return null;

                PowerThrottlingState power;
                bool canReadPower = TryGetPower(handle, out power);
                // Razer can launch games: avoid changing its inheritable CPU priority.
                bool lowerPriority = group != Razer && (priority == ProcessPriorityClass.Normal || elevatedRenderer);
                bool changePower = canReadPower && !ExecutionThrottled(power);
                return lowerPriority || changePower
                    ? new Change(process.Id, started, name, priority, lowerPriority, changePower, power.ControlMask, power.StateMask)
                    : null;
            }
        }
        catch (InvalidOperationException) { return null; }
        catch (Win32Exception) { return null; }
    }

    private void ApplyChange(Process process, Change change)
    {
        try
        {
            using (var opened = OpenCandidate(change.ProcessId, true))
            {
            long started;
            var handle = opened.DangerousGetHandle();
            if (opened.IsInvalid || !TryIdentity(handle, change.ProcessId, change.Name, out started) || started != change.StartUtcTicks)
            { change.PriorityChanged = change.PowerChanged = false; return; }
            var priority = GetPriorityClass(handle);
            bool elevatedRenderer = change.Name.Equals("Discord", StringComparison.OrdinalIgnoreCase) &&
                (change.OriginalPriority == ProcessPriorityClass.AboveNormal || change.OriginalPriority == ProcessPriorityClass.High) &&
                priority == change.OriginalPriority;
            if (priority != ProcessPriorityClass.Normal && priority != ProcessPriorityClass.BelowNormal &&
                priority != ProcessPriorityClass.Idle && !elevatedRenderer)
            {
                change.PriorityChanged = change.PowerChanged = false;
                return;
            }
            if (change.PriorityChanged)
                change.PriorityChanged = priority == change.OriginalPriority &&
                    SetPriorityClass(handle, ProcessPriorityClass.BelowNormal);
            if (change.PowerChanged)
            {
                PowerThrottlingState power;
                bool unchanged = TryGetPower(handle, out power) &&
                    (power.ControlMask & ExecutionSpeed) == (change.PowerControl & ExecutionSpeed) &&
                    (power.StateMask & ExecutionSpeed) == (change.PowerState & ExecutionSpeed);
                if (unchanged)
                {
                    power.ControlMask |= ExecutionSpeed;
                    power.StateMask |= ExecutionSpeed;
                }
                change.PowerChanged = unchanged && TrySetPower(handle, power);
            }
            }
        }
        catch (InvalidOperationException) { change.PriorityChanged = change.PowerChanged = false; }
        catch (Win32Exception) { change.PriorityChanged = change.PowerChanged = false; }
    }

    internal void Restore()
    {
        if (disposed || !journalReadable || !AcquireLease()) return;
        RestoreChanges(true);
        recovering = false;
    }

    private void RestoreChanges(bool all)
    {
        RestoreChanges(all, journalPath);
    }

    private void RestoreChanges(bool all, string recoveryPath)
    {
        if (!ownsLease || changes.Count == 0) return;
        var completed = new List<int>();
        bool dirty = false;
        foreach (var change in changes.Values)
        {
            int group = AppGroups[change.Name];
            if (all || (Selection & group) == 0)
            {
                bool beforePriority = change.PriorityChanged, beforePower = change.PowerChanged;
                if (TryRestore(change)) completed.Add(change.ProcessId);
                dirty |= beforePriority != change.PriorityChanged || beforePower != change.PowerChanged;
            }
            else if (IdentityGone(change)) completed.Add(change.ProcessId);
        }
        foreach (int id in completed) changes.Remove(id);
        if (dirty || completed.Count != 0) WriteJournal(recoveryPath);
    }

    private bool IdentityGone(Change change)
    {
        try
        {
            using (var opened = OpenCandidate(change.ProcessId, false))
            {
                if (opened.IsInvalid) return MissingProcessError();
                var handle = opened.DangerousGetHandle();
                if (HasExited(handle)) return true;
                long started;
                if (!TryStartTicks(handle, out started)) return false;
                if (started != change.StartUtcTicks) return true;
                uint actualSession;
                if (ProcessIdToSessionId(change.ProcessId, out actualSession) && actualSession != sessionId) return true;
                string image = GetExecutableName(handle);
                return image != null && !String.Equals(image, change.Name, StringComparison.OrdinalIgnoreCase);
            }
        }
        catch (ArgumentException) { return true; }
        catch (InvalidOperationException) { return true; }
        catch (Win32Exception) { return false; }
    }

    private bool TryRestore(Change change)
    {
        try
        {
            using (var opened = OpenCandidate(change.ProcessId, true))
            {
                if (opened.IsInvalid) return MissingProcessError();
                var handle = opened.DangerousGetHandle();
                if (HasExited(handle)) return true;
                long started;
                uint actualSession;
                if (!TryStartTicks(handle, out started) || !ProcessIdToSessionId(change.ProcessId, out actualSession)) return false;
                if (started != change.StartUtcTicks || actualSession != sessionId) return true;
                string actualName = GetExecutableName(handle);
                if (actualName == null) return HasExited(handle);
                if (!String.Equals(actualName, change.Name, StringComparison.OrdinalIgnoreCase)) return true;
                if (change.PriorityChanged)
                {
                    var priority = GetPriorityClass(handle);
                    if (priority != 0 && (priority != ProcessPriorityClass.BelowNormal ||
                        SetPriorityClass(handle, change.OriginalPriority))) change.PriorityChanged = false;
                }
                if (change.PowerChanged)
                {
                    PowerThrottlingState power;
                    if (TryGetPower(handle, out power))
                    {
                        if (!ExecutionThrottled(power)) change.PowerChanged = false;
                        else
                        {
                            // Restore only our execution-speed bit, keeping unrelated power settings intact.
                            power.ControlMask = (power.ControlMask & ~ExecutionSpeed) | (change.PowerControl & ExecutionSpeed);
                            power.StateMask = (power.StateMask & ~ExecutionSpeed) | (change.PowerState & ExecutionSpeed);
                            if (TrySetPower(handle, power)) change.PowerChanged = false;
                        }
                    }
                }
                return (!change.PriorityChanged && !change.PowerChanged) || HasExited(handle);
            }
        }
        catch (ArgumentException) { return true; }
        catch (InvalidOperationException) { return true; }
        catch (Win32Exception) { return false; }
    }

    private bool AcquireLease()
    {
        lock (LeaseLock)
        {
            if (ownsLease) return true;
            if (LeasedSessions.Contains(sessionId)) return false;
            try
            {
                if (lease == null) lease = new Mutex(false, "Local\\HytaleBackgroundEfficiencySession" + sessionId.ToString(CultureInfo.InvariantCulture));
                try { ownsLease = lease.WaitOne(0); }
                catch (AbandonedMutexException) { ownsLease = true; }
                if (!ownsLease) return false;
                LeasedSessions.Add(sessionId);
                changes.Clear();
                if (bridgeJournalPath != null && File.Exists(bridgeJournalPath))
                {
                    journalReadable = ReadJournal(bridgeJournalPath);
                    if (journalReadable) RestoreChanges(true, bridgeJournalPath);
                    changes.Clear();
                }
                journalReadable = ReadJournal(journalPath) && journalReadable;
                recovering = changes.Count != 0;
                return journalReadable;
            }
            catch (UnauthorizedAccessException) { return false; }
            catch (IOException) { return false; }
            catch (Win32Exception) { return false; }
        }
    }

    private bool TryReadSelection(out int selection)
    {
        selection = 0;
        try
        {
            return Int32.TryParse(File.ReadAllText(selectionPath), NumberStyles.Integer, CultureInfo.InvariantCulture, out selection)
                && selection >= 0 && (selection & ~All) == 0;
        }
        catch (IOException) { return false; }
        catch (UnauthorizedAccessException) { return false; }
    }

    private bool ReadJournal(string path)
    {
        try
        {
            if (new FileInfo(path).Length > 1048576) return false;
            string[] lines = File.ReadAllLines(path);
            bool modern = lines.Length > 0 && lines[0] == JournalHeader;
            var parsed = new Dictionary<int, Change>();
            for (int index = modern ? 1 : 0; index < lines.Length; index++)
            {
                string line = lines[index];
                if (line.Length > 256 || parsed.Count >= 4096) return false;
                string[] fields = line.Split('|');
                int id;
                long ticks;
                if (fields.Length != (modern ? 8 : 4) || !AppGroups.ContainsKey(fields[2]) ||
                    !Int32.TryParse(fields[0], NumberStyles.None, CultureInfo.InvariantCulture, out id) || id <= 0 ||
                    !Int64.TryParse(fields[1], NumberStyles.None, CultureInfo.InvariantCulture, out ticks) || ticks <= 0 ||
                    ticks > DateTime.MaxValue.Ticks || parsed.ContainsKey(id)) return false;
                ProcessPriorityClass priority;
                bool priorityChanged = true, powerChanged = false;
                uint control = 0, state = 0;
                if (!modern)
                {
                    if (fields[3] != "Normal") return false;
                    priority = ProcessPriorityClass.Normal;
                }
                else
                {
                    if (!Enum.TryParse<ProcessPriorityClass>(fields[3], false, out priority) ||
                        (priority != ProcessPriorityClass.Normal && priority != ProcessPriorityClass.BelowNormal && priority != ProcessPriorityClass.Idle &&
                            !(fields[2].Equals("Discord", StringComparison.OrdinalIgnoreCase) &&
                                (priority == ProcessPriorityClass.AboveNormal || priority == ProcessPriorityClass.High))) ||
                        !TryFlag(fields[4], out priorityChanged) || !TryFlag(fields[5], out powerChanged) ||
                        !UInt32.TryParse(fields[6], NumberStyles.None, CultureInfo.InvariantCulture, out control) ||
                        !UInt32.TryParse(fields[7], NumberStyles.None, CultureInfo.InvariantCulture, out state) ||
                        (!priorityChanged && !powerChanged) ||
                        (priorityChanged && priority != ProcessPriorityClass.Normal &&
                            !(fields[2].Equals("Discord", StringComparison.OrdinalIgnoreCase) &&
                                (priority == ProcessPriorityClass.AboveNormal || priority == ProcessPriorityClass.High))) ||
                        (powerChanged && (control & ExecutionSpeed) != 0 && (state & ExecutionSpeed) != 0)) return false;
                }
                parsed.Add(id, new Change(id, ticks, fields[2], priority, priorityChanged, powerChanged, control, state));
            }
            foreach (var item in parsed) changes.Add(item.Key, item.Value);
            return true;
        }
        catch (FileNotFoundException) { return true; }
        catch (DirectoryNotFoundException) { return true; }
        catch (IOException) { return false; }
        catch (UnauthorizedAccessException) { return false; }
    }

    private static bool TryFlag(string value, out bool flag)
    {
        flag = value == "1";
        return flag || value == "0";
    }

    private bool WriteJournal()
    {
        return WriteJournal(journalPath);
    }

    private bool WriteJournal(string path)
    {
        var content = new StringBuilder(JournalHeader).AppendLine();
        foreach (var change in changes.Values)
            content.Append(change.ProcessId.ToString(CultureInfo.InvariantCulture)).Append('|')
                .Append(change.StartUtcTicks.ToString(CultureInfo.InvariantCulture)).Append('|').Append(change.Name).Append('|')
                .Append(change.OriginalPriority).Append('|').Append(change.PriorityChanged ? "1" : "0").Append('|')
                .Append(change.PowerChanged ? "1" : "0").Append('|').Append(change.PowerControl.ToString(CultureInfo.InvariantCulture)).Append('|')
                .Append(change.PowerState.ToString(CultureInfo.InvariantCulture)).AppendLine();
        return WriteAtomically(path, content.ToString());
    }

    private static bool WriteAtomically(string path, string contents)
    {
        string temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            byte[] bytes = Encoding.UTF8.GetBytes(contents);
            using (var output = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                output.Write(bytes, 0, bytes.Length);
                output.Flush(true);
            }
            if (File.Exists(path)) File.Replace(temporary, path, null);
            else File.Move(temporary, path);
            return true;
        }
        catch (IOException) { return false; }
        catch (UnauthorizedAccessException) { return false; }
        finally
        {
            try { File.Delete(temporary); }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
    }

    private static bool IsDiscordRenderer(int processId)
    {
        try
        {
            using (var search = new ManagementObjectSearcher("SELECT CommandLine FROM Win32_Process WHERE ProcessId=" +
                processId.ToString(CultureInfo.InvariantCulture) + " AND Name='Discord.exe'"))
            {
            search.Options.Timeout = TimeSpan.FromSeconds(2);
            using (var results = search.Get())
                foreach (ManagementObject process in results)
                    using (process)
                    {
                        string command = process["CommandLine"] as string;
                        return command != null && Regex.IsMatch(command, @"(?:^|\s)""?--type=(?:renderer|""renderer"")""?(?=\s|$)", RegexOptions.IgnoreCase);
                    }
            }
        }
        catch (ManagementException) { }
        catch (UnauthorizedAccessException) { }
        catch (System.Runtime.InteropServices.COMException) { }
        return false;
    }

    private static bool ExecutionThrottled(PowerThrottlingState power)
    {
        return (power.ControlMask & ExecutionSpeed) != 0 && (power.StateMask & ExecutionSpeed) != 0;
    }

    private static bool TryGetPower(IntPtr handle, out PowerThrottlingState power)
    {
        power = new PowerThrottlingState { Version = 1 };
        try { return GetProcessInformation(handle, ProcessPowerThrottling, ref power, (uint)Marshal.SizeOf(typeof(PowerThrottlingState))); }
        catch (EntryPointNotFoundException) { return false; }
        catch (DllNotFoundException) { return false; }
    }

    private static bool TrySetPower(IntPtr handle, PowerThrottlingState power)
    {
        try { return SetProcessInformation(handle, ProcessPowerThrottling, ref power, (uint)Marshal.SizeOf(typeof(PowerThrottlingState))); }
        catch (EntryPointNotFoundException) { return false; }
        catch (DllNotFoundException) { return false; }
    }

    public void Dispose()
    {
        if (disposed) return;
        try { Restore(); }
        finally
        {
            disposed = true;
            if (ownsLease)
            {
                lock (LeaseLock)
                {
                    try { lease.ReleaseMutex(); }
                    catch (ApplicationException) { }
                    ownsLease = false;
                    LeasedSessions.Remove(sessionId);
                }
            }
            if (lease != null) lease.Dispose();
        }
    }

    private static string GetExecutableName(IntPtr process)
    {
        var image = new StringBuilder(1024);
        int length = image.Capacity;
        return QueryFullProcessImageName(process, 0, image, ref length)
            ? Path.GetFileNameWithoutExtension(image.ToString()) : null;
    }

    private static NativeProcessHandle OpenCandidate(int id, bool writable)
    {
        // Query-limited + set-information, never PROCESS_ALL_ACCESS or debug privileges.
        return new NativeProcessHandle(OpenProcess(0x1000u | (writable ? 0x0200u : 0u), false, id));
    }

    private static bool MissingProcessError()
    {
        int error = Marshal.GetLastWin32Error();
        return error == 87 || error == 1168;
    }

    private bool TryIdentity(IntPtr handle, int id, string name, out long started)
    {
        uint actualSession;
        started = 0;
        return !HasExited(handle) && ProcessIdToSessionId(id, out actualSession) && actualSession == sessionId &&
            String.Equals(GetExecutableName(handle), name, StringComparison.OrdinalIgnoreCase) && TryStartTicks(handle, out started);
    }

    private static bool TryStartTicks(IntPtr handle, out long ticks)
    {
        long creation, exit, kernel, user;
        ticks = 0;
        if (!GetProcessTimes(handle, out creation, out exit, out kernel, out user)) return false;
        try { ticks = DateTime.FromFileTimeUtc(creation).Ticks; return true; }
        catch (ArgumentOutOfRangeException) { return false; }
    }

    private static bool HasExited(IntPtr handle)
    {
        uint code;
        return GetExitCodeProcess(handle, out code) && code != 259;
    }

    private sealed class NativeProcessHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        internal NativeProcessHandle(IntPtr value) : base(true) { SetHandle(value); }
        protected override bool ReleaseHandle() { return CloseHandle(handle); }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct PowerThrottlingState
    {
        internal uint Version;
        internal uint ControlMask;
        internal uint StateMask;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern bool QueryFullProcessImageName(IntPtr process, int flags, StringBuilder name, ref int size);
    [DllImport("kernel32.dll")]
    private static extern bool ProcessIdToSessionId(int processId, out uint session);
    [DllImport("kernel32.dll")]
    private static extern ProcessPriorityClass GetPriorityClass(IntPtr process);
    [DllImport("kernel32.dll")]
    private static extern bool SetPriorityClass(IntPtr process, ProcessPriorityClass priority);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetProcessInformation(IntPtr process, int informationClass, ref PowerThrottlingState information, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetProcessInformation(IntPtr process, int informationClass, ref PowerThrottlingState information, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr OpenProcess(uint access, bool inheritHandle, int id);
    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")]
    private static extern bool GetProcessTimes(IntPtr handle, out long creation, out long exit, out long kernel, out long user);
    [DllImport("kernel32.dll")]
    private static extern bool GetExitCodeProcess(IntPtr handle, out uint exitCode);

    private sealed class Change
    {
        internal readonly int ProcessId;
        internal readonly long StartUtcTicks;
        internal readonly string Name;
        internal readonly ProcessPriorityClass OriginalPriority;
        internal readonly uint PowerControl;
        internal readonly uint PowerState;
        internal bool PriorityChanged;
        internal bool PowerChanged;

        internal Change(int processId, long startUtcTicks, string name, ProcessPriorityClass priority,
            bool priorityChanged, bool powerChanged, uint powerControl, uint powerState)
        {
            ProcessId = processId;
            StartUtcTicks = startUtcTicks;
            Name = name;
            OriginalPriority = priority;
            PriorityChanged = priorityChanged;
            PowerChanged = powerChanged;
            PowerControl = powerControl;
            PowerState = powerState;
        }
    }
}
