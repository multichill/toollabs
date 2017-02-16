#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This bot helps to get more painting itmes on Wikidata and image files on Commons linked.
It depends on 2 SQL queries on the Wikimedia Commons to gather the data and one SPARQL query.
The program grabs all the data and makes lookup tables. Based on the tables a lot of lists are produced. See:
* https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Image_suggestions
* https://commons.wikimedia.org/wiki/User:Multichill/Same_image_without_Wikidata

The bot will also try to add missing backlinks from Commons to Wikidata.
"""
import pywikibot
import requests
import re
import datetime
import random
import pywikibot.data.sparql

class PaintingsMatchBot:
    """
    A bot to enrich and create monuments on Wikidata
    """
    def __init__(self):
        """
        Build all the lookup tables to work on
        """
        self.commons = pywikibot.Site(u'commons', u'commons')
        self.repo = pywikibot.Site().data_repository()

        self.commonsNoLink = [] # List of images without a link
        self.commonsWithoutCIA = {} # Creator, institution & accession number -> image
        self.commonsWithoutCI = {} # Creator & instution -> image
        self.commonsWithoutIA = {} # Institution & accession number -> image
        self.commonsWithoutCA = {} # Creator & accession number -> image

        self.commonsLink = {} # Dictionary of images with a wikidata link, file -> item
        self.commonsWithCIA = {} # Creator, institution & accession number -> image & item
        self.commonsWithCI = {} # Creator & instution -> image & item
        self.commonsWithIA = {} # Institution & accession number -> image & item
        self.commonsWithCA = {} # Creator & accession number -> image & item

        self.wikidataNoImages = {} # Dictionary of items without images -> item & url
        self.wikidataWithoutCIA = {} # Creator, institution & accession number -> item & url
        self.wikidataWithoutCI = {} # Creator & instution -> item & url
        self.wikidataWithoutIA = {} # Institution & accession number -> item & url
        self.wikidataWithoutCA = {} # Creator & accession number -> item & url

        self.wikidataImages = {} # Dictionary of image on wikidata file -> item, image & url
        self.wikidataWithCIA = {} # Creator, institution & accession number -> item, image & url
        self.wikidataWithCI = {} # Creator & instution -> item, image & url
        self.wikidataWithIA = {} # Institution & accession number -> item, image & url
        self.wikidataWithCA = {} # Creator & accession number -> item, image & url

        self.getCommonsWithoutLookupTables()

        print 'self.commonsNoLink %s' % (len(self.commonsNoLink),)
        print 'self.commonsWithoutCIA %s' % (len(self.commonsWithoutCIA),)
        print 'self.commonsWithoutCI %s' % (len(self.commonsWithoutCI),)
        print 'self.commonsWithoutIA %s' % (len(self.commonsWithoutIA),)
        print 'self.commonsWithoutCA %s' % (len(self.commonsWithoutCA),)

        self.getCommonsWithLookupTables()

        print 'self.commonsLink %s' % (len(self.commonsLink),)
        print 'self.commonsWithCIA %s' % (len(self.commonsWithCIA),)
        print 'self.commonsWithCI %s' % (len(self.commonsWithCI),)
        print 'self.commonsWithIA %s' % (len(self.commonsWithIA),)
        print 'self.commonsWithCA %s' % (len(self.commonsWithCA),)

        self.getWikidataLookupTables()

        print 'self.wikidataNoImages %s' % (len(self.wikidataNoImages),)
        print 'self.wikidataWithoutCIA %s' % (len(self.wikidataWithoutCIA),)
        print 'self.wikidataWithoutCI %s' % (len(self.wikidataWithoutCI),)
        print 'self.wikidataWithoutIA %s' % (len(self.wikidataWithoutIA),)
        print 'self.wikidataWithoutCA %s' % (len(self.wikidataWithoutCA),)

        print 'self.wikidataImages %s' % (len(self.wikidataImages),)
        print 'self.wikidataWithCIA %s' % (len(self.wikidataWithCIA),)
        print 'self.wikidataWithCI %s' % (len(self.wikidataWithCI),)
        print 'self.wikidataWithIA %s' % (len(self.wikidataWithIA),)
        print 'self.wikidataWithCA %s' % (len(self.wikidataWithCA),)

    def run(self):
        """
        Starts the robot.
        """
        #self.addWikidataSuggestions()
        self.publishAllWikidataSuggestions()
        self.addMissingCommonsWikidataLinks()
        self.publishAllCommonsSuggestions()
        self.publishCommonsNoTracker()

    def getCommonsWithoutLookupTables(self):
        '''
        Get the dicts for the images on Commons without a link to Wikidata
        '''
        url = u'http://tools.wmflabs.org/multichill/queries2/commons/paintings_without_wikidata_all.txt'
        regex = u'^\* \[\[:File:(?P<image>[^\]]+)\]\] - (?P<creator>Q\d+|None) - (?P<institution>Q\d+|None) - (?P<invnum>.+)$'
        invurlregex = u'^\[(http[^\s]+)\s(.+)\]$'
        queryPage = requests.get(url)
        for match in re.finditer(regex, queryPage.text, flags=re.M):
            image = match.group("image")
            if match.group("creator").strip().startswith(u'Q'):
                creator = match.group("creator").strip()
            else:
                creator = None
            if match.group("institution").strip().startswith(u'Q'):
                institution = match.group("institution").strip()
            else:
                institution = None
            if match.group("invnum").strip()==u'None':
                invnum = None
            else:
                invnum = match.group("invnum").strip()
                invurlmatch = re.match(invurlregex, invnum)
                if invurlmatch:
                    invnum = invurlmatch.group(2)

            ciakey = None
            cikey = None
            iakey = None
            cakey = None

            if creator and institution and invnum:
                ciakey = (creator, institution, invnum)
            if creator and institution:
                cikey = (creator, institution)
            if institution and invnum:
                iakey = (institution, invnum)
            if creator and invnum:
                cakey = (creator, invnum)

            self.commonsNoLink.append(image)
            if ciakey:
                if not ciakey in self.commonsWithoutCIA:
                    self.commonsWithoutCIA[ciakey] = []
                self.commonsWithoutCIA[ciakey].append(image)
            if cikey:
                if not cikey in self.commonsWithoutCI:
                    self.commonsWithoutCI[cikey] = []
                self.commonsWithoutCI[cikey].append(image)
            if iakey:
                if not iakey in self.commonsWithoutIA:
                    self.commonsWithoutIA[iakey] = []
                self.commonsWithoutIA[iakey].append(image)
            if cakey:
                if not cakey in self.commonsWithoutCA:
                    self.commonsWithoutCA[cakey] = []
                self.commonsWithoutCA[cakey].append(image)

    def getCommonsWithLookupTables(self):
        '''
        Get the dicts for the images on Commons with a link to Wikidata
        '''
        url = u'http://tools.wmflabs.org/multichill/queries2/commons/paintings_with_wikidata_all.txt'
        regex = u'^\* \[\[:File:(?P<image>[^\]]+)\]\] - (?P<paintingitem>Q\d+) - (?P<creator>Q\d+) - (?P<institution>Q\d+) - (?P<invnum>.+)$'
        invurlregex = u'^\[(http[^\s]+)\s(.+)\]$'
        queryPage = requests.get(url)

        for match in re.finditer(regex, queryPage.text, flags=re.M):
            image = match.group("image")
            item = match.group("paintingitem")
            if match.group("creator").strip().startswith(u'Q'):
                creator = match.group("creator").strip()
            else:
                creator = None
            if match.group("institution").strip().startswith(u'Q'):
                institution = match.group("institution").strip()
            else:
                institution = None
            if match.group("invnum").strip()==u'None':
                invnum = None
            else:
                invnum = match.group("invnum").strip()
                invurlmatch = re.match(invurlregex, invnum)
                if invurlmatch:
                    invnum = invurlmatch.group(2)

            ciakey = None
            cikey = None
            iakey = None
            cakey = None

            if creator and institution and invnum:
                ciakey = (creator, institution, invnum)
            if creator and institution:
                cikey = (creator, institution)
            if institution and invnum:
                iakey = (institution, invnum)
            if creator and invnum:
                cakey = (creator, invnum)

            infodict = { u'image' : image, u'item' : item }
            self.commonsLink[image]=item

            if ciakey:
                if not ciakey in self.commonsWithCIA:
                    self.commonsWithCIA[ciakey] = []
                self.commonsWithCIA[ciakey].append(infodict)
            if cikey:
                if not cikey in self.commonsWithCI:
                    self.commonsWithCI[cikey] = []
                self.commonsWithCI[cikey].append(infodict)
            if iakey:
                if not iakey in self.commonsWithIA:
                    self.commonsWithIA[iakey] = []
                self.commonsWithIA[iakey].append(infodict)
            if cakey:
                if not cakey in self.commonsWithCA:
                    self.commonsWithCA[cakey] = []
                self.commonsWithCA[cakey].append(infodict)

    def getWikidataLookupTables(self):
        '''
        Query to make 10 lookup tables.
        These 4 lookup tables for with and without images:
        * CIA : Creator, institution & accession number
        * CI : Creator & instution
        * IA : Institution & accession number
        * CA: Creator & accession number
        And also:
        * Wikidata id -> url table(?)
        * Filename -> wikidata id
        '''
        query = u"""SELECT ?item ?image ?creator ?institution ?invnum ?location ?url WHERE {
        ?item wdt:P31/wdt:P279* wd:Q3305213 .
        OPTIONAL { ?item wdt:P18 ?image } .
        OPTIONAL { ?item wdt:P170 ?creator } .
        OPTIONAL { ?item wdt:P195 ?institution } .
        OPTIONAL { ?item wdt:P217 ?invnum } .
        OPTIONAL { ?item wdt:P276 ?location } .
        OPTIONAL { ?item wdt:P973 ?url } .
}"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            item = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            # First clean up and put in a dictionary
            paintingdict = { u'item' : item,
                             u'image' : False,
                             u'creator' : False,
                             u'institution' : False,
                             u'invnum' : False,
                             u'location' : False,
                             u'url' : False }
            if resultitem.get('image'):
                paintingdict['image'] = pywikibot.FilePage(pywikibot.Site('commons', 'commons'),resultitem.get('image').replace(u'http://commons.wikimedia.org/wiki/Special:FilePath/', u'')).title(underscore=True, withNamespace=False)
            if resultitem.get('creator'):
                paintingdict ['creator'] = resultitem.get('creator').replace(u'http://www.wikidata.org/entity/', u'')
            if resultitem.get('institution'):
                paintingdict['institution'] = resultitem.get('institution').replace(u'http://www.wikidata.org/entity/', u'')
            if resultitem.get('invnum'):
                paintingdict['invnum'] = resultitem.get('invnum')
            if resultitem.get('location'):
                paintingdict['location'] = resultitem.get('location').replace(u'http://www.wikidata.org/entity/', u'')
            if resultitem.get('url'):
                paintingdict['url'] = resultitem.get('url')

            ciakey = None
            clakey = None
            cikey = None
            clkey = None
            iakey = None
            lakey = None
            cakey = None

            if paintingdict.get(u'creator') and paintingdict.get(u'institution') and paintingdict.get(u'invnum'):
                ciakey = (paintingdict.get(u'creator'),
                          paintingdict.get(u'institution'),
                          paintingdict.get(u'invnum'))
            if paintingdict.get(u'creator') and paintingdict.get(u'location') and paintingdict.get(u'invnum'):
                clakey = (paintingdict.get(u'creator'),
                          paintingdict.get(u'location'),
                          paintingdict.get(u'invnum'))
            if paintingdict.get(u'creator') and paintingdict.get(u'institution'):
                cikey = (paintingdict.get(u'creator'),
                         paintingdict.get(u'institution'))
            if paintingdict.get(u'creator') and paintingdict.get(u'location'):
                clkey = (paintingdict.get(u'creator'),
                         paintingdict.get(u'location'))
            if paintingdict.get(u'institution') and paintingdict.get(u'invnum'):
                iakey = (paintingdict.get(u'institution'),
                         paintingdict.get(u'invnum'))
            if paintingdict.get(u'location') and paintingdict.get(u'invnum'):
                lakey = (paintingdict.get(u'location'),
                         paintingdict.get(u'invnum'))
            if paintingdict.get(u'creator') and paintingdict.get(u'invnum'):
                cakey = (paintingdict.get(u'creator'),
                         paintingdict.get(u'invnum'))

            if paintingdict.get(u'image'):
                self.wikidataImages[paintingdict.get(u'image')] = paintingdict
                if ciakey:
                    if not ciakey in self.wikidataWithCIA:
                        self.wikidataWithCIA[ciakey] = []
                    self.wikidataWithCIA[ciakey].append(paintingdict)
                if clakey and clakey!=ciakey:
                    if not clakey in self.wikidataWithCIA:
                        self.wikidataWithCIA[clakey] = []
                    self.wikidataWithCIA[clakey].append(paintingdict)
                if cikey:
                    if not cikey in self.wikidataWithCI:
                        self.wikidataWithCI[cikey] = []
                    self.wikidataWithCI[cikey].append(paintingdict)
                if clkey and clkey!=cikey:
                    if not clkey in self.wikidataWithCI:
                        self.wikidataWithCI[clkey] = []
                    self.wikidataWithCI[clkey].append(paintingdict)
                if iakey:
                    if not iakey in self.wikidataWithIA:
                        self.wikidataWithIA[iakey] = []
                    self.wikidataWithIA[iakey].append(paintingdict)
                if lakey and lakey!=iakey:
                    if not lakey in self.wikidataWithIA:
                        self.wikidataWithIA[lakey] = []
                    self.wikidataWithIA[lakey].append(paintingdict)
                if cakey:
                    if not cakey in self.wikidataWithCA:
                        self.wikidataWithCA[cakey] = []
                    self.wikidataWithCA[cakey].append(paintingdict)
            else:
                self.wikidataNoImages[paintingdict.get(u'item')] = paintingdict
                if ciakey:
                    if not ciakey in self.wikidataWithoutCIA:
                        self.wikidataWithoutCIA[ciakey] = []
                    self.wikidataWithoutCIA[ciakey].append(paintingdict)
                if clakey and clakey!=ciakey:
                    if not clakey in self.wikidataWithoutCIA:
                        self.wikidataWithoutCIA[clakey] = []
                    self.wikidataWithoutCIA[clakey].append(paintingdict)
                if cikey:
                    if not cikey in self.wikidataWithoutCI:
                        self.wikidataWithoutCI[cikey] = []
                    self.wikidataWithoutCI[cikey].append(paintingdict)
                if clkey and clkey!=cikey:
                    if not clkey in self.wikidataWithoutCI:
                        self.wikidataWithoutCI[clkey] = []
                    self.wikidataWithoutCI[clkey].append(paintingdict)
                if iakey:
                    if not iakey in self.wikidataWithoutIA:
                        self.wikidataWithoutIA[iakey] = []
                    self.wikidataWithoutIA[iakey].append(paintingdict)
                if lakey and lakey!=iakey:
                    if not lakey in self.wikidataWithoutIA:
                        self.wikidataWithoutIA[lakey] = []
                    self.wikidataWithoutIA[lakey].append(paintingdict)
                if cakey:
                    if not cakey in self.wikidataWithoutCA:
                        self.wikidataWithoutCA[cakey] = []
                    self.wikidataWithoutCA[cakey].append(paintingdict)

    def publishAllWikidataSuggestions(self):
        """
        Publish the 4 suggestion pages on Wikidata
        """
        self.publishWikidataSuggestions(self.commonsWithoutCIA,
                                        self.wikidataWithoutCIA,
                                        u'Wikidata:WikiProject sum of all paintings/Image suggestions/Creator, institution and inventory number match')
        self.publishWikidataSuggestions(self.commonsWithoutCI,
                                        self.wikidataWithoutCI,
                                        u'Wikidata:WikiProject sum of all paintings/Image suggestions/Creator and institution match')
        self.publishWikidataSuggestions(self.commonsWithoutIA,
                                        self.wikidataWithoutIA,
                                        u'Wikidata:WikiProject sum of all paintings/Image suggestions/Institution and inventory number match')
        self.publishWikidataSuggestions(self.commonsWithoutCA,
                                        self.wikidataWithoutCA,
                                        u'Wikidata:WikiProject sum of all paintings/Image suggestions/Creator and inventory number match')


    def publishWikidataSuggestions(self, commonsdict, wikidatadict, pageTitle, samplesize=300, maxlines=1000):
        matchesKeys = set(commonsdict.keys()) & set(wikidatadict.keys())
        print u'Found %s matches for %s' % (len(matchesKeys), pageTitle)

        if len(matchesKeys) > samplesize:
            publishKeys = random.sample(matchesKeys, samplesize)
        else:
            publishKeys = matchesKeys

        line = 0
        page = pywikibot.Page(self.repo, title=pageTitle)

        text = u'{{Wikidata:WikiProject sum of all paintings/Image suggestions/header}}\n{| class="wikitable sortable"\n'
        text = text + u'! Painting !! Image !! Image title !! Link !! Add !! Creator !! Collection !! Inventory number\n'
        for key in publishKeys:
            firstrow = True
            #(creator, institution, inv) = key

            for image in commonsdict.get(key):
                for paintingdict in wikidatadict.get(key):
                    #paintingitem = paintingdict.get('item')
                    #paintingurl = paintingdict.get('url')
                    line = line + 1

                    if line < maxlines:
                        text = text + u'|-\n'

                        addlink = u'[https://tools.wmflabs.org/wikidata-todo/quick_statements.php?list={{subst:urlencode:%s\tP18\t"%s"}} Add]' % (paintingdict.get('item'), image.replace(u'_', u' ')) # urlencode?
                        describedlink = u''
                        if paintingdict.get('url'):
                            describedlink = u'[%s Link]' % (paintingdict.get('url'),)

                        text = text + u'| {{Q|%s}} || [[File:%s|100px]] || <small>%s</small> || %s || %s ' % (paintingdict.get('item'),
                                                                                                              image,
                                                                                                              image,
                                                                                                              describedlink,
                                                                                                              addlink,
                                                                                                              )
                        if not paintingdict.get('creator'):
                            text = text + u'|| '
                        elif firstrow:
                            text = text + u'|| {{Q|%s}} ' % (paintingdict.get('creator'),)
                        else:
                            text = text + u'|| [[%s]] ' % (paintingdict.get('creator'),)

                        if not paintingdict.get('institution'):
                            text = text + u'|| '
                        elif firstrow:
                            text = text + u'|| {{Q|%s}} ' % (paintingdict.get('institution'),)
                        else:
                            text = text + u'|| [[%s]] ' % (paintingdict.get('institution'),)

                        if not paintingdict.get('invnum'):
                            text = text + u'|| \n'
                        elif firstrow:
                            text = text + u'|| %s \n' % (paintingdict.get('invnum'),)


        text = text + u'|}\n'
        text = text + u'\n[[Category:WikiProject sum of all paintings|Image suggestions/{{SUBPAGENAME}}]]\n'

        summary = u'Updating image suggestions. %s key matches out a total of %s key combinations that matched' % (len(publishKeys), len(matchesKeys))
        pywikibot.output(summary)
        page.put(text, summary)

    def publishAllCommonsSuggestions(self):
        """
        Publish the 8 Commons suggestion pages
        """
        self.publishCommonsSuggestions(self.commonsWithoutCIA,
                                       self.commonsWithCIA,
                                       u'User:Multichill/Same image without Wikidata/Commons creator, institution and inventory number match')
        self.publishCommonsSuggestions(self.commonsWithoutCI,
                                       self.commonsWithCI,
                                       u'User:Multichill/Same image without Wikidata/Commons creator and institution match')
        self.publishCommonsSuggestions(self.commonsWithoutIA,
                                       self.commonsWithIA,
                                       u'User:Multichill/Same image without Wikidata/Commons institution and inventory number match')
        self.publishCommonsSuggestions(self.commonsWithoutCA,
                                       self.commonsWithCA,
                                       u'User:Multichill/Same image without Wikidata/Commons creator and inventory number match')

        self.publishCommonsSuggestions(self.commonsWithoutCIA,
                                       self.wikidataWithCIA,
                                       u'User:Multichill/Same image without Wikidata/Wikidata creator, institution and inventory number match')
        self.publishCommonsSuggestions(self.commonsWithoutCI,
                                       self.wikidataWithCI,
                                       u'User:Multichill/Same image without Wikidata/Wikidata creator and institution match')
        self.publishCommonsSuggestions(self.commonsWithoutIA,
                                       self.wikidataWithIA,
                                       u'User:Multichill/Same image without Wikidata/Wikidata institution and inventory number match')
        self.publishCommonsSuggestions(self.commonsWithoutCA,
                                       self.wikidataWithCA,
                                       u'User:Multichill/Same image without Wikidata/Wikidata creator and inventory number match')

    def publishCommonsSuggestions(self, withoutdict, withdict, pageTitle, samplesize=300, maxlines=1000):
        matchesKeys = set(withoutdict.keys()) & set(withdict.keys())
        print u'Found %s matches for %s' % (len(matchesKeys), pageTitle)

        if len(matchesKeys) > samplesize:
            publishKeys = random.sample(matchesKeys, samplesize)
        else:
            publishKeys = matchesKeys

        line = 0
        page = pywikibot.Page(self.commons, title=pageTitle)
        text = u'{{User:Multichill/Same image without Wikidata/header}}\n{| class="wikitable sortable"\n'
        text = text + u'! Image Wikidata !! Image without !! Wikidata id !! To add !! Filenames\n'

        previousline = u''
        for key in publishKeys:
            for imagewithout in withoutdict.get(key):
                for withinfodict in withdict.get(key):
                    if line < maxlines and not imagewithout in self.commonsLink:
                        thisline = u'| [[File:%s|150px]] || [[File:%s|150px]] || [[:d:%s|%s]] || <nowiki>|</nowiki> wikidata = %s<BR/>[{{fullurl:File:%s|action=edit&withJS=MediaWiki:AddWikidata.js&wikidataid=%s}} Add] || %s<BR/>%s\n' % (withinfodict.get('image'),
                                                                                                                                                                                                                                                imagewithout,
                                                                                                                                                                                                                                                withinfodict.get('item'),
                                                                                                                                                                                                                                                withinfodict.get('item'),
                                                                                                                                                                                                                                                withinfodict.get('item'),
                                                                                                                                                                                                                                                imagewithout,
                                                                                                                                                                                                                                                withinfodict.get('item'),
                                                                                                                                                                                                                                                withinfodict.get('image'),
                                                                                                                                                                                                                                                imagewithout)
                        # Prevent duplicate lines
                        if thisline!=previousline:
                            text = text + u'|-\n'
                            text = text + thisline
                            previousline = thisline
                            line = line + 1

        text = text + u'|}\n'
        text = text + u'\n[[Category:User:Multichill]]\n'

        summary = u'Updating image suggestions. %s key matches out a total of %s key combinations that matched' % (len(publishKeys), len(matchesKeys))
        pywikibot.output(summary)
        page.put(text, summary)

    def addMissingCommonsWikidataLinks(self):
        '''
        Add missing links from Commons to Wikidata and report for which files it didn't work
        '''
        pageTitle = u'User:Multichill/Unable to add Wikidata link'
        page = pywikibot.Page(self.commons, title=pageTitle)
        text = u'{{/header}}\n'

        missingCommonsLinks = set(self.wikidataImages.keys()) & set(self.commonsNoLink)
        for filename in missingCommonsLinks:
            wikidataitem = self.wikidataImages.get(filename).get('item')
            success = self.addMissingCommonsWikidataLink(filename, wikidataitem)
            if success:
                # This prevents these files from showing up in the suggestions and missing link reports
                self.commonsLink[filename]=wikidataitem
            else:
                text = text + u'* [[:File:%s]] - <nowiki>|</nowiki> wikidata = %s\n' % (filename, wikidataitem)


        text = text + u'\n[[Category:User:Multichill]]\n'

        summary = u'Updating list of images to which to bot was unable to add a link'
        pywikibot.output(summary)
        page.put(text, summary)

    def addMissingCommonsWikidataLink(self, filename, wikidataitem):
        """
        Try to add a missing link to Commons. Returns True if it worked and False if it failed
        """
        filepage = pywikibot.FilePage(self.commons, title=filename)

        text = filepage.get()
        replaceregex = u'\{\{(Artwork|Painting|Art Photo|Google Art Project|Google Cultural Institute|Walters Art Museum artwork|NARA-image-full)'
        emptywikidataregex = u'(\s*\|\s*wikidata\s*=)\s*\n'
        wikidataregex = u'[wW]ikidata\s*=\s*(Q\d+)\s*'

        pywikibot.output(u'Working on %s' % (filepage.title(),))

        wdmatch = re.search(wikidataregex, text)

        if wdmatch:
            # Template with duplicate template problems might hit this one or when database query is a bit stale
            pywikibot.output(u'Seems to already link to Wikidata %s' % (wdmatch.group(1),))
            return False

        # First try to update an existing field
        newtext = re.sub(emptywikidataregex, u'\\1%s\n' % (wikidataitem,), text, count=1)

        if text==newtext:
            #Ok, that didn't work, just slap it at the top
            newtext = re.sub(replaceregex, u'{{\\1\n|wikidata=%s' % (wikidataitem,), text, count=1, flags=re.I)
            if text==newtext:
                pywikibot.output(u'Unable to add Wikidata link to %s' % (filename,))
                return False

        pywikibot.showDiff(text, newtext)
        summary = u'Adding link to [[:d:%s]] based on usage on that item' % (wikidataitem,)
        pywikibot.output(summary)
        filepage.put(newtext, summary=summary)
        return True

    def publishCommonsNoTracker(self):
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

    def addWikidataSuggestions(self):
        """
        Not used at the moment
        Some suggestions are too good to add by hand. Have the bot add them
        :return:
        """
        # Make a list of creator/institution/inventory number (ascession number)
        matchesKeys = set(self.commonsWithoutCIA.keys()) & set(self.wikidataWithoutCIA.keys())
        for key in matchesKeys:
            (creator, institution, inv) = key

            # Just get one image and one item
            image = self.commonsWithoutCIA.get(key)[0]
            paintingdict = self.wikidataWithoutCIA.get(key)[0]
            itemTitle = paintingdict.get('item')
            item = pywikibot.ItemPage(self.repo, title=itemTitle)
            data = item.get()
            claims = data.get('claims')
            if u'P18' not in claims:
                #url = paintingdict.get('url')
                summary = u'based on [[%s]] / [[%s]] / %s match with Commons' % (creator, institution, inv)
                newclaim = pywikibot.Claim(self.repo, u'P18')
                imagelink = pywikibot.Link(image, source=self.commons, defaultNamespace=6)
                imagePage = pywikibot.ImagePage(imagelink)
                if imagePage.isRedirectPage():
                    imagePage = pywikibot.ImagePage(imagePage.getRedirectTarget())
                newclaim.setTarget(imagePage)
                item.addClaim(newclaim, summary=summary)


def main():
    paintingsMatchBot = PaintingsMatchBot()
    paintingsMatchBot.run()

if __name__ == "__main__":
    main()
