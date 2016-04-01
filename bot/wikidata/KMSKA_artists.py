#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
C:\pywikibot\core>add_category.py -lang:wikidata -family:wikidata -file:categories_not_category.txt -namespace:0


"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib
import re
import pywikibot.data.wikidataquery as wdquery
import csv
import time
from collections import OrderedDict

class KmskaBot:
    """
    
    """
    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        
        self.repo = pywikibot.Site().data_repository()
        self.generator = generator
        
        self.progressPage = pywikibot.Page(self.repo, title=u'User:Multichill/KMSKA creators')
        #self.progressPage.get()

        #(self.paintings, self.creators) = self.getPaintersCreators()
        self.rkditems = self.getRKD()
        #print self.rkditems
        self.viafitems = self.getVIAF()

        self.kmskaitem = pywikibot.ItemPage(self.repo, title=u'Q1471477')

        #self.creators = self.fillCache()
        #self.missingCreators = self.getMissingCreators()
        
        #self.paintingIdProperty = paintingIdProperty
        #self.paintingIds = self.fillCache(self.paintingIdProperty)

    def getPaintersCreators(self, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        resultPaintings = {}
        resultCreators = []
        query = u'CLAIM[195:190804] AND CLAIM[170]'
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(170),str(217)])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            creatorprops = data.get('props').get(str(170))
            invprops = data.get('props').get(str(217))

            for item in data.get('items'):
                paintingdata = {u'creator' : u'',
                                u'inv' : u'',
                                }
                resultPaintings[item] = paintingdata
                
                    
            for prop in creatorprops:
                resultPaintings[prop[0]][u'creator'] = prop[2]
                resultCreators.append(prop[2])

            for prop in invprops:
                invid = prop[2]
                if invid.startswith(u'SK-'):
                    resultPaintings[prop[0]][u'inv'] =invid                
                    
                    
                
            
            #for prop in creatorprops:                
            #    # FIXME: This will overwrite id's that are used more than once.
            #    # Use with care and clean up your dataset first
            #    resultPaintings[prop[0]] = prop[2]
            #    resultCreators.append(prop[2])

            
            pywikibot.output('I now processed %s items for creators' % expectedItems)

        #print resultCreators
        #resultCreators = 

        #print resultPaintings
        return resultPaintings, set(resultCreators)

    def getRKD(self, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        query = u'CLAIM[650]'
        
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(650),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(650))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = u'Q%s' % (prop[0],)


            pywikibot.output('I expected %s items and now have %s items with RKD in cache' % (expectedItems, len(result)))

        return result

    def getVIAF(self, cacheMaxAge=0):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        query = u'CLAIM[214]'
        
        wd_queryset = wdquery.QuerySet(query)

        wd_query = wdquery.WikidataQuery(cacheMaxAge=cacheMaxAge)
        data = wd_query.query(wd_queryset, props=[str(214),])

        if data.get('status').get('error')=='OK':
            expectedItems = data.get('status').get('items')
            props = data.get('props').get(str(214))
            for prop in props:
                # FIXME: This will overwrite id's that are used more than once.
                # Use with care and clean up your dataset first
                result[prop[2]] = u'Q%s' % (prop[0],)

            pywikibot.output('I expected %s items and now have %s items with VIAF in cache' % (expectedItems, len(result)))

        return result
    
    def run (self):
        '''
        Work on all the painters
        '''

        
        totalFound = 0
        totalAnon = 0
        totalMissing = 0
        totalMissingAll = 0
        totalMissingRKD = 0
        totalMissingVIAF = 0
        totalMissingRKDVIAF = 0


        with open('kmska_artist_completed.csv', 'wb') as csvfile:
            fieldnames = ['creatorId', u'creator', u'creatorOdisPid', 'creatorViafPid', u'creatorRkdPid', u'creatorWikidataPid', u'creatorUlanPid', u'nlLabel', u'nlDesc', u'enLabel', u'enDesc']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            newtext = u'{| class="wikitable sortable"\n! creatorId !! creator !! nlLabel !! nlDesc !! enLabel !! enDesc !! creatorWikidataPid !! creatorOdisPid !! creatorViafPid !! creatorRkdPid !! creatorUlanPid\n'

            missingList = []

            for painterDict in self.generator:
                itemTitle = u''
                resultdata = {u'creatorId' : painterDict.get('creatorId'),
                              u'creator' : painterDict.get('creator'),
                              u'creatorOdisPid' : painterDict.get('creatorOdisPid'),
                              u'creatorViafPid' : painterDict.get('creatorViafPid'),
                              u'creatorRkdPid' : painterDict.get('creatorRkdPid'),
                              u'creatorWikidataPid' : painterDict.get('creatorWikidataPid'),
                              u'creatorUlanPid' : u'',
                              u'nlLabel' : '',
                              u'nlDesc' : '',
                              u'enLabel' : '',
                              u'enDesc' : '',
                              }
                if painterDict.get('creatorWikidataPid'):
                    itemTitle = painterDict.get('creatorWikidataPid').replace('http://www.wikidata.org/entity/', '').replace('http://www.wikidata.org/wiki/', '')

                if not itemTitle and painterDict.get('creatorRkdPid'):
                    print u'RKD!'
                    itemTitle = self.getItemFromRKD(painterDict.get('creatorRkdPid'))

                if not itemTitle and painterDict.get('creatorViafPid'):
                    print u'VIAF!'
                    itemTitle = self.getItemFromVIAF(painterDict.get('creatorViafPid'))
                    
                if itemTitle:
                    totalFound = totalFound + 1
                    print itemTitle
                    
                    item = pywikibot.ItemPage(self.repo, title=itemTitle)

                    if item.isRedirectPage():
                        item = item.getRedirectTarget()

                    resultdata[u'creatorWikidataPid'] = u'http://www.wikidata.org/entity/%s' % (item.title(),)
                    
                    data = item.get()
                    claims = data.get('claims')

                    if u'P650' not in claims and painterDict.get('creatorRkdPid'):
                        rkdid = painterDict.get('creatorRkdPid').replace(u'https://rkd.nl/explore/artists/', u'')
                        newclaim = pywikibot.Claim(self.repo, u'P650')
                        newclaim.setTarget(rkdid)
                        pywikibot.output('Adding RKDartists claim to %s' % item)
                        item.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P143')
                        newreference.setTarget(self.kmskaitem)
                        pywikibot.output('Adding new reference claim to %s' % item)
                        newclaim.addSources([newreference])

                    if u'P214' not in claims and painterDict.get('creatorViafPid'):
                        viafid = painterDict.get('creatorViafPid').replace(u'http://viaf.org/viaf/', u'')
                        newclaim = pywikibot.Claim(self.repo, u'P214')
                        newclaim.setTarget(viafid)
                        pywikibot.output('Adding VIAF claim to %s' % item)
                        item.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P143')
                        newreference.setTarget(self.kmskaitem)
                        pywikibot.output('Adding new reference claim to %s' % item)
                        newclaim.addSources([newreference])

                    if u'P650' in claims:
                        resultdata[u'creatorRkdPid'] = u'https://rkd.nl/explore/artists/%s' % (claims.get(u'P650')[0].getTarget(),)
                    if u'P214' in claims:
                        resultdata[u'creatorViafPid'] = u'http://viaf.org/viaf/%s' % (claims.get(u'P214')[0].getTarget(),)
                    if u'P245' in claims:
                        resultdata[u'creatorUlanPid'] = u'http://vocab.getty.edu/page/ulan/%s' % (claims.get(u'P245')[0].getTarget(),)

                    if data.get('labels').get('nl'):
                        resultdata[u'nlLabel'] = data.get('labels').get('nl').encode(u'utf-8')
                    if data.get('descriptions').get('nl'):
                        resultdata[u'nlDesc'] = data.get('descriptions').get('nl').encode(u'utf-8')
                    if data.get('labels').get('en'):
                        resultdata[u'enLabel'] = data.get('labels').get('en').encode(u'utf-8')
                    if data.get('descriptions').get('en'):
                        resultdata[u'enDesc'] = data.get('descriptions').get('en').encode(u'utf-8')                       
                    
                else:
                    if painterDict.get('creator').startswith('Anoniem'):
                        totalAnon = totalAnon + 1
                        resultdata[u'creatorWikidataPid'] = u'http://www.wikidata.org/entity/Q4233718'
                    else:
                        totalMissing = totalMissing + 1
                        missingList.append(painterDict.get('creator'))

                        if painterDict.get('creatorRkdPid') and painterDict.get('creatorViafPid'):
                            totalMissingRKDVIAF = totalMissingRKDVIAF + 1
                        elif painterDict.get('creatorRkdPid') and not painterDict.get('creatorViafPid'):
                            totalMissingRKD = totalMissingRKD + 1
                        elif not painterDict.get('creatorRkdPid') and painterDict.get('creatorViafPid'):
                            totalMissingVIAF = totalMissingVIAF + 1
                        else:
                            totalMissingAll = totalMissingAll + 1

                        if painterDict.get('creatorRkdPid') or painterDict.get('creatorViafPid'):
                            print u'Going to create shit'
                            item = self.makeCreatorItem(unicode(resultdata.get('creator'), u'utf-8'), painterDict.get('creatorRkdPid'), painterDict.get('creatorViafPid'))
                            resultdata[u'creatorWikidataPid'] = u'http://www.wikidata.org/entity/%s' % (item.title(),)

                writer.writerow(resultdata)
                newtext = newtext + u'|-\n'
                newtext = newtext + u'| %s ' % unicode(resultdata.get('creatorId'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('creator'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('nlLabel'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('nlDesc'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('enLabel'), u'utf-8')
                newtext = newtext + u'|| %s ' % unicode(resultdata.get('enDesc'), u'utf-8')
                newtext = newtext + u'|| [[%s]] ' % resultdata.get('creatorWikidataPid').replace(u'http://www.wikidata.org/entity/', u'')
                newtext = newtext + u'|| %s ' % resultdata.get('creatorOdisPid')
                newtext = newtext + u'|| %s ' % resultdata.get('creatorViafPid')
                newtext = newtext + u'|| %s\n' % resultdata.get('creatorRkdPid')
                newtext = newtext + u'|| %s\n' % resultdata.get('creatorUlanPid')
                #print newtext        

        newtext = newtext + u'|}\n\n'

        print u'Start missing list\n\n\n'

        print missingList

        print u'\n\n\n\n'

        missing = u''

        missing = missing + u'* Total found: %s\n' % (totalFound,)
        missing = missing + u'* Total anon: %s\n' % (totalAnon,)
        missing = missing + u'* Total missing: %s\n' % (totalMissing,)
        missing = missing + u'** Total missing, but do have RKD and VIAF: %s\n' % (totalMissingRKDVIAF,)
        missing = missing + u'** Total missing, but do have RKD: %s\n' % (totalMissingRKD,)
        missing = missing + u'** Total missing, but do have VIAF: %s\n' % (totalMissingVIAF,)
        missing = missing + u'** Total missing, but nothing at all: %s\n' % (totalMissingAll,)

        print missing
        newtext = newtext + missing
        newtext = newtext + u'\n\n[[Category:User:Multichill|{{SUBPAGENAME}}]]'
        summary = u'Updating list'
        self.progressPage.put(newtext, summary)
        
        
            
                
                
    def getItemFromRKD(self, rkdurl):
        '''
        Try to find the wikidata item id based on an rkd url
        '''
        rkdid = rkdurl.replace(u'https://rkd.nl/explore/artists/', u'')
        if rkdid in self.rkditems:
            return self.rkditems[rkdid]
        
        return u''

    def getItemFromVIAF(self, viafurl):
        '''
        Try to find the wikidata item id based on an viaf url
        '''
        viafid = viafurl.replace(u'http://viaf.org/viaf/', u'')
        print u'viaf id is %s' % viafid
        print len(self.viafitems)
        #18653592
        if viafid in self.viafitems:
            print u'found viaf!'
            return self.viafitems[viafid]
        
        return u''            
    def run3(self):
        '''
        Bla die bla
        '''
        text = self.progressPage.get()
        newtext = u''

        totalCreators = 0
        totalWithRKD = 0
        totalWithoutRKD = 0
        totalWithULAN = 0
        totalWithoutULAN = 0
        totalWithBoth = 0
        totalWithoutBoth = 0

        for itemId in sorted(self.creators):
            itemTitle = u'Q%s' % (itemId, )
            totalCreators = totalCreators + 1
            newtext = newtext + '* [[%s]]' % (itemTitle,)
            if itemTitle in self.rkditems:
                newtext = newtext + ' - [//rkd.nl/explore/artists/%s RKD %s]' % (self.rkditems[itemTitle], self.rkditems[itemTitle])
                totalWithRKD = totalWithRKD + 1
            if itemTitle in self.ulanitems:
                newtext = newtext + ' - [https://www.getty.edu/vow/ULANFullDisplay?find=&role=&nation=&subjectid=%s ULAN %s]'% (self.ulanitems[itemTitle], self.ulanitems[itemTitle])
                totalWithULAN = totalWithULAN + 1

            if itemTitle in self.rkditems and itemTitle in self.ulanitems:
                totalWithBoth = totalWithBoth + 1
                
            else:
                newtext = newtext + ' - Dob: {{#invoke:Wikidata|formatStatementsE|item=%s|property=P569}}' % (itemTitle, )
                newtext = newtext + ' - Dod: {{#invoke:Wikidata|formatStatementsE|item=%s|property=P570}}' % (itemTitle, )
                newtext = newtext + ' - Country: {{#invoke:Wikidata|formatStatementsE|item=%s|property=P27}}' % (itemTitle, )

                if not itemTitle in self.rkditems:
                    newtext = newtext + ' - https://rkd.nl/nl/explore/artists/record?query={{urlencode:{{Label|%s}}}}' % (itemTitle,)
                    totalWithoutRKD = totalWithoutRKD + 1
                    
                if not itemTitle in self.ulanitems:
                    newtext = newtext + ' - http://www.getty.edu/vow/ULANServlet?role=&page=1&nation=&find={{urlencode:{{Label|%s}}}}' % (itemTitle,)
                    totalWithoutULAN = totalWithoutULAN + 1

                if not itemTitle in self.rkditems and not itemTitle in self.ulanitems:
                    totalWithoutBoth = totalWithoutBoth + 1
                    

            newtext = newtext + '\n'

        newtext = newtext + u'\n\nSome statistics:\n'
        newtext = newtext + u'* Total creators: %s\n' % (totalCreators,)
        newtext = newtext + u'* Total match with RKD: %s\n' % (totalWithRKD,)
        newtext = newtext + u'* Total without RKD match: %s\n' % (totalWithoutRKD,)
        newtext = newtext + u'* Total match with ULAN: %s\n' % (totalWithULAN,)
        newtext = newtext + u'* Total without ULAN match: %s\n' % (totalWithoutULAN,)
        newtext = newtext + u'* Total with both RKD and ULAN match: %s\n' % (totalWithBoth,)
        newtext = newtext + u'* Total without both RKD and ULAN match: %s\n' % (totalWithoutBoth,)

        newtext = newtext + u'\n\n[[Category:User:Multichill|{{SUBPAGENAME}}]]'
        
        summary = u'Updating list of %s Rijksmuseum creators matched with RKD: %s hits, %s misses and ULAN: %s hits, %s misses, both: %s hits, %s misses' % (totalCreators, totalWithRKD, totalWithoutRKD,totalWithULAN, totalWithoutULAN, totalWithBoth, totalWithoutBoth)

        #pywikibot.output(newtext)
        pywikibot.output(summary)

        self.writeCSVfile()

        self.progressPage.put(newtext, summary)

    def writeCSVfile(self):
        '''
        Dump everything in an csv file for the Rijksmuseum
        '''
        with open('rijksmuseum_wikidata_schilderijen.csv', 'wb') as csvfile:
            fieldnames = ['schilderijid', u'inv', 'creatorid', u'rkd', 'ulan']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for paintingid, paintingfields in self.paintings.iteritems():
                data = {u'schilderijid' : u'Q%s' % (paintingid,),
                        u'inv' : paintingfields[u'inv'],
                        u'creatorid' : u'',
                        u'rkd' : u'',
                        u'ulan' : u'',
                        }
                creator = paintingfields[u'creator']
                if creator:
                    creatorItem = u'Q%s' % (creator,)
                    data[u'creatorid'] = creatorItem
                    
                    if creatorItem in self.rkditems:
                        data[u'rkd'] = self.rkditems[creatorItem]
                    if creatorItem in self.ulanitems:
                        data[u'ulan'] = self.ulanitems[creatorItem]
                
                writer.writerow(data)
                
            
        
            
        
    def fillCache(self):
        '''
        Fill the cache based on the progress page
        '''

        #Moet een normale dict zijn
        result = {}
        
        text = self.progressPage.get()
        regex = u'^\*\s(.+)\s->\s\[\[(Q\d+)\]\]$'
        for match in re.finditer(regex, text, flags=re.M):
            result[match.group(1)] = match.group(2)

        return result

    def getMissingCreators(self):
        '''
        Query Wikidata to fill the cache of monuments we already have an object for
        '''
        result = {}
        query = u'CLAIM[195:190804] AND NOCLAIM[170]'

        paintingGen = pagegenerators.PreloadingItemGenerator(WikidataQueryPageGenerator(query))

        for paintingItem in paintingGen:
            creator = paintingItem.get().get('descriptions').get('en').replace(u'painting by ', u'')
            
            if not creator in result:
                result[creator] = [paintingItem.title(),]
            else:
                result[creator].append(paintingItem.title())

        print result
        return result
                
                
        
    def flushCreators(self):
        '''
        Flush contents
        '''
        text = self.progressPage.get()
        newtext = u''

        # hier moet ik iets met sorted doen
        for name in sorted(self.creators):
            if self.creators[name].startswith(u'Q'):
                newtext = newtext + u'* %s -> [[%s]]\n' % (name, self.creators[name])
            else:
                newtext = newtext + u'* %s -> ??? %s\n' % (name, self.creators[name])

        newtext = newtext + u'\n\n[[Category:User:Multichill|{{SUBPAGENAME}}]]'
        pywikibot.showDiff(text,newtext)

        summary = u'Updating list of matched creators'

        self.progressPage.put(newtext, summary)
                

        #print newtext
        
        

    
                        
    def run2(self):
        """
        Starts the robot.
        """

        totalCreators = 0
        totalMatched = 0
        totalMissed = 0
        totalMissedAllInfo = 0
        totalMissedBasicInfo = 0
        totatlMissedCreators = 0
        
        for painter in self.generator:
            totalCreators = totalCreators + 1
            #print u'start painter loop'
            #print painter.get('name')

            (familyname, sep, givenname) = unicode(painter.get('name'), "utf-8").partition(u',')
            if givenname:
                name = '%s %s'.strip() % (givenname.strip(), familyname.strip(),)
            else:
                name = familyname
            pywikibot.output(name)

            if name in self.creators.keys():
                pywikibot.output(u'Found a creator in the cache.')
                totalMatched = totalMatched + 1

            else:
                

            
                creatergen = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(name, step=None, total=50, namespaces=[0], site=self.repo)))
                            
                newcreator = None

                for creatoritem in creatergen:
                    
                    #print creatoritem.title()
                    if creatoritem.get().get('labels').get('en') == name or creatoritem.get().get('labels').get('nl') == name:
                        #print creatoritem.get().get('labels').get('en')
                        #print creatoritem.get().get('labels').get('nl')
                        # Check occupation and country of citizinship
                        if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                            newcreator = creatoritem
                            continue
                    elif (creatoritem.get().get('aliases').get('en') and name in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and name in creatoritem.get().get('aliases').get('nl')):
                        if u'P106' in creatoritem.get().get('claims') and (u'P21' in creatoritem.get().get('claims') or u'P800' in creatoritem.get().get('claims')):
                            newcreator = creatoritem
                            continue

                if newcreator:
                    pywikibot.output(u'Found a new creator!!!')
                    pywikibot.output(newcreator.title())
                    totalMatched = totalMatched + 1
                    self.creators[name] = newcreator.title()
                else:
                    pywikibot.output(u'Did not find a creator.')
                    totalMissed = totalMissed + 1
                    infostring = u''

                    foundDob = False
                    foundPob = False
                    foundDod = False
                    foundPod = False
                    foundGender = False
                    foundNationality = False
                    
                    if painter.get('birth_on') and painter.get('birth.date.end'):
                        if painter.get('birth_on')==painter.get('birth.date.end'):
                            infostring = infostring + u'- dob: %s ' % (unicode(painter.get('birth_on'), "utf-8"),)
                            foundDob = True
                        else:
                            infostring = infostring + u'- dob: %s/%s ' % (unicode(painter.get('birth_on', "utf-8")), unicode(painter.get('birth.date.end'), "utf-8"))
                    if painter.get('born_at'):
                        infostring = infostring + u'- birth location: %s ' % (unicode(painter.get('born_at'), "utf-8"),)
                        foundPob = True

                    if painter.get('died_on') and painter.get('death.date.end'):
                        if painter.get('died_on')==painter.get('death.date.end'):
                            infostring = infostring + u'- dod: %s ' % (unicode(painter.get('died_on'), "utf-8"),)
                            foundDod = True
                        else:
                            infostring = infostring + u'- dod: %s/%s ' % (unicode(painter.get('died_on'), "utf-8"), unicode(painter.get('death.date.end'), "utf-8"))
                    if painter.get('died_at'):
                        infostring = infostring + u'- death location: %s ' % (unicode(painter.get('died_at'), "utf-8"),)
                        foundPod = True

                    if painter.get('gender'):
                        foundGender = True
                        if painter.get('gender')==u'man':
                            infostring = infostring + u'- gender: male '
                        elif painter.get('gender')==u'vrouw':
                            infostring = infostring + u'- gender: female '

                    if painter.get('nationality'):
                        infostring = infostring + u'- nationality: %s ' % (unicode(painter.get('nationality'), "utf-8"),)
                        foundNationality = True

                    if painter.get('source') and painter.get('source.id'):
                        if painter.get('source')==u'RKD':
                            infostring = infostring + u'- RKDartists: %s ' % (unicode(painter.get('source.id'), "utf-8"),)
      
                    

                    if foundDob and foundPob and foundDod and foundPod and foundGender and foundNationality:
                        totalMissedAllInfo = totalMissedAllInfo + 1
                        self.creators[name] = self.makePainterItem(name, painter)
                    elif foundDob and foundDod and foundGender:
                        totalMissedBasicInfo = totalMissedBasicInfo + 1
                        self.creators[name] = self.makePainterItem(name, painter)
                    elif name in self.missingCreators:
                        totatlMissedCreators = totatlMissedCreators + 1
                        self.creators[name] = self.makePainterItem(name, painter)
                        
                        
                    

                    self.creators[name] = infostring
                        
            pywikibot.output(u'Current score after %s creators: %s hits - %s missed (%s complete, %s basic, %s needed creators)' % (totalCreators, totalMatched, totalMissed, totalMissedAllInfo, totalMissedBasicInfo, totatlMissedCreators))


        self.flushCreators()


    def makeCreatorItem(self, name, rkd, viaf):
        '''
        Function to create a new painter, fill it and return the id
        '''

        data = {'labels': {},
                'descriptions': {},
                }

        for lang in (u'de', u'en', u'es', u'fr', u'nl'):
            data['labels'][lang] = {'language': lang, 'value': name}
            
        print data

        identification = {}
        summary = u'Creating new item for Royal Museum of Fine Arts Antwerp (KMSKA) artist'
        pywikibot.output(summary)

        result = self.repo.editEntity(identification, data, summary=summary)
        print result
        time.sleep(10)
        painterItemTitle = result.get(u'entity').get('id')
        painterItem = pywikibot.ItemPage(self.repo, title=painterItemTitle)
                         

        # It's a human
        humanItem = pywikibot.ItemPage(self.repo, title=u'Q5')
        newclaim = pywikibot.Claim(self.repo, u'P31')
        newclaim.setTarget(humanItem)
        painterItem.addClaim(newclaim)
        
        if rkd:
            rkdid = rkd.replace(u'https://rkd.nl/explore/artists/', u'')
            newclaim = pywikibot.Claim(self.repo, u'P650')
            newclaim.setTarget(rkdid)
            pywikibot.output('Adding RKDartists claim to %s' % painterItem)
            painterItem.addClaim(newclaim)

            newreference = pywikibot.Claim(self.repo, u'P143')
            newreference.setTarget(self.kmskaitem)
            pywikibot.output('Adding new reference claim to %s' % painterItem)
            newclaim.addSources([newreference])

        if viaf:
            viafid = viaf.replace(u'http://viaf.org/viaf/', u'')
            newclaim = pywikibot.Claim(self.repo, u'P214')
            newclaim.setTarget(viafid)
            pywikibot.output('Adding VIAF claim to %s' % painterItem)
            painterItem.addClaim(newclaim)

            newreference = pywikibot.Claim(self.repo, u'P143')
            newreference.setTarget(self.kmskaitem)
            pywikibot.output('Adding new reference claim to %s' % painterItem)
            newclaim.addSources([newreference])
            
        return painterItem.title()


    def getDate (self, datestring):
        if len(datestring)==4:
            newdate = pywikibot.WbTime(year=int(datestring))
            return newdate

        dateList = datestring.split(u'-')

        if len(dateList)==2:
            newdate = pywikibot.WbTime(year=int(dateList[0]), month=int(dateList[1]))
            return newdate
        elif len(dateList)==3:
            newdate = pywikibot.WbTime(year=int(dateList[0]), month=int(dateList[1]), day=int(dateList[2]))
            return newdate
            
            


        """  
                    
            newclaim = pywikibot.Claim(self.repo, u'P170')
            newclaim.setTarget(newcreator)
            pywikibot.output('Adding creator claim to %s' % paintingItem)
            paintingItem.addClaim(newclaim)

                            newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                            newreference.setTarget(europeanaUrl)
                            pywikibot.output('Adding new reference claim to %s' % paintingItem)
                            newclaim.addSource(newreference)
                            
                            #creatoritem = pywikibot.ItemPage(self.repo, creatorpage)
                            print creatoritem.title()
                            print creatoritem.get()
            
            
            # Make sure it's the Frans Hals Museum
            if painting['object']['proxies'][0]['about'].startswith(u'/proxy/provider/92034/GVNRC_FHM01'):
                paintingId = painting['object']['proxies'][0]['dcIdentifier']['def'][0].strip()
                uri = painting['object']['proxies'][0]['dcIdentifier']['def'][1].strip()
                europeanaUrl = u'http://europeana.eu/portal/record/%s.html' % (painting['object']['about'],)

                print paintingId
                print uri

                if painting['object']['proxies'][0].get('dcCreator'):
                    dcCreator = painting['object']['proxies'][0]['dcCreator']['def'][0].strip()
                else:
                    dcCreator = u'anoniem'
                #print dcCreator

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

                    data['labels'][u'nl'] = {'language': u'nl', 'value': painting['object']['title'][0]}
                    

                    if dcCreator:
                        data['descriptions']['en'] = {'language': u'en', 'value' : u'painting by %s' % (dcCreator,)}
                        data['descriptions']['nl'] = {'language': u'nl', 'value' : u'schilderij van %s' % (dcCreator,)}
                        

                    print data

                    identification = {}
                    summary = u'Creating new item with data from %s ' % (europeanaUrl,)
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

                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                    newreference.setTarget(uri)
                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                    newclaim.addSource(newreference)
                    
                    newqualifier = pywikibot.Claim(self.repo, u'P195') #Add collection, isQualifier=True
                    newqualifier.setTarget(fhmuseum)
                    pywikibot.output('Adding new qualifier claim to %s' % paintingItem)
                    newclaim.addQualifier(newqualifier)

                    collectionclaim = pywikibot.Claim(self.repo, u'P195')
                    collectionclaim.setTarget(fhmuseum)
                    pywikibot.output('Adding collection claim to %s' % paintingItem)
                    paintingItem.addClaim(collectionclaim)

                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                    newreference.setTarget(europeanaUrl)
                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                    collectionclaim.addSource(newreference)
                    
                    

                if paintingItem and paintingItem.exists():
                    
                    data = paintingItem.get()
                    claims = data.get('claims')
                    #print claims

                    # located in
                    if u'P276' not in claims:
                        newclaim = pywikibot.Claim(self.repo, u'P276')
                        newclaim.setTarget(fhmuseum)
                        pywikibot.output('Adding located in claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference)
                        

                    # instance of always painting while working on the painting collection
                    if u'P31' not in claims:
                        
                        dcformatItem = pywikibot.ItemPage(self.repo, title='Q3305213')

                        newclaim = pywikibot.Claim(self.repo, u'P31')
                        newclaim.setTarget(dcformatItem)
                        pywikibot.output('Adding instance claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference) 

                    # creator        
                    if u'P170' not in claims and dcCreator:
                        creategen = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(pagegenerators.SearchPageGenerator(dcCreator, step=None, total=10, namespaces=[0], site=self.repo)))
                        
                        newcreator = None


                        for creatoritem in creategen:
                            print creatoritem.title()
                            if creatoritem.get().get('labels').get('en') == dcCreator or creatoritem.get().get('labels').get('nl') == dcCreator:
                                print creatoritem.get().get('labels').get('en')
                                print creatoritem.get().get('labels').get('nl')
                                # Check occupation and country of citizinship
                                if u'P106' in creatoritem.get().get('claims') and u'P27' in creatoritem.get().get('claims'):
                                    newcreator = creatoritem
                                    continue
                            elif (creatoritem.get().get('aliases').get('en') and dcCreator in creatoritem.get().get('aliases').get('en')) or (creatoritem.get().get('aliases').get('nl') and dcCreator in creatoritem.get().get('aliases').get('nl')):
                                if u'P106' in creatoritem.get().get('claims') and u'P27' in creatoritem.get().get('claims'):
                                    newcreator = creatoritem
                                    continue

                        if newcreator:
                            pywikibot.output(newcreator.title())

                            newclaim = pywikibot.Claim(self.repo, u'P170')
                            newclaim.setTarget(newcreator)
                            pywikibot.output('Adding creator claim to %s' % paintingItem)
                            paintingItem.addClaim(newclaim)

                            newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                            newreference.setTarget(europeanaUrl)
                            pywikibot.output('Adding new reference claim to %s' % paintingItem)
                            newclaim.addSource(newreference)
                            
                            #creatoritem = pywikibot.ItemPage(self.repo, creatorpage)
                            print creatoritem.title()
                            print creatoritem.get()
                                
                                

                            

                        else:
                            pywikibot.output('No item found for %s' % (dcCreator, ))
                        
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

                                newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                                newreference.setTarget(europeanaUrl)
                                pywikibot.output('Adding new reference claim to %s' % paintingItem)
                                newclaim.addSource(newreference)
                    '''
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

                                    newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                                    newreference.setTarget(europeanaUrl)
                                    pywikibot.output('Adding new reference claim to %s' % paintingItem)
                                    newclaim.addSource(newreference)
                    
                    # Handle 
                    if u'P1184' not in claims:
                        handleUrl = painting['object']['proxies'][0]['dcIdentifier']['def'][0]
                        handle = handleUrl.replace(u'http://hdl.handle.net/', u'')
                        
                        newclaim = pywikibot.Claim(self.repo, u'P1184')
                        newclaim.setTarget(handle)
                        pywikibot.output('Adding handle claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference)
                    '''
                    # Europeana ID
                    if u'P727' not in claims:
                        europeanaID = painting['object']['about'].lstrip('/')

                        newclaim = pywikibot.Claim(self.repo, u'P727')
                        newclaim.setTarget(europeanaID)
                        pywikibot.output('Adding Europeana ID claim to %s' % paintingItem)
                        paintingItem.addClaim(newclaim)

                        newreference = pywikibot.Claim(self.repo, u'P854') #Add url, isReference=True
                        newreference.setTarget(europeanaUrl)
                        pywikibot.output('Adding new reference claim to %s' % paintingItem)
                        newclaim.addSource(newreference)

        """

def WikidataQueryPageGenerator(query, site=None):
    """Generate pages that result from the given WikidataQuery.

    @param query: the WikidataQuery query string.
    @param site: Site for generator results.
    @type site: L{pywikibot.site.BaseSite}

    """
    if site is None:
        site = pywikibot.Site()
    repo = site.data_repository()

    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=0)
    data = wd_query.query(wd_queryset)

    pywikibot.output(u'retrieved %d items' % data[u'status'][u'items'])
    for item in data[u'items']:
        itempage = pywikibot.ItemPage(repo, u'Q' + unicode(item))
        yield itempage       

def getPainterGenerator():
    #with open('KMSKA_import_wikidata_artists_29102015.csv', 'rb') as csvfile:
    with open('kmska_artist_input_2015-12-02.csv', 'rb') as csvfile:    
        reader = csv.DictReader(csvfile)
        foundit = True
        for row in reader:
            if row.get('creatorId')=="2621":
                foundit = True
            if foundit:
                yield row
    


def main():
    
        
    painterGen = getPainterGenerator()

    #for painter in painterGen:
    #    print painter
    
    kmskaBot = KmskaBot(painterGen)
    kmskaBot.run()
    
    

if __name__ == "__main__":
    main()
