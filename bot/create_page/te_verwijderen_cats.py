#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Script to keep http://nl.wikipedia.org/wiki/Wikipedia:Te_verwijderen_categorie%C3%ABn up to date. 
'''
import sys
sys.path.append("/home/multichill/pywikipedia/")
import wikipedia
from datetime import datetime
from datetime import timedelta

def createPage (monday = None):
    '''
    Create a new week page for http://nl.wikipedia.org/wiki/Wikipedia:Te_verwijderen_categorie%C3%ABn.
    Use http://nl.wikipedia.org/wiki/Sjabloon:Te_verwijderen_categorie%C3%ABn_nieuwe_week as template.
    '''
    day = monday.strftime('%d') # 01-31
    month = monday.strftime('%m') # 01-12 
    year = monday.strftime('%Y') # 2008
    week = monday.strftime('%W')
    #(Null, week,Null) = monday.isocalendar()
    page = wikipedia.Page(wikipedia.getSite(u'nl', u'wikipedia'), u'Wikipedia:Te verwijderen categorieën/Toegevoegd ' + str(year) + u' week ' + str(week))
    wikipedia.output(u'Working on ' + page.title())
    if not page.exists():
	toPut = u'{{subst:Sjabloon:Te verwijderen categorieën nieuwe week|maandag=' + str(year) + str(month) + str(day) + u'}}'
	wikipedia.output(u'Creating category with content: ' + toPut)
	page.put(toPut, u'Nieuwe weekpagina met als inhoud: ' + toPut)
    else:
	wikipedia.output(u'The page already exists.')

def addWeek (monday = None):
    '''
    Add another week to http://nl.wikipedia.org/wiki/Wikipedia:Te_verwijderen_categorie%C3%ABn
    '''
    page = wikipedia.Page(wikipedia.getSite(u'nl', u'wikipedia'), u'Wikipedia:Te verwijderen categorieën')
    pagetext = page.get()
    #(year, week, Null) = monday.isocalendar()
    year = monday.strftime('%Y')
    week = monday.strftime('%W')
    qmonday = monday + timedelta(weeks=3)
    #(qyear, qweek, Null) = qmonday.isocalendar()
    qyear = qmonday.strftime('%Y')
    qweek = qmonday.strftime('%W')

    #Add the current week template
    pagetext = pagetext.replace(u'<!-- HIERVOOR -->', u'{{Wikipedia:Te verwijderen categorieën/Toegevoegd ' + str(year) + u' week ' + str(week) + u'}}\n<!-- HIERVOOR -->')
    #Remove the current week template from the queue
    pagetext = pagetext.replace(u'<!-- {{Wikipedia:Te verwijderen categorieën/Toegevoegd ' + str(year) + u' week ' + str(week) + u'}} -->\n',u'')
    #Add a new week template to the queue
    pagetext = pagetext.replace(u'<!-- EINDE QUEUE -->', u'<!-- {{Wikipedia:Te verwijderen categorieën/Toegevoegd ' + str(qyear) + u' week ' + str(qweek) + u'}} -->\n<!-- EINDE QUEUE -->')
    wikipedia.showDiff(page.get(), pagetext)
    page.put(pagetext, u'{{Wikipedia:Te verwijderen categorieën/Toegevoegd ' + str(year) + u' week ' + str(week) + u'}} erbij')

def main():
    today = datetime.utcnow()
    #Create a new week page for monday
    nextmonday = today + timedelta(days=7 - today.weekday())
    createPage(nextmonday)
    #Already create a new week page for next week
    nextweek = nextmonday + timedelta(days=+7)
    createPage(nextweek)
    #Add the week page 
    addWeek(nextmonday)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
