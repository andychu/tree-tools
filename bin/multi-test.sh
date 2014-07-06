#!/bin/bash
#
# multi-test.sh

. ~/hg/taste/taste.sh

# Bug: $0 changes when called by taste _gen.sh.
readonly this_dir=$(cd $(dirname $0) && pwd)

multi() {
  $this_dir/multi.py "$@"
}

test-invalid() {
  multi foo dest
  expect $? -eq 1
}

readonly TEST_DIR=_tmp/multi-test

test-cp-simple() {
  # TODO: taste needs functions for a per test case dir.  Set an enviroment
  # variable?
  rm -rf $TEST_DIR
  mkdir -p $TEST_DIR/cp1

  # Copy a single file
  echo Auto AA | multi cp $TEST_DIR/cp1

  find $TEST_DIR/cp1 >$TEST_DIR/manifest

  check_file_eq_stdin $TEST_DIR/manifest <<EOF
_tmp/multi-test/cp1
_tmp/multi-test/cp1/AA
EOF
}

test-cp-with-subdir() {
  mkdir -p $TEST_DIR/cp2

  # Copy a file, and make sure subdir foo is made.
  multi cp $TEST_DIR/cp2 <<EOF
Auto
Tree.cfg foo/TT
EOF

  # %M means print permission bits in symbolic form.
  find $TEST_DIR/cp2 -printf "%M %P\n" >$TEST_DIR/manifest

  # Verify that Auto still has executable permissions.  This was a bug.

  check_file_eq_stdin $TEST_DIR/manifest <<EOF
drwxrwxr-x 
-rwxr-xr-x Auto
drwxrwxr-x foo
-rw-r--r-- foo/TT
EOF
}

test-cp-with-symlink() {
  mkdir -p $TEST_DIR/cp3
  touch $TEST_DIR/cp3/file
  mkdir -p $TEST_DIR/cp3/dir
  ln -sf /tmp $TEST_DIR/cp3/link

  find $TEST_DIR/cp3 | multi cp $TEST_DIR/cp4

  tree -p $TEST_DIR/cp4

  # TODO: assert that we still have a symlink here
  find $TEST_DIR/cp4 -ls
}

# NOTE: there is no source.  We have to "cd" to do that?

test-mv() {
  mkdir -p $TEST_DIR/mv
  rm -rf $TEST_DIR/mv

  # setup
  echo Auto deep/dir/Auto | multi cp $TEST_DIR/mv/src
  tree _tmp

  # NOTE: What if we move the directory out from under a file?  Should we only
  # be allowed to move files and empty dirs?
  # We want this to be fast.  So we should be able to move dirs.  But in the
  # "prune" case, we are going to move files.

  # We may want to preserve the dir structure too.
  cd $TEST_DIR/mv/src && find . -type f | multi mv $TEST_DIR/mv/dest
  tree _tmp
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
  rm -rf $TEST_DIR

  # Test file, dir, and different name.
  multi ln $TEST_DIR/ln1 <<EOF
Auto
bin
Package foo
EOF

  # TODO: use "ftree" and assert output here.  It should have no lines so the
  # output is easier to type.
  #
  # ptree is for processes.
  tree $TEST_DIR
}

# TODO: Fix and test this case:
# $PWD/Auto by itself on a line doesn't make sense because you would try to
# copy or move it over itself.  You need the second thing.

test-ln-relative() {
  set -o errexit
  rm -rf $TEST_DIR

  # Test file, dir, and different name.
  multi ln --relative $TEST_DIR/ln2 <<EOF
$PWD/Auto Auto
$PWD/bin bin
$PWD/Package foo
EOF

  # TODO: use "ftree" and assert output here.  It should have no lines so the
  # output is easier to type.
  #
  # ptree is for processes.
  tree $TEST_DIR
}

test-touch() {
  multi touch _tmp/touch1 <<EOF
foo
bar/baz
EOF
  find _tmp/touch1

  # NOTE: This doesn't work, because foo is a file
  multi touch _tmp/touch2 <<EOF
foo1
foo1/bar
EOF
  find _tmp/touch2
}

taste-main "$@"
