#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

"""
import pywikibot
from pywikibot import pagegenerators
import requests
import re

def makeLookupTable():
    """
    Download http://tools.wmflabs.org/multichill/queries/erfgoed/rijksmonumenten_types.txt and make it into a lookup table
    """
    lookup = {  u'Aanlegvoorziening': u'',
                u'Appartementengebouw': u'Q1577547', #(apartment building)
                u'Bedieningsgebouw': u'',
                u'Bedrijfs-,fabriekswoning': u'',
                u'Begraafplaats en -onderdl': u'Q16423655', #(burial or funerary monument or structure) or Q39614', #(Cemetary)
                u'Bestuursgebouw en onderdl': u'',
                u'Bijgebouwen': u'Q41176', #(building)
                u'Bijgebouwen kastelen enz.': u'Q41176', #(building)
                u'Bijzondere woonvorm': u'Q41176', #(building)
                u'Boerderij': u'Q131596', #(farm)
                u'Bomvrij militair object': u'',
                u'Brug': u'Q12280', #(bridge)
                u'Crematorium': u'Q157570', #(crematory)
                u'Dienstwoning': u'',
                u'Dierenverblijf': u'',
                u'Erfscheiding': u'Q148571', #(fence)
                u'Fort, vesting en -onderdl': u'Q57821', #(fortification)
                u'Gedenkteken': u'Q5003624', #(memorial)
                u'Gemaal': u'Q446013', #(pumping station)
                u'Gerechtsgebouw': u'Q24536350', #(court building)
                u'Gezondheidszorg': u'Q4260475', #(medical facility)
                u'Gracht': u'Q523166', #(gracht)
                u'Grensafbakening': u'',
                u'Handel en kantoor': u'',
                u'Horeca': u'',
                u'Industrie': u'Q12144897', #(industrial building)
                u'Industrie- en poldermolen': u'Q44494', #(mill)
                u'Kapel': u'Q108325', #(chapel) 
                u'Kasteel, buitenplaats': u'Q41176', #(building)
                u'Kazemat': u'Q89521', #(casemate)
                u'Kerk en kerkonderdeel': u'Q21029893', #(religious object)
                u'Kerkelijke dienstwoning': u'Q607241', #(rectory)
                u'Klooster, kloosteronderdl': u'Q44613', #(monastery)
                u'Kust- en oevermarkering': u'',
                u'Militair verblijfsgebouw': u'Q6852233', #(military building)
                u'Militair wachtgebouw': u'Q6852233', #(military building)
                u'Militaire opslagplaats': u'Q6852233', #(military building)
                u'Nijverheid': u'',
                u'Nutsbedrijf': u'',
                u'Omwalling': u'',
                u'Onderdeel woningen e.d.': u'',
                u'Onderwijs en wetenschap': u'',
                u'Open verdedigingswerk': u'',
                u'Opslag': u'',
                u'Overheidsgebouw': u'Q16831714', #(government building)
                u'Scheepshulpmiddel': u'',
                u'Sociale zorg, liefdadigh.': u'',
                u'Sport en recreatie': u'',
                u'Stoep': u'Q177749', #(sidewalk)
                u'Straatmeubilair': u'',
                u'Transport': u'',
                u'Tuin, park en plantsoen': u'Q22652', #(green space)
                u'Vanwege onderdelen kerk': u'Q21029893', #(religious object)
                u'Vergadering en vereniging': u'',
                u'Verkeersobject': u'',
                u'Versperring': u'',
                u'Voorwerk': u'',
                u'Waarnemingspost': u'',
                u'Waterkering en -doorlaat': u'',
                u'Waterweg, werf en haven': u'',
                u'Weg': u'Q34442', #(road)
                u'Welzijn, kunst en cultuur': u'',
                u'Werk-woonhuis': u'Q3947', #(house)
                u'Winkel': u'Q213441', #(shop)
                u'Woonhuis': u'Q3947', #(house)
                #u'niks': u'', #default could be Q811979', #(architectural structure)
            }
    result = {}
    typePage = requests.get(u'http://tools.wmflabs.org/multichill/queries/erfgoed/rijksmonumenten_types.txt')

    searchRegex = u'(\d+) - (.+)'
    matches = re.finditer(searchRegex, typePage.text)
    for match in matches:
        rijksid = match.group(1)
        rijkstype = match.group(2)
        if rijkstype in lookup and lookup[rijkstype]:
            result[rijksid]=lookup[rijkstype]

    return result

def main():
    lookuptable = makeLookupTable()
    #print lookuptable
    site = pywikibot.Site()
    repo = site.data_repository()
    query = u'SELECT ?item WHERE { ?item wdt:P359 [] . MINUS {?item wdt:P31 []} }'
    itemGen = pagegenerators.PreloadingItemGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in itemGen:
        pywikibot.output(item.title())
        data = item.get()
        claims = data.get('claims')
        if u'P359' in claims:
            rijksid = claims.get(u'P359')[0].getTarget()
            if u'P31' not in claims:
                if rijksid in lookuptable:
                    summary = u'Adding instance of %s based on %s' % (lookuptable[rijksid], rijksid)
                    typeItem = pywikibot.ItemPage(repo, title=lookuptable[rijksid])

                    newclaim = pywikibot.Claim(repo, u'P31')
                    newclaim.setTarget(typeItem)
                    pywikibot.output('Adding instance claim to %s' % item)
                    item.addClaim(newclaim, summary=summary)


if __name__ == "__main__":
    main()
