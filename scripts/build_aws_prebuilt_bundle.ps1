param(
    [string]$OutputPath = "dist/clara-aws-fullstack-prebuilt-elastic-beanstalk.zip"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stagePath = Join-Path $repoRoot "tmp/clara-aws-fullstack-prebuilt-bundle"
$archivePath = Join-Path $repoRoot $OutputPath
$webRoot = Join-Path $repoRoot "web"

$requiredFiles = @(
    "Dockerfile.aws-fullstack-prebuilt",
    "api/requirements.txt",
    "pyproject.toml",
    "README.md",
    "scripts/start_aws_fullstack.py",
    "web/package.json",
    "web/package-lock.json",
    "web/next.config.ts"
)
$requiredDirectories = @("api", "loan_pipeline", "sample_documents")

foreach ($relativePath in $requiredFiles + $requiredDirectories) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $relativePath))) {
        throw "Required deployment source is missing: $relativePath"
    }
}

$previousApiBase = $env:NEXT_PUBLIC_API_BASE_URL
$previousInternalApi = $env:CLARA_INTERNAL_API_URL
try {
    $env:NEXT_PUBLIC_API_BASE_URL = "__SAME_ORIGIN__"
    $env:CLARA_INTERNAL_API_URL = "http://127.0.0.1:8001"
    Push-Location $webRoot
    try {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) {
            throw "Next.js production build failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:NEXT_PUBLIC_API_BASE_URL = $previousApiBase
    $env:CLARA_INTERNAL_API_URL = $previousInternalApi
}

$standaloneSource = Join-Path $webRoot ".next/standalone"
$staticSource = Join-Path $webRoot ".next/static"
foreach ($generatedPath in @($standaloneSource, $staticSource)) {
    if (-not (Test-Path -LiteralPath $generatedPath)) {
        throw "Next.js build output is missing: $generatedPath"
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

Copy-Item -LiteralPath (Join-Path $repoRoot "Dockerfile.aws-fullstack-prebuilt") `
    -Destination (Join-Path $resolvedStagePath "Dockerfile")
Copy-Item -LiteralPath (Join-Path $repoRoot "api/requirements.txt") `
    -Destination (Join-Path $resolvedStagePath "requirements.txt")
foreach ($file in @("pyproject.toml", "README.md")) {
    Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination $resolvedStagePath
}

foreach ($directory in $requiredDirectories) {
    Copy-Item -LiteralPath (Join-Path $repoRoot $directory) `
        -Destination (Join-Path $resolvedStagePath $directory) -Recurse
}

New-Item -ItemType Directory -Path (Join-Path $resolvedStagePath "scripts") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $repoRoot "scripts/start_aws_fullstack.py") `
    -Destination (Join-Path $resolvedStagePath "scripts/start_aws_fullstack.py")
Copy-Item -LiteralPath $standaloneSource `
    -Destination (Join-Path $resolvedStagePath "web") -Recurse
New-Item -ItemType Directory -Path (Join-Path $resolvedStagePath "web/.next") -Force | Out-Null
Copy-Item -LiteralPath $staticSource `
    -Destination (Join-Path $resolvedStagePath "web/.next/static") -Recurse

$generatedPaths = Get-ChildItem -LiteralPath $resolvedStagePath -Recurse -Force |
    Where-Object {
        $_.Name -eq "__pycache__" -or $_.Extension -eq ".pyc" -or $_.Name -like ".env*"
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
        "scripts/start_aws_fullstack.py",
        "web/server.js",
        "web/package.json"
    )

    if ($archive.Entries | Where-Object { $_.FullName.Contains("\") }) {
        throw "Deployment archive validation failed. ZIP entries must use forward slashes."
    }
    if ($entries | Where-Object {
        $_ -match "(^|/)__pycache__(/|$)" -or $_ -like "*.pyc" -or
        [System.IO.Path]::GetFileName($_) -like ".env*"
    }) {
        throw "Deployment archive validation failed. Generated Python files or secrets were included."
    }
    foreach ($entry in $requiredEntries) {
        if ($entries -notcontains $entry) {
            throw "Deployment archive validation failed. Missing ZIP entry: $entry"
        }
    }
    if (-not ($entries | Where-Object { $_ -like "web/.next/static/*" })) {
        throw "Deployment archive validation failed. Missing Next.js static assets."
    }
}
finally {
    $archive.Dispose()
}

Write-Host "AWS prebuilt full-stack Elastic Beanstalk bundle created and verified:"
Write-Host $archivePath
