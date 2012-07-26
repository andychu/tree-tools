#!/bin/sh
#
# build.sh
# Author: Andy Chu
#
# Build scripts for Poly

this_dir=$(cd $(dirname $0) && pwd)

. $this_dir/common.sh
. $this_dir/tin-info.sh

# Don't package any of these imports
STDLIB_DIR=/usr/lib/python

filter_modules() {
  grep -v $STDLIB_DIR
}

py_imports() {
  $this_dir/py_imports.py "$@"
}

tin() {
  $this_dir/tin.py "$@"
}

# Echos the files we need to stdout
poly_files_helper() {
  local main=$1
  py_imports $main bin.poly_config
  find \
    pgi_lib builtin_apps/home builtin_apps/HOST builtin_apps/META \
    builtin_apps/NODE \
    -type f \
    | egrep -v '\.pyc$'
}

tmpdir=/tmp

embedded_files() {
  local root=$1
  if test -z "$root"; then
    die "A root is required"
  fi
  # %p is the absolute path, %P is the relative path
  # Follow symlinks with -L
  run_cmd find -L $root -type f -printf '%p EMBEDDED/%P\n'
}

poly_files() {
  local main=$1
  local embedded_root=$2
  poly_files_helper $main | sort | uniq
  # static/ dir goes as is
  run_cmd find static -type f -printf '%p %p\n'
  if test -n "$embedded_root"; then
    embedded_files $embedded_root
  fi

  mkdir -p $tmpdir/TIN
  tin_info > $tmpdir/TIN/build-info
  # Add this file to the archive
  echo $tmpdir/TIN/build-info TIN/build-info
}

# Build the server with a given server module and possibly an app dir that
# should be embedded
# TODO: The usage of this function isn't terribly clear... "$@" can only be used
# with an embedded root.
build_server() {
  local server_module=$1
  local tin_out=$2
  shift 2
  poly_files $server_module | \
      filter_modules | \
      tin --output $tin_out -- "$@"
}

# This is a "less preferred" usage... normally you don't want to couple the
# server and the app together.
build_server_with_embedded_app() {
  local server_module=$1
  local embedded_root=$2
  shift 2
  poly_files $server_module $embedded_root | \
      filter_modules | \
      tin -- --local-root=EMBEDDED $more_flags "$@"
}

CHERRYPY_DIR=/tmp/poly-cherrypy

# Download and patch CherryPy
# Run this once per machine that you need to build the CherryPy server on
patch_cherrypy() {
  set -o errexit
  rm -rf "$CHERRYPY_DIR"
  mkdir -p $CHERRYPY_DIR
  cd $CHERRYPY_DIR  # pushd not supported with dash
  wget http://download.cherrypy.org/cherrypy/3.2.2/CherryPy-3.2.2.tar.gz
  tar xvfz CherryPy-3.2.2.tar.gz
  cd CherryPy-3.2.2
  cp $this_dir/../patches/post_listen_hook.patch .
  patch -p0 < post_listen_hook.patch
}


POLY_DIR=$(normpath $this_dir/..)
SIMPLEJSON_DIR=/home/andy/dev/simplejson-2.1.5

wsgiref() {
  local tin_out=$1
  test -n "$tin_out" || die "output file required"
  shift

  export PYTHONPATH=$POLY_DIR:$SIMPLEJSON_DIR
  build_server bin.poly_wsgiref $tin_out "$@"
}

# Build CherryPy version of server
cherry() {
  local tin_out=$1
  test -n "$tin_out" || die "output file required"
  shift

  # NOTE: This doesn't capture the _ssl.so dependency of CherryPy, which is
  # machine-specific.  There can be Python stdlib version mismatches.
  export PYTHONPATH=$POLY_DIR:$CHERRYPY_DIR/CherryPy-3.2.2
  build_server bin.poly_cherry $tin_out "$@"
}

# Build poly_config.tin
poly_config() {
  export PYTHONPATH=$POLY_DIR:$SIMPLEJSON_DIR
  py_imports bin.poly_config | \
    filter_modules | \
    tin
}

test_normpath() {
  # test our helper function
  normpath $this_dir
  normpath $this_dir/..
  normpath $this_dir/../poly
  pwd
}

"$@"

