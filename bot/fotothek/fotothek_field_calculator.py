#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Simple program to calculate all the max field lengths in the Fotothek xml files.
This is to find out suitable field lengths for the mysql database.
'''
import sys, os
import os.path
import xml.etree.ElementTree

xmlFiles = ["wiki-2.xml"]

def main(args):
    '''
    Main loop.
    '''
    elements = dict()
    elementsList = []
    
    for file in xmlFiles:
        tree = xml.etree.ElementTree.parse(file)
        root = tree.getroot()
    
        for element in root.getiterator():
            if (element.get(u'Type') and element.get(u'Value')):
		if not elements.get(element.get(u'Type')):
		    elements[element.get(u'Type')] = dict()
		    elements[str(element.get(u'Type'))]['count'] = 1
		    elements[str(element.get(u'Type'))]['length'] = len(element.get(u'Value'))
		else:
		    elements[str(element.get(u'Type'))]['count'] = elements[element.get(u'Type')]['count'] + 1
		    if elements.get(element.get(u'Type')).get('length') < len(element.get(u'Value')):
			elements[element.get(u'Type')]['length'] = len(element.get(u'Value'))

    print "Ok, all done, here are the restults:"            
    for (t, v) in elements.items():
	elementsList.append((t,v))
    elementsList.sort()
    for t, v in elementsList:
        print (str(t) + " - count: " +  str(v.get('count')) + " - length: " + str(v.get('length'))).encode("UTF-8")     
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
