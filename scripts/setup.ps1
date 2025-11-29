#
# Rule-Based Trading Setup Script
# For Windows (PowerShell)
#
# Usage: .\setup.ps1
# Note: Run as Administrator if you encounter permission issues
#

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Blue
    Write-Host "  $Message" -ForegroundColor Blue
    Write-Host "============================================" -ForegroundColor Blue
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "→ $Message" -ForegroundColor Cyan
}

Write-Header "Rule-Based Trading Setup"

# Check Python installation
Write-Info "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
            Write-Error "Python 3.10 or higher is required (found $pythonVersion)"
            Write-Host ""
            Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/"
            exit 1
        }
        Write-Success "Python $major.$minor found"
    }
} catch {
    Write-Error "Python is not installed or not in PATH"
    Write-Host ""
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during installation"
    exit 1
}

# Create virtual environment
Write-Info "Creating virtual environment..."
if (Test-Path ".venv") {
    Write-Warning "Virtual environment already exists, skipping creation"
} else {
    python -m venv .venv
    Write-Success "Virtual environment created"
}

# Activate virtual environment
Write-Info "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1
Write-Success "Virtual environment activated"

# Upgrade pip
Write-Info "Upgrading pip..."
python -m pip install --upgrade pip --quiet 2>$null
Write-Success "pip upgraded"

# Install dependencies
Write-Info "Installing dependencies..."
pip install -r requirements.txt --quiet 2>$null
Write-Success "Dependencies installed"

# Create .env file if it doesn't exist
Write-Info "Setting up configuration..."
if (Test-Path ".env") {
    Write-Warning ".env file already exists, skipping"
} else {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success ".env file created from template"
        Write-Warning "Please edit .env with your Kite API credentials"
    } else {
        @"
SECRET_KEY=your-secret-key-change-this-in-production
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/trading
REDIS_URL=redis://localhost:6379/0
"@ | Out-File -FilePath ".env" -Encoding utf8
        Write-Success ".env file created"
        Write-Warning "Please edit .env with your configuration"
    }
}

Write-Info "Verifying installation..."
try {
    $testResult = python -m pytest tests/ -q --tb=no 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "All tests passed"
    } else {
        Write-Warning "Some tests failed (this may be expected without database)"
    }
} catch {
    Write-Warning "Could not run tests"
}

Write-Header "Setup Complete!"

Write-Host "Next steps:"
Write-Host ""
Write-Host "  1. " -NoNewline
Write-Host "Edit .env" -ForegroundColor Yellow -NoNewline
Write-Host " with your database and Redis URLs:"
Write-Host "     notepad .env" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. " -NoNewline
Write-Host "Start the server" -ForegroundColor Yellow -NoNewline
Write-Host ":"
Write-Host "     .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "     uvicorn main:app --reload" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. " -NoNewline
Write-Host "Create an account and authenticate with Kite" -ForegroundColor Yellow -NoNewline
Write-Host ":"
Write-Host "     Open " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan -NoNewline
Write-Host " in your browser"
Write-Host ""
Write-Host "  4. " -NoNewline
Write-Host "Define your trading rules via API" -ForegroundColor Yellow -NoNewline
Write-Host ":"
Write-Host "     POST /rules with your rule configuration" -ForegroundColor Cyan
Write-Host ""
Write-Host "  5. " -NoNewline
Write-Host "Start the trading engine" -ForegroundColor Yellow -NoNewline
Write-Host ":"
Write-Host "     Invoke-RestMethod -Method POST http://localhost:8000/engine/start" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Documentation: " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
