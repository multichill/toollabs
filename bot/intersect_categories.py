#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to populate a category based on a intersection of two other categories

'''
import sys
sys.path.append("../pywikipedia")
import wikipedia, config, pagegenerators
import re, imagerecat
import MySQLdb, config

def intersectCategories(cat = None):
    '''
    Populate a category with images which are in both categories.
    '''
    wikipedia.output(u'Working on ' + cat.title())

    # Parse the template    
    (categoryA, categoryB) = getCategories (cat.get())

    # Do a query to find the images
    images = getImages(categoryA.titleWithoutNamespace(), categoryB.titleWithoutNamespace())

    # For each image remove the old categories and add the new one
    counter = 0
    for image in images:
	replaceCategories(image, [categoryA, categoryB], cat)
	counter = counter + 1

    # Remove the template
    removeTemplate(cat, counter)

def getCategories (text = u''):
    '''
    Get the titles of the two categories from the template
    '''
    result = None
    gallery = None
    p = re.compile('\{\{[iI]ntersect categories\|(?P<catA>([^|]+))\|(?P<catB>([^}]+))\}\}')
    match = p.search(text)

    if match:
	catA = wikipedia.Page(wikipedia.getSite(), u'Category:' + match.group('catA'))
	catB = wikipedia.Page(wikipedia.getSite(), u'Category:' + match.group('catB'))
	result = (catA, catB)
	
    return result

def getImages(categoryA, categoryB):
    '''
    Get images both in categoryA and in categoryB
    '''
    result = None

    query = u"""SELECT DISTINCT file.page_namespace, file.page_title FROM page AS file
		JOIN categorylinks AS cat0A ON file.page_id=cat0A.cl_from
		JOIN categorylinks AS cat0B ON file.page_id=cat0B.cl_from
		JOIN page AS pcat0B ON cat0B.cl_to=pcat0B.page_title
		JOIN categorylinks AS cat1B ON pcat0B.page_id=cat1B.cl_from
		JOIN page AS pcat1B ON cat1B.cl_to=pcat1B.page_title
		JOIN categorylinks AS cat2B ON pcat1B.page_id=cat2B.cl_from
		JOIN page AS pcat2B ON cat2B.cl_to=pcat2B.page_title
		JOIN categorylinks AS cat3B ON pcat2B.page_id=cat3B.cl_from
		WHERE file.page_namespace=6 AND file.page_is_redirect=0 AND
		pcat0B.page_namespace=14 AND pcat0B.page_is_redirect=0 AND
		pcat1B.page_namespace=14 AND pcat1B.page_is_redirect=0 AND
		pcat2B.page_namespace=14 AND pcat2B.page_is_redirect=0 AND
		cat0A.cl_to='%s' AND (
		cat0B.cl_to='%s' OR
		cat1B.cl_to='%s' OR
		cat2B.cl_to='%s' OR
		cat3B.cl_to='%s')"""
		
    catA = categoryA.replace(u' ', u'_')
    catB = categoryB.replace(u' ', u'_')

    result = pagegenerators.MySQLPageGenerator(query % (catA, catB, catB, catB, catB))
    return result

def replaceCategories(page, oldcats, newcat):
    oldtext = page.get()
    newcats = []
    newcats.append(newcat)

    for cat in page.categories():
	if not (cat.titleWithoutNamespace()==oldcats[0].titleWithoutNamespace() or cat.titleWithoutNamespace()==oldcats[1].titleWithoutNamespace()):
	    newcats.append(cat)

    newtext = wikipedia.replaceCategoryLinks (oldtext, newcats)
    comment = u'[[' + oldcats[0].title() + u']] \u2229 [[' + oldcats[1].title() + u']] (and 3 levels of subcategories) -> [[' + newcat.title() + u']]' 

    wikipedia.showDiff(oldtext, newtext)
    page.put(newtext, comment)

def removeTemplate(page = None, counter=0):
    '''
    Remove {{category intersection}}, include the stats in the comment
    '''
    oldtext = page.get()
    newtext = re.sub(u'\{\{[Ii]ntersect categories\|?[^}]*\}\}', u'', oldtext)
    if not oldtext==newtext:
        wikipedia.showDiff(oldtext, newtext)
	comment = u'Removing {{Intersect categories}}, moved ' + str(counter)  +  u' images to this category'
	wikipedia.output(comment)
	page.put (newtext, comment)

def main():
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))
    generator = None
    for arg in wikipedia.handleArgs():
        if arg.startswith('-page'):
            if len(arg) == 5:
	        generator = [wikipedia.Page(wikipedia.getSite(), wikipedia.input(u'What page do you want to use?'))]
	    else:
                generator = [wikipedia.Page(wikipedia.getSite(), arg[6:])]
    if not generator:
        generator = pagegenerators.NamespaceFilterPageGenerator(pagegenerators.ReferringPageGenerator(wikipedia.Page(wikipedia.getSite(), u'Template:Intersect categories'), onlyTemplateInclusion=True), [14])
    for cat in generator:
        intersectCategories(cat)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
