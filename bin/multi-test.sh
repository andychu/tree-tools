#!/bin/bash
#
# multi-test.sh

multi() {
  bin/multi.py "$@"
}

test-basic() {
  set -o errexit

  local dir=_tmp/multi-test
  mkdir -p $dir/1
  echo Auto AA | multi cp $dir/1

  mkdir -p $dir/2
  multi cp $dir/2 <<EOF
Auto
Tree.cfg TT
EOF

  tree _tmp/
}

"$@"

