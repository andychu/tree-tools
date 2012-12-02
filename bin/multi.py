#!/usr/bin/python -S
"""Copy, move, or link files in a batch.

Usage:
  multi cp [<source-prefix>] [<dest-prefix>] [-- <cp-args>]
  multi mv [<source-prefix>] [<dest-prefix>] [-- <mv-args>]
  multi ln [<source-prefix>] [<dest-prefix>] [-- <ln-args>]

Examples:

  echo foo bar | multi cp

Lines Pairs of (source, dest) are read from stdin.  Te

Input syntax:

    App App.backup       # move App -> App.backup
    Tests                # move Tests -> Tests

The source and dest may not contain spaces.
"""

# TODO:
#
# Accept copy, move, link for readability?  Yes, it's like GNU long options.
#
# Make all the directories.


import os
import subprocess
import sys


class Error(Exception):
  pass


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

  # For now we buffer all input
  for (src, dest) in pairs:
    d = os.path.join(dest_base, dest)

    # TODO: Add extra args
    argv = [action, src, d]
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
