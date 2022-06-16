#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to generate some more painting statistics, this time for external-id's

These are published at https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/External_identifiers_property_statistics

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
        #self.collection_threshold = 50
        #self.property_threshold = 10
        self.targetPageTitle = u'Wikidata:WikiProject sum of all paintings/External identifiers property statistics'
        self.properties = collections.OrderedDict()
        self.properties['P170'] = '[[Property:P170|creator]]'
        self.properties['P571'] = '[[Property:P571|inception]]'
        self.properties['P195'] = '[[Property:P195|collection]]'
        self.properties['P217'] = '[[Property:P195|inventory number]]'
        self.properties['P276'] = '[[Property:P276|location]]'
        self.properties['P2048'] = '[[Property:P2048|height]] & [[Property:P2049|width]]'
        self.properties['P186'] = '[[Property:P186|material used]]'
        self.properties['P18'] = '[[Property:P18|image]]'
        self.properties['P136'] = '[[Property:P136|genre]]'
        self.properties['P180'] = '[[Property:P180|depicts]]'
        self.properties['P921'] = '[[Property:P921|main subject]]'
        self.properties['P1476'] = '[[Property:P1476|title]]'
        self.properties['P6216'] = '[[Property:P6216|copyright status]]'
        self.propertyData = {}
        self.averageStatements = {}
        self.sumSitelinks = {}

    def get_external_id_info(self):
        """
        Get the information for an external identifier

        :return: Tuple of two (ordered) dictionaries: First with counts, second with country codes
        """
        query = """SELECT ?item (COUNT(?item) as ?count) WITH {
SELECT ?item WHERE {
  ?property wikibase:directClaim ?item ;
            wikibase:propertyType wikibase:ExternalId ;
            wdt:P31 wd:Q44847669 .  
  }
  } AS %properties
  WHERE {
    INCLUDE %properties
  ?painting wdt:P31 wd:Q3305213 .  
  ?painting ?item []  .
} GROUP BY ?item
ORDER BY DESC(?count) 
LIMIT 1000"""
        external_id_counts = collections.OrderedDict()
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/prop/direct/', '')
            external_id_counts[qid] = int(resultitem.get('count'))
        return external_id_counts

    def get_property_info(self, prop):
        """
        Get the usage counts for a property in external identifiers

        :param prop: Wikidata Pid of the property
        :return: (Ordered) dictionary with the counts per collection
        """
        query = """SELECT ?item (COUNT(?item) as ?count) WITH {
SELECT ?item WHERE {
  ?property wikibase:directClaim ?item ;
            wikibase:propertyType wikibase:ExternalId ;
            wdt:P31 wd:Q44847669 .  
  }
  } AS %%properties
  WHERE {
    INCLUDE %%properties
  ?painting wdt:P31 wd:Q3305213 .  
  ?painting ?item []  .
  FILTER EXISTS { ?painting p:%s [] } .
} GROUP BY ?item
ORDER BY DESC(?count) 
LIMIT 1000""" % (prop, )

        result = collections.OrderedDict()
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/prop/direct/', '')
            result[qid] = int(resultitem.get('count'))
        return result

    def getAverageStatements(self):
        """
        Get the average number of statements per collection

        :return: (Ordered) dictionary with the counts per collection
        """
        query = """SELECT ?item (ROUND(AVG(?statements)) as ?count) WITH {
SELECT ?item WHERE {
  ?property wikibase:directClaim ?item ;
            wikibase:propertyType wikibase:ExternalId ;
            wdt:P31 wd:Q44847669 .  
  }
  } AS %properties
  WHERE {
    INCLUDE %properties
  ?painting wdt:P31 wd:Q3305213 ;
            ?item [] ;
            wikibase:statements ?statements . 
} GROUP BY ?item
ORDER BY DESC(?count) 
LIMIT 1000"""

        result = collections.OrderedDict()
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/prop/direct/', '')
            result[qid] = int(resultitem.get('count'))
        return result

    def getSumSitelinks(self):
        """
        Get the total number of sitelinks  per collection

        :return: (Ordered) dictionary with the counts per collection
        """
        query = """SELECT ?item (SUM(?sitelinks) as ?count) WITH {
SELECT ?item WHERE {
  ?property wikibase:directClaim ?item ;
            wikibase:propertyType wikibase:ExternalId ;
            wdt:P31 wd:Q44847669 .  
  }
  } AS %properties
  WHERE {
    INCLUDE %properties
  ?painting wdt:P31 wd:Q3305213 ;
            ?item [] ;
            wikibase:sitelinks ?sitelinks . 
} GROUP BY ?item
ORDER BY DESC(?count) 
LIMIT 1000"""

        result = collections.OrderedDict()
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/prop/direct/', '')
            result[qid] = int(resultitem.get('count'))
        return result

    def getPaintingTotals(self, prop=None, counts=None):
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
        elif counts and counts=='statements':
            query = """SELECT (ROUND(AVG(?statements)) as ?count) WHERE {
  ?painting wdt:P31 wd:Q3305213 ; 
            wikibase:statements ?statements . 
}"""
        elif counts and counts=='sitelinks':
            query = """SELECT (SUM(?sitelinks) as ?count) WHERE {
  ?painting wdt:P31 wd:Q3305213 ; 
            wikibase:sitelinks ?sitelinks . 
}"""
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
        external_id_counts = self.get_external_id_info()
        for prop in self.properties:
            self.propertyData[prop] = self.get_property_info(prop)
        self.averageStatements = self.getAverageStatements()
        self.sumSitelinks = self.getSumSitelinks()

        text = u'{{/Header}}\n{| class="wikitable sortable"\n'
        #text += u'! colspan="3" |[[Wikidata:WikiProject sum of all paintings/Top collections|Top Collections]] (Minimum %s paintings)\n' % (self.collection_threshold, )
        #text += u'! colspan="%s" |[[Wikidata:WikiProject sum of all paintings/Most used painting properties|Top Properties]] (used at least %s times per collection)\n' % (len(self.properties), self.property_threshold, )
        text += u'|-\n'
        #text += u'! Country\n'
        text += u'! Name\n'
        text += u'! Count\n'
        for prop in self.properties:
            text += u'! data-sort-type="number"|%s\n' % self.properties.get(prop)
        text += u'! Statements (average)\n'
        text += u'! Sitelinks (total)\n'

        for external_id in external_id_counts:
            #countrycode = collectionCountries.get(collection)
            workcount = external_id_counts.get(external_id)
            text += u'|-\n'

            text += u'| {{P|%s}}\n' % (external_id, )
            text += u'| %s \n' % (workcount, )
            for prop in self.properties:
                propcount = self.propertyData.get(prop).get(external_id)
                if not propcount:
                    propcount = 0
                percentage = round(1.0 * propcount / max(workcount, 1) * 100, 2)
                text += u'| {{/Cell|%s|%s}}\n' % (percentage, propcount)
            text += u'| %s \n' % (self.averageStatements.get(external_id), )
            text += u'| %s \n' % (self.sumSitelinks.get(external_id), )

        # Get the totals
        totalworks = self.getPaintingTotals()

        text += u'|- class="sortbottom"\n|\n|\'\'\'Totals\'\'\' <small>(all paintings)<small>:\n| %s\n' % (totalworks,)
        for prop in self.properties:
            totalprop = self.getPaintingTotals(prop=prop)
            percentage = round(1.0 * totalprop / totalworks * 100, 2)
            text += u'| {{/Cell|%s|%s}}\n' % (percentage, totalprop)
        text += u'| %s \n' % (self.getPaintingTotals(counts='statements'), )
        text += u'| %s \n' % (self.getPaintingTotals(counts='sitelinks'), )
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
