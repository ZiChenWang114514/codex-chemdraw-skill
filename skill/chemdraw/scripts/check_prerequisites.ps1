<# Read-only host and runtime prerequisite report for the ChemDraw Skill. #>
[CmdletBinding()]
param(
    [string]$Python,
    [switch]$Json,
    [switch]$SkipCodex,
    [switch]$SkipChemDraw,
    [switch]$SkipPythonPackages
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)

$checks = [Collections.Generic.List[object]]::new()
$nextSteps = [Collections.Generic.List[string]]::new()

function Add-Check {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][ValidateSet('pass', 'warning', 'fail', 'skipped')]
        [string]$Status,
        [Parameter(Mandatory)][bool]$Required,
        [Parameter(Mandatory)][string]$Detail,
        [string]$Help = ''
    )

    $checks.Add([pscustomobject][ordered]@{
        name = $Name
        status = $Status
        required = $Required
        detail = $Detail
        help = $Help
    })
}

function Add-NextStep {
    param([Parameter(Mandatory)][string]$Text)

    if (-not $nextSteps.Contains($Text)) {
        $nextSteps.Add($Text)
    }
}

function Get-CommandPath {
    param([Parameter(Mandatory)][string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $command) { return $null }
    $pathProperty = $command.PSObject.Properties['Path']
    if ($pathProperty -and $pathProperty.Value) {
        return [string]$pathProperty.Value
    }
    $sourceProperty = $command.PSObject.Properties['Source']
    if ($sourceProperty -and $sourceProperty.Value) {
        return [string]$sourceProperty.Value
    }
    return [string]$command.Name
}

function Invoke-Captured {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments
    )

    try {
        $output = @(& $FilePath @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) { $exitCode = 0 }
        return [pscustomobject]@{
            ExitCode = [int]$exitCode
            Output = (($output | ForEach-Object { [string]$_ }) -join "`n").Trim()
        }
    } catch {
        return [pscustomobject]@{
            ExitCode = -1
            Output = $_.Exception.Message
        }
    }
}

function Get-RegistryDefaultValue {
    param([Parameter(Mandatory)][string]$LiteralPath)

    try {
        $item = Get-Item -LiteralPath $LiteralPath -ErrorAction Stop
        return $item.GetValue('')
    } catch {
        return $null
    }
}

function Get-ExecutableFromCommandLine {
    param([string]$CommandLine)

    if (-not $CommandLine) { return $null }
    $expanded = [Environment]::ExpandEnvironmentVariables($CommandLine).Trim()
    if ($expanded -match '^"([^"]+\.exe)"') { return $matches[1] }
    if ($expanded -match '^(.+?\.exe)(?:\s|$)') { return $matches[1].Trim() }
    return $null
}

$isWindowsHost = $env:OS -eq 'Windows_NT'
$isSupportedWindows = $isWindowsHost -and `
    [Environment]::Is64BitOperatingSystem -and `
    [Environment]::OSVersion.Version.Major -ge 10
if ($isSupportedWindows) {
    Add-Check -Name 'windows' -Status 'pass' -Required $true `
        -Detail ("{0}; 64-bit OS" -f [Environment]::OSVersion.VersionString) `
        -Help 'Use 64-bit Windows 10 or Windows 11.'
} else {
    Add-Check -Name 'windows' -Status 'fail' -Required $true `
        -Detail 'This project requires 64-bit Windows 10 or Windows 11 for ChemDraw COM automation.' `
        -Help 'Run the server on a Windows 10 or Windows 11 computer with desktop ChemDraw.'
    Add-NextStep 'Move the installation to a supported 64-bit Windows computer.'
}

$powerShellVersion = $PSVersionTable.PSVersion
$powerShellSupported = $powerShellVersion -ge [version]'5.1'
Add-Check -Name 'powershell' `
    -Status $(if ($powerShellSupported) { 'pass' } else { 'fail' }) `
    -Required $true `
    -Detail ("PowerShell {0}" -f $powerShellVersion) `
    -Help 'Windows PowerShell 5.1 or PowerShell 7 is supported.'
