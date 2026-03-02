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

$packages = @(
    @{ Id = "Python.Python.3.13";   Name = "Python 3.13"    },  # any 3.10+ works; skip if already installed
    @{ Id = "Git.Git";              Name = "Git for Windows" },  # needed for Git Bash, which runs make
    @{ Id = "GnuWin32.Make";        Name = "GNU Make"        },
    @{ Id = "7zip.7zip";            Name = "7-Zip"           },  # needed to extract ImageMagick portable archive
    @{ Id = "JRSoftware.InnoSetup"; Name = "Inno Setup 6"   }
)

$alreadyInstalled = -1978335189
foreach ($pkg in $packages) {
    Write-Host "Installing $($pkg.Name)..." -ForegroundColor Yellow
    winget install --id $pkg.Id --source winget --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $alreadyInstalled) {
        Write-Warning "$($pkg.Name) install returned exit code $LASTEXITCODE - you may need to install it manually."
    }
}

# Add GNU Make to the current user PATH so Git Bash can find it
$makePath = "C:\Program Files (x86)\GnuWin32\bin"
if (Test-Path $makePath) {
    $current = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($current -notlike "*GnuWin32*") {
        $newPath = if ($current) { "$current;$makePath" } else { $makePath }
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        Write-Host "Added GNU Make to user PATH." -ForegroundColor Green
    } else {
        Write-Host "GNU Make already on PATH." -ForegroundColor Green
    }
} else {
    Write-Warning "GNU Make not found at $makePath - install may have failed. Add it to PATH manually if needed."
}

Write-Host "Done." -ForegroundColor Green
