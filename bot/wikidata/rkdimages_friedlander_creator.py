#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to create the missing Friedlander related items from RKDimages
See https://rkd.nl/en/explore/images#filters[bron_citeerafk]=Friedl%C3%A4nder+1967-1976

"""
import pywikibot
import requests
import pywikibot.data.sparql
import time


class FriedlanderRKDimagesCreator:
    def __init__(self, amount=10000):
        """
        Build the lookup table and get the generator
        """
        self.repo = pywikibot.Site().data_repository()
        self.amount = amount
        self.all_rkdimages_wikidata = self.rkdimages_on_wikidata()
        self.friedlander_missing_rkdimages = self.friedlander_missing_rkdimages_generator()

    def rkdimages_on_wikidata(self):
        """
        Return a dict with all the RKDimages on Wikidata.
        :return: Dict
        """
        result = {}
        query = """SELECT ?item ?id WHERE {
        ?item p:P350 ?idstatement.
        ?idstatement ps:P350 ?id.
        MINUS { ?idstatement wikibase:rank wikibase:DeprecatedRank. }
        }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        query_result = sq.select(query)

        for result_item in query_result:
            qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
            try:
                result[int(result_item.get('id'))] = qid
            except ValueError:
                # Unknown value will trigger this
                pass
        return result

    def friedlander_missing_rkdimages_generator(self):
        """
        Get a generator that returns Friedlander rekated missing RKDimages
        :return: A generator yielding metdata
        """
        start = 0
        rows = 50
        base_search_url = 'https://api.rkd.nl/api/search/images?filters[bron_citeerafk][]=Friedländer+1967-1976&sort[priref]=asc&format=json&start=%s&rows=%s'
        count = 0
        while count <= self.amount:
            search_url = base_search_url % (start, rows)
            search_page = requests.get(search_url)
            search_json = search_page.json()
            if not search_json.get('response') or not search_json.get('response').get('numFound'):
                # If we don't get a valid response, just return
                return
            numfound = search_json.get('response').get('numFound')

            if not start < numfound:
                return
            start = start + rows
            for rkdimage in search_json.get('response').get('docs'):
                rkdimage_id = rkdimage.get('priref')

                if rkdimage_id not in self.all_rkdimages_wikidata:
                    image_info = {}
                    image_info['id'] = '%s' % (rkdimage_id,)
                    image_info['url'] = 'https://rkd.nl/explore/images/%s' % (rkdimage_id,)
                    if rkdimage.get('benaming_kunstwerk') and rkdimage.get('benaming_kunstwerk')[0]:
                        nl_title = rkdimage.get('benaming_kunstwerk')[0]
                        if len(nl_title) > 220:
                            nl_title = nl_title[0:200]
                        image_info['title_nl'] = nl_title
                    if rkdimage.get('titel_engels'):
                        en_title = rkdimage.get('titel_engels')
                        if len(en_title) > 220:
                            en_title = en_title[0:200]
                        image_info['title_en'] = en_title
                    count += 1
                    yield image_info
                if count >= self.amount:
                    return

    def run(self):
        for image_info in self.friedlander_missing_rkdimages:
            self.create_missing_item(image_info)

    def create_missing_item(self, image_info):
        """
        Create the missing item based on the image_info
        :param image_info:
        :return:
        """
        data = {'labels': {},
                'descriptions': {},
                'claims': [],
                }
        if image_info.get('title_nl'):
            data['labels']['nl'] = {'language': 'nl', 'value': image_info.get('title_nl')}
        if image_info.get('title_en'):
            data['labels']['en'] = {'language': 'en', 'value': image_info.get('title_en')}

        #newclaim = pywikibot.Claim(self.repo, 'P31')
        #newclaim.setTarget(pywikibot.ItemPage(self.repo, 'Q3305213'))
        #data['claims'].append(newclaim.toJSON())

        newclaim = pywikibot.Claim(self.repo, 'P350')
        newclaim.setTarget(image_info.get('id'))
        data['claims'].append(newclaim.toJSON())

        identification = {}
        summary = 'Starting new Friedlander related artwork item for %s ' % (image_info['url'],)
        pywikibot.output(summary)
        result = self.repo.editEntity(identification, data, summary=summary)
        # I'm hitting some limits
        time.sleep(10)


def main(*args):
    friedlander_rkd_images_creator = FriedlanderRKDimagesCreator()
    friedlander_rkd_images_creator.run()


if __name__ == "__main__":
    main()