if (-not $powerShellSupported) {
    Add-NextStep 'Install PowerShell 7, reopen the terminal, and run this check again.'
}

$gitPath = Get-CommandPath 'git'
if ($gitPath) {
    $gitVersion = Invoke-Captured -FilePath $gitPath -Arguments @('--version')
    Add-Check -Name 'git' -Status 'pass' -Required $false `
        -Detail $(if ($gitVersion.Output) { $gitVersion.Output } else { $gitPath }) `
        -Help 'Git is used to clone and update the repository.'
} else {
    Add-Check -Name 'git' -Status 'warning' -Required $false `
        -Detail 'Git was not found. A GitHub ZIP download can be used instead.' `
        -Help 'Install Git for Windows from https://git-scm.com/install/windows.'
    Add-NextStep 'Install Git for Windows, or download the repository ZIP from GitHub.'
}

$condaCommand = Get-Command 'conda' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($condaCommand) {
    $condaPath = Get-CommandPath 'conda'
    $isShellCommand = [string]$condaCommand.CommandType -in @('Alias', 'Filter', 'Function')
    if ($isShellCommand) {
        $condaDetail = "Conda is registered as a PowerShell $([string]$condaCommand.CommandType)."
    } else {
        $condaVersion = Invoke-Captured -FilePath $condaPath -Arguments @('--version')
        $condaDetail = if ($condaVersion.Output) { $condaVersion.Output } else { $condaPath }
    }
    Add-Check -Name 'conda' -Status 'pass' -Required $false `
        -Detail $condaDetail `
        -Help 'A dedicated Conda environment is the recommended Python setup.'
} else {
    Add-Check -Name 'conda' -Status 'warning' -Required $false `
        -Detail 'Conda was not found. An existing compatible Python can still be supplied explicitly.' `
        -Help 'Install 64-bit Miniconda from https://docs.conda.io/projects/conda/en/stable/user-guide/install/windows.html.'
    Add-NextStep 'Install 64-bit Miniconda if you do not already manage isolated Python environments.'
}

$pythonPath = $null
$pythonProblem = $null
if ($Python) {
    $candidate = [Environment]::ExpandEnvironmentVariables($Python.Trim().Trim('"'))
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $pythonPath = [IO.Path]::GetFullPath($candidate)
    } else {
        $pythonProblem = "The explicit Python path does not exist: $candidate"
    }
} else {
    $pythonPath = Get-CommandPath 'python'
    if (-not $pythonPath) {
        $pythonProblem = 'Python was not found. Pass -Python with the cdxml environment python.exe.'
    }
}

