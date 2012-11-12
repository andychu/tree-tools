#!/bin/bash
#
# Tin toolkit.
#
# Draft of docopt:
#
# Usage:
#   tin create
#   tin py-imports
#   tin hg-info  # should these be exposed
#   tin build-normal
#   tin build-python
#   tin list <tin>
#   tin cat <tin> <path>...
#   tin -h | --help
#   tin --version
#
# Actions:
#
#   create      Read paths from stdin and create an archive.
#   py-imports  Use the Python interpreter to find the transitive closure of
#               imported modules.  Output is suitable for input to 'create'.
#               You should set PYTHONPATH.
#
#   build-normal  Short cut for create | py-imports
#   build-python  Like build-normal, but also set PYTHONPATH.
#
#   list        List the contents of a .tin file.
#   cat         Write individual files in a .tin to stdout.
#
# TODO:
#
#   Need to clean up build-normal vs build-python.  Maybe call it build-py.
#   Maybe get rid of build-normal?  Am I using it?
#
# Or maybe I should separate tin and py-imports?  They are already kind of
# separate.
# create: --set-pythonpath and --out
# py_imports: --no-mark (this should be deprecated)

_die() {
  echo 1>&2 "$@"
  exit 2
}

readonly THIS_DIR=$(cd $(dirname $0) && pwd)

# When running INSIDE a tin file (bootstrapped), TIN_EXTRACT_DIR will be set.
# In normal mode, just use this dir's parent (tintool, not tintool/bin)
TIN_BASE_DIR=${TIN_EXTRACT_DIR:-$(dirname $THIS_DIR)}

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
  shift
  test -n "$main_module" || _die "No main module given"
  py-imports-and-files "$main_module" \
    | create "$@"
}

build-python() {
  local main_module=$1
  shift
  test -n "$main_module" || _die "No main module given"
  py-imports-and-files "$main_module" \
    | create --set-pythonpath "$@"
}

# List the contents of a tin file.
list() {
  set -o nounset
  local tin_file=$1
  TIN_UNTAR=1 ./$tin_file | tar tvzf -
}

# Print a specific file.
cat() {
  set -o nounset
  local tin_file=$1
  shift
  TIN_UNTAR=1 ./$tin_file | tar --to-stdout -xvzf - "$@"
}

"$@"
