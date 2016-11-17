#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
C:\pywikibot\core>add_category.py -lang:wikidata -family:wikidata -file:categories_not_category.txt -namespace:0


"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib2
import re
import pywikibot.data.wikidataquery as wdquery
import datetime

class PaintingsBot:
    """
    A bot to enrich and create monuments on Wikidata
    """
    def __init__(self, dictGenerator, paintingIdProperty):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        
        self.paintingIdProperty = paintingIdProperty
        self.paintingIds = self.fillCache(self.paintingIdProperty)
        
    def fillCache(self, propertyId, queryoverride=u'', cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        if queryoverride:
            query = queryoverride
        else:
            query = u'CLAIM[195:190804] AND CLAIM[%s]' % (propertyId,)
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(propertyId),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(propertyId))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = prop[0]

            if expectedItems==len(result):
                pywikibot.output('I now have %s items in cache' % expectedItems)

        return result
                        
    def run(self):
        """
        Starts the robot.
        """
        rijksmuseum = pywikibot.ItemPage(self.repo, u'Q190804')
        for painting in self.generator:
            # Buh, for this one I know for sure it's in there
            
            
            paintingId = painting['artObject']['objectNumber']
            uri = u'https://www.rijksmuseum.nl/nl/collectie/%s' % (paintingId,)
            #europeanaUrl = u'http://europeana.eu/portal/record/%s.html' % (painting['object']['about'],)

            print paintingId
            print uri

            dcCreatorName = painting['artObject']['principalOrFirstMaker'].strip()


            #dcCreatorName = u''

            #for agent in painting['object']['agents']:
            #    if agent.get('about')== dcCreator:
            #        #print u'Found my agent'
            #        if u',' in agent['prefLabel']['def'][0]:
            #            (surname, givenname) = agent['prefLabel']['def'][0].split(u',')
            #            dcCreatorName = u'%s %s' % (givenname.strip(), surname.strip(),)
            #        else:
            #            dcCreatorName = agent['prefLabel']['def'][0]
            
            #print painting['object']['language']
            #print painting['object']['title']
            #print painting['object']['about']
            #print painting['object']['proxies'][0]['dcCreator']['def'][0]
            #print painting['object']['proxies'][0]['dcFormat']['def'][0]
            #print painting['object']['proxies'][0]['dcIdentifier']['def'][0]
            #print painting['object']['proxies'][0]['dcIdentifier']['def'][1]
            
            paintingItem = None
            newclaims = []
            if paintingId in self.paintingIds:
                paintingItemTitle = u'Q%s' % (self.paintingIds.get(paintingId),)
                print paintingItemTitle
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

            else:
                
                #print 'bla'
                #monumentItem = pywikibot.ItemPage(self.repo, title=u'')

                
                        #print dcCreatorName


                data = {'labels': {},
                        'descriptions': {},
                        }

                data['labels']['nl'] = {'language': 'nl', 'value': painting['artObject']['title']}
                

                if dcCreatorName:
                    data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s' % (dcCreatorName,)}
                    data['descriptions']['nl'] = {'language': u'nl', 'value' : u'schilderij van %s' % (dcCreatorName,)}
                    

                print data
                
                identification = {}
                summary = u'Creating new item with data from %s ' % (uri,)
                pywikibot.output(summary)
                #monumentItem.editEntity(data, summary=summary)
                result = self.repo.editEntity(identification, data, summary=summary)
                #print result
                paintingItemTitle = result.get(u'entity').get('id')
                paintingItem = pywikibot.ItemPage(self.repo, title=paintingItemTitle)

                newclaim = pywikibot.Claim(self.repo, u'P%s' % (self.paintingIdProperty,))
                newclaim.setTarget(paintingId)
                pywikibot.output('Adding new id claim to %s' % paintingItem)
                paintingItem.addClaim(newclaim)

                self.addReference(paintingItem, newclaim, uri)
                
                newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                newqualifier.setTarget(rijksmuseum)
                pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                newclaim.addQualifier(newqualifier)

                collectionclaim = pywikibot.Claim(self.repo, u'P195')
                collectionclaim.setTarget(rijksmuseum)
                pywikibot.output('Adding collection claim to %s' % paintingItem)
                paintingItem.addClaim(collectionclaim)

                self.addReference(paintingItem, collectionclaim, uri)

                
            
            if paintingItem and paintingItem.exists():
                
                data = paintingItem.get()
                claims = data.get('claims')
                #print claims

                # located in
                if u'P276' not in claims:
                    newclaim = pywikibot.Claim(self.repo, u'P276')
                    newclaim.setTarget(rijksmuseum)
                    pywikibot.output('Adding located in claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    self.addReference(paintingItem, newclaim, uri)
                    

                # instance of always painting while working on the painting collection
                if u'P31' not in claims:
                    
                    dcformatItem = pywikibot.ItemPage(self.repo, title='Q3305213')

                    newclaim = pywikibot.Claim(self.repo, u'P31')
                    newclaim.setTarget(dcformatItem)
                    pywikibot.output('Adding instance claim to %s' % paintingItem)
                    paintingItem.addClaim(newclaim)

                    self.addReference(paintingItem, newclaim, uri)


                # creator        
                if u'P170' not in claims and dcCreatorName:
                    creategen = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(dcCreatorName, step=None, total=10, namespaces=[0], site=self.repo)))
                    
                    newcreator = None


                    for creatoritem in creategen:
                        print creatoritem.title()
                        if creatoritem.get().get('labels').get('en') == dcCreatorName or creatoritem.get().get('labels').get('nl') == dcCreatorName:
                            print creatoritem.get().get('labels').get('en')
                            print creatoritem.get().get('labels').get('nl')
                            # Check occupation and country of citizinship
                            if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                                newcreator = creatoritem
                                continue
                        elif (creatoritem.get().get('aliases').get('en') and dcCreatorName in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and dcCreatorName in creatoritem.get().get('aliases').get('nl')):
                            if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                                newcreator = creatoritem
                                continue

                    if newcreator:
                        pywikibot.output(newcreator.title())

                        newclaim = pywikibot.Claim(self.repo, u'P170')
                        newclaim.setTarget(newcreator)
                        pywikibot.output('Adding creator claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        self.addReference(paintingItem, newclaim, uri)

                        print creatoritem.title()
                        print creatoritem.get()
                            
                            

                        

                    else:
                        pywikibot.output('No item found for %s' % (dcCreatorName, ))
                else:
                    print u'Already has a creator'

                """
                # date of creation
                if u'P571' not in claims:
                    if painting['object']['proxies'][0].get('dctermsCreated'):
                        dccreated = painting['object']['proxies'][0]['dctermsCreated']['def'][0].strip()
                        if len(dccreated)==4: # It's a year
                            newdate = pywikibot.WbTime(year=dccreated)
                            newclaim = pywikibot.Claim(self.repo, u'P571')
                            newclaim.setTarget(newdate)
                            pywikibot.output('Adding date of creation claim to %s' % paintingItem)
                            paintingItem.addClaim(newclaim)

                            self.addReference(paintingItem, newclaim, uri)


                # material used
                if u'P186' not in claims:
                    dcFormats = { u'http://vocab.getty.edu/aat/300014078' : u'Q4259259', # Canvas
                                  u'http://vocab.getty.edu/aat/300015050' : u'Q296955', # Oil paint
                                  }
                    if painting['object']['proxies'][0].get('dcFormat') and painting['object']['proxies'][0]['dcFormat'].get('def'):
                        for dcFormat in painting['object']['proxies'][0]['dcFormat']['def']:
                            if dcFormat in dcFormats:
                                dcformatItem = pywikibot.ItemPage(self.repo, title=dcFormats[dcFormat])

                                newclaim = pywikibot.Claim(self.repo, u'P186')
                                newclaim.setTarget(dcformatItem)
                                pywikibot.output('Adding material used claim to %s' % paintingItem)
                                paintingItem.addClaim(newclaim)

                                self.addReference(paintingItem, newclaim, uri)
                """
                ## Handle 
                #if u'P1184' not in claims:
                #    handleUrl = painting['object']['proxies'][0]['dcIdentifier']['def'][0]
                #    handle = handleUrl.replace(u'http://hdl.handle.net/', u'')
                #    
                #    newclaim = pywikibot.Claim(self.repo, u'P1184')
                #    newclaim.setTarget(handle)
                #    pywikibot.output('Adding handle claim to %s' % paintingItem)
                #    paintingItem.addClaim(newclaim
                #    self.addReference(paintingItem, newclaim, uri)

                # Europeana ID
                #if u'P727' not in claims:
                #    europeanaID = painting['object']['about'].lstrip('/')
                #    newclaim = pywikibot.Claim(self.repo, u'P727')
                #    newclaim.setTarget(europeanaID)
                #    pywikibot.output('Adding Europeana ID claim to %s' % paintingItem)
                #    paintingItem.addClaim(newclaim)
                #    self.addReference(paintingItem, newclaim, uri)

    def addReference(self, paintingItem, newclaim, uri):
        """
        Add a reference with a retrieval url and todays date
        """
        pywikibot.output('Adding new reference claim to %s' % paintingItem)
        refurl = pywikibot.Claim(self.repo, u'P854') # Add url, isReference=True
        refurl.setTarget(uri)
        refdate = pywikibot.Claim(self.repo, u'P813')
        today = datetime.datetime.today()
        date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
        refdate.setTarget(date)
        newclaim.addSources([refurl, refdate])

def getNoclaimGeneratorOld(templates, lang=u'nl'):
    '''
    Bla %02d
    '''
    url = u'https://tools.wmflabs.org/multichill/queries/wikidata/noclaims_%swiki_infobox_full.txt' % (lang,)
    site = pywikibot.Site(lang, u'wikipedia')
    regex = u'^\* \[\[(?P<title>[^\]]+)\]\] - (?P<template>Template:.+)$'

    noclaimPage = urllib2.urlopen(url)
    noclaimData = unicode(noclaimPage.read(), u'utf-8')

    #print noclaimData[0:100]

    for match in re.finditer(regex, noclaimData, flags=re.M):
        if match.group('template') in templates:
            #print match.group("title")
            yield (pywikibot.Page(pywikibot.Link(match.group("title"), site)), match.group('template'))

    #for linkmatch in pywikibot.link_regex.finditer(noclaimData):
    #    yield pywikibot.Page(pywikibot.Link(linkmatch.group("title"), site))

def getNoclaimGenerator(lang=u'nl', pageTitle = u'Wikidata:Database reports/without claims by site/nlwiki'):
    '''
    Bla %02d
    '''
    site = pywikibot.Site(lang, u'wikipedia')
    repo = site.data_repository()
    page = pywikibot.Page(repo, title=pageTitle)

    text = page.get()

    regex = u'^\* \[\[(?P<item>Q\d+)\]\] - \[\[:%s:(?P<article>[^\]]+)\]\]' % (lang,)




    for match in re.finditer(regex, text, flags=re.M):
        yield pywikibot.Page(pywikibot.Link(match.group("article"), site))
        
def getTemplateClaims(lang=u'nl', pageTitle = u'user:NoclaimsBot/Template claim'):
    site = pywikibot.Site(lang, u'wikipedia')
    page = pywikibot.Page(site, title=pageTitle)

    text = page.get()


    regex = u'^\* \[\[(?P<title>%s:[^\]]+)\]\]\s*(?P<P1>P\d+)\s*(?P<Q1>Q\d+)\s*((?P<P2>P\d+)\s*(?P<Q2>Q\d+))?\s*((?P<P3>P\d+)?\s*(?P<Q3>Q\d+))?$' % (site.namespace(10),)

    result = {}

    for match in re.finditer(regex, text, flags=re.M):
        result[match.group('title')] = [(match.group('P1'), match.group('Q1'))]
        if match.group('Q2'):
            result[match.group('title')].append((match.group('P2'), match.group('Q2')))
        if match.group('Q3'):
            result[match.group('title')].append((match.group('P3'), match.group('Q3')))            

    #print result
    return result

def processPage(page, templates):
    repo = pywikibot.Site().data_repository()

    for pagetemplate in page.itertemplates():
        templatetitle = pagetemplate.title()
        if templatetitle in templates.keys():
            pywikibot.output(u'Working on %s using %s' % (page.title(), templatetitle))
            claimslist = templates.get(templatetitle)
            try:
                item = page.data_item()
                data = item.get()
                claims = data.get('claims')

                for pid, qid in claimslist:
                    if pid not in claims:
                        newclaim = pywikibot.Claim(repo, pid)
                        claimtarget = pywikibot.ItemPage(repo, qid)
                        newclaim.setTarget(claimtarget)
                        summary = u'Adding [[Property:%s]] -> [[%s]] based on [[%s:%s]]' % (pid, qid, page.site.lang, templatetitle)
                        pywikibot.output(summary)
                        item.addClaim(newclaim, summary=summary)
            except pywikibot.exceptions.NoPage:
                print u'That page did not exist'
            return


def main(*args):
    lang = u'nl'

    # https://ca.wikipedia.org/wiki/Usuari:NoclaimsBot/Template_claim empty
    # https://de.wikipedia.org/wiki/Benutzer:NoclaimsBot/Template_claim empty
    # https://en.wikipedia.org/wiki/User:NoclaimsBot/Template_claim long list
    # https://es.wikipedia.org/wiki/Usuario:NoclaimsBot/Template_claim empty
    # https://fr.wikipedia.org/wiki/Utilisateur:NoclaimsBot/Template_claim one item
    # https://sv.wikipedia.org/wiki/Anv%C3%A4ndare:NoclaimsBot/Template_claim


    sources = {u'en' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/enwiki',
                        u'templateclaims' : u'User:NoclaimsBot/Template claim',
                       },
               u'fr' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/frwiki',
                        u'templateclaims' : u'Utilisateur:NoclaimsBot/Template_claim',
                        },
               u'nl' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/nlwiki',
                        u'templateclaims' : u'Gebruiker:NoclaimsBot/Template claim',
                       },
               u'sv' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/svwiki',
                        u'templateclaims' : u'Användare:NoclaimsBot/Template claim',
                       },
    }


    source = None

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-source:'):
            if len(arg) == 8:
                source = pywikibot.input(
                        u'Please enter the source property you want to work on:')
            else:
                source = arg[8:]

    repo = pywikibot.Site().data_repository()

    if source and source in sources.keys():
        worklangs = [source,]
    else:
        worklangs = sources.keys()

    for lang in worklangs: # in sites:
        templates = getTemplateClaims(lang, sources[lang][u'templateclaims'])

        #for template in templates:
        #    print template
        #    print templates[template]
        noclaimgen = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(getNoclaimGenerator(lang, sources[lang][u'noclaims']), 0))
        for page in noclaimgen:
            processPage(page, templates)

    '''
    #templates = getTemplateClaims(lang=lang)
    ##print templates
    #noclaimgen = getNoclaimGenerator(templates, lang=lang)
    #
    ##print templates.keys()

        for page in noclaimgen:
            pywikibot.output(u'Working on %s using %s' % (page.title(), template))
            if template in templates.keys() and page.exists() and not page.isRedirectPage():
                claimslist = templates.get(template)
                try:
                    item = page.data_item()
                    data = item.get()
                    claims = data.get('claims')

                    for pid, qid in claimslist:
                        if pid not in claims:
                            newclaim = pywikibot.Claim(repo, pid)
                            claimtarget = pywikibot.ItemPage(repo, qid)
                            newclaim.setTarget(claimtarget)
                            summary = u'Adding [[Property:%s]] -> [[%s]] based on [[%s:%s]]' % (pid, qid, lang, template)
                            pywikibot.output(summary)
                            item.addClaim(newclaim, summary=summary)
                except pywikibot.exceptions.NoPage:
                    print u'That page did not exist'
                #except pywikibot.data.api.APIError:
                #    print u'That did not save'
                


    categories = {}
    templates = {}
    i = 0
    

    for page in noclaimGen:
        firstletter = page.title()[0:1]
        if firstletter not in alfabet:
            firstletter = u'0'
            
        pages[firstletter] = pages[firstletter] + u'* [[%s]]\n' % (page.title(),)
        #print pages[firstletter]

    site = pywikibot.Site(u'nl', 'wikipedia')
    summary = u'Updating list'
    for key, value in pages.iteritems():
        pageTitle = baseTitle + key
        page = pywikibot.Page(site, title=pageTitle)
        page.put(value, summary)
        #print page.title()
        #pywikibot.output(value)#print value
        
            
        #print page.title()
        #print firstletter
    
        i = i + 1
        for cat in page.categories():
            catTitle = cat.title()
            if catTitle in categories:
                categories[catTitle] = categories[catTitle] + 1
            else:
                categories[catTitle] = 1
        for template in page.templates():
            templateTitle = template.title()
            if templateTitle in templates:
                templates[templateTitle] = templates[templateTitle] + 1
            else:
                templates[templateTitle] = 1
        if i % 100 == 0:
            for cat, catcount in categories.iteritems():
                if catcount > 10:
                    pywikibot.output(u'* [[%s]] - %s' % (cat, catcount))
            for templ, templcount in templates.iteritems():
                if templcount > 10:
                    pywikibot.output(u'* [[%s]] - %s' % (templ, templcount))
        if i % 500 == 0:
            print categories
            print templates
            
               

    site = pywikibot.Site(u'nl', 'wikipedia')
    newtext = u'Dit is een lijstje van personen die onder [[:Categorie:Nederlandse adel]] [http://tools.wmflabs.org/catscan2/catscan2.php?language=nl&depth=5&categories=Nederlandse+adel&show_redirects=no&get_q=1 vinden zijn], maar geen ouders of kinderen hebben:\n'
    page = pywikibot.Page(site, title=u'User:Multichill/Adel_zonder_familie')
    summary = u'Lijst van adel zonder familie'
    
    for item in adelGen:
        print item.title()
        data = item.get()
        labels = data.get('labels')
        claims = data.get('claims')
        sitelinks = data.get('sitelinks')
        # Crude gender check to see if it's a human
        if 'P21' in claims:
            # Copy label
            if labels.get('nl') and not labels.get('en'):
                labels['en']=labels.get('nl')
                labelsum = u'Copying label "%s" nl->en for this person' % (labels.get('nl'),)
                item.editLabels(labels, summary=labelsum)
            # Not father, mother or child in claims
            if u'P22' not in claims and u'P25' not in claims and u'P40' not in claims:
                newtext = newtext + u'* [[%s]] - [[:d:%s]]\n' % (sitelinks.get('nlwiki'), item.title(),)
                print len(newtext)

    page.put(newtext, summary)

    

    

    
    #paintingGen = getPaintingGenerator()
    



    #paintingsBot = PaintingsBot(paintingGen, 217)
    #paintingsBot.run()
    '''
    
    

if __name__ == "__main__":
    main()
