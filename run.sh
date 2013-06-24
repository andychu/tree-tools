#!/bin/bash

unit() {
  "$@"
}

# TODO: Write an AUTO file that runs this.
all-unit-tests() {
  find . -name \*_test.py | sh -o xtrace -o errexit
}

"$@"
