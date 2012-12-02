#!/bin/bash
#
# tin-test.sh

smoke-test() {
  set -o errexit

  # Build tin.tin, then run it twice.
  TIN_VERBOSE=1 _tmp/out/tin.tin --tin-info
  TIN_VERBOSE=1 _tmp/out/tin.tin --tin-info
}

if test $# -eq 0; then
  # Run all tests here
  smoke-test
else
  "$@"
fi
