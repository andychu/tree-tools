#!/bin/bash
#
# multi-test.sh

multi() {
  bin/multi.py "$@"
}

readonly TEST_DIR=_tmp/multi-test

test-cp() {
  set -o errexit

  rm -rf $TEST_DIR  # TODO: shell framework needs functions for this

  mkdir -p $TEST_DIR/cp1
  echo Auto AA | multi cp $TEST_DIR/cp1

  mkdir -p $TEST_DIR/cp2
  multi cp $TEST_DIR/cp2 <<EOF
Auto
Tree.cfg foo/TT
EOF

  mkdir -p $TEST_DIR/cp3
  touch $TEST_DIR/cp3/file
  mkdir -p $TEST_DIR/cp3/dir
  ln -sf /tmp $TEST_DIR/cp3/link

  find $TEST_DIR/cp3 | multi cp $TEST_DIR/cp4

  # TODO: verify that Auto still has executable permissions.  This was a bug.
  tree -p _tmp/
}

# This fails because we passed --no-force to override.
# TODO: Should --force not be the default?
test-args() {
  multi cp $TEST_DIR/3 -- --no-force <<EOF
Auto
Tree.cfg Auto
EOF
  tree $TEST_DIR/3
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

  # --verbose so that we check permission bits
  tar --list --verbose -z <$TEST_DIR/test.tar.gz
}

test-empty-dir-made() {
  local src=$TEST_DIR/4
  rm -rf $src
  mkdir -p $src/dir
  touch $src/file

  find $src | multi cp $TEST_DIR/copy-4

  tree $TEST_DIR/copy-4
}

test-ln() {
  set -o errexit

  rm -rf $TEST_DIR  # TODO: shell framework needs functions for this

  multi ln $TEST_DIR/ln1 <<EOF
Auto
bin
Package foo
EOF

  tree $TEST_DIR
}

"$@"

