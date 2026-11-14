/*
 * Odinštalovanie FUKAI. Spúšťa → Aplikácie cez UninstallString.
 * Dáta používateľa (chaty, nastavenia, modely) sa mažú len na výslovnú žiadosť.
 */

using Microsoft.Win32;
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("FUKAI Uninstall")]
[assembly: AssemblyProduct("FUKAI")]
[assembly: AssemblyDescription("Odinštalovanie FUKAI")]
[assembly: AssemblyCompany("Lukas Vavro")]
[assembly: AssemblyCopyright("Copyright (C) 2026 Lukas Vavro")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace Fukai
{
    internal static class Uninstall
    {
        private const string AppName = "FUKAI";
        private const string UninstallKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\FUKAI";

        [STAThread]
        private static int Main(string[] args)
        {
            AppContext.SetSwitch("Switch.System.IO.UseLegacyPathHandling", false);
            AppContext.SetSwitch("Switch.System.IO.BlockLongPaths", false);

            string self = typeof(Uninstall).Assembly.Location;
            int index = Array.IndexOf(args, "--from");
            if (index >= 0 && index + 1 < args.Length)
                return Remove(args[index + 1]);

            string target = Path.GetDirectoryName(self);
            if (!Ask("Naozaj chceš odinštalovať FUKAI?\n\n" + target, MessageBoxIcon.Question))
                return 0;
            if (IsRunning(target))
            {
                Say("FUKAI je spustený. Zavri ho a skús to znova.", MessageBoxIcon.Warning);
                return 1;
            }
            return Relaunch(self, target);
        }

        private static int Relaunch(string self, string target)
        {
            try
            {
                string copy = Path.Combine(Path.GetTempPath(), "fukai-uninstall-" + Guid.NewGuid().ToString("N").Substring(0, 8) + ".exe");
                File.Copy(self, copy, true);
                Process.Start(new ProcessStartInfo(copy, "--from \"" + target + "\"") { UseShellExecute = false });
                return 0;
            }
            catch (Exception exc)
            {
                Say("Odinštalovanie sa nepodarilo spustiť.\n\n" + exc.Message, MessageBoxIcon.Error);
                return 1;
            }
        }

        private static int Remove(string target)
        {
            for (int attempt = 0; attempt < 20 && File.Exists(Path.Combine(target, "uninstall.exe")); attempt++)
            {
                try
                {
                    File.OpenWrite(Path.Combine(target, "uninstall.exe")).Dispose();
                    break;
                }
                catch (IOException)
                {
                    System.Threading.Thread.Sleep(250);
                }
            }

            string data = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), AppName);
            bool removeData = Directory.Exists(data) && Ask(
                "Zmazať aj chaty, nastavenia a stiahnuté modely?\n\n" + data + " (" + Size(data) + ")\n\n" +
                "Ak vyberieš Nie, dáta zostanú a nová inštalácia ich nájde.", MessageBoxIcon.Warning, false);

            string failed = null;
            if (!DeleteTree(target))
                failed = target;
            if (removeData && !DeleteTree(data))
                failed = data;

            DeleteShortcut(Environment.SpecialFolder.Programs);
            DeleteShortcut(Environment.SpecialFolder.DesktopDirectory);
            try { Microsoft.Win32.Registry.CurrentUser.DeleteSubKeyTree(UninstallKey, false); }
            catch (Exception) { }

            if (failed != null)
            {
                Say("FUKAI bol odinštalovaný, ale priečinok " + failed +
                    " sa nepodarilo zmazať celý. Zmaž ho ručne.", MessageBoxIcon.Warning);
                return 1;
            }
            Say("FUKAI bol odinštalovaný.", MessageBoxIcon.Information);
            return 0;
        }

        private static bool IsRunning(string target)
        {
            foreach (Process process in Process.GetProcessesByName("FUKAI"))
            {
                try
                {
                    if (process.MainModule.FileName.StartsWith(target, StringComparison.OrdinalIgnoreCase))
                        return true;
                }
                catch (Exception)
                {
                    return true;
                }
            }
            return false;
        }

        private static void DeleteShortcut(Environment.SpecialFolder folder)
        {
            try
            {
                string path = Path.Combine(Environment.GetFolderPath(folder), AppName + ".lnk");
                if (File.Exists(path))
                    File.Delete(path);
            }
            catch (Exception)
            {
            }
        }

        private static bool DeleteTree(string path)
        {
            for (int attempt = 0; attempt < 5; attempt++)
            {
                if (!Directory.Exists(path))
                    return true;
                try
                {
                    Directory.Delete(Long(path), true);
                    return true;
                }
                catch (Exception)
                {
                    System.Threading.Thread.Sleep(500);
                }
            }
            return !Directory.Exists(path);
        }

        private static string Long(string path)
        {
            string full = Path.GetFullPath(path);
            return full.StartsWith(@"\\", StringComparison.Ordinal) ? full : @"\\?\" + full;
        }

        private static string Size(string path)
        {
            try
            {
                long total = 0;
                foreach (string file in Directory.GetFiles(path, "*", SearchOption.AllDirectories))
                    total += new FileInfo(file).Length;
                return total < 1024L * 1024 * 1024
                    ? (total / (1024 * 1024)) + " MB"
                    : (total / (1024.0 * 1024 * 1024)).ToString("0.0") + " GB";
            }
            catch (Exception)
            {
                return "?";
            }
        }

        private static bool Ask(string text, MessageBoxIcon icon, bool defaultYes = true)
        {
            MessageBoxDefaultButton first = defaultYes ? MessageBoxDefaultButton.Button1 : MessageBoxDefaultButton.Button2;
            return MessageBox.Show(text, AppName, MessageBoxButtons.YesNo, icon, first) == DialogResult.Yes;
        }

        private static void Say(string text, MessageBoxIcon icon)
        {
            MessageBox.Show(text, AppName, MessageBoxButtons.OK, icon);
        }
    }
}
