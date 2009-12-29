#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Simple script to create a bulk of subcategories of http://commons.wikimedia.org/wiki/Category:Files_moved_to_Commons_requiring_review_by_date
The bot will create a lot of categories if they didnt exist yet.
The start date is hardcoded.

'''
import sys
sys.path.append("/home/multichill/pywikipedia/")
import wikipedia, catlib
from datetime import datetime
from datetime import timedelta

def createCategory (date = None):
    day = date.strftime('%d')
    month = date.strftime('%B')
    year = date.strftime('%Y')
    page = catlib.Category(wikipedia.getSite(u'commons', u'commons'), u'Category:Files moved from en.wikipedia to Commons requiring review as of ' + str(int(day)) + u' ' + month + u' ' + year)
    wikipedia.output(u'Working on ' + page.title())
    if not page.exists():
	for article in  page.articles():
	    toPut = u'{{BotMoveToCommonsHeader|lang=en|project=wikipedia|day=' + day + u'|month=' + month + u'|year=' + year + u'}}' 
	    wikipedia.output(u'Creating category with content: ' + toPut)
	    page.put(toPut, toPut)
	    break
    else:
	wikipedia.output(u'Category already exists')

def main():
    startDate = datetime(year=2007, month=10, day=1)
    workDate = startDate
    today = datetime.utcnow()
    while(workDate < today):
	createCategory(workDate)
	workDate = workDate + timedelta(days=+1)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
