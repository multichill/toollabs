#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Work on https://vangoghworldwide.org/ . Just adding a bunch of links for now to give more background info

Result at https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Creator/Vincent_van_Gogh

"""
import artdatabot
import pywikibot
import requests
import pywikibot.data.sparql
import re


class VanGoghWorldwidePaintingDataBot(artdatabot.ArtDataBot):
    """
    Subclass of ArtDataBot because that one has logic completely based on collections
    """
    def __init__(self, dictGenerator, create=False):
        """
        Arguments:
            * generator    - A generator that yields Dict objects.
            * create       - Boolean to say if you want to create new items or just update existing

        """
        self.generator = dictGenerator
        self.repo = pywikibot.Site().data_repository()
        self.create = create

    def run(self):
        """
        Starts the robot.
        """

        for metadata in self.generator:
            if not 'wikidata' in metadata:
                continue
            artworkItem = pywikibot.ItemPage(self.repo, title=metadata.get('wikidata'))
            self.updateArtworkItem(artworkItem, metadata)

    def updateArtworkItem(self, artworkItem, metadata):
        """
        Override this one for now

        Add statements and other data to the artworkItem
        :param artworkItem: The artwork item to work on
        :param metadata: All the metadata about this artwork.
        :return: Nothing, updates item in place
        """
        # Add a link to the item in a collection. Either described at URL (P973) or custom.
        self.addCollectionLink(artworkItem, metadata)


def createCatalogTables():
    """
    Make three catalog tables
    """
    bothtable = {}
    ftable = {}
    jhtable = {}

    # Need to use the long version here to get all ranks
    query = """SELECT DISTINCT ?item ?fcat ?jhcat WHERE {
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
        qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', u'')
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

def vanGoghwoldwideGenerator():
    """
    Loop over the json and grab the needed info
    :return: Generator of metadata compatible with artdatabot
    """
    bothtable, ftable, jhtable = createCatalogTables()

    url = 'https://rest.spinque.com/2.5/vangoghworldwide/api/platform/e/artworks/q/type%3AFILTER/p/value/1.0(http%3A%2F%2Fvocab.getty.edu%2Faat%2F300033618)/results?config=production&count=1000'
    page = requests.get(url)

    fregex = '^https\:\/\/vangoghworldwide\.org\/data\/artwork\/(F.+)$'

    for item in page.json().get('items'):
        metadata = {}
        furl = item.get('tuple')[0].get('attributes').get('sameAs')[0].get('@id')
        fmatch = re.match(fregex, furl)
        if fmatch:
            fid = fmatch.group(1)
            #print (item.get('tuple')[0].get('attributes').get('sameAs'))
            if fid in ftable:
                metadata['wikidata'] = ftable.get(fid)
                metadata['describedbyurl'] = 'https://vangoghworldwide.org/artwork/%s' % (fid,)

                yield metadata
            else:
                print('%s not found on Wikidata' % (fid,))
        else:
            print('%s did not match' % (furl,))


def main(*args):
    paintingGenerator = vanGoghwoldwideGenerator()
    #for entry in paintingGenerator:
    #    print (entry)
    artDataBot = VanGoghWorldwidePaintingDataBot(paintingGenerator, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()