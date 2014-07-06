#!/usr/bin/python -S
"""Copy, move, link, or touch files in a batch.

A difference vs. doing find | xargs [cp/mv] is that we make the parent
directories.

Examples:

  echo foo bar | multi cp

Each line read from stdin specifies a file to be
copied/moved/linked/tarred.  It is either a filename by itself, or a pair of
filenames, separated by whitespace.  Filenames may not contain spaces.

Input syntax:

    App App.backup       # move App -> App.backup
    Tests                # move Tests -> Tests

LHS
  Path relative to current dir, or absolute path.

RHS
  Path relative to destination base (which defaults to current dir), or
  absolute path.  
  NOTE: With multi ln, when --relative is passed, the symlink target is
  relative to the symlink itself.

cp is different in that it duplicates the symlink literally, rather than
derefrencing it and copying contents.
"""

# TODO:
#
# - Accept copy, move, link for readability?  Yes, it's like GNU long options.
# - implement --force and --dereference
#   --force defaults to yes or no?
#
# The usage isn't right, we haven't implemented [source-prefix].
#
# Force people to pass empty source or not?
# multi cp '' /some/dest
#
# - multi touch <dest>
#   - for app bundle definition, e.g. special/tmp, special/dev/null

# BUGS:
# - Copying a file over itself raises an exception -- should be caught.
#   - e.g. echo foo | multi cp .


import errno
import optparse
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


def MultiMv(pairs, dest_base):
  """Move sets of any kind of file (including devices.)"""
  maker = DirMaker()

  input_files = []
  i = 0
  for source, rel_dest in pairs:
    log('%s -> %s', source, rel_dest)
    source = os.path.abspath(source)
    dest = JoinPath(dest_base, rel_dest)
    maker.mkdir(os.path.dirname(dest))

    os.rename(source, dest)
    i += 1

  log('moved %d files', i)
  return 0  # exit code


def RelativePath(left, right):
  """
  Given two absolute paths, calculate the path of 'left' relative to right.
  Note that this is always possible since / is a common root.
  """
  assert os.path.isabs(left) 
  assert os.path.isabs(right) 

  parts1 = left.split(os.sep)
  parts2 = right.split(os.sep)

  # n is the number of common parts 
  n = 0
  for p1, p2 in zip(parts1, parts2):
    if p1 != p2:
      break
    n += 1

  num_up = len(parts2) - n - 1

  rel_parts = ['..'] * num_up
  rel_parts.extend(parts1[n:])

  return '/'.join(rel_parts)


def MultiLn(pairs, dest_base, force=True, relative=False):
  """Create links to sets of any kind of file (including devices.)

  Args:
    force: whether to overwrite old files.
       TODO: This should be false by default?  It's only on because some
       AppBuild files produce duplicate entries, e.g.
       polyweb/app_root/examples/container/AppBuild.
    relative: whether to maek relative symlinks
  """
  maker = DirMaker()

  input_files = []
  i = 0
  for source, rel_dest in pairs:
    # TODO: what if input contains ../../ ?
    source = os.path.abspath(source)
    dest = JoinPath(dest_base, rel_dest)
    maker.mkdir(os.path.dirname(dest))
    #log('%s => %s', source, dest)

    # TODO: handle --relative
    # Algorithm:
    #
    # Turn both into absolute paths?  Using cwd?
    # Then find common prefix
    # Then calculate distance from common prefix to RHS (number of ../../../)
    # prepend that to the relative part

    if relative:
      # source is absolute.  dest must be made absolute, since dest_base may
      # have been relative.
      dest = os.path.abspath(dest)
      rel_source = RelativePath(source, dest)
      _MakeLink(rel_source, dest, force=force)
      log('%s -> %s', rel_source, dest)
    else:
      _MakeLink(source, dest, force=force)
      log('%s -> %s', source, dest)
    i += 1

  log('linked %d files', i)
  return 0  # exit code


def MultiTouch(files, dest_base, force=True):
  maker = DirMaker()
  for filename in files:
    path = JoinPath(dest_base, filename)
    log('%s', path)
    maker.mkdir(os.path.dirname(path))
    try:
      with open(path, 'w') as f:
        pass
    except IOError, e:
      # TODO: would be nice to print a nicer error
      log('FATAL: %s', e)
      return 1

  return 0  # exit code


# We have to use normpath because find output gives us stuff like:
#   ./deep/dir
# And we don't want:
#   dest/./deep/dir paths.
# 
# This messes up the DirMaker recursion.
# 
# normpath does not make a path absolute.

