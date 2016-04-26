#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to generate three matrice to be used in the 280 procject


"""
import json
import pywikibot
from pywikibot import pagegenerators
import urllib2
import re
import pywikibot.data.wikidataquery as wdquery
import datetime
import HTMLParser
import posixpath
from urlparse import urlparse
from urllib import urlopen
import hashlib
import io
import base64
#import upload
import tempfile
import os
#import cProfile

class Europeana280Bot:
    """
    A bot to enrich and create paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.

        """
        self.repo = pywikibot.Site().data_repository()
        configpage = pywikibot.Page(self.repo, title=u'User:Wittylama/280 config.js')
        newtext = u''
        for line in configpage.get().splitlines(True):
            if u'*' not in line:
                newtext = newtext + line
        jsondata = json.loads(newtext)
        self.eulangs = jsondata.get('configuration').get('languages')
        self.countries = jsondata.get('configuration').get('countries')

        self.officialArtworksIds = {}
        for country in self.countries:
            for itemid in self.countries[country].get('items'):
                self.officialArtworksIds[itemid]=country
        #self.totalArtworks = 300 # FIXME: Get this from the configuration
        
        #self.languages = []
        #self.eulangs = [u'de', u'en', u'fr', u'it', u'nl']
        self.artworks = []
        self.langTotals = {}
        self.langTotals['labels'] = {}
        self.langTotals['descriptions'] = {}
        self.langTotals['sitelinks'] = {}
        

        self.labelMatrix = {}
        self.descriptionMatrix = {}
        self.sitelinkMatrix = {}

    def run(self):
        '''
        Do shit
        '''
        self.artworks = self.getArtworks()
        self.languages = self.getLanguages(self.artworks)
        
        header = self.getHeader()
        textlabels = header
        textdescriptions = header
        textsitelinks = header
        eulangstats = {}
        for eulang in self.eulangs:
            eulangstats[eulang]={}
        

        for artwork in self.artworks:
            artworkid = artwork.getID(numeric=True)
            data = artwork.get()
            textlabels = textlabels + self.getRow(artworkid, data.get(u'labels'), u'labels')
            textdescriptions = textdescriptions + self.getRow(artworkid, data.get(u'descriptions'), u'descriptions')
            textsitelinks = textsitelinks + self.getRow(artworkid, data.get(u'sitelinks'), u'sitelinks')
            for eulang in self.eulangs:
                langstats = { u'label' : False,
                              u'description' : False,
                              u'sitelink' : False,
                              }
                if data.get(u'labels').get(eulang):
                    langstats[u'label']=data.get(u'labels').get(eulang)
                if data.get(u'descriptions').get(eulang):
                    langstats[u'description']=data.get(u'descriptions').get(eulang)
                if data.get(u'sitelinks').get(u'%swiki' % (eulang,)):
                    langstats[u'sitelink']=data.get(u'sitelinks').get(u'%swiki' % (eulang,))
                eulangstats[eulang][artworkid]=langstats

        #print eulangstats
        for eulang in self.eulangs:
            self.publishLangStats(eulang, eulangstats.get(eulang), eulangstats.get('en'))
        #self.publishLangStats(u'de', eulangstats.get(u'de'))
        #self.publishLangStats(u'nl', eulangstats.get(u'nl'), eulangstats.get('en'))
        #self.publishTotalStats()
                
    def publishTotalStats(self):
        '''
        FIXME: Totally broken. Fix later
        Publish the huge page with language statistics on Wikidata
        FIXME: Still a local/object variables clusterfuck
        '''
        textlabels = textlabels + self.getFooter(u'labels')
        textdescriptions = textdescriptions + self.getFooter(u'descriptions')
        textsitelinks = textsitelinks + self.getFooter(u'sitelinks')

        textclaims = self.getClaims(self.artworks)

        text = u'Overview of [[Wikidata:Europeana 280|Europeana 280]] progress. All these items have {{P|608}} -> {{Q|20980830}}\n\n'
        text = text + u'== Labels ==\n\n'
        text = text + textlabels
        text = text + u'== Descriptions ==\n\n'
        text = text + textdescriptions
        text = text + u'== Sitelinks ==\n\n'
        text = text + textsitelinks
        text = text + u'== Claims ==\n\n'
        text = text + textclaims
        
        repo = pywikibot.Site().data_repository()
        title = u'User:Multichill/Europeana 280'
        page = pywikibot.Page(repo, title=title)
        summary = u'Updating Europeana 280 statistics'
        print text
        page.put(text, summary)
        
        #print textlabels
        #print textdescriptions
        #print textsitelinks    

    def publishLangStats(self, lang, langstats, fallback):
        """
        Publish the statistics for one language
        """

        # Love to count things
        totalitems = 0
        totalcompleteitems = 0
        totallabel = 0
        totaldescription = 0
        totalsitelink = 0

        # First build the rows and count in the process
        rowtext = u''

        langname = self.eulangs.get(lang).get(u'label')

        for artworkid, artworkinfo in langstats.items():
            if u'Q%s' % (artworkid,) not in self.officialArtworksIds:
                #Skip all the others
                continue
            #if artworkid not in self.officialArtworksIds:
            #    # Some of the artworks are in the Wikidata query, but not in the list
            #    continue
            rowtext = rowtext + u'|-\n'
            totalitems = totalitems + 1
            foundall = False

            if artworkinfo.get(u'label') and artworkinfo.get(u'description') and artworkinfo.get(u'sitelink'):
                foundall = True
                #rowtext = rowtext + u'| style="background: lightgreen;" '
                totalcompleteitems = totalcompleteitems + 1

            ## Show the local label if available, otherwise fallback
            #if artworkinfo.get(u'label'):
            #    rowtext = rowtext + u'| [[Q%s|{{label|Q%s|%s}}]]\n' % (artworkid, artworkid, lang, artworkid,)
            #else:
            #    rowtext = rowtext + u'| [[Q%s|{{label|Q%s|%s}}]]\n' % (artworkid, artworkid, lang, artworkid,)
            #    #rowtext = rowtext + u'| {{Q|%s}}\n' % (artworkid,)
                
            # Insert country here
            if foundall:
                rowtext = rowtext + u'| style="background: lightgreen;" data-sort-value="1"'
            else:
                rowtext = rowtext + u'| '
            rowtext = rowtext + self.getFlag(u'Q%s' % (artworkid,))

            # Wikipedia article
            #if foundall:
            #    rowtext = rowtext + u'| style="background: darkgreen;" data-sort-value="1"'
            #    totalsitelink = totalsitelink + 1
            if artworkinfo.get(u'sitelink'):
                totalsitelink = totalsitelink + 1
                rowtext = rowtext + u'| style="background: lightgreen;" data-sort-value="1"'
                #rowtext = rowtext + u'|[[File:Yes_check.svg|25px|link=W:%s:%s|%s]]\n' % (lang, artworkinfo.get(u'sitelink'), artworkinfo.get(u'sitelink'),)
            #else:
            #    #rowtext = rowtext + u'| [[File:Noun project - crayon.svg|25px|link=]]\n' # FIXME: Add correct link
            
            rowtext = rowtext + u'| %s \n' % (self.getArticleLink(artworkid, lang, artworkinfo),)
            
            # Wikidata label
            if artworkinfo.get(u'label'):
                totallabel = totallabel + 1
                rowtext = rowtext + u'| style="background: lightgreen;" data-sort-value="1"'
                rowtext = rowtext + u'| [[Q%s|%s]]\n' % (artworkid, artworkinfo.get(u'label'),)  # FIXME: Hard code label if known
            else:
                #rowtext = rowtext + u'| style="background: yellow;"'
                #rowtext = rowtext + u'| <small>[<i>[[Q%s|{{label|Q%s|%s}}]]</i>]</small>\n' % (artworkid, artworkid, lang,)
                fallbacklabel = u'no label'
                if fallback.get(artworkid).get('label'):
                    fallbacklabel= fallback.get(artworkid).get('label')
                rowtext = rowtext + u'| <small>[<i>[[Q%s|%s]]</i>]</small>\n' % (artworkid, fallbacklabel,)


            # Wikidata description
            if artworkinfo.get(u'description'):
                totaldescription = totaldescription + 1
                rowtext = rowtext + u'| style="background: lightgreen;" data-sort-value="1"'
                rowtext = rowtext + u'| %s\n' % (artworkinfo.get(u'description'),) # FIXME: Hard code description if known
            else:
                fallbackdescription = u'no description'
                if fallback.get(artworkid).get('description'):
                    fallbackdescription = fallback.get(artworkid).get('description')
                #rowtext = rowtext + u'| <small>[<i>{{Autodescription|Q%s|%s}}</i>]</small>\n' % (artworkid, lang,)
                rowtext = rowtext + u'| <small>[<i>%s</i>]</small>\n' % (fallbackdescription,)

        # We got the rows and counted along the way. Build the page text

        text = u''
        text = text + u'Overview of [[Wikidata:Europeana Art History Challenge|Europeana Art History Challenge]] progress in %s. \n' % (langname,)
        text = text + u'Total number of \'\'completed\'\' artworks for %s: \'\'\'%s\'\'\'. \n' % (self.eulangs.get(lang).get(u'label'), totalcompleteitems,)
        text = text + u'The target number for articles/labels/descriptions is \'\'\'%s\'\'\'\n' % (len(self.officialArtworksIds),)
        text = text + u'{| class="wikitable sortable"\n'
        text = text + u'|-\n'
        text = text + u'! Country\n'
        text = text + u'! Wikipedia\nArticle\n'
        text = text + u'! Wikidata\nLabel\n'
        text = text + u'! Wikidata\nDescription\n'

        # Second header ine
        text = text + u'|- \n'
        #if totalitems==totalcompleteitems:
        #    text = text + u'| style="background: lightgreen;" '
        text = text + u'! %s\n' % (len(self.countries), )

        # Doesn't work, sortable breaks
        #if totalsitelink==totalitems:
        #    text = text + u'! <font color=darkgreen>%s</font>\n' % (totalsitelink,) # FIXME: Include baseline
        #else:
        text = text + u'! %s\n' % (totalsitelink,) # FIXME: Include baseline
        
        #if totallabel==totalitems:
        #    text = text + u'! <font color=darkgreen>%s</font>\n' % (totallabel,) # FIXME: Include baseline
        #else:
        text = text + u'! %s\n' % (totallabel,) # FIXME: Include baseline

        #if totaldescription==totalitems:
        #    text = text + u'! <font color=darkgreen>%s</font>\n' % (totaldescription,) # FIXME: Include baseline
        #else:
        text = text + u'! %s\n' % (totaldescription,) # FIXME: Include baseline
  
        #text = text + u'!\n'
        text = text + rowtext
        text = text + u'|}\n\n'
        text = text + u'\n<noinclude>[[Category:Europeana Art History Challenge languages|%s]]</noinclude>' % (langname,)
        #text = text + u'Total number of completed items: %s' % (totalcompleteitems,)

        # FIXME: Add category
        
        repo = pywikibot.Site().data_repository()
        title = u'Wikidata:Europeana Art History Challenge/%s' % (langname,)
        page = pywikibot.Page(repo, title=title)
        summary = u'Updating statistics: %s labels, %s descriptions, %s translations %s completed items' % (totallabel,
                                                                                                         totaldescription,
                                                                                                         totalsitelink,
                                                                                                         totalcompleteitems,)
        page.put(text, summary)
            
    def getFlag(self, itemid):
        """Get the flag as wikitext for an item"""
        if self.officialArtworksIds.get(itemid):
            country = self.officialArtworksIds.get(itemid)
            if self.countries.get(country):
                label = self.countries.get(country).get('label')
                flag = self.countries.get(country).get('flag')
                return u' data-sort-value="%s" | [[%s|link=Wikidata:Europeana Art History Challenge/%s|30x30px|%s]]\n' % (label, flag, label, label)

        return u'[[File:Pirate Flag.svg|link=Wikidata:Europeana Art History Challenge|30x30px|Arrr matey, this needs to be fixed]]\n'

    def getArticleLink(self, itemid, destlang, artworkinfo):
        """
        Make this link in wikitext for itemid in the destination language
        * If it exists, just check it
        * If it doesn't exist 
        """
        if artworkinfo.get(u'sitelink'):
            return u'[[File:Yes_check.svg|25px|link=W:%s:%s|%s]]\n' % (destlang, artworkinfo.get(u'sitelink'), artworkinfo.get(u'sitelink'),)

        return u'[[File:Noun project - crayon.svg|25px|link=//www.wikidata.org/w/index.php?title=Wikidata:Europeana_Art_History_Challenge/Content_Translation&withJS=MediaWiki:EuropeanaContentTranslation.js&itemid=Q%s&destlang=%s|Translate]]' % (itemid, destlang) 

                
    def getLanguages(self, artworks):
        '''
        Get a list of languages to work on
        '''
        result = []
        for artwork in artworks:
            result.extend(artwork.get().get('labels').keys())
            #result.extend(artwork.get().get('descriptions').keys())
            #result.extend(artwork.get().get('aliases').keys())
        result = sorted(set(result))
            
        return result


    
    def getArtworks(self):
        '''
        Get the artworks to work on sorted by the Q id (from low to high)
        '''
        result = []
        artdict = {}
        query=u'CLAIM[608:20980830]'
        generator = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataItemGenerator(WikidataQueryItemPageGenerator(query)))

        for artwork in generator:
            if artwork.title() in self.officialArtworksIds:
                artdict[artwork.getID(numeric=True)] = artwork

        for key in sorted(artdict.keys()):
            result.append(artdict[key])

        return result

    def getHeader(self):
        '''
        Get a table header
        '''
        result = u'{| class="wikitable sortable"\n! \n'
        for language in self.languages:
            result = result + u'! %s\n' % (language,)
        result = result + u'! total\n'
        return result

    def getRow(self, artworkid, tabledata, tableType):
        '''
        Get a row for a table
        '''
        result = u'|-\n| {{Q|%s}} ' % (artworkid,)
        total = 0
        #tabledata = artwork.get().get(tableType)
        for language in self.languages:
            if tableType==u'sitelinks':
                locallang = u'%swiki' % (language,)
            else:
                locallang = language
            if locallang in tabledata: # FIXME: Bottleneck, cache this
                result = result + u'|| 1 '
                total = total + 1
                if language not in self.langTotals.get(tableType):
                    self.langTotals.get(tableType)[language] = 1
                else:
                    self.langTotals[tableType][language] = self.langTotals[tableType][language] + 1
            else:
                result = result + u'|| 0 '
        result = result + u'|| %s \n' % (total,)
        return result

    def getFooter(self, tableType):
        '''
        Generate the footer of a table
        '''
        result = u'|- class="sortbottom"\n| '
        total = 0
        for language in self.languages:
            if language in self.langTotals.get(tableType):
                result = result + u'|| %s ' % self.langTotals.get(tableType).get(language)
                total = total + self.langTotals.get(tableType).get(language)
            else:
                result = result + u'|| 0 '
        result = result + u'|| %s \n|}\n' % (total,)
        return result

    def getClaims(self, artworks):
        '''
        Return a matrix of most used claims
        '''
        pids = []
        counts = {}
        countstotals = {}
        for artwork in artworks:
            counts[artwork.getID(numeric=True)]={}
            artworktotal=0
            for claimid, claims in artwork.get().get('claims').iteritems():
                counts[artwork.getID(numeric=True)][claimid] = len(claims)
                artworktotal = artworktotal + len(claims)
    
                if countstotals.get(claimid):
                    countstotals[claimid] = countstotals[claimid] + len(claims)
                else:
                    countstotals[claimid] = len(claims)
            counts[artwork.getID(numeric=True)]['total'] = artworktotal

        pids = sorted(countstotals, key=lambda k: countstotals[k], reverse=True)

        result = u'{| class="wikitable sortable"\n! \n'
        for pid in pids:
            result = result + u'! {{P|%s}}\n' % (pid.replace(u'P', u''),)
        result = result + u'! total\n'

        #for qid, claimcounts in counts.iteritems():
        for qid in sorted(counts.keys()):
            result = result + u'|-\n| {{Q|%s}} ' % (qid,)
            for pid in pids:
                if pid in counts[qid]:
                    result = result + u'|| %s ' % (counts[qid][pid],)
                else:
                    result = result + u'|| 0 '
            result = result + u'|| %s \n' % (counts[qid].get('total'),)

        result = result + u'|- class="sortbottom"\n| '
        grandtotal = 0
        for pid in pids:
            result = result + u'|| %s ' % countstotals.get(pid)
            grandtotal = grandtotal + countstotals.get(pid)

        result = result + u'|| %s \n|}\n' % (grandtotal,)

        return result


def WikidataQueryItemPageGenerator(query, site=None):
    """Generate pages that result from the given WikidataQuery.

    @param query: the WikidataQuery query string.

    """
    if site is None:
        site = pywikibot.Site()
    repo = site.data_repository()

    wd_queryset = wdquery.QuerySet(query)

    wd_query = wdquery.WikidataQuery(cacheMaxAge=0)
    data = wd_query.query(wd_queryset)

    pywikibot.output(u'retrieved %d items' % data[u'status'][u'items'])
    for item in data[u'items']:
        yield pywikibot.ItemPage(repo, u'Q' + unicode(item))

def main():
    europeana280Bot = Europeana280Bot()
    europeana280Bot.run()

if __name__ == "__main__":
    main()
    #cProfile.run('main()')
