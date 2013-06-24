#!/bin/bash
#
# tin-test.sh

smoke-test() {
  set -o errexit

  # DISABLED until we have the executable basis package.
  exit 0

  # Build tin.tin, then run it twice.
  TIN_VERBOSE=1 _tmp/out/tin.tin --tin-info
  TIN_VERBOSE=1 _tmp/out/tin.tin --tin-info

  # Try out the --no-prelude option.
  echo 'x Auto Auto' \
    | _tmp/out/tin.tin create --no-prelude --output _tmp/raw.tar.gz
}

if test $# -eq 0; then
  # Run all tests here
  smoke-test
else
  "$@"
fi
