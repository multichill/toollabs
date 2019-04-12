#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the National Gallery in London

Using the data from http://cima.ng-london.org.uk/collection/ . This uses an API that can be queried:
* All paintings http://cima.ng-london.org.uk/collection/search.php?what=tiles&sortby=ObjectAlphaSort&start_gx=0&start_gy=0&end_gx=60&end_gy=60&g_cols=51&no_ims=2609&grid_max_x=6144&grid_max_y=6144&gxoffset=98&gyoffset=38&crop=false&sqllimit=%20AND%20FileGroup_id%20in%20(14)%20&whichdb=externalIIP&whichtable=Image&newset=false
* Info for a single painting http://cima.ng-london.org.uk/collection/search.php?what=details&val=252&crop=false&sqllimit=%20AND%20FileGroup_id%20in%20(14)%20&whichdb=externalIIP&whichtable=Image&sortby=ObjectAlphaSort
* Get the URL for a single painting: http://www.nationalgallery.org.uk/cgi-bin/WebObjects.dll/CollectionPublisher.woa/wa/work?workNumber=NG666 - That stopped working

Fixed up the bot to squeeze out the last data.

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import HTMLParser


def getNationalGalleryGenerator():
    """
    Generator to return National Gallery
    * Grab all paintings
    * Loop over the regex and fetch single one
    * Use converter to find the url
    
    """
    allUrl = u'http://cima.ng-london.org.uk/collection/search.php?what=tiles&sortby=ObjectAlphaSort&start_gx=0&start_gy=0&end_gx=60&end_gy=60&g_cols=51&no_ims=2609&grid_max_x=6144&grid_max_y=6144&gxoffset=98&gyoffset=38&crop=false&sqllimit=%20AND%20FileGroup_id%20in%20(14)%20&whichdb=externalIIP&whichtable=Image&newset=false'
    itemRegex = u'new Array \((\d+)'

    htmlparser = HTMLParser.HTMLParser()

    allPage = requests.get(allUrl)
    allText = allPage.text
    itemmatches = re.finditer(itemRegex, allText)

    idlist = []

    # Same ID is returned multiple times so we have to remove the duplicates
    for itemmatch in itemmatches:
        idlist.append(itemmatch.group(1))

    # If a ' is in a field this breaks
    fieldRegex = u'\'([^\']+)\' : \'([^\']+)\''

    idredirecturl = u'http://www.nationalgallery.org.uk/cgi-bin/WebObjects.dll/CollectionPublisher.woa/wa/work?workNumber=%s'

    for apiid in list(set(idlist)):
        apiurl = u'http://cima.ng-london.org.uk/collection/search.php?what=details&val=%s&crop=false&sqllimit=%%20AND%%20FileGroup_id%%20in%%20(14)%%20&whichdb=externalIIP&whichtable=Image&sortby=ObjectAlphaSort' % (apiid,)
        print apiurl
        apiPage = requests.get(apiurl)
        apiText = apiPage.text

        sourcemetadata = {}
        metadata = {}
        
        firstline = apiText.split(u'\n', 1)[0]

        fieldmatches = re.finditer(fieldRegex, firstline)
        for fieldmatch in fieldmatches:
            sourcemetadata[fieldmatch.group(1)] = fieldmatch.group(2)

        for field in sorted(sourcemetadata):
            print(u'* %s - %s' % (field, sourcemetadata.get(field)))
        #print sourcemetadata
        
        metadata['collectionqid'] = u'Q180788'
        metadata['collectionshort'] = u'National Gallery'
        metadata['locationqid'] = u'Q180788'
            
        #No need to check, I'm actually searching for paintings. See only one mistake
        metadata['instanceofqid'] = u'Q3305213'

        metadata['id'] = sourcemetadata['ObjectNumber']
        metadata['idpid'] = u'P217'
        # Doesn't work anymore
        #paintingpage = requests.get(idredirecturl % (sourcemetadata['ObjectNumber'],))
        #metadata[u'url'] = paintingpage.url
        metadata[u'refurl'] = apiurl

        metadata['title'] = { u'en' : htmlparser.unescape(sourcemetadata['ObjectShortTitle']),
                                  }

        # Might have an encoding problem here. Keep an eye out.
        name = htmlparser.unescape(sourcemetadata['ObjectAlphaSort'])

        # We need to normalize the name
        if u',' in name:
            (surname, sep, firstname) = name.partition(u',')
            name = u'%s %s' % (firstname.strip(), surname.strip(),)
        metadata['creatorname'] = name
                
        metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                    u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                    }

        # Inception
        dateregex = u'^(\d\d\d\d)$'
        datecircaregex = u'about (\d\d\d\d)$'
        begindateregex = u'^(\d\d\d\d)-\d\d-\d\d$'
        enddateregex = u'^(\d\d\d\d)-\d\d-\d\d$'

        datematch = re.match(dateregex, sourcemetadata.get('ObjectDisplayDate'))
        datecircamatch = re.match(datecircaregex, sourcemetadata.get('ObjectDisplayDate'))
        datebeginmatch = re.match(begindateregex, sourcemetadata.get('ObjectDateBegin'))
        dateendmatch = re.match(enddateregex, sourcemetadata.get('ObjectDateEnd'))

        if datematch:
            metadata['inception'] = datematch.group(1)
        elif datecircamatch:
            metadata['inception'] = datecircamatch.group(1)
            metadata['inceptioncirca'] = True
        elif datebeginmatch and dateendmatch:
            metadata['inceptionstart'] = int(datebeginmatch.group(1))
            metadata['inceptionend'] = int(dateendmatch.group(1))

        # If the credit line ends with a year, we'll take it
        if sourcemetadata.get(u'ObjectCreditLine'):
            acquisitiondateregex = u'^.+, (\d\d\d\d)$'
            acquisitiondatematch = re.match(acquisitiondateregex, sourcemetadata.get(u'ObjectCreditLine'))
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)

        if sourcemetadata.get('ObjectMedium')==u'Oil on canvas':
            metadata['medium'] = u'oil on canvas'

        # Dimensions
        if sourcemetadata.get('ObjectDimensions'):
            dimensiontext = sourcemetadata.get('ObjectDimensions')
            regex_2d = u'^\s*(?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) cm$'
            regex_3d = u'^\s*(?P<height>\d+(\.\d+)?) x (?P<width>\d+(.\d+)?) x (?P<depth>\d+(,\d+)?) cm$'
            match_2d = re.match(regex_2d, dimensiontext)
            match_3d = re.match(regex_3d, dimensiontext)
            if match_2d:
                metadata['heightcm'] = match_2d.group(u'height')
                metadata['widthcm'] = match_2d.group(u'width')
            elif match_3d:
                metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')
            
        yield metadata
    
def main():
    dictGen = getNationalGalleryGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    artDataBot.run()

if __name__ == "__main__":
    main()
