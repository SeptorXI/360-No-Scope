using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Management;

internal static class HytaleActivity
{
    internal static bool IsActive()
    {
        int session;
        using (var current = Process.GetCurrentProcess()) session = current.SessionId;
        foreach (string name in new[] { "HytaleClient", "HytaleServer" })
        {
            Process[] processes;
            try { processes = Process.GetProcessesByName(name); }
            catch (Win32Exception) { continue; }
            catch (InvalidOperationException) { continue; }
            try
            {
                foreach (var process in processes)
                {
                    try { if (process.SessionId == session && !process.HasExited) return true; }
                    catch (InvalidOperationException) { }
                    catch (Win32Exception) { }
                }
            }
            finally { foreach (var process in processes) process.Dispose(); }
        }
        // A port alone is not enough: only an actual Hytale JVM activates the mode.
        try
        {
            const string query = "SELECT SessionId FROM Win32_Process WHERE " +
                "(Name = 'java.exe' OR Name = 'javaw.exe') AND CommandLine LIKE '%HytaleServer.jar%'";
            using (var searcher = new ManagementObjectSearcher(query))
            {
                searcher.Options.Timeout = TimeSpan.FromSeconds(2);
                using (var processes = searcher.Get())
                    foreach (ManagementObject process in processes)
                        using (process)
                            if (Convert.ToInt32(process["SessionId"]) == session) return true;
            }
        }
        catch (ManagementException) { }
        catch (UnauthorizedAccessException) { }
        catch (System.Runtime.InteropServices.COMException) { }
        return false;
    }
}
