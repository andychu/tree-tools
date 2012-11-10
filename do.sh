#!/bin/bash

unit() {
  "$@"
}

# TODO: Write an AUTO file that runs this.
all-unit-tests() {
  find . -name \*_test.py | sh -o xtrace -o errexit
}

smoke-test() {
  set -o errexit

  # Build tin.tin, then run it twice.
  ./BUILD.sh build-tar
  TIN_VERBOSE=1 ./tin.tin --tin-info
  TIN_VERBOSE=1 ./tin.tin --tin-info
}

list-tar() {
  tar -ztvf "$@"
}

"$@"
