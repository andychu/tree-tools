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

# When running INSIDE a tin file (bootstrapped), TIN_EXTRACT_DIR will be set.
# In normal mode, just use the current dir.
TIN_BASE_DIR=${TIN_EXTRACT_DIR:-.}

filter-stdlib-modules() {
  readonly STDLIB_DIR=/usr/lib/python
  grep -v $STDLIB_DIR
}

# define 3 binaries in the bin/ dir

py-imports() {
  $TIN_BASE_DIR/tin/py_imports.py "$@"
}

create() {
  $TIN_BASE_DIR/tin/create.py "$@"
}

hg-info() {
  $TIN_BASE_DIR/tin/hg-info.sh "$@"
}

# BUILD


# Generate the build info file, and echo it to stdout to be piped into 'tin
# create'.
build-info-files() {
  local tmpdir=/tmp  # TODO: a better choice
  mkdir -p $tmpdir/TIN
  hg-info > $tmpdir/TIN/build-info
  # Add this file to the archive
  echo $tmpdir/TIN/build-info TIN/build-info
}

py-imports-and-files() {
  build-info-files
  py-imports "$@"
}


# Common build.  You can add your own data with a custom pipeline.
build-normal() {
  local main_module=$1
  test -n "$main_module" || _die "No main module given"
  py-imports-and-files "$main_module" \
    | filter-stdlib-modules \
    | create
}

build-python() {
  local main_module=$1
  test -n "$main_module" || _die "No main module given"
  py-imports-and-files "$main_module" \
    | filter-stdlib-modules \
    | create --set-pythonpath
}

"$@"
