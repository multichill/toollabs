#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Tool to compare a csv file with the catalogs with what we have on Wikidata.
Report the differences

Result at https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Creator/Vincent_van_Gogh

"""
import pywikibot
import requests
import pywikibot.data.sparql
import re
import datetime
import csv

def createCatalogTables():
    '''
    Make three catalog tables
    '''
    bothtable = {}
    ftable = {}
    jhtable = {}

    result = {}
    # Need to use the long version here to get all ranks
    query = u"""SELECT DISTINCT ?item ?fcat ?jhcat WHERE {
  ?item p:P170 ?creatorstatement .
  ?creatorstatement ps:P170 wd:Q5582 .
  ?item wdt:P31 wd:Q3305213 .
  #MINUS { ?item wdt:P31 wd:Q15727816 }
  OPTIONAL { ?item p:P528 ?fcatstatement .
            ?fcatstatement ps:P528 ?fcat .
            ?fcatstatement pq:P972 wd:Q17280421 }
  OPTIONAL { ?item p:P528 ?jhcatstatement .
            ?jhcatstatement ps:P528 ?jhcat .
            ?jhcatstatement pq:P972 wd:Q19833315 }

} LIMIT 5003"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        fcat = None
        jhcat = None
        if resultitem.get('fcat'):
            fcat = resultitem.get('fcat')
            ftable[fcat] = qid
        if resultitem.get('jhcat'):
            jhcat = resultitem.get('jhcat')
            jhtable[jhcat] = qid
        if fcat or jhcat:
            bothtable[(fcat,jhcat)] = qid

    return (bothtable, ftable, jhtable)

