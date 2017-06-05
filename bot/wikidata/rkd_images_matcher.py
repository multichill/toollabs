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
        result[int(resultitem.get('id'))] = qid
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
        print searchUrl
        searchPage = requests.get(searchUrl, verify=False)
        searchJson = searchPage.json()
        numfound = searchJson.get('response').get('numFound')
        print numfound
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
                imageinfo[u'title_nl'] = rkdimage.get(u'benaming_kunstwerk')[0]
                imageinfo[u'title_en'] = rkdimage.get(u'titel_engels')
                imageinfo[u'creator'] = rkdimage.get(u'kunstenaar')
                if rkdimage.get(u'toeschrijving'):
                    imageinfo[u'rkdartistid'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_linkref')
                    # Overwrite creator with something more readable
                    imageinfo[u'creator'] = rkdimage.get(u'toeschrijving')[0].get(u'naam_inverted')
                imageinfo[u'invnum'] = None
                imageinfo[u'qid'] = None
                imageinfo[u'url'] = None
                for collectie in rkdimage.get(u'collectie'):
                    if collectie.get('collectienaam') == collection:
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
        print searchUrl
        searchPage = requests.get(searchUrl, verify=False)
        searchJson = searchPage.json()
        #print searchJson
        numfound = searchJson.get('response').get('numFound')
        print numfound
        if not start < numfound:
            return
        start = start + rows
        for rkdimage in  searchJson.get('response').get('docs'):
            imageinfo = {}
            imageinfo[u'id'] = rkdimage.get(u'priref')
            titlenl = rkdimage.get(u'benaming_kunstwerk')[0]
            titleen = rkdimage.get(u'titel_engels')
            if titlenl==titleen:
                imageinfo[u'title'] = titlenl
            else:
                imageinfo[u'title'] = u'%s / %s' % (titlenl, titleen)
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
                        collection = collection + collectie.get('collectienaam')
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
                        summary = summary + u' / %(invnum)s / [https://rkd.nl/explore/artists/%(id)s %(creator)s]' % rkdimageid
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

    text = text + u'This pages gives an overview of [https://rkd.nl/en/explore/images#filters%%5Cnaam%%5D=%s&filters%%5Bobjectcategorie%%5D%%5B%%5D=painting %s paintings in RKDimages] ' % (artistname.replace(u' ', u'%20'), artistname, )
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
    i = 0
    for imageinfo in genrkd:
        i = i + 1
        if imageinfo.get('id') in allimages:
            #FIXME: Better info
            pywikibot.output(u'Already in use')
        else:
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

    for painting in genwd:
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

    return

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

def publishStatistics(workstatistics):
    repo = pywikibot.Site().data_repository()
    page = pywikibot.Page(repo, title=u'Wikidata:WikiProject sum of all paintings/RKD to match')
    text = u'This pages gives an overview of [https://rkd.nl/en/explore/images#filters%5Bobjectcategorie%5D%5B%5D=painting paintings in RKDimages] to match with paintings in collections on Wikidata.\n'
    text = text + u'{| class="wikitable sortable"\n'
    text = text + u'! Collection !! RKDimages !! Page !! Total !! Auto added !! Auto next !! Suggestions !! Failed in use !! Failed options !! Failed else\n'

    totalimages = 0
    totalautoadded = 0
    totalnextadd = 0
    totalsuggestions = 0
    totalfailedinuse = 0
    totailfailedoptions= 0
    totalfailedelse = 0

    for collectionstats in workstatistics:
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
                u'Q160236' : { u'collectienaam' : u'Metropolitan Museum of Art, The',
                            u'replacements' : [],
                            u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/MET',
                            },
                u'Q214867' : { u'collectienaam' : u'National Gallery of Art (Washington)',
                            u'replacements' : [(u'^(\d+\.\d+\.\d+)[^\d]+.+$', u'\\1'), ],
                            u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/NGA',
                            },
                u'Q132783' : { u'collectienaam' : u'Hermitage',
                               u'replacements' : [(u'^(\d+)$', u'ГЭ-\\1'), ],
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
                               u'replacements' : [],
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
                              u'replacements' : [(u'^(\d\d\d\d)$', u'P0\\1'),
                                                 (u'^(\d\d\d)$', u'P00\\1'),
                                                 (u'^PO? ?(\d\d\d\d)(\s*\(cat\. 2006\))?$', u'P0\\1'),
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
                              u'replacements' : [],
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Museum Rotterdam',
                              },
                u'Q224124' : { u'collectienaam' : u'Van Gogh Museum',
                              u'replacements' : [(u'^F (\d+.+)$', u'F\\1'),], # A lot of them use F numbers
                              u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Van Gogh Museum',
                              },
                u'Q3044768' : { u'collectienaam' : u'Musée du Louvre',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Louvre',
                               },
                u'Q812285' : { u'collectienaam' : u'Bayerische Staatsgemäldesammlungen',
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
                               u'replacements' : [(u'^(.+)\s(.+)$', u'\\1\\2'),], # Remove the extra space
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
                u'Q18600731' : { u'collectienaam' : u'Instituut Collectie Nederland', #u'Rijksdienst voor het Cultureel Erfgoed',
                                u'replacements' : [(u'^(.+)\s(.+)$', u'\\1\\2'),], # Remove the extra space
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
                u'Q28097342' : { u'collectienaam' : u'Hoop, Adriaan van der',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Adriaan van der Hoop collection',
                                 },
                u'Q51252' : { u'collectienaam' : u'Uffizi, Galleria degli',
                                 u'replacements' : [],
                                 u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Uffizi',
                                 },
                u'Q1954426' : { u'collectienaam' : u'Museum Catharijneconvent',
                              u'replacements' : [],
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
                                u'replacements' : [],
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
                #u'Q768717' : { u'collectienaam' : u'Private collection', # Probably still too big
                #                u'replacements' : [],
                #                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Private collection',
                #                },

               }

    artists = { u'Q289441' : { u'artistname' : u'Breitner, George Hendrik',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/George Hendrik Breitner',
                             },
                u'Q150679' : { u'artistname' : u'Dyck, Anthony van',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Anthony van Dyck',
                               },
                u'Q5582' : { u'artistname' : u'Gogh, Vincent van',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Vincent van Gogh',
                             },
                u'Q979534' : { u'artistname' : u'Israels, Isaac',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Isaac Israëls',
                             },
                u'Q528460' : { u'artistname' : u'Israëls, Jozef',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jozef Israëls',
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
                u'Q151803' : { u'artistname' : u'Mondriaan, Piet',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Piet Mondrian',
                               },
                u'Q5598' : { u'artistname' : u'Rembrandt',
                               u'replacements' : [],
                               u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Rembrandt',
                               },
                u'Q5599' : { u'artistname' : u'Rubens, Peter Paul',
                             u'replacements' : [],
                             u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Peter Paul Rubens',
                            },
                u'Q1682227' : { u'artistname' : u'Sluijters, Jan',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Jan Sluyters',
                              },
                u'Q1691988' : { u'artistname' : u'Weissenbruch, Jan Hendrik',
                                u'replacements' : [],
                                u'pageTitle' : u'Wikidata:WikiProject sum of all paintings/RKD to match/Johan Hendrik Weissenbruch',
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
        for artistid in artists.keys():
            processArtist(artistid,
                          artists[artistid][u'artistname'],
                          artists[artistid][u'replacements'],
                          artists[artistid][u'pageTitle'],
                          autoadd,
                          )
        workstatistics = []
        for collectionid in sources.keys():
            collectionstats = processCollection(collectionid,
                                                sources[collectionid][u'collectienaam'],
                                                sources[collectionid][u'replacements'],
                                                sources[collectionid][u'pageTitle'],
                                                autoadd,
                                                )
        workstatistics.append(collectionstats)
        publishStatistics(workstatistics)

if __name__ == "__main__":
    main()