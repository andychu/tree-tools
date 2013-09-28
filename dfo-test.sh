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

  echo "filename with space contents" > 'bar/filename with space'

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

"$@"
