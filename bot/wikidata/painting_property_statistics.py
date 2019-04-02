#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to generate some painting statistics

These are published at https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Property_statistics

"""
import pywikibot
import pywikibot.data.sparql
import collections

class PaintingPropertyStatistics:
    """
    Generate painting statitics

    """
    def __init__(self):
        """
        Set what to work on and other variables here.
        """
        self.repo = pywikibot.Site().data_repository()
        self.collection_threshold = 50
        self.property_threshold = 10
        self.targetPageTitle = u'Wikidata:WikiProject sum of all paintings/Property statistics'
        self.properties = collections.OrderedDict()
        self.properties[u'P170'] = u'[[Property:P170|creator]]'
        self.properties[u'P276'] = u'[[Property:P276|location]]'
        self.properties[u'P571'] = u'[[Property:P571|inception]]'
        self.properties[u'P2048'] = u'[[Property:P2048|height]] & [[Property:P2049|width]]'
        self.properties[u'P186'] = u'[[Property:P186|material used]]'
        self.properties[u'P18'] = u'[[Property:P18|image]]'
        self.properties[u'P136'] = u'[[Property:P136|genre]]'
        self.properties[u'P180'] = u'[[Property:P180|depicts]]'
        self.properties[u'P921'] = u'[[Property:P921|main subject]]'
        self.propertyData = {}

    def getCollectionInfo(self):
        """
        Get the information for a single collection.

        :return: Tuple of two (ordered) dictionaries: First with counts, second with country codes
        """
        query = """SELECT ?item ?countrycode  (COUNT(?item) as ?count) WHERE {
  ?painting wdt:P31 wd:Q3305213 .
  ?painting wdt:P195 ?item .
  OPTIONAL { ?item wdt:P17/wdt:P298 ?countrycode }.
} GROUP BY ?item ?countrycode
HAVING (?count > %s)
ORDER BY DESC(?count)
LIMIT 1000""" % (self.collection_threshold,)
        collectionsCounts = collections.OrderedDict()
        collectionsCountries = collections.OrderedDict()
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            collectionsCounts[qid] = int(resultitem.get('count'))
            collectionsCountries[qid] = resultitem.get('countrycode')
        return (collectionsCounts, collectionsCountries)

    def getPropertyInfo(self, prop):
        """
        Get the usage counts for a property in the collections

        :param prop: Wikidata Pid of the property
        :return: (Ordered) dictionary with the counts per collection
        """
        query = """SELECT ?item (COUNT(?item) as ?count) WHERE {
  ?painting wdt:P31 wd:Q3305213 .  
  ?painting wdt:P195 ?item .
  FILTER EXISTS { ?painting p:%s [] } .
} GROUP BY ?item
HAVING (?count > %s)
ORDER BY DESC(?count) 
LIMIT 1000""" % (prop, self.property_threshold)

        result = collections.OrderedDict()
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[qid] = int(resultitem.get('count'))
        return result

    def getPaintingTotals(self, prop=None):
        """
        Get the painting totals
        :param prop:  Wikidata Pid of the property. If set, just get the count of paintings with that property
        :return: number of paintings found
        """
        if prop:
            query = """SELECT (COUNT(?item) as ?count) WHERE {
  ?item wdt:P31 wd:Q3305213 .
  FILTER EXISTS { ?item p:%s [] } .
}""" % (prop,)
        else:
            query = """SELECT (COUNT(?item) as ?count) WHERE {
  ?item wdt:P31 wd:Q3305213 .
}"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)
        for resultitem in queryresult:
            # Just one result, return that right away
            return int(resultitem.get('count'))

    def run(self):
        """
        Starts the robot and do all the work.
        """
        (collectionsCounts, collectionCountries) = self.getCollectionInfo()
        for prop in self.properties:
            self.propertyData[prop] = self.getPropertyInfo(prop)

        text = u'{{/Header}}\n{| class="wikitable sortable"\n'
        text += u'! colspan="3" |[[Wikidata:WikiProject sum of all paintings/Top collections|Top Collections]] (Minimum %s paintings)\n' % (self.collection_threshold, )
        text += u'! colspan="%s" |[[Wikidata:WikiProject sum of all paintings/Most used painting properties|Top Properties]] (used at least %s times per collection)\n' % (len(self.properties), self.property_threshold, )
        text += u'|-\n'
        text += u'! Country\n'
        text += u'! Name\n'
        text += u'! Count\n'
        for prop in self.properties:
            text += u'! data-sort-type="number"|%s\n' % self.properties.get(prop)

        for collection in collectionsCounts:
            countrycode = collectionCountries.get(collection)
            workcount = collectionsCounts.get(collection)

            text += u'|-\n'
            if countrycode:
                text += u'|data-sort-value="%s"|{{Flag|%s}}\n' % (countrycode, countrycode, )
            else:
                text += u'|\n'
            text += u'| {{Q|%s}}\n' % (collection,)
            text += u'| %s \n' % (workcount, )
            for prop in self.properties:
                propcount = self.propertyData.get(prop).get(collection)
                if not propcount:
                    propcount = 0
                percentage = round(1.0 * propcount / max(workcount, 1) * 100, 2)
                text += u'| {{/Cell|%s|%s}}\n' % (percentage, propcount)

        # Get the totals
        totalworks = self.getPaintingTotals()

        text += u'|- class="sortbottom"\n|\n|\'\'\'Totals\'\'\' <small>(all paintings)<small>:\n| %s\n' % (totalworks,)
        for prop in self.properties:
            totalprop = self.getPaintingTotals(prop=prop)
            percentage = round(1.0 * totalprop / totalworks * 100, 2)
            text += u'| {{/Cell|%s|%s}}\n' % (percentage, totalprop)
        text += u'|}\n'
        text += u'{{/Footer}}\n'
        text += u'[[Category:WikiProject sum of all paintings|Property statistics]]\n'

        page = pywikibot.Page(self.repo, title=self.targetPageTitle)
        summary = u'Painting property usage stats'
        page.put(text, summary)


def main(*args):
    """
    Main function. Bot does all the work.
    """
    paintingPropertyStatistics = PaintingPropertyStatistics()
    paintingPropertyStatistics.run()

if __name__ == "__main__":
    main()
