[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot,

    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ArchiveFullPath = [IO.Path]::GetFullPath($ArchiveRoot)

function Get-ProjectRelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )

    $BaseUri = New-Object System.Uri(($BasePath.TrimEnd("\") + "\"))
    $TargetUri = New-Object System.Uri($TargetPath)
    return [Uri]::UnescapeDataString($BaseUri.MakeRelativeUri($TargetUri).ToString()).Replace("/", "\")
}

if ($ArchiveFullPath.StartsWith($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "ArchiveRoot must be outside the repository."
}
if (Test-Path -LiteralPath $ArchiveFullPath) {
    throw "Archive target already exists: $ArchiveFullPath"
}

New-Item -ItemType Directory -Path $ArchiveFullPath | Out-Null
$PayloadRoot = Join-Path $ArchiveFullPath "payload"
New-Item -ItemType Directory -Path $PayloadRoot | Out-Null

$BundlePath = Join-Path $ArchiveFullPath "git-history.bundle"
git -C $ProjectRoot bundle create $BundlePath --all
$PreviousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$BundleOutput = (git -C $ProjectRoot bundle verify $BundlePath 2>&1 | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
$BundleExitCode = $LASTEXITCODE
$ErrorActionPreference = $PreviousErrorActionPreference
if ($BundleExitCode -ne 0 -or $BundleOutput -notmatch "is okay") {
    throw "Git bundle verification failed: $BundleOutput"
}

$CandidateDirectories = @(
    "server_uploads",
    "server_reports",
    "test file",
    "report sample",
    "tmp_contractor_submission_samples",
    "tmp_qa_batch_test",
    "tmp_reports",
    "tmp_reports_v2",
    "tmp_reports_v3",
    "tmp_reports_v4",
    "tmp_reports_v5",
    "tmp_sample_extract",
    "dist"
)

$CandidateFiles = @()
foreach ($Directory in $CandidateDirectories) {
    $CandidatePath = Join-Path $ProjectRoot $Directory
    if (Test-Path -LiteralPath $CandidatePath) {
        $CandidateFiles += Get-ChildItem -LiteralPath $CandidatePath -Recurse -File -Force
    }
}
$CandidateFiles += Get-ChildItem -LiteralPath $ProjectRoot -File -Force | Where-Object {
    $_.Name -like "tmp_*" -or
    $_.Name -like "~`$*.docx" -or
    $_.Name -in @("idc.log", "idc_ocr.log")
}
$CandidateFiles = $CandidateFiles | Sort-Object FullName -Unique

$HashToArchivePath = @{}
$SourceRows = @()
foreach ($File in $CandidateFiles) {
    if ($File.FullName -eq (Join-Path $ProjectRoot ".env")) {
        continue
    }

    $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash
    $RelativePath = Get-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $File.FullName
    $IsDuplicate = $HashToArchivePath.ContainsKey($Hash)

    if (-not $IsDuplicate) {
        $ArchiveFile = Join-Path $PayloadRoot $RelativePath
        New-Item -ItemType Directory -Path (Split-Path -Parent $ArchiveFile) -Force | Out-Null
        Copy-Item -LiteralPath $File.FullName -Destination $ArchiveFile
        $CopiedHash = (Get-FileHash -LiteralPath $ArchiveFile -Algorithm SHA256).Hash
        if ($CopiedHash -ne $Hash) {
            throw "Archive hash mismatch: $RelativePath"
        }
        $HashToArchivePath[$Hash] = Get-ProjectRelativePath -BasePath $ArchiveFullPath -TargetPath $ArchiveFile
    }

    $SourceRows += [pscustomobject]@{
        original_path = $RelativePath
        size_bytes    = $File.Length
        sha256        = $Hash
        archived_path = $HashToArchivePath[$Hash]
        duplicate     = $IsDuplicate
    }
}

$SourceRows | Export-Csv -LiteralPath (Join-Path $ArchiveFullPath "source_map.csv") -NoTypeInformation -Encoding utf8

$PayloadBytes = (Get-ChildItem -LiteralPath $PayloadRoot -Recurse -File | Measure-Object Length -Sum).Sum
$SourceBytes = ($SourceRows | Measure-Object size_bytes -Sum).Sum
$Inventory = [ordered]@{
    created_at           = (Get-Date).ToString("o")
    repository           = $ProjectRoot
    source_commit        = (git -C $ProjectRoot rev-parse HEAD)
    remote_url           = (git -C $ProjectRoot remote get-url origin)
    env_present          = (Test-Path -LiteralPath (Join-Path $ProjectRoot ".env"))
    env_archived         = $false
    source_records       = $SourceRows.Count
    unique_payload_files = $HashToArchivePath.Count
    source_bytes         = [int64]$SourceBytes
    unique_payload_bytes = [int64]$PayloadBytes
}
$Inventory | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $ArchiveFullPath "inventory.json") -Encoding utf8

$ChecksumLines = Get-ChildItem -LiteralPath $PayloadRoot -Recurse -File | Sort-Object FullName | ForEach-Object {
    $ItemHash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    "$ItemHash  $(Get-ProjectRelativePath -BasePath $ArchiveFullPath -TargetPath $_.FullName)"
}
$BundleHash = (Get-FileHash -LiteralPath $BundlePath -Algorithm SHA256).Hash
$ChecksumLines += "$BundleHash  git-history.bundle"
$ChecksumLines | Set-Content -LiteralPath (Join-Path $ArchiveFullPath "sha256sums.txt") -Encoding ascii

$GitInventory = @(
    "Remote: $(git -C $ProjectRoot remote get-url origin)",
    "HEAD: $(git -C $ProjectRoot rev-parse HEAD)",
    "",
    "Branches:",
    (git -C $ProjectRoot branch -avv),
    "",
    "Tags:",
    (git -C $ProjectRoot tag --sort=version:refname),
    "",
    "Recent commits:",
    (git -C $ProjectRoot log --date=iso --pretty=format:"%H %ad %s" --all -n 50)
)
$GitInventory | Set-Content -LiteralPath (Join-Path $ArchiveFullPath "git-inventory.txt") -Encoding utf8

$Verification = [ordered]@{
    bundle_verified         = $true
    payload_hashes_verified = $true
    records                 = $SourceRows.Count
    unique_files            = $HashToArchivePath.Count
    verified_at             = (Get-Date).ToString("o")
    bundle_output           = $BundleOutput.Trim()
}
$Verification | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $ArchiveFullPath "verification.json") -Encoding utf8

if ($Clean) {
    $CleanupDirectories = @(
        "build",
        "dist",
        ".venv-server",
        "__pycache__",
        "spec_files",
        "server_uploads",
        "server_reports",
        "test file",
        "report sample",
        "tmp_contractor_submission_samples",
        "tmp_qa_batch_test",
        "tmp_reports",
        "tmp_reports_v2",
        "tmp_reports_v3",
        "tmp_reports_v4",
        "tmp_reports_v5",
        "tmp_sample_extract",
        "output"
    )

    foreach ($Directory in $CleanupDirectories) {
        $Target = [IO.Path]::GetFullPath((Join-Path $ProjectRoot $Directory))
        if (-not $Target.StartsWith($ProjectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Unsafe cleanup target: $Target"
        }
        if (Test-Path -LiteralPath $Target) {
            Remove-Item -LiteralPath $Target -Recurse -Force
        }
    }

    Get-ChildItem -LiteralPath $ProjectRoot -Directory -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        ForEach-Object {
            $Target = [IO.Path]::GetFullPath($_.FullName)
            if ($Target.StartsWith($ProjectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath $Target -Recurse -Force
            }
        }

    Get-ChildItem -LiteralPath $ProjectRoot -File -Force | Where-Object {
        $_.Name -like "tmp_*" -or
        $_.Name -like "~`$*.docx" -or
        $_.Name -in @("idc.log", "idc_ocr.log")
    } | Remove-Item -Force
}

$RemainingBytes = (Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -Force | Measure-Object Length -Sum).Sum
[pscustomobject]@{
    archive               = $ArchiveFullPath
    source_records        = $SourceRows.Count
    unique_payload_files  = $HashToArchivePath.Count
    source_mib            = [math]::Round($SourceBytes / 1MB, 2)
    archive_payload_mib   = [math]::Round($PayloadBytes / 1MB, 2)
    remaining_repo_mib    = [math]::Round($RemainingBytes / 1MB, 2)
    env_preserved         = (Test-Path -LiteralPath (Join-Path $ProjectRoot ".env"))
    cleanup_performed     = [bool]$Clean
}
