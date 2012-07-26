#!/bin/sh
#
# tin-info.sh
# Author: Andy Chu
#
# Stuff that goes in the archive

tin_info() {
  echo 'BUILD DATE'
  date
  echo

  echo 'MACHINE'
  uname -a
  echo

  echo 'WORKING DIRECTORY'
  pwd
  echo

  echo 'USER'
  whoami
  echo

  echo 'REPOSITORY'
  hg log --verbose --limit 3 
  echo

  echo 'LOCAL CHANGES'
  hg status --exclude 'glob:**.pyc'
  echo
}
