#!/usr/bin/env python2
"""
multi_test.py: Tests for multi.py
"""

import unittest

import multi  # module under test


class MultiTest(unittest.TestCase):

  def testRelativePath(self):
    print multi.RelativePath('/foo/bar.txt', '/foo/link')
    print multi.RelativePath('/foo/bar.txt', '/foo/dir/link')

    print multi.RelativePath('/foo/bar/baz.txt', '/foo/link')
    print multi.RelativePath('/foo/bar/baz.txt', '/foo/dir/link')
    print multi.RelativePath('/foo/bar/baz.txt', '/foo/dir/dir2/link')


if __name__ == '__main__':
  unittest.main()
