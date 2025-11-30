param (
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Command,
    [Parameter(Mandatory=$true, Position=1)]
    [string]$Language
)

$ErrorActionPreference = "Stop"
$ToolchainFile = Join-Path $PSScriptRoot "toolchain.json"

if (-not (Test-Path $ToolchainFile)) {
    Write-Error "toolchain.json not found at $ToolchainFile"
    exit 1
}

try {
    $Json = Get-Content $ToolchainFile -Raw | ConvertFrom-Json
} catch {
    Write-Error "Failed to parse toolchain.json: $_"
    exit 1
}

$Binding = $Json.bindings.$Language

if (-not $Binding) {
    Write-Error "Language '$Language' not found in toolchain.json"
    exit 1
}

$Path = $Binding.path
$CheckBin = $Binding.check_bin

if (-not (Get-Command $CheckBin -ErrorAction SilentlyContinue)) {
    Write-Error "Required tool '$CheckBin' not found. Please install it to work with $Language."
    exit 1
}

$CmdArray = @($Binding.$Command)

if (-not $CmdArray -or $CmdArray.Count -eq 0 -or ($CmdArray.Count -eq 1 -and [string]::IsNullOrWhiteSpace($CmdArray[0]))) {
    Write-Host "No '$Command' command defined for $Language."
    exit 0
}

$TargetDir = Join-Path $PSScriptRoot $Path
Write-Host ">> Running $Command for $Language in $TargetDir..."

Push-Location $TargetDir
try {
    # Execute the command
    $Exe = $CmdArray[0]
    $Args = $CmdArray[1..($CmdArray.Length-1)]
    
    Write-Host ">> Executing: $Exe $Args"
    & $Exe $Args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Error "Execution failed: $_"
    exit 1
} finally {
    Pop-Location
}
