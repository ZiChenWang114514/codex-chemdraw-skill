[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Python,
    [string]$SkillRoot,
    [string]$ConfigPath,
    [string]$CodexCommand = 'codex',
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$discoveryScript = Join-Path $scriptRoot 'runtime_discovery.py'

function Get-DiscoveryBootstrap {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        return [pscustomobject]@{ Command = $launcher.Source; Arguments = @('-3') }
    }
    $interpreter = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($interpreter) {
        return [pscustomobject]@{ Command = $interpreter.Source; Arguments = @() }
    }
    if ($Python -and (Test-Path -LiteralPath $Python -PathType Leaf)) {
        return [pscustomobject]@{ Command = $Python; Arguments = @() }
    }
    throw 'A bootstrap Python is required to run runtime_discovery.py.'
}

function Invoke-RuntimeDiscovery {
    $bootstrap = Get-DiscoveryBootstrap
    $arguments = @($bootstrap.Arguments) + @($discoveryScript, '--json')
    if ($Python) { $arguments += @('--python', $Python) }
    if ($SkillRoot) { $arguments += @('--skill-root', $SkillRoot) }
    $output = & $bootstrap.Command @arguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = $output | Out-String
    if ($exitCode -ne 0) {
        throw "Runtime discovery failed with exit code $exitCode`: $($text.Trim())"
    }
    try {
        return $text | ConvertFrom-Json
    } catch {
        throw "Runtime discovery returned invalid JSON: $($text.Trim())"
    }
}

function Invoke-CodexCommand {
    param([string[]]$Arguments)

    $output = & $CodexCommand @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = ($output | Out-String).Trim()
    }
}

function Get-ConfigFingerprint {
    param([string]$ResolvedConfigPath)

    if (-not (Test-Path -LiteralPath $ResolvedConfigPath -PathType Leaf)) {
        return '<absent>'
    }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $ResolvedConfigPath).Hash
}

function Test-SamePath {
    param([string]$Actual, [string]$Expected)

    if (-not $Actual -or -not $Expected) { return $false }
    try {
        $actualPath = [IO.Path]::GetFullPath($Actual)
        $expectedPath = [IO.Path]::GetFullPath($Expected)
        return [string]::Equals(
            $actualPath,
            $expectedPath,
            [StringComparison]::OrdinalIgnoreCase
        )
    } catch {
        return [string]::Equals(
            $Actual,
            $Expected,
            [StringComparison]::OrdinalIgnoreCase
        )
    }
}

function Test-CorrectRegistration {
    param(
        [object]$Registration,
        [string]$PythonPath,
        [string]$ServerPath
    )

    if (-not $Registration -or -not $Registration.transport) { return $false }
    if ($Registration.PSObject.Properties['enabled'] -and -not $Registration.enabled) {
        return $false
    }
    $transport = $Registration.transport
    if ($transport.type -ne 'stdio') { return $false }
    if (-not (Test-SamePath $transport.command $PythonPath)) { return $false }
    $registeredArguments = @($transport.args)
    if ($registeredArguments.Count -notin @(1, 2)) { return $false }
    if (-not (Test-SamePath $registeredArguments[0] $ServerPath)) { return $false }
    if (
        $registeredArguments.Count -eq 2 -and
        $registeredArguments[1] -ne '--no-preload-decimer'
    ) {
        return $false
    }

    $requiredEnvironment = [ordered]@{
        TF_CPP_MIN_LOG_LEVEL = '3'
        TF_ENABLE_ONEDNN_OPTS = '0'
    }
    if (-not $transport.env) { return $false }
    foreach ($entry in $requiredEnvironment.GetEnumerator()) {
        $property = $transport.env.PSObject.Properties[$entry.Key]
        if (-not $property -or [string]$property.Value -ne $entry.Value) {
            return $false
        }
    }
    return $true
}

function Get-ReplacementEnvironment {
    param([object]$Registration)

    $environment = @{}
    if ($Registration -and $Registration.transport -and $Registration.transport.env) {
        foreach ($property in $Registration.transport.env.PSObject.Properties) {
            $environment[$property.Name] = [string]$property.Value
        }
    }
    $environment['TF_CPP_MIN_LOG_LEVEL'] = '3'
    $environment['TF_ENABLE_ONEDNN_OPTS'] = '0'
    return $environment
}

