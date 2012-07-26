#!/bin/bash
#
# Shell functions exported by the tin repo.
#
# Usage:
#   source PROVIDES.sh

die() {
  echo 1>&2 "$@"
  exit 2
}

test -n "$TIN_BASE_DIR" || die 'tin PROVIDES.sh: $TIN_BASE_DIR not set'

tin_filter_stdlib_modules() {
  readonly STDLIB_DIR=/usr/lib/python
  grep -v $STDLIB_DIR
}

# define 3 binaries in the bin/ dir

py_imports() {
  $TIN_BASE_DIR/bin/py_imports.py "$@"
}

tin() {
  $TIN_BASE_DIR/bin/tin.py "$@"
}

tin_info() {
  $TIN_BASE_DIR/bin/tin-info.sh "$@"
}

# Build standard
tin_build_normal() {
  local main_module=$1
  test -n "$main_module" || die "No main module given"
  py_imports "$main_module" | \
    tin_filter_stdlib_modules | \
    tin
}