$pythonReady = $false
if ($pythonPath) {
    $pythonCode = 'import json, platform, struct, sys; print(json.dumps({"version": list(sys.version_info[:3]), "executable": sys.executable, "bits": struct.calcsize("P") * 8, "implementation": platform.python_implementation()}))'
    $pythonProbe = Invoke-Captured -FilePath $pythonPath -Arguments @('-c', $pythonCode)
    if ($pythonProbe.ExitCode -eq 0) {
        try {
            $pythonInfo = $pythonProbe.Output | ConvertFrom-Json
            $major = [int]$pythonInfo.version[0]
            $minor = [int]$pythonInfo.version[1]
            $supportedVersion = $major -eq 3 -and $minor -ge 10 -and $minor -lt 14
            $supportedBits = [int]$pythonInfo.bits -eq 64
            $pythonReady = $supportedVersion -and $supportedBits
            $detail = "{0} {1}.{2}.{3}, {4}-bit, {5}" -f `
                $pythonInfo.implementation,
                $pythonInfo.version[0],
                $pythonInfo.version[1],
                $pythonInfo.version[2],
                $pythonInfo.bits,
                $pythonInfo.executable
            $help = 'Use a 64-bit Python 3.10-3.13 runtime. Python 3.12 is tested.'
            Add-Check -Name 'python_runtime' `
                -Status $(if ($pythonReady) { 'pass' } else { 'fail' }) `
                -Required $true -Detail $detail -Help $help
            if (-not $supportedVersion) {
                Add-NextStep 'Create a new Conda environment with Python 3.12.'
            }
            if (-not $supportedBits) {
                Add-NextStep 'Use 64-bit Python for the main MCP environment; keep any 32-bit ChemScript helper separate.'
            }
        } catch {
            $pythonProblem = "Python returned invalid diagnostic JSON: $($_.Exception.Message)"
        }
    } else {
        $pythonProblem = "Python could not run the diagnostic probe: $($pythonProbe.Output)"
    }
}
if (-not $pythonReady -and -not ($checks | Where-Object { $_.name -eq 'python_runtime' })) {
    Add-Check -Name 'python_runtime' -Status 'fail' -Required $true `
        -Detail $(if ($pythonProblem) { $pythonProblem } else { 'No usable Python runtime was found.' }) `
        -Help 'Create a 64-bit Conda environment with Python 3.12 and pass its python.exe with -Python.'
    Add-NextStep 'Create the recommended Python 3.12 Conda environment, then run this check with -Python.'
}

if ($SkipPythonPackages) {
    Add-Check -Name 'python_packages' -Status 'skipped' -Required $false `
        -Detail 'Python package checks were skipped by request.'
    Add-Check -Name 'pip_dependencies' -Status 'skipped' -Required $false `
        -Detail 'pip dependency consistency was skipped by request.'
} elseif ($pythonReady) {
    $packageCode = @'
import importlib
import importlib.metadata as metadata
import json

modules = {
    "cdxml_toolkit": "cdxml-toolkit",
    "mcp": "mcp",
    "rdkit": "rdkit",
    "win32com.client": "pywin32",
}
result = {}
for module_name, distribution_name in modules.items():
    try:
        importlib.import_module(module_name)
        try:
            version = metadata.version(distribution_name)
        except metadata.PackageNotFoundError:
            version = "unknown"
        result[module_name] = {"ok": True, "version": version}
    except Exception as exc:
        result[module_name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
print(json.dumps(result))
'@
    $packageProbe = Invoke-Captured -FilePath $pythonPath -Arguments @('-c', $packageCode)
    if ($packageProbe.ExitCode -eq 0) {
        try {
            $packageInfo = $packageProbe.Output | ConvertFrom-Json
            $missingPackages = [Collections.Generic.List[string]]::new()
            $versions = [Collections.Generic.List[string]]::new()
            foreach ($property in $packageInfo.PSObject.Properties) {
                if ($property.Value.ok) {
                    $versions.Add("$($property.Name)=$($property.Value.version)")
                } else {
                    $missingPackages.Add("$($property.Name): $($property.Value.error)")
                }
            }
            if ($missingPackages.Count -eq 0) {
                $versionText = ($versions -join ', ')
                $testedVersions = $versionText -match 'cdxml_toolkit=0\.5\.17' -and `
                    $versionText -match 'mcp=2\.0\.0'
                Add-Check -Name 'python_packages' `
                    -Status $(if ($testedVersions) { 'pass' } else { 'warning' }) `
                    -Required $true `
                    -Detail $versionText `
                    -Help 'The tested versions are cdxml-toolkit 0.5.17 and MCP 2.0.0; compatible MCP 1.x installations are also supported.'
            } else {
                Add-Check -Name 'python_packages' -Status 'fail' -Required $true `
                    -Detail ($missingPackages -join '; ') `
                    -Help 'Install mcp==2.0.0 and cdxml-toolkit==0.5.17 into this exact Python environment.'
                Add-NextStep 'Install the tested Python packages into the selected environment.'
            }
        } catch {
            Add-Check -Name 'python_packages' -Status 'fail' -Required $true `
                -Detail "The package probe returned invalid JSON: $($_.Exception.Message)" `
                -Help 'Reinstall the tested package versions in a clean Python 3.12 environment.'
        }
    } else {
        Add-Check -Name 'python_packages' -Status 'fail' -Required $true `
            -Detail $packageProbe.Output `
            -Help 'Install mcp==2.0.0 and cdxml-toolkit==0.5.17 into this exact Python environment.'
        Add-NextStep 'Install the tested Python packages into the selected environment.'
    }

    $pipCheck = Invoke-Captured -FilePath $pythonPath -Arguments @('-m', 'pip', 'check')
    Add-Check -Name 'pip_dependencies' `
        -Status $(if ($pipCheck.ExitCode -eq 0) { 'pass' } else { 'fail' }) `
        -Required $true `
        -Detail $(if ($pipCheck.Output) { $pipCheck.Output } else { 'No broken requirements found.' }) `
        -Help 'Run python -m pip check after package installation.'
    if ($pipCheck.ExitCode -ne 0) {
        Add-NextStep 'Repair the dependency conflicts reported by python -m pip check.'
    }
} else {
    Add-Check -Name 'python_packages' -Status 'skipped' -Required $true `
        -Detail 'Package checks require a supported Python runtime.'
    Add-Check -Name 'pip_dependencies' -Status 'skipped' -Required $true `
        -Detail 'pip dependency checks require a supported Python runtime.'
}

