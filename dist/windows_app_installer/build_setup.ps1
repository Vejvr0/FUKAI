# --- ./dist/windows_app_installer/build_setup.ps1 ---
# setup.exe builder

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$HERE = Split-Path -Parent $MyInvocation.MyCommand.Path
$DIST = Split-Path -Parent $HERE
$ROOT = Split-Path -Parent $DIST
$OUT = Join-Path $DIST 'out'
$CSC = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'

function Krok($text) { Write-Host "==> $text" }
function Chyba($text) { Write-Host "CHYBA: $text" -ForegroundColor Red; exit 1 }

if (-not (Test-Path $CSC)) { Chyba "csc.exe sa nenašiel: $CSC" }

# --- manifest a kontrola verzie ---
$manifest = Get-Content (Join-Path $DIST 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$verzia = $manifest.app_version

$constants = Get-Content (Join-Path $ROOT 'core\constants.py') -Raw -Encoding UTF8
if ($constants -notmatch 'APP_VERSION\s*=\s*"([^"]+)"') { Chyba 'APP_VERSION sa v core/constants.py nenašla.' }
if ($Matches[1] -ne $verzia) {
    Chyba "Verzia v manifeste ($verzia) a v core/constants.py ($($Matches[1])) sa nezhodujú."
}
Krok "FUKAI $verzia"

# --- temp priečinok ---
$TMP = Join-Path ([System.IO.Path]::GetTempPath()) ("fukai-build-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$PAYLOAD = Join-Path $TMP 'payload'
New-Item -ItemType Directory -Force $PAYLOAD | Out-Null
New-Item -ItemType Directory -Force (Join-Path $PAYLOAD 'installer\locks') | Out-Null
New-Item -ItemType Directory -Force $OUT | Out-Null

try {
    # --- uv podľa manifestu ---
    Krok "Sťahujem uv $($manifest.uv.version)"
    $uvZip = Join-Path $TMP 'uv.zip'
    Invoke-WebRequest $manifest.uv.windows.url -OutFile $uvZip
    $hash = (Get-FileHash $uvZip -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne $manifest.uv.windows.sha256) { Chyba "uv má iný SHA-256, než hovorí manifest." }
    Expand-Archive $uvZip -DestinationPath (Join-Path $TMP 'uv') -Force

    # --- spúšťač a odinštalovanie ---
    $ikona = Join-Path $ROOT 'assets\ico\fukai.ico'
    Krok 'Prekladám FUKAI.exe'
    & $CSC /nologo /target:winexe /platform:x64 /optimize+ /warnaserror+ `
        "/win32icon:$ikona" "/out:$(Join-Path $PAYLOAD 'FUKAI.exe')" `
        "$(Join-Path $HERE 'launcher.cs')"
    if ($LASTEXITCODE -ne 0) { Chyba 'FUKAI.exe sa nepodarilo preložiť.' }

    Krok 'Prekladám uninstall.exe'
    & $CSC /nologo /target:winexe /platform:x64 /optimize+ /warnaserror+ `
        /r:System.Windows.Forms.dll "/win32icon:$ikona" `
        "/out:$(Join-Path $PAYLOAD 'uninstall.exe')" "$(Join-Path $HERE 'uninstall.cs')"
    if ($LASTEXITCODE -ne 0) { Chyba 'uninstall.exe sa nepodarilo preložiť.' }

    # --- zdrojové kódy aplikácie ---
    Krok 'Zbieram zdrojáky aplikácie'
    Push-Location $ROOT
    $subory = & git ls-files | Where-Object { $_ -notmatch '^(dist|archiv)/' }
    Pop-Location
    if (-not $subory) { Chyba 'git ls-files nevrátil nič – stojíš mimo repa?' }
    foreach ($s in $subory) {
        $ciel = Join-Path (Join-Path $PAYLOAD 'app') ($s -replace '/', '\')
        $priecinok = Split-Path $ciel
        if (-not (Test-Path $priecinok)) { New-Item -ItemType Directory -Force $priecinok | Out-Null }
        Copy-Item (Join-Path $ROOT ($s -replace '/', '\')) $ciel -Force
    }

    # --- veci pre inštaláciu ---
    Copy-Item (Join-Path $TMP 'uv\uv.exe') (Join-Path $PAYLOAD 'installer') -Force
    Copy-Item (Join-Path $DIST 'manifest.json') (Join-Path $PAYLOAD 'installer') -Force
    Copy-Item (Join-Path $DIST 'backend_test.py') (Join-Path $PAYLOAD 'installer') -Force
    Copy-Item (Join-Path $DIST 'locks\win-cuda.txt') (Join-Path $PAYLOAD 'installer\locks') -Force
    Copy-Item (Join-Path $DIST 'locks\win-cpu.txt') (Join-Path $PAYLOAD 'installer\locks') -Force

    # --- Visual C++ runtime ---
    Krok 'Pribaľujem Visual C++ runtime'
    $redist = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Redist\MSVC'
    if (-not (Test-Path $redist)) { Chyba "VC++ redist sa nenašiel: $redist" }
    $rv = (Get-ChildItem $redist -Directory | Where-Object { $_.Name -match '^\d+\.' } |
           Sort-Object Name -Descending | Select-Object -First 1).Name
    Copy-Item (Join-Path $redist "$rv\x64\Microsoft.VC143.CRT\*.dll") $PAYLOAD -Force
    Copy-Item (Join-Path $redist "$rv\x64\Microsoft.VC143.OpenMP\*.dll") $PAYLOAD -Force
    foreach ($dll in @('msvcp140.dll', 'vcomp140.dll')) {
        if (-not (Test-Path (Join-Path $PAYLOAD $dll))) { Chyba "V payloade chýba $dll." }
    }

    # --- payload do zipu ---
    Krok 'Balím payload'
    $zip = Join-Path $TMP 'payload.zip'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $PAYLOAD, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $false)

    # --- inštalačka ---
    Krok 'Prekladám setup.exe'
    $exe = Join-Path $OUT "FUKAI-Setup-$verzia.exe"
    & $CSC /nologo /target:winexe /platform:x64 /optimize+ /warnaserror+ `
        /r:System.Management.dll /r:System.Web.Extensions.dll `
        /r:System.Windows.Forms.dll /r:System.Drawing.dll `
        /r:System.IO.Compression.dll /r:System.IO.Compression.FileSystem.dll `
        "/win32icon:$ikona" "/win32manifest:$(Join-Path $HERE 'setup.manifest')" `
        "/resource:$zip,payload.zip" "/out:$exe" `
        "$(Join-Path $HERE 'setup.cs')" "$(Join-Path $HERE 'setup_form.cs')"
    if ($LASTEXITCODE -ne 0) { Chyba 'setup.exe sa nepodarilo preložiť.' }

    $mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Krok "Hotovo: $exe ($mb MB)"
    Write-Host ("SHA-256: " + (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower())
}
finally {
    if (Test-Path $TMP) { Remove-Item $TMP -Recurse -Force -ErrorAction SilentlyContinue }
}
