#!/usr/bin/python -S
"""
tin.py

Create an executable Python archive.  Eventually this should be a Polyglot
archive, with native executables, .so files to be uncompressed, shell scripts,
interpeters, etc.

TODO:

- Is there any reason to keep the .zip file support?  Maybe at some point you
  will need Windows support, but it's doubtful.  If clients ever run on Windows,
  they'll need some sort of POSIX environment (mingw and whatnot).

- Make everything read-only in order to prevent 2 copies started at the same
  time from interfering with ong another
- Make sure two different users running on the machine can't create files that
  interfere with each other.  (i.e. one can't read the files created by the
  other)
- Check that the *last* file in the archive, TIN/checksum, exists before
  starting the main program
- Don't change the working directory at startup; rather provide an environment
  variable to do it


FEATURES

- TIN_VERBOSE=1 shows debug information at runtime
- TIN_LIST=1 lists the contents of the file
- TODO: Do you need TIN_CAT to cat a specific file?  LIke the checksum?

- You build default flags into the archive.  Then the user can override them
  appending new values on the command line.
  - I would want --log-root to be the internal one
  - And --log-format for dev builds
- TIN/checksum is a checksum of each input file

NOTES

- build info (timestamp, hostname, current directory, etc.) is the
  responsibility of a separate process.  Put it in TIN/build-info
- This script depends on md5sum (could just busybox it)

Reasons to uncompress everything:

- The only thing that doesn't have to be uncompressed is .py files, which are
  small.  Native executables, .so files, shell scripts, etc. all need to be
  uncompressed.
- It's faster and simpler just to uncompress everything.  Requires less
  modification of the underlying code.
"""

__author__ = 'Andy Chu'


import cStringIO
import optparse
import os
import md5
import subprocess
import sys
import tarfile
import time
import zipfile


class Error(Exception):
  pass


# NOTE: Some boilerplate is duplicated from the .zip prelude below.

_TAR_PRELUDE = """\
#!/bin/sh -e

main_module='_MAIN_MODULE_'
checksum='_CHECKSUM_'
set_pythonpath='_SET_PYTHONPATH_'

log() {
  if test -n "$TIN_VERBOSE"; then
    echo 1>&2 '(tin)' "$@"
  fi
}

die() {
  echo 1>&2 "$@"
  exit 6  # exit code 1 is saved for the program
}

main() {
  # This is used for listing the contents of a .tin file, for examining
  # contents, etc.
  if test -n "$TIN_UNTAR"; then
    sed -e '1,/^exit$/d' "$0"
    exit 0
  fi

  log argv: "$@"
  local tmp=${TMP:-/tmp}
  local extract_dir=$tmp/tin-$checksum

  local extra_flags='_EXTRA_FLAGS_'

  if test -d "$extract_dir"; then
    log "$extract_dir exists"
  else
    log "extracting into $extract_dir"
    mkdir -p $extract_dir
    # Filter the payload in this file using sed, then pipe it to tar, which
    # reads from stdin and writes to $extract_dir.
    sed -e '1,/^exit$/d' "$0" | tar xzf - -C "$extract_dir"

    # TODO: test for the last file, which should be the manifest, here;
    # otherwise cleanup
  fi

  # We need to set PYTHONPATH for the executable (e.g. Poly) to run.  But if
  # that executable is spawning Python subprocesses, we don't want them to use
  # this PYTHONPATH.  So if it does this, it should set PYTHONPATH to
  # TIN_OLD_PYTHONPATH.
  if test "$set_pythonpath" = 1; then
    export TIN_OLD_PYTHONPATH=$PYTHONPATH
    export PYTHONPATH=$extract_dir
  fi

  # visible through /proc/PID/environ
  export TIN_EXTRACT_DIR=$extract_dir

  # If the first arg is --tin-info, just display a couple files and exit.
  if test "$1" = --tin-info; then
    echo CONTENTS
    echo
    cat $extract_dir/TIN/checksum
    echo
    cat $extract_dir/TIN/build-info
    exit 0
  fi

  # $extra_flags is optional, so no quotes
  log running: $extract_dir/$main_module $extra_flags "$@"
  exec $extract_dir/$main_module $extra_flags "$@"
}

main "$@"

# sed command above looks for this line.
exit
"""


