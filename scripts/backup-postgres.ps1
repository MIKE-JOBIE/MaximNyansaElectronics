$ErrorActionPreference = "Stop"

# Creates a PostgreSQL custom-format backup locally. It never uploads the dump to GitHub.
$pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
$pgRestore = Get-Command pg_restore -ErrorAction SilentlyContinue
if (-not $pgDump -or -not $pgRestore) {
    throw "PostgreSQL command-line tools are required. Install PostgreSQL client tools and ensure pg_dump/pg_restore are on PATH."
}
if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    throw "Set DATABASE_URL in this PowerShell session to the DIRECT PostgreSQL connection URL. Do not put it in a committed file."
}

try {
    $uri = [System.Uri]$env:DATABASE_URL
    $userInfo = [System.Uri]::UnescapeDataString($uri.UserInfo)
    $separator = $userInfo.IndexOf(":")
    if ($separator -lt 1) { throw "DATABASE_URL must include a username and password." }

    $pgUser = $userInfo.Substring(0, $separator)
    $pgPassword = $userInfo.Substring($separator + 1)
    $pgDatabase = [System.Uri]::UnescapeDataString($uri.AbsolutePath.TrimStart("/"))
    if ([string]::IsNullOrWhiteSpace($uri.Host) -or [string]::IsNullOrWhiteSpace($pgDatabase)) {
        throw "DATABASE_URL is missing a host or database name."
    }

    Write-Host "Backup target host: $($uri.Host)"
    Write-Host "Database name: $pgDatabase"
    Write-Warning "This may contain personal data and orders. Store the backup securely and never commit it."
    $confirmation = Read-Host "Type BACKUP to continue"
    if ($confirmation -cne "BACKUP") { throw "Backup cancelled." }

    $backupDir = Join-Path $PSScriptRoot "..\backups"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $outputFile = Join-Path $backupDir "maxim-nyansa-$stamp.dump"

    $env:PGHOST = $uri.Host
    $env:PGPORT = if ($uri.Port -gt 0) { [string]$uri.Port } else { "5432" }
    $env:PGUSER = $pgUser
    $env:PGPASSWORD = $pgPassword
    $env:PGDATABASE = $pgDatabase
    $env:PGSSLMODE = "require"

    & $pgDump.Source --no-owner --no-privileges --format=custom --file $outputFile
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -LiteralPath $outputFile -ErrorAction SilentlyContinue
        throw "pg_dump failed with exit code $LASTEXITCODE."
    }

    & $pgRestore.Source --list $outputFile | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "The archive listing check failed; do not treat this backup as verified." }

    $hash = Get-FileHash -LiteralPath $outputFile -Algorithm SHA256
    Write-Host "Backup created and archive-list check passed:"
    Write-Host (Resolve-Path $outputFile).Path
    Write-Host "Size: $((Get-Item $outputFile).Length) bytes"
    Write-Host "SHA256: $($hash.Hash)"
    Write-Warning "This verifies archive readability, not a full restore. Restore it into a SEPARATE test database before a production deployment."
}
finally {
    Remove-Item Env:PGHOST -ErrorAction SilentlyContinue
    Remove-Item Env:PGPORT -ErrorAction SilentlyContinue
    Remove-Item Env:PGUSER -ErrorAction SilentlyContinue
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:PGDATABASE -ErrorAction SilentlyContinue
    Remove-Item Env:PGSSLMODE -ErrorAction SilentlyContinue
}
