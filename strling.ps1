param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Command,
    [Parameter(Mandatory = $false, Position = 1)]
    [string]$Language,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Options
)

$ErrorActionPreference = "Stop"
$ToolchainFile = Join-Path $PSScriptRoot "toolchain.json"

if (-not (Test-Path $ToolchainFile)) {
    Write-Error "toolchain.json not found at $ToolchainFile"
    exit 1
}

function Get-Toolchain {
    Get-Content $ToolchainFile -Raw | ConvertFrom-Json
}

function Get-BindingNames {
    (Get-Toolchain).bindings.PSObject.Properties.Name | Sort-Object
}

function Get-Binding {
    param([string]$BindingName)
    (Get-Toolchain).bindings.$BindingName
}

function Get-BindingRequiredBins {
    param([string]$BindingName)
    $binding = Get-Binding $BindingName
    if (-not $binding) {
        return @()
    }
    if ($binding.required_bins) {
        return @($binding.required_bins)
    }
    if ($binding.check_bin) {
        return @($binding.check_bin)
    }
    return @()
}

function Resolve-CommandName {
    param([string]$Name)
    switch ($Name) {
        "python3" {
            foreach ($candidate in @("python3", "python", "py")) {
                $resolved = Get-Command $candidate -ErrorAction SilentlyContinue
                if ($resolved -and $resolved.Source -notmatch '[\\/]WindowsApps[\\/]') {
                    return $candidate
                }
            }
            return $null
        }
        default {
            if (Get-Command $Name -ErrorAction SilentlyContinue) {
                return $Name
            }
            return $null
        }
    }
}

function Get-InstallPackages {
    param([string]$BindingName, [string]$Manager)
    $binding = Get-Binding $BindingName
    if (-not $binding -or -not $binding.install) {
        return @()
    }
    $packages = $binding.install.$Manager
    if (-not $packages) {
        return @()
    }
    return @($packages)
}

function Get-PackageManager {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        return "winget"
    }
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        return "choco"
    }
    return $null
}

function Install-Packages {
    param([string]$Manager, [string[]]$Packages)
    if (-not $Packages -or $Packages.Count -eq 0) {
        return $false
    }

    Write-Host ">> Attempting prerequisite install via ${Manager}: $($Packages -join ', ')"
    switch ($Manager) {
        "winget" {
            foreach ($package in $Packages) {
                & winget install --id $package --exact --accept-package-agreements --accept-source-agreements --silent
                if ($LASTEXITCODE -ne 0) {
                    return $false
                }
            }
            return $true
        }
        "choco" {
            & choco install -y @Packages
            return ($LASTEXITCODE -eq 0)
        }
        default {
            return $false
        }
    }
}

function Set-BindingPrereqs {
    param([string]$BindingName)
    $missing = @()
    $requiredBins = Get-BindingRequiredBins $BindingName

    foreach ($requiredBin in $requiredBins) {
        if (-not (Resolve-CommandName $requiredBin)) {
            $missing += $requiredBin
        }
    }

    if ($missing.Count -eq 0) {
        return $true
    }

    Write-Host ">> Missing prerequisite tools for ${BindingName}: $($missing -join ', ')"
    $manager = Get-PackageManager
    if (-not $manager) {
        return $false
    }

    $packages = Get-InstallPackages $BindingName $manager
    if ($packages.Count -eq 0) {
        Write-Host ">> No install metadata is defined for '$BindingName' on package manager '$manager'."
        return $false
    }

    if (-not (Install-Packages $manager $packages)) {
        return $false
    }

    foreach ($requiredBin in $requiredBins) {
        if (-not (Resolve-CommandName $requiredBin)) {
            return $false
        }
    }

    return $true
}

function Set-PythonEnv {
    param([string]$TargetDir)
    $pythonCommand = Resolve-CommandName "python3"
    if (-not $pythonCommand) {
        throw "Python is required to create the binding virtual environment."
    }

    $version = & $pythonCommand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $venvDir = Join-Path $TargetDir ".venv-$version"
    $legacyDir = Join-Path $TargetDir ".venv"

    if (Test-Path $legacyDir) {
        Remove-Item $legacyDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path $venvDir)) {
        Write-Host ">> Creating Python virtual environment ($venvDir)..."
        & $pythonCommand -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create Python virtual environment"
        }
    }

    $venvScripts = Join-Path $venvDir "Scripts"
    if (Test-Path $venvScripts) {
        $env:PATH = "$venvScripts;$env:PATH"
    }
}

