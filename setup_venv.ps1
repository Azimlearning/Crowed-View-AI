# Setup script for Venue Intelligence AI
# This script helps set up a virtual environment with Python 3.11 or 3.12

Write-Host "=== Venue Intelligence AI - Virtual Environment Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check for Python 3.11 or 3.12
Write-Host "Checking for Python installations..." -ForegroundColor Yellow

# Try to find Python 3.11 or 3.12
$pythonVersion = $null
$pythonCmd = $null

# Check Python 3.11
try {
    $output = py -3.11 --version 2>&1
    if ($LASTEXITCODE -eq 0 -or $output -match "3\.11") {
        $pythonVersion = "3.11"
        $pythonCmd = "py -3.11"
        Write-Host "Found Python 3.11" -ForegroundColor Green
    }
} catch {
    # Try Python 3.12
    try {
        $output = py -3.12 --version 2>&1
        if ($LASTEXITCODE -eq 0 -or $output -match "3\.12") {
            $pythonVersion = "3.12"
            $pythonCmd = "py -3.12"
            Write-Host "Found Python 3.12" -ForegroundColor Green
        }
    } catch {
        Write-Host "Python 3.11 or 3.12 not found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Python 3.11 or 3.12 from:" -ForegroundColor Yellow
        Write-Host "https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "During installation, make sure to check 'Add Python to PATH'" -ForegroundColor Yellow
        exit 1
    }
}

if (-not $pythonVersion) {
    Write-Host "Python 3.11 or 3.12 not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.11 or 3.12 from:" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "During installation, make sure to check 'Add Python to PATH'" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Using Python $pythonVersion" -ForegroundColor Green
Write-Host ""

# Remove existing venv if it exists
if (Test-Path "venv") {
    Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force venv
}

# Create new virtual environment
Write-Host "Creating virtual environment with Python $pythonVersion..." -ForegroundColor Yellow
& $pythonCmd -m venv venv

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create virtual environment!" -ForegroundColor Red
    exit 1
}

Write-Host "Virtual environment created successfully!" -ForegroundColor Green
Write-Host ""

# Activate and upgrade pip
Write-Host "Activating virtual environment and upgrading pip..." -ForegroundColor Yellow
& .\venv\Scripts\activate.ps1
python -m pip install --upgrade pip

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Activate the virtual environment: .\venv\Scripts\activate" -ForegroundColor White
Write-Host "2. Install dependencies: pip install -r requirements.txt" -ForegroundColor White
Write-Host "3. Make sure you have a .env file with your GEMINI_API_KEY" -ForegroundColor White
Write-Host ""
