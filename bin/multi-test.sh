#!/bin/bash
#
# multi-test.sh

multi() {
  bin/multi.py "$@"
}

readonly TEST_DIR=_tmp/multi-test

test-basic() {
  set -o errexit

  mkdir -p $TEST_DIR/1
  echo Auto AA | multi cp $TEST_DIR/1

  mkdir -p $TEST_DIR/2
  multi cp $TEST_DIR/2 <<EOF
Auto
Tree.cfg TT
EOF

  tree _tmp/
}

test-tar() {
  mkdir -p $TEST_DIR/tar
  # Test dupes
  multi tar $TEST_DIR/test.tar.gz <<EOF
Auto AA
Auto AA
Tree.cfg TT
Package dir/Package
README dir1/dir2/README
README   dir1/dir2/README
Auto Auto
Auto
EOF

  tar --list -z <$TEST_DIR/test.tar.gz
}

"$@"

