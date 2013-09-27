#!/usr/bin/python -S
"""Serialize/Deserialize a file system tree.

Usage:
  dfo [options] pack <dir>
  dfo [options] unpack <dir>
  dfo [options] verify [<archive>...]
  dfo -h | --help
  dfo --version

Actions:
  pack: read the given directory and output an archive stream to stdout.
    Does it make sense for this to take multiple dirs, or is that another tool?
  unpack: read archive stream from stdin, and write to the given directory.
  verify: check the integrity by going through checksums.
  id: read the value of a .dfo file?

Options:
  --indent=INDENT
      Number of spaces to indent.  (or character?)
"""
# options:
# pack:
#   - allow symlinks pointing outside the tree?
#   - follow symlinks (to /cas)?
# unpack:
#   - use cas to unpack?
#
# CGI mode?  For dynamically constructing packs?  Probably should just export
# it as a library.

import hashlib
import os
import sys

import docopt
# TODO:
import tnet


def log(msg, *args):
  if msg:
    msg = msg % args
  print >>sys.stderr, msg

# Format
#
# (header, sha1)
# (content, sha1) records
# (footer, sha1)
# should there be a sha1 of all of it?
# footer I think contains debug information -- it's not part of the logical
# content.  It's out of band debugging information.
#
# NOTE: The DFO format does NOT need to be seekable.  That's job is for the
# file system itself!  Unpack it!  Don't reinvent the file system.
#
# or maybe the header should be a file itself?
# e.g. _dfo_
#
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

def _PackTree(dir, outf, indent=0):
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
      #outf.write('%s%s -> %s\n' % (ind, entry, target))

      # symlink: checksum
      obj = target

      # TODO:
      Write(outf, obj)

    elif os.path.isdir(path):
      #outf.write(ind + entry + '/\n')  # trailing slash means dir

      # What does this return?  I guess it has checksums of every entry.  It
      # needs the names.
      #
      # (name, checksum, type, perms)

      obj = _PackTree(path, outf, indent+1)

    else:
      # regular file: open it and checksum.
      #outf.write(ind + entry + '\n')
      f = open(path)
      obj = f.read()
      f.close()

      c = hashlib.sha1()
      c.update(obj)
      sha1 = c.digest()
      #log('%r', sha1)

      outf.write(tnet.dumps(obj))
      outf.write(tnet.dumps(c.hexdigest()))

      # TODO:
      #Write(outf, obj)

      # should digests be hex?  tnet?
      # contents first, then digest




  # TODO: output an object representing: (type, permissions)
  return dir_obj


def _UnpackTree(f, dir):
  pass


def main(argv):
  """Returns an exit code."""

  opts = docopt.docopt(__doc__, version='ftree 0.1')

  # I guess you could run this on plain file:
  # dfo read foo.  And then it could output that?

  if opts['pack']:
    d = opts['<dir>'] or ['.']
    _PackTree(d, sys.stdout)
  elif opts['unpack']:
    _UnpackTree(sys.stdin, opts['<dir>'])
    print 'unpack'
  else:
    raise AssertionError('Invalid action')

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

