param(
    [string]$OutputPath = "tmp\clara-aws-elastic-beanstalk.zip"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedOutput = Join-Path $repoRoot $OutputPath
$outputDirectory = Split-Path -Parent $resolvedOutput
$stagingDirectory = Join-Path $repoRoot "tmp\aws-elastic-beanstalk-staging"
$trackedArchive = Join-Path $repoRoot "tmp\clara-aws-tracked.zip"

if (-not (Test-Path (Join-Path $repoRoot "docker-compose.aws.yml"))) {
    throw "docker-compose.aws.yml was not found at the repository root."
}

if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

$expectedStagingRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "tmp"))
$resolvedStaging = [System.IO.Path]::GetFullPath($stagingDirectory)
if (-not $resolvedStaging.StartsWith($expectedStagingRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to prepare an AWS bundle outside the repository tmp directory."
}

if (Test-Path $stagingDirectory) {
    Remove-Item -LiteralPath $stagingDirectory -Recurse -Force
}
if (Test-Path $trackedArchive) {
    Remove-Item -LiteralPath $trackedArchive -Force
}
if (Test-Path $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Force
}

git -C $repoRoot archive --format=zip --output=$trackedArchive HEAD
if ($LASTEXITCODE -ne 0) {
    throw "git archive failed. Commit the AWS deployment files before building the bundle."
}

Expand-Archive -LiteralPath $trackedArchive -DestinationPath $stagingDirectory
Remove-Item -LiteralPath (Join-Path $stagingDirectory "docker-compose.yml") -Force
Copy-Item `
    -LiteralPath (Join-Path $stagingDirectory "docker-compose.aws.yml") `
    -Destination (Join-Path $stagingDirectory "docker-compose.yml")
Remove-Item -LiteralPath (Join-Path $stagingDirectory "docker-compose.aws.yml") -Force

if (Test-Path (Join-Path $stagingDirectory ".env")) {
    throw "The AWS bundle unexpectedly contains .env. Refusing to package secrets."
}

Compress-Archive -Path (Join-Path $stagingDirectory "*") -DestinationPath $resolvedOutput
Remove-Item -LiteralPath $trackedArchive -Force

Write-Output "AWS Elastic Beanstalk bundle created:"
Write-Output $resolvedOutput
Write-Output "The bundle contains docker-compose.aws.yml as docker-compose.yml and does not contain .env."
