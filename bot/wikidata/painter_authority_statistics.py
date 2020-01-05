#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to generate some painter authority statistics

These are published at https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Property_statistics

"""
import pywikibot
import pywikibot.data.sparql
import collections

class PainterAuthorityStatistics:
    """
    Generate painting statitics

    """
    def __init__(self):
        """
        Set what to work on and other variables here.
        """
        self.repo = pywikibot.Site().data_repository()
        self.artistProperties = self.getArtistProperties()
        self.propertyTotals = {}
        self.propertyPainterTotals = {}
        self.propertyIdentifiers = {}
        self.propertyPainterIdentifiers = {}
        self.propertyPairTotals = {}
        self.propertyPairPainterTotals = {}

        self.collection_threshold = 50
        self.property_threshold = 10
        self.targetPageTitle = u'Wikidata:WikiProject sum of all paintings/Painter authority statistics'
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
        self.properties[u'P1476'] = u'[[Property:P1476|title]]'
        self.propertyData = {}

    def run(self):
        """
        Do the actual data gathering and publish the statistics
        :return:
        """
        self.getPropertyData()
        self.publishStatistics()

    def getArtistProperties(self):
        """
        Get the list of artist properties.
        :return: a list of integers
        """
        result = []
        query = """SELECT ?property WHERE {
  ?property wdt:P31 wd:Q55653847 .
  } LIMIT 20"""

        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            if resultitem.get('property').startswith(u'http://www.wikidata.org/entity/P'):
                pid = resultitem.get('property').replace(u'http://www.wikidata.org/entity/P', u'')
                result.append(int(pid))
        return sorted(result)

    def getPropertyData(self):
        """

        :return:
        """
        for propertyid1 in self.artistProperties:
            print (propertyid1)
            self.propertyTotals[propertyid1] = self.getPropertyTotals(propertyid1)
            self.propertyPainterTotals[propertyid1] = self.getPropertyTotals(propertyid1, itemtype=u'painter')
            self.propertyIdentifiers[propertyid1] = self.getpropertyIdentifiers(propertyid1)
            self.propertyPainterIdentifiers[propertyid1] = self.getpropertyIdentifiers(propertyid1, itemtype=u'painter')
            for propertyid2 in self.artistProperties:
                # This way we only work on each pair once
                if propertyid1 < propertyid2:
                    pair = (propertyid1, propertyid2)
                    print (pair)
                    self.propertyPairTotals[pair] = self.getpropertyPairTotals(propertyid1, propertyid2)
                    self.propertyPairPainterTotals[pair] = self.getpropertyPairTotals(propertyid1, propertyid2,
                                                                                      itemtype=u'painter')


    def getPropertyTotals(self, propertyid, itemtype=u''):
        """
        Get the totals for one property
        :param propertyid:
        :param itemtype:
        :return:
        """
        if itemtype==u'painter':
            query = """SELECT (COUNT(?item) AS ?count) WHERE {
  ?item wdt:P%s ?id .
  ?item wdt:P106 wd:Q1028181 .
  ?item wdt:P31 wd:Q5 .
  }""" % (propertyid,)
        else:
            query = """SELECT (COUNT(?item) AS ?count) WHERE {
  ?item wdt:P%s ?id .
  ?item wdt:P31 wd:Q5 .
  }""" % (propertyid,)

        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        # Only one row
        for resultitem in queryresult:
            count = resultitem.get('count')
            print (count)
            return int(count)
        return 0

    def getpropertyPairTotals(self, propertyid1, propertyid2, itemtype=u''):
        """
        Get the totals for a pair of properties
        :param propertyid:
        :param itemtype:
        :return:
        """
        if itemtype==u'painter':
            query = """SELECT (COUNT(?item) AS ?count) WHERE {
  ?item wdt:P%s ?id2 .
  ?item wdt:P%s ?id1 .
  ?item wdt:P106 wd:Q1028181 .
  ?item wdt:P31 wd:Q5 .
  }""" % (propertyid2, propertyid1,)
        else:
            query = """SELECT (COUNT(?item) AS ?count) WHERE {
  ?item wdt:P%s ?id2 .
  ?item wdt:P%s ?id1 .
  ?item wdt:P31 wd:Q5 .
  }""" % (propertyid2, propertyid1,)

        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        # Only one row
        for resultitem in queryresult:
            count = resultitem.get('count')
            print (count)
            return int(count)
        return 0

    def getpropertyIdentifiers(self, propertyid, itemtype=u''):
        """
        :return:
        """
        if itemtype==u'painter':
            query = """SELECT ?ids (COUNT(?item) AS ?count) WHERE {
  ?item wdt:P%s ?id .
  ?item wdt:P106 wd:Q1028181 .
  ?item wdt:P31 wd:Q5 .
  ?item wikibase:identifiers ?ids
  } GROUP BY ?ids
