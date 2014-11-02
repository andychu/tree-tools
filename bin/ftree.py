#!/usr/bin/python -S
"""Show a file system tree.

Usage:
  ftree [options] [<dir>...]
  ftree -h | --help
  ftree --version

Options:
  --indent=INDENT
      Number of spaces to indent.  (or character?)
"""

import os
import stat
import sys

import docopt

# NOTE: This is forked from polyweb/app_root/examples/container/pages.py.
# Maybe replace it there.

# Options:
# - follow symlinks
# - show permissions
# - get rid of .hg/.git dirs?  Or maybe hide hidden . dirs?  Probably same -a
# syntax is useful.
#
#
# This should be used for BFO files too.

def _ListTree(dir, lines, indent=0):
  ind = indent * '    '
  entries = sorted(os.listdir(dir))
  for entry in entries:
    path = os.path.join(dir, entry)
    mode = os.lstat(path).st_mode
    # This must come FIRST -- a directory can also be a link.
    if stat.S_ISLNK(mode):
      target = os.readlink(path)
      lines.append('%s%s -> %s' % (ind, entry, target))
    elif stat.S_ISDIR(mode):
      lines.append(ind + entry + '/')  # trailing slash means dir
      _ListTree(path, lines, indent+1)
    else:
      # TODO: distinguish regular files from sockets, devices, etc.?
      lines.append(ind + entry)


def ListTree(dir):
  lines = []
  _ListTree(dir, lines)
  return '\n'.join(lines) + '\n'


def main(argv):
  """Returns an exit code."""

  opts = docopt.docopt(__doc__, version='ftree 0.1')

  dirs = opts['<dir>'] or ['.']
  for d in dirs:
    #print d
    print ListTree(d)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError, e:
    print >>sys.stderr, e.args[0]
    sys.exit(1)
  except KeyboardInterrupt, e:
    print >>sys.stderr, '(ftree) Interrupted.'
    sys.exit(1)

