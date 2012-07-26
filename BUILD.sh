#!/bin/bash
#
# BUILD.sh
#
# Usage:
#   ./BUILD.sh <action>

readonly CURRENT_VERSION=0.1.2

# This has a version-numbered filename.  The archive inside it doesn't.

release() {
  build
  local out=tin-$CURRENT_VERSION.zip
  rm $out
  zip $out tin.tin
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

_manifest() {
  # Generate build-info
  bin/tin.sh build-info-files
  echo 'x bin/tin.sh bin/tin.sh'
  find tin -type f -name \*.py -o -name \*.sh
}

# Build tin.tin
build() {
  _manifest | bin/tin.sh create
}

"$@"
