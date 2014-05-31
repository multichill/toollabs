from dbfpy import dbf
import sys, time
import wikipedia as pywikibot
import config
import geo_helper

def procesDB(db):
    #db = dbf.Dbf('Listed_Buildings.dbf', readOnly=1)
    #dbf1.openFile('Listed_Buildings.dbf', readOnly=1)
    #print db.fieldNames()

    #fields = dict()
    #fields[u'HBNUM'] = set()
    #fields[u'COUNAME']
    #fields[u'PARBUR']

    countyMappings = {
        u'ABERDEEN, CITY OF' : u'Aberdeen',
        u'ABERDEENSHIRE' : u'Aberdeenshire',
        u'ANGUS' : u'Angus',
        u'ARGYLL AND BUTE' : u'Argyll and Bute',
        u'CLACKMANNAN' : u'Clackmannanshire',
        u'DUMFRIES AND GALLOWAY' : u'Dumfries and Galloway',
        u'DUNDEE, CITY OF' : u'Dundee',
        u'EAST AYRSHIRE' : u'East Ayrshire',
        u'EAST DUNBARTONSHIRE' : u'East Dunbartonshire',
        u'EAST LOTHIAN' : u'East Lothian',
        u'EAST RENFREWSHIRE' : u'East Renfrewshire',
        u'EDINBURGH, CITY OF' : u'Edinburgh',
        u'FALKIRK' : u'Falkirk (council area)',
        u'FIFE' : u'Fife',
        u'GLASGOW, CITY OF' : u'Glasgow',
        u'HIGHLAND' : u'Highland (council area)',
        u'INVERCLYDE' : u'Inverclyde',
        u'MIDLOTHIAN' : u'Midlothian',
        u'MORAY' : u'Moray',
        u'NORTH AYRSHIRE' : u'North Ayrshire',
        u'NORTH LANARKSHIRE' : u'North Lanarkshire',
        u'ORKNEY ISLANDS' : u'Orkney',
        u'PERTH AND KINROSS' : u'Perth and Kinross',
        u'RENFREWSHIRE' : u'Renfrewshire',
        u'SCOTTISH BORDERS' : u'Scottish Borders',
        u'SHETLAND ISLANDS' : u'Shetland Islands',
        u'SOUTH AYRSHIRE' : u'South Ayrshire',
        u'SOUTH LANARKSHIRE' : u'South Lanarkshire',
        u'STIRLING' : u'Stirling (council area)',
        u'WEST DUNBARTONSHIRE' : u'West Dunbartonshire',
        u'WEST LOTHIAN' : u'West Lothian',
        u'WESTERN ISLES' : u'Western Isles',
    }
    
    locations = {}
    hbnums = set()
    counties = set()
    #parburs = []
    for record in db:
        recorddict = record.asDict()
        if not recorddict[u'HBNUM'] in hbnums:
            counties.add(recorddict[u'COUNAME'])
            #parburs.append(recorddict[u'PARBUR'])
            if not (recorddict[u'COUNAME'], recorddict[u'PARBUR']) in locations:
                locations[(recorddict[u'COUNAME'], recorddict[u'PARBUR'])] = []
            hbnums.add(recorddict[u'HBNUM'])

            locations[(recorddict[u'COUNAME'], recorddict[u'PARBUR'])].append({
                u'hbnum' : recorddict[u'HBNUM'],
                u'name' : recorddict[u'ADDRESS'],
                u'category' : recorddict[u'CATEGORY'],
                u'date' : recorddict[u'LISTDATE1'],
                u'x' : recorddict[u'X'],
                u'y' : recorddict[u'Y']
                })

    shortest = 100
    longest = 0

    locationnames = []
    
    for (county, parbur) in locations:
        items = len(locations[(county, parbur)])
        if items > 10 and items < 20 or True:
            print u'%s - %s - %s' % (county, parbur, items)
            locationnames.append(parbur.title() + u', ' + countyMappings[county].replace(u' (council area)', u''))
            if items < shortest:
                shortest = items
            if items > longest:
                longest = items

    print u'Shortest list is %s items' % shortest
    print u'Longest list is %s items' % longest
    print u'Total numer of lists: %s' % len(locations)
    print u'Number of counties: %s'% len(counties)

    for county in sorted(counties):
        print county

    for locationname in sorted(locationnames):
        print u'*[[' + locationname + u']]' 
    #for parbur in sorted(parburs):
    #    print parbur

    #for key in sorted(countyMappings):
    #    name = countyMappings[key].replace(u' (council area)', u'')
    #    print u'* [[List of listed buildings in %s]]' % (name, )

    for countycaps in sorted(countyMappings):
        print u'------------------------------'
        countyarticle = countyMappings[countycaps]
        countytitle = countyMappings[countycaps].replace(u' (council area)', u'')
        print u'This is a list of [[listed building#Scotland|listed building]]s in [[%s|%s]]. The list is split out by [[List of civil parishes in Scotland|parish]].' % (countyarticle, countytitle)
        print u''
        items = []
        for county, parbur in locations:
            if countycaps == county:
                listTitle = u'List of listed buildings in %s, %s' % (parbur.title(), countytitle) 
                items.append(u'* [[List of listed buildings in %s, %s]]' % (parbur.title(), countytitle))
                
                maxLength = 150
                
                if len(locations[(county, parbur)]) > maxLength:
                    n =0
                    for i in xrange(0, len(locations[(county, parbur)]), maxLength):
                        n = n + 1
                        createListPage(listTitle + u'/%s' %(n,) , parbur.title(), countyarticle, countytitle, locations[(county, parbur)][i:i+maxLength])
                else:
                    createListPage(listTitle, parbur.title(), countyarticle, countytitle, locations[(county, parbur)])
        for item in sorted(items):
            print item

        print u''
        print u'{{Commons category|Listed buildings in %s}}' % (countyarticle,)
        print u'{{Navigation lists of listed buildings in Scotland}}'
        print u'[[Category:Lists of listed buildings in Scotland|%s]]' % (countyarticle,)
        print u'[[Category:Lists of listed buildings in %s| ]]' % (countyarticle,)           
                            
                
    #    name = countyMappings[key].replace(u' (council area)', u'')
    #    print u'* [[List of listed buildings in %s]]' % (name, )
        
    # Get the county article and county name
    # Get the parish article and parish name
    '''
    print u'This is a \'\'\'list of [[listed building#Scotland|listed building]]s in the [[List of civil parishes in Scotland|parish]] [[Uig, Lewis|Uig]]\'\'\', [[Western Isles]], [[Scotland]].'
    print u''
    
    examplelist = locations[(u'WESTERN ISLES', u'UIG')]

    print u'{{HB Scotland header|county=%s|parbur=Uig, Lewis}}' % countyMappings[u'WESTERN ISLES']
    for item in examplelist:
        print u'{{HB Scotland row'
        print u'|hbnum = %s' % item[u'hbnum']
        #print u'|county = %s' % u'PERTH AND KINROSS'
        #print u'|parbur = %s' %  u'TIBBERMORE'
        print u'|name = %s' % item[u'name'].title().replace(u'\'S', u'\'s')
        print u'|notes = ' #% item[u'name']
        print u'|category = %s' % item[u'category']
        print u'|date = %s' % item[u'date']
        #print u'|x = %s' % item[u'x']
        #print u'|y = %s' % item[u'y']
        (lat_dec, long_dec) = geo_helper.turn_eastingnorthing_into_osgb36(item[u'x'],item[u'y'])
        (lat, lon, height) = geo_helper.turn_osgb36_into_wgs84(lat_dec, long_dec,0)
        print u'|lat = %s' % lat
        print u'|lon = %s' % lon
        print u'|image = ' 
        print u'}}'

    print u'|}'
    print u''
    print u'== See also =='
    print u'* [[List of listed buildings in Western Isles]]'
    print u''
    print u'== References =='
    print u'* All entries, addresses and coordinates are based on data from [http://hsewsf.sedsh.gov.uk Historic Scotland]. This data falls under the [http://www.nationalarchives.gov.uk/doc/open-government-licence/ Open Government Licence]'
    print u''
    print u'[[Category:Lists of listed buildings in Western Isles]]'                   
        
    '''
    #for fldName in db.fieldNames():
    #     print '%s:\t %s'%(fldName, record[fldName])

    '''
PERTH AND KINROSS - TIBBERMORE
                print u'{{HB Scotland row'
                print u'|hbnum = %s' % recorddict[u'HBNUM']
                print u'|county = %s' % recorddict[u'COUNAME']
                print u'|parbur = %s' % recorddict[u'PARBUR']
                print u'|address = %s' % recorddict[u'ADDRESS']
                print u'|category = %s' % recorddict[u'CATEGORY']
                print u'|date = %s' % recorddict[u'LISTDATE1']
                print u'|x = %s' % recorddict[u'X']
                print u'|y = %s' % recorddict[u'Y']
                print u'|}}'
    db.reportOn()
    print 'sample records:'
    for i1 in range(min(3,len(dbf1))):
        rec = dbf1[i1]
        for fldName in dbf1.fieldNames():
            print '%s:\t %s'%(fldName, rec[fldName])
        print
    dbf1.close()
    '''
