#!/usr/bin/python
"""
naming.py

Demo for DFO
"""

import sys
import base64
import hashlib
import string


class Error(Exception):
  pass


DIGITS = string.ascii_letters + '3'

# nonstandard: have vowels here?
# hard to read
B32_DIGITS = string.ascii_lowercase + 'AEIOUY'

# ugly
B32_DIGITS = string.ascii_lowercase + '=+:.;/'

# standard
B32_DIGITS = string.ascii_lowercase + '234567'


# naive implementation of base53
def b53(s):
  """
  s: byte string
  """
  n = 0
  for i, char in enumerate(s):
    n += ord(char) * (256 ** i)
  #print 'N', n

  digits = []
  while True:
    digit = n % 53
    digits.append(digit)
    n /= 53  # truncate
    if n == 0:
      break

  #print digits

  #print DIGITS

  result = ''
  for d in digits:
    result = DIGITS[d] + result

  return result


# naive implementation of base53
def b32(s):
  """
  s: byte string
  """
  n = 0
  for i, char in enumerate(s):
    n += ord(char) * (256 ** i)
  #print 'N', n

  digits = []
  while True:
    # TODO: bit mask and bit shift
    digit = n % 32
    digits.append(digit)
    n /= 32 # truncate
    if n == 0:
      break

  #print digits

  #print DIGITS

  result = ''
  for d in digits:
    result = B32_DIGITS[d] + result

  return result


# oh this is differnt than just doing the whole thing!  Because it's not an
# even fit.  That's not a great property.
# You want the property of having decimal points.

def b53sha1(s):
  b53chunks = []
  for i in xrange(4):
    group = s[i*5 : (i+1)*5]
    b53chunks.append(b53(group))

  b53chunks.reverse()
  return '-'.join(b53chunks)


def b32sha1(s):
  b32chunks = []
  for i in xrange(4):
    group = s[i*5 : (i+1)*5]
    b32chunks.append(b32(group))

  b32chunks.reverse()
  return '-'.join(b32chunks)


def group(s, chunk_len):
  chunks = []

  c = chunk_len
  n = len(s) / chunk_len
  for i in xrange(n):
    group = s[i*c : (i+1)*c]
    chunks.append(group)

  #chunks.reverse()
  return '-'.join(chunks)


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

  sha1bytes = c.digest()
  print repr(sha1bytes)
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


  #print 'b53'
  #print b53(sha1bytes)
  print 'b53 (31)\t', b53sha1(sha1bytes)
  print

  #print 'b32'
  #print b32(sha1bytes)
  print 'b32 (35)\t', b32sha1(sha1bytes)
  print

  # Try 8 groups
  arg_b32 = b32(sha1bytes)
  #print arg_b32

  print 'b32 (39)\t', group(arg_b32, 4)

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

  # base  ratio
  # 16    1:2 16^2 == 256^1                   256^(1/2)
  # 41    2:3                                 256^(2/3)
  # 64    3:4 64^4 == 256^3 == 16,777,216     256^(3/4)
  # 85    4:5 (4 chars to 5)  85^5   2^32 =   256^(4/5)
  #
  # 5/6 = 102 -- only 92 printable characters
  # 5/7 = 53.  Because sha1 divides into 4 groups of 5 bytes.  28+3 seps = 31 bytes.  more readable than 40.
  #   base64 would be 29 bytes, vs 31 bytes.  Probably worth it.
  # 5/8 = base32 exactly
  #   this could be 26 letters, and then 6 digits.  hm.
  #   8*4 + 3 == 35 characters
  # http://en.wikipedia.org/wiki/Base32

  # 53 is alpha+alpha.  And maybe 0 digit?  That is different than 0.
  # you could leave out 1 and l.

  # 10/13: base 72


  # properties:
  # - can be used in shell
  # - can be used in URL
  #   - if base53 uses the number 3 it could be that
  # can be written easily?  copied off of a screen?

  #  35 vs 31 bytes
  # 4 groups of 7 bytes
  # 4 groups of 8 bytes
  #
  # base32 already exists, can be read aloud easily
  #
  # 32 * 32 is 1024 initial directories (vs. 16*16 = 256).  This seems OK.

  # b32 is not that much more readable than base64?  It's better in that it has
  # no punctuation.  But capital letters don't seem to add much complexity.
  # They make it shorter.
  # Groups of 7 seems more readable than groups of 8 for b53.

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
