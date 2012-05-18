from dbfpy import dbf
import geo_helper

def demo1():
    db = dbf.Dbf('Listed_Buildings.dbf', readOnly=1)
    #dbf1.openFile('Listed_Buildings.dbf', readOnly=1)
    #print db.fieldNames()

    #fields = dict()
    #fields[u'HBNUM'] = set()
    #fields[u'COUNAME']
    #fields[u'PARBUR']
    locations = {}
    hbnums = set()
    counties = set()
    for record in db:
        recorddict = record.asDict()
        if not recorddict[u'HBNUM'] in hbnums:
            counties.add(recorddict[u'COUNAME'])
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

    for (county, parbur) in locations:
        items = len(locations[(county, parbur)])
        if items > 10 and items < 20:
            print u'%s - %s - %s' % (county, parbur, items)
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

    countyMappings = {
        u'ABERDEEN, CITY OF' : u'City of Aberdeen',
        u'ABERDEENSHIRE' : u'Aberdeenshire',
        u'ANGUS' : u'Angus',
        u'ARGYLL AND BUTE' : u'Argyll and Bute',
        u'CLACKMANNAN' : u'Clackmannanshire',
        u'DUMFRIES AND GALLOWAY' : u'Dumfries and Galloway',
        u'DUNDEE, CITY OF' : u'City of Dundee',
        u'EAST AYRSHIRE' : u'East Ayrshire',
        u'EAST DUNBARTONSHIRE' : u'East Dunbartonshire',
        u'EAST LOTHIAN' : u'East Lothian',
        u'EAST RENFREWSHIRE' : u'East Renfrewshire',
        u'EDINBURGH, CITY OF' : u'City of Edinburgh',
        u'FALKIRK' : u'Falkirk (council area)',
        u'FIFE' : u'Fife',
        u'GLASGOW, CITY OF' : u'City of Glasgow',
        u'HIGHLAND' : u'Highland (council area)',
        u'INVERCLYDE' : u'Inverclyde',
        u'MIDLOTHIAN' : u'Midlothian',
        u'MORAY' : u'Moray',
        u'NORTH AYRSHIRE' : u'North Ayrshire',
        u'NORTH LANARKSHIRE' : u'North Lanarkshire',
        u'ORKNEY ISLANDS' : u'Orkney Islands',
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
        
    # Get the county article and county name
    # Get the parish article and parish name

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

if __name__ == "__main__":
    try:
        demo1()
    finally:
        print "done"

