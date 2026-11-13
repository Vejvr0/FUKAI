/*
 * Rozloženie bundlu:
 *   Contents/MacOS/FUKAI              tento program
 *   Contents/Resources/python/...     Python z uv (libpython3.12.dylib)
 *   Contents/Resources/env/           prostredie appky (pyvenv.cfg)
 *   Contents/Resources/app/main.py    zdrojáky FUKAI
 */


#include <Python.h>
#include <CoreFoundation/CoreFoundation.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void alert(const char *message, const char *detail) {
    CFStringRef title = CFStringCreateWithCString(NULL, message, kCFStringEncodingUTF8);
    CFStringRef text = CFStringCreateWithCString(NULL, detail, kCFStringEncodingUTF8);
    CFUserNotificationDisplayAlert(0, kCFUserNotificationStopAlertLevel, NULL, NULL, NULL, title, text, NULL, NULL, NULL, NULL);
    CFRelease(title);
    CFRelease(text);
}

static int contents_dir(char *out, size_t size) {
    char exe[PATH_MAX], real[PATH_MAX];
    uint32_t length = sizeof(exe);
    if (_NSGetExecutablePath(exe, &length) != 0 || realpath(exe, real) == NULL) {
        return -1;
    }
    for (int i = 0; i < 2; i++) {
        char *slash = strrchr(real, '/');
        if (slash == NULL) {
            return -1;
        }
        *slash = '\0';
    }
    return snprintf(out, size, "%s", real) < (int)size ? 0 : -1;
}

int main(int argc, char **argv) {
    char contents[PATH_MAX], python[PATH_MAX], script[PATH_MAX];
    if (contents_dir(contents, sizeof(contents)) != 0) {
        alert("FUKAI sa nepodarilo spustiť.", "Nedá sa zistiť umiestnenie aplikácie.");
        return 1;
    }
    snprintf(python, sizeof(python), "%s/Resources/env/bin/python3", contents);
    snprintf(script, sizeof(script), "%s/Resources/app/main.py", contents);
    if (access(python, X_OK) != 0 || access(script, R_OK) != 0) {
        alert("FUKAI nie je nainštalovaný úplne.", "Spusti inštaláciu FUKAI znova.");
        return 1;
    }

    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.parse_argv = 0;
    PyStatus status = PyConfig_SetBytesString(&config, &config.program_name, python);
    if (!PyStatus_Exception(status)) status = PyConfig_SetBytesString(&config, &config.run_filename, script);
    if (!PyStatus_Exception(status)) {
        argv[0] = script;
        status = PyConfig_SetBytesArgv(&config, argc, argv);
    }
    if (!PyStatus_Exception(status)) status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)){
        alert("FUKAI sa nepodarilo spustiť.", status.err_msg ? status.err_msg : "Python sa nepodarilo inicializovať.");
        Py_ExitStatusException(status);
    }
    return Py_RunMain();
}
