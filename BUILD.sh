#!/bin/bash
#
# do.sh
#
# Usage:
#   ./do.sh <action>

readonly CURRENT_VERSION=0.1.1

release() {
  local out=tin-$CURRENT_VERSION.zip
  rm $out
  # Don't include this do.sh script!
  zip $out \
    bin/*.py bin/*.sh BUILD.sh PROVIDES.sh
  unzip -l $out
}

get-uploader() {
  mkdir _tmp
  wget -O _tmp/googlecode_upload.py \
    http://support.googlecode.com/svn/trunk/scripts/googlecode_upload.py
  chmod +x _tmp/googlecode_upload.py
}

upload() {
  _tmp/googlecode_upload.py \
      -s "Tin $CURRENT_VERSION" \
      -p tintool \
      tin-$CURRENT_VERSION.zip
}

"$@"
