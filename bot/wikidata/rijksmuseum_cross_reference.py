#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Got a nice data set with old id's and id's in other collections for Rijksmuseum works.
Let's see what we can do with this.

"""
import pywikibot
import requests
import pywikibot.data.sparql
import re
import codecs
        
def rkdImagesOnWikidata(collectionid=None):
    '''
    Just return all the RKD images as a dict
    :return: Dict
    '''
    result = {}
    sq = pywikibot.data.sparql.SparqlQuery()
    if collectionid:
        # Need to use the long version here to get all ranks
        query = u"""SELECT ?item ?id WHERE {
        ?item wdt:P350 ?id .
        ?item p:P195 ?colstatement .
        ?colstatement ps:P195 wd:%s . } LIMIT 100003""" % (collectionid,)
    else:
        query = u'SELECT ?item ?id WHERE { ?item wdt:P350 ?id  } LIMIT 100003'
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
    query = u"""SELECT ?item ?id ?url ?rkdimageid ?rkdartistid WHERE {
    ?item p:P195 ?colstatement .
    ?colstatement ps:P195 wd:%s .
    ?item wdt:P31 wd:Q3305213 .
    ?item p:P217 ?invstatement .
    ?invstatement ps:P217 ?id .
    ?invstatement pq:P195 wd:%s .
    OPTIONAL { ?item wdt:P973 ?url } .
    OPTIONAL { ?item wdt:P350 ?rkdimageid } .
    OPTIONAL { ?item wdt:P170 ?creator .
    ?creator wdt:P650 ?rkdartistid }
    } LIMIT 100003""" % (collectionid, collectionid, )
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
        start = start + rows
        print searchUrl
        searchPage = requests.get(searchUrl, verify=False)
        searchJson = searchPage.json()
        numfound = searchJson.get('response').get('numFound')
        print numfound
        if not start < numfound:
            return
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

def processCollection(collectionid, collectienaam, replacements, pageTitle, autoadd):

    result = u''

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
            # We found a match, just not sure how solid it is
            if rkdimageid.get(u'qid'):
                result = result + u'%(id)s|%(qid)s\n' % rkdimageid
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
                        else:
                            suggestionstext = suggestionstext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid

                            addtext = addtext + u'%(qid)s\tP350\t"%(id)s"\n' % rkdimageid
                            i = i + 1
                            if not i % addcluster:
                                suggestionstext = suggestionstext + addlink % (addtext, addcluster)
                                addtext = u''

                    else:
                        nextaddedtext = nextaddedtext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                # Something is not adding up, add it to the suggestions list
                else:
                    suggestionstext = suggestionstext + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid

                    addtext = addtext + u'%(qid)s\tP350\t"%(id)s"\n' % rkdimageid
                    i = i + 1
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

                # Anonymous (rkd id 1984) will make the list explode
                elif not rkdimageid.get(u'rkdartistid')==u'1984':
                    firstsuggestion = True
                    for inv, invitem in invnumbers.items():
                        if invitem.get(u'rkdartistid') and not invitem.get(u'rkdimageid') \
                                and invitem.get(u'rkdartistid')==rkdimageid.get(u'rkdartistid'):
                            if firstsuggestion:
                                failedtext = failedtext + u' -> Paintings by \'\'%s\'\' that still need a link: ' % (rkdimageid.get(u'creator'),)
                                firstsuggestion = False
                            else:
                                failedtext = failedtext + u', '
                            failedtext = failedtext + u'{{Q|%s}}' % (invitem.get(u'qid'),)
                    failedtext = failedtext + u'\n'
                else:
                    failedtext = failedtext + u'\n'

    # Add the last link if needed
    if addtext:
        suggestionstext = suggestionstext + addlink % (addtext, i % addcluster)

    text = text + autoaddedtext
    text = text + nextaddedtext
    text = text + suggestionstext
    text = text + failedtext
    text = text + u'\n[[Category:WikiProject sum of all paintings RKD to match|%s]]' % (collectienaam, )
    repo = pywikibot.Site().data_repository()

    page = pywikibot.Page(repo, title=pageTitle)
    summary = u'RKDimages to link'
    page.put(text, summary)

    return result

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

def parseRijksmuseumFile(filename=u'/tmp/Alternatieve nummers OB schilderij.dat'):
    data = {u'I1' : [],
            u'I3' : [],
            u'I5' : [],
            u'I6' : [],
            u'IN' : None,
            }
    regex = u'^(I1|I3|I5|I6|IN|\*\*)\s?(.*)$'
    with codecs.open(filename, 'r', "utf-8") as datafile:
        for line in datafile.readlines():
            match = re.match(regex, line.strip())
            if match:
                datakey = match.group(1)
                datavalue = match.group(2)
                if datakey==u'**':
                    yield data
                    data = {u'I1' : [],
                            u'I3' : [],
                            u'I5' : [],
                            u'I6' : [],
                            u'IN' : None,
                            }
                elif datakey==u'IN':
                    data[datakey] = datavalue
                else:
                    data[datakey].append(datavalue)

def addExtraInventoryNumber(repo, qid, invnumber, collectionid):

    item = pywikibot.ItemPage(repo, title=qid)
    collectionitem = pywikibot.ItemPage(repo, title=collectionid)

    data = item.get()
    claims = data.get('claims')

    foundinv = False
    if u'P217' in claims:
        for invnumberclaim in claims.get(u'P217'):
            if invnumberclaim.getTarget()==u'invnumber':
                print u'Invnumber %s already present on %s' % (invnumber, qid)
                foundinv = True
    if not foundinv:
        summary = u'Adding old inventory number from it was on loan to the Rijksmuseum based on data from their collection database'
        newclaim = pywikibot.Claim(repo, u'P217')
        newclaim.setTarget(invnumber)
        pywikibot.output('Adding new id claim to %s' % item)
        item.addClaim(newclaim, summary=summary)

        newqualifier = pywikibot.Claim(repo, u'P195')
        newqualifier.setTarget(collectionitem)
        pywikibot.output('Adding new qualifier claim to %s' % item)
        newclaim.addQualifier(newqualifier)


def main(*args):
    rijksmuseumPaintings = paintingsInvOnWikidata(u'Q190804')
    amsterdamMuseumPaintings = paintingsInvOnWikidata(u'Q1820897')
    rcePaintings = paintingsInvOnWikidata(u'Q18600731')
    snkPaintings = paintingsInvOnWikidata(u'Q28045665')

    repo = pywikibot.Site().data_repository()

    oldinvnumbers = u''
    possibleduplicates = u''

    for item in parseRijksmuseumFile():
        #print item
        rijksinv = item.get(u'IN')
        if item.get(u'I6'):
            i = 0
            for collectienaam in item.get(u'I6'):
                if item.get(u'I3'):
                    inv = item.get(u'I3')[i]
                    if collectienaam==u'Rijksmuseum Amsterdam':
                        qid1 = rijksmuseumPaintings.get(rijksinv).get('qid')
                        if inv in rijksmuseumPaintings:
                            qid2 = rijksmuseumPaintings.get(inv).get('qid')
                            if qid1!=qid2:
                                possibleduplicates = possibleduplicates + u'* {{Q|%s}} (%s) & {{Q|%s}} (Rijksmuseum %s)\n' % (qid1,
                                                                                                                              rijksinv,
                                                                                                                              qid2,
                                                                                                                              inv)
                        elif inv.startswith(u'SK-C'):
                            addExtraInventoryNumber(repo, qid1, inv, u'Q190804')
                            oldinvnumbers = oldinvnumbers + u'* {{Q|%s}} (%s): old inventory number %s can be added\n' % (qid1,
                                                                                                                          rijksinv,
                                                                                                                          inv,
                                                                                                                          )
                            #print u'%s is an old inventory number for %s' % (inv, rijksinv)
                        #else:
                        #    print u'Weird id %s is an old inventory number for %s' % (inv, rijksinv)
                    elif collectienaam==u'Amsterdams Historisch Museum':
                        if inv.startswith(u'A') or inv.startswith(u'B'):
                            inv = u'S%s' % (inv,)
                        if inv in amsterdamMuseumPaintings:
                            qid1 = rijksmuseumPaintings.get(rijksinv).get('qid')
                            qid2 = amsterdamMuseumPaintings.get(inv).get('qid')
                            if qid1!=qid2:
                                possibleduplicates = possibleduplicates + u'* {{Q|%s}} ([%s %s]) & {{Q|%s}} (Amsterdam Museum [%s %s])\n' % (qid1,
                                                                                                                                             rijksmuseumPaintings.get(rijksinv).get('url'),
                                                                                                                                             rijksinv,
                                                                                                                                             qid2,
                                                                                                                                             amsterdamMuseumPaintings.get(inv).get('url'),
                                                                                                                                             inv,
                                                                                                                                             )
                        #else:
                        # FIXME: Figure this part out
                        #    print u'Amsterdam Museum id %s seems to be the same for %s' % (inv, rijksinv)
                    elif collectienaam==u'Instituut Collectie Nederland':
                        if inv in rcePaintings:
                            qid1 = rijksmuseumPaintings.get(rijksinv).get('qid')
                            qid2 = rcePaintings.get(inv).get('qid')
                            if qid1!=qid2:
                                possibleduplicates = possibleduplicates + u'* {{Q|%s}} ([%s %s]) & {{Q|%s}} (RCE [%s %s])\n' % (qid1,
                                                                                                                                rijksmuseumPaintings.get(rijksinv).get('url'),
                                                                                                                                rijksinv,
                                                                                                                                qid2,
                                                                                                                                rcePaintings.get(inv).get('url'),
                                                                                                                                inv,
                                                                                                                                )
                                #else:
                                # FIXME: Figure this part out
                                #    print u'Amsterdam Museum id %s seems to be the same for %s' % (inv, rijksinv)
                    elif collectienaam==u'Stichting Nederlands Kunstbezit':
                        if inv in snkPaintings:
                            qid1 = rijksmuseumPaintings.get(rijksinv).get('qid')
                            qid2 = snkPaintings.get(inv).get('qid')
                            if qid1!=qid2:
                                possibleduplicates = possibleduplicates + u'* {{Q|%s}} ([%s %s]) & {{Q|%s}} (SNK [%s %s])\n' % (qid1,
                                                                                                                                rijksmuseumPaintings.get(rijksinv).get('url'),
                                                                                                                                rijksinv,
                                                                                                                                qid2,
                                                                                                                                snkPaintings.get(inv).get('url'),
                                                                                                                                inv,
                                                                                                                                )
                                #else:
                                # FIXME: Figure this part out
                                #    print u'Amsterdam Museum id %s seems to be the same for %s' % (inv, rijksinv)
                i = i + 1
    #print possibleduplicates
    #print oldinvnumbers


    page = pywikibot.Page(repo, title=u'User:Multichill/Zandbak')

    summary = u'Some Rijksmuseum stuff to clean up.'
    text = summary + u'\n'
    text = text + u'== Possible duplicates ==\n' + possibleduplicates
    #text = text + u'== Old inventory numbers ==\n' + oldinvnumbers

    print text
    page.put(text, summary)
        #if rijksinv in rijksmuseumPaintings:
        #    print rijksmuseumPaintings.get(rijksinv).get('qid')
        #else:
        #    print u'Not found %s' % (rijksinv,)
        #print item




if __name__ == "__main__":
    main()