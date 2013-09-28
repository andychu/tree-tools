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

# Results
#
# Original R .tar.gz    25.4 MB
# dfo.gz                25.5 MB   4.08 s
# dfo.xz                18.9 MB  56.99 s  !

readonly R_TAR=~/hg/poly-runtimes/src/R-2.15.3.tar.gz

make-big-dfo() {
  set -x

  local tar=$R_TAR
  ls -al $(readlink -f $tar)
  local dir=_tmp/R
  if ! test -d $dir; then
    mkdir $dir
    tar --extract --checkpoint=1000 --file $tar --directory $dir
  fi

  du -hs $dir

  local out=_tmp/R.dfo
  if ! test -f $out; then
    bin/dfo pack $dir >$out
  fi

  ls -al $out

  # gzip it
  if ! test -f $out.gz; then
    time gzip <$out >$out.gz
  fi
  ls -al $out.gz

  # xz it
  if ! test -f $out.xz; then
    time xz <$out >$out.xz
  fi
  ls -al $out.xz
}

# Results:
#
# .tar   72.29 MB
# .dfo   72.31 MB
#
# Very slightly bigger, because of all the 40 byte checksums.  Could probably
# get it down by using 20 byte checksums.  Hm.

compare-uncompressed() {
  local out=_tmp/R-2.15.3.tar
  time gzip -d <$R_TAR >$out
  ls -al $out
  ls -al _tmp/R.dfo
}

"$@"
