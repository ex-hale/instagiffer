# Instagiffer Developer Tools Installer
# Run once on a fresh machine to install all build prerequisites.
# Some packages (Git, GNU Make) will prompt for administrator access via UAC.
#
# Usage (in any PowerShell prompt):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\install-devtools.ps1
#
# Requires: Windows 11 (winget pre-installed as part of App Installer)

Write-Host "Instagiffer Windows dev environment setup" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Error "winget not found. Install 'App Installer' from the Microsoft Store and try again."
    exit 1
}

$PythonVersion = "3.13"
$packages = @(
    # any Python 3.10+ works; skip if already installed:
    @{ Id = "Python.Python.$PythonVersion";   Name = "Python $PythonVersion"; Override = "Include_tcltk=1"},
    # needed for Git Bash, which runs make:
    @{ Id = "Git.Git";              Name = "Git for Windows" },
    @{ Id = "ezwinports.make";      Name = "GNU Make"        },
    # needed to extract ImageMagick portable archive:
    @{ Id = "7zip.7zip";            Name = "7-Zip"           },
    @{ Id = "JRSoftware.InnoSetup"; Name = "Inno Setup 6"    },
    # needed for `make deploy` to create GitHub releases:
    @{ Id = "GitHub.cli";           Name = "GitHub CLI"      }
)

$alreadyInstalled = -1978335189
foreach ($pkg in $packages) {
    if ($pkg.Id -eq "Python.Python.$PythonVersion") {
        $hasPython = (Get-Command "py" -ErrorAction SilentlyContinue) -and (& py -$PythonVersion --version 2>$null)
        & py -$PythonVersion -c "import tkinter" 2>$null
        $hasTk = $hasPython -and ($LASTEXITCODE -eq 0)

        if ($hasTk) {
            Write-Host "Python $PythonVersion with tkinter already present, skipping." -ForegroundColor Green
            continue
        } elseif ($hasPython) {
            Write-Host "Python $PythonVersion found but tkinter missing, modifying installation..." -ForegroundColor Yellow
            winget install --id $pkg.Id --source winget --accept-source-agreements --accept-package-agreements --force --override "Include_tcltk=1"
        } else {
            Write-Host "Installing Python $PythonVersion with tkinter..." -ForegroundColor Yellow
            winget install --id $pkg.Id --source winget --silent --accept-source-agreements --accept-package-agreements
        }
        continue
    }

    Write-Host "Installing $($pkg.Name)..." -ForegroundColor Yellow
    winget install --id $pkg.Id --source winget --silent --accept-source-agreements --accept-package-agreements$override
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $alreadyInstalled) {
        Write-Warning "$($pkg.Name) install returned exit code $LASTEXITCODE - you may need to install it manually."
    }
}

function Add-ToUserPath {
    param(
        [string]$Path,
        [string]$Name
    )
    if (Test-Path $Path) {
        $current = [Environment]::GetEnvironmentVariable("PATH", "User")
        if ($current -notlike "*$Name*") {
            $newPath = if ($current) { "$current;$Path" } else { $Path }
            [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
            Write-Host "Added $Name to user PATH!" -ForegroundColor Green
        } else {
            Write-Host "$Name already on PATH!" -ForegroundColor Green
        }
    } else {
        Write-Warning "$Name not found at $Path - install may have failed. Add it to PATH manually if needed."
    }
}

# Add Inno Setup to current user PATH so make can find it
$isccPath = "${env:ProgramFiles(x86)}\Inno Setup 6"
if (-not (Test-Path $isccPath)) {
    $isccPath = "${env:LOCALAPPDATA}\Programs\Inno Setup 6"
}
Add-ToUserPath $isccPath "Inno Setup"

$gitSh = (Get-Command "git" -ErrorAction SilentlyContinue).Source -replace "cmd\\git.exe", "usr\bin\sh.exe"
if ($gitSh -and (Test-Path $gitSh)) {
    $gitShForward = $gitSh -replace "\\", "/"
    if ($gitShForward -ne "C:/Program Files/Git/usr/bin/sh.exe") {
        Write-Warning "Git is installed at a non-default location: $gitShForward"
        Write-Warning "Update SHELL in `Makefile` to: $gitShForward"
    } else {
        Write-Host "Git sh.exe found at expected location!" -ForegroundColor Green
    }
} else {
    Write-Warning "Could not detect Git sh.exe location!"
}

Write-Host "Done." -ForegroundColor Green
