param(
    [string]$ArchiveRoot = "C:\Users\11131\Documents\IDC-Archive",
    [string]$CandidateName = "2026-08-12-v0.17-release-candidates"
)

$ErrorActionPreference = "Stop"
$archive = (Resolve-Path -LiteralPath $ArchiveRoot).Path
if ((Split-Path -Leaf $archive) -ne "IDC-Archive") {
    throw "Refusing cleanup outside an IDC-Archive directory."
}

$candidate = Join-Path $archive $CandidateName
if (-not (Test-Path -LiteralPath (Join-Path $candidate "dist\IDC_CLI.exe") -PathType Leaf)) {
    throw "Verified final release candidates were not found."
}

foreach ($childName in @("build", "spec_files")) {
    $child = Join-Path $candidate $childName
    if (Test-Path -LiteralPath $child) {
        $resolved = (Resolve-Path -LiteralPath $child).Path
        if ((Split-Path -Parent $resolved) -ne $candidate) {
            throw "Unsafe candidate cleanup path: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

$pidFile = Join-Path $candidate "build.pid"
if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
    Remove-Item -LiteralPath $pidFile -Force
}

$staleNames = @(
    "2026-08-12-v0.16-pre-clean.failed",
    "2026-08-12-v0.16-pre-clean.failed2",
    "2026-08-12-v0.17-release-candidates.failed-python313",
    "2026-08-12-v0.17-release-candidates.prefinal",
    "2026-08-12-v0.17-release-candidates.stale2",
    "2026-08-12-v0.17-release-candidates.stale3",
    "2026-08-12-v0.17-release-candidates.superseded-concrete-default",
    "idc-v0.17-build-env"
)
foreach ($name in $staleNames) {
    $path = Join-Path $archive $name
    if (-not (Test-Path -LiteralPath $path)) {
        continue
    }
    $resolved = (Resolve-Path -LiteralPath $path).Path
    if ((Split-Path -Parent $resolved) -ne $archive -or (Split-Path -Leaf $resolved) -ne $name) {
        throw "Unsafe stale cleanup path: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

Write-Output "Final release candidates retained at $candidate; verified stale build artifacts removed."
