#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to match Berlinische Galerie arists to Wikidata.

They seems to use Emuseum with json output. Loop over all works and work on each artist once.
"""
import pywikibot
import requests
import re

def process_berlinische_galerie_works(dry_run=False, create=False):
    """
    Generator to return Berlinische Galerie works
    """
    # First one is just the painting
    #base_search_url = 'https://sammlung-online.berlinischegalerie.de/solr/published/select?&fq=type:Object&fq=loans_b:%%22false%%22&fq={!tag=et_classification_en_s}classification_en_s:(%%22Painting%%22)&q=*:*&rows=%s&sort=person_sort_en_s%%20asc&start=%s'
    base_search_url = 'https://sammlung-online.berlinischegalerie.de/solr/published/select?&fq=type:Object&fq=loans_b:%%22false%%22&&q=*:*&rows=%s&sort=person_sort_en_s%%20asc&start=%s'

    start_url = base_search_url % (1, 0, )

    session = requests.Session()
    start_page = session.get(start_url)
    number_found = start_page.json().get('response').get('numFound')

    # Trying to hide the json with a build id that changes
    collection_page = session.get('https://sammlung-online.berlinischegalerie.de/en/collection/')
    build_id_regex = '<script id="__NEXT_DATA__" type="application/json">.+"buildId":"([^"]+)","isFallback":false,"gsp":true,"scriptLoader":\[\]}</script>'
    build_id_match = re.search(build_id_regex, collection_page.text)
    build_id = build_id_match.group(1)

    step = 100

    current_artists = get_berlinische_galerie_artists_wikidata()
    ulan_artists = get_wikidata_lookup_table('P245')
    gnd_artists = get_wikidata_lookup_table('P227')
    visited_artists = []

    site = pywikibot.Site('de', 'wikipedia')
    repo = site.data_repository()

    for i in range(0, number_found + step, step):
        search_url = base_search_url % (step, i,)

        print(search_url)
        search_page = session.get(search_url)

        for object_docs in search_page.json().get('response').get('docs'):
            if not object_docs.get('person_ns'):
                continue
            for person_ns in object_docs.get('person_ns'):
                if person_ns in current_artists:
                    continue
                elif person_ns in visited_artists:
                    continue
                visited_artists.append(person_ns)
                print(person_ns)

                url = 'https://sammlung-online.berlinischegalerie.de/en/artists/artist/%s/' % (person_ns, )
                json_url = 'https://sammlung-online.berlinischegalerie.de/_next/data/%s/en/artists/artist/%s.json' % (build_id, person_ns, )

                pywikibot.output(url)
                pywikibot.output(json_url)

                json_page = session.get(json_url)
                if json_page.status_code == 404:
                    continue
                item_json = json_page.json().get('pageProps').get('data').get('item')
                print(item_json.get('PerPersonTxt'))
                print(item_json.get('PerURLLnk'))

                wikipedia_link = None
                ulan_link = None
                gnd_link = None
                for url_grp in item_json.get('PerUrlGrp'):
                    if url_grp.get('WebLinkLabel') == 'Wikipedia':
                        wikipedia_link = url_grp.get('WeblinkLnk')
                    elif url_grp.get('ULANLnk'):
                        ulan_link = url_grp.get('ULANLnk')
                    elif url_grp.get('GNDLnk'):
                        gnd_link = url_grp.get('GNDLnk')

                print(wikipedia_link)
                print(ulan_link)
                print(gnd_link)

                wikipedia_item = None
                ulan_item = None
                gnd_item = None
                if wikipedia_link and wikipedia_link.startswith('https://de.wikipedia.org/wiki/'):
                    try:
                        de_article_title = wikipedia_link.replace('https://de.wikipedia.org/wiki/', '')
                        de_page = pywikibot.Page(pywikibot.Link(de_article_title, source=site))
                        print(de_page.title())
                        wikipedia_item = pywikibot.ItemPage.fromPage(de_page)
                    except pywikibot.exceptions.NoPageError:
                        continue
                    except pywikibot.exceptions.InvalidTitleError:
                        continue
                if ulan_link and ulan_link.startswith('https://vocab.getty.edu/ulan/'):
                    ulan_id = ulan_link.replace('https://vocab.getty.edu/ulan/', '')
                    if ulan_id in ulan_artists:
                        ulan_qid = ulan_artists.get(ulan_id)
                        ulan_item = pywikibot.ItemPage(repo, ulan_qid)
                elif ulan_link and ulan_link.startswith('http://vocab.getty.edu/ulan/'):
                    ulan_id = ulan_link.replace('http://vocab.getty.edu/ulan/', '')
                    if ulan_id in ulan_artists:
                        ulan_qid = ulan_artists.get(ulan_id)
                        ulan_item = pywikibot.ItemPage(repo, ulan_qid)
                if gnd_link and gnd_link.startswith('https://d-nb.info/gnd/'):
                    gnd_id = gnd_link.replace('https://d-nb.info/gnd/', '')
                    if gnd_id in gnd_artists:
                        gnd_qid = gnd_artists.get(gnd_id)
                        gnd_item = pywikibot.ItemPage(repo, gnd_qid)
                elif gnd_link and gnd_link.startswith('http://d-nb.info/gnd/'):
                    gnd_id = gnd_link.replace('http://d-nb.info/gnd/', '')
                    if gnd_id in gnd_artists:
                        gnd_qid = gnd_artists.get(gnd_id)
                        gnd_item = pywikibot.ItemPage(repo, gnd_qid)

                if wikipedia_item:
                    claims = wikipedia_item.get().get('claims')
                    if 'P4580' in claims:
                        continue
                    new_claim = pywikibot.Claim(repo, 'P4580')
                    new_claim.setTarget(str(person_ns))
                    summary = '"%s" based on %s' % (item_json.get('PerPersonTxt'), wikipedia_link)
                    print(summary)
                    if not dry_run:
                        wikipedia_item.addClaim(new_claim, summary=summary)
                elif ulan_item:
                    claims = ulan_item.get().get('claims')
                    if 'P4580' in claims:
                        continue
                    new_claim = pywikibot.Claim(repo, 'P4580')
                    new_claim.setTarget(str(person_ns))
                    summary = '"%s" based on %s' % (item_json.get('PerPersonTxt'), ulan_link)
                    if not dry_run:
                        ulan_item.addClaim(new_claim, summary=summary)
                elif gnd_item:
                    claims = gnd_item.get().get('claims')
                    if 'P4580' in claims:
                        continue
                    new_claim = pywikibot.Claim(repo, 'P4580')
                    new_claim.setTarget(str(person_ns))
                    summary = '"%s" based on %s' % (item_json.get('PerPersonTxt'), gnd_link)
                    if not dry_run:
                        gnd_item.addClaim(new_claim, summary=summary)

def get_berlinische_galerie_artists_wikidata():
    """
    Get the artists for which we have a link
    """
    pywikibot.output('Loading Berlinische Galerie artist ID lookup table')
    result = {}
    query = 'SELECT ?item ?id WHERE { ?item wdt:P4580 ?id  }'
    sq = pywikibot.data.sparql.SparqlQuery()
    query_result = sq.select(query)

    for result_item in query_result:
        qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
        result[int(result_item.get('id'))] = qid
    pywikibot.output('Loaded %s Wikidata items for Berlinische Galerie artist ID' % (len(result,)))
    return result

def get_wikidata_lookup_table(wikidata_property):
    """
    Get a lookup table for a Wikidata property
    """
    pywikibot.output('Loading %s lookup table' % (wikidata_property, ))
    result = {}
    query = 'SELECT ?item ?id WHERE { ?item wdt:%s ?id  }' % (wikidata_property, )
    sq = pywikibot.data.sparql.SparqlQuery()
    query_result = sq.select(query)

    for result_item in query_result:
        qid = result_item.get('item').replace('http://www.wikidata.org/entity/', '')
        result[result_item.get('id')] = qid
    pywikibot.output('Loaded %s Wikidata items for %s' % (len(result),wikidata_property))
    return result


def main(*args):
    dry_run = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dry_run = True
        elif arg.startswith('-create'):
            create = True

    process_berlinische_galerie_works(dry_run=dry_run, create=create)


if __name__ == "__main__":
    main()
