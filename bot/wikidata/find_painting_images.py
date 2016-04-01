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
import random

class PaintingsMatchBot:
    """
    A bot to enrich and create monuments on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.commons = pywikibot.Site(u'commons', u'commons')
        self.repo = pywikibot.Site().data_repository()

        self.commonsNoLink = [] # List of images without a link
        self.commonsLink = {} # Dictionary of images with a wikidata link, file -> item
        
        self.commonsCIWithout = {} # Creator/institution -> image
        self.commonsCIWith = {} # Creator/institution -> image and item
        
        self.wikidataNoImages = [] # List of items without images
        self.wikidataImages = {} # Dictionary of image on wikidata file -> item

        self.wikidataCIWithout = {} # Creator/institution -> item & url
        self.wikidataCIWith = {} # Creator/institution -> item & url

        self.filter=False
        self.filtercollections = [#u'679527', # Museum Boijmans Van Beuningen
                                  #u'132783', # Hermitage Museum
                                  #u'160236', # Metropolitan Museum of Art
                                  #u'176251', # Thyssen-Bornemisza
                                  #u'214867', # National Gallery of Art
                                  u'731126', # J. Paul Getty Museum
                                  u'29247', # Getty Center
                                  ]


             
    def run(self):
        """
        Starts the robot.
        """
        self.commonsCIWithout = self.getCommonsWithoutCI()
        self.commonsNoLink = self.getCommonsWithoutAll()

        self.commonsCIWith = self.getCommonsWithCI()
        self.commonsLink = self.getCommonsWithAll()

        print len(self.commonsNoLink)
        print len(self.commonsLink)
        print len(self.commonsCIWithout)
        print len(self.commonsCIWith)
        
        self.getWikidataWithout()
        self.getWikidataWith()

        print len(self.wikidataNoImages)
        print len(self.wikidataImages)
        print len(self.wikidataCIWithout)
        print len(self.wikidataCIWith)

        #testci = (u'330848', u'679527')
        #print u'Commons without Boij'
        #print self.commonsCIWithout.get((u'330848', u'679527'))
        #print u'Wikidata without Boij'
        #print self.wikidataCIWithout.get((u'330848', u'679527'))

        self.addMissingCommonsLinks()
        self.addMissingWikidataStatements()
        
        self.publishWikidataSuggestions()
        self.publishCommonsSuggestions()
        self.publishCommonsNoTracker()

    def getCommonsWithoutCI(self):
        '''
        Bla 
        '''
        result = {}
        creatorcounts = {}
        institutioncounts = {}
        cicounts = {}
        
        url = u'http://tools.wmflabs.org/multichill/queries/commons/paintings_without_wikidata_ci.txt'
        regex = u'^\* \[\[:File:(?P<image>[^\]]+)\]\] - Q(?P<creator>\d+) - Q(?P<institution>\d+)$'

        queryPage = urllib2.urlopen(url)
        queryData = unicode(queryPage.read(), u'utf-8')

        for match in re.finditer(regex, queryData, flags=re.M):
            ci = (match.group("creator"), match.group("institution"))
            if not ci in result:
                result[ci] = []
            
            result[ci].append(match.group("image"))
            #self.commonsNoLink.append(match.group("image"))
            if not match.group("creator") in creatorcounts:
                creatorcounts[match.group("creator")]=0
            creatorcounts[match.group("creator")] = creatorcounts[match.group("creator")] + 1
            
            if not match.group("institution") in institutioncounts:
                institutioncounts[match.group("institution")]=0
            institutioncounts[match.group("institution")] = institutioncounts[match.group("institution")] + 1

            if not ci in cicounts:
                cicounts[ci]=0
            cicounts[ci] = cicounts[ci] + 1

        pywikibot.output(u'The top creators without link on Commons are:')
        for creator in sorted(creatorcounts, key=creatorcounts.get, reverse=True)[:20]:
            pywikibot.output(u'* {{Q|%s}} - %s' % (creator, creatorcounts[creator]))

        pywikibot.output(u'The top institutions without link on Commons  are:')
        for institution in sorted(institutioncounts, key=institutioncounts.get, reverse=True)[:20]:
            pywikibot.output(u'* {{Q|%s}} - %s' % (institution, institutioncounts[institution]))

        pywikibot.output(u'The top combinations without link on Commons are:')
        for (creator, institution)  in sorted(cicounts, key=cicounts.get, reverse=True)[:10]:
            pywikibot.output(u'* {{Q|%s}} & {{Q|%s}} - %s' % (creator, institution, cicounts[ci]))

        return result

    def getCommonsWithoutAll(self):
        '''
        Bla 
        '''
        result = []
        url = u'http://tools.wmflabs.org/multichill/queries/commons/paintings_without_wikidata.txt'
        regex = u'^\* \[\[:File:(?P<image>[^\]]+)\]\]$'

        queryPage = urllib2.urlopen(url)
        queryData = unicode(queryPage.read(), u'utf-8')

        for match in re.finditer(regex, queryData, flags=re.M):
            result.append(match.group("image"))

        return result

    def getCommonsWithCI(self):
        '''
        Bla %02d
        '''
        result = {}
        url = u'http://tools.wmflabs.org/multichill/queries/commons/paintings_with_wikidata_ci.txt'
        regex = u'^\* \[\[:File:(?P<image>[^\]]+)\]\] - Q(?P<paintingitem>\d+) - Q(?P<creator>\d+) - Q(?P<institution>\d+)$'

        queryPage = urllib2.urlopen(url)
        queryData = unicode(queryPage.read(), u'utf-8')

        for match in re.finditer(regex, queryData, flags=re.M):
            ci = (match.group("creator"), match.group("institution"))
            if not ci in result:
                result[ci] = []
            result[ci].append({ u'image' : match.group("image"), u'item' : match.group("paintingitem") })
        
        return result

    def getCommonsWithAll(self):
        '''
        Bla %02d
        '''
        result = {}
        url = u'http://tools.wmflabs.org/multichill/queries/commons/paintings_with_wikidata.txt'
        regex = u'^\* \[\[:File:(?P<image>[^\]]+)\]\] - Q(?P<paintingitem>\d+)$'

        queryPage = urllib2.urlopen(url)
        queryData = unicode(queryPage.read(), u'utf-8')

        for match in re.finditer(regex, queryData, flags=re.M):
            result[match.group("image")]=match.group("paintingitem")
            #if u'zondeval' in match.group("image"):
            #    pywikibot.output(u'Found in Commons all %s' % (match.group("image"),))
            #    if match.group("image")==u'Cornelis_van_Haarlem_-_De_zondeval.jpg':
            #        pywikibot.output(u'And it gives an exact string match')
            #    else:
            #        pywikibot.output(u'No match')

        return result
    
    def getWikidataWithout(self):
        '''
        Query Wikidata to get paintings without images, but with creator and collection
        '''
        paintingdict = {}
        creatorcounts = {}
        institutioncounts = {}
        cicounts = {}
        #result = {}

        #wdq.wmflabs.org/api?q=CLAIM[31:3305213] AND CLAIM[170] AND CLAIM[195] AND CLAIM[357] AND NOCLAIM[18]&props=170,195

        query = u'CLAIM[31:3305213] AND CLAIM[170] AND CLAIM[195] AND NOCLAIM[18]'
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=0) # 30, be careful
        data = wd_query.query(wd_queryset, props=[str(170),str(195),str(276),str(973)])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            for item in data.get('items'):
                paintingdict[item] = { u'creator' : False, u'institution' : False, u'location' : False, u'url' : False }
                self.wikidataNoImages.append(u'%s' % (item,))

            creatorprops = data.get('props').get(str(170))

            for creatorprop in creatorprops:
                paintingdict[creatorprop[0]][u'creator']=creatorprop[2]

            institutionprops = data.get('props').get(str(195))

            for institutionprop in institutionprops:
                paintingdict[institutionprop[0]][u'institution']=institutionprop[2]

            locationprops = data.get('props').get(str(276))

            for locationprop in locationprops:
                paintingdict[locationprop[0]][u'institution']=locationprop[2]
                
            urlprops = data.get('props').get(str(973))

            for urlprop in urlprops:
                paintingdict[urlprop[0]][u'url']=urlprop[2]

            for paintingid, painting in paintingdict.items():
                ci = (u'%s' % (painting.get(u'creator'),), u'%s' % (painting.get(u'institution'),))

                if not ci in self.wikidataCIWithout:
                    self.wikidataCIWithout[ci] = []
                self.wikidataCIWithout[ci].append({ u'item' : u'%s' % (paintingid,), u'url' : painting.get(u'url')})

                # Location and collection are sometimes different:
                if painting.get(u'location') and painting.get(u'institution')!=painting.get(u'location'):
                    ci2 = (u'%s' % (painting.get(u'creator'),), u'%s' % (painting.get(u'location'),))
                    if not ci2 in self.wikidataCIWithout:
                        self.wikidataCIWithout[ci2] = []
                    self.wikidataCIWithout[ci2].append({ u'item' : u'%s' % (paintingid,), u'url' : painting.get(u'url')})

                (creator, institutions) = ci
                if not creator in creatorcounts:
                    creatorcounts[creator]=0
                creatorcounts[creator] = creatorcounts[creator] + 1
                
                if not institutions in institutioncounts:
                    institutioncounts[institutions]=0
                institutioncounts[institutions] = institutioncounts[institutions] + 1

                if not ci in cicounts:
                    cicounts[ci]=0
                cicounts[ci] = cicounts[ci] + 1

        pywikibot.output(u'The top creators without image on Wikidata are:')
        for creator in sorted(creatorcounts, key=creatorcounts.get, reverse=True)[:20]:
            pywikibot.output(u'* {{Q|%s}} - %s' % (creator, creatorcounts[creator]))

        pywikibot.output(u'The top institutions without image on Wikidata are:')
        for institution in sorted(institutioncounts, key=institutioncounts.get, reverse=True)[:20]:
            pywikibot.output(u'* {{Q|%s}} - %s' % (institution, institutioncounts[institution]))

        pywikibot.output(u'The top combinations without image on Wikidata are:')
        for (creator, institution)  in sorted(cicounts, key=cicounts.get, reverse=True)[:10]:
            pywikibot.output(u'* {{Q|%s}} & {{Q|%s}} - %s' % (creator, institution, cicounts[ci]))
        return

    def getWikidataWith(self):
        '''
        Query Wikidata to get paintings with images, but with creator and collection
        '''
        paintingdict = {}
        result = {}

        #wdq.wmflabs.org/api?q=CLAIM[31:3305213] AND CLAIM[170] AND CLAIM[195] AND CLAIM[357] AND NOCLAIM[18]&props=170,195

        query = u'CLAIM[31:3305213] AND CLAIM[170] AND CLAIM[195] AND CLAIM[18]'
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=0) # 30, be careful
        data = wd_query.query(wd_queryset, props=[str(18),str(170),str(195),str(973)])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            for item in data.get('items'):
                paintingdict[item] = { u'creator' : False, u'institution' : False, u'url' : u'', u'image' : False}

            imageprops = data.get('props').get(str(18))

            for imageprop in imageprops:
                #print imageprop[2]
                #self.wikidataImages[imageprop[2]]=imageprop[0]
                if type(imageprop[2]) is not int:
                    paintingdict[imageprop[0]][u'image']=imageprop[2].replace(u' ', u'_')
                    self.wikidataImages[imageprop[2].replace(u' ', u'_')]=imageprop[0]
                    if u'zondeval' in imageprop[2]:
                        pywikibot.output(u'Found in Wikidata %s on item Q%s' % (imageprop[2].replace(u' ', u'_'), imageprop[0]))
                        if imageprop[2].replace(u' ', u'_')==u'Cornelis_van_Haarlem_-_De_zondeval.jpg':
                            pywikibot.output(u'And it gives an exact string match')
                        else:
                            pywikibot.output(u'No match')
                
            creatorprops = data.get('props').get(str(170))

            for creatorprop in creatorprops:
                paintingdict[creatorprop[0]][u'creator']=creatorprop[2]

            institutionprops = data.get('props').get(str(195))

            for institutionprop in institutionprops:
                paintingdict[institutionprop[0]][u'institution']=institutionprop[2]

            urlprops = data.get('props').get(str(973))

            for urlprop in urlprops:
                paintingdict[urlprop[0]][u'url']=urlprop[2]

            for paintingid, painting in paintingdict.items():
                ci = (u'%s' % (painting.get(u'creator'),), u'%s' % (painting.get(u'institution'),))
                if not ci in self.wikidataCIWith:
                    self.wikidataCIWith[ci] = []
                self.wikidataCIWith[ci].append({ u'id' : str(paintingid), u'image' : painting.get(u'image'), u'url' : painting.get(u'url') })

    def addMissingCommonsLinks(self):
        '''
        Bla %02d
        '''
        pageTitle = u'User:Multichill/Unable to add Wikidata link'
        page = pywikibot.Page(self.commons, title=pageTitle)
        text = u'{{/header}}\n'
        
        missingCommonsLinks = set(self.wikidataImages.keys()) & set(self.commonsNoLink)
        for filename in missingCommonsLinks:
            success = self.addMissingCommonsLink(filename, self.wikidataImages.get(filename))
            if not success:
                text = text + u'* [[:File:%s]] - <nowiki>|</nowiki> wikidata = Q%s\n' % (filename, self.wikidataImages.get(filename))
                
        text = text + u'\n[[Category:User:Multichill]]\n'
            
        summary = u'Updating list of images to which to bot was unable to add a link'
        pywikibot.output(summary)
        page.put(text, summary)

    def addMissingCommonsLink(self, filename, wikidataitem):
        """
        Try to add a missing link to Commons. Returns True if it worked and False if it failed
        """
        filepage = pywikibot.FilePage(self.commons, title=filename)

        text = filepage.get()
        replaceregex = u'\{\{(Artwork|Painting|Art Photo|Google Art Project|Google Cultural Institute|Walters Art Museum artwork|NARA-image-full)'
        emptywikidataregex = u'(\s*\|\s*wikidata\s*=)\s*\n'
        #cleanupregex = u'(\|wikidata=Q\d+)(.+)(\s*\|\s*wikidata\s*=\s*\n)'
        wikidataregex = u'[wW]ikidata\s*=\s*(Q\d+)\s*'

        pywikibot.output(u'Working on %s' % (filepage.title(),))

        #emptywdmatch = re.search(emptywikidataregex, text)
        wdmatch = re.search(wikidataregex, text)
        
        if wdmatch:
            # Template with duplicate template problems might hit this one or when database query is a bit stale
            pywikibot.output(u'Seems to already link to Wikidata %s' % (wdmatch.group(1),))
            return False

        # First try to update an existing fiel
        newtext = re.sub(emptywikidataregex, u'\\1Q%s\n' % (wikidataitem,), text, count=1)

        if text==newtext:
            #Ok, that didn't work, just slap it at the top   
            newtext = re.sub(replaceregex, u'{{\\1\n|wikidata=Q%s' % (wikidataitem,), text, count=1, flags=re.I)
            if text==newtext:
                pywikibot.output(u'Unable to add Wikidata link to %s' % (filename,))
                return False

        #nextext = re.sub(cleanupregex, u'\\1\\2', newtext, count=1, flags=re.DOTALL)

        pywikibot.showDiff(text, newtext)
        summary = u'Adding link to [[:d:Q%s]] based on usage on that item' % (wikidataitem,)
        pywikibot.output(summary)
        filepage.put(newtext, summary=summary)
        return True

    def addMissingWikidataStatements(self):
        '''
        Disabled. Denkfoutje gemaakt. Het moet file -> item zijn, er kunnen namelijk meerdere files zijn die naar hetzelfde item linken
        '''
        return
        missingWikidataClaims = set(self.wikidataNoImages) & set(self.commonsLink.values())

        for itemid in missingWikidataClaims:
            paintingItem = pywikibot.ItemPage(self.repo, title=u'Q%s' % (itemid,))
            filename = self.commonsLink.get(itemid)
            filepage = pywikibot.FilePage(self.commons, title=filename)
            data = paintingItem.get()
            claims = data.get('claims')
            
            if u'P18' not in claims:
                newclaim = pywikibot.Claim(self.repo, u'P18')
                newclaim.setTarget(filepage)
                summary = u'based on Commons backlink'
                paintingItem.addClaim(newclaim, summary=summary)

    def publishWikidataSuggestions(self, samplesize=300, maxlines=1000):
        #self.commonsWithoutKeys = set(self.commonsCIWithout.keys())
        #self.wikidataWithoutKeys = set(self.wikidataCIWithout.keys())

        self.bothWithoutKeys = set(self.commonsCIWithout.keys()) & set(self.wikidataCIWithout.keys())

        #pywikibot.output(u'Found %s possible creator & collection combinations' % (len(self.bothWithoutKeys),))

        if self.filter:
            self.sampleKeys = self.bothWithoutKeys
        else:
            self.sampleKeys = random.sample(self.bothWithoutKeys, samplesize)

        pageTitle = u'User:Multichill/Image suggestions'
        line = 0
        

        page = pywikibot.Page(self.repo, title=pageTitle)
        
        text = u'{{/header}}\n{| class="wikitable sortable"\n'
        #text = text + u'! Painting !! Image title !! Link !! Creator !! Collection !! Image !! \n'
        text = text + u'! Painting !! Image !! Image title !! Link !! Add !! Creator !! Collection\n'
        for key in self.sampleKeys: #sorted(self.sampleKeys, reverse=True):
            firstrow = True
            (creator, institution) = key
            # Only work on certain collections
            if self.filter and not institution in self.filtercollections:
                continue

            # Anonymous is messing things up
            if not self.filter and creator==u'4233718':
                continue
            elif creator==u'1507231' or creator==u'192062': #Temp to get rid of the guys
                continue
                
            for image in self.commonsCIWithout.get(key):
                for paintingdict in self.wikidataCIWithout.get(key):
                    paintingitem = paintingdict.get('item')
                    paintingurl = paintingdict.get('url')
                    line = line + 1
                    
                    if line < maxlines:
                        text = text + u'|-\n'
                    
                        addlink = u'[https://tools.wmflabs.org/wikidata-todo/quick_statements.php?list={{subst:urlencode:Q%s\tP18\t"%s"}} Add]' % (paintingitem, image) # urlencode?
                        describedlink = u''
                        if paintingurl:
                            describedlink = u'[%s Link]' % (paintingurl,)
   
                        if firstrow:
                            #text = text + u'| {{Q|%s}} || <small>%s</small> || %s || {{Q|%s}} || {{Q|%s}} || [[File:%s|100px]] || %s \n' % (paintingitem, image, describedlink, creator, institution, image, addlink)
                            text = text + u'| {{Q|%s}} || [[File:%s|100px]] || <small>%s</small> || %s || %s || {{Q|%s}} || {{Q|%s}}   \n' % (paintingitem, image, image, describedlink, addlink, creator, institution,)
                            firstrow=False
                        else:
                            #text = text + u'| {{Q|%s}} || <small>%s</small> || %s || [[Q%s]] || [[Q%s]] || [[File:%s|100px]] || %s \n' % (paintingitem, image, describedlink, creator, institution, image, addlink)
                            text = text + u'| {{Q|%s}} || [[File:%s|100px]] || <small>%s</small> || %s || %s || [[Q%s]] || [[Q%s]]   \n' % (paintingitem, image, image, describedlink, addlink, creator, institution,)
           
        text = text + u'|}\n'
        text = text + u'\n[[Category:User:Multichill]]\n'

        possiblematches = 0
        for key in self.bothWithoutKeys:
            possiblematches = possiblematches + min(len(self.commonsCIWithout.get(key)),len(self.wikidataCIWithout.get(key)))
            
        summary = u'Updating image suggestions. %s suggestions out a total of %s suggestions in %s combinations' % (min(line, maxlines), possiblematches, len(self.bothWithoutKeys))
        pywikibot.output(summary)
        page.put(text, summary)


    def publishCommonsSuggestions(self, samplesize=300, maxlines=1500):
        """
        Publish a list of images pairs that might be the same

        FIXME: Left hand side should only show the image that is in use on Wikidata
        """
        self.bothWithoutKeys = set(self.commonsCIWithout.keys()) & set(self.commonsCIWith.keys())

        if self.filter:
            self.sampleKeys = self.bothWithoutKeys
        else:
            self.sampleKeys = random.sample(self.bothWithoutKeys, samplesize)

        pageTitle = u'User:Multichill/Same image without Wikidata'
        line = 0
        wikidataimageslist = self.wikidataImages.keys()
        
        page = pywikibot.Page(self.commons, title=pageTitle)
        # self.commonsCIWith[ci].append({ u'image' : match.group("image"), u'item' : match.group("paintingitem") })
        text = u'{{/header}}\n{| class="wikitable sortable"\n'
        text = text + u'! Image Wikidata !! Image without !! Wikidata id !! To add !! Filenames\n'
        for key in self.sampleKeys: #sorted(self.sampleKeys, reverse=True):
            firstrow = True
            (creator, institution) = key
            # Only work on certain collections
            if self.filter and not institution in self.filtercollections:
                continue
            for imagedict in self.commonsCIWith.get(key):
                # Only use images that are in use on Wikidata
                if imagedict.get('image') in wikidataimageslist:
                    for imagewithout in self.commonsCIWithout.get(key):
                        line = line + 1
                        
                        if line < maxlines:
                            text = text + u'|-\n'
                            text = text + u'| [[File:%s|150px]] || [[File:%s|150px]] || [[:d:Q%s|Q%s]] || <nowiki>|</nowiki> wikidata = Q%s<BR/>[{{fullurl:File:%s|action=edit&withJS=MediaWiki:AddWikidata.js&wikidataid=Q%s}} Add] || %s<BR/>%s\n' % (imagedict.get('image'), imagewithout, imagedict.get('item'), imagedict.get('item'), imagedict.get('item'), imagewithout, imagedict.get('item'), imagedict.get('image'), imagewithout)
           
        text = text + u'|}\n'
        text = text + u'\n[[Category:User:Multichill]]\n'

        possiblematches = 0
        for key in self.bothWithoutKeys:
            possiblematches = possiblematches + min(len(self.commonsCIWithout.get(key)),len(self.commonsCIWith.get(key)))
            
        summary = u'Updating same image suggestions. %s suggestions out a total of %s suggestions in %s combinations' % (min(line, maxlines), possiblematches, len(self.bothWithoutKeys))
        pywikibot.output(summary)
        page.put(text, summary)

    def publishCommonsNoTracker(self, maxlines=1000):
        """
        Publish a list of files that are in use on Wikidata, but don't have a tracker category
        Files that are in use on Wikidata, but not in the without Wikikidata category and also not in the with Wikidata category
        """
        nottracked = set(self.wikidataImages.keys()) - (set(self.commonsNoLink) | set(self.commonsLink.keys()))

        pageTitle = u'User:Multichill/Painting images no artwork template'

        page = pywikibot.Page(self.commons, title=pageTitle)

        text = u'{{/header}}\n'
        for filename in nottracked:
            text = text + u'* [[:File:%s]]\n' % filename
        text = text + u'\n[[Category:User:Multichill]]\n'

        summary = u'Updating list of %s painting images with no artwork template' % (len(nottracked),)
        pywikibot.output(summary)
        page.put(text, summary)
        
def main():
    paintingsMatchBot = PaintingsMatchBot()
    paintingsMatchBot.run()

if __name__ == "__main__":
    main()
