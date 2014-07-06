#!/bin/bash
#
# Usage:
#   ./val-perftest.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Results
#
# Original R .tar.gz    25.4 MB
# dfo.gz                25.5 MB   4.08 s
# dfo.bzip2             21.6 MB  17.24 s
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

  # bzip2 it
  if ! test -f $out.bz2; then
    time bzip2 <$out >$out.bz2
  fi
  ls -al $out.bz2

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
