#!/usr/bin/python -S
"""Copy, move, link, or tar files in a batch.

Usage:
  multi cp [<source-prefix>] [<dest-prefix>] [-- <cp-args>]
  multi mv [<source-prefix>] [<dest-prefix>] [-- <mv-args>]
  multi ln [<source-prefix>] [<dest-prefix>] [-- <ln-args>]
  multi tar [<dest-file>]

Examples:

  echo foo bar | multi cp

Each line read from stdin specifies a file to be
copied/moved/linked/tarred.  It is either a filename by itself, or a pair of
filenames, separated by whitespace.  Filenames may not contain spaces.

Input syntax:

    App App.backup       # move App -> App.backup
    Tests                # move Tests -> Tests
"""

# TODO:
#
# Accept copy, move, link for readability?  Yes, it's like GNU long options.
#
# Make all the directories.


import os
import subprocess
import sys
import tarfile


class Error(Exception):
  pass


def log(msg, *args):
  if args:
    msg = msg % args
  print >>sys.stderr, 'multi:', msg


def RemoveDupes(pairs):
  # sort by the destination
  return sorted(set(pairs), key=lambda p: p[1])


def MultiTar(pairs, dest):
  # gzip compression.
  t = tarfile.open(dest, mode='w:gz')

  input_files = []
  for filename, archive_name in pairs:
    log('%s -> %s', filename, archive_name)
    t.add(filename, arcname=archive_name)
    input_files.append(filename)
  t.close()

  log('Wrote %s', dest)
  return 0  # exit code


def main(argv):
  """Returns an exit code."""

  try:
    action = argv[1]
    dest_base = argv[2]
  except IndexError:
    raise Error(__doc__)

  pairs = []
  for line in sys.stdin:
    parts = line.split(None, 1)
    if len(parts) == 1:
      src = parts[0]
      dest = parts[0]
    elif len(parts) == 2:
      src = parts[0]
      dest = parts[1]
    else:
      raise AssertionError
    src = src.strip()
    dest = dest.strip()

    pairs.append((src, dest))

  pairs = RemoveDupes(pairs)

  if action == 'tar':
    return MultiTar(pairs, dest_base)

  # For now we buffer all input
  for (src, dest) in pairs:
    d = os.path.join(dest_base, dest)

    # TODO: Do this more efficiently.
    m = ['mkdir', '-p', os.path.dirname(d)]
    log('\t$ %s', m)
    exit_code = subprocess.call(m)
    if exit_code != 0:
      raise Error('%s failed with code %s' % (argv, exit_code))

    # TODO: Add extra args
    argv = [action, '--force', src, d]
    log('\t$ %s', argv)
    exit_code = subprocess.call(argv)
    if exit_code != 0:
      raise Error('%s failed with code %s' % (argv, exit_code))

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
