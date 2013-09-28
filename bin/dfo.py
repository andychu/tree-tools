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

from __future__ import with_statement

# options:
# pack:
#   - allow symlinks pointing outside the tree?
#   - follow symlinks (to /cas)?
# unpack:
#   - use cas to unpack?
#
# CGI mode?  For dynamically constructing packs?  Probably should just export
# it as a library.
#
# TODO:
# - implement unpack
# - round trip it
# - I guess you can do diff -R

import errno
import hashlib
import os
import stat
import sys

import docopt
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


# TODO: obj could be a file too?  Checksum it gradually.
def _WriteObj(outf, name, obj):
  #log('%r', sha1)

  # Write out path.  This is technically extraneous, but makes unpacking
  # faster.  We know where to put it, rather than having to write it out to a
  # tmp file, and then move it when we get its parent dir entry.
  #
  # Use dump_line (tag '\n') so it's a little more human-parseable.
  #
  # We are fixing the format to (path, contents, checksum) here, but additional
  # file metadata could be put in the dir formats?  (excluding the root).

  outf.write(tnet.dump_line(name))
  outf.write(tnet.dump_line(obj))
  # Then sha1.


def _PackTree(prefix, dir, outf, indent=0):
  """
  Args:
    dir: root directory
    outf: stream to decompress to

  Returns:
    Byte string representing the directory
  """
  ind = indent * '    '

  full_dir = os.path.join(prefix, dir)
  entries = sorted(os.listdir(full_dir))

  # list of (name, sha1, type, perms), sorted by name.
  # What does this return?  I guess it has checksums of every entry.  It
  # needs the names.
  #
  # (name, checksum, type, perms)


  # list of records
  # (TYPE, name, checksum)

  # (PUSH, name, '')
  # (FILE, name, contents)
  # (LINK, name, contents)
  # (POP, '', contents)  # contents contain permissions, checksums
  #
  # So dir is PUSH/POP.  Files/symlinks are single nodes.
  #
  # Dir looks like:
  #
  # PERMS TYPE CHECKSUM NAME
  # (type is redundant, but you wouldn't want changing a file to a symlink not
  # to change the dir checksum)
  #
  # then TRAILER containers the overall checksum?  No perms.

  this_dir = []

  for name in entries:
    rel_path = os.path.join(dir, name)
    path = os.path.join(prefix, rel_path)
    mode = os.lstat(path).st_mode

    if stat.S_ISLNK(mode):
      # contents of the blob is simply the target.
      obj = os.readlink(path)

      # In git, a symlink has type "blob" but has flags 120000.  We're using a
      # separate type.  We only have soft links -- no hard links now.
      node_type = 'L'
      outf.write(tnet.dump_line('L'))  # symlink
      _WriteObj(outf, name, obj)

    elif stat.S_ISDIR(mode):
      # TODO: Push 'name' here?  To help streams.
      outf.write(tnet.dump_line('>'))  # push
      outf.write(tnet.dump_line(name))
      outf.write(tnet.dump_line(''))  # no contents

      obj = _PackTree(prefix, rel_path, outf, indent+1)

      outf.write(tnet.dump_line('<'))  # pop
      outf.write(tnet.dump_line(''))
      outf.write(tnet.dump_line(obj))  # checksums, etc.

      # pop here: write out checksums, permissions, type
      node_type = 'D'

    elif stat.S_ISREG(mode):
      # TODO: stream this
      f = open(path)
      obj = f.read()
      f.close()

      node_type = 'F'
      outf.write(tnet.dump_line('F'))  # file
      _WriteObj(outf, name, obj)

    else:
      raise RuntimeError("Can't serialize %r, of type %o" % (name, mode))

    c = hashlib.sha1()
    c.update(obj)
    hex = c.hexdigest()

    # Git uses a binary format.  And then you can use git cat-file -p to pretty
    # print it.  I think it's fine just to use text.  No special tools needed.
    perms = stat.S_IMODE(mode)
    rec = (perms, node_type, hex, name)
    this_dir.append('%o %s %s %s' % rec)  # octal perms

  # TODO: output an object representing: (type, permissions)
  #log('---')
  #log('%s', '\n'.join(this_dir))
  #log('---')

  return '\n'.join(this_dir) + '\n'


def PackTree(d, outf):
  """Top level helper."""
  obj = _PackTree(d, '', outf)
  # write the final entry and checksum.
  _WriteObj(outf, '', obj)


def _MakeOneDir(dir):
  try:
    return os.mkdir(dir)
  except OSError, e:
    if e.errno != errno.EEXIST:
      raise


def _UnpackTree(in_file, dir):
  # algorithm:
  # 1. in a single pass, extract all the content to /_dfo-tmp/<sha1>, and
  # verify checksums.
  # 2. the LAST one is a directory.  Pase it.
  #  for each entry:
  #    if file, move it
  #    if symlink, create it
  #    if directory
  #      create it
  #      recurse using the that file checksum
  #    set permissions (executable)

  # I think we should only make one level -- not mkdir -p.
  log('making %s', dir)
  _MakeOneDir(dir)

  log('chdir %s', dir)
  os.chdir(dir)  # everything is relative to this dir

  while True:
    try:
      command = tnet.readbytes(in_file)
    except EOFError:
      break  # no more
    #print repr(command)

    try:
      name = tnet.readbytes(in_file)
    except EOFError:
      raise RuntimeError('Expected node name, got EOF')
    #print repr(name)

    try:
      contents = tnet.readbytes(in_file)
    except EOFError:
      raise RuntimeError('Expected contents, got EOF')
    #print repr(contents)

    if command == '>':
      log('> %s', name)
      _MakeOneDir(name)
      os.chdir(name)
    elif command == '<':
      # TODO:
      # - parse line
      # - chmod
      # - verify checksums
      log('<')
      os.chdir('..')
    elif command == 'F':
      log('F %s', name)
      with open(name, 'w') as f:
        f.write(contents)
    elif command == 'L':
      log('L %s', name)
      try:
        os.symlink(contents, name)
      except OSError, e:
        if e.errno != errno.EEXIST:
          raise RuntimeError('Error making symlink %r: %s' % (name, e))

    else:
      raise RuntimeError('Invalid command %r' % command)

  log('done unpack')


def main(argv):
  """Returns an exit code."""

  opts = docopt.docopt(__doc__, version='ftree 0.1')

  # I guess you could run this on plain file:
  # dfo read foo.  And then it could output that?

  if opts['pack']:
    d = opts['<dir>'] or ['.']
    outf = sys.stdout
    PackTree(d, outf)

  elif opts['unpack']:
    _UnpackTree(sys.stdin, opts['<dir>'])

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