if ($SkipCodex) {
    Add-Check -Name 'codex_cli' -Status 'skipped' -Required $false `
        -Detail 'Codex CLI discovery was skipped by request.'
} else {
    $codexPath = Get-CommandPath 'codex'
    if ($codexPath) {
        $codexVersion = Invoke-Captured -FilePath $codexPath -Arguments @('--version')
        Add-Check -Name 'codex_cli' `
            -Status $(if ($codexVersion.ExitCode -eq 0) { 'pass' } else { 'fail' }) `
            -Required $true `
            -Detail $(if ($codexVersion.Output) { $codexVersion.Output } else { $codexPath }) `
            -Help 'The installer uses codex mcp add to register the server.'
    } else {
        Add-Check -Name 'codex_cli' -Status 'fail' -Required $true `
            -Detail 'The codex command was not found.' `
            -Help 'Install and sign in to Codex using https://developers.openai.com/codex/cli.'
        Add-NextStep 'Install Codex CLI, run codex once, and complete sign-in.'
    }
}

$chemdrawExe = $null
if ($SkipChemDraw) {
    Add-Check -Name 'dotnet_framework' -Status 'skipped' -Required $false `
        -Detail '.NET and ChemDraw checks were skipped by request.'
    Add-Check -Name 'chemdraw_com' -Status 'skipped' -Required $false `
        -Detail 'ChemDraw COM discovery was skipped by request.'
    Add-Check -Name 'chemdraw_activation' -Status 'skipped' -Required $false `
        -Detail 'ChemDraw activation must be checked manually on a native workstation.'
    Add-Check -Name 'chemscript_files' -Status 'skipped' -Required $false `
        -Detail 'ChemScript file discovery was skipped by request.'
} else {
    $dotNetRelease = $null
    try {
        $dotNetRelease = (Get-ItemProperty `
            -LiteralPath 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' `
            -Name Release -ErrorAction Stop).Release
    } catch {
        $dotNetRelease = $null
    }
    $dotNetReady = $dotNetRelease -and [int]$dotNetRelease -ge 528040
    Add-Check -Name 'dotnet_framework' `
        -Status $(if ($dotNetReady) { 'pass' } else { 'fail' }) `
        -Required $true `
        -Detail $(if ($dotNetRelease) { ".NET Framework 4.8-compatible release $dotNetRelease" } else { '.NET Framework 4.8 was not detected.' }) `
        -Help 'ChemDraw 22.0 and later require .NET Framework 4.8 on Windows.'
    if (-not $dotNetReady) {
        Add-NextStep 'Install all Windows updates and .NET Framework 4.8 before installing ChemDraw.'
    }

    $clsid = Get-RegistryDefaultValue `
        'Registry::HKEY_CLASSES_ROOT\ChemDraw.Application\CLSID'
    if ($clsid) {
        $serverCommand = Get-RegistryDefaultValue `
            "Registry::HKEY_CLASSES_ROOT\CLSID\$clsid\LocalServer32"
        $chemdrawExe = Get-ExecutableFromCommandLine ([string]$serverCommand)
    }
    if ($chemdrawExe -and (Test-Path -LiteralPath $chemdrawExe -PathType Leaf)) {
        $chemdrawExe = [IO.Path]::GetFullPath($chemdrawExe)
        Add-Check -Name 'chemdraw_com' -Status 'pass' -Required $true `
            -Detail "ChemDraw.Application is registered: $chemdrawExe" `
            -Help 'The Windows desktop edition is required; the browser-only product cannot provide COM automation.'
    } else {
        Add-Check -Name 'chemdraw_com' -Status 'fail' -Required $true `
            -Detail 'The ChemDraw.Application COM registration was not found or its executable is missing.' `
            -Help 'Install and activate desktop ChemDraw, then repair or reinstall it if COM registration remains absent.'
        Add-NextStep 'Install the licensed Windows desktop edition of ChemDraw and open it once.'
    }

    Add-Check -Name 'chemdraw_activation' -Status 'warning' -Required $false `
        -Detail 'Activation is intentionally not tested by this read-only script.' `
        -Help 'Open ChemDraw manually, sign in or activate, create and save one document, then close the application.'
    Add-NextStep 'Confirm ChemDraw activation manually before running native probes.'

    if ($chemdrawExe) {
        $chemRoot = Split-Path -Parent $chemdrawExe
        $cursor = $chemRoot
        while ($cursor) {
            $parent = Split-Path -Parent $cursor
            if (-not $parent -or $parent -eq $cursor) { break }
            if ((Split-Path -Leaf $parent) -in @('Program Files', 'Program Files (x86)')) {
                $chemRoot = $cursor
                break
            }
            $cursor = $parent
        }
        $chemScriptDlls = @(Get-ChildItem -LiteralPath $chemRoot `
            -Filter '*ChemScript*.dll' -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object Length)
        $managedDll = $chemScriptDlls | Select-Object -First 1
        $nativeDll = $chemScriptDlls | Select-Object -Last 1
        if ($managedDll -and $nativeDll) {
            Add-Check -Name 'chemscript_files' -Status 'pass' -Required $false `
                -Detail "Managed: $($managedDll.Name); native: $($nativeDll.Name)" `
                -Help 'Run cdxml-doctor --no-tests after Python package installation to configure the bridge.'
        } else {
            Add-Check -Name 'chemscript_files' -Status 'warning' -Required $false `
                -Detail 'A complete managed/native ChemScript DLL pair was not found near ChemDraw.exe.' `
                -Help 'Core CDXML tools can still work. Molecule comparison and full SDK tools require ChemScript.'
            Add-NextStep 'Run cdxml-doctor --no-tests to discover or configure ChemScript if those tools are needed.'
        }
    } else {
        Add-Check -Name 'chemscript_files' -Status 'warning' -Required $false `
            -Detail 'ChemScript files could not be checked before ChemDraw COM discovery succeeds.' `
            -Help 'Molecule comparison and full SDK tools require a configured ChemScript installation.'
    }
}

if ($isWindowsHost) {
    $wordRegistered = [bool](Get-RegistryDefaultValue `
        'Registry::HKEY_CLASSES_ROOT\Word.Application\CLSID')
    $powerPointRegistered = [bool](Get-RegistryDefaultValue `
        'Registry::HKEY_CLASSES_ROOT\PowerPoint.Application\CLSID')
    if ($wordRegistered -and $powerPointRegistered) {
        Add-Check -Name 'office_desktop' -Status 'pass' -Required $false `
            -Detail 'Microsoft Word and PowerPoint desktop COM registrations are present.' `
            -Help 'Office is needed only for editable DOCX/PPTX ChemDraw object workflows.'
    } else {
        $available = @()
        if ($wordRegistered) { $available += 'Word' }
        if ($powerPointRegistered) { $available += 'PowerPoint' }
        $detail = if ($available.Count) {
            "Detected: $($available -join ', '). The other Office application is unavailable."
        } else {
            'Word and PowerPoint desktop COM registrations were not found.'
        }
        Add-Check -Name 'office_desktop' -Status 'warning' -Required $false `
            -Detail $detail `
            -Help 'Install the required desktop Office application only if you need editable Office objects.'
    }
} else {
    Add-Check -Name 'office_desktop' -Status 'skipped' -Required $false `
        -Detail 'Office COM is available only on the supported Windows host.'
}

try {
    $homeRoot = [IO.Path]::GetPathRoot([Environment]::GetFolderPath('UserProfile'))
    $driveName = $homeRoot.TrimEnd('\').TrimEnd(':')
    $drive = Get-PSDrive -Name $driveName -ErrorAction Stop
    $freeGiB = [math]::Round($drive.Free / 1GB, 1)
    Add-Check -Name 'disk_space' `
        -Status $(if ($freeGiB -ge 10) { 'pass' } else { 'warning' }) `
        -Required $false `
        -Detail "$freeGiB GiB free on $homeRoot" `
        -Help 'Keep at least 10 GiB free for ChemDraw, the Python environment, caches, and optional models.'
    if ($freeGiB -lt 10) {
        Add-NextStep 'Free at least 10 GiB before installing the complete runtime or DECIMER models.'
    }
} catch {
    Add-Check -Name 'disk_space' -Status 'warning' -Required $false `
        -Detail "Free disk space could not be determined: $($_.Exception.Message)" `
        -Help 'Keep at least 10 GiB free for the complete installation.'
}

$blockingChecks = @($checks | Where-Object {
    $_.required -and $_.status -eq 'fail'
})
$requiredSkipped = @($checks | Where-Object {
    $_.required -and $_.status -eq 'skipped' -and -not $SkipPythonPackages
})
$ok = $blockingChecks.Count -eq 0 -and $requiredSkipped.Count -eq 0
if ($ok) {
    Add-NextStep 'Preview installation with scripts\install.ps1, then add -Apply -ConfigureMcp when the paths are correct.'
}

$report = [pscustomobject][ordered]@{
    schema_version = 1
    ok = $ok
    summary = [pscustomobject][ordered]@{
        passed = @($checks | Where-Object { $_.status -eq 'pass' }).Count
        warnings = @($checks | Where-Object { $_.status -eq 'warning' }).Count
        failed = $blockingChecks.Count
        skipped = @($checks | Where-Object { $_.status -eq 'skipped' }).Count
    }
    checks = @($checks)
    next_steps = @($nextSteps)
}

if ($Json) {
    $report | ConvertTo-Json -Depth 6
} else {
    Write-Output 'ChemDraw Skill prerequisite check'
    Write-Output ''
    foreach ($check in $checks) {
        $marker = switch ($check.status) {
            'pass' { 'PASS' }
            'warning' { 'WARN' }
            'fail' { 'FAIL' }
            default { 'SKIP' }
        }
        Write-Output ("[{0}] {1}: {2}" -f $marker, $check.name, $check.detail)
        if ($check.status -in @('warning', 'fail') -and $check.help) {
            Write-Output ("       {0}" -f $check.help)
        }
    }
    Write-Output ''
    Write-Output ("Result: {0}" -f $(if ($ok) { 'ready for Skill installation' } else { 'required items need attention' }))
    if ($nextSteps.Count) {
        Write-Output 'Next steps:'
        for ($index = 0; $index -lt $nextSteps.Count; $index++) {
            Write-Output ("  {0}. {1}" -f ($index + 1), $nextSteps[$index])
        }
    }
}

if (-not $ok) { exit 1 }
exit 0
