#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to show recent additions of paintings to RKDimages for easy matching

"""
import pywikibot
import requests
import pywikibot.data.sparql
import re

class RecentRKDimagesBot:
    def __init__(self):
        """
        Build all the lookup tables to work on
        """
        self.repo = pywikibot.Site().data_repository()
        self.highestrkdimage = None
        self.lowestrkdimage = 0
        self.maxlength = 500
        self.currentrkdimages = self.rkdImagesOnWikidata()
        self.currentcollections = self.rkdImagesCollectionsOnWikidata()
        self.currentrkdartists = self.rkdArtistsOnWikidata()
        self.rkdidgenerator = self.getRKDidgenerator()

    def rkdImagesOnWikidata(self):
        '''
        Just return all the RKD images as a dict
        :return: Dict
        '''
        result = {}
        query = u'SELECT ?item ?id WHERE { ?item wdt:P350 ?id  } ORDER BY DESC (xsd:integer(?id))'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            if not self.highestrkdimage:
                self.highestrkdimage = int(resultitem.get('id'))
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[int(resultitem.get('id'))] = qid
        return result

    def rkdImagesCollectionsOnWikidata(self):
        '''
        Just return all the collections of RKD images as a dict
        :return: Dict
        '''
        result = {}
        query = u"""SELECT DISTINCT ?item ?id WHERE {
  ?artwork wdt:P350 ?id .
  ?artwork wdt:P195 ?item .
  FILTER NOT EXISTS { ?item wdt:P361 ?realcollection .
          ?artwork wdt:P195 ?realcollection }
}"""

        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[int(resultitem.get('id'))] = qid
        return result

    def rkdArtistsOnWikidata(self):
        '''
        Just return all the RKD artists as a dict
        :return: Dict
        '''
        result = {}
        query = u'SELECT ?item ?id WHERE { ?item wdt:P650 ?id }'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[resultitem.get('id')] = qid
        return result

    def getRKDidgenerator(self):
        for i in range(self.highestrkdimage, 1, -1):
            print i
            if i not in self.currentrkdimages:

                yield i

    def run(self):
        foundimages = []
        for rkdimageid in self.rkdidgenerator:
            rkdinfo = self.getRkdInfo(rkdimageid)
            if rkdinfo:
                print rkdinfo
                foundimages.append(rkdinfo)
                if len(foundimages) >= self.maxlength:
                    self.lowestrkdimage = rkdinfo.get('id')
                    break
        print foundimages
        print self.lowestrkdimage
        self.outputReport(foundimages)

    def getRkdInfo(self, rkdimageid):
        """
        Get the RKDinfo, but only if it's a painting
        :return:
        """
        imageinfo = {}
        baseurl = u'https://api.rkd.nl/api/record/images/%s?format=json&language=nl'
        print baseurl % (rkdimageid,)
        rkdpage = requests.get(baseurl % (rkdimageid,), verify=False)
        # Try and return
        searchJson = rkdpage.json()
        if not searchJson.get('response'):
            return None
        rkdimage = searchJson.get('response').get('docs')[0]

        if not rkdimage.get('objectcategorie')[0] == u'schilderij':
            return None

        imageinfo[u'id'] = rkdimage.get(u'priref')
        if rkdimage.get(u'benaming_kunstwerk') and rkdimage.get(u'benaming_kunstwerk')[0]:
            imageinfo[u'title_nl'] = rkdimage.get(u'benaming_kunstwerk')[0]
        else:
            imageinfo[u'title_nl'] = u'(geen titel)'
        imageinfo[u'title_en'] = rkdimage.get(u'titel_engels')
        imageinfo[u'creator'] = rkdimage.get(u'kunstenaar')
        if rkdimage.get(u'toeschrijving'):
            imageinfo[u'rkdartistid'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_linkref')
            # Overwrite creator with something more readable
            imageinfo[u'creator'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_inverted')

        imageinfo[u'qid'] = None
        imageinfo[u'url'] = u'https://rkd.nl/explore/images/%s'  % (rkdimageid,)

        imageinfo[u'artistqid'] = None
        print imageinfo.get(u'rkdartistid')
        if imageinfo.get(u'rkdartistid') in self.currentrkdartists:
            imageinfo[u'artistqid'] = self.currentrkdartists.get(imageinfo.get(u'rkdartistid'))
            print imageinfo[u'artistqid']

        imageinfo[u'collectienaam'] = None
        imageinfo[u'invnum'] = None
        #This will just overwrite the collection with the last one
        if rkdimage.get(u'collectie'):
            for collectie in rkdimage.get(u'collectie'):
                print collectie
                #First we have to extract the collection name. This can be a string or a dict
                collectienaam = None
                if collectie.get('collectienaam'):

                    print collectie.get('collectienaam')
                    if isinstance(collectie.get('collectienaam'), unicode):
                        collectienaam = collectie.get('collectienaam')
                    elif collectie.get('collectienaam')[0].get('collectienaam'):
                        collectienaam = collectie.get('collectienaam')[0].get('collectienaam')
                    imageinfo[u'invnum'] = None
                    if collectie.get('inventarisnummer'):
                        imageinfo[u'invnum'] = collectie.get('inventarisnummer')



            imageinfo[u'collectienaam'] = collectienaam

        if imageinfo.get(u'collectienaam'):
            imageinfo[u'collectionqid'] = self.getCollection(imageinfo.get(u'collectienaam'))

            """
            # And is it the one we're looking for?
            if collectienaam == collection:
                invnum = collectie.get('inventarisnummer')
                if invnum:
                    for (regex, replace) in replacements:
                        invnum = re.sub(regex, replace, invnum)
                imageinfo[u'invnum'] = invnum
                imageinfo[u'startime'] = collectie.get('begindatum_in_collectie')
                if invnum in invnumbers:
                    pywikibot.output(u'Found a Wikidata id!')
                    imageinfo[u'qid'] = invnumbers.get(invnum).get('qid')
                    if invnumbers.get(invnum).get('url'):
                        imageinfo[u'url'] = invnumbers.get(invnum).get('url')
                    # Break out of the loop, otherwise the inventory might get overwritten
                    break
            """

        return imageinfo

    def getCollection(self, collectienaam):
        """
        Try to find a Qid for a collection based on it's name
        :param collectienaam:
        :return:
        """
        start = 0
        rows = 50
        basesearchurl = u'https://api.rkd.nl/api/search/images?filters[collectienaam]=%s&filters[objectcategorie][]=schilderij&format=json&start=%s&rows=%s'
        #while True:
        searchUrl = basesearchurl % (collectienaam.replace(u' ', u'+'), start, rows)
        print searchUrl
        searchPage = requests.get(searchUrl, verify=False)
        searchJson = searchPage.json()
        numfound = searchJson.get('response').get('numFound')
        #print numfound
        #if not start < numfound:
        #   return
        #start = start + rows

        foundcollections = {}
        totalfound = 0

        for rkdimage in  searchJson.get('response').get('docs'):
            if rkdimage.get(u'priref') in self.currentcollections:
                collection = self.currentcollections.get(rkdimage.get(u'priref'))
                if collection not in foundcollections:
                    foundcollections[collection] = 0
                foundcollections[collection]+=1

        print foundcollections

        if len(foundcollections.keys())==1:
            collectionqid = foundcollections.keys()[0]
            if foundcollections.get(collectionqid) > 1:
                return collectionqid
        elif len(foundcollections.keys())==2:
            if foundcollections.keys()[0] < foundcollections.keys()[1]:
                collectionqid = foundcollections.keys()[1]
            else:
                collectionqid = foundcollections.keys()[0]
            if foundcollections.get(collectionqid) > 2:
                return collectionqid
        return None


    def outputReport(self, foundimages):
        """

        :param foundimages:
        :return:
        """
        text = u'This is an overview of recently added [https://rkd.nl/en/explore/images#filters%5Bobjectcategorie%5D%5B%5D=painting&start=0 paintings in RKDimages].\n'
        text += u'This page lists %s suggestions from %s to %s\n\n' % (self.maxlength,
                                                                   self.highestrkdimage,
                                                                   self.lowestrkdimage)
        text += u'{| class="wikitable sortable"\n'
        text += u'|-\n! RKDimage !! Title !! Creator !! Collection !! Query\n'
        for foundimage in foundimages:
            text += u'|-\n'
            text += u'| [%(url)s %(id)s]\n' % foundimage
            text += u'| %(title_nl)s / %(title_en)s\n' % foundimage
            if foundimage.get(u'artistqid'):
                text += u'| {{Q|%(artistqid)s}} <small>([https://rkd.nl/explore/artists/%(rkdartistid)s %(creator)s])</small>\n' % foundimage
            else:
                text += u'| [https://rkd.nl/explore/artists/%(rkdartistid)s %(creator)s]\n' % foundimage

            if foundimage.get(u'collectionqid'):
                text += u'| {{Q|%(collectionqid)s}} <small>%(collectienaam)s</small>' % foundimage
            else:
                text += u'| %(collectienaam)s' % foundimage
            if foundimage.get('invnum'):
                text += u'  (%(invnum)s)\n' % foundimage
            else:
                text += u'\n'
            if foundimage.get(u'artistqid') and foundimage.get(u'collectionqid'):
                text += u'''| [https://query.wikidata.org/#{{urlencode:SELECT ?item ?itemLabel ?inv WHERE {
  ?item wdt:P195 wd:%(collectionqid)s .
  ?item wdt:P170 wd:%(artistqid)s .
  ?item wdt:P31 wd:Q3305213 .
  OPTIONAL { ?item wdt:P217 ?inv } .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]" }
  }|PATH}} query]\n''' % foundimage
            else:
                text += u'| \n'


        text += u'|}\n'
        text += u'\n[[Category:WikiProject sum of all paintings RKD to match| Recent additions]]'
        pageTitle = u'Wikidata:WikiProject sum of all paintings/RKD to match/Recent additions'

        page = pywikibot.Page(self.repo, title=pageTitle)
        summary = u'Updating recent RKDimages suggestionswith %s suggestions from %s to %s' % (self.maxlength,
                                                                                               self.highestrkdimage,
                                                                                               self.lowestrkdimage)
        page.put(text, summary)



def paintingsInvOnWikidata(collectionid):
    '''
    Just return all the RKD images as a dict
    :return: Dict
    '''
    result = {}
    # Need to use the long version here to get all ranks
    query = u"""SELECT DISTINCT ?item ?id ?url ?rkdimageid ?rkdartistid WHERE {
    ?item wdt:P31 wd:Q3305213 .
    { ?item p:P195 ?colstatement .
    ?colstatement ps:P195 wd:%s .
    ?item p:P217 ?invstatement .
    ?invstatement ps:P217 ?id .
    ?invstatement pq:P195 wd:%s . } UNION
    { wd:%s wdt:P361 ?collection .
    ?item p:P276 ?locationstatement .
    ?locationstatement ps:P276 wd:%s  .
    ?item p:P217 ?invstatement .
    ?invstatement ps:P217 ?id .
    ?invstatement pq:P195 ?collection . }
    OPTIONAL { ?item wdt:P973 ?url } .
    OPTIONAL { ?item wdt:P350 ?rkdimageid } .
    OPTIONAL { ?item wdt:P170 ?creator .
    ?creator wdt:P650 ?rkdartistid }
    } LIMIT 10000007""" % (collectionid, collectionid,collectionid,collectionid )
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = { u'qid' : qid }
        if resultitem.get('url'):
            result[resultitem.get('id')]['url'] = resultitem.get('url')
        if resultitem.get('rkdimageid'):
            result[resultitem.get('id')]['rkdimageid'] = resultitem.get('rkdimageid')
        if resultitem.get('rkdartistid'):
            result[resultitem.get('id')]['rkdartistid'] = resultitem.get('rkdartistid')

    return result

def paintingsArtistOnWikidata(artistid):
    '''
    Just return all the RKD images as a dict
    :return: Dict
    '''
    result = {}
    # Need to use the long version here to get all ranks
    query = u"""SELECT DISTINCT ?item ?year ?collection ?inv WHERE {
    ?item wdt:P31 wd:Q3305213 .
    ?item wdt:P170 wd:%s .
    MINUS { ?item wdt:P350 [] } .
    OPTIONAL { ?item wdt:P571 ?inception . BIND(year(?inception) as ?year) } .
    OPTIONAL { ?item wdt:P195 ?collection } .
    } ORDER BY ?item LIMIT 10000007""" % (artistid,  )
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)
    #print query
    #print queryresult

    previousqid = None

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')

        paintingitem = { u'qid' : qid,
                         u'inception' : u'',
                         u'collection' : u'',
                         }
        if resultitem.get('year'):
            paintingitem['inception'] = resultitem.get('year')
        if resultitem.get('collection'):
            paintingitem['collection'] = resultitem.get('collection').replace(u'http://www.wikidata.org/entity/', u'')

        #result[qid] = { u'qid' : qid }
        #if resultitem.get('url'):
        #    result[resultitem.get('id')]['url'] = resultitem.get('url')
        #if resultitem.get('rkdimageid'):
        #    result[resultitem.get('id')]['rkdimageid'] = resultitem.get('rkdimageid')
        #if resultitem.get('rkdartistid'):
        #    result[resultitem.get('id')]['rkdartistid'] = resultitem.get('rkdartistid')
        yield paintingitem

    #return result


def rkdImagesGenerator(currentimages, invnumbers, collection, replacements):
    '''

    :param currentimages:
    :param collection:
    :return:
    '''
    # https://api.rkd.nl/api/search/images?filters[collectienaam]=Rijksmuseum&format=json&start=100&rows=50
    start = 0
    rows = 50
    basesearchurl = u'https://api.rkd.nl/api/search/images?filters[collectienaam]=%s&filters[objectcategorie][]=schilderij&format=json&start=%s&rows=%s'
    while True:
        searchUrl = basesearchurl % (collection.replace(u' ', u'+'), start, rows)
        #print searchUrl
        searchPage = requests.get(searchUrl, verify=False)
        searchJson = searchPage.json()
        numfound = searchJson.get('response').get('numFound')
        #print numfound
        if not start < numfound:
            return
        start = start + rows
        for rkdimage in  searchJson.get('response').get('docs'):
            if rkdimage.get(u'priref') in currentimages:
                pywikibot.output(u'RKDimage id %s found on %s' % (rkdimage.get(u'priref'),
                                                                  currentimages.get(rkdimage.get(u'priref'))))
            else:
                imageinfo = {}
                imageinfo[u'id'] = rkdimage.get(u'priref')
                if rkdimage.get(u'benaming_kunstwerk') and rkdimage.get(u'benaming_kunstwerk')[0]: 
                    imageinfo[u'title_nl'] = rkdimage.get(u'benaming_kunstwerk')[0]
                else:
                    imageinfo[u'title_nl'] = u'(geen titel)'
                imageinfo[u'title_en'] = rkdimage.get(u'titel_engels')
                imageinfo[u'creator'] = rkdimage.get(u'kunstenaar')
                if rkdimage.get(u'toeschrijving'):
                    imageinfo[u'rkdartistid'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_linkref')
                    # Overwrite creator with something more readable
                    imageinfo[u'creator'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_inverted')
                imageinfo[u'invnum'] = None
                imageinfo[u'qid'] = None
                imageinfo[u'url'] = None
                #print rkdimage.get(u'collectie')
                for collectie in rkdimage.get(u'collectie'):
                    #First we have to extract the collection name. This can be a string or a dict
                    collectienaam = None
                    if collectie.get('collectienaam'):
                        if collectie.get('collectienaam')[0]:
                            if collectie.get('collectienaam')[0].get('collectienaam'):
                                collectienaam = collectie.get('collectienaam')[0].get('collectienaam')
                        else:
                            collectienaam = collectie.get('collectienaam')
                    # And is it the one we're looking for?
                    if collectienaam == collection:
                        invnum = collectie.get('inventarisnummer')
                        if invnum:
                            for (regex, replace) in replacements:
                                invnum = re.sub(regex, replace, invnum)
                        imageinfo[u'invnum'] = invnum
                        imageinfo[u'startime'] = collectie.get('begindatum_in_collectie')
                        if invnum in invnumbers:
                            pywikibot.output(u'Found a Wikidata id!')
                            imageinfo[u'qid'] = invnumbers.get(invnum).get('qid')
                            if invnumbers.get(invnum).get('url'):
                                imageinfo[u'url'] = invnumbers.get(invnum).get('url')
                            # Break out of the loop, otherwise the inventory might get overwritten
                            break

                yield imageinfo

def rkdImagesArtistGenerator(aristname):
    '''

    :param currentimages:
    :param collection:
    :return:
    '''
    # https://api.rkd.nl/api/search/images?filters[collectienaam]=Rijksmuseum&format=json&start=100&rows=50
    start = 0
    rows = 50
    basesearchurl = u'https://api.rkd.nl/api/search/images?filters[naam]=%s&filters[objectcategorie][]=schilderij&format=json&start=%s&rows=%s'
    while True:
        searchUrl = basesearchurl % (aristname.replace(u' ', u'+'), start, rows)
        #print searchUrl
        searchPage = requests.get(searchUrl, verify=False)
        searchJson = searchPage.json()
        #print searchJson
        numfound = searchJson.get('response').get('numFound')
        #print numfound
        if not start < numfound:
            return
        start = start + rows
        for rkdimage in  searchJson.get('response').get('docs'):
            imageinfo = {}
            imageinfo[u'id'] = rkdimage.get(u'priref')
            imageinfo[u'id'] = rkdimage.get(u'priref')
            if rkdimage.get(u'benaming_kunstwerk') and rkdimage.get(u'benaming_kunstwerk')[0]:
                imageinfo[u'title_nl'] = rkdimage.get(u'benaming_kunstwerk')[0]
            else:
                imageinfo[u'title_nl'] = u'(geen titel)'
            imageinfo[u'title_en'] = rkdimage.get(u'titel_engels')
            if imageinfo.get(u'title_nl')==imageinfo.get(u'title_en'):
                imageinfo[u'title'] = imageinfo.get(u'title_nl')
            else:
                imageinfo[u'title'] = u'%s / %s' % (imageinfo.get(u'title_nl'), imageinfo.get(u'title_en'))
            if rkdimage.get(u'datering'):
                datering = rkdimage.get(u'datering')[0]
                if datering.startswith(u'ca.'):
                    imageinfo[u'inception'] = datering[3:] + u' ' + datering[:3]
                else:
                    imageinfo[u'inception'] = datering
            else:
                imageinfo[u'inception'] = u''

            # Inception and collection
            imageinfo[u'creator'] = rkdimage.get(u'kunstenaar')
            #if rkdimage.get(u'toeschrijving'):
            #        imageinfo[u'rkdartistid'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_linkref')
            #        # Overwrite creator with something more readable
            #        imageinfo[u'creator'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_inverted')
            collection = u''
            if len(rkdimage.get(u'collectie')) > 0 :
                for collectie in rkdimage.get(u'collectie'):
                    if collectie.get('collectienaam'):
                        if isinstance(collectie.get('collectienaam'), basestring):
                            # For some reason I sometimes get a list.
                            collection = collection + collectie.get('collectienaam')
                        else:
                            collection = collection + collectie.get('collectienaam')[0].get('collectienaam')
                        if collectie.get('inventarisnummer') or collectie.get('begindatum_in_collectie'):
                            collection = collection + u' (%s, %s)' % (collectie.get('inventarisnummer'),
                                                                      collectie.get('begindatum_in_collectie'),)
                        collection = collection + u'<BR/>\n'
            imageinfo[u'collection'] = collection
            yield imageinfo

def processCollection(collectionid, collectienaam, replacements, pageTitle, autoadd):


    currentimages = rkdImagesOnWikidata(collectionid)
    allimages = rkdImagesOnWikidata()
    invnumbers = paintingsInvOnWikidata(collectionid)
    #print invnumbers

    #print currentimages
    gen = rkdImagesGenerator(currentimages, invnumbers, collectienaam, replacements)

    # Page consists of several sections
    autoaddedtext = u'' # List of auto added links in this run so user can review
    nextaddedtext = u'' # List of links that will be auto added on the next run\
    suggestionstext = u'' # List of suggestions that not completely add up
    failedtext = u'' # List of links that failed, but might have some suggestions
    text = u'' # Everything combined in the end

    text = text + u'This pages gives an overview of [https://rkd.nl/en/explore/images#filters%%5Bcollectienaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s paintings in RKDimages] ' % (collectienaam.replace(u' ', u'%20'), collectienaam, )
    text = text + u'that are not in use on a painting item here on Wikidata in the {{Q|%s}} collection.\n' % (collectionid, )
    text = text + u'This pages is split up in several sections.\n__TOC__'

    autoaddedtext = autoaddedtext + u'\n== Auto added links ==\n'
    autoaddedtext = autoaddedtext + u'A maxiumum of %s links have been added in the previous bot run. Please review.\n' % (autoadd,)
    autoaddedtext = autoaddedtext + u'If you find an incorrect link, you have two options:\n'
    autoaddedtext = autoaddedtext + u'# Move it to the right painting in the same collection.\n'
    autoaddedtext = autoaddedtext + u'# Set the rank to deprecated so the bot won\'t add it again.\n'
    autoaddedtext = autoaddedtext + u'-----\n\n'

    nextaddedtext = nextaddedtext + u'\n== Links to add on next run ==\n'
    nextaddedtext = nextaddedtext + u'On this run the bot added a maximum of %s links. Next up are these links. \n' % (autoadd,)
    nextaddedtext = nextaddedtext + u'-----\n\n'

    suggestionstext = suggestionstext + u'== Suggestions to add ==\n'
    suggestionstext = suggestionstext + u'These suggestions are based on same collection and inventory number, but not a link to the same RKDartist.\n'
    suggestionstext = suggestionstext + u'This can have several reasons: \n'
    suggestionstext = suggestionstext + u'# It\'s a (completely) different painting. Just skip it.\n'
    suggestionstext = suggestionstext + u'# Same painting, but Wikidata and RKD don\'t agree on the creator. Just add the link. You could check and maybe correct the creator.\n'
    suggestionstext = suggestionstext + u'# Same painting, Wikidata and RKD agree on the creator, but the creator doesn\'t have the {{P|P650}} link. Just add the link. You can also add the missing RKDartists link to the creator.\n'
    suggestionstext = suggestionstext + u'-----\n\n'

    failedtext = failedtext + u'\n== No matches found ==\n'
    failedtext = failedtext + u'For the following links, no direct matches were found. This is the puzzle part.\n'
    failedtext = failedtext + u'# If the id is used on an item not in {{Q|%s}}, it will be mentioned here.\n' % (collectionid, )
    failedtext = failedtext + u'# If painter has other works in {{Q|%s}}, these will be suggested.\n' % (collectionid, )
    failedtext = failedtext + u'-----\n\n'

    #text = u'<big><big><big>This list contains quite a few mistakes. These will probably fill up at the top. Please check every suggestion before approving</big></big></big>\n\n'
    #text = text + u'This list was generated with a bot. If I was confident enough about the suggestions I would have just have the bot add them. '
    #text = text + u'Feel free to do any modifications in this page, but a bot will come along and overwrite this page every once in a while.\n\n'
    addtext = u''

    totalimages = 0
    totalautoadded = 0
    totalnextadd = 0
    totalsuggestions = 0
    totalfailedinuse = 0
    totailfailedoptions= 0
    totalfailedelse = 0

    i = 0
    addcluster = 10

    addlink = u'** [https://tools.wmflabs.org/wikidata-todo/quick_statements.php?list={{subst:urlencode:%s}} Add the previous %s]\n'

    imagedict = {}
    for rkdimageid in gen:
        if not rkdimageid.get(u'invnum') in imagedict:
            imagedict[rkdimageid.get(u'invnum')] = []
        imagedict[rkdimageid.get(u'invnum')].append(rkdimageid)

    for invnum in sorted(imagedict.keys()):
        for rkdimageid in imagedict.get(invnum):
            totalimages = totalimages + 1
            # We found a match, just not sure how solid it is
            if rkdimageid.get(u'qid'):
                # We found the same inventory number. If the creator matches too than I'm confident enough to add it by bot
                if invnumbers[invnum].get(u'rkdartistid') and \
                                invnumbers[invnum].get(u'rkdartistid')==rkdimageid.get(u'rkdartistid') and \
                        rkdimageid.get(u'qid') not in allimages.values():
                    if autoadd > 0:
                        summary = u'Based on [[%s]]' % (collectionid,)
                        summary = summary + u' / %(invnum)s / https://rkd.nl/explore/artists/%(rkdartistid)s (name: %(creator)s)' % rkdimageid
                        #summary = u'Based on [[%s]] / %s / [https://rkd.nl/explore/artists/%s %s]' % (collectionid,
                        #                                                                            rkdimageid.get(u'invnum'),
                        #                                                                            rkdimageid.get(u'rkdartistid'),
                        #                                                                            rkdimageid.get(u'creator'))
                        addsuccess = addRkdimagesLink(rkdimageid.get('qid'), rkdimageid.get('id'), summary)
                        if addsuccess:
                            autoaddedtext = autoaddedtext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                            autoadd = autoadd - 1
                            totalautoadded = totalautoadded + 1
                        else:
                            suggestionstext = suggestionstext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid

                            addtext = addtext + u'%(qid)s\tP350\t"%(id)s"\n' % rkdimageid
                            i = i + 1
                            totalsuggestions = totalsuggestions + 1
                            if not i % addcluster:
                                suggestionstext = suggestionstext + addlink % (addtext, addcluster)
                                addtext = u''

                    else:
                        nextaddedtext = nextaddedtext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                        totalnextadd = totalnextadd + 1
                # Something is not adding up, add it to the suggestions list
                else:
                    suggestionstext = suggestionstext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid

                    addtext = addtext + u'%(qid)s\tP350\t"%(id)s"\n' % rkdimageid
                    i = i + 1
                    totalsuggestions = totalsuggestions + 1
                    if not i % addcluster:
                        suggestionstext = suggestionstext + addlink % (addtext, addcluster)
                        addtext = u''

                #if i > 5000:
                #    break
            # Failed to find a Qid to suggest
            else:
                failedtext = failedtext + u'* [https://rkd.nl/explore/images/%(id)s %(id)s] -  %(invnum)s - %(title_nl)s - %(title_en)s' % rkdimageid
                # The id is used on some other Wikidata item.
                if rkdimageid['id'] in allimages.keys():
                    failedtext = failedtext + u' -> Id already in use on {{Q|%s}}\n' % allimages[rkdimageid['id']]
                    totalfailedinuse = totalfailedinuse + 1

                # Anonymous (rkd id 1984) will make the list explode
                elif not rkdimageid.get(u'rkdartistid')==u'1984':
                    firstsuggestion = True
                    for inv, invitem in invnumbers.items():
                        if invitem.get(u'rkdartistid') and not invitem.get(u'rkdimageid') \
                                and invitem.get(u'rkdartistid')==rkdimageid.get(u'rkdartistid'):
                            if firstsuggestion:
                                failedtext = failedtext + u' -> Paintings by \'\'%s\'\' that still need a link: ' % (rkdimageid.get(u'creator'),)
                                firstsuggestion = False
                                totailfailedoptions = totailfailedoptions + 1
                            else:
                                failedtext = failedtext + u', '
                            failedtext = failedtext + u'{{Q|%s}}' % (invitem.get(u'qid'),)
                    failedtext = failedtext + u'\n'
                    if firstsuggestion:
                        totalfailedelse = totalfailedelse + 1
                else:
                    failedtext = failedtext + u'\n'
                    totalfailedelse = totalfailedelse + 1

    # Add the last link if needed
    if addtext:
        suggestionstext = suggestionstext + addlink % (addtext, i % addcluster)

    text = text + autoaddedtext
    text = text + nextaddedtext
    text = text + suggestionstext
    text = text + failedtext
    text = text + u'\n== Statistics ==\n'
    text = text + u'* RKDimages needing a link: %s\n' % (totalimages,)
    text = text + u'* Auto added links this run: %s\n' % (totalautoadded,)
    text = text + u'* To auto add nex run: %s\n' % (totalnextadd,)
    text = text + u'* Number of suggestions: %s\n' % (totalsuggestions,)
    text = text + u'* No suggestion, but in use on another item: %s\n' % (totalfailedinuse,)
    text = text + u'* No suggestion, but paintings available by the same painter: %s\n' % (totailfailedoptions,)
    text = text + u'* No suggestion and nothing found: %s\n' % (totalfailedelse,)

    text = text + u'\n[[Category:WikiProject sum of all paintings RKD to match|%s]]' % (collectienaam, )
    repo = pywikibot.Site().data_repository()

    page = pywikibot.Page(repo, title=pageTitle)
    summary = u'%s RKDimages to link, autoadd now %s, autoadd next %s , suggestions %s, failed in use %s, failed with options %s, left fails %s' % (totalimages,
                                                                                                                                                    totalautoadded,
                                                                                                                                                    totalnextadd,
                                                                                                                                                    totalsuggestions,
                                                                                                                                                    totalfailedinuse,
                                                                                                                                                    totailfailedoptions,
                                                                                                                                                    totalfailedelse,
                                                                                                                                                    )
    page.put(text, summary)

    collectionstats = {u'collectionid' : collectionid,
                       u'collectienaam' : collectienaam,
                       u'pageTitle' : pageTitle,
                       u'totalimages' : totalimages,
                       u'totalautoadded' : totalautoadded,
                       u'totalnextadd' : totalnextadd,
                       u'totalsuggestions' : totalsuggestions,
                       u'totalfailedinuse' : totalfailedinuse,
                       u'totailfailedoptions' : totailfailedoptions,
                       u'totalfailedelse' : totalfailedelse,
                       }

    return collectionstats


def processArtist(artistid, artistname, replacements, pageTitle, autoadd):

    #currentimages = rkdImagesOnWikidata(collectionid)
    allimages = rkdImagesOnWikidata()
    #invnumbers = paintingsInvOnWikidata(collectionid)
    #print invnumbers

    text = u'' # Everything combined in the end

    text = text + u'This pages gives an overview of [https://rkd.nl/en/explore/images#filters%%5Bnaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s paintings in RKDimages] ' % (artistname.replace(u' ', u'%20'), artistname, )
    text = text + u'that are not in use on a painting item (left table) and the painting items by {{Q|%s}} that do not have a link to RKDimages (right table).\n' % (artistid, )
    text = text + u'You can help by connecting these two lists.\n'
    text = text + u'{| style=\'width:100%\'\n| style=\'width:50%;vertical-align: top;\' |\n'
    text = text + u'== RKD with no link to Wikidata ==\n'

    text = text + u'{| class=\'wikitable sortable\' style=\'width:100%\'\n'
    text = text + u'! RKDimage id\n'
    text = text + u'! Title\n'
    text = text + u'! Inception\n'
    text = text + u'! Collection(s)\n'

    #print currentimages
    genrkd = rkdImagesArtistGenerator(artistname)
    rkdcount = 0
    rkdsuggestioncount = 0
    for imageinfo in genrkd:
        rkdcount = rkdcount + 1
        if imageinfo.get('id') in allimages:
            #FIXME: Better info
            pywikibot.output(u'Already in use')
        else:
            rkdsuggestioncount = rkdsuggestioncount + 1
            text = text + u'|-\n'
            text = text + u'| [https://rkd.nl/explore/images/%(id)s %(id)s]\n| %(title)s \n| %(inception)s \n| %(collection)s\n' % imageinfo

    text = text + u'|}\n| style=\'width:50%;vertical-align: top;\' |\n'
    text = text + u'== Wikidata with no link to RKD ==\n'
    text = text + u'{| class=\'wikitable sortable\' style=\'width:100%\'\n'
    text = text + u'! Painting\n'
    text = text + u'! Inception\n'
    text = text + u'! Collection\n'
    #text = text + u'! Title (nl)\n'
    #text = text + u'! Title (en)\n'
    #text = text + u'! Collection(s)\n'

    genwd = paintingsArtistOnWikidata(artistid)

    wdsuggestioncount = 0
    for painting in genwd:
        wdsuggestioncount = wdsuggestioncount + 1
        text = text + u'|-\n'
        text = text + u'| {{Q|%(qid)s}} || %(inception)s ||' % painting
        if painting.get(u'collection'):
            text = text + u' {{Q|%(collection)s}} \n' % painting
        else:
            text = text + u'\n'

    text = text + u'|}\n\n'

    text = text + u'\n[[Category:WikiProject sum of all paintings RKD to match|%s]]' % (artistname, )
    repo = pywikibot.Site().data_repository()

    page = pywikibot.Page(repo, title=pageTitle)
    summary = u'Updating RKD artist page'
    page.put(text, summary)

    artiststats = {u'artistid' : artistid,
                   u'artistname' : artistname,
                   u'pageTitle' : pageTitle,
                   u'rkdcount' : rkdcount,
                   u'rkdsuggestioncount' : rkdsuggestioncount,
                   u'wdsuggestioncount' : wdsuggestioncount,
                   }

    return artiststats

def addRkdimagesLink(itemTitle, rkdid, summary):
    repo = pywikibot.Site().data_repository()
    item = pywikibot.ItemPage(repo, title=itemTitle)
    if not item.exists():
        return False
    if item.isRedirectPage():
        return False
    data = item.get()
    claims = data.get('claims')
    if u'P350' in claims:
        claim = claims.get('P350')[0]
        if claim.getTarget()==u'%s' % (rkdid,):
            pywikibot.output(u'Already got the right link on %s to rkdid %s!' % (itemTitle, rkdid))
            return True
        pywikibot.output(u'Already got a link to %s on %s, I\'m trying to add %s' % (claim.getTarget(),
                                                                                     itemTitle,
                                                                                     rkdid))
        return False

    newclaim = pywikibot.Claim(repo, u'P350')
    newclaim.setTarget(u'%s' % (rkdid,))
    pywikibot.output(summary)
    item.addClaim(newclaim, summary=summary)

    return True

def publishStatistics(artistsstats, collectionsstats):
    repo = pywikibot.Site().data_repository()
    page = pywikibot.Page(repo, title=u'Wikidata:WikiProject sum of all paintings/RKD to match')
    text = u'This pages gives an overview of [https://rkd.nl/en/explore/images#filters%5Bobjectcategorie%5D%5B%5D=painting paintings in RKDimages] to match with paintings in collections on Wikidata.\n'

    totalrkd = 0
    totalrkdsuggestions = 0
    totalwikidata = 0

    text = text + u'== Artists ==\n'
    text = text + u'{| class="wikitable sortable"\n'
    text = text + u'! Artist !! RKDimages !! Page !! Total RKDimages !! RKDimages left to match !! Wikidata possibilities\n'

    for artiststats in artistsstats:
        rkdimageslink = '[https://rkd.nl/en/explore/images#filters%%5Bnaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s in RKDimages] ' % (artiststats.get('artistname').replace(u' ', u'%20'),
                                                                                                                                                        artiststats.get('artistname'), )
        pagelink = u'[[%s|%s]]' % (artiststats.get(u'pageTitle'),
                                   artiststats.get(u'pageTitle').replace(u'Wikidata:WikiProject sum of all paintings/RKD to match/', u''),
                                   )
        text = text + u'|-\n'
        text = text + u'|| {{Q|%s}} ' % (artiststats.get(u'artistid'),)
        text = text + u'|| %s ' % (rkdimageslink,)
        text = text + u'|| %s ' % (pagelink,)
        text = text + u'|| %s ' % (artiststats.get(u'rkdcount'),)
        text = text + u'|| %s ' % (artiststats.get(u'rkdsuggestioncount'),)
        text = text + u'|| %s \n' % (artiststats.get(u'wdsuggestioncount'),)

        totalrkd = totalrkd + artiststats.get(u'rkdcount')
        totalrkdsuggestions = totalrkdsuggestions + artiststats.get(u'rkdsuggestioncount')
        totalwikidata = totalwikidata + artiststats.get(u'wdsuggestioncount')

    text = text + u'|- class="sortbottom"\n'
    text = text + u'| || || || %s || %s || %s\n' % (totalrkd,
                                                    totalrkdsuggestions,
                                                    totalwikidata,
                                                    )
    text = text + u'|}\n\n'
    text = text + u'== Collections ==\n'
    text = text + u'{| class="wikitable sortable"\n'
    text = text + u'! Collection !! RKDimages !! Page !! RKDimages left to match !! Auto added !! Auto next !! Suggestions !! Failed in use !! Failed options !! Failed else\n'

    totalimages = 0
    totalautoadded = 0
    totalnextadd = 0
    totalsuggestions = 0
    totalfailedinuse = 0
    totailfailedoptions= 0
    totalfailedelse = 0

    for collectionstats in collectionsstats:
        rkdimageslink = '[https://rkd.nl/en/explore/images#filters%%5Bcollectienaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s in RKDimages] ' % (collectionstats.get('collectienaam').replace(u' ', u'%20'),
                                                                                                                                                                 collectionstats.get('collectienaam'), )
        pagelink = u'[[%s|%s]]' % (collectionstats.get(u'pageTitle'),
                                   collectionstats.get(u'pageTitle').replace(u'Wikidata:WikiProject sum of all paintings/RKD to match/', u''),
                                   )
        text = text + u'|-\n'
        text = text + u'|| {{Q|%s}} ' % (collectionstats.get(u'collectionid'),)
        text = text + u'|| %s ' % (rkdimageslink,)
        text = text + u'|| %s ' % (pagelink,)
        text = text + u'|| %s ' % (collectionstats.get(u'totalimages'),)
        text = text + u'|| %s ' % (collectionstats.get(u'totalautoadded'),)
        text = text + u'|| %s ' % (collectionstats.get(u'totalnextadd'),)
        text = text + u'|| %s ' % (collectionstats.get(u'totalsuggestions'),)
        text = text + u'|| %s ' % (collectionstats.get(u'totalfailedinuse'),)
        text = text + u'|| %s ' % (collectionstats.get(u'totailfailedoptions'),)
        text = text + u'|| %s \n' % (collectionstats.get(u'totalfailedelse'),)

        totalimages = totalimages + collectionstats.get(u'totalimages')
        totalautoadded = totalautoadded + collectionstats.get(u'totalautoadded')
        totalnextadd = totalnextadd + collectionstats.get(u'totalnextadd')
        totalsuggestions = totalsuggestions + collectionstats.get(u'totalsuggestions')
        totalfailedinuse = totalfailedinuse + collectionstats.get(u'totalfailedinuse')
        totailfailedoptions = totailfailedoptions + collectionstats.get(u'totailfailedoptions')
        totalfailedelse = totalfailedelse + collectionstats.get(u'totalfailedelse')

    text = text + u'|- class="sortbottom"\n'
    text = text + u'| || || || %s || %s || %s || %s || %s || %s || %s\n' % (totalimages,
                                                                            totalautoadded,
                                                                            totalnextadd,
                                                                            totalsuggestions,
                                                                            totalfailedinuse,
                                                                            totailfailedoptions,
                                                                            totalfailedelse,
                                                                            )
    text = text + u'|}\n\n[[Category:WikiProject sum of all paintings RKD to match| ]]'

    summary = u'%s RKDimages to link, autoadd now %s, autoadd next %s , suggestions %s, failed in use %s, failed with options %s, left fails %s' % (totalimages,
                                                                                                                                                    totalautoadded,
                                                                                                                                                    totalnextadd,
                                                                                                                                                    totalsuggestions,
                                                                                                                                                    totalfailedinuse,
                                                                                                                                                    totailfailedoptions,
                                                                                                                                                    totalfailedelse,
                                                                                                                                                    )
    page.put(text, summary)


def main(*args):
    recentRKDimagesBot = RecentRKDimagesBot()
    recentRKDimagesBot.run()


if __name__ == "__main__":
    main()
