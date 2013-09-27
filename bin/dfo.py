#!/usr/bin/python -S
"""Serialize/Deserialize a file system tree.

Usage:
  dfo [options] read [<dir>...]
  dfo [options] write [<dir>...]
  dfo -h | --help
  dfo --version

Actions:
  read: read the given directory and output an archive stream to stdout.
  write: read archive stream from stdin, and write to the given directory.

Options:
  --indent=INDENT
      Number of spaces to indent.  (or character?)
"""

import hashlib
import os
import sys

import docopt

# Format
#
# 1/
#   2/
#     3
#     4
#   5/
#     6/
#       7
#   8
#
# Dirs: 1, 2, 5, 6
# files: 3 4 7 8
#
# Algorithm: write stream
#
# listdir
# the problem really is streaming
# can I do it in parallel?  disks aren't really parallel.  It's disk-bound, not
# CPU bound.  would only make sense if you actually spanned disks.
#
# Side note: the natural situation of a tree, for maximum read/write
# throughput, would be to spread it out on multiple disks.  shard it.  may be a
# cool trick.
#
# issue: don't know the parent checksum until you have written the child.  You
# could do that easily.  Just keep it in memory.
#
# Then the problem is that you can't decompress it.  You could have "hints"?
#
# (sha1, path, contents)
# (sha1, path, contents)
#
# Does it ever make sense to write symlinks?  To save space?
# could have dfo write --cas /cas or something.

def _ReadTree(dir, outf, indent=0):
  """
  Args:
    dir: root directory
    outf: stream to decompress to

  Returns:
    Byte string representing the directory
  """
  ind = indent * '    '
  entries = sorted(os.listdir(dir))
  dir_obj = []
  for entry in entries:
    # TODO: doing a stat is more efficient
    path = os.path.join(dir, entry)
    # This must come FIRST -- a directory can also be a link.
    if os.path.islink(path):
      target = os.readlink(path)
      outf.write('%s%s -> %s\n' % (ind, entry, target))

      # symlink: checksum
      obj = target
    elif os.path.isdir(path):
      outf.write(ind + entry + '/\n')  # trailing slash means dir
      obj = _ReadTree(path, outf, indent+1)
    else:
      # regular file: open it and checksum.
      outf.write(ind + entry + '\n')
      f = open(path)
      obj = f.read()
      f.close()

  # TODO: output an object representing: (type, permissions)
  return dir_obj


def ReadTree(dir):
  outf = sys.stdout
  _ReadTree(dir, outf)


def main(argv):
  """Returns an exit code."""

  opts = docopt.docopt(__doc__, version='ftree 0.1')

  # I guess you could run this on plain file:
  # dfo read foo.  And then it could output that?

  dirs = opts['<dir>'] or ['.']
  for d in dirs:
    #print d
    ReadTree(d)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError, e:
    print >>sys.stderr, e.args[0]
    sys.exit(1)
  except KeyboardInterrupt, e:
    print >>sys.stderr, '(dfo) Interrupted.'
    sys.exit(1)

