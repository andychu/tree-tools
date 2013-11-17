#!/usr/bin/python
"""
naming.py

Demo for DFO
"""

import sys
import base64
import hashlib


class Error(Exception):
  pass


def vid(a):
  """Vat ID."""
  return '-'.join( ( a[0:9], a[9:18], a[18:27] ) ) 

def b64(c):
  return base64.b64encode(c.digest())

def main(argv):
  """Returns an exit code."""

  # More readable hashes


  # 160 bits, or 20 bytes
  c = hashlib.sha1()
  c.update(argv[1])
  print

  print repr(c.digest())
  print

  # 1:2 ratio (20 -> 40 bytes)
  print 'hex (40)\t', c.hexdigest()
  print

  # 3:4 ratio (20 -> 27 bytes)
  b = b64(c)
  print 'base64 (28)\t', b
  print

  print 'vat (29)\t', vid(b)
  print

  # I think it is good if we don't use the same syntax as git and hg.  It could
  # get confusing for beginners.

  # Urbit is 32 bits:
  # ~tasfyn-partyv
  # ~sivbud-barnel
  # ~tomsyt-balsen
  #
  # 128 bits:
  #  ~machec-binnev-dordeb-sogduc--dosmul-sarrum-faplec-nidted
  #
  # This is too long: 64


  # right now it is 7 -> 9 bytes?
  #
  # 20 bytes:
  #
  # split up into 2 groups of 10.  10->15 bytes.
  #
  # or 4 groups of 5.  5-> 8 bytes?  5 to 7 or 8 bytes?
  # then it will be

  # don't like / or + right now.

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
