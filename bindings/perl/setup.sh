#!/bin/bash
set -e

# STRling Perl Binding Setup Script
# This script installs the required CPAN dependencies for the Perl binding.

echo "Setting up STRling Perl binding dependencies..."

if ! command -v cpanm >/dev/null 2>&1; then
    echo "Error: governed setup requires cpanm from the selected toolchain."
    exit 1
fi

# Resolve exactly the dependencies declared by Makefile.PL. Setup does not
# download its own package manager or fall back to ambient system packages.
echo "Installing declared Perl dependencies..."
cpanm --notest --installdeps .

# Generate Makefile
echo "Generating Makefile..."
perl Makefile.PL

echo "Perl binding setup complete."
