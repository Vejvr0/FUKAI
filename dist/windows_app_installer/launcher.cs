/*
 * Rozloženie inštalácie (%LOCALAPPDATA%\Programs\FUKAI):
 *   FUKAI.exe       tento program
 *   python\...      Python z uv (pythonXYZ.dll)
 *   env\            prostredie appky (pyvenv.cfg)
 *   app\main.py     zdrojáky FUKAI
 */

using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;

[assembly: AssemblyTitle("FUKAI")]
[assembly: AssemblyProduct("FUKAI")]
[assembly: AssemblyDescription("FUKAI")]
[assembly: AssemblyCompany("Lukas Vavro")]
[assembly: AssemblyCopyright("Copyright (C) 2026 Lukas Vavro")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace Fukai
{
    internal static class Program
    {
        private const string AppName = "FUKAI";
        private const string NotInstalled = "FUKAI nie je nainštalovaný úplne. Spusti inštaláciu FUKAI znova.";
        private const uint MB_OK = 0x0;
        private const uint MB_ICONERROR = 0x10;
        private const uint LOAD_WITH_ALTERED_SEARCH_PATH = 0x8;

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int MessageBoxW(IntPtr hWnd, string text, string caption, uint type);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr LoadLibraryExW(string fileName, IntPtr file, uint flags);

        [DllImport("kernel32.dll", CharSet = CharSet.Ansi, SetLastError = true, BestFitMapping = false)]
        private static extern IntPtr GetProcAddress(IntPtr module, string name);

        [UnmanagedFunctionPointer(CallingConvention.Cdecl, CharSet = CharSet.Unicode)]
        private delegate void SetProgramNameFn([MarshalAs(UnmanagedType.LPWStr)] string name);

        [UnmanagedFunctionPointer(CallingConvention.Cdecl, CharSet = CharSet.Unicode)]
        private delegate int MainFn(int argc, [In, MarshalAs(UnmanagedType.LPArray, ArraySubType = UnmanagedType.LPWStr)] string[] argv);

        [STAThread]
        private static int Main(string[] args)
        {
            try
            {
                return Run(args);
            }
            catch (Exception exc)
            {
                return Fail(exc.Message);
            }
        }

        private static int Run(string[] args)
        {
            string root = Path.GetDirectoryName(typeof(Program).Assembly.Location);
            string app = Path.Combine(root, "app");
            string mainPy = Path.Combine(app, "main.py");
            string pythonw = Path.Combine(root, "env", "Scripts", "pythonw.exe");
            string pyvenvCfg = Path.Combine(root, "env", "pyvenv.cfg");

            if (!File.Exists(mainPy) || !File.Exists(pythonw) || !File.Exists(pyvenvCfg)) return Fail();

            string pythonDll = FindPythonDll(pyvenvCfg);
            if (pythonDll == null) return Fail();

            IntPtr module = LoadLibraryExW(pythonDll, IntPtr.Zero, LOAD_WITH_ALTERED_SEARCH_PATH);
            if (module == IntPtr.Zero) return Fail("LoadLibraryEx: " + Marshal.GetLastWin32Error());

            SetProgramNameFn setProgramName = GetFunction<SetProgramNameFn>(module, "Py_SetProgramName");

            MainFn pyMain = GetFunction<MainFn>(module, "Py_Main");
            if (setProgramName == null || pyMain == null) return Fail();

            Environment.SetEnvironmentVariable("PYTHONHOME", null);
            Environment.SetEnvironmentVariable("PYTHONPATH", null);
            Directory.SetCurrentDirectory(app);

            setProgramName(pythonw);
            string[] argv = new[] { pythonw, mainPy }.Concat(args).ToArray();
            return pyMain(argv.Length, argv);
        }

        private static T GetFunction<T>(IntPtr module, string name) where T : class
        {
            IntPtr address = GetProcAddress(module, name);
            return address == IntPtr.Zero ? null : Marshal.GetDelegateForFunctionPointer(address, typeof(T)) as T;
        }

        private static string FindPythonDll(string pyvenvCfg)
        {
            string home = null;
            foreach (string line in File.ReadAllLines(pyvenvCfg))
            {
                Match match = Regex.Match(line, @"^\s*home\s*=\s*(.+?)\s*$");
                if (match.Success)
                {
                    home = match.Groups[1].Value;
                    break;
                }
            }
            if (home == null || !Directory.Exists(home))
                return null;
            return Directory.GetFiles(home, "python3??.dll").FirstOrDefault();
        }

        private static int Fail(string detail = null)
        {
            string text = detail == null ? NotInstalled : NotInstalled + "\n\n" + detail;
            MessageBoxW(IntPtr.Zero, text, AppName, MB_OK | MB_ICONERROR);
            return 1;
        }
    }
}
