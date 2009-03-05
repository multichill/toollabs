#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Simple script to create the daily subcategory of http://commons.wikimedia.org/wiki/Category:Unknown
The bot will create todays category and tomorrows category if they didnt exist yet.

'''
import sys
sys.path.append("/home/multichill/pywikipedia/")
import wikipedia
from datetime import datetime
from datetime import timedelta

def createCategory (date = None):
    day = date.strftime('%d')
    month = date.strftime('%B')
    year = date.strftime('%Y')
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'Category:Unknown as of ' + str(int(day)) + u' ' + month + u' ' + year)
    wikipedia.output(u'Working on ' + page.title())
    if not page.exists():
	toPut = u'{{UnknownHeader|day=' + day + u'|month=' + month + u'|year=' + year + u'}}' 
	wikipedia.output(u'Creating category with content: ' + toPut)
	page.put(toPut, toPut)
    else:
	wikipedia.output(u'Category already exists')

def main():
    today = datetime.utcnow()
    tomorrow = today + timedelta(days=+1)
    createCategory(today)
    createCategory(tomorrow)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
