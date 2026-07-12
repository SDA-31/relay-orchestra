[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$InstallerArgs
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Repository = "SDA-31/relay-orchestra"
$EntryPointPath = $PSCommandPath

function Stop-Install {
    param([string]$Message)
    throw "Relay Orchestra installation failed: $Message"
}

function Find-Python {
    $candidates = @(
        @{ Name = "py"; Prefix = @("-3") },
        @{ Name = "python3"; Prefix = @() },
        @{ Name = "python"; Prefix = @() }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Name -ErrorAction SilentlyContinue)) {
            continue
        }
        $command = $candidate.Name
        $prefix = $candidate.Prefix
        & $command @prefix -c "import sys; raise SystemExit(sys.version_info < (3, 7))" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }
    }
    Stop-Install "Python 3.7 or newer is required"
}

function Test-LocalCheckout {
    $scriptPath = $script:EntryPointPath
    if (-not $scriptPath) {
        return $null
    }
    $root = Split-Path -Parent $scriptPath
    $installer = Join-Path $root "scripts/install.py"
    $skill = Join-Path $root "skills/relay-orchestra/SKILL.md"
    if ((Test-Path -LiteralPath $installer -PathType Leaf) -and (Test-Path -LiteralPath $skill -PathType Leaf)) {
        return $root
    }
    return $null
}

function Test-Ref {
    param([string]$Ref)
    if (
        -not $Ref -or
        $Ref.StartsWith("-") -or
        $Ref.Contains("..") -or
        $Ref.Contains("//") -or
        $Ref.EndsWith("/") -or
        $Ref -notmatch '^[A-Za-z0-9._/-]+$'
    ) {
        Stop-Install "invalid RELAY_ORCHESTRA_REF: $Ref"
    }
}

function Expand-RelayArchive {
    param(
        [hashtable]$Python,
        [string]$Archive,
        [string]$Destination
    )

    $validator = Join-Path (Split-Path -Parent $Archive) "extract.py"
    @'
import os
import posixpath
import shutil
import stat
import sys
import zipfile

archive_path, destination = sys.argv[1:]
max_members = 1024
max_bytes = 20 * 1024 * 1024

with zipfile.ZipFile(archive_path) as bundle:
    members = bundle.infolist()
    if not members or len(members) > max_members:
        raise SystemExit("archive has an invalid number of entries")

    roots = set()
    paths = set()
    total_size = 0
    checked = []

    for member in members:
        name = member.filename.replace("\\", "/")
        normalized = posixpath.normpath(name)
        parts = normalized.split("/")
        mode = member.external_attr >> 16
        is_directory = member.is_dir()
        if (
            not name
            or name.startswith("/")
            or normalized in ("", ".")
            or any(part in ("", ".", "..") or ":" in part for part in parts)
            or normalized in paths
            or (mode and not (is_directory or stat.S_ISREG(mode)))
        ):
            raise SystemExit("archive contains an unsafe entry: {!r}".format(member.filename))
        roots.add(parts[0])
        paths.add(normalized)
        total_size += member.file_size
        if total_size > max_bytes:
            raise SystemExit("archive contents exceed the 20 MiB safety limit")
        checked.append((member, normalized, is_directory))

    if len(roots) != 1:
        raise SystemExit("archive must contain exactly one repository root")

    for member, normalized, is_directory in sorted(checked, key=lambda item: item[1].count("/")):
        output = os.path.join(destination, *normalized.split("/"))
        if is_directory:
            os.makedirs(output, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with bundle.open(member) as source, open(output, "xb") as target:
            shutil.copyfileobj(source, target, length=64 * 1024)

root = os.path.join(destination, roots.pop())
required = (
    os.path.join(root, "scripts", "install.py"),
    os.path.join(root, "skills", "relay-orchestra", "SKILL.md"),
)
if not all(os.path.isfile(path) for path in required):
    raise SystemExit("archive does not contain the Relay Orchestra installer and skill")
print(root)
'@ | Set-Content -LiteralPath $validator -Encoding UTF8

    $command = $Python.Name
    $prefix = $Python.Prefix
    $output = & $command @prefix $validator $Archive $Destination
    if ($LASTEXITCODE -ne 0) {
        Stop-Install "downloaded archive failed validation"
    }
    return ($output | Select-Object -Last 1)
}

function Invoke-RemoteInstall {
    param(
        [hashtable]$Python,
        [string[]]$Arguments
    )

    if ($Arguments -contains "--link") {
        Stop-Install "--link requires a local checkout"
    }

    $ref = if ($env:RELAY_ORCHESTRA_REF) { $env:RELAY_ORCHESTRA_REF } else { "main" }
    Test-Ref $ref
    $work = Join-Path ([IO.Path]::GetTempPath()) ("relay-orchestra-" + [guid]::NewGuid().ToString("N"))
    $archive = Join-Path $work "source.zip"
    $extract = Join-Path $work "source"
    New-Item -ItemType Directory -Path $extract -Force | Out-Null

    try {
        if ($env:RELAY_ORCHESTRA_TEST_ARCHIVE) {
            Copy-Item -LiteralPath $env:RELAY_ORCHESTRA_TEST_ARCHIVE -Destination $archive
        } else {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $encodedRef = [uri]::EscapeDataString($ref)
            $archiveUrl = "https://codeload.github.com/$Repository/zip/$encodedRef"
            Invoke-WebRequest -UseBasicParsing -Uri $archiveUrl -OutFile $archive
        }
        if ((Get-Item -LiteralPath $archive).Length -gt 50MB) {
            Stop-Install "downloaded archive exceeds the 50 MiB limit"
        }

        $root = Expand-RelayArchive -Python $Python -Archive $archive -Destination $extract
        $installer = Join-Path $root "scripts/install.py"
        $command = $Python.Name
        $prefix = $Python.Prefix
        & $command @prefix $installer @Arguments
        $status = $LASTEXITCODE
        if ($status -ne 0) {
            Stop-Install "installer exited with status $status"
        }
        return
    } finally {
        Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$python = Find-Python
$checkout = Test-LocalCheckout
if ($checkout -and -not $env:RELAY_ORCHESTRA_REF) {
    $installer = Join-Path $checkout "scripts/install.py"
    $command = $python.Name
    $prefix = $python.Prefix
    & $command @prefix $installer @InstallerArgs
    $status = $LASTEXITCODE
    if ($status -ne 0) {
        Stop-Install "installer exited with status $status"
    }
    return
}

Invoke-RemoteInstall -Python $python -Arguments $InstallerArgs
