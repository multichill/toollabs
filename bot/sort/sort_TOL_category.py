#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
test
'''
import sys
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, pagegenerators, catlib

site = None

def sort_TOL_Category(cat):
    # Get all subcategories
    subcategories = cat.subcategories();
    goodSubcategories= []
    wrongSubcategories=[]
    
    # Get all subcategories which are in the form <parent category><suffix>
    for subcat in subcategories:
	if subcat.titleWithoutNamespace().startswith(cat.titleWithoutNamespace()):
	    goodSubcategories.append(subcat)
	# Do something with unidentified
	else:
	    wrongSubcategories.append(subcat)
	
    # Compare total with the number found
    
    # Sort each category as [[Category:<parent>|<suffix>]]
    for goodCat in goodSubcategories:
	sort_TOL_subcat(cat, goodCat)
	

    # Move all galleries with the same name to subcats

def sort_TOL_subcat(parent, child):
    suffix = child.titleWithoutNamespace().replace(parent.titleWithoutNamespace(), u'').lstrip()
    wikipedia.output(parent.titleWithoutNamespace())
    wikipedia.output(suffix)
    # Replace \[\[[cC]ategory:<parent>[\^]*\]\]
    # With [[Category:<parent>|<suffix>]]
    old = u'\[\[[cC]ategory:' + parent.titleWithoutNamespace() + u'[^\]]*\]\]'
    new = u'[[Category:' + parent.titleWithoutNamespace() + u'|' + suffix + u']]'
    newgal = u'[[' + child.title() + u'| ]]'
    newtext = wikipedia.replaceExcept(child.get(), old, new, [])
    comment = u'Sorting category'
    commentgal = u'Moving to category with the same name'
    wikipedia.showDiff(child.get(), newtext)
    child.put(newtext, comment)
    gallery = wikipedia.Page(site, child.titleWithoutNamespace())
    if gallery.exists():
	wikipedia.output(u'Found gallery')
	newgaltext = wikipedia.replaceExcept(gallery.get(), old, newgal, [])
	wikipedia.showDiff(gallery.get(), newgaltext)
	gallery.put(newgaltext, commentgal)
	

def main():
    wikipedia.output(u'Testing 1 2 3')
    generator = None;
    genFactory = pagegenerators.GeneratorFactory()

    site = wikipedia.getSite(u'commons', u'commons')
    wikipedia.setSite(site)
    for arg in wikipedia.handleArgs():
	if arg.startswith('-page'):
	    if len(arg) == 5:
		generator = [wikipedia.Page(site, wikipedia.input(u'What page do you want to use?'))]
	    else:
		generator = [wikipedia.Page(site, arg[6:])]
	else:
	    generator = genFactory.handleArg(arg)
    if generator:
	for page in generator:
	    if(page.namespace() == 14):
		sort_TOL_Category(catlib.Category(site, page.title()))
    else:
	wikipedia.output(u'No categories to work on!')

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
