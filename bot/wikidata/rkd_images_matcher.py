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
        query = u'SELECT ?item ?id WHERE { ?item wdt:P350 ?id . ?item wdt:P195 wd:%s }' % (collectionid,)
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
    sq = pywikibot.data.sparql.SparqlQuery()
    query = u'SELECT ?item ?id ?url WHERE { ?item wdt:P195 wd:%s . ?item wdt:P31 wd:Q3305213 . ?item wdt:P217 ?id .  OPTIONAL { ?item wdt:P973 ?url } }' % (collectionid,)
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = { u'qid' : qid }
        if resultitem.get('url'):
            result[resultitem.get('id')]['url'] = resultitem.get('url')

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

                yield imageinfo

def processCollection(collectionid, collectienaam, replacements, pageTitle):

    result = u''

    currentimages = rkdImagesOnWikidata(collectionid)
    allimages = rkdImagesOnWikidata()
    invnumbers = paintingsInvOnWikidata(collectionid)
    #print invnumbers

    #print currentimages
    gen = rkdImagesGenerator(currentimages, invnumbers, collectienaam, replacements)

    text = u'<big><big><big>This list contains quite a few mistakes. These will probably fill up at the top. Please check every suggestion before approving</big></big></big>\n\n'
    text = text + u'This list was generated with a bot. If I was confident enough about the suggestions I would have just have the bot add them. '
    text = text + u'Feel free to do any modifications in this page, but a bot will come along and overwrite this page every once in a while.\n\n'
    addtext = u''
    failedtext = u''

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
            if rkdimageid.get(u'qid'):
                text = text + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                result = result + u'%(id)s|%(qid)s\n' % rkdimageid
                addtext = addtext + u'%(qid)s\tP350\t"%(id)s"\n' % rkdimageid
                i = i + 1
                if not i % addcluster:
                    text = text + addlink % (addtext, addcluster)
                    addtext = u''

                if i > 5000:
                    break
            else:
                failedtext = failedtext + u'* [https://rkd.nl/explore/images/%(id)s %(id)s] -  %(invnum)s - %(title_nl)s - %(title_en)s' % rkdimageid
                if rkdimageid['id'] in allimages.keys():
                    failedtext = failedtext + u' -> Id already in use on {{Q|%s}}\n' % allimages[rkdimageid['id']]
                else:
                    failedtext = failedtext + u'\n'

    # Add the last link if needed
    if addtext:
        text = text + addlink % (addtext, i % addcluster)

    text = text + u'\n== No matches found ==\n' + failedtext
    text = text + u'\n[[Category:User:Multichill]]'
    repo = pywikibot.Site().data_repository()

    page = pywikibot.Page(repo, title=pageTitle)
    summary = u'RKDimages to link'
    page.put(text, summary)

    return result

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
                            u'replacements' : [(u'^(\d+)$', u'A \\1'),],
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
                               u'replacements' : [],
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
                              u'replacements' : [],
                              u'pageTitle' : u'User:Multichill/National Gallery RKD to match',
                              },
                u'Q1471477' : { u'collectienaam' : u'Koninklijk Museum voor Schone Kunsten Antwerpen',
                              u'replacements' : [],
                              u'pageTitle' : u'User:Multichill/KMSKA RKD to match',
                              },
                u'Q2874177' : { u'collectienaam' : u'Dordrechts Museum',
                              u'replacements' : [],
                              u'pageTitle' : u'User:Multichill/Dordrechts Museum RKD to match',
                              },
                u'Q2098586' : { u'collectienaam' : u'Stedelijk Museum De Lakenhal',
                              u'replacements' : [],
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

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-collectionid:'):
            if len(arg) == 14:
                collectionid = pywikibot.input(
                        u'Please enter the collectionid you want to work on:')
            else:
                collectionid = arg[14:]

    if collectionid and collectionid in sources.keys():
        worksources = [collectionid, ]
    else:
        worksources = sources.keys()

    for collectionid in worksources:
        suggestion = processCollection(collectionid,
                                       sources[collectionid][u'collectienaam'],
                                       sources[collectionid][u'replacements'],
                                       sources[collectionid][u'pageTitle'])
        suggestions = suggestions + suggestion

    with open('/tmp/rkd_images_suggestions.txt', u'wb') as txt:
        txt.write(suggestions)
        txt.close()

if __name__ == "__main__":
    main()