# Port of Python _MAIN above.  If it gets complicated, we could revert ot
# Python.  But right now shell looks like it solves our problems.
_SHELL_PRELUDE = """\
#!/bin/sh

main_module='_MAIN_MODULE_'
checksum='_CHECKSUM_'
set_pythonpath='_SET_PYTHONPATH_'

log() {
  if test -n "$TIN_VERBOSE"; then
    echo 1>&2 '(tin-prefix)' "$@"
  fi
}

die() {
  echo 1>&2 "$@"
  exit 6  # exit code 1 is saved for the program
}

main() {
  log argv: "$@"
  local tmp=${TMP:-/tmp}
  local extract_dir=$tmp/tin-$checksum

  local extra_flags='_EXTRA_FLAGS_'

  if test -d "$extract_dir"; then
    log "$extract_dir exists"
  else
    # This exits 1 because 'unzip' doesn't like leading bytes
    log "Unzipping to $extract_dir"
    which unzip >/dev/null || die "Please install 'unzip' to run .tin files."
    unzip -qq -d "$extract_dir" $0
    # TODO: test for the last file, which should be the manifest, here;
    # otherwise cleanup
  fi

  # We need to set PYTHONPATH for the executable (e.g. Poly) to run.  But if
  # that executable is spawning Python subprocesses, we don't want them to use
  # this PYTHONPATH.  So if it does this, it should set PYTHONPATH to
  # TIN_OLD_PYTHONPATH.
  if test "$set_pythonpath" = 1; then
    export TIN_OLD_PYTHONPATH=$PYTHONPATH
    export PYTHONPATH=$extract_dir
  fi

  # visible through /proc/PID/environ
  export TIN_EXTRACT_DIR=$extract_dir

  # If the first arg is --tin-info, just display a file an exit
  if test "$1" = --tin-info; then
    cat $extract_dir/TIN/build-info
    exit 0
  fi

  # $extra_flags is optional, so no quotes
  log running: $extract_dir/$main_module $extra_flags "$@"
  exec $extract_dir/$main_module $extra_flags "$@"
}

main "$@"
# This prevents the rest of the zip file from executing
exit 0
"""

def log(msg, *args):
  if msg:
    msg = msg % args
  print >>sys.stderr, msg


def WritePrelude(zip_filename, prelude):
  f = open(zip_filename, 'rb')
  zip_contents = f.read()
  f.close()

  f = open(zip_filename, 'wb')
  f.write(prelude)
  f.write(zip_contents)
  f.close()

  os.chmod(zip_filename, 0755)


def Checksum(input_files):
  """Take the md5 a file containing the md5 of each individual file."""
  argv = ['md5sum'] + input_files
  p = subprocess.Popen(argv, stdout=subprocess.PIPE)
  out = p.stdout.read()
  exit_code = p.wait()
  assert exit_code == 0, exit_code
  checksum = md5.new(out)
  return checksum.hexdigest(), out


def CreateOptionsParser():
  parser = optparse.OptionParser()

  parser.add_option(
      '-o', '--output', dest='output', type='str', default='',
      help='Output name.  By default it will be determined from the executable')

  # TODO: reverse the default on this -- add the prelude to make it executable.
  parser.add_option(
      '--no-prelude', dest='no_prelude', action='store_true',
      help="Don't include a shell script prelude; make it a raw .tar.gz file")

  # This should prevent reliance on system libraries?  But allow stdlib.  TODO:
  # test it out.
  parser.add_option(
      '--set-pythonpath', dest='set_pythonpath', default=False,
      action='store_true',
      help='Whether to set PYTHONPATH in the shell prelude to the extraction '
           'dir.')

  # TODO: change default to .tar
  parser.add_option(
      '--kind', dest='kind', choices=['tar', 'zip'], default='tar',
      help='What kind of executable to output.')

  # TODO: Implement this
  #parser.add_option(
  #    '-e', '--env', dest='env', type='str', default='',
  #    help='Environment variable to set, e.g. NAME=value')

  # Other options:
  # - set the extract directory base, could be $TMP, $CHROOT_DIR, etc.
  return parser


DATA_FILE = 0
EXECUTABLE_FILE = 1

