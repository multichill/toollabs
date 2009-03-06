#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Simple script to create a bulk of subcategories of http://commons.wikimedia.org/wiki/Category:Files_moved_to_Commons_requiring_review_by_date
The bot will create a lot of categories if they didnt exist yet.
The start date is hardcoded.

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
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'Category:Files moved to Commons requiring review as of ' + str(int(day)) + u' ' + month + u' ' + year)
    wikipedia.output(u'Working on ' + page.title())
    if not page.exists():
	toPut = u'{{BotMoveToCommonsHeader|day=' + day + u'|month=' + month + u'|year=' + year + u'}}' 
	wikipedia.output(u'Creating category with content: ' + toPut)
	page.put(toPut, toPut)
    else:
	wikipedia.output(u'Category already exists')

def main():
    startDate = datetime(year=2007, month=3, day=15)
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
