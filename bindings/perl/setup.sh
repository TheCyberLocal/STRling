#!/bin/bash
set -e

# STRling Perl Binding Setup Script
# This script installs the required CPAN dependencies for the Perl binding.

echo "Setting up STRling Perl binding dependencies..."

# Try cpanm first, fall back to cpan, then try apt
install_module() {
    local module=$1
    local apt_package=$2

    # Check if module is already installed
    if perl -e "use $module" 2>/dev/null; then
        echo "$module is already installed."
        return 0
    fi

    if command -v cpanm &> /dev/null; then
        cpanm --notest "$module" || cpanm --notest --sudo "$module"
    elif command -v apt-get &> /dev/null && [ -n "$apt_package" ]; then
        echo "Attempting to install $module via apt-get..."
        sudo apt-get update -qq 2>/dev/null || true
        sudo apt-get install -y "$apt_package" 2>/dev/null || true
        # Verify the module was installed
        if perl -e "use $module" 2>/dev/null; then
            echo "$module installed successfully via apt."
        else
            # Fall back to cpan if apt fails
            echo "apt installation failed, falling back to cpan..."
            PERL_MM_USE_DEFAULT=1 PERL_AUTOINSTALL=--skipdeps cpan -T "$module" 2>&1 || true
        fi
    else
        # Fall back to cpan with non-interactive mode
        # Use environment variables to avoid interactive prompts
        PERL_MM_USE_DEFAULT=1 PERL_AUTOINSTALL=--skipdeps cpan -T "$module" 2>&1 || true
        # Verify the module was installed
        if perl -e "use $module" 2>/dev/null; then
            echo "$module installed successfully."
        else
            echo "Warning: $module may not have installed correctly."
        fi
    fi
}

# Cleanup temp file function
cleanup_temp() {
    rm -f /tmp/cpanm_installer
}

# Install cpanminus if not present and we have network
if ! command -v cpanm &> /dev/null; then
    echo "cpanm not found, attempting to install..."
    trap cleanup_temp EXIT
    if curl -sL --connect-timeout 5 https://cpanmin.us -o /tmp/cpanm_installer 2>/dev/null; then
        perl /tmp/cpanm_installer --sudo App::cpanminus 2>/dev/null || \
        perl /tmp/cpanm_installer App::cpanminus 2>/dev/null || \
        echo "Could not install cpanm, will use cpan or apt instead"
    else
        echo "Network unavailable or cpanmin.us unreachable, will use cpan or apt"
    fi
fi

# Install dependencies from Makefile.PL
echo "Installing Perl dependencies..."
install_module "Moo" "libmoo-perl"
install_module "Type::Tiny" "libtype-tiny-perl"
install_module "Test::Exception" "libtest-exception-perl"

# Generate Makefile
echo "Generating Makefile..."
perl Makefile.PL

echo "Perl binding setup complete."
