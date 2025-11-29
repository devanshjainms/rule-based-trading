#!/bin/bash
#
# Rule-Based Trading Setup Script
# For macOS and Linux
#
# Usage: ./setup.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

print_header "Rule-Based Trading Setup"

# Check Python installation
print_info "Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
else
    print_error "Python 3 is not installed"
    echo ""
    echo "Please install Python 3.10 or higher:"
    echo "  macOS: brew install python3"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    exit 1
fi

# Check Python version (need 3.10+)
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    print_error "Python 3.10 or higher is required (found $PYTHON_MAJOR.$PYTHON_MINOR)"
    exit 1
fi

# Create virtual environment
print_info "Creating virtual environment..."
if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists, skipping creation"
else
    python3 -m venv .venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip --quiet
print_success "pip upgraded"

# Install dependencies
print_info "Installing dependencies..."
pip install -r requirements.txt --quiet
print_success "Dependencies installed"

# Create .env file if it doesn't exist
print_info "Setting up configuration..."
if [ -f ".env" ]; then
    print_warning ".env file already exists, skipping"
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created from template"
        print_warning "Please edit .env with your configuration"
    else
        cat > .env << 'EOF'
SECRET_KEY=your-secret-key-change-this-in-production
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/trading
REDIS_URL=redis://localhost:6379/0
EOF
        print_success ".env file created"
        print_warning "Please edit .env with your configuration"
    fi
fi

print_info "Verifying installation..."
if python -m pytest tests/ -q --tb=no 2>/dev/null; then
    print_success "All tests passed"
else
    print_warning "Some tests failed (this may be expected without database)"
fi

print_header "Setup Complete!"

echo -e "Next steps:"
echo ""
echo -e "  1. ${YELLOW}Edit .env${NC} with your database and Redis URLs:"
echo -e "     ${BLUE}nano .env${NC}"
echo ""
echo -e "  2. ${YELLOW}Start the server${NC}:"
echo -e "     ${BLUE}source .venv/bin/activate${NC}"
echo -e "     ${BLUE}uvicorn main:app --reload${NC}"
echo ""
echo -e "  3. ${YELLOW}Create an account and authenticate with Kite${NC}:"
echo -e "     Open ${BLUE}http://localhost:8000/docs${NC} in your browser"
echo ""
echo -e "  4. ${YELLOW}Define your trading rules via API${NC}:"
echo -e "     POST ${BLUE}/rules${NC} with your rule configuration"
echo ""
echo -e "  5. ${YELLOW}Start the trading engine${NC}:"
echo -e "     ${BLUE}curl -X POST http://localhost:8000/engine/start${NC}"
echo ""
echo -e "API Documentation: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