def JoinPath(base, rel):
  return os.path.normpath(os.path.join(base, rel))


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

    dest = JoinPath(self.dest_base, rel_dest)
    self.maker.mkdir(os.path.dirname(dest))

    # NOTE: Permission bits are copied, but not stuff like mod time, which is
    # what we want.
    shutil.copy(source, dest)

  def OnDir(self, source, rel_dest):
    # make the dir
    dest = JoinPath(self.dest_base, rel_dest)
    self.maker.mkdir(dest)

  def OnLink(self, source, rel_dest):
    target = os.readlink(source)
    dest = JoinPath(self.dest_base, rel_dest)
    self.maker.mkdir(os.path.dirname(dest))

    # Make the same symlink.
    _MakeLink(target, dest, self.force)


def Dispatch(pairs, handler):
  """Read input files and pass them to a handler."""

  num_files = 0
  num_dirs = 0
  num_links = 0

  for (source, dest) in pairs:
    # lstat so we don't dereference symlinks.
    mode = os.lstat(source).st_mode
    # NOTE: test for link has to come first.
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
  log('processed %d files, %d dirs, %d links', num_files, num_dirs, num_links)
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


def ContentLines(stdin):
  pairs = []
  for line in stdin:
    # allow comments and blank lines in specs.
    line = line.strip()
    if not line:
      continue
    if line.startswith('#'):
      continue
    yield line


def MakePairs(stdin):
  pairs = []
  for line in ContentLines(stdin):
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

    yield src, dest


USAGE = """\
multi [options] cp DEST
       multi [options] mv DEST
       multi [options] ln DEST

       multi [options] touch DEST\
"""
# The first 3 take pairs.  The 'touch' takes a file of paths.
# NOTE: Not advertising 'tar' because we generally don't want to use tar.

# -n / --preview: makes sense for all
# --force : makes sense for all
#   - it's the default now.  --no-force would be the opposite.
# --parents: is the default, don't need it
# -q / --quiet: don't print the summary at the end?
# -s: source prefix.  Will I ever use it?

def Options():
  """Returns an option parser instance."""
  # TODO: where to get version number from?
  p = optparse.OptionParser(USAGE, version='0.1')
  p.add_option(
      '-v', '--verbose', dest='verbose', action='store_true', default=False,
      help='Show verbose log messages')

  # This is used to control the help output.  The API is a little weird since
  # you pass p and then register with p.
  g = optparse.OptionGroup(p, "Flags specific to 'ln'", '')
  g.add_option(
      '-r', '--relative', dest='relative', action='store_true', default=False,
      help='Make symlinks with relative paths where possible (../.. '
           'target syntax)')

  p.add_option_group(g)
  return p


def main(argv):
  """Returns an exit code."""
  (opts, argv) = Options().parse_args(argv)

  try:
    action = argv[1]
  except IndexError:
    raise Error('Action required')

  # Check before we read from stdin.
  if action not in ('tar', 'cp', 'mv', 'ln', 'touch'):
    raise Error('Invalid action %r' % action)

  try:
    dest_base = argv[2]
  except IndexError:
    raise Error('Destination required')

  # Since there are so few options, we can validate these manually.
  if opts.relative and action != 'ln':
    raise Error("-r / --relative can't be used with %r" % action)

  if action == 'touch':
    files = list(ContentLines(sys.stdin))
    return MultiTouch(files, dest_base, force=True)
  else:
    pairs = list(MakePairs(sys.stdin))
    pairs = RemoveDupes(pairs)

  # TODO:
  # - the default should be a more efficient internal version
  #   - but you will need to expose the full power of cp, ln, mv
  #   - for --overwrite, --no-dereference, etc.
  # - should there be an --external or --exec flag?  Not sure we really need
  #   it.  What options would we use?
  extra_argv = argv[4:]

  if action == 'tar':
    return MultiTar(pairs, dest_base)

  elif action == 'mv':
    return MultiMv(pairs, dest_base)

  elif action == 'ln':
    return MultiLn(pairs, dest_base, force=True, relative=opts.relative)

  elif action == 'cp':
    # TODO: parse --force.  cp has it true by default, and has --no-clobber to
    # turn it off.  Hm.  I think maybe mine should be false.
    # Have to test 2 cases: symlinks and files.
    copy = CopyHandler(dest_base, force=True)
    return Dispatch(pairs, copy)

  else:
    raise AssertionError('Invalid action %r' % action)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    if e.args:
      print >>sys.stderr, 'multi:', e.args[0]
    sys.exit(1)
