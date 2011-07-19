#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to create lots of batches for Geograph

'''
import sys, os.path, glob, re, urllib, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, query
import shutil
from subprocess import *

def getWorkList(start, end):
    result = []
    i = int(start)
    while i <= int(end):
	if i < 100:
	    baseid = u'00'
	    setid = u'%.2d' % (i,)
	else:
	    baseid = u'01'
	    setid = u'%.2d' % (i-100,)
	result.append((baseid, setid))
	i = i + 1

    return result


def generateBatch(baseid, setid):
    python_p = Popen(["/usr/bin/python", " /home/multichill/bot/geograph/batch_generator.py " " /mnt/user-store/geograph_new/%s/%s/ " % (baseid, setid), " /mnt/user-store/geograph_new_output/%s/%s/ " % (baseid, setid)], stdout=PIPE)
    tail_p = Popen(["tail", "-1000"], stdin=python_p.stdout, stdout=PIPE)
    mail_p = Popen(["mail", "-s \"Created batch %s-%s\" multichill@toolserver.org" % (baseid, setid)], stdin=tail_p.stdout, stdout=PIPE)
    mail_p.communicate()[0]

    tar_p = Popen(["/bin/tar", "-cvf", "/mnt/user-store/geograph_new_output/%s/batch_%s.tar" % (baseid, setid), "/mnt/user-store/geograph_new_output/%s/%s/*" % (baseid, setid)], stdout=PIPE)
    cat_p = Popen(["cat", "-n"], stdin=tar_p.stdout, stdout=PIPE)
    tail2_p = Popen(["tail"], stdin=cat_p.stdout, stdout=PIPE)
    mail2_p = Popen(["mail", "-s \"Tarred batch %s-%s\" multichill@toolserver.org" % (baseid, setid)], stdin=tail2_p.stdout, stdout=PIPE)
    mail2_p.communicate()[0]

    return


def main(args):
    '''
    Main loop.
    '''

    if(len(args)==2):
	worklist = getWorkList(args[0], args[1])
	for (baseid, setid) in worklist:
	    generateBatch(baseid, setid)
 
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
