#!/bin/sh
set -eu

test_library="$(mktemp -d)"
trap 'rm -rf "$test_library"' EXIT HUP INT TERM

R CMD INSTALL --preclean --library="$test_library" .
cd tests
R_LIBS="$test_library${R_LIBS:+:$R_LIBS}" Rscript testthat.R
