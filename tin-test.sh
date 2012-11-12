#!/bin/bash
#
# tin-test.sh
# Author: Andy Chu
#
# Usage:
#   FILL IN

smoke-test() {
  set -o errexit

  # Build tin.tin, then run it twice.
  ./BUILD.sh build
  TIN_VERBOSE=1 ./tin.tin --tin-info
  TIN_VERBOSE=1 ./tin.tin --tin-info
}

"$@"
