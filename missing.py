#!/usr/bin/env python3
# -*- coding: utf-8 -*-"

from collections import defaultdict
import operator
import os
import re
import subprocess
import sqlite3

from config import stable_path, stable_branches
from common import workdir, stabledb, upstreamdb, stable_branch

nowhere = open('/dev/null', 'w')

def get_status(sha):
  '''
  Check if patch needs to be applied to current branch.
  The working directory and branch must be set when calling
  this function.

  Return 0 if the patch has already been applied,
  1 if the patch is missing and applies cleanly,
  2 if the patch is missing and fails to apply.
  '''

  ret = 0

  os.system("git reset --hard HEAD > /dev/null 2>&1")

  try:
    result = subprocess.check_output(['git', 'cherry-pick', '-n', sha], stderr=nowhere)
    if result:
      ret = 2
    else:
      diff = subprocess.check_output(['git', 'diff', 'HEAD'])
      if diff:
        ret = 1
  except:
    ret = 2

  os.system("git reset --hard HEAD > /dev/null 2>&1")

  return ret

def missing(version):
  """
  Look for missing Fixup commits in provided stable release
  """

  bname = stable_branch(version)

  print("Checking branch %s" % bname)

  subprocess.check_output(['git', 'checkout', bname], stderr=nowhere)

  sdb = sqlite3.connect(stabledb(version))
  cs = sdb.cursor()
  udb = sqlite3.connect(upstreamdb)
  cu = udb.cursor()

  cs.execute("select sha, usha, description from commits where usha != ''")
  for (sha, usha, description) in cs.fetchall():
    cu.execute("select fsha, patchid from fixes where sha='%s'" % usha)
    for (fsha, patchid) in cu.fetchall():
      # print("SHA %s ('%s') fixed by %s" % (sha, description, fsha))
      cs.execute("select sha, usha from commits where usha is '%s'" % fsha)
      fix=cs.fetchone()
      if not fix:
        # The fix is not in our code base. Try to find it using its patch ID.
        # print(" SHA %s not found, trying patch ID based lookup" % fsha)
        cs.execute("select sha, usha from commits where patchid is '%s'" % patchid)
        fix=cs.fetchone()
        if not fix:
          status = get_status(fsha)
          if status != 0:
            print("SHA %s [%s] ('%s')" % (sha, usha, description))
            print("  fixed by upstream commit %s" % fsha)
            if status == 1:
              print("  Fix is missing from %s and applies cleanly" % bname)
            else:
              print("  Fix may be missing from %s; trying to apply it results in conflicts/errors" %
                    bname)

  udb.close()
  sdb.close()

def findmissing():
  os.chdir(stable_path)
  for b in stable_branches:
    missing(b)

findmissing()
