#!/usr/bin/env python2
"""
py_deps_test.py: Tests for py_deps.py
"""

__author__ = 'Andy Chu'


import sys
import unittest

import py_deps  # module under test


class PyDepsTest(unittest.TestCase):

  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testModules(self):
    pairs = [ ( 'poly.util',
               'poly/util.py'),
              ( 'simplejson', 
                '/home/andy/dev/simplejson-2.1.5/simplejson/__init__.py')
              ]
    print list(py_deps.ModuleToRelativePath(pairs, 'main'))


if __name__ == '__main__':
  unittest.main()
