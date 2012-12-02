#!/usr/bin/python -S
"""Copy, move, or link files in a batch.

Usage:
  multi cp [<source-prefix>] [<dest-prefix>]
  multi mv [<source-prefix>] [<dest-prefix>]
  multi ln [<source-prefix>] [<dest-prefix>]

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


import sys


class Error(Exception):
  pass


def main(argv):
  """Returns an exit code."""
  for line in sys.stdin:
    parts = line.split(None, 2)
    print parts

  print 'Hello from multi.py'
  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
