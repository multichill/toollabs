#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Clean up the wiki tabels for the erfgoed project

'''
import sys, time
sys.path.append("/home/multichill/pywikipedia")
import wikipedia, config, re, pagegenerators

def cleanupMonument(page, oldtext):
    '''
    Process a single instance of the Tabelrij rijksmonument template
    '''
    fields = [  (u'woonplaats', u'optional'), 
		(u'buurt', u'extra'),
		(u'objectnaam', u'optional'),
		(u'type_obj', u'optional'),
		(u'oorspr_functie', u'optional'),
		(u'cbs_tekst', u'optional'),
		(u'bouwjaar', u'optional'),
		(u'architect', u'optional'),
		(u'adres', u'optional'),
		(u'postcode', u'extra'),
		(u'RD_x', u'optional'),
		(u'RD_y', u'optional'),
		(u'lat', u'optional'),
		(u'lon', u'optional'),
		(u'objrijksnr', u'optional'),
		(u'image', u'optional'),
		]	

    templates = page.templatesWithParams(thistxt=oldtext)
    (template, params) = templates.pop()
    if not template==u'Tabelrij rijksmonument':
	print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAh wtf"
	return oldtext

    contents = {}
    for param in params:
	#Split at =
	(field, sep, value) = param.partition(u'=')	
	contents[field] = value

    result = u'{{Tabelrij rijksmonument'
   
    for (fieldname, required) in fields:
	if contents.get(fieldname):
	    result = result + u'|' + fieldname + u'=' + contents.get(fieldname)
	elif not required==u'extra':
	    result = result + u'|' + fieldname + u'='
    result = result + u'}}'
    return result

def cleanupPage(page):
    '''
    '''
    oldtext = page.get()
    text = oldtext

    regex = u'(\{\{Tabelrij[ _]rijksmonument\|[^\}]+\}\})'
    matches = re.findall(regex, text, re.I|re.M)
    for match in matches:
	newMatch = cleanupMonument(page, match)
	text = text.replace(match, newMatch)
    #wikipedia.showDiff(oldtext, text)
    comment=u'[[Wikipedia:Verzoekpagina_voor_bots#Rijksmonumentenlijsten|Op verzoek]] : Velden in een andere volgorde en toevoegen lege velden'
    page.put_async(text, comment)

def main():
    '''
    The main loop
    '''
    # First find out what to work on

    genFactory = pagegenerators.GeneratorFactory()

    for arg in wikipedia.handleArgs():
	genFactory.handleArg(arg)

    generator = genFactory.getCombinedGenerator()
    if not generator:
	wikipedia.output(u'You have to specify what to work on.')
    else:
	for page in generator:
	    if page.exists() and not page.isRedirectPage():
		# Do some checking
		cleanupPage(page)
    
if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
