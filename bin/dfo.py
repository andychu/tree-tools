#!/usr/bin/python -S
"""Serialize/Deserialize a file system tree.

Usage:
  dfo [options] pack <dir>
  dfo [options] unpack <dir>
  dfo [options] list [<archive>...]
  dfo [options] verify [<archive>...]
  dfo -h | --help
  dfo --version

Actions:
  pack: read the given directory and output an archive stream to stdout.
    Does it make sense for this to take multiple dirs, or is that another tool?
  unpack: read archive stream from stdin, and write to the given directory.
  list: list filenames in the archive (requires linear scan through entire file)
  verify: check the integrity by going through checksums.
  id: read the value of a .dfo file?
    that's at the end.  do I need a reverse offset at the end?

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
#
# - implement verification, error checking
# - implement streaming of files
# - tests
#   - I guess you can do diff -R
# - condense the format to 2-tuples
# - write documentation about the format (doc/dfo.txt)


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


# TODO: obj could be a file too?  Checksum it gradually.
def _WriteObj(outf, name, obj):
  outf.write(tnet.dump_line(name))
  outf.write(tnet.dump_line(obj))


# FORMAT
#
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


def _PackTree(prefix, dir, outf, indent=0):
  """
  Args:
    dir: root directory
    outf: stream to decompress to

  Returns:
    Byte string representing the directory
  """
  ind = indent * '    '

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
      outf.write(tnet.dump_line('>'))  # push
      outf.write(tnet.dump_line(name))
      outf.write(tnet.dump_line(''))  # no contents

      obj = _PackTree(prefix, rel_path, outf, indent+1)

      outf.write(tnet.dump_line('<'))  # pop
      _WriteObj(outf, name, obj)

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

  return '\n'.join(this_dir) + '\n'


# TODO: This should be:
# PackDir
#   PackNode -- this has a switch, one of which calls PackDir
# 
# Consider '> name' ''
#          'F name' contents
#          'L name' contents
#          '< '     contents
#
# The 'command' is the first two chars.

def PackTree(d, outf):
  """Top level helper."""

  # TODO: header?  Or maybe the trailer is all I need.
  # Header is where you would put a version number.

  # to balance < and >, the top level has no name.
  outf.write(tnet.dump_line('>'))  # push
  outf.write(tnet.dump_line(''))
  outf.write(tnet.dump_line(''))  # no contents

  obj = _PackTree(d, '', outf)

  outf.write(tnet.dump_line('<'))  # last record: current dir
  _WriteObj(outf, '', obj)

  # Write out final checksum in trailer.
  c = hashlib.sha1()
  c.update(obj)
  hex = c.hexdigest()

  outf.write(tnet.dump_line(hex))  # last record: current dir

  # TODO: put other stuff here?  stamp?  I think stamps can go in internal
  # files.
  node_count = 0  # TODO
  log('checksum of %d files: %s', node_count, hex)


def _MakeOneDir(dir):
  try:
    return os.mkdir(dir)
  except OSError, e:
    if e.errno != errno.EEXIST:
      raise


# TODO: Should be Pop()
def _FinishDir(contents):
  """chmod and verify.

  Raises:
    RuntimeError on any verification errors.
  """
  log('chmod and verify %s', contents)
  for line in contents.splitlines():
    print repr(line)
    # name can have spaces in it
    mode, expected_type, expected_sum, name = line.split(None, 3)
    print mode
    print expected_type
    print expected_sum
    print name


def _UnpackTree(in_file, dir):
  # I think we should only make one level -- not mkdir -p.
  log('making %s', dir)
  _MakeOneDir(dir)

  log('chdir %s', dir)
  os.chdir(dir)  # everything is relative to this dir

  # we verify one dir at at time
  # (actual name, actual checksum) pairs.
  # this needs a cursor?
  # Verifier()
  #   Push()
  #   OnEntry()  # add actual
  #   Pop()  # get expected, then verifies it
  #
  # Verifier can also track:
  # - stack too deep (1000)

  to_verify = []

  # The last record is always the last <, where we return to 0.
  level = 0
  
  while True:
    try:
      command = tnet.readbytes(in_file)
    except EOFError:
      break  # no more
    log('%r', command)

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
      if name:
        log('> %s', name)
        _MakeOneDir(name)
        os.chdir(name)
      else:
        log('BEGIN')
      level += 1
      #to_verify.append([])

    elif command == '<':
      # TODO:
      # - parse line
      # - chmod
      # - verify checksums
      log('<')
      _FinishDir(contents)
      level -= 1
      if level == 0:
        log('DONE')
        break

      # NOTE: special last case: if you're at /, this will just put you back at
      # /?
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

  try:
    root_checksum = tnet.readbytes(in_file)
  except EOFError:
    raise RuntimeError('Expected root checksum, got EOF')

  log('%s ok', root_checksum)


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
    print >>sys.stderr, 'dfo: fatal: %s' % e.args[0]
    sys.exit(1)
  except KeyboardInterrupt, e:
    print >>sys.stderr, '(dfo) Interrupted.'
    sys.exit(1)
