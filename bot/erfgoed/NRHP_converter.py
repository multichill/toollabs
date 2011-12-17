#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
Tool to update lists like https://en.wikipedia.org/wiki/National_Register_of_Historic_Places_listings_in_Washington_County,_Nebraska to the new template based format

'''
import sys, time, warnings, traceback
import wikipedia, config, re, pagegenerators


def convertList(page):
    '''
    Convert a list of NRHP entries. Both headers and items will be converted.
    '''
    wikipedia.output(u'Working on %s' % page.title())
    
    text = page.get()
    try:
        newtext = convertHeaders(page, text)
        newtext = convertItems(page, newtext)
    except TypeError or AttributeError:
        wikipedia.output(u'One of the regexes failed at %s, skipping this page' % (page.title,))
        traceback.print_exc(file=sys.stdout)
        time.sleep(10)
        return u'Failed'

    if not text==newtext:
        wikipedia.showDiff(text, newtext)
        
        comment = u'Converting list to use [[Template:NRHP header]] and [[Template:NRHP row]]'

        #choice = wikipedia.inputChoice(u'Do you want to accept these changes?', ['Yes', 'No'], ['y', 'n'], 'n')
        choice = 'y'

        if choice == 'y':
            #DEBUG
            page.put(newtext, comment)
            return u'Success'
            #wikipedia.output(newtext)

    return u'Unchanged'
        

def convertHeaders(page, text):
    '''
    Convert the headers of a NRHP list. It's possible to have multiple headers on a page.
    '''
    pattern = u'\{\|\s*class="wikitable sortable"(\s*style="width:\d+%")?[\s\r\n]+(?P<pos>\!\s*\{\{(NRHP|HD|NHL|NHLD|NMON|NHS|NMEM|NHP|NB|NMP|NBP|NBS|NHR|IHS) color\}\}.*[\s\r\n]+)(?P<name>\!.*[\s\r\n]+)(?P<image>\!.*[\s\r\n]+)(?P<date>\!.*[\s\r\n]+)(?P<location>\!.*[\s\r\n]+)(?P<city>\!.*[\s\r\n]+)(?P<description>\!.*[\s\r\n]+)'

    return re.sub(pattern, convertHeader, text)
        
    
def convertHeader(match):
    '''
    Function to convert a single header. Match should contain a match of the header.
    The function will try to extract the two custom fields:
    * NRISref - Reference in the landmark name column
    * city - Default is city or town. This can be overridden
    '''

    # Find the reference:
    patternreffirst = u'<ref name=["]?nris["]?>\{\{NRISref\|(.+)\}\}</ref>'
    matchreffirst = re.search(patternreffirst, match.group(u'name'))
    patternrefmore = u'<ref name=(.+) />' # Not sure everywhere the backreference is the same
    matchrefmore = re.search(patternrefmore, match.group(u'name'))
    
    if matchreffirst:
        NRISref = matchreffirst.group(1)
    elif matchrefmore:
        NRISref = u'prev'
    else:
        NRISref = False

    patterncity = u'\!.*\|\s*\'\'\'City or Town\'\'\''
    matchcity = re.search(patterncity, match.group(u'city'))

    patternlocation = u'\!.*\|\s*\'\'\'(.+)\'\'\''
    matchlocation = re.search(patternlocation, match.group(u'city'))

    if patterncity:
        city = False
    elif matchlocation:
        city = matchlocation.group(1).strip()
    else:
        # That is strange. Found nothing. Just go to default
        city = False

    result = u'{{NRHP header'
    if NRISref:
        result = result + u'|NRISref=%s' % (NRISref,)
    if city:
        result = result + u'|city=%s' % (city,)

    result = result + u'}}\n'

    return result


def convertItems(page, text):
    '''
    Convert NRHP list items.
    '''
    # Added the color part to prevent matching on other tables
    # Only these 4, rest should be done by hand
    #pattern = u'\|--[\s\r\n]+(?P<pos>\!\s*\{\{(NRHP|HD|NHL|NHLD) color\}\}.*[\s\r\n]+)(?P<name>\|.*[\s\r\n]+)(?P<image>\|.*[\s\r\n]+)(?P<date>\|.*[\s\r\n]+)(?P<location>\|.*[\s\r\n]+)(?P<city>\|.*[\s\r\n]+)(?P<description>\|.*[\s\r\n]+)'
    pattern = u'\|--[\s\r\n]+(?P<pos>\!\s*\{\{(NRHP|HD|NHL|NHLD) color\}\}.+[\s\r\n]+)(?P<name>\|.*[\s\r\n]+)(?P<image>\|.*[\s\r\n]+)(?P<date>\|.*[\s\r\n]+)(?P<location>\|.*[\s\r\n]+)(?P<city>\|.*[\s\r\n]+)(?P<description>\|[^-^\}].*[\s\r\n]+)'
    text = re.sub(pattern, convertItem, text)
    text = addCounty(page, text)
    
    return text

    
def convertItem(match):
    '''
    Function to convert a single item. Match should contain a match of an item.

    '''

    # FIXME: Should do something with throwing and catch exceptions when no match is found

    fields = {}
    
    (fields['type'], fields['pos']) = extractTypeAndPos(match.group(u'pos'))
    (fields['article'], fields['name']) = extractArticleAndName(match.group(u'name'))
    fields['image'] = extractImage(match.group(u'image'))
    fields['date'] = extractDate(match.group(u'date'))
    (fields['address'], fields['lat'], fields['lon']) = extractLocation(match.group(u'location'))
    fields['city'] = extractCity(match.group(u'city'))
    fields['description'] = extractdescription(match.group(u'description'))

    #DEBUG
    #fields['refnum'] = u''
    fields['refnum'] = getRefnum(fields.get('article'))
    fields['county'] = u''

    return u'{{NRHP row\n|pos=%(pos)s\n|refnum=%(refnum)s\n|type=%(type)s\n|article=%(article)s\n|name=%(name)s\n|address=%(address)s\n|city=%(city)s\n|county=%(county)s\n|date=%(date)s\n|image=%(image)s\n|lat=%(lat)s\n|lon=%(lon)s\n|description=%(description)s\n}}\n' % fields

def extractTypeAndPos(line):
    '''
    Extract the NRHP type and the position in the list
    '''
    print line
    pattern = u'\!\s*\{\{(?P<type>.+) color\}\}\s*\|\s*<small>(?P<pos>[\.\d\s]+)</small>'

    match = re.search(pattern, line)

    #if match:
    # FIXME: Add excpetion handling

    return (match.group('type').strip(), match.group('pos').strip())

def extractArticleAndName(line):
    '''
    Extract the name of the article and the name of the item
    '''

    #FIXME : Will fail if it contains more than an article link
    patternSimple = u'^\|\s*\[\[(?P<name>[^\|^\]]+)\]\]\s*\r\n$'
    patternDifferent = u'^\|\s*\[\[(?P<article>[^\|^\]]+)\|(?P<name>[^\|^\]]+)\]\]\s*\r\n$'

    matchSimple = re.search(patternSimple, line)
    matchDifferent = re.search(patternDifferent, line)

    if matchSimple:
        return (matchSimple.group('name').strip(), matchSimple.group('name').strip())
    if matchDifferent:
        return (matchDifferent.group('article').strip(), matchDifferent.group('name').strip())

    wikipedia.output(line)
    # FIXME: If the bot reaches this, it will die
    return

def extractImage(line):
    '''
    Get the name of the image or an empty string when the image is still missing
    '''
    patternImage = u'^\|\s*\[\[(Image|image|File|file):(?P<image>[^\|]+)\|(.+)\]\]'
    patternEmpty = u'^\|[\s\r\n]*(<\!-- Image goes here -->)?[\s\r\n]*$'

    matchImage = re.search(patternImage, line)
    matchEmpty = re.search(patternEmpty, line)

    if matchImage:
        return (matchImage.group('image').strip())
    if matchEmpty:
        return u''
    
    # FIXME: If the bot reaches this, it will die
    return

def extractDate(line):
    '''
    Get the date or an empty string when the date is still missing
    '''
    patternDate = u'^\|\s*\{\{dts(\|link=off)?\|(?P<year>\d{4,4})\|(?P<month>\d{1,2})\|(?P<day>\d{1,2})\}\}[\s\r\n]*$'
    patternEmpty = u'^\|[\s\r\n]*(<\!-- .+ -->)?[\s\r\n]*$'

    matchDate = re.search(patternDate, line, flags=re.IGNORECASE)
    matchEmpty = re.search(patternEmpty, line)

    if matchDate:
        year = matchDate.group('year')
        if len(matchDate.group('month'))==1:
            month = u'0%s' % (matchDate.group('month'),)
        else:
            month = matchDate.group('month')
            
        if len(matchDate.group('day'))==1:
            day = u'0%s' % (matchDate.group('day'),)
        else:
            day = matchDate.group('day')
                                            
        return u'%s-%s-%s' % (year, month, day)
    
    if matchEmpty:
        return u''
    
    # FIXME: If the bot reaches this, it will die
    return

def extractLocation(line):
    '''
    Get the address, latitude and longitude
    '''
    patternAddressCoords = u'^\|\s*(?P<address>.+)[\s\r\n]*<br\s*/>[\s\r\n]*<small>[\s\r\n]*\{\{coord\|(?P<latd>\d+)\s*\|(?P<latm>\d+)\s*\|(?P<lats>[\d\.]+)\s*\|(?P<latdir>N|S)\s*\|(?P<lond>\d+)\s*\|(?P<lonm>\d+)\s*\|(?P<lons>[\d\.]+)\s*\|(?P<londir>E|W)\s*\|([^\}]+)\}\}\s*(</small>)?[\s\r\n]*$'
    patternAddress = u'^\|\s*(?P<address>.+)[\s\r\n]*$'
    patternEmpty = u'^\|[\s\r\n]*(<\!-- .+ -->)?[\s\r\n]*$'

    matchAddressCoords = re.search(patternAddressCoords, line, flags=re.IGNORECASE)
    matchAddress = re.search(patternAddress, line)
    matchEmpty = re.search(patternEmpty, line)

    if matchAddressCoords:
        address = matchAddressCoords.group('address')
        
        latd = float(matchAddressCoords.group('latd'))
        latm = float(matchAddressCoords.group('latm'))
        lats = float(matchAddressCoords.group('lats'))
        latdir = matchAddressCoords.group('latdir')

        lat = 0.0
        lat = latd + ( latm + lats / 60.0 ) / 60.0

        if latdir==u'S':
            lat = lat * -1.0
        
        lond = float(matchAddressCoords.group('lond'))
        lonm = float(matchAddressCoords.group('lonm'))
        lons = float(matchAddressCoords.group('lons'))
        londir = matchAddressCoords.group('londir')

        lon = lond + ( lonm + lons / 60.0 ) / 60.0

        if londir==u'W':
            lon = lon * -1.0

        return(address, round(lat,6), round(lon,6))

    if matchAddress:
        address = matchAddress.group('address')
        return (address, u'', u'')

    if matchEmpty:
        return (u'', u'', u'')

    # FIXME: If the bot reaches this, it will die
    return

def extractCity(line):
    '''
    Get the city
    '''
    patternCity = u'^\|\s*(?P<city>.+)[\s\r\n]*$'
    patternEmpty = u'^\|[\s\r\n]*(<\!-- .+ -->)?[\s\r\n]*$'

    matchCity = re.search(patternCity, line)
    matchEmpty = re.search(patternEmpty, line)

    if matchCity:
        city = matchCity.group('city').strip()
        return city

    if matchEmpty:
        return u''

    # FIXME: If the bot reaches this, it will die
    return

def extractdescription(line):
    '''
    Get the description
    '''
    patternDescription = u'^\|\s*(?P<description>.+)[\s\r\n]*$'
    patternEmpty = u'^\|[\s\r\n]*(<\!-- .+ -->)?[\s\r\n]*$'

    matchDescription = re.search(patternDescription, line)
    matchEmpty = re.search(patternEmpty, line)

    if matchDescription:
        description = matchDescription.group('description').strip()
        return description

    if matchEmpty:
        return u''

    # FIXME: If the bot reaches this, it will die
    return

def getRefnum(article):
    page = wikipedia.Page(wikipedia.getSite(), article)

    if page.exists() and (page.namespace() == 0) and not page.isRedirectPage():
        refnum = u''
        templates = page.templatesWithParams()
        
        for (template, params) in templates:
            if template.lower().replace(u'_', u' ')==u'infobox nrhp':
                for param in params:
                    #Split at =
                    (field, sep, value) = param.partition(u'=')
                    # Remove leading or trailing spaces
                    field = field.strip()
                    value = value.split("<ref")[0].strip()
                    
                    #Check first that field is not empty
                    if field:
                        if field==u'refnum':
                            refnum = value
                            return refnum.strip().lstrip(u'#')

    # We didn't find anything so return empty string
    return u''


def addCounty(page, text):
    '''
    Replace all '|county= |' with '|county=<name of county> |'
    '''
    countyFromTitle = page.title().replace(u'National Register of Historic Places listings in ', u'').strip()

    # Check if we're actually on a county page.
    # FIXME: Parish and borough
    if (not u'County' in countyFromTitle) and (not u'Parish' in countyFromTitle):
        return text
    
    foundCountyCategory = False  
    for category in page.categories():
        if category.titleWithoutNamespace() == countyFromTitle:
            foundCountyCategory = True
            
        countryFromCategory = category.titleWithoutNamespace().replace(u'National Register of Historic Places in', u'').strip()
        if countryFromCategory == countyFromTitle:
            foundCountyCategory = True
            
        countryFromCategory2 = category.titleWithoutNamespace().replace(u'National Register of Historic Places listings in', u'').strip()
        if countryFromCategory2 == countyFromTitle:
            foundCountyCategory = True

        countryFromCategory3 = category.titleWithoutNamespace().replace(u'Buildings and structures in', u'').strip()
        if countryFromCategory3 == countyFromTitle:
            foundCountyCategory = True

        countryFromCategory4 = category.titleWithoutNamespace().replace(u'History of', u'').strip()
        if countryFromCategory4 == countyFromTitle:
            foundCountyCategory = True

    foundCountyPage = False
    for linkedPage in page.linkedPages():
        if linkedPage.titleWithoutNamespace() == countyFromTitle:
            foundCountyPage = True    

    if foundCountyCategory and foundCountyPage:
        pattern = u'\|county=[\s\r\n]+\|'
        newtext = re.sub(pattern, u'|county=[[%s]] \n|' % (countyFromTitle,), text)
        return newtext

    # That didn't work. Return the unchanged text
    return text


def main():
    '''
    The main loop
    '''
    # First find out what to work on
    successList = []
    failedList = []

    # Load a lot of default generators
    genFactory = pagegenerators.GeneratorFactory()

    for arg in wikipedia.handleArgs():
        genFactory.handleArg(arg)

    generator = genFactory.getCombinedGenerator()
    if not generator:
        raise add_text.NoEnoughData('You have to specify the generator you want to use for the script!')
    else:
        pregenerator = pagegenerators.PreloadingGenerator(generator)

        for page in pregenerator:
            if page.exists() and (page.namespace() == 0) and not page.isRedirectPage():
                status = convertList(page)
                if status==u'Success':
                    successList.append(page.title())
                elif status==u'Failed':
                    failedList.append(page.title())

    wikipedia.output(u'Number of pages changed: %s' % (len(successList),))
    for title in successList:
        wikipedia.output(title)

    wikipedia.output(u'Number of pages that failed: %s' % (len(failedList),))
    for title in failedList:
        wikipedia.output(title)  



if __name__ == "__main__":
    try:
        main()
    finally:
        wikipedia.stopme()