def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]


def createListPage(listTitle, parbur, countyarticle, countytitle, items):
    todo = [
        u'Aberdeen',
        u'Dundee',
        u'Edinburgh',
        u'Glasgow',
        ]
    if not countyarticle in todo:
        return

    if not parbur in todo:
        return
    
    #countyarticle = u'Aberdeen'
    #countytitle = u'Aberdeen'
    listTitle = listTitle.replace(u', %s/' % (countyarticle,), u'/')
    text = u''

    text = text + u'This is a list of [[listed building#Scotland|listed building]]s in the [[List of civil parishes in Scotland|parish]] of '
    if countyarticle == parbur:
        text = u'This is a list of [[listed building#Scotland|listed building]]s in [[%s]], [[Scotland]].\n' % (parbur)
        text = text + u'{{KML}}\n'
        text = text + u'== List ==\n'
        text = text + u'{{HB Scotland header|county=[[%s]]|parbur=[[%s]]}}\n' % (countyarticle, parbur)        
    elif countyarticle == countytitle:
        text = text + u'[[%s, %s|%s]] in [[%s]], [[Scotland]].\n' % (parbur, countytitle, parbur, countyarticle)
        text = text + u'{{KML}}\n'
        text = text + u'== List ==\n'
        text = text + u'{{HB Scotland header|county=[[%s]]|parbur=[[%s, %s|%s]]}}\n' % (countyarticle, parbur, countytitle, parbur)
    else:
        text = text + u'[[%s, %s|%s]] in [[%s|%s]], [[Scotland]].\n' % (parbur, countytitle, parbur, countyarticle, countytitle)
        text = text + u'{{KML}}\n'
        text = text + u'== List ==\n'
        text = text + u'{{HB Scotland header|county=[[%s|%s]]|parbur=[[%s, %s|%s]]}}\n' % (countyarticle, countytitle, parbur, countytitle, parbur)

    for item in items:
        text = text + u'{{HB Scotland row\n'
        text = text + u'|hbnum = %s\n' % item[u'hbnum']
        #print item[u'name']
        try:
            name = item[u'name']
            name = name.title()
            name = name.replace(u'\'S', u'\'s')
            name = name.rstrip(u'.')
        except UnicodeDecodeError:
            name = u'{{UnicodeDecodeError}}'
        text = text + u'|name = %s\n' % name
        text = text + u'|notes = \n'
        text = text + u'|category = %s\n' % item[u'category']
        #text = text + u'|date = %s\n' % item[u'date']
        (lat_dec, long_dec) = geo_helper.turn_eastingnorthing_into_osgb36(item[u'x'],item[u'y'])
        (lat, lon, height) = geo_helper.turn_osgb36_into_wgs84(lat_dec, long_dec,0)
        text = text + u'|lat = %s\n' % round(lat, 6)
        text = text + u'|lon = %s\n' % round(lon, 6)
        text = text + u'|image = \n' 
        text = text + u'}}\n'

    text = text + u'|}\n'
    text = text + u'\n'
    text = text + u'== Key ==\n'
    text = text + u'{{Listed-Scotland}}\n'
    text = text + u'\n'
    text = text + u'== See also ==\n'
    text = text + u'* [[List of listed buildings in %s]]\n' % (countyarticle,)
    text = text + u'\n'
    text = text + u'== References ==\n'
    text = text + u'* All entries, addresses and coordinates are based on data from [http://hsewsf.sedsh.gov.uk Historic Scotland]. This data falls under the [http://www.nationalarchives.gov.uk/doc/open-government-licence/ Open Government Licence]\n'
    text = text + u'\n'
    text = text + u'{{Reflist}}\n'
    text = text + u'\n'
    text = text + u'[[Category:Lists of listed buildings in %s|%s]]\n' % (countyarticle, parbur)

    site = pywikibot.getSite(u'en', u'wikipedia')
    page = pywikibot.Page(site, listTitle)
    
    if not page.exists():
        comment = u'Creating new list of listed buildings'
        #pywikibot.output(listTitle)
        pywikibot.showDiff(u'', text)
        page.put(text, comment)
        time.sleep(10)
    

    #print text
    
def usage():
    pywikibot.output(u'Scotland_lists.py -db:<dblocation>')


def main(*args):
    dblocation = u''
    for arg in pywikibot.handleArgs(*args):
        if arg.startswith('-db:'):
            if len(arg) == 4:
                dblocation = pywikibot.input(
                    u'Please enter the location of the database')
            else:
                dblocation = arg[4:]
    if not dblocation:
        usage()
        return
        
    db = dbf.Dbf(dblocation, readOnly=1)
    procesDB(db)
    

if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