function Assert-ConfigBlockCanRoundTrip {
    param(
        [string]$PythonPath,
        [string]$ResolvedConfigPath
    )

    if (-not (Test-Path -LiteralPath $ResolvedConfigPath -PathType Leaf)) {
        return
    }
    $auditCode = '"CHEMDRAW_MCP_CONFIG_AUDIT"; import json, sys, tomllib; from pathlib import Path; config_path = Path(sys.argv[1]); data = tomllib.loads(config_path.read_text(encoding="utf-8")); block = data.get("mcp_servers", {}).get("cdxml-toolkit", {}); print(json.dumps(block))'
    try {
        $auditOutput = & $PythonPath -c $auditCode $ResolvedConfigPath 2>&1
    } catch {
        throw "Cannot safely inspect the current MCP block for round-trip settings: $($_.Exception.Message)"
    }
    $auditExitCode = $LASTEXITCODE
    $auditText = ($auditOutput | Out-String).Trim()
    if ($auditExitCode -ne 0) {
        throw "Cannot safely inspect the current MCP block for round-trip settings (audit exit code $auditExitCode)."
    }
    try {
        $block = $auditText | ConvertFrom-Json
    } catch {
        throw 'Cannot safely inspect the current MCP block because the audit returned invalid JSON.'
    }
    $allowedKeys = @('args', 'command', 'env')
    $unsupportedKeys = @(
        $block.PSObject.Properties.Name |
            Where-Object { $_ -notin $allowedKeys } |
            Sort-Object
    )
    if ($unsupportedKeys.Count -gt 0) {
        throw (
            'Refusing to replace cdxml-toolkit because codex mcp add cannot ' +
            'round-trip these settings: ' + ($unsupportedKeys -join ', ')
        )
    }
}

function Get-CurrentRegistration {
    $result = Invoke-CodexCommand @('mcp', 'get', 'cdxml-toolkit', '--json')
    if ($result.ExitCode -ne 0) {
        if (
            $result.Output -match
            '(?i)(not\s+found|does\s+not\s+exist|unknown\s+mcp\s+server|no\s+mcp\s+server\s+named)'
        ) {
            return $null
        }
        throw "codex mcp get failed with exit code $($result.ExitCode); output was withheld to protect stored environment values."
    }
    try {
        return $result.Output | ConvertFrom-Json
    } catch {
        throw 'codex mcp get returned invalid JSON; output was withheld to protect stored environment values.'
    }
}

