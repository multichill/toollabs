#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
test
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia

#First get a list of images to work on

#Create some html lists?

#Create an index page?

#For each image:
##Download the image
##Create a html page with the same name.html


def main():
    wikipedia.output(u'Testing 1 2 3')

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
