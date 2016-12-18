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
        query = u"""SELECT ?item ?id WHERE {
        ?item wdt:P350 ?id .
        ?item p:P195 ?colstatement .
        ?colstatement ps:P195 wd:%s . }""" % (collectionid,)
    else:
        query = u'SELECT ?item ?id WHERE { ?item wdt:P350 ?id  }'
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
    }""" % (collectionid, collectionid, )
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
    text = text + u'\n[[Category:User:Multichill]]'
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

def main(*args):

    suggestions = u''

    sources = { u'Q190804' : { u'collectienaam' : u'Rijksmuseum',
                               u'replacements' : [(u'^(A|C)\s*(\d+)$', u'SK-\\1-\\2'),
                                                  (u'^[sS][kK]\s*-?(A|C)-?\s*(\d+)$', u'SK-\\1-\\2'),
                                                  (u'^cat\.(A|C)\s*(\d+)$', u'SK-\\1-\\2')],
                               u'pageTitle' : u'User:Multichill/Rijksmuseum RKD to match',
                             },
                u'Q221092' : { u'collectienaam' : u'Koninklijk Kabinet van Schilderijen Mauritshuis',
                               u'replacements' : [],
                               u'pageTitle' : u'User:Multichill/Mauritshuis RKD to match',
                              },
                u'Q1820897' : { u'collectienaam' : u'Amsterdam Museum',
                               u'replacements' : [(u'^S?(A|B)\s*(\d+)$', u'S\\1 \\2'), ],
                               u'pageTitle' : u'User:Multichill/Amsterdam Museum RKD to match',
                               },
                u'Q679527' : { u'collectienaam' : u'Museum Boijmans Van Beuningen',
                            u'replacements' : [(u'^(\d+)$', u'\\1 (MK)'), ],
                            u'pageTitle' : u'User:Multichill/Boijmans RKD to match',
                            },
                u'Q924335' : { u'collectienaam' : u'Stedelijk Museum Amsterdam',
                            u'replacements' : [(u'^(\d+)$', u'A \\1'), # Switch to B at some point
                                               (u'^A(\d+)$', u'A \\1'),
                                               (u'^B(\d+)$', u'B \\1'),
                                               ],
                            u'pageTitle' : u'User:Multichill/Stedelijk RKD to match',
                            },
                u'Q160236' : { u'collectienaam' : u'Metropolitan Museum of Art, The',
                            u'replacements' : [],
                            u'pageTitle' : u'User:Multichill/MET RKD to match',
                            },
                u'Q214867' : { u'collectienaam' : u'National Gallery of Art (Washington)',
                            u'replacements' : [(u'^(\d+\.\d+\.\d+)[^\d]+.+$', u'\\1'), ],
                            u'pageTitle' : u'User:Multichill/NGA RKD to match',
                            },
                u'Q132783' : { u'collectienaam' : u'Hermitage',
                               u'replacements' : [(u'^(\d+)$', u'ГЭ-\\1'), ],
                               u'pageTitle' : u'User:Multichill/Hermitage RKD to match',
                               },
                u'Q260913' : { u'collectienaam' : u'Centraal Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'User:Multichill/Centraal Museum RKD to match',
                               },
                u'Q1499958' : { u'collectienaam' : u'Gemeentemuseum Den Haag',
                               u'replacements' : [(u'^(\d+) / .+$', u'\\1'), # Multiple inventory numbers
                                                  (u'^.+ / (\d+)$', u'\\1'),], # And vanished from website
                               u'pageTitle' : u'User:Multichill/Gemeentemuseum Den Haag RKD to match',
                               },
                u'Q1542668' : { u'collectienaam' : u'Groninger Museum',
                               u'replacements' : [],
                               u'pageTitle' : u'User:Multichill/Groninger Museum RKD to match',
                               },
                u'Q574961' : { u'collectienaam' : u'Frans Halsmuseum',
                               u'replacements' : [],
                               u'pageTitle' : u'User:Multichill/Frans Halsmuseum RKD to match',
                               },
                u'Q842858' : { u'collectienaam' : u'Nationalmuseum Stockholm',
                               u'replacements' : [],
                               u'pageTitle' : u'User:Multichill/Nationalmuseum RKD to match',
                               },
                u'Q671384' : { u'collectienaam' : u'SMK - National Gallery of Denmark',
                               u'replacements' : [],
                               u'pageTitle' : u'User:Multichill/SMK RKD to match',
                               },
                u'Q95569' : { u'collectienaam' : u'Kunsthistorisches Museum',
                               u'replacements' : [(u'^(\d+)$', u'GG_\\1'),
                                                  (u'^GG (\d+)$', u'GG_\\1'),
                                                  ],
                               u'pageTitle' : u'User:Multichill/Kunsthistorisches Museum RKD to match',
                               },
                u'Q160112' : { u'collectienaam' : u'Museo Nacional del Prado',
                              u'replacements' : [(u'^(\d\d\d\d)$', u'P0\\1'),
                                                 (u'^(\d\d\d)$', u'P00\\1'),
                                                 (u'^PO? ?(\d\d\d\d)(\s*\(cat\. 2006\))?$', u'P0\\1'),
                                                 ],
                              u'pageTitle' : u'User:Multichill/Prado RKD to match',
                              },
                u'Q180788' : { u'collectienaam' : u'National Gallery (London)',
                              u'replacements' : [(u'^(\d+)$', u'NG\\1'),],
                              u'pageTitle' : u'User:Multichill/National Gallery RKD to match',
                              },
                u'Q1471477' : { u'collectienaam' : u'Koninklijk Museum voor Schone Kunsten Antwerpen',
                              u'replacements' : [],
                              u'pageTitle' : u'User:Multichill/KMSKA RKD to match',
                              },
                u'Q2874177' : { u'collectienaam' : u'Dordrechts Museum',
                              u'replacements' : [], # TODO: Add better regex
                              u'pageTitle' : u'User:Multichill/Dordrechts Museum RKD to match',
                              },
                u'Q2098586' : { u'collectienaam' : u'Stedelijk Museum De Lakenhal',
                              u'replacements' : [(u'^(\d+)$', u'S \\1'),],
                              u'pageTitle' : u'User:Multichill/Lakenhal RKD to match',
                              },
                u'Q2130225' : { u'collectienaam' : u'Het Schielandshuis',
                              u'replacements' : [],
                              u'pageTitle' : u'User:Multichill/Museum Rotterdam RKD to match',
                              },
                u'Q224124' : { u'collectienaam' : u'Van Gogh Museum',
                              u'replacements' : [],
                              u'pageTitle' : u'User:Multichill/Van Gogh Museum RKD to match',
                              },
               }
    collectionid = None
    autoadd = 0

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collectionid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]
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
        worksources = [collectionid, ]
    else:
        worksources = sources.keys()

    for collectionid in worksources:
        suggestion = processCollection(collectionid,
                                       sources[collectionid][u'collectienaam'],
                                       sources[collectionid][u'replacements'],
                                       sources[collectionid][u'pageTitle'],
                                       autoadd,
                                       )
        suggestions = suggestions + suggestion

    with open('/tmp/rkd_images_suggestions.txt', u'wb') as txt:
        txt.write(suggestions)
        txt.close()

if __name__ == "__main__":
    main()