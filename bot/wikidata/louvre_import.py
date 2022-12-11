#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Louvre to Wikidata.

The ark website at https://collections.louvre.fr/recherche?page=4&nCategory%5B0%5D=40&collection%5B0%5D=6 returns
a bit over 10.000 paintings from the Département des Peintures

For each entry they have json documented at https://collections.louvre.fr/en/page/documentationJSON

The paintings are all over France so adding that where possible

Use artdatabot to upload it to Wikidata
"""
import artdatabot
import pywikibot
import requests
import re
import html
from decimal import *

def get_louvre_generator():
    """
    Generator to return Louvre paintings
    """
    session = requests.Session()

    base_search_url = 'https://collections.louvre.fr/recherche?page=%s&nCategory%%5B0%%5D=40'

    loaners = {'Musée du Petit Palais, Avignon': 'Q1664416',
               'Musée des Beaux-arts, Arras': 'Q75566',
               'Musée des Beaux-Arts, Valenciennes': 'Q3330222',
               'Musée des Augustins, Toulouse': 'Q2711480',
               'Ecole Nationale Supérieure des Beaux-Arts de Paris, Paris': 'Q273593',
               'Musée des Beaux-Arts, Lille': 'Q2628596',
               'Musée des Beaux-Arts, Pau': 'Q3330217',
               'Musée des Beaux-Arts, Tours': 'Q2404549',
               'Musée Goya, Castres': 'Q246821',
               'Musée national du château de Fontainebleau, Fontainebleau': 'Q17560765',
               'Musée national du Château de Compiègne, Compiègne': 'Q516697',
               'Musée Hyacinthe Rigaud, Perpignan': 'Q3329201',
               'Château - Domaine national de Versailles, Versailles': 'Q3329787',
               'Musée Baron Martin, Gray': 'Q10333407',
               'Musée des Beaux-Arts, Strasbourg': 'Q1535963',
               'Musée Calvet, Avignon': 'Q1142988',
               'Musée d\'Orsay, Paris': 'Q23402',
               'Musées d’Amiens Métropole – Musée de Picardie, Amiens': 'Q3107709',
               'Musée des Beaux-Arts et d\'Archéologie, Besançon': 'Q1324926',
               'Musée des Beaux-Arts, Nantes': 'Q1783956',
               'Musée Bonnat-Helleu, Bayonne': 'Q2620702',
               'Musée des Beaux-Arts, Rennes': 'Q3098373',
               'Musée d\'Art et d\'Histoire, Cholet': 'Q3329613',
               'Musée des Beaux-Arts, Lyon': 'Q511',
               'Musée de Tessé, Le Mans': 'Q3329758',
               'Musée d\'Art moderne, Saint-Etienne': 'Q3329646',
               'Musée de la Chasse et de la Nature, Paris': 'Q1128657',
               'Musée des Beaux-Arts, Dijon': 'Q1955739',
               'Musée des Beaux-Arts, Reims': 'Q3330225',
               'Musée des Arts décoratifs, Paris': 'Q1319378',
               'Château royal et Musées de Blois, Blois': 'Q3330190',
               'Musée des Beaux Arts d\'Angers, Angers': 'Q3277885',
               'Musée Fabre, Montpellier': 'Q1519002',
               'Musée Massey, Tarbes': 'Q3329271',
               'Musée des Beaux-Arts Denys Puech, Rodez': 'Q3330186',
               'Musée Crozatier, Le Puy-en-Velay': 'Q3329125',
               'Musée des Beaux-Arts, Bordeaux': 'Q954222',
               'Musée d\'Art, d\'Archéologie et de Sciences naturelles, Troyes': 'Q3330226',
               'Musée des Beaux-Arts, Chambéry': 'Q3330197',
               'Musée Boucher-de-Perthes, Abbeville': 'Q3329099',
               'Musée de la Révolution française, Vizille': 'Q2389498',
               'Musée-Palais Fesch, Ajaccio': 'Q2483597',
               'Cathédrale Notre-Dame, Paris': 'Q2981',
               'Villa-Musée Jean-Honoré Fragonard, Grasse': 'Q22916181',
               'Musée national Eugène Delacroix, Paris': 'Q1782606',
               'Musée des Beaux-Arts, Caen': 'Q569079',
               'Musée d\'Art, Toulon': 'Q3329600',
               }
    # Musée du Louvre, Département des Peintures - 401 <- LOL
    # Palais du Luxembourg - Sénat, Paris - 30
    # Assemblée nationale, Paris - 28
    # Musée national de la Marine, Paris - 28 <- collection mess
    # Musée national de la Renaissance - Château d'Ecouen, Ecouen - 20 <- weird mix up
    # Musée de Chartres, Chartres - 19
    # Mairie, Versailles - 17

    owners = {'Campana, Giampietro, marquis di Cavelli': 'Q15934283',
              }

    missing_loaners = {}
    missing_owners = {}

    for i in range(1, 514):
        search_url = base_search_url % (i,)

        print(search_url)
        search_page = session.get(search_url)

        work_url_regex = '<a href="/ark:/53355/cl([^"]+)" class="h_4">([^<]+)</a>'
        matches = re.finditer(work_url_regex, search_page.text)

        for match in matches:
            metadata = {}
            url = 'https://collections.louvre.fr/ark:/53355/cl%s' % (match.group(1),)
            url_json = 'https://collections.louvre.fr/ark:/53355/cl%s.json' % (match.group(1),)

            item_page = session.get(url_json)
            item_json = item_page.json()
            pywikibot.output(url)
            metadata['url'] = url
            metadata['artworkidpid'] = 'P9394'  # Louvre Museum ARK ID
            metadata['artworkid'] = match.group(1)

            metadata['collectionqid'] = 'Q3044768'  # Search is for Département des Peintures
            metadata['collectionshort'] = 'Louvre'
            metadata['locationqid'] = 'Q19675'  # Will only be used if no more specific is available

            # Searching for paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            if item_json.get('objectNumber')[0].get('type') == 'Numéro principal':
                metadata['id'] = item_json.get('objectNumber')[0].get('value')
            elif len(item_json.get('objectNumber')) == 1:
                metadata['id'] = item_json.get('objectNumber')[0].get('value')
            else:
                print('ID FAILED, skipping this one for now')
                print(item_json.get('objectNumber'))
                continue

            ## Getting "Autre numéro d'inventaire" and 'Numéro dépositaire' here.
            #if len(item_json.get('objectNumber')) > 1:
            #    print('More identifiers found')
            #    print(item_json.get('objectNumber'))

            title = item_json.get('title')

            if title:
                # Chop chop, might have long titles
                if len(title) > 220:
                    title = title[0:200]
                # Some titles contain whitespace junk that the Wikibase API doesn't like
                title = title.replace('\t', '').replace('\n', '').replace('  ', ' ').strip()
                metadata['title'] = {'fr': title, }

            creators_found = 0
            name = ''
            name_prefix = ''
            creator_qid = ''
            other_attributions = ['Ancienne Attribution', 'Inventorié Comme']
            for possible_creator in item_json.get('creator'):
                if possible_creator.get('attributionLevel') == 'Attribution actuelle':
                    if possible_creator.get('linkType') == 'École de':
                        # Every painting seems to have the school added to it. Ignoring
                        pass
                    elif possible_creator.get('linkType') == '' and possible_creator.get('creatorRole') == '' and \
                            possible_creator.get('authenticationType') == '' and possible_creator.get('doubt') == '':
                        creators_found += 1
                        name = possible_creator.get('label')
                        creator_qid = possible_creator.get('wikidata')
                    elif possible_creator.get('linkType') and possible_creator.get('creatorRole') == '' and \
                            possible_creator.get('authenticationType') == '' and possible_creator.get('doubt') == '':
                        creators_found += 1
                        name = possible_creator.get('label')
                        name_prefix = possible_creator.get('linkType')
                elif possible_creator.get('attributionLevel') in other_attributions:
                    # Previous attributions ignored for now
                    pass
                else:
                    print('Unknown attribution level %s' % (possible_creator.get('attributionLevel'),))
                    creators_found += 100

            # If it has more than one (or none), a human should have a look
            if creators_found == 1:
                if ',' in name:
                    (surname, sep, firstname) = name.partition(',')
                    name = '%s %s' % (firstname.strip(), surname.strip(),)

                if name_prefix:
                    metadata['creatorname'] = '%s %s' % (name_prefix.lower().strip(), name.strip())
                    metadata['description'] = {'fr': '%s %s' % ('peinture', metadata.get('creatorname'), ),
                                                }
                    if creator_qid:
                        metadata['uncertaincreatorqid'] = creator_qid
                else:
                    metadata['creatorname'] = name.strip()
                    metadata['description'] = {'nl': '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                               'en': '%s by %s' % ('painting', metadata.get('creatorname'),),
                                               'de': '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                               'fr': '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                               }
                    if creator_qid:
                        metadata['creatorqid'] = creator_qid

            else:
                print('Number of attributions found %s' % (creators_found,))
                print(item_json.get('creator'))

            #print(item_json.get('dateCreated'))
            if item_json.get('dateCreated') and len(item_json.get('dateCreated'))==1:
                date_created = item_json.get('dateCreated')[0]
                if date_created.get('type') == 'Date de création/fabrication' and date_created.get('doubt') == '' and \
                        date_created.get('startYear'):
                    if date_created.get('endYear'):
                        metadata['inceptionstart'] = date_created.get('startYear')
                        metadata['inceptionend'] = date_created.get('endYear')
                    else:
                        metadata['inception'] = date_created.get('startYear')

                    if date_created.get('imprecision'):
                        metadata['inceptioncirca'] = True

            materials = { 'huile sur toile': 'oil on canvas'}
            ignore_materials = ['toile', 'bois']
            materials_and_techniques = item_json.get('materialsAndTechniques')

            if materials_and_techniques:
                if materials_and_techniques in materials:
                    metadata['medium'] = materials.get(materials_and_techniques)
                elif ignore_materials:
                    pass
                else:
                    print('Unable to match materials for %s' % (materials_and_techniques,))

            if item_json.get('dimension'):
                height = None
                width = None
                if len(item_json.get('dimension')) == 2:
                    height = item_json.get('dimension')[0]
                    width = item_json.get('dimension')[1]
                elif len(item_json.get('dimension')) == 4:
                    height = item_json.get('dimension')[0]
                    width = item_json.get('dimension')[2]
                if height and width:
                    if height.get('type') == 'Hauteur' and height.get('unit') == 'm' and height.get('value'):
                        decimal_height_cm = Decimal(height.get('value').replace(',', '.'))*100
                        if decimal_height_cm == decimal_height_cm.to_integral():
                            metadata['heightcm'] = '%s' % (decimal_height_cm.to_integral(), )
                        else:
                            metadata['heightcm'] = '%s' % (decimal_height_cm.normalize(), )
                    if width.get('type') == 'Largeur' and width.get('unit') == 'm' and width.get('value'):
                        decimal_width_cm = Decimal(width.get('value').replace(',', '.'))*100
                        if decimal_width_cm == decimal_width_cm.to_integral():
                            metadata['widthcm'] = '%s' % (decimal_width_cm.to_integral(), )
                        else:
                            metadata['widthcm'] = '%s' % (decimal_width_cm.normalize(), )

            if item_json.get('longTermLoanTo'):
                loaner = item_json.get('longTermLoanTo')
                if loaner in loaners:
                    metadata['extracollectionqid'] = loaners.get(loaner)
                    metadata['locationqid'] = loaners.get(loaner)  # Also use it for location
                else:
                    if loaner not in missing_loaners:
                        missing_loaners[loaner] = 0
                    missing_loaners[loaner] += 1

            # TODO: Parse current owner ("Etat")

            # TODO: Add previous collection Campana Collection
            # TODO: Add previous owner Campana???

            # TODO: Add MNR collection isMuseesNationauxRecuperation:True
            if item_json.get('isMuseesNationauxRecuperation'):
                metadata['extracollectionqid2'] = 'Q19013512'
            elif item_json.get('previousOwner') and len(item_json.get('previousOwner')) ==1:
                previous_owner = item_json.get('previousOwner')[0].get('value')
                if previous_owner in owners:
                    metadata['extracollectionqid2'] = owners.get(previous_owner)
                else:
                    if previous_owner not in missing_owners:
                        missing_owners[previous_owner] = 0
                    missing_owners[previous_owner] += 1

            yield metadata
            continue


            # TODO: Parse credit line
            credit_line_regex = '<div class="label">Credit line</div><div class="value">\s*([^<]+)</div>'
            credit_line_match = re.search(credit_line_regex, item_page.text)

            if credit_line_match:
                print(credit_line_match.group(1))
                acquisition_date_regex = '^.+ (\d\d\d\d)$'
                acquisition_date_match = re.match(acquisition_date_regex, credit_line_match.group(1))
                if acquisition_date_match:
                    metadata['acquisitiondate'] = acquisition_date_match.group(1)
                if 'bruikleen RCE' in credit_line_match.group(1):
                    metadata['extracollectionqid'] = 'Q18600731'

            image_regex = 'href="(https://dordrecht\.adlibhosting\.com/ais6/webapi/wwwopac\.ashx\?command=getcontent&amp;server=image&amp;imageformat=jpg&amp;value=[^"]+)"'
            image_match = re.search(image_regex, item_page.text)

            if image_match:
                image_url = html.unescape(image_match.group(1)).replace('server=image', 'server=images')
                recent_inception = False
                if metadata.get('inception') and metadata.get('inception') > 1924:
                    recent_inception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                    recent_inception = True
                if not recent_inception:
                    metadata['imageurl'] = image_url
                    metadata['imageurlformat'] = 'Q2195'  # JPEG
                    #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
                    metadata['imageoperatedby'] = metadata.get('collectionqid')
                    metadata['imageurlforce'] = False  # Used this to add suggestions everywhere
            yield metadata
        for owner in sorted(missing_owners, key=missing_owners.get, reverse=True)[0:25]:
            print('%s - %s' % (owner, missing_owners.get(owner)))
    for loaner in sorted(missing_loaners, key=missing_loaners.get, reverse=True)[0:25]:
        print('%s - %s' % (loaner, missing_loaners.get(loaner)))

def main(*args):
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        if arg.startswith('-create'):
            create = True

    paintingGen = get_louvre_generator()

    if dryrun:
        for painting in paintingGen:
            print(painting)
    else:
        artDataBot = artdatabot.ArtDataBot(paintingGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
