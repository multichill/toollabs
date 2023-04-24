#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
A bot to report OpenStreetMap relations missing Wikidata tag

See https://commons.wikimedia.org/wiki/Commons:Reverse_geocoding/Reports

"""
import pywikibot
import requests


class OsmMissingWikidata:
    """
    A bot to compare Wikidata and OpenStreetMap
    """
    def __init__(self):
        """
        Arguments: None
        """
        self.site = pywikibot.Site('commons', 'commons')

    def run(self):
        """

        :return:
        """
        limit = 5000
        text = 'Per admin levels the number of OpenStreetMap relations that don\'t have a Wikidata tag.\n'
        text += '{| class="wikitable sortable"\n'
        text += '!Admin level\n'
        text += '!Count\n'
        for admin_level in range(1, 11):
            count = self.check_admin_level(admin_level, limit)
            text += '|-\n'
            text += '| [[Commons:Reverse geocoding/Reports/Admin level %s|%s]]\n' % (admin_level, admin_level, )
            if count == limit:
                text += '| %s (hit limit)\n' % (count, )
            else:
                text += '| %s\n' % (count, )

        text += '|}\n'
        text += '[[Category:Commons reverse geocoding]]\n'

        page_title = 'Commons:Reverse geocoding/Reports/Admin_level_summary'
        page = pywikibot.Page(self.site, title=page_title)
        summary = 'Updating report'
        page.put(text, summary)

    def check_admin_level(self, admin_level, limit):
        """

        :return:
        """
        query = """[timeout:600][out:json];
rel[admin_level="%s"][boundary="administrative"][!wikidata];
out tags %s;""" % (admin_level, limit, )
        url = 'http://overpass-api.de/api/interpreter?data=%s' % (requests.utils.quote(query),)
        page = requests.get(url)
        json = page.json()

        count = len(json.get('elements'))

        text = '{| class="wikitable sortable"\n'
        text += '!OpenStreetMap\n'
        text += '!Name\n'
        text += '!Remark\n'

        for element in json.get('elements'):
            text += '|-\n'
            text += '| [https://www.openstreetmap.org/relation/%s %s]\n' % (element.get('id'), element.get('id'), )
            text += '| %s\n' % (element.get('tags').get('name'), )
            if element.get('tags').get('wikipedia'):
                text += '| [[%s]]\n' % (element.get('tags').get('wikipedia'), )
            elif element.get('tags').get('ISO3166-2'):
                text += '| ISO3166-2: %s\n' % (element.get('tags').get('ISO3166-2'), )
            else:
                text += '|\n'

        text += '|}\n'
        text += '[[Category:Commons reverse geocoding]]\n'

        page_title = 'Commons:Reverse geocoding/Reports/Admin_level_%s' % (admin_level,)
        page = pywikibot.Page(self.site, title=page_title)
        summary = 'Updating report, found %s' % (count, )
        page.put(text, summary)
        return count


def main(*args):
    """
    Main function.
    """
    osm_missing_wikidata = OsmMissingWikidata()
    osm_missing_wikidata.run()

if __name__ == "__main__":
    main()
