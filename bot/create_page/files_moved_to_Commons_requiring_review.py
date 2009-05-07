#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Simple script to create the daily subcategory of http://commons.wikimedia.org/wiki/Category:Files_moved_to_Commons_requiring_review_by_date
The bot will create todays category and tomorrows category if they didnt exist yet.

'''
import sys
sys.path.append("/home/multichill/pywikipedia/")
import wikipedia
from datetime import datetime
from datetime import timedelta

projects = [(u'en', u'wikipedia'), (u'nl', 'wikipedia')]

def createCategory (date = datetime.utcnow()):
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

def createProjectCategory (date = datetime.utcnow(), lang=u'en', project=u'wikipedia'):
    day = date.strftime('%d')
    month = date.strftime('%B')
    year = date.strftime('%Y')
    page = wikipedia.Page(wikipedia.getSite(u'commons', u'commons'), u'Category:Files moved from ' + lang + u'.' + project + u' to Commons requiring review as of ' + str(int(day)) + u' ' + month + u' ' + year)
    wikipedia.output(u'Working on ' + page.title())
    if not page.exists():
        toPut = u'{{BotMoveToCommonsHeader|lang=' + lang + u'|project=' + project + u'|day=' + day + u'|month=' + month + u'|year=' + year + u'}}'
        wikipedia.output(u'Creating category with content: ' + toPut)
        page.put(toPut, toPut)
    else:
        wikipedia.output(u'Category already exists')

def main():
    today = datetime.utcnow()
    tomorrow = today + timedelta(days=+1)

    createCategory(today)
    for (lang, project) in projects:
	createProjectCategory(today, lang, project)

    createCategory(tomorrow)
    for (lang, project) in projects:
        createProjectCategory(tomorrow, lang, project)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