function Invoke-BindingAction {
    param([string]$Action, [string]$BindingName)

    if ($Action -eq "bootstrap") {
        & $PSCommandPath setup $BindingName
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $PSCommandPath build $BindingName
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $PSCommandPath test $BindingName
        exit $LASTEXITCODE
    }

    $binding = Get-Binding $BindingName
    if (-not $binding) {
        Write-Error "Language '$BindingName' not found in toolchain.json"
        exit 1
    }

    if ($Action -ne "clean" -and -not (Set-BindingPrereqs $BindingName)) {
        Write-Error "Missing prerequisites for $BindingName"
        exit 1
    }

    $commandArray = @($binding.$Action)
    if (-not $commandArray -or $commandArray.Count -eq 0 -or ($commandArray.Count -eq 1 -and [string]::IsNullOrWhiteSpace($commandArray[0]))) {
        Write-Host "No '$Action' command defined for $BindingName."
        exit 0
    }

    $targetDir = Join-Path $PSScriptRoot $binding.path
    Write-Host ">> Running $Action for $BindingName in $targetDir..."
    Write-Host ">> Executing: $($commandArray -join ' ')"

    Push-Location $targetDir
    try {
        if ($BindingName -eq "python" -and $Action -ne "clean") {
            Set-PythonEnv $targetDir
        }

        $exe = $commandArray[0]
        $arguments = if ($commandArray.Count -gt 1) { $commandArray[1..($commandArray.Count - 1)] } else { @() }
        & $exe @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Error $_
        exit 1
    }
    finally {
        Pop-Location
    }
    exit 0
}

function Invoke-AllBindings {
    param([string]$Action)
    $failed = @()
    $passed = 0

    foreach ($binding in Get-BindingNames) {
        Write-Host "--------------------------------------------------"
        Write-Host ">> $Action $binding"
        & $PSCommandPath $Action $binding
        if ($LASTEXITCODE -eq 0) {
            $passed += 1
        }
        else {
            $failed += $binding
        }
    }

    Write-Host "--------------------------------------------------"
    Write-Host ">> Summary: $passed succeeded, $($failed.Count) failed"
    if ($failed.Count -gt 0) {
        Write-Host ">> Failed bindings: $($failed -join ', ')"
        exit 1
    }
    exit 0
}

function Show-Bindings {
    Write-Host "Available Bindings:"
    foreach ($binding in Get-BindingNames) {
        $missing = @()
        foreach ($required in Get-BindingRequiredBins $binding) {
            if (-not (Resolve-CommandName $required)) {
                $missing += $required
            }
        }
        if ($missing.Count -eq 0) {
            Write-Host ("  {0,-12} [READY]" -f $binding)
        }
        else {
            Write-Host ("  {0,-12} [MISSING: {1}]" -f $binding, ($missing -join ', '))
        }
    }
}

function Show-Help {
    Write-Host "Usage: .\strling.ps1 <command> [language|all] [options]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  format [--check] [lang|all]  Run or verify configured formatters"
    Write-Host "  lint [lang|all]              Run configured static analyzers"
    Write-Host "  hygiene                      Validate tracked repository artifacts"
    Write-Host "  generate [--check] [--json]  Regenerate or verify registered artifacts"
    Write-Host "  governance [--json]          Validate task scope and architecture rules"
    Write-Host "  contracts [--check] [--json] Regenerate or verify public contracts"
    Write-Host "  compile [options]           Compile a canonical request or Semantic STRling source"
    Write-Host "  import --input PATH|-       Import regex-compatible source into canonical semantics"
    Write-Host "  explain --input|--request   Return semantic and optional no-match evidence"
    Write-Host "  migrate --input|--request   Convert canonical semantics to Semantic STRling or Simply"
    Write-Host "  check --input|--request     Check source through canonical compiler diagnostics"
    Write-Host "  target list|inspect         List or inspect exact target profiles"
    Write-Host "  simply [options]            Compile a Simply BuilderRequest through the canonical kernel"
    Write-Host "  typecheck [lang|all]         Run configured type/static analysis"
    Write-Host "  setup <lang|all>      Install prerequisites and dependencies"
    Write-Host "  build <lang|all>      Build a binding if it has a build step"
    Write-Host "  test <lang|all>       Run tests for one binding or all bindings"
    Write-Host "  check [lang|all]      Run the fast quality aggregate"
    Write-Host "  certify [lang|all]    Run the current certification aggregate"
    Write-Host "  profile <local|pull-request|full|release> [lang|all]  Run a certification profile"
    Write-Host "  environment [lang|all]  Validate declared tool versions"
    Write-Host "  bootstrap <lang|all>  Run setup, build, and test in sequence"
    Write-Host "  clean <lang|all>      Clean artifacts"
    Write-Host "  cache-dir <lang>      Print cache directory path (for CI)"
    Write-Host "  lockfile <lang>       Print lockfile name (for CI)"
    Write-Host "  list                  List all bindings and tool status"
    Write-Host "  help                  Show this help message"
    Write-Host ""
    Show-Bindings
}

