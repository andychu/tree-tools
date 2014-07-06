#!/bin/bash
#
# Usage:
#   ./dfo-test.sh <function name>

. ~/hg/taste/taste.sh

create-tree() {
  local out=_tmp/pack
  mkdir -p $out

  pushd $out

  mkdir -p bar
  echo "baz contents" > bar/baz
  chmod +x bar/baz

  mkdir -p empty-dir

  echo "filename with space contents" > 'bar/filename with space'

  echo "spam contents" > spam
  ln -s spam link

  popd

  bin/ftree $out
}

test-pack() {
  local out=_tmp/foo.dfo
  bin/dfo pack _tmp/pack >$out
  expect $? -eq 0

  ls -al $out
  cat $out
  echo
}

test-unpack() {
  local out=_tmp/unpack
  rm -rf $out
  cat _tmp/foo.dfo | bin/dfo unpack $out
  echo

  bin/ftree $out
  tree -p _tmp/pack
  tree -p $out


  # Purposely corrupt it
  cat _tmp/foo.dfo |
    sed 's/spam contents/SPAM contents/' |
    bin/dfo unpack $out

  # Purposely corrupt a filename too
  cat _tmp/foo.dfo |
    sed 's/spam/SPAM/' |
    bin/dfo unpack $out
}

taste-main "$@"
