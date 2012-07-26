#!/bin/bash
#
# BUILD.sh for the tin repository.
#
# Usage:
#   ./BUILD.sh <action>

this_dir=$(cd $(dirname $0) && pwd)

die() {
  echo 1>&2 "$@"
  exit 1
}

# Install the binaries that this hg repository exports into a directory.  It
# will overwrite them with name conflicts.
install() {
  local dest_dir=$1
  test -n "$dest_dir" || die "Usage: ./do.sh install <dest dir>"
  local bin_dir=$this_dir/bin
  ln -s --force --verbose \
    $bin_dir/tin.py $bin_dir/py_imports.py $bin_dir/tin-info.sh \
    $dest_dir
}

"$@"
