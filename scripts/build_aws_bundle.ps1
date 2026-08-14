param(
    [string]$OutputPath = "dist/clara-aws-elastic-beanstalk.zip"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stagePath = Join-Path $repoRoot "tmp/clara-aws-bundle"
$archivePath = Join-Path $repoRoot $OutputPath

$requiredFiles = @(
    "Dockerfile.api",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
    ".dockerignore"
)
$requiredDirectories = @(
    "api",
    "loan_pipeline",
    "sample_documents"
)

foreach ($relativePath in $requiredFiles + $requiredDirectories) {
    $sourcePath = Join-Path $repoRoot $relativePath
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Required deployment source is missing: $relativePath"
    }
}

$resolvedTmpRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "tmp"))
$resolvedStagePath = [System.IO.Path]::GetFullPath($stagePath)
if (-not $resolvedStagePath.StartsWith(
    "$resolvedTmpRoot\",
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Refusing to prepare an AWS bundle outside the repository tmp directory."
}

if (Test-Path -LiteralPath $resolvedStagePath) {
    Remove-Item -LiteralPath $resolvedStagePath -Recurse -Force
}
New-Item -ItemType Directory -Path $resolvedStagePath -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $repoRoot "Dockerfile.api") `
    -Destination (Join-Path $resolvedStagePath "Dockerfile")
foreach ($file in $requiredFiles | Where-Object { $_ -ne "Dockerfile.api" }) {
    Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination $resolvedStagePath
}

foreach ($directory in $requiredDirectories) {
    Copy-Item -LiteralPath (Join-Path $repoRoot $directory) `
        -Destination (Join-Path $resolvedStagePath $directory) -Recurse
}

$generatedDirectories = Get-ChildItem -LiteralPath $resolvedStagePath -Directory -Recurse |
    Where-Object { $_.Name -eq "__pycache__" } |
    Sort-Object { $_.FullName.Length } -Descending
foreach ($directory in $generatedDirectories) {
    if (-not $directory.FullName.StartsWith(
        "$resolvedStagePath\",
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Refusing to remove a generated directory outside the staging directory."
    }
    Remove-Item -LiteralPath $directory.FullName -Recurse -Force
}

$archiveDirectory = Split-Path -Parent $archivePath
New-Item -ItemType Directory -Path $archiveDirectory -Force | Out-Null
if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archiveStream = [System.IO.File]::Open(
    $archivePath,
    [System.IO.FileMode]::CreateNew
)
$archiveWriter = [System.IO.Compression.ZipArchive]::new(
    $archiveStream,
    [System.IO.Compression.ZipArchiveMode]::Create
)
try {
    foreach ($file in Get-ChildItem -LiteralPath $resolvedStagePath -File -Recurse) {
        $entryName = $file.FullName.Substring($resolvedStagePath.Length + 1).Replace("\", "/")
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archiveWriter,
            $file.FullName,
            $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
}
finally {
    $archiveWriter.Dispose()
    $archiveStream.Dispose()
}

$archive = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
try {
    $entries = @($archive.Entries | ForEach-Object { $_.FullName.Replace("\", "/") })
    $requiredEntries = @(
        "Dockerfile",
        "requirements.txt",
        "pyproject.toml",
        "README.md",
        ".dockerignore"
    )

    if ($archive.Entries | Where-Object { $_.FullName.Contains("\") }) {
        throw "Deployment archive validation failed. ZIP entries must use forward slashes."
    }

    foreach ($entry in $requiredEntries) {
        if ($entries -notcontains $entry) {
            throw "Deployment archive validation failed. Missing ZIP entry: $entry"
        }
    }

    foreach ($directory in $requiredDirectories) {
        if (-not ($entries | Where-Object { $_ -like "$directory/*" })) {
            throw "Deployment archive validation failed. Missing ZIP directory: $directory/"
        }
    }
}
finally {
    $archive.Dispose()
}

Write-Host "AWS Elastic Beanstalk bundle created and verified:"
Write-Host $archivePath
