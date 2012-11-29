#!/usr/bin/python -S
"""
py_imports_test.py: Tests for py_imports.py
"""

__author__ = 'Andy Chu'


import sys
import unittest

import py_imports  # module under test


class PyImportsTest(unittest.TestCase):

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
    print list(py_imports.ModuleToRelativePath(pairs, 'main'))


if __name__ == '__main__':
  unittest.main()
