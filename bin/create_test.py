#!/usr/bin/env python2
"""
create_test.py: Tests for create.py
"""

__author__ = 'Andy Chu'


import sys
import unittest

import create  # module under test


class TinTest(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testChecksum(self):
    print create.Checksum([sys.argv[0]])

  def testParseLines(self):
    print list(create.ParseLines([
      '/tmp/foo foo',
      'foo',
      'f /tmp/bar bar',
      'x /tmp/bin bin',
      ]))


if __name__ == '__main__':
  unittest.main()