$ProductCommand = @("compile", "import", "explain", "migrate", "simply", "target") -contains $Command
$SemanticCheck = $Command -eq "check" -and (
    @("--input", "--request") -contains $Language -or
    ($Options | Where-Object { @("--input", "--request") -contains $_ }).Count -gt 0
)
if ($ProductCommand -or $SemanticCheck) {
    $cargoCommand = Resolve-CommandName "cargo"
    if (-not $cargoCommand) {
        Write-Error "Cargo is required to run the canonical compiler."
        exit 69
    }
    $productArguments = @($Command)
    if ($Language) {
        $productArguments += $Language
    }
    if ($Options) {
        $productArguments += $Options
    }
    Push-Location $PSScriptRoot
    try {
        & $cargoCommand run --quiet --manifest-path "core/internal/Cargo.toml" --bin strling-kernel -- @productArguments
        exit $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

$QualityCommands = @(
    "format",
    "hygiene",
    "lint",
    "typecheck",
    "build",
    "test",
    "check",
    "certify",
    "profile",
    "environment"
)
if ($QualityCommands -contains $Command) {
    $pythonCommand = Resolve-CommandName "python3"
    if (-not $pythonCommand) {
        Write-Error "Python is required to run canonical quality operations."
        exit 1
    }
    $qualityArguments = @($Command)
    if ($Language) {
        $qualityArguments += $Language
    }
    if ($Options) {
        $qualityArguments += $Options
    }
    Push-Location $PSScriptRoot
    try {
        & $pythonCommand "tooling/quality.py" @qualityArguments
        exit $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}

switch ($Command) {
    "help" {
        Show-Help
        exit 0
    }
    "list" {
        Show-Bindings
        exit 0
    }
    "generate" {
        $pythonCommand = Resolve-CommandName "python3"
        if (-not $pythonCommand) {
            Write-Error "Python is required to manage generated artifacts."
            exit 1
        }
        $generateArguments = @()
        if ($Language) {
            $generateArguments += $Language
        }
        if ($Options) {
            $generateArguments += $Options
        }
        Push-Location $PSScriptRoot
        try {
            & $pythonCommand "tooling/generated_artifacts.py" @generateArguments
            exit $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
    }
    "governance" {
        $pythonCommand = Resolve-CommandName "python3"
        if (-not $pythonCommand) {
            Write-Error "Python is required to validate change governance."
            exit 1
        }
        $governanceArguments = @()
        if ($Language) {
            $governanceArguments += $Language
        }
        if ($Options) {
            $governanceArguments += $Options
        }
        Push-Location $PSScriptRoot
        try {
            & $pythonCommand "tooling/governance.py" @governanceArguments
            exit $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
    }
    "contracts" {
        $pythonCommand = Resolve-CommandName "python3"
        if (-not $pythonCommand) {
            Write-Error "Python is required to manage public contracts."
            exit 1
        }
        $contractArguments = @()
        if ($Language) {
            $contractArguments += $Language
        }
        if ($Options) {
            $contractArguments += $Options
        }
        Push-Location $PSScriptRoot
        try {
            & $pythonCommand "tooling/public_contracts.py" @contractArguments
            exit $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
    }
    "baseline" {
        $pythonCommand = Resolve-CommandName "python3"
        if (-not $pythonCommand) {
            Write-Error "Python is required to validate frozen baseline evidence."
            exit 1
        }
        $baselineArguments = @()
        if ($Language) {
            $baselineArguments += $Language
        }
        if ($Options) {
            $baselineArguments += $Options
        }
        Push-Location $PSScriptRoot
        try {
            & $pythonCommand "tooling/baseline.py" @baselineArguments
            exit $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
    }
    "cache-dir" {
        if (-not $Language) { exit 1 }
        switch ($Language) {
            "php" { Write-Output "$HOME/.cache/composer"; Write-Output "bindings/php/vendor" }
            "typescript" { Write-Output "$HOME/.npm"; Write-Output "bindings/typescript/node_modules" }
            "rust" { Write-Output "$HOME/.cargo/registry"; Write-Output "$HOME/.cargo/git"; Write-Output "bindings/rust/target" }
            "python" { Write-Output "$HOME/.cache/pip"; Write-Output "bindings/python/.venv" }
            "go" { Write-Output "$HOME/go/pkg/mod"; Write-Output "$HOME/.cache/go-build" }
            "ruby" { Write-Output "bindings/ruby/vendor/bundle" }
            "dart" { Write-Output "$HOME/.pub-cache"; Write-Output "bindings/dart/.dart_tool" }
            "java" { Write-Output "$HOME/.m2/repository"; Write-Output "bindings/java/target" }
            "kotlin" { Write-Output "$HOME/.gradle/caches"; Write-Output "bindings/kotlin/build" }
            "lua" { Write-Output "bindings/lua/.luarocks" }
            "perl" { Write-Output "bindings/perl/local" }
            "csharp" { Write-Output "$HOME/.nuget/packages" }
            "fsharp" { Write-Output "$HOME/.nuget/packages" }
            "swift" { Write-Output "$HOME/.swiftpm"; Write-Output "bindings/swift/.build" }
            "c" { Write-Output "bindings/c/build" }
            "cpp" { Write-Output "bindings/cpp/build" }
            "r" { Write-Output "bindings/r/renv/library" }
            default { Write-Output "" }
        }
        exit 0
    }
    "lockfile" {
        if (-not $Language) { exit 1 }
        switch ($Language) {
            "php" { Write-Output "composer.lock" }
            "typescript" { Write-Output "package-lock.json" }
            "rust" { Write-Output "Cargo.lock" }
            "python" { Write-Output "requirements.txt" }
            "go" { if (Test-Path (Join-Path $PSScriptRoot "bindings/go/go.sum")) { Write-Output "go.sum" } else { Write-Output "go.mod" } }
            "ruby" { Write-Output "Gemfile.lock" }
            "dart" { Write-Output "pubspec.lock" }
            "java" { Write-Output "pom.xml" }
            "kotlin" { Write-Output "build.gradle.kts" }
            "lua" { Write-Output "strling-3.0.0-1.rockspec" }
            "perl" { Write-Output "Makefile.PL" }
            "csharp" { Write-Output "src/STRling/STRling.csproj" }
            "fsharp" { Write-Output "src/STRling/STRling.fsproj" }
            "swift" { if (Test-Path (Join-Path $PSScriptRoot "bindings/swift/Package.resolved")) { Write-Output "Package.resolved" } else { Write-Output "Package.swift" } }
            "c" { Write-Output "Makefile" }
            "cpp" { Write-Output "CMakeLists.txt" }
            "r" { Write-Output "DESCRIPTION" }
            default { Write-Output "" }
        }
        exit 0
    }
}

if (-not $Language) {
    Write-Error "Language argument is required for '$Command'."
    exit 1
}

if ($Language -eq "all" -and @("setup", "build", "test", "bootstrap", "clean") -contains $Command) {
    Invoke-AllBindings $Command
}

if ($Command -eq "clean") {
    if ($Language -eq "all") {
        Write-Host ">> Cleaning global artifacts..."
        $DirsToRemove = @("build", "target", "dist", "vendor", "__pycache__", ".venv", ".pytest_cache", ".mypy_cache")
        Get-ChildItem -Path $PSScriptRoot -Recurse -Directory -Force -ErrorAction SilentlyContinue | Where-Object { $DirsToRemove -contains $_.Name } | ForEach-Object {
            Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
        Write-Host ">> Global clean complete."
        exit 0
    }

    $binding = Get-Binding $Language
    if (-not $binding) {
        Write-Error "Language '$Language' not found in toolchain.json"
        exit 1
    }
    $targetDir = Join-Path $PSScriptRoot $binding.path
    Write-Host ">> Cleaning artifacts in $targetDir..."
    $DirsToRemove = @("build", "target", "dist", "vendor", "__pycache__", ".venv")
    Get-ChildItem -Path $targetDir -Recurse -Directory -Force -ErrorAction SilentlyContinue | Where-Object { $DirsToRemove -contains $_.Name } | ForEach-Object {
        Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host ">> Clean complete for $Language."
    exit 0
}

Invoke-BindingAction $Command $Language
