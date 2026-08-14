param(
    [string]$OutputPath = "dist/clara-aws-fullstack-elastic-beanstalk.zip"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stagePath = Join-Path $repoRoot "tmp/clara-aws-fullstack-bundle"
$archivePath = Join-Path $repoRoot $OutputPath

$requiredFiles = @(
    "Dockerfile.aws-fullstack",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
    ".dockerignore",
    "scripts/start_aws_fullstack.py"
)
$requiredDirectories = @(
    "api",
    "loan_pipeline",
    "sample_documents",
    "web"
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

Copy-Item -LiteralPath (Join-Path $repoRoot "Dockerfile.aws-fullstack") `
    -Destination (Join-Path $resolvedStagePath "Dockerfile")
foreach ($file in $requiredFiles | Where-Object {
    $_ -notin @("Dockerfile.aws-fullstack", "scripts/start_aws_fullstack.py")
}) {
    Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination $resolvedStagePath
}

New-Item -ItemType Directory -Path (Join-Path $resolvedStagePath "scripts") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $repoRoot "scripts/start_aws_fullstack.py") `
    -Destination (Join-Path $resolvedStagePath "scripts/start_aws_fullstack.py")

foreach ($directory in $requiredDirectories) {
    Copy-Item -LiteralPath (Join-Path $repoRoot $directory) `
        -Destination (Join-Path $resolvedStagePath $directory) -Recurse
}

$generatedPaths = Get-ChildItem -LiteralPath $resolvedStagePath -Recurse -Force |
    Where-Object {
        $_.Name -in @("__pycache__", ".next", "node_modules", "out") -or
        $_.Extension -eq ".pyc" -or
        $_.Name -like ".env*"
    } |
    Sort-Object { $_.FullName.Length } -Descending
foreach ($path in $generatedPaths) {
    if (-not $path.FullName.StartsWith(
        "$resolvedStagePath\",
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Refusing to remove a generated path outside the staging directory."
    }
    Remove-Item -LiteralPath $path.FullName -Recurse -Force
}

$archiveDirectory = Split-Path -Parent $archivePath
New-Item -ItemType Directory -Path $archiveDirectory -Force | Out-Null
if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archiveStream = [System.IO.File]::Open($archivePath, [System.IO.FileMode]::CreateNew)
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
        ".dockerignore",
        "scripts/start_aws_fullstack.py",
        "web/package.json",
        "web/package-lock.json",
        "web/next.config.ts"
    )

    if ($archive.Entries | Where-Object { $_.FullName.Contains("\") }) {
        throw "Deployment archive validation failed. ZIP entries must use forward slashes."
    }
    if ($entries | Where-Object {
        $_ -match "(^|/)(node_modules|\.next|__pycache__)(/|$)" -or
        $_ -like "*.pyc" -or
        [System.IO.Path]::GetFileName($_) -like ".env*"
    }) {
        throw "Deployment archive validation failed. Generated files or secrets were included."
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

Write-Host "AWS full-stack Elastic Beanstalk bundle created and verified:"
Write-Host $archivePath
