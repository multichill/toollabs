#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to match RKD images on Wikidata with RKD images and make some sort of easy result

"""
import pywikibot
import requests
import pywikibot.data.sparql

        
def getArtistsGenerator():
    '''
    Generate a bunch of artists from RKD.
    It returns tuples of title and description to be imported to http://tools.wmflabs.org/mix-n-match/
    ''' 
    url = 'http://api-rkd.picturae.pro/api/record/artists/%d?format=json'


    for i in range(1, 335560):
        
        apiPage = urllib.urlopen(url % (i,))
        apiData = apiPage.read()
        jsonData = json.loads(apiData)
        if jsonData.get(u'response'):
            docs = jsonData.get(u'response').get('docs')[0]
            
            title = docs.get('kunstenaarsnaam')
            descriptions = []

            fields = [u'nationaliteit',
                      u'kwalificatie',
                      u'geboortedatum_begin',
                      u'geboortedatum_eind',
                      u'geboorteplaats',
                      u'sterfdatum_begin',
                      u'sterfdatum_eind',
                      u'sterfplaats',
                     ]

            for field in fields:
                if docs.get(field):
                    if isinstance(docs.get(field), list):
                        descriptions.extend(docs.get(field))
                    elif not docs.get(field) == descriptions[-1]:
                        # Remove dupes.
                        descriptions.append(docs.get(field))

            description = u'/'.join(descriptions)

            print title
            print description

            yield (title, description)


def rkdImagesOnWikidata(collectionid):
    '''
    Just return all the RKD images as a dict
    :return: Dict
    '''
    result = {}
    sq = pywikibot.data.sparql.SparqlQuery()
    query = u'SELECT ?item ?id WHERE { ?item wdt:P350 ?id . ?item wdt:P195 wd:%s }' % (collectionid,)
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
    query = u'SELECT ?item ?id WHERE { ?item wdt:P217 ?id . ?item wdt:P195 wd:%s }' % (collectionid,)
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result

def rkdImagesGenerator(currentimages, invnumbers, collection=u''):
    '''

    :param currentimages:
    :param collection:
    :return:
    '''
    # https://api.rkd.nl/api/search/images?filters[collectienaam]=Rijksmuseum&format=json&start=100&rows=50
    start = 0
    rows = 50
    basesearchurl = u'https://api.rkd.nl/api/search/images?filters[collectienaam]=%s&format=json&start=%s&rows=%s'
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
                for collectie in rkdimage.get(u'collectie'):
                    if collectie.get('collectienaam') == collection:
                        invnum = collectie.get('inventarisnummer')
                        if invnum:
                            if (invnum.startswith(u'A ') or invnum.startswith(u'C ')):
                                invnum = u'SK-' + invnum.replace(u' ', u'-')
                            elif invnum.startswith(u'A'):
                                invnum = invnum.replace(u'A', u'SK-A-')
                            elif invnum.startswith(u'C'):
                                invnum = invnum.replace(u'C', u'SK-C-')
                        imageinfo[u'invnum'] = invnum
                        imageinfo[u'startime'] = collectie.get('begindatum_in_collectie')
                        if invnum in invnumbers:
                            pywikibot.output(u'Found a Wikidata id!')
                            imageinfo[u'qid'] = invnumbers.get(invnum)



                yield imageinfo



def main():

    """
    collectienaam = u'Rijksmuseum'
    collectionid = u'Q190804'
    urlformat = u'https://www.rijksmuseum.nl/nl/collectie/%(invnum)s'
    pageTitle = u'User:Multichill/Rijksmuseum RKD to match'

    """
    collectienaam = u'Koninklijk Kabinet van Schilderijen Mauritshuis'
    collectionid = u'Q221092'
    urlformat = u'http://resolver.kb.nl/resolve?urn=urn:gvn:MAU01:%(invnum)04d'
    pageTitle = u'User:Multichill/Mauritshuis RKD to match'

    """
    collectienaam = u'Amsterdam Museum'
    collectionid = u'Q1820897'
    urlformat = u'http://resolver.kb.nl/resolve?urn=urn:gvn:MAU01:%(invnum)04d' # https://www.rijksmuseum.nl/nl/collectie/%(invnum)s
    """

    currentimages = rkdImagesOnWikidata(collectionid)
    invnumbers = paintingsInvOnWikidata(collectionid)
    #print invnumbers

    #print currentimages
    gen = rkdImagesGenerator(currentimages, invnumbers, collection=collectienaam)

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
            invnum = rkdimageid.get('invnum')
            if not invnum:
                rkdimageid[u'url'] = None
            else:
                if invnum.isdigit():
                    invnum = int(invnum)
                try:
                    rkdimageid[u'url'] = urlformat % { u'invnum' : invnum }
                except TypeError:
                    rkdimageid[u'url'] = None


            if rkdimageid.get(u'qid'):
                text = text + u'* {{Q|%(qid)s}} - [https://rkd.nl/explore/images/%(id)s %(id)s] - [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
                addtext = addtext + u'%(qid)s\tP350\t"%(id)s"\n' % rkdimageid
                i = i + 1
                if not i % addcluster:
                    text = text + addlink % (addtext, addcluster)
                    addtext = u''

                if i > 5000:
                    break
            else:
                failedtext = failedtext + u'* [https://rkd.nl/explore/images/%(id)s %(id)s] -  [%(url)s %(invnum)s] - %(title_nl)s - %(title_en)s\n' % rkdimageid
    text = text + u'\n== No matches found ==\n' + failedtext
    text = text + u'\n[[Category:User:Multichill]]'
    #print text
    repo = pywikibot.Site().data_repository()

    page = pywikibot.Page(repo, title=pageTitle)
    summary = u'RKDimages to link'
    page.put(text, summary)

    #artistGen = getArtistsGenerator()
    #for artist in artistGen:
    #    # Do something here
    #    pass
    

if __name__ == "__main__":
    main()
