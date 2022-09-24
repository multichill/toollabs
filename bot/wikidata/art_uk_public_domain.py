#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Art UK started providing public domain images and marking them with CC BY-NC-ND.
That's good enough for me because these all fall under PD-art on Commons
See for example https://artuk.org/discover/artworks/landscape-with-figures-5364

Loop over all the items on Wikidata with Art UK artwork ID, but without an image (and some additional filter).
If a public domain image is found, add the suggestion link.

"""
import pywikibot
from pywikibot import pagegenerators
import requests
import pywikibot.data.sparql
import re

class ArtUKPublicDomain():

    """A bot to import public domain images from Art UK"""

    def __init__(self, generator):
        """
        Arguments:
            * generator    - A generator that yields ItemPage objects.

        """
        self.generator = generator
        self.repo = pywikibot.Site().data_repository()

    def run(self):
        """
        Starts the robot.
        """
        for itempage in self.generator:
            pywikibot.output(u'Working on %s' % (itempage.title(),))
            if not itempage.exists():
                pywikibot.output(u'Item does not exist, skipping')
                continue

            data = itempage.get()
            claims = data.get('claims')

            # Do some checks so we are sure we found exactly one inventory number and one collection
            if u'P1679' not in claims:
                pywikibot.output(u'No Art UK artwork ID found, skipping')
                continue

            if u'P18' in claims:
                pywikibot.output(u'Already has an image, done')
                continue

            if u'P4765' in claims:
                pywikibot.output(u'Already has an image suggestion, done')
                continue

            if len(claims.get('P1679')) != 1:
                pywikibot.output('More than one claim, skipping this one')
                continue

            if claims.get('P1679')[0].getRank() == 'deprecated':
                pywikibot.output('The claim is deprecated, skipping this one')
                continue

            artukid = claims.get(u'P1679')[0].getTarget()
            artukidurl = 'https://artuk.org/discover/artworks/%s' % (artukid,)

            imagePage = requests.get(artukidurl) #, verify=False)
            # They are sending the wrong headers so I got ISO-8859-1 instead of utf-8
            imagePage.encoding = imagePage.apparent_encoding

            ccregex = 'id\=\"download-artwork\"[\s\t\r\n]*class\=\"btn dl toolbar_icon\"[\s\t\r\n]*title\=\"Creative Commons\"'
            dlregex = '\<a href\=\"(https\:\/\/artuk\.org\/download\/[^\"]+)\" class\=\"btn btn-default\" id\=\"download-button\" data-val\=\"Downloaded\"\>Download\<\/a\>'
            thumbregex = '\<div class\=\"artwork\"\>[\s\t\r\n]*\<div[\s\t\r\n]*class\=\"artwork_thumb\"[\s\t\r\n]*data-artwork_thumb[\s\t\r\n]*\>[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<div[\s\t\r\n]*class\=\"artwork_slider\"[\s\t\r\n]*data-artwork_slider[\s\t\r\n]*\>[\s\t\r\n]*\<div class\=\"single_img\"\>[\s\t\r\n]*\<img src\=\"([^\"]+)\"'

            ccmatch = re.search(ccregex, imagePage.text)
            dlmatch = re.search(dlregex, imagePage.text)
            thumbmatch = re.search(thumbregex, imagePage.text)

            if ccmatch and dlmatch:
                imageurl = dlmatch.group(1).replace(' ', '%20')
            elif thumbmatch:
                imageurl = thumbmatch.group(1).replace(' ', '%20')
            else:
                continue

            titleregex = '\<h1 class\=\"artwork-title\"\>([^\<]+)\s*\<\/h1\>'
            creatorregex = '\<h2 class\=\"artist\"\>[\s\t\r\n]*\<a href\=\"[^\"]*\"\>\s*([^\<]+)\s*</a>'

            titlematch = re.search(titleregex, imagePage.text)
            creatormatch = re.search(creatorregex, imagePage.text)

            if titlematch and creatormatch:
                title = titlematch.group(1).strip()
                creator = " ".join(creatormatch.group(1).split()).replace('–','-')
            else:
                continue

            print (imageurl)
            print (title)
            print (creator)

            newclaim = pywikibot.Claim(self.repo, u'P4765')
            newclaim.setTarget(imageurl)
            pywikibot.output('Adding commons compatible image available at URL claim to %s' % (itempage.title(),))
            itempage.addClaim(newclaim)

            # JPEG
            newqualifier = pywikibot.Claim(self.repo, u'P2701')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q2195'))
            newclaim.addQualifier(newqualifier)

            # Source link
            newqualifier = pywikibot.Claim(self.repo, u'P2699')
            newqualifier.setTarget(artukidurl)
            newclaim.addQualifier(newqualifier)

            # Operated by link
            newqualifier = pywikibot.Claim(self.repo, u'P137')
            newqualifier.setTarget(pywikibot.ItemPage(self.repo, u'Q7257339'))
            newclaim.addQualifier(newqualifier)

            # Title qualifier
            entitle = pywikibot.WbMonolingualText(title, u'en')
            newqualifier = pywikibot.Claim(self.repo, u'P1476')
            newqualifier.setTarget(entitle)
            newclaim.addQualifier(newqualifier)

            # Author name string qualifier
            newqualifier = pywikibot.Claim(self.repo, u'P2093')
            newqualifier.setTarget(creator)
            newclaim.addQualifier(newqualifier)


def main(*args):


    repo = pywikibot.Site().data_repository()
    query = """SELECT DISTINCT ?item WHERE {
  ?item wdt:P1679 ?id .
  MINUS { ?item wdt:P18 ?image } .
  MINUS { ?item wdt:P4765 ?ccimage } .
  MINUS { ?item wdt:P6500 ?unfreeimage } .
  ?item wdt:P31 wd:Q3305213 .
  MINUS { ?item wdt:P170/wdt:P569 ?dob . FILTER(YEAR(?dob)>1900) } .
  MINUS { ?item wdt:P170/wdt:P570 ?dod . FILTER(YEAR(?dod)>1925) } .
  MINUS { ?item wdt:P571 ?inception . FILTER(YEAR(?inception)>1925) } .                                                
  ?item schema:dateModified ?modified
  } ORDER BY DESC(?modified)
"""
    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    imagesPublicDomainRobot = ArtUKPublicDomain(generator)
    imagesPublicDomainRobot.run()

if __name__ == "__main__":
    main()