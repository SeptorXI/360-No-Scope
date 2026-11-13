using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;

internal sealed class ServerWhitelist
{
    internal static readonly Regex Username = new Regex(@"\A[A-Za-z0-9_]{1,32}\z");
    private const string JoinPermission = "hytale.server.join";
    private readonly string permissionsPath;
    private readonly string playersPath;
    private readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = Int32.MaxValue };
    private readonly Dictionary<Guid, SavedName> names = new Dictionary<Guid, SavedName>();

    internal ServerWhitelist(string serverRoot)
    {
        string serverDirectory = Path.Combine(serverRoot, "Server");
        permissionsPath = Path.Combine(serverDirectory, "permissions.json");
        playersPath = Path.Combine(serverDirectory, "universe", "players");
    }

    internal bool TryRead(out List<string> usernames, out int unnamed)
    {
        usernames = new List<string>();
        unnamed = 0;
        Dictionary<string, object> permissions;
        try { permissions = ReadObject(permissionsPath); }
        catch (FileNotFoundException) { return true; }
        catch (DirectoryNotFoundException) { return true; }
        catch (Exception error)
        {
            if (!IsReadError(error)) throw;
            return false;
        }

        object entries;
        if (!permissions.TryGetValue("users", out entries)) return true;
        var users = entries as Dictionary<string, object>;
        if (users == null) return false;

        foreach (var user in users)
        {
            Guid id;
            var record = user.Value as Dictionary<string, object>;
            object grants;
            if (record == null || !record.TryGetValue("permissions", out grants) || !Guid.TryParseExact(user.Key, "D", out id)) continue;
            var values = grants as IList;
            if (values == null || !values.Contains(JoinPermission)) continue;

            string name = ReadSavedName(id);
            if (name == null) unnamed++;
            else usernames.Add(name);
        }
        usernames.Sort(StringComparer.OrdinalIgnoreCase);
        return true;
    }

    private string ReadSavedName(Guid id)
    {
        string path = Path.Combine(playersPath, id.ToString("D") + ".json");
        try
        {
            var file = new FileInfo(path);
            if (!file.Exists) return null;
            DateTime written = file.LastWriteTimeUtc;
            long length = file.Length;
            SavedName known;
            if (names.TryGetValue(id, out known) && known.Written == written && known.Length == length)
                return known.Name;

            var player = ReadObject(path);
            var components = ChildObject(player, "Components");
            var nameplate = ChildObject(components, "Nameplate");
            object text;
            string name = nameplate != null && nameplate.TryGetValue("Text", out text) ? text as string : null;
            if (name != null && !Username.IsMatch(name)) name = null;
            names[id] = new SavedName { Written = written, Length = length, Name = name };
            return name;
        }
        catch (Exception error)
        {
            if (!IsReadError(error)) throw;
            return null;
        }
    }

    private Dictionary<string, object> ReadObject(string path)
    {
        using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
        using (var reader = new StreamReader(stream))
        {
            var data = json.DeserializeObject(reader.ReadToEnd()) as Dictionary<string, object>;
            if (data == null) throw new InvalidDataException();
            return data;
        }
    }

    private static Dictionary<string, object> ChildObject(Dictionary<string, object> parent, string key)
    {
        object value;
        return parent != null && parent.TryGetValue(key, out value) ? value as Dictionary<string, object> : null;
    }

    private static bool IsReadError(Exception error)
    {
        return error is IOException || error is UnauthorizedAccessException || error is ArgumentException || error is InvalidOperationException;
    }

    private sealed class SavedName
    {
        internal DateTime Written;
        internal long Length;
        internal string Name;
    }
}
