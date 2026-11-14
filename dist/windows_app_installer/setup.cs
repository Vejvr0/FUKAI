/*
 * Inštalačka FUKAI pre Windows
 *   minimá a verzie    manifest.json
 *   CPU                IsProcessorFeaturePresent
 *   GPU                nvidia-smi
 *   prostredie         uv (Python, zámok, wheel), test backendu, záloha na CPU
 * Kód 0 = hotovo, 1 = počítač nestačí, 2 = chyba manifestu, 3 = inštalácia zlyhala.
 */

using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Management;
using System.Net;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

[assembly: AssemblyTitle("FUKAI Setup")]
[assembly: AssemblyProduct("FUKAI")]
[assembly: AssemblyDescription("Inštalácia FUKAI")]
[assembly: AssemblyCompany("Lukas Vavro")]
[assembly: AssemblyCopyright("Copyright (C) 2026 Lukas Vavro")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace Fukai
{
    internal enum Backend { None, Cpu, Cuda }
    internal sealed class Detection
    {
        public Backend Backend;
        public string Blocker;
        public readonly List<string> Notes = new List<string>();
        public int OsBuild;
        public bool? Avx2;
        public bool GpuChecked;
        public string GpuName;
        public string DriverVersion;
        public string ComputeCapability;
        public int VramMb;
    }

    internal static class Detector
    {
        private const uint PF_AVX2_INSTRUCTIONS_AVAILABLE = 40;
        private const int SmiTimeoutMs = 10000;

        [DllImport("kernel32.dll")]
        private static extern bool IsProcessorFeaturePresent(uint feature);

        public static Detection Detect(Manifest manifest)
        {
            Detection result = new Detection();

            result.OsBuild = OsBuild();
            if (result.OsBuild > 0 && result.OsBuild < manifest.WindowsBuild)
            {
                result.Blocker = string.Format(
                    "FUKAI potrebuje aspoň Windows 10 verziu 2004 (zostava {0}), tento počítač má {1}.", manifest.WindowsBuild, result.OsBuild
                );
                return result;
            }

            result.Avx2 = IsProcessorFeaturePresent(PF_AVX2_INSTRUCTIONS_AVAILABLE);
            if (result.Avx2 != true)
            {
                result.Blocker = "Procesor tohto počítača nepodporuje inštrukcie AVX2, ktoré FUKAI potrebuje. Vyžaduje sa Intel od roku 2013 alebo AMD od roku 2015.";
                return result;
            }

            result.Backend = ChooseGpuBackend(manifest, result);
            return result;
        }

        private static Backend ChooseGpuBackend(Manifest manifest, Detection result)
        {
            result.GpuChecked = true;
            string smi = RunNvidiaSmi();
            if (smi == null)
            {
                string card = NvidiaCardFromWmi();
                if (card != null)
                {
                    result.GpuName = card;
                    result.Notes.Add("Karta " + card + " sa nepoužije: ovládač NVIDIA chýba alebo je poškodený. Nainštaluj ovládač a spusti inštaláciu FUKAI znova.");
                }
                return Backend.Cpu;
            }

            string[] parts = smi.Split(',');
            if (parts.Length < 3) return Backend.Cpu;
            result.GpuName = parts[0].Trim();
            result.DriverVersion = parts[1].Trim();
            result.ComputeCapability = parts[2].Trim();
            if (parts.Length > 3) result.VramMb = ParseMib(parts[3]);
            if (Version(result.ComputeCapability) < Version(manifest.CudaComputeCapability))
            {
                result.Notes.Add(string.Format(
                    "Karta {0} je staršia, než knižnica FUKAI podporuje (vyžaduje sa {1}, karta má {2}). FUKAI pobeží na CPU.", result.GpuName, manifest.CudaComputeCapability, result.ComputeCapability
                ));
                return Backend.Cpu;
            }
            if (Version(result.DriverVersion) < Version(manifest.CudaDriver))
            {
                result.Notes.Add(string.Format(
                    "Ovládač NVIDIA {0} je starší, než CUDA 13 potrebuje (vyžaduje sa {1}). Aktualizuj ovládač a spusti inštaláciu FUKAI znova. FUKAI pobeží na CPU.", result.DriverVersion, manifest.CudaDriver
                ));
                return Backend.Cpu;
            }
            return Backend.Cuda;
        }

        private static int OsBuild()
        {
            try
            {
                using (Microsoft.Win32.RegistryKey key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion"))
                {
                    if (key == null) return 0;
                    object value = key.GetValue("CurrentBuildNumber");
                    int build;
                    return value != null && int.TryParse(value.ToString(), out build) ? build : 0;
                }
            }
            catch (Exception)
            {
                return 0;
            }
        }

        private static string RunNvidiaSmi()
        {
            try
            {
                ProcessStartInfo info = new ProcessStartInfo("nvidia-smi", "--query-gpu=name,driver_version,compute_cap,memory.total --format=csv,noheader");
                info.UseShellExecute = false;
                info.RedirectStandardOutput = true;
                info.RedirectStandardError = true;
                info.CreateNoWindow = true;
                info.StandardOutputEncoding = Encoding.UTF8;

                using (Process process = Process.Start(info))
                {
                    string output = process.StandardOutput.ReadToEnd();
                    if (!process.WaitForExit(SmiTimeoutMs))
                    {
                        try { process.Kill(); } catch (Exception) { }
                        return null;
                    }
                    if (process.ExitCode != 0) return null;
                    string[] lines = output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                    return lines.Length > 0 ? lines[0] : null;
                }
            }
            catch (Exception)
            {
                return null;
            }
        }

        private static string NvidiaCardFromWmi()
        {
            try
            {
                using (ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT Name FROM Win32_VideoController"))
                {
                    foreach (ManagementBaseObject item in searcher.Get())
                    {
                        object name = item["Name"];
                        if (name != null && name.ToString().IndexOf("NVIDIA", StringComparison.OrdinalIgnoreCase) >= 0) return name.ToString().Trim();
                    }
                }
            }
            catch (Exception) { }
            return null;
        }

        private static int ParseMib(string text)
        {
            string digits = new string(Array.FindAll(text.ToCharArray(), char.IsDigit));
            int value;
            return int.TryParse(digits, out value) ? value : 0;
        }

        private static long Version(string text)
        {
            long result = 0;
            if (string.IsNullOrEmpty(text)) return 0;
            foreach (string part in text.Split('.'))
            {
                int number;
                int.TryParse(part.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out number);
                result = result * 10000 + number;
            }
            return result;
        }
    }

    internal sealed class Manifest
    {
        public string AppVersion;
        public string Python;
        public string Releases;
        public int WindowsBuild;
        public string CudaComputeCapability;
        public string CudaDriver;
        private readonly Dictionary<string, BackendSpec> _backends = new Dictionary<string, BackendSpec>();

        public BackendSpec Backend(string name)
        {
            BackendSpec spec;
            if (!_backends.TryGetValue(name, out spec))
                throw new InstallException("Manifest nepozná backend " + name + ".");
            return spec;
        }

        public static Manifest Parse(string json)
        {
            Dictionary<string, object> root = (Dictionary<string, object>) new JavaScriptSerializer().DeserializeObject(json);
            Dictionary<string, object> minimum = (Dictionary<string, object>)root["minimum"];

            Manifest manifest = new Manifest();
            manifest.AppVersion = Text(root["app_version"]);
            manifest.Python = Text(root["python"]);
            manifest.Releases = Text(root["releases"]).TrimEnd('/');
            manifest.WindowsBuild = Convert.ToInt32(minimum["windows_build"]);
            manifest.CudaComputeCapability = Text(minimum["cuda_compute_capability"]);
            manifest.CudaDriver = Text(minimum["cuda_driver"]);

            foreach (KeyValuePair<string, object> entry in (Dictionary<string, object>)root["backends"])
            {
                Dictionary<string, object> item = (Dictionary<string, object>)entry.Value;
                if (!string.Equals(Text(item["os"]), "windows", StringComparison.OrdinalIgnoreCase))
                    continue;                           // metal patrí macOS inštalačke
                Dictionary<string, object> wheel = (Dictionary<string, object>)item["wheel"];
                BackendSpec spec = new BackendSpec();
                spec.Name = entry.Key;
                spec.Lock = Text(item["lock"]);
                spec.Fallback = item.ContainsKey("fallback") ? Text(item["fallback"]) : null;
                spec.WheelRelease = Text(wheel["release"]);
                spec.WheelFile = Text(wheel["file"]);
                spec.WheelSha256 = Text(wheel["sha256"]);
                manifest._backends[spec.Name] = spec;
            }
            return manifest;
        }

        private static string Text(object value)
        {
            return Convert.ToString(value, CultureInfo.InvariantCulture);
        }
    }


    internal sealed class BackendSpec
    {
        public string Name;
        public string Lock;
        public string Fallback;
        public string WheelRelease;
        public string WheelFile;
        public string WheelSha256;
    }

    internal sealed class Log
    {
        private readonly string _path;
        private readonly Action<string> _sink;

        /// <param name="sink">Kam okrem súboru – konzola alebo okno inštalačky.</param>
        public Log(string path, Action<string> sink)
        {
            _path = path;
            _sink = sink;
            Directory.CreateDirectory(Path.GetDirectoryName(path));
        }

        public void Write(string text)
        {
            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture) + " " + text;
            if (_sink != null)
                _sink(line);
            try { File.AppendAllText(_path, line + Environment.NewLine, Encoding.UTF8); }
            catch (IOException) { }
        }
    }

    /// <summary>Súbory, ktoré sa majú dostať do cieľa. Pri hotovej inštalačke sú
    /// v nej samej ako zazipovaný prostriedok, pri vývoji v priečinku (--payload).
    /// Zip sa rozbaľuje rovno do cieľa, nie najprv do dočasného priečinka –
    /// ušetrí to jedno prekopírovanie stoviek megabajtov.</summary>
    internal sealed class Payload
    {
        public const string Resource = "payload.zip";

        private readonly string _directory;             // null = vnorený v exe

        private Payload(string directory)
        {
            _directory = directory;
        }

        public static Payload Embedded() { return new Payload(null); }
        public static Payload FromDirectory(string directory) { return new Payload(directory); }

        public string Describe()
        {
            return _directory ?? "payload v inštalačke";
        }

        public string ReadText(string relative)
        {
            if (_directory != null)
                return File.ReadAllText(Path.Combine(_directory, relative.Replace('/', '\\')), Encoding.UTF8);

            using (Stream stream = Open())
            using (ZipArchive archive = new ZipArchive(stream, ZipArchiveMode.Read))
            {
                // .NET Framework zapisuje položky zipu so spätnou lomkou, hoci
                // norma velí lomku dopredu – hľadá sa teda bez ohľadu na ňu.
                string hladane = relative.Replace('\\', '/');
                foreach (ZipArchiveEntry entry in archive.Entries)
                    if (string.Equals(entry.FullName.Replace('\\', '/'), hladane, StringComparison.OrdinalIgnoreCase))
                        using (StreamReader reader = new StreamReader(entry.Open(), Encoding.UTF8))
                            return reader.ReadToEnd();
                throw new FileNotFoundException("V inštalačke chýba " + relative);
            }
        }

        public void DeployTo(string target)
        {
            if (_directory != null)
            {
                if (string.Equals(Path.GetFullPath(_directory).TrimEnd('\\'),
                                  Path.GetFullPath(target).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
                    return;                             // payload už leží v cieli
                CopyTree(_directory, target);
                return;
            }

            using (Stream stream = Open())
            using (ZipArchive archive = new ZipArchive(stream, ZipArchiveMode.Read))
                foreach (ZipArchiveEntry entry in archive.Entries)
                {
                    string path = Path.Combine(target, entry.FullName.Replace('/', '\\').Replace("\\\\", "\\"));
                    if (entry.Name.Length == 0)         // samotný priečinok
                    {
                        Directory.CreateDirectory(path);
                        continue;
                    }
                    Directory.CreateDirectory(Path.GetDirectoryName(path));
                    entry.ExtractToFile(path, true);
                }
        }

        private static void CopyTree(string from, string to)
        {
            Directory.CreateDirectory(to);
            foreach (string directory in Directory.GetDirectories(from, "*", SearchOption.AllDirectories))
                Directory.CreateDirectory(directory.Replace(from, to));
            foreach (string file in Directory.GetFiles(from, "*", SearchOption.AllDirectories))
                File.Copy(file, file.Replace(from, to), true);
        }

        private static Stream Open()
        {
            Stream stream = typeof(Payload).Assembly.GetManifestResourceStream(Resource);
            if (stream == null)
                throw new FileNotFoundException(
                    "Inštalačka neobsahuje súbory aplikácie. Stiahni ju znova.");
            return stream;
        }

    }

    internal sealed class InstallException : Exception
    {
        public readonly bool CanFallBack;

        public InstallException(string message, bool canFallBack = false) : base(message)
        {
            CanFallBack = canFallBack;
        }
    }

    internal sealed class Installer
    {
        public const string UninstallKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\FUKAI";

        private readonly Manifest _manifest;
        private readonly string _target;
        private readonly Payload _payload;
        private readonly Log _log;
        private readonly bool _desktopShortcut;
        private string _temp;

        public Installer(Manifest manifest, string target, Payload payload, Log log, bool desktopShortcut)
        {
            _manifest = manifest;
            _target = target;
            _payload = payload;
            _log = log;
            _desktopShortcut = desktopShortcut;
        }

        private string Installer_ { get { return Path.Combine(_target, "installer"); } }
        private string EnvDir { get { return Path.Combine(_target, "env"); } }
        private string EnvPython { get { return Path.Combine(EnvDir, "Scripts", "python.exe"); } }
        private string AppDir { get { return Path.Combine(_target, "app"); } }
        private string Uv { get { return Path.Combine(Installer_, "uv.exe"); } }

        public string Run(Backend chosen)
        {
            _temp = Path.Combine(Path.GetTempPath(), "fukai-install-" + Guid.NewGuid().ToString("N").Substring(0, 8));
            Directory.CreateDirectory(_temp);
            try
            {
                CopyPayload();
                DeleteTree(Path.Combine(_target, "python"));
                _log.Write("Inštalujem Python " + _manifest.Python);
                Uvx("python install --no-bin " + _manifest.Python, "Python sa nepodarilo nainštalovať.");

                BackendSpec spec = _manifest.Backend(chosen == Backend.Cuda ? "cuda" : "cpu");
                string backend;
                try
                {
                    backend = Provision(spec);
                }
                catch (InstallException exc)
                {
                    if (!exc.CanFallBack || spec.Fallback == null)
                        throw;
                    _log.Write("Backend " + spec.Name + " v tomto počítači nebeží: " + exc.Message);
                    _log.Write("Inštalujem zálohu: " + spec.Fallback);
                    backend = Provision(_manifest.Backend(spec.Fallback));
                }
                CreateShortcuts();
                RegisterUninstall();
                return backend;
            }
            catch (InstallException)
            {
                TryDelete(EnvDir);
                throw;
            }
            finally
            {
                TryDelete(_temp);
                TryDelete(Installer_);
            }
        }

        private void CreateShortcuts()
        {
            string exe = Path.Combine(_target, "FUKAI.exe");
            Shortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), "FUKAI.lnk"), exe);
            if (_desktopShortcut)
                Shortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "FUKAI.lnk"), exe);
        }

        private void Shortcut(string path, string exe)
        {
            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                object shell = Activator.CreateInstance(shellType);
                object link = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { path });
                Type linkType = link.GetType();
                linkType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, link, new object[] { exe });
                linkType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, link, new object[] { _target });
                linkType.InvokeMember("IconLocation", BindingFlags.SetProperty, null, link, new object[] { exe + ",0" });
                linkType.InvokeMember("Description", BindingFlags.SetProperty, null, link, new object[] { "FUKAI" });
                linkType.InvokeMember("Save", BindingFlags.InvokeMethod, null, link, null);
                _log.Write("Zástupca " + path);
            }
            catch (Exception exc)
            {
                _log.Write("Zástupcu " + path + " sa nepodarilo vytvoriť: " + exc.Message);
            }
        }

        private void RegisterUninstall()
        {
            try
            {
                using (RegistryKey key = Microsoft.Win32.Registry.CurrentUser.CreateSubKey(UninstallKey))
                {
                    key.SetValue("DisplayName", "FUKAI");
                    key.SetValue("DisplayVersion", _manifest.AppVersion);
                    key.SetValue("Publisher", "Lukáš Vavro");
                    key.SetValue("DisplayIcon", Path.Combine(_target, "FUKAI.exe"));
                    key.SetValue("InstallLocation", _target);
                    key.SetValue("UninstallString", Quote(Path.Combine(_target, "uninstall.exe")));
                    key.SetValue("EstimatedSize", SizeKb(), RegistryValueKind.DWord);
                    key.SetValue("NoModify", 1, RegistryValueKind.DWord);
                    key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
                }
                _log.Write("Zapísané do Nastavenia → Aplikácie");
            }
            catch (Exception exc)
            {
                _log.Write("Záznam v Nastaveniach sa nepodarilo vytvoriť: " + exc.Message);
            }
        }

        private int SizeKb()
        {
            long total = 0;
            foreach (string file in Directory.GetFiles(_target, "*", SearchOption.AllDirectories))
            {
                try { total += new FileInfo(file).Length; }
                catch (IOException) { }
            }
            return (int)(total / 1024);
        }

        private void CopyPayload()
        {
            _log.Write("Rozbaľujem súbory aplikácie do " + _target);
            _payload.DeployTo(_target);
        }

        private string Provision(BackendSpec spec)
        {
            _log.Write("Backend " + spec.Name);
            string wheel = DownloadWheel(spec);

            DeleteTree(EnvDir);
            Uvx("venv --python " + _manifest.Python + " " + Quote(EnvDir), "Prostredie aplikácie sa nepodarilo vytvoriť.");
            if (!File.Exists(EnvPython))
                throw new InstallException("Prostredie aplikácie nemá interpreter Pythonu.");

            _log.Write("Inštalujem balíky zo zámku " + spec.Lock);
            Uvx("pip install --python " + Quote(EnvPython) + " --require-hashes --compile-bytecode -r "
                + Quote(Path.Combine(Installer_, spec.Lock.Replace('/', '\\'))),
                "Balíky sa nepodarilo nainštalovať. Skontroluj pripojenie na internet a spusti inštaláciu znova.");
            Uvx("pip install --python " + Quote(EnvPython) + " --no-deps --compile-bytecode " + Quote(wheel),
                "llama-cpp-python sa nepodarilo nainštalovať.");

            Run(EnvPython, "-m compileall -q " + Quote(AppDir), "Zdrojový kód aplikácie sa nepodarilo preložiť.", false);

            return BackendTest(spec);
        }

        private string DownloadWheel(BackendSpec spec)
        {
            string url = _manifest.Releases + "/" + spec.WheelRelease + "/" + spec.WheelFile;
            string path = Path.Combine(_temp, spec.WheelFile);
            _log.Write("Sťahujem " + url);
            try
            {
                ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
                using (WebClient client = new WebClient())
                    client.DownloadFile(url, path);
            }
            catch (WebException exc)
            {
                throw new InstallException(
                    "Súbor sa nepodarilo stiahnuť. Skontroluj pripojenie na internet a spusti inštaláciu znova. ("
                    + exc.Message + ")");
            }

            string hash = Sha256(path);
            if (!string.Equals(hash, spec.WheelSha256, StringComparison.OrdinalIgnoreCase))
                throw new InstallException("Stiahnutý súbor " + spec.WheelFile + " je poškodený. Spusti inštaláciu znova.");
            return path;
        }

        private string BackendTest(BackendSpec spec)
        {
            _log.Write("Test backendu");
            string output = Run(EnvPython, Quote(Path.Combine(Installer_, "backend_test.py")) + " " + Quote(AppDir),
                                "Test backendu zlyhal.", true);
            _log.Write(output.Trim());

            string backend;
            try
            {
                Dictionary<string, object> result = (Dictionary<string, object>)
                    new JavaScriptSerializer().DeserializeObject(output.Trim());
                backend = Convert.ToString(result["backend"], CultureInfo.InvariantCulture);
            }
            catch (Exception)
            {
                throw new InstallException("Testu backendu sa nedá rozumieť.", true);
            }

            if (!string.Equals(backend, spec.Name, StringComparison.OrdinalIgnoreCase))
                throw new InstallException("Engine nebeží na " + spec.Name + ", ale na " + backend + ".", true);
            return backend;
        }

        private void Uvx(string arguments, string error)
        {
            Run(Uv, arguments, error, false);
        }

        private string Run(string exe, string arguments, string error, bool canFallBack)
        {
            ProcessStartInfo info = new ProcessStartInfo(exe, arguments);
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.RedirectStandardOutput = true;
            info.RedirectStandardError = true;
            info.StandardOutputEncoding = Encoding.UTF8;
            info.StandardErrorEncoding = Encoding.UTF8;
            info.EnvironmentVariables["UV_NO_CONFIG"] = "1";
            info.EnvironmentVariables["UV_NO_PROGRESS"] = "1";
            info.EnvironmentVariables["UV_LINK_MODE"] = "copy";
            info.EnvironmentVariables["UV_PYTHON_PREFERENCE"] = "only-managed";
            info.EnvironmentVariables["UV_PYTHON_INSTALL_DIR"] = Path.Combine(_target, "python");
            info.EnvironmentVariables["UV_CACHE_DIR"] = Path.Combine(_temp, "cache");
            info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

            StringBuilder output = new StringBuilder();
            StringBuilder errors = new StringBuilder();
            try
            {
                using (Process process = new Process())
                {
                    process.StartInfo = info;
                    process.OutputDataReceived += (sender, e) => { if (e.Data != null) output.AppendLine(e.Data); };
                    process.ErrorDataReceived += (sender, e) => { if (e.Data != null) errors.AppendLine(e.Data); };
                    process.Start();
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    process.WaitForExit();
                    if (process.ExitCode != 0)
                    {
                        string detail = errors.Length > 0 ? errors.ToString() : output.ToString();
                        _log.Write(detail.Trim());
                        throw new InstallException(error, canFallBack);
                    }
                }
            }
            catch (System.ComponentModel.Win32Exception exc)
            {
                throw new InstallException(error + " (" + exc.Message + ")", canFallBack);
            }
            return output.ToString();
        }


        private static void DeleteTree(string path)
        {
            for (int attempt = 0; ; attempt++)
            {
                if (!Directory.Exists(path))
                    return;
                try
                {
                    Directory.Delete(Long(path), true);
                    return;
                }
                catch (Exception exc)
                {
                    if (attempt >= 4)
                        throw new InstallException(
                            "Priečinok " + path + " sa nepodarilo zmazať (" + exc.Message +
                            "). Zavri bežiaci FUKAI a spusti inštaláciu znova.");
                    System.Threading.Thread.Sleep(500);
                }
            }
        }

        private static void TryDelete(string path)
        {
            try
            {
                if (path != null && Directory.Exists(path))
                    Directory.Delete(Long(path), true);
            }
            catch (Exception)
            {
            }
        }

        private static string Long(string path)
        {
            string full = Path.GetFullPath(path);
            return full.StartsWith(@"\\", StringComparison.Ordinal) ? full : @"\\?\" + full;
        }

        private static string Sha256(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }

        private static string Quote(string text)
        {
            return "\"" + text + "\"";
        }
    }
    internal static class Program
    {
        private const uint ATTACH_PARENT_PROCESS = 0xFFFFFFFF;

        [DllImport("kernel32.dll")]
        private static extern bool AttachConsole(uint processId);

        [STAThread]
        private static int Main(string[] args)
        {
            AppContext.SetSwitch("Switch.System.IO.UseLegacyPathHandling", false);
            AppContext.SetSwitch("Switch.System.IO.BlockLongPaths", false);

            List<string> rest = new List<string>(args);
            bool detectOnly = rest.Remove("--detect");
            bool console = rest.Remove("--console") || detectOnly;
            bool desktopShortcut = !rest.Remove("--no-desktop");
            string payloadDir = TakeOption(rest, "--payload");
            Payload payload = payloadDir == null ? Payload.Embedded() : Payload.FromDirectory(payloadDir);
            string target = TakeOption(rest, "--target") ?? Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "FUKAI");

            // Okno je predvolené, ale exe je WinExe a vlastnú konzolu nemá – pri
            // spustení z terminálu sa treba pripojiť na tú jeho, inak výpis zmizne.
            if (console)
            {
                AttachConsole(ATTACH_PARENT_PROCESS);
                Console.OutputEncoding = Encoding.UTF8;
            }

            Manifest manifest;
            try
            {
                manifest = Manifest.Parse(payload.ReadText("installer/manifest.json"));
            }
            catch (Exception exc)
            {
                string message = "Manifest sa nepodarilo načítať: " + payload.Describe() + "\n" + exc.Message;
                if (console) Console.Error.WriteLine(message);
                else MessageBox.Show(message, "FUKAI", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 2;
            }

            Detection detection = Detector.Detect(manifest);

            if (!console)
            {
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                Application.Run(new SetupForm(manifest, detection, payload, target));
                return 0;
            }

            Report(manifest, detection);
            if (detection.Blocker != null) return 1;
            if (detectOnly) return 0;

            Log log = new Log(Path.Combine(target, "install.log"), Console.WriteLine);
            log.Write("Inštalácia FUKAI " + manifest.AppVersion + " do " + target);
            foreach (string note in detection.Notes)
                log.Write("upozornenie: " + note);
            try
            {
                string backend = new Installer(manifest, target, payload, log, desktopShortcut).Run(detection.Backend);
                log.Write("Hotovo, backend " + backend);
                return 0;
            }
            catch (InstallException exc)
            {
                log.Write("CHYBA: " + exc.Message);
                return 3;
            }
            catch (Exception exc)
            {
                log.Write("CHYBA: " + exc);
                return 3;
            }
        }

        private static void Report(Manifest manifest, Detection detection)
        {
            Console.WriteLine("FUKAI {0} · Python {1}", manifest.AppVersion, manifest.Python);
            Console.WriteLine("Windows zostava : {0} (minimum {1})", detection.OsBuild, manifest.WindowsBuild);

            if (detection.Avx2.HasValue)
                Console.WriteLine("AVX2            : {0}", detection.Avx2.Value ? "áno" : "nie");
            if (detection.GpuChecked)
                Console.WriteLine("GPU             : {0}", detection.GpuName ?? "žiadna NVIDIA");
            if (detection.DriverVersion != null)
                Console.WriteLine("ovládač         : {0} (minimum {1})", detection.DriverVersion, manifest.CudaDriver);
            if (detection.ComputeCapability != null)
                Console.WriteLine("compute cap.    : {0} (minimum {1})", detection.ComputeCapability, manifest.CudaComputeCapability);
            if (detection.VramMb > 0)
                Console.WriteLine("VRAM            : {0} MB", detection.VramMb);
            if (detection.Blocker != null)
            {
                Console.WriteLine();
                Console.WriteLine("NEDÁ SA INŠTALOVAŤ: " + detection.Blocker);
                return;
            }

            Console.WriteLine();
            Console.WriteLine("BACKEND: {0}", detection.Backend.ToString().ToUpperInvariant());
            foreach (string note in detection.Notes) Console.WriteLine(" upozornenie: " + note);
            Console.WriteLine();
        }

        private static string TakeOption(List<string> args, string name)
        {
            int index = args.IndexOf(name);
            if (index < 0 || index + 1 >= args.Count) return null;
            string value = args[index + 1];
            args.RemoveRange(index, 2);
            return value;
        }
    }
}
