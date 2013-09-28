#!/usr/bin/python -S
"""Serialize/Deserialize a file system tree.

Usage:
  dfo [options] pack <dir>
  dfo [options] unpack <dir>
  dfo [options] verify [<archive>...]
  dfo [options] list [<archive>...]
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
  --verbose=VERBOSE
      Show verbose logging.
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
#   - the verify command should use the Verifier class
# - implement streaming of files (on unpacking)
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


# TODO: change to a single pair
def _WritePair(outf, cmd, name):
  outf.write(tnet.dump_line(cmd))
  outf.write(tnet.dump_line(name))


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

def _PackTree(prefix, dir, outf):
  """
  Args:
    prefix: root directory
    dir: current dir
    outf: stream to decompress to

  Returns:
    Byte string representing the directory
  """
  chunk_size = 1  # 1024 * 1024  # 1 MB -- make this a flag for testing?

  this_dir = []
  this_count = 0

  full_dir = os.path.join(prefix, dir)
  entries = sorted(os.listdir(full_dir))

  for name in entries:
    rel_path = os.path.join(dir, name)
    path = os.path.join(prefix, rel_path)
    mode = os.lstat(path).st_mode

    hex = None

    if stat.S_ISLNK(mode):  # symlink
      # contents of the blob is simply the target.
      obj = os.readlink(path)

      # In git, a symlink has type "blob" but has flags 120000.  We're using a
      # separate type.  We only have soft links -- no hard links now.
      node_type = 'L'
      _WritePair(outf, node_type, name)
      outf.write(tnet.dump_line(obj))
      this_count += 1

    elif stat.S_ISREG(mode):  # file
      node_type = 'F'
      _WritePair(outf, node_type, name)

      # Stream regular files so we don't take up too much memory.
      checksum = hashlib.sha1()
      length = os.path.getsize(path)
      outf.write('%d:' % length)  # netstring prefix
      with open(path) as f:
        while True:
          chunk = f.read(chunk_size)
          if not chunk:  # EOF
            break
          outf.write(chunk)
          checksum.update(chunk)

      outf.write('\n')  # netstring suffix
      hex = checksum.hexdigest()
      this_count += 1

    elif stat.S_ISDIR(mode):  # directory
      _WritePair(outf, '>', name)
      outf.write(tnet.dump_line(''))  # no contents

      obj, node_count = _PackTree(prefix, rel_path, outf)  # recurse
      this_count += node_count + 1  # +1 for yourself

      _WritePair(outf, '<', '')  # no name
      outf.write(tnet.dump_line(obj))

      node_type = 'D'

    else:
      raise RuntimeError("Can't serialize %r, of type %o" % (name, mode))

    if not hex:
      c = hashlib.sha1()
      c.update(obj)
      hex = c.hexdigest()

    # Git uses a binary format.  And then you can use git cat-file -p to pretty
    # print it.  I think it's fine just to use text.  No special tools needed.
    perms = stat.S_IMODE(mode)
    rec = (perms, node_type, hex, name)
    this_dir.append('%o %s %s %s' % rec)  # octal perms

  return '\n'.join(this_dir) + '\n', this_count


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

  # To balance < and >, the top level has no name.
  _WritePair(outf, '>', '')
  outf.write(tnet.dump_line(''))  # no contents

  obj, node_count = _PackTree(d, '', outf)

  _WritePair(outf, '<', '')  # no name
  outf.write(tnet.dump_line(obj))

  # Write out final checksum in trailer.
  c = hashlib.sha1()
  c.update(obj)
  hex = c.hexdigest()

  outf.write(tnet.dump_line(hex))  # last record: current dir

  # TODO: put other stuff here?  stamp?  I think stamps can go in internal
  # files.
  log('checksum of %d nodes: %s', node_count, hex)


def _MakeOneDir(dir):
  try:
    return os.mkdir(dir)
  except OSError, e:
    if e.errno != errno.EEXIST:
      raise


class Verifier(object):
  """Verifies that content has the expected checksums."""

  def __init__(self):
    self.current = None  # list of actual entries in the current dir
    self.stack = []  # list of lists of actuals

  def Push(self):
    """Call on opening dir ('>' command)."""
    self.current = []
    self.stack.append(self.current)

  def Pop(self, expected):
    """Call on closing dir ('<' command).

    Raises:
      RuntimeError: if something doesn't match.
    """
    # TODO:
    # - compared expected vs self.current

    self.stack.pop()

  def OnEntry(self, entry):
    """Call this on each entry in a dir."""
    self.current.append(entry)  # actual entry


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

  v = Verifier()

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
      v.Push()
      level += 1
      #to_verify.append([])

    elif command == '<':
      # TODO:
      # - parse line
      # - chmod
      # - verify checksums
      log('<')
      v.Pop(contents)
      level -= 1
      if level == 0:
        log('DONE')
        break

      # NOTE: special last case: if you're at /, this will just put you back at
      # /?
      os.chdir('..')

    elif command == 'F':
      log('F %s', name)
      # TODO: stream it
      with open(name, 'w') as f:
        f.write(contents)

      v.OnEntry(contents)

    elif command == 'L':
      log('L %s', name)
      try:
        os.symlink(contents, name)
      except OSError, e:
        if e.errno != errno.EEXIST:
          raise RuntimeError('Error making symlink %r: %s' % (name, e))

      v.OnEntry(contents)

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
