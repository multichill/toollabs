#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to match RKD images on Wikidata with RKD images and make some sort of easy result

"""
import pywikibot
import requests
import pywikibot.data.sparql
import re

        
def rkdImagesOnWikidata(collectionid=None):
    '''
    Just return all the RKD images as a dict
    :return: Dict
    '''
    result = {}
    sq = pywikibot.data.sparql.SparqlQuery()
    if collectionid:
        # Need to use the long version here to get all ranks
        query = u"""SELECT DISTINCT ?item ?id WHERE {
        ?item wdt:P350 ?id .
        { ?item p:P195 ?colstatement .
        ?colstatement ps:P195 wd:%s . } UNION
        { ?item p:P276 ?locationstatement .
        ?locationstatement ps:P276 wd:%s . }
        } LIMIT 10000007""" % (collectionid,collectionid,)
    else:
        query = u'SELECT ?item ?id WHERE { ?item wdt:P350 ?id  } LIMIT 10000003'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        try:
            result[int(resultitem.get('id'))] = qid
        except ValueError:
            # Unknown value will trigger this
            pass
    return result

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
                        if isinstance(collectie.get('collectienaam'), str):
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
    bestsuggestions = ''

    i = 0
    addcluster = 10

    addlink = u'** [https://tools.wmflabs.org/wikidata-todo/quick_statements.php?list={{subst:urlencode:%s}} Add the previous %s]\n'

    imagedict = {}
    for rkdimageid in gen:
        invnum = rkdimageid.get(u'invnum')
        if not invnum:
            invnum = ''
        if not invnum in imagedict:
            imagedict[invnum] = []
        imagedict[invnum].append(rkdimageid)

    for invnum in sorted(list(imagedict.keys())):
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
                        bestsuggestions+= u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
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
                       u'bestsuggestions' : bestsuggestions,
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
    text = u'This pages gives an overview of [https://rkd.nl/en/explore/images#filters%5Bobjectcategorie%5D%5B%5D=painting paintings in RKDimages] to match with paintings in [[Wikidata:WikiProject sum of all paintings/Collection|collections]] and [[Wikidata:WikiProject sum of all paintings/Creator|creators]] on Wikidata.\n'
    text = text + u'\nSee also the [[Wikidata:WikiProject sum of all paintings/RKD to match/Oldest additions|oldest]] and [[Wikidata:WikiProject sum of all paintings/RKD to match/Recent additions|recent additions]] to RKDimages.\n'
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
    bestsuggestions = ''

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
        bestsuggestions += collectionstats.get(u'bestsuggestions')

    text = text + u'|- class="sortbottom"\n'
    text = text + u'| || || || %s || %s || %s || %s || %s || %s || %s\n' % (totalimages,
                                                                            totalautoadded,
                                                                            totalnextadd,
                                                                            totalsuggestions,
                                                                            totalfailedinuse,
                                                                            totailfailedoptions,
                                                                            totalfailedelse,
                                                                            )
    text = text + u'|}\n\n'
    text = text + u'=== Best suggestions ===\n'
    text = text + bestsuggestions + '\n\n'

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

    suggestions = u''

    sources = { u'Q190804' : { u'collectienaam' : u'Rijksmuseum',
                               u'replacements' : [(u'^(A|C)\s*(\d+)$', u'SK-\\1-\\2'),
                                                  (u'^[sS][kK]\s*-?(A|C)-?\s*(\d+)$', u'SK-\\1-\\2'),
                                                  (u'^cat\.(A|C)\s*(\d+)$', u'SK-\\1-\\2')],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Rijksmuseum',
                             },
                u'Q221092' : { u'collectienaam' : u'Koninklijk Kabinet van Schilderijen Mauritshuis',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Mauritshuis',
                              },
                u'Q1820897' : { u'collectienaam' : u'Amsterdam Museum',
                               u'replacements' : [(u'^S?(A|B)\s*(\d+)$', u'S\\1 \\2'), ],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Amsterdam Museum',
                               },
                u'Q679527' : { u'collectienaam' : u'Museum Boijmans Van Beuningen',
                            u'replacements' : [(u'^(\d+)$', u'\\1 (OK)'), ],
                            u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Boijmans',
                            },
                u'Q924335' : { u'collectienaam' : u'Stedelijk Museum Amsterdam',
                            u'replacements' : [(u'^(\d+)$', u'A \\1'), # Switch to B at some point
                                               (u'^A(\d+)$', u'A \\1'),
                                               (u'^B(\d+)$', u'B \\1'),
                                               ],
                            u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Stedelijk',
                            },
                u'Q160236' : { u'collectienaam' : u'Metropolitan Museum of Art, The', #u'Metropolitan Museum of Art (The Cloisters), The', #
                            u'replacements' : [],
                            u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/MET',
                            },
                u'Q214867' : { u'collectienaam' : u'National Gallery of Art (Washington)',
                            u'replacements' : [(u'^(\d+\.\d+\.\d+)[^\d]+.+$', u'\\1'), ],
                            u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/NGA',
                            },
                u'Q132783' : { u'collectienaam' : u'Hermitage',
                               u'replacements' : [(u'^(\d+)$', u'ГЭ-\\1'),
                                                  (u'^GE (\d+)$', u'ГЭ-\\1'),
                                                  ],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Hermitage',
                               },
                u'Q260913' : { u'collectienaam' : u'Centraal Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Centraal Museum',
                               },
                u'Q1499958' : { u'collectienaam' : u'Gemeentemuseum Den Haag',
                               u'replacements' : [(u'^(\d+) / .+$', u'\\1'), # Multiple inventory numbers
                                                  (u'^.+ / (\d+)$', u'\\1'),], # And vanished from website
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gemeentemuseum Den Haag',
                               },
                u'Q1542668' : { u'collectienaam' : u'Groninger Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Groninger Museum',
                               },
                u'Q574961' : { u'collectienaam' : u'Frans Halsmuseum',
                               u'replacements' : [#(u'^(\d+[a-z]?)$', u'os I-\\1'),
                                                  #(u'^(\d+-\d+[a-z]?)$', u'os I-\\1'),
                                                  (u'^(I-\d+[a-z]?)$', u'os \\1'),
                                                  (u'^(I-\d+-\d+[a-z]?)$', u'os \\1'),
                                                  (u'^OK?S[ -]?([^\s]+)$', u'os \\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Frans Halsmuseum',
                               },
                u'Q842858' : { u'collectienaam' : u'Nationalmuseum Stockholm',
                               u'replacements' : [(u'^(\d+)$', u'NM \\1'),
                                                  (u'^NM(\d+)$', u'NM \\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Nationalmuseum',
                               },
                u'Q671384' : { u'collectienaam' : u'SMK - National Gallery of Denmark',
                               u'replacements' : [], #(u'^(\d+)$', u'KMS\\1'), # Mostly done, left overs manual
                                                     #(u'^KMS (\d+)$', u'KMS\\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/SMK',
                               },
                u'Q95569' : { u'collectienaam' : u'Kunsthistorisches Museum',
                               u'replacements' : [(u'^(\d+)$', u'GG_\\1'),
                                                  (u'^GG (\d+)$', u'GG_\\1'),
                                                  ],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Kunsthistorisches Museum',
                               },
                u'Q160112' : { u'collectienaam' : u'Museo Nacional del Prado',
                              u'replacements' : [(u'^(\d\d\d\d)$', u'P00\\1'),
                                                 (u'^(\d\d\d)$', u'P000\\1'),
                                                 (u'^PO? ?(\d\d\d\d)(\s*\(cat\. 2006\))?$', u'P00\\1'),
                                                 #(u'^00(\d\d\d\d)$', u'P0\\1'),
                                                 ],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Prado',
                              },
                u'Q180788' : { u'collectienaam' : u'National Gallery (London)',
                              u'replacements' : [(u'^(\d+)$', u'NG\\1'),
                                                 (u'^NG (\d+)$', u'NG\\1'),],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/National Gallery',
                              },
                u'Q1471477' : { u'collectienaam' : u'Koninklijk Museum voor Schone Kunsten Antwerpen',
                              u'replacements' : [],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/KMSKA',
                              },
                u'Q2874177' : { u'collectienaam' : u'Dordrechts Museum',
                              u'replacements' : [], # TODO: Add better regex
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Dordrechts Museum',
                              },
                u'Q2098586' : { u'collectienaam' : u'Stedelijk Museum De Lakenhal',
                              u'replacements' : [(u'^(\d+)$', u'S \\1'),],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Lakenhal',
                              },
                u'Q2130225' : { u'collectienaam' : u'Het Schielandshuis',
                              u'replacements' : [(u'^(\d+)$', u'\\1-A-B'),],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum Rotterdam',
                              },
                u'Q224124' : { u'collectienaam' : u'Van Gogh Museum',
                              u'replacements' : [(u'^F (\d+.+)$', u'F\\1'),], # A lot of them use F numbers
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Van Gogh Museum',
                              },
                u'Q3044768' : { u'collectienaam' : u'Musée du Louvre',
                               u'replacements' : [(u'^(\d+)$', u'INV \\1'),
                                                  (u'^(\w)\.(\w)\.\s?(\d+)', u'\\1\\2 \\3')],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Louvre',
                               },
                u'Q812285' : { u'collectienaam' : u'Bayerische Staatsgemäldesammlungen', #u'Staatsgalerie im neuen Schloss Schleissheim', # u'Alte Pinakothek', #
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Bavarian State Painting Collections',
                                },
                u'Q154568' : { u'collectienaam' : u'Alte Pinakothek',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Alte Pinakothek',
                               },
                u'Q848313' : { u'collectienaam' : u'Fries Museum',
                               u'replacements' : [(u'^(\d\d)$', u'S000\\1'),
                                                  (u'^(\d\d\d)$', u'S00\\1'),
                                                  (u'^(\d\d\d\d)$', u'S0\\1'),
                                                  (u'^(\d.+)$', u'S\\1'),
                                                  (u'^S (\d.+)$', u'S\\1'),
                                                  (u'^FM (\d.+)$', u'S\\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Fries Museum',
                               },
                u'Q510324' : { u'collectienaam' : u'Philadelphia Museum of Art  - John G. Johnson Collection',
                               u'replacements' : [(u'^(\d+)$', u'Cat. \\1'),
                                                  (u'^cat\. (\d+)$', u'Cat. \\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Philadelphia Museum of Art',
                               },
                u'Q1051928' : { u'collectienaam' : u'Kröller-Müller Museum',
                               u'replacements' : [(u'^KM([^\s]+.+)$', u'KM \\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Kröller-Müller',
                               },
                u'Q239303' : { u'collectienaam' : u'Art Institute of Chicago, The',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Art Institute of Chicago',
                                },
                u'Q1201549' : { u'collectienaam' : u'Detroit Institute of Arts',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Detroit Institute of Arts',
                               },
                u'Q49133' : { u'collectienaam' : u'Museum of Fine Arts Boston',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum of Fine Arts Boston',
                                },
                u'Q2365880' : { u'collectienaam' : u'Museum voor Schone Kunsten Gent',
                              u'replacements' : [],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/MSK Gent',
                              },
                u'Q12013217' : { u'collectienaam' : u'Noordbrabants Museum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Noordbrabants Museum',
                                },
                u'Q1459037' : { u'collectienaam' : u'Royal Collection, The', # Royal Collection - Windsor Castle
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Royal Collection',
                                 },
                u'Q153306' : { u'collectienaam' : u'Muzeum Narodowe w Warszawie',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/National Museum in Warsaw',
                                },
                u'Q2051997' : { u'collectienaam' : u'Scottish National Gallery',
                               u'replacements' : [(u'^(\d+)$', u'NG \\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/National Galleries of Scotland',
                               },
                u'Q1641836' : { u'collectienaam' : u'Los Angeles County Museum of Art',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/LACMA',
                                },
                u'Q176251' : { u'collectienaam' : u'Museo Thyssen-Bornemisza',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museo Thyssen-Bornemisza',
                                },
                u'Q2066737' : { u'collectienaam' : u'Instituut Collectie Nederland',
                               u'replacements' : [(u'^(.+)\s(.+)$', u'\\1\\2'), # Remove the extra space
                                                  (u'^(C\d+)\;(\d+)$', u'\\1'), # C numbers sometimes have junk in it
                                                  ],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Instituut Collectie Nederland',
                               },
                u'Q28045660' : { u'collectienaam' : u'Dienst voor \'s Rijks Verspreide Kunstvoorwerpen',
                                u'replacements' : [(u'^(.+)\s(.+)$', u'\\1\\2'),], # Remove the extra space
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Dienst Verspreide Rijkscollecties',
                                },
                u'Q28045665' : { u'collectienaam' : u'Stichting Nederlands Kunstbezit',
                                 u'replacements' : [#(u'^(\d+)$', u'NK\\1'),
                                                    (u'^S?N[kK] (\d+)$', u'NK\\1'),],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Stichting Nederlands Kunstbezit',
                                 },
                u'Q28045674' : { u'collectienaam' : u'Rijksdienst Beeldende Kunst',
                                 u'replacements' : [(u'^(.+)\s(.+)$', u'\\1\\2'),], # Remove the extra space
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Rijksdienst Beeldende Kunst',
                                 },
                u'Q1053735' : { u'collectienaam' : u'Central Collecting Point',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Munich Central Collecting Point',
                                 },
                u'Q1241163' : { u'collectienaam' : u'Dulwich Picture Gallery',
                                u'replacements' : [(u'^DPG\s?(\d\d)$', u'DPG0\\1'),
                                                   (u'^DPG (\d+)$', u'DPG\\1'),
                                                   (u'^(\d\d)$', u'DPG0\\1'),
                                                   (u'^(\d+)$', u'DPG\\1'),],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Dulwich Picture Gallery',
                                },
                u'Q18600731' : { u'collectienaam' : u'Instituut Collectie Nederland', #u'Rijksdienst voor het Cultureel Erfgoed', u'Dienst voor \'s Rijks Verspreide Kunstvoorwerpen',
                                u'replacements' : [(u'^(.+)\s(.+)$', u'\\1\\2'), # Remove the extra space
                                                   (u'^(C\d+)\;(\d+)$', u'\\1'), # C numbers sometimes have junk in it
                                                   ],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Rijksdienst voor het Cultureel Erfgoed',
                                },
                u'Q2324618' : { u'collectienaam' : u'Staatliches Museum Schwerin',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Staatliches Museum Schwerin',
                                 },
                u'Q2284748' : { u'collectienaam' : u'Goudstikker, Jacques',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jacques Goudstikker collection',
                                },
                u'Q28065304' : { u'collectienaam' : u'Goudstikker, erven Jacques',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Goudstikker heirs collection',
                                },
                u'Q19750488' : { u'collectienaam' : u'Hoop, Adriaan van der',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Adriaan van der Hoop collection',
                                 },
                u'Q51252' : { u'collectienaam' : u'Uffizi, Galleria degli',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Uffizi',
                                 },
                u'Q1954426' : { u'collectienaam' : u'Museum Catharijneconvent',
                              u'replacements' : [(u'^([\w\w]{2,4}) [sS][\s0]*(\d+\w?)$', u'\\1 s\\2'),
                                                 (u'^([\w\w]{2,4}) [sS]s\?(\d+)$', u'\\1 s\\2'),
                                                 ],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum Catharijneconvent',
                              },
                u'Q892727' : { u'collectienaam' : u'Bonnefantenmuseum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Bonnefantenmuseum',
                                },
                u'Q281903' : { u'collectienaam' : u'Stedelijk Museum Het Prinsenhof',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Prinsenhof',
                               },
                u'Q1976985' : { u'collectienaam' : u'Nelson-Atkins Museum of Art, The',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Nelson-Atkins Museum of Art',
                               },
                u'Q731126' : { u'collectienaam' : u'J. Paul Getty Museum, The',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/J. Paul Getty Museum',
                                },
                u'Q2628596' : { u'collectienaam' : u'Palais des Beaux-Arts de Lille',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Palais des Beaux-Arts de Lille',
                               },
                u'Q1948674' : { u'collectienaam' : u'Groeningemuseum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Groeningemuseum',
                                },
                u'Q430682' : { u'collectienaam' : u'Tate Gallery',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Tate',
                                },
                u'Q1565911' : { u'collectienaam' : u'Museum of Fine Arts Houston',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum of Fine Arts Houston',
                               },
                u'Q474563' : { u'collectienaam' : u'Teylers Museum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Teylers Museum',
                                },
                u'Q657415' : { u'collectienaam' : u'Cleveland Museum of Art, The',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Cleveland Museum of Art',
                               },
                u'Q866498' : { u'collectienaam' : u'Galleria Palatina (Palazzo Pitti)',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Galleria Palatina',
                               },
                u'Q1700481' : { u'collectienaam' : u'Minneapolis Institute of Arts',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Minneapolis Institute of Arts',
                               },
                u'Q238587' : { u'collectienaam' : u'National Portrait Gallery',
                                u'replacements' : [(u'^(\d+)$', u'NPG \\1'),],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/National Portrait Gallery',
                                },
                u'Q23402' : { u'collectienaam' : u'Musée d\'Orsay',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Musée d\'Orsay',
                               },
                u'Q1416890' : { u'collectienaam' : u'Fine Arts Museums of San Francisco',
                              u'replacements' : [],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Fine Arts Museums of San Francisco',
                              },
                u'Q1117704' : { u'collectienaam' : u'Indianapolis Museum of Art',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Indianapolis Museum of Art',
                                },
                u'Q2970522' : { u'collectienaam' : u'Cincinnati Art Museum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Cincinnati Art Museum',
                                },
                u'Q210081' : { u'collectienaam' : u'Walters Art Museum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Walters Art Museum',
                                },
                u'Q188740' : { u'collectienaam' : u'Museum of Modern Art, The',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum of Modern Art',
                               },
                u'Q1505892' : { u'collectienaam' : u'Rijksmuseum Twenthe',
                               u'replacements' : [(u'^(\d)$', u'000\\1'),
                                                  (u'^(\d\d)$', u'00\\1'),
                                                  (u'^(\d\d\d)$', u'0\\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Rijksmuseum Twenthe',
                               },
                u'Q658725' : { u'collectienaam' : u'Staatliche Kunsthalle Karlsruhe',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Staatliche Kunsthalle Karlsruhe',
                                },
                u'Q377500' : { u'collectienaam' : u'Koninklijke Musea voor Schone Kunsten van België',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Royal Museums of Fine Arts of Belgium',
                               },
                u'Q165631' : { u'collectienaam' : u'Gemäldegalerie (Staatliche Museen zu Berlin)',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gemäldegalerie, Berlin',
                               },
                u'Q431431' : { u'collectienaam' : u'Singer Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Singer Laren',
                               },
                u'Q163804' : { u'collectienaam' : u'Städel Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Städel Museum',
                               },
                u'Q653002' : { u'collectienaam' : u'Staatliche Kunstsammlungen Dresden - Gemäldegalerie Alte Meister',
                               u'replacements' : [(u'^(\d+)$', u'Gal.-Nr. \\1'),],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gemäldegalerie Alte Meister',
                               },
                u'Q2382575' : { u'collectienaam' : u'Westfries Museum',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Westfries Museum',
                             },
                u'Q1616123' : { u'collectienaam' : u'Nederlands Scheepvaartmuseum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Nederlands Scheepvaartmuseum',
                                },
                u'Q700959' : { u'collectienaam' : u'Wallraf-Richartz-Museum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Wallraf-Richartz-Museum',
                                },
                u'Q714783' : { u'collectienaam' : u'Gripsholm Slott',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gripsholm Castle',
                               },
                u'Q255409' : { u'collectienaam' : u'De Mesdag Collectie',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Mesdag Collectie',
                               },
                u'Q678082' : { u'collectienaam' : u'Herzog Anton Ulrich-Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Herzog Anton Ulrich Museum',
                               },
                u'Q61942636' : { u'collectienaam' : u'Bisschoppelijk Museum (Haarlem)',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Bisschoppelijk Museum Haarlem',
                               },
                u'Q1258370' : { u'collectienaam' : u'Drents Museum',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Drents Museum',
                                 },
                u'Q692381' : { u'collectienaam' : u'Paleis Het Loo Nationaal Museum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Het Loo Palace',
                                },
                u'Q4623539' : { u'collectienaam' : u'Stedelijk Museum Alkmaar',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Stedelijk Museum Alkmaar',
                               },
                u'Q2425770' : { u'collectienaam' : u'Museum Simon van Gijn',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Huis Van Gijn',
                                },
                u'Q840886' : { u'collectienaam' : u'Szépmüvészeti Múzeum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum of Fine Arts, Budapest',
                                },
                u'Q11722011' : { u'collectienaam' : u'Haags Historisch Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Haags Historisch Museum',
                               },
                u'Q4872' : { u'collectienaam' : u'Pushkin Museum',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Pushkin Museum',
                                 },
                u'Q2216754' : { u'collectienaam' : u'Museum Bredius',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum Bredius',
                             },
                u'Q169542' : { u'collectienaam' : u'Hamburger Kunsthalle',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Kunsthalle Hamburg',
                                },
                u'Q226103' : { u'collectienaam' : u'The National Museum of History Frederiksborg Castle',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Frederiksborg Palace',
                               },
                u'Q2114028' : { u'collectienaam' : u'Museum voor Moderne Kunst Arnhem',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum Arnhem',
                               },
                u'Q43655709' : { u'collectienaam' : u'Aartsbisschoppelijk Museum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Aartsbisschoppelijk Museum',
                                },
                u'Q468169' : { u'collectienaam' : u'Suermondt-Ludwig-Museum',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Suermondt-Ludwig-Museum',
                                 },
                u'Q1419555' : { u'collectienaam' : u'Národní Galerie v Praze',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/National Gallery in Prague',
                               },
                u'Q2131198' : { u'collectienaam' : u'Slot Zuylen',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Slot Zuylen',
                                },
                u'Q1519002' : { u'collectienaam' : u'Musée Fabre',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Musée Fabre',
                                },
                u'Q566661' : { u'collectienaam' : u'Museum der bildenden Künste Leipzig',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum der bildenden Künste',
                                },
                u'Q687186' : { u'collectienaam' : u'Museum Schloss Wilhelmshöhe',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Schloss Wilhelmshöhe',
                               },
                u'Q702726' : { u'collectienaam' : u'Joods Historisch Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jewish Historical Museum',
                               },
                u'Q1421440' : { u'collectienaam' : u'Fitzwilliam Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Fitzwilliam Museum',
                               },
                u'Q1501215' : { u'collectienaam' : u'Düsseldorfer Galerie',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Düsseldorfer Galerie',
                               },
                u'Q878678' : { u'collectienaam' : u'Lindenau-Museum Altenburg',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Lindenau-Museum',
                                },
                u'Q1568434' : { u'collectienaam' : u'Yale University Art Gallery',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Yale University Art Gallery',
                               },
                u'Q7374509' : { u'collectienaam' : u'National Maritime Museum',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Royal Museums Greenwich',
                                },
                u'Q303139' : { u'collectienaam' : u'Österreichische Galerie Belvedere',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Österreichische Galerie Belvedere',
                                },
                u'Q2362660' : { u'collectienaam' : u'M – Museum Leuven',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/M – Museum Leuven',
                                },
                u'Q29908492' : { u'collectienaam' : u'Museum Flehite',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum Flehite',
                                },
                #u'Q768717' : { u'collectienaam' : u'Private collection', # Probably still too big
                #                u'replacements' : [],
                #                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Private collection',
                #                },

               }
    artists = { u'Q711737' : { u'artistname' : u'Berchem, Nicolaes',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Nicolaes Pieterszoon Berchem',
                             },
                u'Q374039' : { u'artistname' : u'Bol, Ferdinand',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Ferdinand Bol',
                               },
                u'Q346808' : { u'artistname' : u'Borch, Gerard ter (II)',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gerard ter Borch',
                               },
                u'Q130531' : { u'artistname' : u'Bosch, Jheronimus',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Hieronymus Bosch',
                               },
                u'Q289441' : { u'artistname' : u'Breitner, George Hendrik',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/George Hendrik Breitner',
                               },
                u'Q153472' : { u'artistname' : u'Cleve, Joos van',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Joos van Cleve',
                                },
                u'Q367798' : { u'artistname' : u'Coorte, Adriaen',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Adriaen Coorte',
                               },
                u'Q313194' : { u'artistname' : u'Cuyp, Aelbert',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Aelbert Cuyp',
                               },
                u'Q160422' : { u'artistname' : u'Doesburg, Theo van',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Theo van Doesburg',
                               },
                u'Q335927' : { u'artistname' : u'Dou, Gerard',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gerrit Dou',
                               },
                u'Q150679' : { u'artistname' : u'Dyck, Anthony van',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Anthony van Dyck',
                               },
                u'Q624802' : { u'artistname' : u'Fijt, Joannes',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan Fyt',
                               },
                u'Q1442507' : { u'artistname' : u'Francken, Frans (II)',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Frans Francken the Younger',
                                },
                u'Q5582' : { u'artistname' : u'Gogh, Vincent van',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Vincent van Gogh',
                             },
                u'Q315996' : { u'artistname' : u'Goyen, Jan van',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan van Goyen',
                             },
                u'Q167654' : { u'artistname' : u'Hals, Frans (I)',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Frans Hals',
                               },
                u'Q538350' : { u'artistname' : u'Heemskerck, Maarten van',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Maarten van Heemskerck',
                             },
                u'Q380704' : { u'artistname' : u'Helst, Bartholomeus van der',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Bartholomeus van der Helst',
                               },
                u'Q370567' : { u'artistname' : u'Heyden, Jan van der',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan van der Heyden',
                               },
                u'Q314548' : { u'artistname' : u'Honthorst, Gerard van',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gerard van Honthorst',
                               },
                u'Q314889' : { u'artistname' : u'Hooch, Pieter de',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Pieter de Hooch',
                               },
                u'Q979534' : { u'artistname' : u'Israels, Isaac',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Isaac Israëls',
                             },
                u'Q528460' : { u'artistname' : u'Israëls, Jozef',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jozef Israëls',
                               },
                u'Q270658' : { u'artistname' : u'Jordaens, Jacob (I)',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jacob Jordaens',
                               },
                u'Q2500930' : { u'artistname' : u'Kat, Otto B. de',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Otto B. de Kat',
                               },
                u'Q505150' : { u'artistname' : u'Maes, Nicolaes',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Nicolaes Maes',
                               },
                u'Q978158' : { u'artistname' : u'Maris, Jacob',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jacob Maris',
                               },
                u'Q1375830' : { u'artistname' : u'Maris, Matthijs',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Matthijs Maris',
                               },
                u'Q591907' : { u'artistname' : u'Mauve, Anton',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Anton Mauve',
                               },
                u'Q355213' : { u'artistname' : u'Metsu, Gabriel',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Gabriël Metsu',
                               },
                u'Q864092' : { u'artistname' : u'Mierevelt, Michiel van',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Michiel van Mierevelt',
                               },
                u'Q959236' : { u'artistname' : u'Mieris, Frans van (I)',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Frans van Mieris the Elder',
                               },
                u'Q151803' : { u'artistname' : u'Mondriaan, Piet',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Piet Mondrian',
                               },
                u'Q352438' : { u'artistname' : u'Ostade, Adriaen van',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Adriaen van Ostade',
                               },
                u'Q5598' : { u'artistname' : u'Rembrandt',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Rembrandt',
                               },
                u'Q5599' : { u'artistname' : u'Rubens, Peter Paul',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Peter Paul Rubens',
                            },
                u'Q213612' : { u'artistname' : u'Ruisdael, Jacob van',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jacob van Ruisdael',
                             },
                u'Q1682227' : { u'artistname' : u'Sluijters, Jan',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan Sluyters',
                              },
                u'Q205863' : { u'artistname' : u'Steen, Jan',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan Steen',
                                },
                u'Q335022' : { u'artistname' : u'Teniers, David (II)',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/David Teniers the Younger',
                                },
                u'Q41264' : { u'artistname' : u'Vermeer, Johannes',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Johannes Vermeer',
                                },
                u'Q1691988' : { u'artistname' : u'Weissenbruch, Jan Hendrik',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Johan Hendrik Weissenbruch',
                                },
                u'Q2614892' : { u'artistname' : u'Witsen, Willem',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Willem Witsen',
                                },
                u'Q454671' : { u'artistname' : u'Wouwerman, Philips',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Philips Wouwerman',
                                },
                }
    collectionid = None
    artistid = None
    autoadd = 0

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collectionid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]
        elif arg.startswith('-artistid:'):
            if len(arg) == 10:
                artistid = pywikibot.input(
                        u'Please enter the aristid you want to work on:')
            else:
                artistid = arg[10:]
        elif arg.startswith('-autoadd:'):
            if len(arg) == 9:
                autoadd = int(pywikibot.input(
                        u'Please enter the number of items you want to update automatically:'))
            else:
                autoadd = int(arg[9:])

    if collectionid:
        if collectionid not in sources.keys():
            pywikibot.output(u'%s is not a valid collectionid!' % (collectionid,))
            return
        processCollection(collectionid,
                          sources[collectionid][u'collectienaam'],
                          sources[collectionid][u'replacements'],
                          sources[collectionid][u'pageTitle'],
                          autoadd,
                          )
    elif artistid:
        processArtist(artistid,
                      artists[artistid][u'artistname'],
                      artists[artistid][u'replacements'],
                      artists[artistid][u'pageTitle'],
                      autoadd,
                      )

    else:
        artistsstats = []
        for artistid in artists.keys():
            artiststats = processArtist(artistid,
                                        artists[artistid][u'artistname'],
                                        artists[artistid][u'replacements'],
                                        artists[artistid][u'pageTitle'],
                                        autoadd,
                                        )
            artistsstats.append(artiststats)
        collectionsstats = []
        for collectionid in sources.keys():
            collectionstats = processCollection(collectionid,
                                                sources[collectionid][u'collectienaam'],
                                                sources[collectionid][u'replacements'],
                                                sources[collectionid][u'pageTitle'],
                                                autoadd,
                                                )
            collectionsstats.append(collectionstats)
        publishStatistics(artistsstats, collectionsstats)

if __name__ == "__main__":
    main()
