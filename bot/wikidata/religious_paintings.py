#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add genre is religious art and main subject to paintings based on the label

"""
import pywikibot
import pywikibot.data.sparql

class ReligiousPaintingsBot:
    """
    A bot to add genre to paintings on Wikidata
    """
    def __init__(self):
        """
        Arguments:
            * generator    - A generator that yields Wikidata items objects.

        """
        self.repo = pywikibot.Site().data_repository()
        self.generator = self.getLabelGenerator()
        self.religiousart = 'Q2864737'
        self.processedQids = []

    def getLabelGenerator(self, threshold=4):
        """
        Build a SPARQL query to get the most used labels for religious main subjects
        :return: A generator that yields dicts
        """
        query = """SELECT DISTINCT ?label (LANG(?label) AS ?lang) ?mainsubject (COUNT(CONCAT(LANG(?label), STR(?label), STR(?mainsubject))) AS ?count) (SAMPLE(?item) AS ?item) WHERE {
  ?item wdt:P136 wd:%s;
    wdt:P921 ?mainsubject;
    wdt:P31 wd:Q3305213;
    rdfs:label ?label.
  FILTER(NOT EXISTS { ?item (wdt:P31/(wdt:P279*)) wd:Q1278452. })
}
GROUP BY ?label ?lang ?mainsubject
HAVING (?count > %s)
ORDER BY DESC (?count)""" % (self.religiousart, threshold,)
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            result = {
                'label' : resultitem.get('label'),
                'lang' : resultitem.get('lang'),
                'mainsubject' : resultitem.get('mainsubject').replace(u'http://www.wikidata.org/entity/', u''),
                'genre' : self.religiousart,
                'count' : int(resultitem.get('count')),
                'example' : resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u''),
            }
            yield result

    def run(self):
        """
        Starts the robot.
        """
        for labelinfo in self.generator:
            self.processLabel(labelinfo)

    def processLabel(self, labelinfo):
        """
        Process the label
        :param labelinfo:
        :return:
        """
        mainsubjects = {}
        genres = {}

        pywikibot.output('Working on "%(label)s" (%(lang)s) for %(mainsubject)s with %(count)s hits' % labelinfo)

        suggestions = self.getItemLabelSuggestions(labelinfo)

        # First process the items that already have main subject and genre
        for suggestion in suggestions:
            if suggestion.get('mainsubject'):
                if suggestion.get('mainsubject') not in mainsubjects:
                    mainsubjects[suggestion.get('mainsubject')] = []
                mainsubjects[suggestion.get('mainsubject')].append(suggestion.get('item'))
            if suggestion.get('genre'):
                if suggestion.get('genre') not in genres:
                    genres[suggestion.get('genre')] = []
                genres[suggestion.get('genre')].append(suggestion.get('item'))

        addmainsubject = None
        addgenre = None

        # If all is good, we found one main subject
        if len(list(mainsubjects.keys()))==1 and list(mainsubjects.keys())[0]==labelinfo.get('mainsubject'):
            addmainsubject = labelinfo.get('mainsubject')
        else:
            pywikibot.output('Found multiple main subjects %s' % (list(mainsubjects.keys()),))
        # And we found one genre (religious art)
        if len(list(genres.keys()))==1 and list(genres.keys())[0]==labelinfo.get('genre'):
            addgenre = labelinfo.get('genre')
        # It's possible we found multiple genres, but that all paintings that have a genre have religious art too
        elif labelinfo.get('genre') in list(genres.keys()):
            withoutgenre = False
            for foundgenre in list(genres.keys()):
                if not foundgenre==labelinfo.get('genre'):
                    for item in genres.get(foundgenre):
                        if item not in genres.get(labelinfo.get('genre')):
                            pywikibot.output('On item %s I only found genre %s' % (item, foundgenre))
                            withoutgenre = True
            if not withoutgenre:
                addgenre = labelinfo.get('genre')

        mainsubjectitem = pywikibot.ItemPage(self.repo, labelinfo.get('mainsubject'))
        genreitem = pywikibot.ItemPage(self.repo, labelinfo.get('genre'))

        # Second pass of the suggestions to actually add things
        for suggestion in suggestions:
            # Don't want to work on the same item twice
            if suggestion.get('item') in self.processedQids:
                continue
            self.processedQids.append(suggestion.get('item'))
            # Don't want to load items to which we add nothing anyway
            if suggestion.get('mainsubject') and suggestion.get('genre'):
                continue
            # Only add something if we found the genre without any conflicts
            if not addgenre:
                pywikibot.output('Not working on item %s because I don\'t have genre to add' % (suggestion.get('item'),) )
                continue
            item =  pywikibot.ItemPage(self.repo, suggestion.get('item'))
            if item.isRedirectPage():
                item = item.getRedirectTarget()
            claims = item.get().get('claims')
            if addmainsubject and not suggestion.get('mainsubject') and not 'P921' in claims:
                summary = 'based on label "%(label)s" (%(lang)s) on %(count)s items, example [[%(example)s]]' % labelinfo
                newclaim = pywikibot.Claim(self.repo, u'P921')
                newclaim.setTarget(mainsubjectitem)
                pywikibot.output(summary)
                item.addClaim(newclaim, summary=summary)
            if not suggestion.get('genre') and not 'P136' in claims:
                summary = 'based on label "%(label)s" (%(lang)s) on at least %(count)s items, example [[%(example)s]]' % labelinfo
                newclaim = pywikibot.Claim(self.repo, u'P136')
                newclaim.setTarget(genreitem)
                pywikibot.output(summary)
                item.addClaim(newclaim, summary=summary)

    def getItemLabelSuggestions(self, labelinfo):
        """
        Do query for items to process based on the label info
        :param labelinfo:
        :return:
        """
        query = """SELECT ?item ?mainsubject ?genre WHERE {
  ?item rdfs:label "%(label)s"@%(lang)s ;
        wdt:P31 wd:Q3305213 .
  FILTER(NOT EXISTS { ?item (wdt:P31/(wdt:P279*)) wd:Q1278452. })
  OPTIONAL { ?item wdt:P921 ?mainsubject } .
  OPTIONAL { ?item wdt:P136 ?genre } . 
  }
        """ % labelinfo
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        result = []

        for resultitem in queryresult:
            suggestion = { 'item' : resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u''),
                           'mainsubject' : None,
                           'genre' : None,
                           }
            if resultitem.get('mainsubject'):
                suggestion['mainsubject'] = resultitem.get('mainsubject').replace(u'http://www.wikidata.org/entity/', u'')
            if resultitem.get('genre'):
                suggestion['genre'] = resultitem.get('genre').replace(u'http://www.wikidata.org/entity/', u'')
            result.append(suggestion)
        return result

def main():
    """
    Just a main function to start the robot
    """
    religiousPaintingsBot = ReligiousPaintingsBot()
    religiousPaintingsBot.run()

if __name__ == "__main__":
    main()
