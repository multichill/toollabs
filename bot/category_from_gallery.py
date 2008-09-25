#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Bot to categorize images based on gallery information
*Put uncategorized files in a category
*Put categorized files in a subcategory
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, pagegenerators
import re, imagerecat
import MySQLdb, config

def populateCategory(cat = None):
    galleries = []
    categories = []
    uncatStats = 0
    recatStats = 0
    wikipedia.output(u'Working on ' + cat.title())
    #Find gallery with the same name
    if wikipedia.Page(wikipedia.getSite(), cat.titleWithoutNamespace()).exists():
    	galleries.append(cat.titleWithoutNamespace())
    #Find hint
    hint = findGalleryHint(cat.get())
    if not hint == u'':
        galleries.append(hint)
    
    # Get the current categories
    categories = imagerecat.getCurrentCats(cat)

    if galleries:
        imagesInGalleriesGenerator = getImagesInGalleriesAndCategories(galleries, categories)
	for image in imagesInGalleriesGenerator:
	    if image.categories():
	        #The image contains categories
		recatStats = recatStats + replaceCategory(image, categories, cat.titleWithoutNamespace())
	    else:
	        #No categories
		uncatStats = uncatStats + addCategory(image, cat.titleWithoutNamespace())

    #Remove the template, leave stats.
    removePopulateCategoryTemplate(cat, uncatStats, recatStats)

def findGalleryHint (text = u''):
    result = u''
    gallery = None
    p = re.compile('\{\{[pP]opulate category\|[gG]allery\=(?P<gallery>([^}]+))\}\}')
    match = p.search(text)

    if match:
        gallery = wikipedia.Page(wikipedia.getSite(), match.group('gallery'))
	wikipedia.output(u'Found a match: '+ gallery.title())
	if gallery.exists():
	    wikipedia.output(u'Exists')
	    if gallery.namespace()==0:
	        result = gallery.titleWithoutNamespace()
	
    wikipedia.output(result)
    return result

def getImagesInGalleriesAndCategories (galleries = [], categories = []):
    '''
    Get the uncategorized images which are in one of these galleries
    '''
    result = None
    categories.append(u'Media needing categories as of%')
    query = u'SELECT DISTINCT imagepage.page_namespace, imagepage.page_title FROM page AS gallery '
    query = query + u'JOIN imagelinks ON gallery.page_id = il_from '
    query = query + u'JOIN page AS imagepage ON il_to=imagepage.page_title '
    query = query + u'JOIN categorylinks ON imagepage.page_id=cl_from '
    query = query + u'WHERE imagepage.page_namespace=6 AND imagepage.page_is_redirect=0 '
    query = query + u'AND gallery.page_namespace=0 AND gallery.page_is_redirect=0 AND ('
    if galleries and categories:
	firstGallery = True
        for gallery in galleries:
	    if firstGallery:
	        query = query + u'gallery.page_title=\'' + gallery.replace(u' ', u'_').replace(u"'", u"\\'") + u'\''
		firstGallery = False
	    else:
                query = query + u' OR gallery.page_title=\'' +  gallery.replace(u' ', u'_').replace(u"'", u"\\'") + u'\''
	query = query + u') AND ('
	firstCategory = True
	for category in categories:
	    if firstCategory:
	        query = query + u'cl_to LIKE \'' +  category.replace(u' ', u'_').replace(u"'", u"\\'") + u'\''
		firstCategory = False
	    else:
	        query = query + u' OR cl_to LIKE \'' +  category.replace(u' ', u'_').replace(u"'", u"\\'") + u'\''
	query = query + u') LIMIT 1000'

	result = pagegenerators.MySQLPageGenerator(query)
    return result

def addCategory (image = None, category = u''):
    '''
    Replace the uncategorized template with a category
    '''
    result = 0
    if not category == u'':
        oldtext = image.get()
        newtext = re.sub(u'\{\{\s*([Uu]ncat(egori[sz]ed( image)?)?|[Nn]ocat|[Nn]eedscategory)[^}]*\}\}', u'[[Category:' + category + u']]', oldtext)
	if not oldtext==newtext:
	    wikipedia.output(image.title())
	    wikipedia.showDiff(oldtext, newtext)
	    comment = u'Adding [[Category:' + category + u']] to this uncategorized image'
	    image.put (newtext, comment)
	    result = 1
    return result

def getParentImages (parents = [], galleries = []):
    '''
    Get images which are in a parent category and in a gallery
    '''

def replaceCategory (image = None, parents = [], newcat = u''):
    '''
    Remove all parent categories and add newcat
    '''
    result = 0
    newcats = []
    if not newcat == u'':    
        currentCats = imagerecat.getCurrentCats(image)
	workingCategories = currentCats
	workingCategories.append(newcat)
	# Adding parents if the category filter is lagging.
	# The bot often works on new categories. In these cases the filter does know the parent categories
	workingCategories = workingCategories + parents
        for cat in imagerecat.applyAllFilters(workingCategories):
	    #Now remove those parents again
	    if cat not in parents:
                newcats.append(cat)
	if not(set(currentCats)==set(newcats)):
	    newtext = wikipedia.removeCategoryLinks(image.get(), image.site()) + u'\n'
	    for category in newcats:
	        newtext = newtext + u'[[Category:' + category + u']]\n'
	    comment = u'Moving image to (a subcategory of) [[Category:' + newcat + u']] and trying to filter categories'
	    wikipedia.output(image.title())
	    wikipedia.showDiff(image.get(), newtext)
	    image.put(newtext, comment)
            result = 1
    return result

def removePopulateCategoryTemplate(page = None, uncatStats=0, recatStats=0):
    '''
    Remove {{populate category}}, include the stats in the comment
    '''
    oldtext = page.get()
    newtext = re.sub(u'\{\{[Pp]opulate category\|?[^}]*\}\}', u'', oldtext)
    if not oldtext==newtext:
        wikipedia.showDiff(oldtext, newtext)
	comment = u'Removing {{Populate category}}, bot categorized ' + str(uncatStats)  +  u' images and recategorized ' + str(recatStats) + u' images'
	wikipedia.output(comment)
	page.put (newtext, comment)

def main():
    generator = None
    for arg in wikipedia.handleArgs():
        if arg.startswith('-page'):
            if len(arg) == 5:
	        generator = [wikipedia.Page(wikipedia.getSite(), wikipedia.input(u'What page do you want to use?'))]
	    else:
                generator = [wikipedia.Page(wikipedia.getSite(), arg[6:])]
    if not generator:
        generator = pagegenerators.NamespaceFilterPageGenerator(pagegenerators.ReferringPageGenerator(wikipedia.Page(wikipedia.getSite(), u'Template:Populate category'), onlyTemplateInclusion=True), [14])
    for cat in generator:
        populateCategory(cat)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
