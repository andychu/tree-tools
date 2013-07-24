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
# The usage isn't right, we haven't implemented [source-prefix].  I should use
# docopt to fix this.
#
# Should we add an --internal or --shell options?  might be faster for a lot of
# cases.
#
# Accept copy, move, link for readability?  Yes, it's like GNU long options.
#
# Make all the directories.


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


class CopyHandler(object):
  def __init__(self, dest_base):
    self.dest_base = dest_base
    self.maker = DirMaker()

  def OnFile(self, source, rel_dest):
    # TODO: may not want to allow dest to be an absolute path.  This violates
    # an invariant.

    dest = os.path.join(self.dest_base, rel_dest)
    self.maker.mkdir(os.path.dirname(dest))

    # TODO: mkdir too
    shutil.copyfile(source, dest)

  def OnDir(self, source, rel_dest):
    # make the dir
    dest = os.path.join(self.dest_base, rel_dest)
    try:
      os.makedirs(dest)
    except OSError, e:
      if e.errno != errno.EEXIST:
        raise

  def OnLink(self, source, rel_dest):
    target = os.readlink(source)
    dest = os.path.join(self.dest_base, rel_dest)
    try:
      os.makedirs(os.path.dirname(dest))
    except OSError, e:
      if e.errno != errno.EEXIST:
        raise

    # link to the same place as the source
    try:
      os.symlink(target, dest)
    except OSError, e:
      print target, dest
      raise


def Dispatch(pairs, handler):
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


class DirMaker(object):
  """
  More efficient way to do many os.makedirs().  This saves syscalls, and also
  doesn't have the dumb behavior of raising an error when the rightmost dir
  already exists.
  """
  def __init__(self, dest='.'):
    self.dest = dest
    self.made = {}  # cache of dirs we already made

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
    # TODO: Use self.made
    try:
      os.makedirs(path)
    except OSError, e:
      if e.errno != errno.EEXIST:
        raise


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
    copy = CopyHandler(dest_base)
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
