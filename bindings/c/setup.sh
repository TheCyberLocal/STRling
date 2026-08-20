#!/usr/bin/env sh
set -eu

cmake -S . -B build -DSTRLING_C_WARNINGS_AS_ERRORS=ON
