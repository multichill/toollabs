#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to compare Rijksmonumenten sources

* https://www.wikidata.org/wiki/Property:P359 - Rijksmonument ID
* https://www.wikidata.org/wiki/Property:P7135 - Rijksmonument complex ID


"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql


class RijksmonumentenCompareBot:
    """
    A bot to enrich humans on Wikidata
    """
    def __init__(self):
        """
        """
        self.repo = pywikibot.Site().data_repository()

        self.rce_endpoint = 'https://linkeddata.cultureelerfgoed.nl/_api/datasets/rce/cho/services/cho/sparql'
        self.rce_entity_url = 'https://linkeddata.cultureelerfgoed.nl/cho-kennis/id/'

        self.rijksmonumenten_wikidata = self.get_rijksmonumenten_wikidata()
        self.former_rijksmonumenten_wikidata = self.get_former_rijksmonumenten_wikidata()
        self.rijksmonumenten_rce = self.get_rijksmonumenten_rce()
        self.former_rijksmonumenten_rce = self.get_former_rijksmonumenten_rce()
        self.rijksmonument_complex_wikidata = self.get_rijksmonument_complex_wikidata()
        self.rijksmonument_complex_rce = self.get_rijksmonument_complex_rce()

    def get_rijksmonumenten_wikidata(self):
        """
        Just return all the usage of Rijksmonument ID as a dict
        :return: Dict
        """
        result = {}
        query = 'SELECT ?item ?id WHERE { ?item wdt:P359 ?id }'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            try:
                result[int(resultitem.get('id'))] = qid
            except ValueError:
                print (resultitem)
        return result

    def get_former_rijksmonumenten_wikidata(self):
        """
        Just return all the usage of Rijksmonument ID as a dict
        :return: Dict
        """
        result = {}
        query = 'SELECT ?item ?id WHERE { ?item p:P359 [ps:P359 ?id; wikibase:rank wikibase:DeprecatedRank]}'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
            try:
                result[int(resultitem.get('id'))] = qid
            except ValueError:
                print (resultitem)
        return result

    def get_rijksmonumenten_rce(self):
        """
        Just return all the usage of Rijksmonument ID as a dict
        :return: Dict
        """
        self.rce_endpoint = 'https://linkeddata.cultureelerfgoed.nl/_api/datasets/rce/cho/services/cho/sparql'
        self.rce_entity_url = 'https://linkeddata.cultureelerfgoed.nl/cho-kennis/id/'
        result = {}
        step = 10000
        for i in range(0, 70000, step):
            query = """PREFIX ceo: <https://linkeddata.cultureelerfgoed.nl/def/ceo#>
    PREFIX graph: <https://linkeddata.cultureelerfgoed.nl/graph/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT DISTINCT ?item ?id WHERE {
      ?item a ceo:Rijksmonument ;
            ceo:rijksmonumentnummer ?id 
      MINUS {?item ceo:heeftJuridischeStatus <https://data.cultureelerfgoed.nl/term/id/rn/3e79bb7c-b459-4998-a9ed-78d91d069227>}
    } LIMIT %s
    OFFSET %s""" % (step, i)
            sq = pywikibot.data.sparql.SparqlQuery(self.rce_endpoint, self.rce_entity_url)
            queryresult = sq.select(query)

            for resultitem in queryresult:
                qid = resultitem.get('item').replace(self.rce_entity_url, '')
                result[int(resultitem.get('id'))] = qid
        return result

    def get_former_rijksmonumenten_rce(self):
        """
        Just return all the usage of Rijksmonument ID as a dict
        :return: Dict
        """

        result = {}

        query = """PREFIX ceo: <https://linkeddata.cultureelerfgoed.nl/def/ceo#>
PREFIX graph: <https://linkeddata.cultureelerfgoed.nl/graph/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?item ?id WHERE {
  ?item ceo:rijksmonumentnummer ?id .
  ?item ceo:heeftJuridischeStatus <https://data.cultureelerfgoed.nl/term/id/rn/3e79bb7c-b459-4998-a9ed-78d91d069227> #}
} LIMIT 10000"""
        sq = pywikibot.data.sparql.SparqlQuery(self.rce_endpoint, self.rce_entity_url)
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(self.rce_entity_url, '')
            result[int(resultitem.get('id'))] = qid
        return result

    def get_rijksmonument_complex_wikidata(self):
        """
        Just return all the usage of Rijksmonument complex ID as a dict based on Wikidata
        :return: Dict
        """
        result = {}
        query = u'SELECT ?item ?id WHERE { ?item wdt:P7135 ?id }'
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[int(resultitem.get('id'))] = qid
        return result

    def get_rijksmonument_complex_rce(self):
        """
        Return all the usage of Rijksmonument complex ID as a dict based on the RCE platform
        :return: Dict
        """
        result = {}
        query = """PREFIX ceo: <https://linkeddata.cultureelerfgoed.nl/def/ceo#>
PREFIX graph: <https://linkeddata.cultureelerfgoed.nl/graph/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?item ?id WHERE {
      ?item a ceo:Complex ;
            ceo:complexnummer ?id 
      MINUS {?item ceo:heeftHoofdobject/ceo:heeftJuridischeStatus <https://data.cultureelerfgoed.nl/term/id/rn/3e79bb7c-b459-4998-a9ed-78d91d069227>}
    } LIMIT 10000"""
        sq = pywikibot.data.sparql.SparqlQuery(endpoint=self.rce_endpoint, entity_url=self.rce_entity_url)
        queryresult = sq.select(query)

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(self.rce_entity_url, '')
            result[int(resultitem.get('id'))] = qid
        #print (result)
        return result

    def run(self):
        """
        Starts the robot.
        """
        output = ''
        output += '__TOC__\n== Summary ==\n'
        output += '* Wikidata has %s keys\n' % (len(self.rijksmonumenten_wikidata.keys()))
        output += '* Wikidata has %s deprecated keys\n' % (len(self.former_rijksmonumenten_wikidata.keys()))
        output += '* RCE has %s keys\n' % (len(self.rijksmonumenten_rce.keys()))
        output += '* RCE has %s no Rijksmonument keys\n' % (len(self.former_rijksmonumenten_rce.keys()))

        both_sets = set(self.rijksmonumenten_wikidata.keys()) & set(self.rijksmonumenten_rce.keys())
        output += '* RCE and Wikidata have %s shared keys\n' % (len(both_sets), )

        both_former_sets = set(self.former_rijksmonumenten_wikidata.keys()) & set(self.former_rijksmonumenten_rce.keys())
        output += '* RCE and Wikidata have %s shared former keys\n' % (len(both_former_sets), )

        wikidata_not_rce = set(self.rijksmonumenten_wikidata.keys()).difference(set(self.rijksmonumenten_rce.keys()))
        wikidata_former_rce = wikidata_not_rce & (set(self.former_rijksmonumenten_rce.keys()))
        wikidata_all_not_rce = wikidata_not_rce.difference((set(self.former_rijksmonumenten_rce.keys())))

        rce_not_wikidata = set(self.rijksmonumenten_rce.keys()).difference(set(self.rijksmonumenten_wikidata.keys()))

        output += '* Wikidata and not RCE %s keys\n' % (len(wikidata_not_rce), )
        output += '* Wikidata and former RCE %s keys\n' % (len(wikidata_former_rce), )
        output += '* RCE and not Wikidata %s keys\n' % (len(rce_not_wikidata), )

        complex_both_sets = set(self.rijksmonument_complex_wikidata.keys()) & set(self.rijksmonument_complex_rce.keys())
        output += '* RCE and Wikidata have %s complex shared keys\n' % (len(complex_both_sets), )

        complex_wikidata_not_rce = set(self.rijksmonument_complex_wikidata.keys()).difference(set(self.rijksmonument_complex_rce.keys()))
        complex_rce_not_wikidata = set(self.rijksmonument_complex_rce.keys()).difference(set(self.rijksmonument_complex_wikidata.keys()))

        output += '* Complex Wikidata and not RCE %s keys\n' % (len(complex_wikidata_not_rce), )
        output += '* Complex RCE and not Wikidata %s keys\n' % (len(complex_rce_not_wikidata), )

        output += '== Wikidata former RCE ==\nShould be deprecated\n'
        for rm_id in sorted(wikidata_former_rce):
            output += '* %s - {{Q|%s}}\n' % (rm_id, self.rijksmonumenten_wikidata.get(rm_id))

        output += '== Wikidata not RCE ==\nShould be figured out\n'
        for rm_id in sorted(wikidata_all_not_rce):
            output += '* %s - {{Q|%s}}\n' % (rm_id, self.rijksmonumenten_wikidata.get(rm_id))

        output += '== RCE not Wikidata ==\n'
        cultureelerfgoed_url = 'https://monumentenregister.cultureelerfgoed.nl/monumenten/'
        for rm_id in sorted(rce_not_wikidata):
            output += '* %s - %s%s / %s%s\n' % (rm_id,
                                                        self.rce_entity_url,
                                                        self.rijksmonumenten_rce.get(rm_id),
                                                        cultureelerfgoed_url,
                                                        rm_id,)

        missing_no_rijksmonument = set(self.former_rijksmonumenten_rce.keys()).difference(set(self.rijksmonumenten_wikidata.keys())).difference(set(self.former_rijksmonumenten_wikidata.keys()))

        output += '== RCE former Rijksmonument not Wikidata ==\n'
        for rm_id in sorted(missing_no_rijksmonument):
            output += '* %s - %s%s\n' % (rm_id, self.rce_entity_url, self.former_rijksmonumenten_rce.get(rm_id), )

        output += '== Complex Wikidata not RCE ==\nShould be figured out\n'
        for rm_id in sorted(complex_wikidata_not_rce):
            output += '* %s - {{Q|%s}}\n' % (rm_id, self.rijksmonument_complex_wikidata.get(rm_id))

        output += '== Complex RCE not Wikidata ==\n'
        complex_cultureelerfgoed_url = 'https://monumentenregister.cultureelerfgoed.nl/complexen/'

        for rm_id in sorted(complex_rce_not_wikidata):
            output += '* %s - %s%s / %s%s\n' % (rm_id,
                                                self.rce_entity_url,
                                                self.rijksmonument_complex_rce.get(rm_id),
                                                complex_cultureelerfgoed_url,
                                                rm_id,)

        #pywikibot.output(output)
        page_title = 'User:Multichill/Rijksmonumenten'
        page = pywikibot.Page(self.repo, title=page_title)

        summary = 'RCE and Wikidata have %s shared keys' % (len(both_sets), )
        pywikibot.output(summary)
        page.put(output, summary)

def main(*args):
    Rijksmonumenten_compare_bot = RijksmonumentenCompareBot()
    Rijksmonumenten_compare_bot.run()

if __name__ == "__main__":
    main()
