#!/bin/bash
#
# Shell functions exported by the tin repo.
#
# Usage:
#   source PROVIDES.sh

_die() {
  echo 1>&2 "$@"
  exit 2
}

filter-stdlib-modules() {
  readonly STDLIB_DIR=/usr/lib/python
  grep -v $STDLIB_DIR
}

# define 3 binaries in the bin/ dir

py-imports() {
  $TIN_BASE_DIR/bin/py_imports.py "$@"
}

create() {
  $TIN_BASE_DIR/bin/create.py "$@"
}

hg-info() {
  $TIN_BASE_DIR/bin/hg-info.sh "$@"
}

# Common build.  You can add your own data with a custom pipeline.
build-normal() {
  local main_module=$1
  test -n "$main_module" || _die "No main module given"
  py-imports "$main_module" \
    | filter-stdlib-modules \
    | create
}

"$@"
