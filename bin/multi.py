#!/usr/bin/python -S
"""Copy, move, link, or tar files in a batch.

Usage:
  multi cp [<source-prefix>] [<dest-prefix>] [ -- <cp-arg>... ]
  multi mv [<source-prefix>] [<dest-prefix>] [ -- <mv-arg>... ]
  multi ln [<source-prefix>] [<dest-prefix>] [ -- <ln-arg>... ]
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
# - implement ln and mv in-process
# - Accept copy, move, link for readability?  Yes, it's like GNU long options.
# - implement --force and --dereference
#   --force defaults to yes or no?
#
# The usage isn't right, we haven't implemented [source-prefix].  I should use
# docopt to fix this.
#
# Should we keep the ShellOut?  probably not... unless there are some obscure
# flags we need.
# I mean there is stuff like --interactive.  and recursive copy.  hm.


import errno
import os
import shutil
import subprocess
import stat
import sys
import tarfile


class Error(Exception):
  pass


def log(msg, *args):
  if args:
    msg = msg % args
  print >>sys.stderr, 'multi:', msg



def ShellOut(action, pairs, dest_base, extra_argv):
  """
  Slower implementation.  Do I need this?
  """
  #if action == 'cp':
  #  extra_argv = opts['<cp-arg>']
  #elif action == 'mv':
  #  extra_argv = opts['<mv-arg>']
  #elif action == 'cp':
  #  extra_argv = opts['<cp-arg>']
  #else:
  #  raise AssertionError(action)

  # For now we buffer all input
  for (src, dest) in pairs:
    d = os.path.join(dest_base, dest)

    # cp doesn't copy directories, so we should make them.
    # 'find' output often includes directories.
    if action == 'cp' and os.path.isdir(src):
      try:
        os.makedirs(d)
      except OSError, e:
        if e.errno != errno.EEXIST:
          raise
      continue

    # TODO: Do this more efficiently.
    m = ['mkdir', '-p', os.path.dirname(d)]
    #log('YAH\t$ %s', m)
    exit_code = subprocess.call(m)
    if exit_code != 0:
      raise Error('%s failed with code %s' % (argv, exit_code))

    argv = [action, '--force'] + extra_argv + [src, d]
    #log('\t$ %s', argv)
    exit_code = subprocess.call(argv)
    if exit_code != 0:
      raise Error('%s failed with code %s' % (argv, exit_code))


def RemoveDupes(pairs):
  # sort by the destination
  return sorted(set(pairs), key=lambda p: p[1])


def MultiTar(pairs, dest):
  """
  TODO: Does this handle symlinks and directories correctly?  Or does it
  dereference symlinks (which you don't want in general)?
  """
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


def _MakeLink(target, dest, force):
  # link to the same place as the source
  try:
    os.symlink(target, dest)
  except OSError, e:
    print target, dest
    if e.errno == errno.EEXIST:
      if force:
        os.remove(dest)
        os.symlink(target, dest)
      else:
        raise Error("Can't overwrite symlink %s" % dest)
    else:
      raise


class CopyHandler(object):
  """Copy a tree of files, dirs, symlinks.

  TODO:
  flags: --force means overwrite
         --dereference means to follow symlinks
  """

  def __init__(self, dest_base, force=False):
    self.dest_base = dest_base
    self.maker = DirMaker()
    self.force = force

  def OnFile(self, source, rel_dest):
    # TODO: may not want to allow dest to be an absolute path.  This violates
    # an invariant.

    dest = os.path.join(self.dest_base, rel_dest)
    self.maker.mkdir(os.path.dirname(dest))

    # NOTE: Permission bits are copied, but not stuff like mod time, which is
    # what we want.
    shutil.copy(source, dest)

  def OnDir(self, source, rel_dest):
    # make the dir
    dest = os.path.join(self.dest_base, rel_dest)
    self.maker.mkdir(dest)

  def OnLink(self, source, rel_dest):
    target = os.readlink(source)
    dest = os.path.join(self.dest_base, rel_dest)
    self.maker.mkdir(os.path.dirname(dest))

    _MakeLink(target, dest, self.force)


class LinkHandler(object):
  """Symlink files, dirs.

  TODO: links could have an optimization to dereference the target?
  """
  def __init__(self, dest_base, force=False):
    self.dest_base = dest_base
    self.maker = DirMaker()
    self.force = force

  def _Link(self, source, rel_dest):
    # for symlinks, resolve the symlink target with respect to the current
    # working directory.
    #
    # This lets us do something like 'echo Auto | multi ln some/other/dir'
    # We don't have to specify $PWD/Auto.
    #
    # NOTE: Would it be possible to calculate relative symlinks?
    # Instead of 
    #
    # _tmp/poly/dev/treemap -> /home/andy/hg/treemap/_tmp/app
    #
    # It would be nicer to have
    #
    # _tmp/poly/dev/treemap -> ../../app

    source = os.path.abspath(source)
    dest = os.path.join(self.dest_base, rel_dest)
    self.maker.mkdir(os.path.dirname(dest))

    _MakeLink(source, dest, self.force)

  def OnFile(self, source, rel_dest):
    self._Link(source, rel_dest)

  def OnDir(self, source, rel_dest):
    self._Link(source, rel_dest)

  def OnLink(self, source, rel_dest):
    self._Link(source, rel_dest)


def Dispatch(pairs, handler):
  """Read input files and pass them to a handler."""

  num_files = 0
  num_dirs = 0
  num_links = 0

  for (source, dest) in pairs:
    # lstat so we don't dereference symlinks.
    mode = os.lstat(source).st_mode
    # NOTE: test for link should come first
    if stat.S_ISLNK(mode):
      handler.OnLink(source, dest)
      num_links += 1
    elif stat.S_ISREG(mode):
      handler.OnFile(source, dest)
      num_files += 1
    elif stat.S_ISDIR(mode):
      handler.OnDir(source, dest)
      num_dirs += 1
    else:
      raise Error("Can only handle files, dirs, and symlinks: %r" % source)

  # TODO: put the action there
  log('copied %d files, %d dirs, %d links', num_files, num_dirs, num_links)
  # TODO: fix
  log('num mkdir syscalls: %d', handler.maker.num_mkdir)


class DirMaker(object):
  """
  More efficient way to do many os.makedirs().  This saves syscalls, and also
  doesn't have the dumb behavior of raising an error when the rightmost dir
  already exists.
  """
  def __init__(self, dest='.'):
    self.dest = dest
    self.made = {}  # cache of dirs we already made
    self.num_mkdir = 0  # assuming os.mkdir() is one syscall

  def mkdir(self, path):
    """
    Args:
      path: absolute or relative path

    Returns:
      None

    Raises:
      Error conditions:
      - can't mkdir over a file/symlink/etc.
      - permission error
    """
    # Don't try to make stuff we already made.  Lots of files will be in the
    # same dirs.
    if path in self.made:
      return
    self.made[path] = True

    #print 'mkdir', path, self.num_mkdir
    try:
      self.num_mkdir += 1
      os.mkdir(path)
    except OSError, e:
      #print e
      if e.errno == errno.ENOENT:   # parent doesn't exist
        # recurse: this ensures the parent exists
        self.mkdir(os.path.dirname(path))
        self.num_mkdir += 1
        os.mkdir(path)
      elif e.errno == errno.EEXIST:  # already exists
        pass
      else:
        raise  # permission errors, etc.


def main(argv):
  """Returns an exit code."""

  try:
    action = argv[1]
    dest_base = argv[2]
  except IndexError:
    raise Error(__doc__)

  pairs = []
  for line in sys.stdin:
    # allow comments and blank lines in specs.
    line = line.strip()
    if not line:
      continue
    if line.startswith('#'):
      continue

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


  # TODO:
  # - switch to docopt
  # - the default should be a more efficient internal version
  #   - but you will need to expose the full power of cp, ln, mv
  #   - for --overwrite, --no-dereference, etc.
  extra_argv = argv[4:]

  if action == 'tar':
    return MultiTar(pairs, dest_base)
  elif action == 'cp':
    # TODO: parse --force.  cp has it true by default, and has --no-clobber to
    # turn it off.  Hm.  I think maybe mine should be false.
    # Have to test 2 cases: symlinks and files.
    copy = CopyHandler(dest_base, force=True)
    return Dispatch(pairs, copy)
  elif action == 'ln':
    copy = LinkHandler(dest_base, force=True)
    return Dispatch(pairs, copy)
  else:
    ShellOut(action, pairs, dest_base, extra_argv)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >>sys.stderr, 'multi: ' + e.args[0]
    sys.exit(1)
