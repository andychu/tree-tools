#!/bin/bash
#
# Usage:
#   ./dfo-test.sh <function name>

create() {
  local out=_tmp/pack
  mkdir -p $out

  pushd $out

  mkdir -p bar
  echo "baz contents" > bar/baz
  chmod +x bar/baz
  echo "spam contents" > spam
  ln -s spam link

  popd

  bin/ftree $out
}

pack() {
  local out=_tmp/foo.dfo
  bin/dfo pack _tmp/pack >$out
  ls -al $out
  cat $out
  echo
}

unpack() {
  local out=_tmp/unpack2
  rm -rf $out
  cat _tmp/foo.dfo | bin/dfo unpack $out
  echo

  bin/ftree $out
}

"$@"