function Invoke-Configuration {
    $discovery = Invoke-RuntimeDiscovery
    $pythonPath = [IO.Path]::GetFullPath([string]$discovery.python.path)
    $skillPath = [IO.Path]::GetFullPath([string]$discovery.skill_root.path)
    $serverPath = [IO.Path]::GetFullPath((Join-Path $skillPath 'scripts\mcp_server.py'))

    if (-not (Test-Path -LiteralPath $serverPath -PathType Leaf)) {
        throw "MCP server script not found: $serverPath"
    }

    $serverDirectory = Split-Path -Parent $serverPath
    $validationCode = @'
import sys
sys.path.insert(0, sys.argv[1])
import mcp_server
mcp_server.build_server()
'@
    $validationOutput = & $pythonPath -c $validationCode $serverDirectory 2>&1
    $validationExitCode = $LASTEXITCODE
    if ($validationExitCode -ne 0) {
        $detail = ($validationOutput | Out-String).Trim()
        throw "MCP server import validation failed with exit code $validationExitCode`: $detail"
    }

    if (-not $ConfigPath) {
        $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
        $script:ConfigPath = Join-Path $codexHome 'config.toml'
    }
    $resolvedConfigPath = [IO.Path]::GetFullPath($ConfigPath)
    if ([IO.Path]::GetFileName($resolvedConfigPath) -ne 'config.toml') {
        throw "ConfigPath must name config.toml: $resolvedConfigPath"
    }

    $previousCodexHome = $env:CODEX_HOME
    $env:CODEX_HOME = Split-Path -Parent $resolvedConfigPath
    try {
        if (-not (Get-Command $CodexCommand -ErrorAction SilentlyContinue)) {
            throw "Codex command not found: $CodexCommand"
        }

        $current = Get-CurrentRegistration
        $isCorrect = Test-CorrectRegistration $current $pythonPath $serverPath
        $replacementEnvironment = Get-ReplacementEnvironment $current
        $visibleEnvironmentKeys = @(
            'TF_CPP_MIN_LOG_LEVEL',
            'TF_ENABLE_ONEDNN_OPTS'
        )
        $environmentPreview = @(
            $replacementEnvironment.Keys |
                Sort-Object |
                ForEach-Object {
                    $displayValue = if ($_ -in $visibleEnvironmentKeys) {
                        $replacementEnvironment[$_]
                    } else {
                        '<preserved>'
                    }
                    "--env $_=$displayValue"
                }
        ) -join ' '
        $proposal = [ordered]@{
            apply = [bool]$Apply
            python = $pythonPath
            skill_root = $skillPath
            server = $serverPath
            config = $resolvedConfigPath
            command = "codex mcp add cdxml-toolkit $environmentPreview -- `"$pythonPath`" `"$serverPath`""
            status = if ($isCorrect) { 'unchanged' } else { 'proposal' }
        }

        if ($isCorrect -or -not $Apply) {
            $proposal | ConvertTo-Json -Depth 4
            return
        }

        if (-not $PSCmdlet.ShouldProcess(
            $resolvedConfigPath,
            'Register the cdxml-toolkit MCP server'
        )) {
            $proposal.status = 'whatif'
            $proposal | ConvertTo-Json -Depth 4
            return
        }

        Assert-ConfigBlockCanRoundTrip $pythonPath $resolvedConfigPath

        $hadConfig = Test-Path -LiteralPath $resolvedConfigPath -PathType Leaf
        $baselineFingerprint = Get-ConfigFingerprint $resolvedConfigPath
        $backup = $null
        if ($hadConfig) {
            $stamp = Get-Date -Format 'yyyyMMdd-HHmmssfff'
            $backup = "$resolvedConfigPath.chemdraw-$stamp-$([guid]::NewGuid().ToString('N')).bak"
            Copy-Item -LiteralPath $resolvedConfigPath -Destination $backup -Force
            if ((Get-ConfigFingerprint $resolvedConfigPath) -ne $baselineFingerprint) {
                throw 'config.toml changed while its backup was being created; no mutation was attempted.'
            }
        }

        $lastKnownFingerprint = $baselineFingerprint
        try {
            if ($current) {
                if ((Get-ConfigFingerprint $resolvedConfigPath) -ne $lastKnownFingerprint) {
                    throw 'config.toml changed before MCP removal; no mutation was attempted.'
                }
                $remove = Invoke-CodexCommand @('mcp', 'remove', 'cdxml-toolkit')
                if ($remove.ExitCode -ne 0) {
                    throw "codex mcp remove failed with exit code $($remove.ExitCode)."
                }
                $lastKnownFingerprint = Get-ConfigFingerprint $resolvedConfigPath
            }

            if ((Get-ConfigFingerprint $resolvedConfigPath) -ne $lastKnownFingerprint) {
                throw 'config.toml changed before MCP registration; the add operation was not started.'
            }
            $addArguments = @('mcp', 'add', 'cdxml-toolkit')
            foreach ($key in @($replacementEnvironment.Keys | Sort-Object)) {
                $addArguments += @('--env', "$key=$($replacementEnvironment[$key])")
            }
            $addArguments += @('--', $pythonPath, $serverPath)
            $add = Invoke-CodexCommand $addArguments
            if ($add.ExitCode -ne 0) {
                throw "codex mcp add failed with exit code $($add.ExitCode)."
            }
            $lastKnownFingerprint = Get-ConfigFingerprint $resolvedConfigPath

            $verified = Get-CurrentRegistration
            if (-not (Test-CorrectRegistration $verified $pythonPath $serverPath)) {
                throw 'The written MCP registration did not match the requested command.'
            }

            $proposal.backup = $backup
            $proposal.status = 'applied'
            $proposal | ConvertTo-Json -Depth 4
        } catch {
            $originalFailure = $_.Exception.Message
            try {
                $currentFingerprint = Get-ConfigFingerprint $resolvedConfigPath
                if ($currentFingerprint -ne $lastKnownFingerprint) {
                    $backupDetail = if ($backup) { " Backup remains at $backup." } else { '' }
                    throw (
                        'MCP registration failed; config.toml changed concurrently or during ' +
                        'the failed command and was not overwritten.' + $backupDetail + ' ' +
                        $originalFailure
                    )
                }
                if ($backup) {
                    Copy-Item -LiteralPath $backup -Destination $resolvedConfigPath -Force
                    throw "MCP registration failed; config was restored from $backup. $originalFailure"
                }
                if (-not $hadConfig -and (Test-Path -LiteralPath $resolvedConfigPath)) {
                    Remove-Item -LiteralPath $resolvedConfigPath -Force
                }
                throw "MCP registration failed; the absent config state was restored. $originalFailure"
            } catch {
                if (
                    $_.Exception.Message -like 'MCP registration failed;*restored*' -or
                    $_.Exception.Message -like 'MCP registration failed;*not overwritten*'
                ) {
                    throw
                }
                throw "MCP registration failed and automatic restore also failed. $originalFailure Restore error: $($_.Exception.Message)"
            }
        }
    } finally {
        if ($null -eq $previousCodexHome) {
            Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue
        } else {
            $env:CODEX_HOME = $previousCodexHome
        }
    }
}

Invoke-Configuration