ORDER BY ASC(?ids)""" % (propertyid,)
        else:
            query = """SELECT ?ids (COUNT(?item) AS ?count) WHERE {
  ?item wdt:P%s ?id .
  ?item wdt:P31 wd:Q5 .
  ?item wikibase:identifiers ?ids
  } GROUP BY ?ids
ORDER BY ASC(?ids)""" % (propertyid,)

        result = {}
        for i in range(1,12):
            result[i] = 0
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            ids = int(resultitem.get('ids'))
            count = int(resultitem.get('count'))
            if ids <= 10:
                result[ids]=count
            else:
                result[11] = result[11] + count
        return result

    def publishStatistics(self):
        """
        We have all the data, time to publish it.
        """
        #(collectionsCounts, collectionCountries) = self.getCollectionInfo()
        #for prop in self.properties:
        #    self.propertyData[prop] = self.getPropertyInfo(prop)

        text = u'{{/Header}}\n{| class="wikitable sortable"\n'
        #text += u'! colspan="3" |[[Wikidata:WikiProject sum of all paintings/Top collections|Top Collections]] (Minimum %s paintings)\n' % (self.collection_threshold, )
        #text += u'! colspan="%s" |[[Wikidata:WikiProject sum of all paintings/Most used painting properties|Top Properties]] (used at least %s times per collection)\n' % (len(self.properties), self.property_threshold, )
        text += u'|-\n'
        text += u'! Properties\n'

        # Complete the header
        for prop in self.artistProperties:
            text += u'! data-sort-type="number"|P%s\n' % (prop,)
        text += u'! <!-- spacer -->\n'
        text += u'! data-sort-type="number"|1 ID\n'
        for i in range(2,11):
            text += u'! data-sort-type="number"|%s ID\'s\n' % (i,)
        text += u'! data-sort-type="number"|>10 ID\'s\n'

        # Build the rows
        for prop1 in self.artistProperties:
            text += u'|-\n'
            text += u'| {{P|%s}}\n' % (prop1,)
            prop1number = self.propertyTotals.get(prop1)
            prop1painternumber = self.propertyPainterTotals.get(prop1)
            for prop2 in self.artistProperties:
                if prop1==prop2:
                    number = prop1number
                    painternumber = prop1painternumber
                    percentage = 100
                    painterpercentage = round(1.0 * painternumber / max(number, 1) * 100, 2)
                else:
                    if prop1 < prop2:
                        pair = (prop1, prop2)
                    else:
                        pair = (prop2, prop1)
                    number = self.propertyPairTotals.get(pair)
                    painternumber = self.propertyPairPainterTotals.get(pair)
                    percentage = round(1.0 * number / max(prop1number, 1) * 100, 2)
                    painterpercentage = round(1.0 * painternumber / max(prop1painternumber, 1) * 100, 2)
                text += u'| {{/Cell|%s|%s|%s|%s}}\n' % (percentage, number, painterpercentage, painternumber)
            text += u'| <!-- spacer -->\n'
            for i in range (1,12):
                number = self.propertyIdentifiers.get(prop1).get(i)
                painternumber = self.propertyPainterIdentifiers.get(prop1).get(i)
                percentage = round(1.0 * number / max(prop1number, 1) * 100, 2)
                painterpercentage = round(1.0 * painternumber / max(prop1painternumber, 1) * 100, 2)
                text += u'| {{/Cell|%s|%s|%s|%s}}\n' % (percentage, number, painterpercentage, painternumber)

            # Could insert identifier stuff here

        # Get the totals
        #totalworks = self.getPaintingTotals()

        #text += u'|- class="sortbottom"\n|\n|\'\'\'Totals\'\'\' <small>(all paintings)<small>:\n| %s\n' % (totalworks,)
        #for prop in self.properties:
        #    totalprop = self.getPaintingTotals(prop=prop)
        #    percentage = round(1.0 * totalprop / totalworks * 100, 2)
        #    text += u'| {{/Cell|%s|%s}}\n' % (percentage, totalprop)
        text += u'|}\n'
        text += u'{{/Footer}}\n'
        text += u'[[Category:WikiProject sum of all paintings|Painter authority statistics]]\n'

        page = pywikibot.Page(self.repo, title=self.targetPageTitle)
        summary = u'Painting property usage stats'
        print (text)
        page.put(text, summary)


def main(*args):
    """
    Main function. Bot does all the work.
    """
    painterAuthorityStatistics = PainterAuthorityStatistics()
    painterAuthorityStatistics.run()

if __name__ == "__main__":
    main()
