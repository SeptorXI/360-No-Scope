using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

// Temporary bridge for the panel already running during this update. The rebuilt
// panel has the same manager built in; a shared lease prevents overlapping owners.
internal static class HytaleQuietMode
{
    [STAThread]
    private static void Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string settings = Path.Combine(root, "PanelSettings");
        string maintenance = Path.Combine(root, ".performance-2026-11-06");
        string stopFile = Path.Combine(maintenance, "stop-live-mode.txt");
        string receipt = Path.Combine(maintenance, "live-status.json");
        Directory.CreateDirectory(maintenance);
        using (var single = new Mutex(false, @"Local\HytaleQuietModeMonitor"))
        {
            bool acquired;
            try { acquired = single.WaitOne(0); }
            catch (AbandonedMutexException) { acquired = true; }
            if (!acquired) return;
            try
            {
                using (var manager = new BackgroundAppPriority(settings, "live-efficiency-"))
                {
                    try
                    {
                        while (!File.Exists(stopFile) && HytaleActivity.IsActive())
                        {
                            int adjusted = manager.Apply();
                            WriteStatus(receipt, "Active", adjusted, manager.ActiveCount);
                            for (int seconds = 0; seconds < 20 && !File.Exists(stopFile); seconds++)
                                Thread.Sleep(1000);
                        }
                    }
                    finally { manager.Restore(); }
                }
                WriteStatus(receipt, "Stopped", 0);
            }
            catch (Exception error)
            {
                // Do not write paths, command lines, or other apps' private data.
                WriteStatus(receipt, "Stopped: " + error.GetType().Name, 0);
            }
            finally { single.ReleaseMutex(); }
        }
    }

    private static void WriteStatus(string path, string state, int adjusted, int managed = 0)
    {
        try
        {
            using (var current = Process.GetCurrentProcess())
            {
                string json = new JavaScriptSerializer().Serialize(new {
                    State = state, UpdatedUtc = DateTime.UtcNow.ToString("o"),
                    HelperProcessId = current.Id, NewlyAdjusted = adjusted,
                    ManagedProcesses = managed, PollSeconds = 20
                });
                string temporary = path + ".tmp";
                File.WriteAllText(temporary, json, new UTF8Encoding(false));
                if (File.Exists(path)) File.Replace(temporary, path, null);
                else File.Move(temporary, path);
            }
        }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }
}
