#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Simple generator to get data from RKD

"""
import json
import urllib
        
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


def main():
    artistGen = getArtistsGenerator()
    for artist in artistGen:
        # Do something here
        pass
    

if __name__ == "__main__":
    main()