def ParseLines(lines):
  """
  Input file format:

  3 tokens: x filename, archive name
  2 tokens: filename, archive name
  1 token : filename and archive name
  """
  for line in lines:
    line = line.strip()
    parts = line.split(None, 2)
    if len(parts) == 3:
      f = parts[0]
      if f == 'x':
        file_type = EXECUTABLE_FILE
      elif f == 'f':
        file_type = DATA_FILE
      else:
        raise Error('Invalid file type %r in line %r' % (f, line))
      yield file_type, parts[1], parts[2]
    elif len(parts) == 2:
      yield DATA_FILE, parts[0], parts[1]
    else:
      yield DATA_FILE, parts[0], parts[0]


def main(argv):
  """Returns an exit code."""
  (options, argv) = CreateOptionsParser().parse_args(argv)
  extra_flags = argv[1:]

  # Make a first pass to find the main module
  entries = []
  main_modules = []
  for file_type, _, archive_name in ParseLines(sys.stdin):
    if file_type == EXECUTABLE_FILE:
      main_modules.append(archive_name)
    entries.append((file_type, _, archive_name))

  if len(main_modules) == 0:
    raise Error("Got no executables (with a leading 'x').")
  elif len(main_modules) == 1:
    main_module = main_modules[0]
  else:
    raise Error('Got duplicate executables: %s' % main_modules)

  default_out  = os.path.basename(main_module)
  default_out = os.path.splitext(default_out)[0] + '.tin'
  out_filename = options.output or default_out

  if options.kind == 'zip':
    # Write input files to a .zip
    input_files = []
    z = zipfile.ZipFile(out_filename, 'w', zipfile.ZIP_DEFLATED)
    for file_type, filename, archive_name in entries:
      log('%s -> %s', filename, archive_name)
      z.write(filename, archive_name)
      input_files.append(filename)

    checksum, checksum_file_contents = Checksum(input_files)
    checksum_name = 'TIN/checksum'
    z.writestr(checksum_name, checksum_file_contents)
    log('(computed checksum) -> %s', checksum_name)

    z.close()

    if options.set_pythonpath:
      set_pythonpath = '1'
    else:
      set_pythonpath = '0'
    prelude = _SHELL_PRELUDE.replace(
        '_MAIN_MODULE_', main_module).replace(
        '_CHECKSUM_', checksum).replace(
        '_EXTRA_FLAGS_', ' '.join(extra_flags)).replace(
        '_SET_PYTHONPATH_', set_pythonpath)
    WritePrelude(out_filename, prelude)
    log('Wrote %s with extra args %s', out_filename, extra_flags)

  else:

    # gzip decompression is used in the prelude.
    t = tarfile.open(out_filename, mode='w:gz')

    input_files = []
    for file_type, filename, archive_name in entries:
      log('%s -> %s', filename, archive_name)
      t.add(filename, arcname=archive_name)
      input_files.append(filename)

    checksum, checksum_file_contents = Checksum(input_files)
    checksum_name = 'TIN/checksum'

    c = cStringIO.StringIO(checksum_file_contents)

    tarinfo = tarfile.TarInfo(checksum_name)
    # TODO: user attributes?  do they matter?  We could use a temp file instead,
    # it might be easier.
    #
    # The stamping might need to happen at a later step, for caching.
    tarinfo.size = len(checksum_file_contents)
    tarinfo.mtime = time.time()  # if not set, GNU tar gives a warning.
    t.addfile(tarinfo, c)

    t.close()

    log('(computed checksum) -> %s', checksum_name)

    if options.no_prelude:
      log('Wrote tar %s', out_filename)
    else:
      if options.set_pythonpath:
        set_pythonpath = '1'
      else:
        set_pythonpath = '0'
      prelude = _TAR_PRELUDE.replace(
          '_MAIN_MODULE_', main_module).replace(
          '_CHECKSUM_', checksum).replace(
          '_EXTRA_FLAGS_', ' '.join(extra_flags)).replace(
          '_SET_PYTHONPATH_', set_pythonpath)

      WritePrelude(out_filename, prelude)
      log('Wrote self-extracting tar %s with extra args %s',
          out_filename, extra_flags)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