def itemsMissingInfo():
    """
    Make a list of items that need some info
    """
    result = []
    # Need to use the long version here to get all ranks
    query = u"""SELECT ?item WHERE {
  ?item wdt:P31 wd:Q3305213 . # Only paintings
  ?item wdt:P170 wd:Q5582 . # By Vincent van Gogh
  MINUS { ?item wdt:P1071 [] . # Location where it was made
          ?item wdt:P571 [] . # When it was made
          ?item wdt:P195 [] . # Has a collection, could add more here later like width and height
          ?item rdfs:label ?label .
         FILTER(LANG(?label) = "en").
         }
} LIMIT 1004"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result.append(qid)

    return result

def vggalleryPaintingGenerator():

    urls = [u'http://www.vggallery.com/painting/main_ac.htm',
            u'http://www.vggallery.com/painting/main_df.htm',
            u'http://www.vggallery.com/painting/main_gi.htm',
            u'http://www.vggallery.com/painting/main_jl.htm',
            u'http://www.vggallery.com/painting/main_mo.htm',
            u'http://www.vggallery.com/painting/main_pr.htm',
            u'http://www.vggallery.com/painting/main_su.htm',
            u'http://www.vggallery.com/painting/main_vz.htm',
            ]

    pageurls = []
    pageurlregex = u'\<tr\>\<td valign\=top\>\<a href\=\"(?P<itemurl>[^\"]+)\"\>'
    itemregex = u'\<tr\>\<td valign\=top\>\<a href\=\"(?P<itemurl>[^\"]+)\"\>\<b\>(?P<title>[^\<]+)(\<(\/)?(a|b|td)\>)*[\t\s\r\n]*\<\/td\>\<td valign\=top\>(?P<locationdate>[^\<]+)[\t\s\r\n]*\<\/td\>\<td valign\=top\>(?P<collection>[^\<]+)[\t\s\r\n]*\<\/td><td valign=top>(?P<fcat>[^\<]+)[\t\s\r\n]*\<\/td\>\<td valign\=top\>(?P<jhcat>[^\<]+)[\t\s\r\n]*\<\/td\>\<\/tr\>'

    for url in urls:
        i = 0
        #print url
        listpage = requests.get(url, verify=False)
        matches = re.finditer(itemregex, listpage.text)
        pageurlmatches = re.finditer(pageurlregex, listpage.text)

        # Fill up all the matches
        for pageurlmatch in pageurlmatches:
            pageurls.append(u'http://www.vggallery.com/painting/%s' % (pageurlmatch.group(u'itemurl'),))

        for match in matches:
            i = i + 1
            metadata = {}
            metadata[u'url'] = u'http://www.vggallery.com/painting/%s' % (match.group(u'itemurl'),)
            pageurls.remove(u'http://www.vggallery.com/painting/%s' % (match.group(u'itemurl'),))
            # FIXME: HTML excape
            metadata[u'title'] = match.group(u'title').strip()
            metadata[u'locationdate'] = match.group(u'locationdate').strip()
            metadata[u'collection'] = match.group(u'collection').strip()
            if match.group(u'fcat').strip()==u'None':
                metadata[u'fcat'] = None
            else:
                metadata[u'fcat'] = u'F%s' % (match.group(u'fcat').strip(),)

            if match.group(u'jhcat').strip()==u'None':
                metadata[u'jhcat'] = None
            else:
                metadata[u'jhcat'] = u'JH%s' % (match.group(u'jhcat').strip(),)
            #print match.group(1)
            yield metadata

    print u'The left over urls are:'
    print pageurls

def processItem(qid, metadata):
    repo = pywikibot.Site().data_repository()
    #item = None
    item = pywikibot.ItemPage(repo, title=qid)
    addLocationDate(repo, item, metadata)
    addCollection(repo, item, metadata)
    addLabel(repo, item, metadata)

    # Add title
    # Add description
    # Add collection

def addLocationDate(repo, item, metadata):

    locations = { u'Arles' : u'Q48292',
                  u'Auvers-sur-Oise' : u'Q212406',
                  u'Drente' : u'Q772',
                  u'Nieuw-Amsterdam' : u'Q743632',
                  u'Nuenen' : u'Q153516',
                  u'Paris' : u'Q90',
                  u'Saint-Rémy' : u'Q221507',
                  u'Scheveningen' : u'Q837211',
                  u'The Hague' : u'Q36600',
                  }
    #print item.title()
    #print metadata
    data = item.get()
    claims = data.get('claims')
    (location, sep, date) = metadata.get(u'locationdate').partition(u':')
    if u'P1071'not  in claims and location in locations:
        locationitem = pywikibot.ItemPage(repo, title=locations.get(location))
        newclaim = pywikibot.Claim(repo, u'P1071')
        newclaim.setTarget(locationitem)
        item.addClaim(newclaim)
        addReference(repo, item, newclaim, metadata.get(u'url'))

    dateregex = u'^(.+), (\d\d\d\d)$'
    datematch = re.match(dateregex, date.strip())

    months = { u'January' : 1,
               u'February' : 2,
               u'March' : 3,
               u'April' : 4,
               u'May' : 5,
               u'June' : 6,
               u'July' : 7,
               u'August' : 8,
               u'September' : 9,
               u'October' : 10,
               u'November' : 11,
               u'December' : 12,
               }

    if datematch and u'P571' not in claims:
        partofyear = datematch.group(1)
        year = datematch.group(2)

        newdate = False

        if partofyear in months:
            month = months.get(partofyear)
            newdate = pywikibot.WbTime(year=year, month=month)
        elif partofyear==u'Spring':
            newdate = pywikibot.WbTime(year=year, month=5, day=6, precision=9)
        elif partofyear==u'Summer':
            newdate = pywikibot.WbTime(year=year, month=8, day=6, precision=9)
        elif partofyear==u'Autumn':
            newdate = pywikibot.WbTime(year=year, month=11, day=6, precision=9)

        if newdate:
            newclaim = pywikibot.Claim(repo, u'P571')
            newclaim.setTarget(newdate)
            item.addClaim(newclaim)
            addReference(repo, item, newclaim, metadata[u'url'])
        else:
            print u'Could not add the date %s %s to %s' % (partofyear, year, item.title(), )

def addCollection(repo, item, metadata):

    collections = { u'Private collection' : u'Q768717',
                    u'Otterlo, Kröller-Müller Museum' : u'Q1051928',
                    u'The Hague, Haags Gemeentemuseum' : u'Q1499958',
                    u'Den Bosch, Noordbrabants Museum' : u'Q12013217',
                    }
    data = item.get()
    claims = data.get('claims')
    collection = metadata.get(u'collection')
    if u'P195'not in claims:
        if collection in collections:
            collectionitem = pywikibot.ItemPage(repo, title=collections.get(collection))
            newclaim = pywikibot.Claim(repo, u'P195')
            newclaim.setTarget(collectionitem)
            item.addClaim(newclaim)
            addReference(repo, item, newclaim, metadata.get(u'url'))
        elif collection not in collections:
            print u'Did not find the collection %s for %s' % (collection, item.title(), )

def addLabel(repo, item, metadata):
    data = item.get()
    labels = data.get('labels')

    summary = u'Adding missing label for Vincent Van Gogh painting bassed on %s' % (metadata.get(u'url'),)
    if not labels.get(u'en') and metadata.get(u'title'):
        labels['en'] = metadata.get(u'title')
        try:
            item.editLabels(labels, summary=summary)
        except pywikibot.exceptions.APIError:
            pywikibot.output(u'Failed to add %s to %s' % (metadata.get(u'title'), item.title(),))
            pass

def addReference(repo, item, newclaim, url):
    """
    Add a reference with a retrieval url and todays date
    """
    pywikibot.output('Adding new reference claim to %s' % item)
    refurl = pywikibot.Claim(repo, u'P854') # Add url, isReference=True
    refurl.setTarget(url)
    refdate = pywikibot.Claim(repo, u'P813')
    today = datetime.datetime.today()
    date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
    refdate.setTarget(date)
    newclaim.addSources([refurl, refdate])

def concordantieGenerator():
    with open('/home/mdammers/Documents/Van_Gogh_concordantie.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            item = { 'F' : '',
                     'JH' : '',
                     'W' : '',
                     'Q' : '',
                     }
            if row.get('F'):
                if row.get('F')==u'-':
                    item['F']=None
                else:
                    item['F']=u'F%s' % (row.get('F'),)
            if row.get('JH'):
                if row.get('JH')==u'-':
                    item['JH']=None
                else:
                    item['JH']=u'JH%s' % (row.get('JH'),)
            item['W']=row.get('W')
            item['Q']=row.get('Q')
            yield item

def main(*args):

    total = 0
    matched = 0
    unmatched = 0
    bothtable, ftable, jhtable = createCatalogTables()
    print len(bothtable)
    print len(ftable)
    print len(jhtable)
    #print bothtable
    #print ftable
    #print jhtable
    #missingitems = itemsMissingInfo()

    qidsmatched = []

    for citem in concordantieGenerator():
        #if citem.get('F') and citem.get('JH'):
        qid = bothtable.get((citem.get('F'), citem.get('JH')))
        if qid:
            qidsmatched.append(qid)
        elif citem.get('Q'):
            qidsmatched.append(citem.get('Q'))
        else:
            print citem
            print ftable.get(citem.get('F'))
            print jhtable.get(citem.get('JH'))
        #print qid

        #print row

    for wditem in bothtable.values():
        if wditem not in qidsmatched:
            print wditem
    """
    #print bothtable
    for painting in vggalleryPaintingGenerator():
        total = total + 1
        #print painting
        if (painting.get(u'fcat'), painting.get(u'jhcat')) in bothtable:
            #pywikibot.output(u'Found a match')
            matched = matched + 1
            qid = bothtable.get((painting.get(u'fcat'), painting.get(u'jhcat')))
            #print u'%s\tP973\t"%s"' % (bothtable.get((painting.get(u'fcat'), painting.get(u'jhcat'))),
            #                           painting.get(u'url'))
            if qid in missingitems:
                processItem(qid, painting)
                #print u'Found %s to add something to' % (qid,)



        elif painting.get(u'fcat')in ftable:
            if painting.get(u'jhcat') in jhtable:
                pywikibot.output(u'Only F match: %s, but it collides with %s' % (ftable.get(painting.get(u'fcat')),
                                                                                 jhtable.get(painting.get(u'jhcat'))))
            else:
                pywikibot.output(u'Only F match: %s, no collision' % (ftable.get(painting.get(u'fcat')),))
            print painting
        elif painting.get(u'jhcat') in jhtable:
            if painting.get(u'fcat')in ftable:
                pywikibot.output(u'Only JH match: %s, but collides with %s' % (jhtable.get(painting.get(u'jhcat')),
                                                                               ftable.get(painting.get(u'fcat'))))
            else:
                pywikibot.output(u'Only JH match: %s, no collision' % (jhtable.get(painting.get(u'jhcat')),))
            print painting
        else:
            #pywikibot.output(u'No match found')
            #print painting
            unmatched = unmatched + 1
            #print u'CREATE'
            #print u'LAST\tLen\t"%s"' % (painting.get(u'title'),)
            #print u'LAST\tP31\tQ3305213'
            #print u'LAST\tP170\tQ5582'
            #print u'LAST\tP973\t"%s"' % (painting.get(u'url'),)
            #print u'LAST\tP528\t"%s"\tP972\tQ17280421' % (painting.get(u'fcat'),)
            #print u'LAST\tP528\t"%s"\tP972\tQ19833315' % (painting.get(u'jhcat'),)
            #print u'LAST\tDen\t"painting by Vincent van Gogh"'
            #print u'LAST\tDfr\t"peinture de Vincent van Gogh"'
            #print u'LAST\tDnl\t"schilderij van Vincent van Gogh"'
            #collection
            #location
            #datae
    """
    pywikibot.output(u'Worked on a total of %s paintings, %s matched, %s not matched' % (total, matched, unmatched))




if __name__ == "__main__":
    main()