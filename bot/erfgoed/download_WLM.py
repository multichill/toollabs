#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

A robot to download all Wiki Loves Monuments images. Usage:
download_WLM.py -lang:commons -family:commons -target:"c:\temp\WLM" -cat:Images_from_Wiki_Loves_Monuments_2011

'''
import sys
import wikipedia, config, pagegenerators
import urllib2, codecs
 
def downloadFile(imagepage, target):

    html = imagepage.getImagePageHtml()
    fileUrl = imagepage.fileUrl()
    filename = target + imagepage.titleWithoutNamespace()

    # Download the image
    uo = wikipedia.MyURLopener
    remotefile = uo.open(fileUrl)
    # Store the image
    localfile = open(filename, "wb")
    localfile.write(remotefile.read())
    localfile.close() 
    # Store the html    
    localhtmlfile = codecs.open(filename + u'.html', 'wb', 'utf-8')
    localhtmlfile.write(html)
    localhtmlfile.close()

    return

def main():
    wikipedia.setSite(wikipedia.getSite(u'commons', u'commons'))

    generator = None
    genFactory = pagegenerators.GeneratorFactory()
    target = u'/mnt/user-store/Wiki_Loves_Monuments_Netherlands_2011/'

    for arg in wikipedia.handleArgs():
        if arg.startswith('-target:'):
            target = arg [len('-target:'):]
        else:
            genFactory.handleArg(arg)

    generator = genFactory.getCombinedGenerator()

    if generator:
	# Get a preloading generator with only images
	pgenerator = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(generator, [6]))
	for page in pgenerator:
	    imagepage = wikipedia.ImagePage(page.site(), page.title())
	    downloadFile(imagepage, target)

if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
