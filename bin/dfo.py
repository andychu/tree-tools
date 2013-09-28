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
    note: we could output a text file compatible with sha1sum?  doesn't check
    file metadata though.
  verify: check the integrity by going through checksums.
  id: read the value of a .dfo file?
    that's at the end.  do I need a reverse offset at the end?

Options:
  --verbose=VERBOSE
      Show verbose logging.
"""

from __future__ import with_statement

# other actions
#   - unpack-content?  use sha1-named files
#   - index: create index of sha1.  for negotiation when transferring?

# options:
# pack:
#   - allow symlinks pointing outside the tree?
#   - follow symlinks (to /cas)?
# unpack:
#   - use cas to unpack?
# both:
#   - --progress like tar --checkpoint=1000
#
# CGI mode?  For dynamically constructing packs?  Probably should just export
# it as a library.
#
# TODO:
#
# - figure out the algorithm for reading the trailer.
#
# - implement streaming of files (on unpacking)
# - implement 'verify' action with verifier class
# - implement 'list' action
#
# - tests
#   - I guess you can do diff -R
#   - compare in size vs tar
#
# - package it
# - name it (kar?)
#
# - write documentation about the format (doc/dfo.txt)


import errno
import hashlib
import os
import stat
import sys

import docopt
import tnet


# Read/write large files in chunks of this size, so we dont' use too much
# memory.
CHUNK_SIZE = 1  # 1024 * 1024  # 1 MB 


def log(msg, *args):
  if msg:
    msg = msg % args
  print >>sys.stderr, msg


def _WriteChunk(outf, chunk):
  """Write a byte string in length-prefixed netstring format."""
  outf.write(tnet.dump_line(chunk))


def _WritePair(outf, cmd, name):
  """Write a 'cmd' pair in length-prefixed netstring format."""
  s = '%s %s' % (cmd, name)
  outf.write(tnet.dump_line(s))


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
  chunk_size = CHUNK_SIZE  # make this a flag for testing?

  this_dir = []
  this_count = 0

  full_dir = os.path.join(prefix, dir)
  entries = sorted(os.listdir(full_dir))

  for name in entries:
    rel_path = os.path.join(dir, name)
    path = os.path.join(prefix, rel_path)
    mode = os.lstat(path).st_mode

    checksum = None  # hex sha1

    if stat.S_ISLNK(mode):  # symlink
      # contents of the blob is simply the target.
      obj = os.readlink(path)

      # In git, a symlink has type "blob" but has flags 120000.  We're using a
      # separate type.  We only have soft links -- no hard links now.
      node_type = 'L'
      _WritePair(outf, node_type, name)
      _WriteChunk(outf, obj)
      this_count += 1

    elif stat.S_ISREG(mode):  # file
      node_type = 'F'
      _WritePair(outf, node_type, name)

      # Stream regular files so we don't take up too much memory.
      sha1 = hashlib.sha1()
      length = os.path.getsize(path)
      outf.write('%d:' % length)  # netstring prefix
      with open(path) as f:
        while True:
          chunk = f.read(chunk_size)
          if not chunk:  # EOF
            break
          outf.write(chunk)
          sha1.update(chunk)

      outf.write('\n')  # netstring suffix
      checksum = sha1.hexdigest()
      this_count += 1

    elif stat.S_ISDIR(mode):  # directory
      _WritePair(outf, '>', name)
      _WriteChunk(outf, '')  # no contents

      obj, node_count = _PackTree(prefix, rel_path, outf)  # recurse
      this_count += node_count + 1  # +1 for yourself

      # REDUNDANT name for extra integrity (and easier parsing).  Repeating
      # every dir name twice isn't significant size overhead in most cases.
      _WritePair(outf, '<', name)
      _WriteChunk(outf, obj)

      node_type = 'D'

    else:
      raise RuntimeError("Can't serialize %r, of type %o" % (name, mode))

    if not checksum:
      c = hashlib.sha1()
      c.update(obj)
      checksum = c.hexdigest()

    # Git uses a binary format.  And then you can use git cat-file -p to pretty
    # print it.  I think it's fine just to use text.  No special tools needed.
    perms = stat.S_IMODE(mode)

    # We ONLY care about the user's execute bit.  We have no concept of 'group'
    # and 'other' permissions.  We also don't care if a file is read-only --
    # that is controlled at a higher layer (per directory, not per file!).
    if node_type == 'F' and perms & stat.S_IXUSR:
      p = 'x' 
    else:
      p = '-'
    rec = (p, node_type, checksum, name)
    this_dir.append('%s %s %s %s' % rec)  # octal perms

  return '\n'.join(this_dir) + '\n', this_count


# Consider '> name' ''
#          'F name' contents
#          'L name' contents
#          '< '     contents
#
# The 'command' is the first two chars.

def PackTree(d, outf):
  """Top level helper."""

  # This is an 8 byte magic string: '5:dfo--\n'.  Can be used by 'file' to
  # identify a DFO stream.
  # We don't have any other info in the header now.  That could be addeed by
  # using 'dfo2-'?  Hopefully we won't need it.
  _WriteChunk(outf, 'dfo--')

  # First record is always '> .', and last one is always '< .'.  Period is not
  # a valid dir name, so it can be used.
  _WritePair(outf, '>', '.')
  _WriteChunk(outf, '')  # no contents

  obj, node_count = _PackTree(d, '', outf)

  _WritePair(outf, '<', '.')
  _WriteChunk(outf, obj)

  # Write out final checksum in trailer.
  c = hashlib.sha1()
  c.update(obj)
  checksum = c.hexdigest()

  _WriteChunk(outf, checksum)  # last record: current dir

  # TODO: put other stuff in the trailer?  stamp?  I think stamps can go in
  # internal files.
  log('checksum of %d nodes: %s', node_count, checksum)


def _MakeOneDir(dir):
  try:
    return os.mkdir(dir)
  except OSError, e:
    if e.errno != errno.EEXIST:
      raise


class Verifier(object):
  """Verifies that content has the expected checksums."""

  # Verifier can also track:
  # - stack too deep (1000)
  # - too many pops?

  def __init__(self):
    self.current = None  # list of actual entries in the current dir
    self.stack = []  # list of lists of actuals

  def Push(self):
    """Call on opening dir ('>' command)."""
    self.current = []
    self.stack.append(self.current)

  def Pop(self, dir_obj):
    """Call on closing dir ('<' command).

    Raises:
      RuntimeError: if there is a verification error, or other I/O error.
    """
    # TODO:
    # - parse line
    # - chmod
    # - verify checksums

    exec_mask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH  # x bit

    expected = []
    for line in dir_obj.splitlines():
      # split on single space, not whitespace, so we don't accept multiple
      # spaces, etc.  There's no reason to be more ambiguous than necessary.
      try:
        exec_bit, type, expected_checksum, name = line.split(' ', 3)
      except ValueError:
        raise RuntimeError('Invalid directory entry %r' % line)
      #print '.', perms, type, expected_checksum, name
      expected.append((name, expected_checksum))

      if exec_bit == 'x':
        mode = os.lstat(name).st_mode
        os.chmod(name, mode | exec_mask)  # add 3 x bits
      elif exec_bit == '-':
        pass
      else:
        raise RuntimeError('Invalid exec bit %r' % exec_bit)

    # TODO: Could display a nice diff here and so forth
    actual = self.current
    if expected == actual:
      log('Verified %d entries', len(expected))
    else:
      log('Actual:')
      for n, c in actual:
        log('    %s %s', n, c)
      log('Expected:')
      for n, c in expected:
        log('    %s %s', n, c)
      raise RuntimeError('Stream integrity error')

    self.stack.pop()
    if self.stack:
      self.current = self.stack[-1]

  def OnEntry(self, name, actual_checksum):
    """Call this on each ACTUAL entry in a dir."""
    self.current.append((name, actual_checksum))


def _UnpackTree(in_file, dir):
  # I think we should only make one level -- not mkdir -p.
  #log('making %s', dir)
  _MakeOneDir(dir)

  #log('chdir %s', dir)
  os.chdir(dir)  # everything is relative to this dir

  v = Verifier()

  # The last record is always the last <, where we return to 0.
  level = 0

  try:
    header = tnet.readbytes(in_file)
  except EOFError:
    raise RuntimeError('Expected DFO header, got EOF')
  if header != 'dfo--':
    raise RuntimeError("Expected 'dfo--' header, got %r" % header)
  
  while True:
    try:
      op = tnet.readbytes(in_file)
    except EOFError:
      break  # no more
    #log('%r', command)

    try:
      command, name = op.split(' ', 1)
    except ValueError:
      raise RuntimeError('Invalid op record %r' % op)

    # TODO: read length from stream.  Then read in CHUNK_SIZE chunks.  And checksum.
    c = hashlib.sha1()
    try:
      contents = tnet.readbytes(in_file)
    except EOFError:
      raise RuntimeError('Expected contents, got EOF')
    #print repr(contents)
    c.update(contents)
    actual_checksum = c.hexdigest()

    if command == '>':
      if name != '.':  # first record is '.'
        _MakeOneDir(name)
        os.chdir(name)

      v.Push()
      level += 1

    elif command == '<':
      v.Pop(contents)  # pass expected checksums and permissions to verify
      v.OnEntry(name, actual_checksum)  # add this dir entry

      level -= 1
      if level == 0:
        break

      if name != '.':
        os.chdir('..')

    elif command == 'F':
      # TODO: stream this.
      with open(name, 'w') as f:
        f.write(contents)

      v.OnEntry(name, actual_checksum)

    elif command == 'L':
      try:
        os.symlink(contents, name)
      except OSError, e:
        if e.errno != errno.EEXIST:
          raise RuntimeError('Error making symlink %r: %s' % (name, e))

      v.OnEntry(name, actual_checksum)

    else:
      raise RuntimeError('Invalid command %r' % command)

  try:
    root_checksum = tnet.readbytes(in_file)
  except EOFError:
    raise RuntimeError('Expected root checksum, got EOF')

  # if we get a checksum on stdout, that means it's OK.
  print root_checksum


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
