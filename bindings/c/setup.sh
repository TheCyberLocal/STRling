#!/bin/bash
set -e

# STRling C Binding Setup Script
# This script downloads required dependencies for building and testing the C binding.

echo "Setting up STRling C binding dependencies..."

# Create deps directory if it doesn't exist
mkdir -p deps

# Parson commit to use (pinned for reproducibility and security)
# Commit ba29f4eda9ea7703a9f6a9cf2b0532a2605723c3 is from v1.5.3 (2023-10-31)
PARSON_COMMIT="ba29f4eda9ea7703a9f6a9cf2b0532a2605723c3"

# Download parson (public domain JSON parser) if not present
if [ ! -f deps/parson.c ] || [ ! -f deps/parson.h ]; then
    echo "Downloading parson JSON parser (commit: ${PARSON_COMMIT})..."
    if ! curl -sfL "https://raw.githubusercontent.com/kgabis/parson/${PARSON_COMMIT}/parson.c" -o deps/parson.c; then
        echo "Error: Failed to download parson.c (HTTP error or network issue)"
        rm -f deps/parson.c  # Clean up partial download
        exit 1
    fi
    if ! curl -sfL "https://raw.githubusercontent.com/kgabis/parson/${PARSON_COMMIT}/parson.h" -o deps/parson.h; then
        echo "Error: Failed to download parson.h (HTTP error or network issue)"
        rm -f deps/parson.h  # Clean up partial download
        exit 1
    fi
    # Validate downloaded files are actually C code (not HTML error pages)
    if head -1 deps/parson.c | grep -q "^<\|^404\|Not Found"; then
        echo "Error: Downloaded parson.c appears to be an error page, not C code"
        rm -f deps/parson.c deps/parson.h
        exit 1
    fi
    echo "Parson downloaded successfully."
else
    echo "Parson already present."
fi

# Install system libraries if not present (jansson for JSON, cmocka for tests,
# pcre2 for end-to-end regex execution in the Essential 5 suite)
install_system_deps() {
    local deps_to_install=""

    # Check for jansson
    if ! pkg-config --exists jansson 2>/dev/null; then
        deps_to_install="$deps_to_install libjansson-dev"
    fi

    # Check for cmocka (test framework)
    if ! pkg-config --exists cmocka 2>/dev/null; then
        deps_to_install="$deps_to_install libcmocka-dev"
    fi

    # Check for PCRE2 (used by end-to-end matcher tests)
    if ! pkg-config --exists libpcre2-8 2>/dev/null; then
        deps_to_install="$deps_to_install libpcre2-dev"
    fi

    if [ -z "$deps_to_install" ]; then
        echo "All system dependencies are already installed."
        return 0
    fi

    echo "Installing missing system dependencies: $deps_to_install"

    # Detect OS and install accordingly
    # Note: Package names are controlled by the case statement, so no injection risk
    if [ -f /etc/debian_version ] || [ -f /etc/ubuntu_version ] || command -v apt-get &> /dev/null; then
        # Debian/Ubuntu - use word-splitting intentionally for multiple packages
        # shellcheck disable=SC2086
        sudo apt-get update -qq && sudo apt-get install -y -qq $deps_to_install
    elif [ -f /etc/redhat-release ] || command -v dnf &> /dev/null; then
        # Fedora/RHEL - different package names
        local fedora_deps=""
        for dep in $deps_to_install; do
            case "$dep" in
                libjansson-dev) fedora_deps="$fedora_deps jansson-devel" ;;
                libcmocka-dev) fedora_deps="$fedora_deps libcmocka-devel" ;;
                libpcre2-dev) fedora_deps="$fedora_deps pcre2-devel" ;;
            esac
        done
        # shellcheck disable=SC2086
        if [ -n "$fedora_deps" ]; then
            sudo dnf install -y $fedora_deps
        fi
    elif [ -f /etc/arch-release ] || command -v pacman &> /dev/null; then
        # Arch Linux
        local arch_deps=""
        for dep in $deps_to_install; do
            case "$dep" in
                libjansson-dev) arch_deps="$arch_deps jansson" ;;
                libcmocka-dev) arch_deps="$arch_deps cmocka" ;;
                libpcre2-dev) arch_deps="$arch_deps pcre2" ;;
            esac
        done
        # shellcheck disable=SC2086
        if [ -n "$arch_deps" ]; then
            sudo pacman -Sy --noconfirm $arch_deps
        fi
    elif command -v brew &> /dev/null; then
        # macOS
        local brew_deps=""
        for dep in $deps_to_install; do
            case "$dep" in
                libjansson-dev) brew_deps="$brew_deps jansson" ;;
                libcmocka-dev) brew_deps="$brew_deps cmocka" ;;
                libpcre2-dev) brew_deps="$brew_deps pcre2" ;;
            esac
        done
        # shellcheck disable=SC2086
        if [ -n "$brew_deps" ]; then
            brew install $brew_deps
        fi
    else
        echo "Warning: Could not auto-install dependencies. Please install manually:"
        echo "  Ubuntu/Debian: sudo apt-get install $deps_to_install"
        echo "  macOS: brew install jansson cmocka pcre2"
        echo "  Fedora: sudo dnf install jansson-devel libcmocka-devel pcre2-devel"
    fi
}

install_system_deps

# Verify dependencies
echo "Verifying dependencies..."
deps_ok=true
if pkg-config --exists jansson 2>/dev/null; then
    echo "  ✓ jansson library is available."
else
    echo "  ✗ jansson library not found."
    deps_ok=false
fi

if pkg-config --exists cmocka 2>/dev/null; then
    echo "  ✓ cmocka library is available."
else
    echo "  ✗ cmocka library not found."
    deps_ok=false
fi

if pkg-config --exists libpcre2-8 2>/dev/null; then
    echo "  ✓ pcre2 library is available."
else
    echo "  ✗ pcre2 library not found."
    deps_ok=false
fi

if [ "$deps_ok" = false ]; then
    echo "Error: Required dependencies are missing. Please install them manually."
    exit 1
fi

echo "C binding setup complete."
