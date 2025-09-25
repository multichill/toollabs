#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to convert own work images to SDoC (structured data on Commons).

https://commons.wikimedia.org/wiki/Category:Self-published_work contains about 25M files. The source, author and license
information should be converted to structured data format (https://commons.wikimedia.org/wiki/Commons:Structured_data).

Relevant modeling pages:
* https://commons.wikimedia.org/wiki/Commons:Structured_data/Modeling/Source
* https://commons.wikimedia.org/wiki/Commons:Structured_data/Modeling/Author
* https://commons.wikimedia.org/wiki/Commons:Structured_data/Modeling/Licensing

Should be switched to a more general Pywikibot implementation.

"""

import pywikibot
import re
import pywikibot.data.sparql
import time
import json
from pywikibot import pagegenerators

class OwnWorkBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, gen, loose, alwaystouch, fileownwork, authorpage, authorname, authorqid, filelicenses):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()

        self.informationTemplates = ['information',
                                     'photograph',
                                     'specimen']
        self.validLicenses = self.getLicenseTemplates()
        self.pubDedication = ['Q6938433',
                              'Q98592850',
                              'Q152481',
                              'Q10249'
                              ]
        self.participantTemplates = self.getParticipantTemplates()
        self.sponsorTemplates = self.getSponsorTemplates()
        self.exifCameraMakeModel = self.getExifCameraMakeModel()
        self.generator = gen
        self.loose = loose
        self.alwaystouch = alwaystouch
        self.fileownwork = fileownwork
        self.authorpage = authorpage
        self.authorname = authorname
        self.authorqid = authorqid
        self.filelicenses = filelicenses

    def getLicenseTemplates(self):
        """
        Get the template to qid mappings for license templates
        Everything all lowercase and spaces instead of underscores
        :return: dict()
        """
        # FIXME: Do query later
        result = { 'attribution only license' : 'Q98923445',
                   'attribution' : 'Q98923445',
                   'bild-by' : 'Q98923445',
                   'bsd' : 'Q191307', # One template and tracker category for multiple versions
                   'beerware' : 'Q10249',
                   'cc-zero' : 'Q6938433',
                   'cc0' : 'Q6938433',
                   'cc-0' : 'Q6938433',
                   'careware' : 'Q6938433',
                   'cc-by-1.0' : 'Q30942811',
                   'cc-by-1.0-fi' : 'Q75446635',
                   'cc-by-1.0-il' : 'Q75446609',
                   'cc-by-1.0-nl' : 'Q75445499',
                   'cc-by-2.0' : 'Q19125117',
                   'cc-by-2.0-at' : 'Q75450165',
                   'cc-by-2.0-au' : 'Q75452310',
                   'cc-by-2.0-be' : 'Q75457467',
                   'cc-by-2.0-br' : 'Q75457506',
                   'cc-by-2.0-ca' : 'Q75460106',
                   'cc-by-2.0-cl' : 'Q75460149',
                   'cc-by-2.0-de' : 'Q75466259',
                   'cc-by-2.0-es' : 'Q75470365',
                   'cc-by-2.0-fr' : 'Q75470422',
                   'cc-by-2.0-hr' : 'Q75474094',
                   'cc-by-2.0-it' : 'Q75475677',
                   'cc-by-2.0-jp' : 'Q75477775',
                   'cc-by-2.0-kr' : 'Q44282633',
                   'cc-by-2.0-nl' : 'Q75476747',
                   'cc-by-2.0-pl' : 'Q75486069',
                   'cc-by-2.0-tw' : 'Q75487055',
                   'cc-by-2.0-uk' : 'Q63241773',
                   'cc-by-2.0-za' : 'Q75488238',
                   'cc-by-2.1-au' : 'Q75894680',
                   'cc-by-2.1-es' : 'Q75894644',
                   'cc-by-2.1-jp' : 'Q26116436',
                   'cc-by-2.5' : 'Q18810333',
                   'cc-by-2.5-ar' : 'Q75491630',
                   'cc-by-2.5-au' : 'Q75494411',
                   'cc-by-2.5-bg' : 'Q75500112',
                   'cc-by-2.5-br' : 'Q75501683',
                   'cc-by-2.5-ca' : 'Q75504835',
                   'cc-by-2.5-ch' : 'Q75506669',
                   'cc-by-2.5-cn' : 'Q75434631',
                   'cc-by-2.5-co' : 'Q75663969',
                   'cc-by-2.5-dk' : 'Q75665696',
                   'cc-by-2.5-es' : 'Q75705948',
                   'cc-by-2.5-hr' : 'Q75706881',
                   'cc-by-2.5-hu' : 'Q75759387',
                   'cc-by-2.5-il' : 'Q75759731',
                   'cc-by-2.5-in' : 'Q75443434',
                   'cc-by-2.5-it' : 'Q75760479',
                   'cc-by-2.5-mk' : 'Q75761383',
                   'cc-by-2.5-mt' : 'Q75761779',
                   'cc-by-2.5-mx' : 'Q75762418',
                   'cc-by-2.5-my' : 'Q75762784',
                   'cc-by-2.5-nl' : 'Q75763101',
                   'cc-by-2.5-pe' : 'Q75764151',
                   'cc-by-2.5-pl' : 'Q75764470',
                   'cc-by-2.5-pt' : 'Q75764895',
                   'cc-by-2.5-scotland' : 'Q75765287',
                   'cc-by-2.5-se' : 'Q27940776',
                   'cc-by-2.5-si' : 'Q75766316',
                   'cc-by-2.5-tw' : 'Q75767185',
                   'cc-by-2.5-za' : 'Q75767606',
                   'cc-by 3.0' : 'Q14947546',
                   'cc-by-3.0' : 'Q14947546',
                   'cc-by-3.0-at' : 'Q75768706',
                   'cc-by-3.0-au' : 'Q52555753',
                   'cc-by-3.0-br' : 'Q75770766',
                   'cc-by-3.0-ch' : 'Q75771320',
                   'cc-by-3.0-cl' : 'Q75771874',
                   'cc-by-3.0-cn' : 'Q75779562',
                   'cc-by-3.0-cr' : 'Q75789929',
                   'cc-by-3.0-cz' : 'Q67918154',
                   'cc-by-3.0-de' : 'Q62619894',
                   'cc-by-3.0-ec' : 'Q75850366',
                   'cc-by-3.0-ee' : 'Q75850813',
                   'cc-by-3.0-eg' : 'Q75850832',
                   'cc-by-3.0-es' : 'Q75775133',
                   'cc-by-3.0-fr' : 'Q75775714',
                   'cc-by-3.0-gr' : 'Q75851799',
                   'cc-by-3.0-gt' : 'Q75852313',
                   'cc-by-3.0-hk' : 'Q75779905',
                   'cc-by-3.0-hr' : 'Q75776014',
                   'cc-by-3.0-ie' : 'Q75852938',
                   'cc-by-3.0-igo' : 'Q26259495',
                   'cc-by-3.0-it' : 'Q75776487',
                   'cc-by-3.0-lu' : 'Q75853187',
                   'cc-by-3.0-nl' : 'Q53859967',
                   'cc-by-3.0-no' : 'Q75853549',
                   'cc-by-3.0-nz' : 'Q75853514',
                   'cc-by-3.0-ph' : 'Q75856699',
                   'cc-by-3.0-pl' : 'Q75777688',
                   'cc-by-3.0-pr' : 'Q75857518',
                   'cc-by-3.0-pt' : 'Q75854323',
                   'cc-by-3.0-ro' : 'Q75858169',
                   'cc-by-3.0-rs' : 'Q75859019',
                   'cc-by-3.0-sg' : 'Q75859751',
                   'cc-by-3.0-th' : 'Q75866892',
                   'cc-by-3.0-tw' : 'Q75778801',
                   'cc-by-3.0-ug' : 'Q75882470',
                   'cc-by-3.0-us' : 'Q18810143',
                   'cc-by-3.0-vn' : 'Q75889409',
                   'cc-by-3.0,2.5,2.0,1.0' : ['Q14947546', 'Q18810333', 'Q19125117', 'Q30942811'],
                   'cc-by-all' : ['Q20007257', 'Q14947546', 'Q18810333', 'Q19125117', 'Q30942811'],
                   'cc by 4.0' : 'Q20007257',
                   'cc-by 4.0' : 'Q20007257',
                   'cc-by-4.0' : 'Q20007257',
                   'cc-by-sa-1.0' : 'Q47001652',
                   'cc-by-sa-1.0-fi' : 'Q76767348',
                   'cc-by-sa-1.0-il' : 'Q76769447',
                   'cc-by-sa-1.0-nl' : 'Q77014037',
                   'cc-by-sa-old' : 'Q47001652',
                   'cc-by-sa-1.0+' : ['Q18199165', 'Q14946043', 'Q19113751', 'Q19068220', 'Q47001652'],
                   'cc-by-sa-2.0' : 'Q19068220',
                   'cc-by-sa-2.0+' : ['Q18199165', 'Q14946043', 'Q19113751', 'Q19068220'],
                   'cc-by-sa-2.0-at' : 'Q77021108',
                   'cc-by-sa-2.0-au' : 'Q77131257',
                   'cc-by-sa-2.0-be' : 'Q77132386',
                   'cc-by-sa-2.0-br' : 'Q77133402',
                   'cc-by-sa-2.0-ca' : 'Q77135172',
                   'cc-by-sa-2.0-cl' : 'Q77136299',
                   'cc-by-sa-2.0-de' : 'Q77143083',
                   'cc-by-sa-2.0-es' : 'Q77352646',
                   'cc-by-sa-2.0-fr' : 'Q77355872',
                   'cc-by-sa-2.0-hr' : 'Q77361415',
                   'cc-by-sa-2.0-it' : 'Q77362254',
                   'cc-by-sa-2.0-jp' : 'Q77363039',
                   'cc-by-sa-2.0-kr' : 'Q44282641',
                   'cc-by-sa-2.0-nl' : 'Q77363856',
                   'cc-by-sa-2.0-pl' : 'Q77364488',
                   'cc-by-sa-2.0-tw' : 'Q77364872',
                   'cc-by-sa-2.0-uk' : 'Q77365183',
                   'cc-by-sa-2.0-za' : 'Q77365530',
                   'cc-by-sa-2.1-au' : 'Q77366066',
                   'cc-by-sa-2.1-es' : 'Q77366576',
                   'cc-by-sa-2.1-jp' : 'Q77367349',
                   'cc-by-sa-2.5' : 'Q19113751',
                   'cc-by-sa-2.5-ar' : 'Q99239269',
                   'cc-by-sa-2.5-au' : 'Q99239530',
                   'cc-by-sa-2.5-bg' : 'Q99239903',
                   'cc-by-sa-2.5-br' : 'Q99239977',
                   'cc-by-sa-2.5-ca' : 'Q24331618',
                   'cc-by-sa-2.5-ch' : 'Q99240068',
                   'cc-by-sa-2.5-cn' : 'Q99240158',
                   'cc-by-sa-2.5-co' : 'Q99240246',
                   'cc-by-sa-2.5-dk' : 'Q99240336',
                   'cc-by-sa-2.5-es' : 'Q99240437',
                   'cc-by-sa-2.5-hr' : 'Q99240535',
                   'cc-by-sa-2.5-hu' : 'Q98755330',
                   'cc-by-sa-2.5-il' : 'Q99240616',
                   'cc-by-sa-2.5-in' : 'Q99240684',
                   'cc-by-sa-2.5-it' : 'Q98929925',
                   'cc-by-sa-2.5-mk' : 'Q99437988',
                   'cc-by-sa-2.5-mt' : 'Q99438077',
                   'cc-by-sa-2.5-mx' : 'Q99438138',
                   'cc-by-sa-2.5-my' : 'Q99438269',
                   'cc-by-sa-2.5-nl' : 'Q18199175',
                   'cc-by-sa-2.5-pe' : 'Q99438515',
                   'cc-by-sa-2.5-pl' : 'Q98755337',
                   'cc-by-sa-2.5-pt' : 'Q99438743',
                   'cc-by-sa-2.5-scotland' : 'Q99438747',
                   'cc-by-sa-2.5-se' : 'Q15914252',
                   'cc-by-sa-2.5-si' : 'Q99438751',
                   'cc-by-sa-2.5-sl' : 'Q99438751',
                   'cc-by-sa-2.5-tw' : 'Q99438755',
                   'cc-by-sa-2.5-za' : 'Q99438757',
                   'cc-by-sa-2.5,2.0,1.0' : ['Q19113751', 'Q19068220', 'Q47001652'],
                   'cc-by-sa 3.0' : 'Q14946043',
                   'cc-by-sa-3.0' : 'Q14946043',
                   'cc-by-sa-3.0,2.5,2.0,1.0' : ['Q14946043', 'Q19113751', 'Q19068220', 'Q47001652'],
                   'cc-by-sa-3.0-migrated' : 'Q14946043', # Just cc-by-sa-3.0
                   'cc-by-sa-3.0-migrated-with-disclaimers' : 'Q14946043',
                   'cc-by-sa-3.0-at' : 'Q80837139',
                   'cc-by-sa-3.0-au' : 'Q86239208',
                   'cc-by-sa-3.0-br' : 'Q98755369',
                   'cc-by-sa-3.0-ch' : 'Q99457378',
                   'cc-by-sa-3.0-cl' : 'Q99457535',
                   'cc-by-sa-3.0-cn' : 'Q99458406',
                   'cc-by-sa-3.0-cr' : 'Q99458659',
                   'cc-by-sa-3.0-cz' : 'Q98755321',
                   'cc-by-sa-3.0-de' : 'Q42716613',
                   'bild-cc-by-sa/3.0/de' : 'Q42716613',
                   'cc-by-sa-3.0-ec' : 'Q99458819',
                   'cc-by-sa-3.0-ee' : 'Q86239559',
                   'cc-by-sa-3.0-es' : 'Q86239991',
                   'cc-by-sa-3.0-fr' : 'Q86240326',
                   'cc-by-sa-3.0-gr' : 'Q99457707',
                   'cc-by-sa-3.0-gt' : 'Q99459010',
                   'cc-by-sa-3.0-hk' : 'Q99459076',
                   'cc-by-sa-3.0-hr' : 'Q99459365',
                   'cc-by-sa-3.0-ie' : 'Q99459488',
                   'cc-by-sa-3.0-igo' : 'Q56292840',
                   'cc-by-sa-3.0-it' : 'Q98755364',
                   'cc-by-sa-3.0-lu' : 'Q86240624',
                   'cc-by-sa-3.0-nl' : 'Q18195572',
                   'cc-by-sa-3.0-no' : 'Q63340742',
                   'cc-by-sa-3.0-nz' : 'Q99438798',
                   'cc-by-sa-3.0-ph' : 'Q99460006',
                   'cc-by-sa-3.0-pl' : 'Q80837607',
                   'cc-by-sa-3.0-pr' : 'Q99460154',
                   'cc-by-sa-3.0-pt' : 'Q99460272',
                   'cc-by-sa-3.0-ro' : 'Q86241082',
                   'cc-by-sa-3.0-rs' : 'Q98755344',
                   'cc-by-sa-3.0-sg' : 'Q99460356',
                   'cc-by-sa-3.0-th' : 'Q99460411',
                   'cc-by-sa-3.0-tw' : 'Q98960995',
                   'cc-by-sa-3.0-ug' : 'Q99460475',
                   'cc-by-sa-3.0-us' : 'Q18810341',
                   'cc-by-sa-3.0-vn' : 'Q99460484',
                   'cc-by-sa-3.0-za' : 'Q99460515',
                   'cc-by-sa 4.0' : 'Q18199165',
                   'cc-by-sa-4.0' : 'Q18199165',
                   'cc by-sa 4.0' : 'Q18199165',
                   'cc-by-sa-4.0,3.0,2.5,2.0,1.0' : ['Q18199165', 'Q14946043', 'Q19113751', 'Q19068220', 'Q47001652'],
                   'cc-by-sa-all' : ['Q18199165', 'Q14946043', 'Q19113751', 'Q19068220', 'Q47001652'],
                   'cc-sa-1.0' : 'Q75209430',
                   'cc-sa' : 'Q75209430',
                   'cecill' : 'Q1052189',
                   'copyrighted free use' : 'Q99578078',
                   'copyrightedfreeuse' : 'Q99578078',
                   'fal' : 'Q152332',
                   'art libre' : 'Q152332',
                   'fal-1.3' : 'Q152332', # Less than 100 files, could be a new more specific item
                   'flickr-no known copyright restrictions' : 'Q99263261',
                   'gfdl' : 'Q50829104',
                   'gfdl-no-disclaimers' : 'Q50829104',
                   'gfdl-disclaimers' : 'Q50829104',
                   'gfdl-con-disclaimer' : 'Q50829104',
                   'gfdl-disclamers' : 'Q50829104',
                   'gfdl-with-disclaimers' : 'Q50829104',
                   'gfdl-gmt' : 'Q50829104',
                   'gfdl-el' : 'Q50829104',
                   'gfdl-en' : 'Q50829104',
                   'gfdl-it' : 'Q50829104',
                   'gfdl-ja' : 'Q50829104',
                   'gfdl-sr' : 'Q50829104',
                   'bild-gfdl-neu' : 'Q50829104',
                   'gfdl-user-w' : 'Q50829104',
                   'gfdl-1.2' : 'Q26921686',
                   'gfdl 1.2' : 'Q26921686',
                   'gfdl-1.2-en' : 'Q26921686',
                   'gfdl 1.2 or cc-by-nc-2.0' : 'Q26921686',
                   'cc-by-nc-2.0-dual' : 'Q26921686',
                   'gfdl 1.2 or cc-by-nc-3.0' : 'Q26921686',
                   'gfdl 1.2 or cc-by-nc 3.0' : 'Q26921686',
                   'gfdl-1.3' : 'Q27019786',
                   'gfdl 1.3' : 'Q27019786',
                   'gfdl-1.3-only' : 'Q26921691',
                   'gfdl-1.1,1.2,1.3' : ['Q26921685', 'Q26921686', 'Q26921691'],
                   'gplv2 only' : 'Q10513450',
                   'gplv2' : 'Q10513450',
                   'gplv2+' : 'Q27016752',
                   'gpl' : 'Q27016752',
                   'gplv3 only' : 'Q10513445',
                   'gplv3' : 'Q27016754',
                   'agpl' : 'Q27020062',
                   'lgplv2.1+' : 'Q27016757',
                   'lgpl' : 'Q27016757',
                   'lgplv3' : 'Q27016762',
                   'mit' : 'Q334661', # See the MIT license article
                   'expat' : 'Q334661',
                   'x11' : 'Q334661',
                   'godl-india' : 'Q99891295',
                   'ogl' : 'Q99891660',
                   'ogl2' : 'Q99891692',
                   'ogl3' : 'Q99891702',
                   'pd-author' : 'Q98592850',
                   'pd-heirs' : 'Q98592850',
                   'pd-self' : 'Q98592850', #  released into the public domain by the copyright holder (Q98592850)
                   'pd-release' : 'Q98592850',
                   'pd-user' : 'Q98592850',
                   'pd-user-at-project' : 'Q98592850',
                   'pd-user-w' : 'Q98592850',
                   'pd-retouched-user' : 'Q98592850',
                   'pdmark-owner' : 'Q98592850', # Idiots
                   'cc-pd' : 'Q98592850', # More crap
                   'wtfpl' : 'Q152481',
                   }
        return result

    def getParticipantTemplates(self):
        """
        Get the template to qid mappings for participation templates
        Everything all lowercase and spaces instead of underscores
        :return: dict()
        """
        result = { 'wiki loves earth 2013': 'Q98768417',
                   'wiki loves earth 2014': 'Q15978259',
                   'wiki loves earth 2015': 'Q23953679',
                   'wiki loves earth 2016': 'Q23946940',
                   'wiki loves earth 2017': 'Q98751859',
                   'wiki loves earth 2018': 'Q98751978',
                   'wiki loves earth 2019': 'Q98752118',
                   'wiki loves earth 2020': 'Q97331615',
                   'wiki loves earth 2021': 'Q105954660',
                   'wiki loves earth 2022': 'Q111498696',
                   'wiki loves earth 2023': 'Q117447474',
                   'wiki loves earth 2024': 'Q124666252',
                   'wiki loves earth 2025': 'Q132532301',
                   'wiki loves monuments 2010': 'Q20890568',
                   'wiki loves monuments 2011': 'Q8168264',
                   'wiki loves monuments 2012': 'Q13390164',
                   'wiki loves monuments 2013': 'Q14568386',
                   'wiki loves monuments 2014': 'Q15975254',
                   'wiki loves monuments 2015': 'Q19833396',
                   'wiki loves monuments 2016': 'Q26792317',
                   'wiki loves monuments 2017': 'Q30015204',
                   'wiki loves monuments 2018': 'Q56165596',
                   'wiki loves monuments 2019': 'Q56427997',
                   'wiki loves monuments 2020': 'Q66975112',
                   'wiki loves monuments 2021': 'Q106533232',
                   'wiki loves monuments 2022': 'Q111382293',
                   'wiki loves monuments 2023': 'Q119978762',
                   'wiki loves monuments 2024': 'Q124255587',
                   'wiki loves monuments 2025': 'Q131411758',
                   'wiki loves monuments 2026': 'Q136339403',
                   }
        return result

    def getSponsorTemplates(self):
        """
        Get the template to qid mappings for participation templates
        Everything all lowercase and spaces instead of underscores
        :return: dict()
        """
        result = { 'supported by wikimedia argentina' : 'Q18559618',
                   'supported by wikimedia armenia' : 'Q20515521',
                   'supported by wikimedia ch' : 'Q15279140',
                   'supported by wikimedia deutschland' : 'Q8288',
                   'supported by wikimedia españa' : 'Q14866877',
                   'supported by wikimedia france' : 'Q8423370',
                   'supported by wikimedia israel' : 'Q16130851',
                   'supported by wikimedia österreich' : 'Q18559623',
                   'supported by wikimedia polska' : 'Q9346299',
                   'supported by wikimedia uk' : 'Q7999857',
                   }
        return result

    def getExifCameraMakeModel(self):
        """
        Do a SPARQL query to get the exif make and model lookup table
        :return: Dict with (make, model) as keys
        """
        query = """SELECT ?item ?make ?model WHERE {
  ?item wdt:P2010 ?make ;
        wdt:P2009 ?model ;
        }"""
        sq = pywikibot.data.sparql.SparqlQuery()
        queryresult = sq.select(query)
        result = {}

        for resultitem in queryresult:
            qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
            result[(resultitem.get('make'),resultitem.get('model'))] = qid
        return result

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.getCurrentMediaInfo(mediaid)
            self.handleOwnWork(filepage, mediaid, currentdata)

    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return that so we can expand it.
        Otherwise return an empty structure with just <s>claims</>statements in it to start
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: json
            """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M52611909
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M10038
        request = self.site.simple_request(action='wbgetentities', ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def handleOwnWork(self, filepage, mediaid, currentdata):
        """
        Handle a single own work file.
        Try to extract the template, look up the id and add the Q if no mediainfo is present.

        :param filepage: The page of the file to work on.
        :return: Nothing, edit in place
        """
        pywikibot.output(u'Working on %s' % (filepage.title(),))
        if not filepage.exists():
            return

        if not filepage.has_permission():
            # Picture might be protected
            return

        # Check if the file is own work
        ownwork = self.isOwnWorkFile(filepage)
        if not ownwork and not self.loose:
            pywikibot.output(u'No own and self templates found on %s, skipping' % (filepage.title(),))
            return

        # Get the author
        authorInfo = self.getAuthor(filepage)
        if not authorInfo and not self.authorqid and not self.loose:
            pywikibot.output(u'Unable to extract author on %s, skipping' % (filepage.title(),))
            return

        # Get one or more licenses
        licenses = self.getSelfLicenses(filepage)
        if not licenses and not self.loose:
            pywikibot.output(u'Unable to extract licenses on %s, skipping' % (filepage.title(),))
            return

        # Need to have found something to continue in loose mode
        if self.loose and not ownwork and (not authorInfo or not self.authorqid) and not licenses:
            pywikibot.output(u'Loose mode, but did not find anything on %s, skipping' % (filepage.title(),))
            return

        # Here we're collecting
        newclaims = {}

        # We got all the needed info, let's add it
        if ownwork:
            newclaims['source'] = self.addSourceOwn(mediaid, currentdata)
        if self.authorqid:
            newclaims['author'] = self.addAuthorQid(mediaid, currentdata, self.authorqid)
        elif authorInfo:
            (authorPage, authorName) = authorInfo
            newclaims['author'] = self.addAuthor(mediaid, currentdata, authorPage, authorName)
        # Try alternatives for sourcing like Flickr, Geograph and Panoramico
        if not ownwork and not self.authorqid and not authorInfo:
            othersource = self.getOtherSource(mediaid, currentdata, filepage)
            if othersource:
                (othersourcename, othersouceclaims) = othersource
                newclaims[othersourcename] = othersouceclaims
        if licenses:
            newclaims['copyright'] = self.addLicenses(mediaid, currentdata, licenses)
        # Optional stuff, maybe split that up too
        newclaims['date'] = self.handleDate(mediaid, currentdata, filepage)
        # TODO: Consider adding date from exif DateTimeOriginal if nothing is found
        newclaims['coordinates'] = self.handlePointOfViewCoordinates(mediaid, currentdata, filepage)
        newclaims['object coordinates'] = self.handleObjectCoordinates(mediaid, currentdata, filepage)
        newclaims['camera'] = self.handleCameraMakeModel(mediaid, currentdata, filepage)
        newclaims['participant'] = self.handleParticipant(mediaid, currentdata, filepage)
        newclaims['sponsor'] = self.handleSponsor(mediaid, currentdata, filepage)

        addedclaims = []

        itemdata = {u'claims' : [] }

        for newclaim in newclaims:
            if newclaims.get(newclaim):
                itemdata['claims'].extend(newclaims.get(newclaim))
                addedclaims.append(newclaim)

        if len(addedclaims) > 0:
            summary = u'Adding structured data: %s' % (addedclaims[0],)
            if len(addedclaims) > 2:
                for i in range(1, len(addedclaims)-1):
                    summary = summary + u', %s' % (addedclaims[i],)
            if len(addedclaims) > 1:
                summary = summary + u' & %s' % (addedclaims[-1],)

            # Flush it
            pywikibot.output(summary)

            token = self.site.tokens['csrf']
            postdata = {'action': 'wbeditentity',
                        'format': 'json',
                        'id': mediaid,
                        'data': json.dumps(itemdata),
                        'token': token,
                        'summary': summary,
                        'bot': True,
                        'tags': 'BotSDC'
                        }
            if currentdata:
                # This only works when the entity has been created
                postdata['baserevid'] = currentdata.get('lastrevid')

            request = self.site.simple_request(**postdata)
            try:
                data = request.submit()
                # Always touch the page to flush it
                filepage.touch()
            except (pywikibot.exceptions.APIError, pywikibot.exceptions.OtherPageSaveError):
                pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
                # Print the offending token
                print (token)
                time.sleep(30)
                # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
                self. site.tokens.load_tokens(['csrf'])
                # This should be a new token
                print (self.site.tokens['csrf'])
        elif self.alwaystouch:
            try:
                filepage.touch()
            except:
                pywikibot.output('Got an API error while touching page. Sleeping, getting a new token and skipping')
                self. site.tokens.load_tokens(['csrf'])


    def isOwnWorkFile(self, filepage):
        """
        Check if the file is own work. We do that by looking for both the "own" and the "self" template.
        :param filepage: The page of the file to work on.
        :return:
        """
        if self.fileownwork:
            pywikibot.output(u'Own work forced!')
            return True
        ownfound = False
        selfFound = False

        ownTemplates = ['Template:Own',
                        'Template:Own photograph',
                        'Template:Own work by original uploader',
                        'Template:Self-photographed',
                        ]
        selfTemplates = ['Template:Self',
                         'Template:PD-self',
                         ]

        for template in filepage.itertemplates():
            if template.title() in ownTemplates:
                ownfound = True
            elif template.title() in selfTemplates:
                selfFound = True

        if ownfound and selfFound:
            pywikibot.output(u'Own work found!')
            return True
        return False

    def getAuthor(self, filepage):
        """
        Extract the author form the information template
        :param filepage: The page of the file to work on.
        :return: Tuple with a User and a string
        """
        if self.authorpage and self.authorname:
            return (pywikibot.User(self.site, self.authorpage), self.authorname)
        elif self.authorpage:
            return (pywikibot.User(self.site, self.authorpage), self.authorpage)
        elif self.authorname:
            return (pywikibot.User(self.site, self.authorname), self.authorname)

        authorRegex = u'^\s*[aA]uthor\s*\=\s*\[\[[uU]ser\:([^\|^\]]+)\|([^\|^\]]+)\]\](\s*\(\s*\[\[[uU]ser talk\:[^\|^\]]+\|[^\|^\]]+\]\]\s*\)\s*)?\s*$'

        for template, parameters in filepage.templatesWithParams():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.informationTemplates:
                for field in parameters:
                    if field.lower().startswith(u'author'):
                        match = re.match(authorRegex, field)
                        if match:
                            try:
                                authorPage = pywikibot.User(self.site, match.group(1))
                            except pywikibot.exceptions.InvalidTitleError:
                                # Sometimes weird junk in the field. Just skip it
                                return False
                            authorName = match.group(2).strip()
                            return (authorPage, authorName)
                        # The author regex didn't match. Let's get the uploader in the log to compare
                        # Todo, do a bit of trickery to detect a customer user template like {{User:<user>/<something}}
                        else:
                            pywikibot.output(field)
                        break

        return False

    def getOtherSource(self, mediaid, currentdata, filepage):
        """
        The file is not some standard own work file. Try to extract other sources like Flickr
        :return: Tuple with (type of source, list of statements)
        """
        operators = { 'flickr' : 'Q103204', }
        authordpids = { 'flickr' : 'P3267',  }
        sourceregexes = { 'flickr' : '^\s*source\s*\=(\s*originally posted to\s*\'\'\'\[\[Flickr\|Flickr\]\]\'\'\'\s* as)?\s*\[(?P<url>https?\:\/\/(www\.)?flickr\.com\/photos\/[^\s]+\/[^\s]+\/?)\s+(?P<title>[^\]]+)\]\s*$'}
        authorregexes = { 'flickr' : '^\s*author\s*\=\s*\[(?P<url>https?:\/\/(www\.)?flickr\.com\/(people|photos)\/(?P<id>\d{5,11}@N\d{2}))\/?\s+(?P<authorname>[^\]]+)\].*$'}
        sourcefound = {}
        authorfound = {}
        for template, parameters in filepage.templatesWithParams():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.informationTemplates:
                for field in parameters:
                    if field.lower().startswith('source'):
                        for operator in sourceregexes:
                            match = re.match(sourceregexes.get(operator), field, flags=re.IGNORECASE)
                            if match:
                                sourcefound[operator] = match.groupdict()
                    elif field.lower().startswith('author'):
                        for operator in authorregexes:
                            match = re.match(authorregexes.get(operator), field, flags=re.IGNORECASE)
                            if match:
                                authorfound[operator] = match.groupdict()
        # Check if we got one match for both
        if sourcefound and authorfound and len(sourcefound)==1 and sourcefound.keys()==authorfound.keys():
            result = []
            operator = next(iter(sourcefound))
            operatorqid = operators.get(operator)
            operatornumid = operatorqid.replace('Q', '')
            if not currentdata.get('statements') or not currentdata.get('statements').get('P7482'):
                sourceurl = sourcefound.get(operator).get('url')
                sourceclaim = {'mainsnak': { 'snaktype': 'value',
                                             'property': 'P7482',
                                             'datavalue': { 'value': { 'numeric-id': 74228490,
                                                                       'id' : 'Q74228490',
                                                                       },
                                                            'type' : 'wikibase-entityid',
                                                            }
                                             },
                               'type': 'statement',
                               'rank': 'normal',
                               'qualifiers' : {'P137' : [ {'snaktype': 'value',
                                                           'property': 'P137',
                                                           'datavalue': { 'value': { 'numeric-id': operatornumid,
                                                                                     'id' : operatorqid,
                                                                                     },
                                                                          'type' : 'wikibase-entityid',
                                                                          },
                                                       } ],
                                               'P973' : [ {'snaktype': 'value',
                                                           'property': 'P973',
                                                           'datavalue': { 'value': sourceurl,
                                                                          'type' : 'string',
                                                                          },
                                                           } ],
                                               },
                               }
                result.append(sourceclaim)
            if not currentdata.get('statements') or not currentdata.get('statements').get('P170'):
                authordpid = authordpids.get(operator)
                authorid = authorfound.get(operator).get('id')
                authorname = authorfound.get(operator).get('authorname').strip()
                authorurl = authorfound.get(operator).get('url')
                authorclaim = {'mainsnak': { 'snaktype':'somevalue',
                                             'property': 'P170',
                                             },
                               'type': 'statement',
                               'rank': 'normal',
                               'qualifiers' : {'P2093' : [ {'snaktype': 'value',
                                                            'property': 'P2093',
                                                            'datavalue': { 'value': authorname,
                                                                           'type' : 'string',
                                                                           },
                                                            } ],
                                               'P2699' : [ {'snaktype': 'value',
                                                            'property': 'P2699',
                                                            'datavalue': { 'value': authorurl,
                                                                           'type' : 'string',
                                                                           },
                                                            } ],
                                               },
                               }
                if authordpid and authorid:
                    authorclaim['qualifiers'][authordpid] = [ {'snaktype': 'value',
                                                               'property': authordpid,
                                                               'datavalue': { 'value': authorid,
                                                                              'type' : 'string',
                                                                              },
                                                               } ]
                result.append(authorclaim)
            if result:
                return (operator, result)
        return False

    def getSelfLicenses(self, filepage):
        """
        Extract one or more licenses from the Self template
        :param filepage: The page of the file to work on.
        :return: List of Q ids of licenses
        """
        result = []

        if self.filelicenses:
            for license in self.filelicenses:
                if license.lower() in self.validLicenses:
                    licenseqid = self.validLicenses.get(license.lower())
                    if isinstance(licenseqid, list):
                        result.extend(licenseqid)
                    else:
                        result.append(self.validLicenses.get(license.lower()))
                else:
                    return False

        for template, parameters in filepage.templatesWithParams():
            if template.title()==u'Template:Self':
                for license in parameters:
                    cleanlicense = license.lower().strip().replace(' =', '=')
                    if cleanlicense in self.validLicenses:
                        licenseqid = self.validLicenses.get(cleanlicense)
                        if isinstance(licenseqid, list):
                            result.extend(licenseqid)
                        else:
                            result.append(licenseqid)
                    elif license=='':
                        continue
                    elif cleanlicense.startswith('author='):
                        continue
                    elif cleanlicense.startswith('attribution='):
                        continue
                    elif cleanlicense.startswith('migration='):
                        continue
                    elif cleanlicense.startswith('user:'):
                        # Funky user templates
                        continue
                    else:
                        pywikibot.output('Unable to parse self field: "%s"' % (cleanlicense,))
                        return False
                break
        # When we reach this point it means we didn't find an invalid self template or no self at all
        for template in filepage.templates():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.validLicenses:
                licenseqid = self.validLicenses.get(lowertemplate)
                if isinstance(licenseqid, list):
                    result.extend(licenseqid)
                else:
                    result.append(licenseqid)
        return list(set(result))

    def addSourceOwn(self, mediaid, currentdata):
        """
        Dummy method for now
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P7482'):
            return False
        return self.addClaimJson(mediaid, 'P7482', 'Q66458942')

    def addAuthorQid(self, mediaid, currentdata, authorqid):
        """
        Add an author that has a qid
        :param mediaid:
        :param currentdata:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P170'):
            return False
        return self.addClaimJson(mediaid, 'P170', authorqid)

    def addAuthor(self, mediaid, currentdata, authorPage, authorName):
        """
        Add the author info to filepage
        :param authorPage:
        :param authorName:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P170'):
            return False

        toclaim = {'mainsnak': { 'snaktype':'somevalue',
                                 'property': 'P170',
                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   'qualifiers' : {#'P3831' : [ {'snaktype': 'value',
                                   #             'property': 'P3831',
                                   #             'datavalue': { 'value': { 'numeric-id': '33231',
                                   #                                       'id' : 'Q33231',
                                   #                                       },
                                   #                            'type' : 'wikibase-entityid',
                                   #                            },
                                   #             } ],
                                   'P2093' : [ {'snaktype': 'value',
                                                'property': 'P2093',
                                                'datavalue': { 'value': authorName,
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   'P4174' : [ {'snaktype': 'value',
                                                'property': 'P4174',
                                                'datavalue': { 'value': authorPage.username,
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   'P2699' : [ {'snaktype': 'value',
                                                'property': 'P2699',
                                                'datavalue': { 'value': u'https://commons.wikimedia.org/wiki/User:%s' % (authorPage.title(underscore=True, with_ns=False, as_url=True), ),
                                                               'type' : 'string',
                                                               },
                                                } ],
                                   },
                   }
        return [toclaim,]

    def addLicenses(self, mediaid, currentdata, licenses):
        """
        Add the author info to filepage
        :param authorPage:
        :param authorName:
        :return:
        """
        result = []

        currentlicenses = []
        if currentdata.get('statements') and currentdata.get('statements').get('P275'):
            for licensestatement in currentdata.get('statements').get('P275'):
                if licensestatement.get('mainsnak').get('datavalue'):
                    currentlicenses.append(licensestatement.get('mainsnak').get('datavalue').get('value').get('id'))

        # Add the different licenses
        for license in licenses:
            if license not in currentlicenses:
                result.extend(self.addClaimJson(mediaid, u'P275', license))

        if not currentdata.get('statements') or not currentdata.get('statements').get('P6216'):
            # Add the fact that the file is copyrighted only if a license has been found
            if currentlicenses or licenses:
                # Check if current or new licenses are a public domain dedication license like CC0
                if (set(currentlicenses) | set(licenses) ) & set(self.pubDedication):
                    result.extend(self.addClaimJson(mediaid, u'P6216', u'Q88088423'))
                elif 'Q99263261' in (set(currentlicenses) | set(licenses) ):
                    # Flickr no known copyright restrictions junk
                    result.extend(self.addClaimJson(mediaid, u'P6216', u'Q99263261'))
                else:
                    # Add copyrighted, won't be reached is a file is both cc-zero and some other license
                    result.extend(self.addClaimJson(mediaid, u'P6216', u'Q50423863'))
        return result

    def handleDate(self, mediaid, currentdata, filepage):
        """
        Handle the date on the filepage. If it matches an ISO date (YYYY-MM-DD) (with or without time), add a date claim
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P571'):
            return False

        dateRegex = u'^\s*[dD]ate\s*\=\s*(?P<date>\d\d\d\d-\d\d-\d\d)(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*$'
        date_dtz_regex = '^\s*[dD]ate\s*\=\s*\{\{DTZ\|(?P<date>\d\d\d\d-\d\d-\d\d)T\d\d:\d\d.*$'
        takenRegex = u'^\s*date\s*\=\s*\{\{taken on\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\|\s*(?P<date>\d\d\d\d-\d\d-\d\d)(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\}\}(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*$'
        exifRegex = u'^\s*date\s*\=\s*\{\{According to Exif(\s*data)?\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\|\s*(?P<date>\d\d\d\d-\d\d-\d\d)(\s*\d\d\:\d\d(\:\d\d(\.\d\d)?)?)?\s*(\|\s*location\s*\=\s*[^\|]*)?\s*\}\}\s*$'

        dateString = None

        for template, parameters in filepage.templatesWithParams():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.informationTemplates:
                for field in parameters:
                    if field.lower().startswith(u'date'):
                        datematch = re.match(dateRegex, field, flags=re.IGNORECASE)
                        date_dtz_match = re.match(date_dtz_regex, field, flags=re.IGNORECASE)
                        takenmatch = re.match(takenRegex, field, flags=re.IGNORECASE)
                        exifmatch = re.match(exifRegex, field, flags=re.IGNORECASE)
                        if datematch:
                            dateString = datematch.group('date').strip()
                        elif date_dtz_match:
                            dateString = date_dtz_match.group('date').strip()
                        elif takenmatch:
                            dateString = takenmatch.group('date').strip()
                        elif exifmatch:
                            dateString = exifmatch.group('date').strip()
                        break
        if not dateString:
            return False

        request = self.site.simple_request(action='wbparsevalue', datatype='time', values=dateString)
        try:
            data = request.submit()
        except AssertionError:
            # This will break at some point in the future
            return False
        except pywikibot.exceptions.APIError:
            # The API did not like it at all
            return False
        postvalue = data.get(u'results')[0].get('value')

        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': 'P571',
                                 'datavalue': { 'value': postvalue,
                                                'type' : 'time',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return [toclaim,]

    def handlePointOfViewCoordinates(self, mediaid, currentdata, filepage):
        """
        Handle the point of view coordinates on the file page
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P1259'):
            return False

        cameraregex = '\{\{[lL]ocation(\s*dec)?\|(1\=)?(?P<lat>-?\d+\.?\d*)\|(2\=)?(?P<lon>-?\d+\.?\d*)(\|)?(_?source:[^_]+)?(_?heading\:(?P<heading>\d+(\.\d+)?))?(\|prec\=\d+)?\}\}'
        exifcameregex = '\{\{[lL]ocation\|(\d+)\|(\d+\.?\d*)\|(\d+\.?\d*)\|(N|S)\|(\d+)\|(\d+\.?\d*)\|(\d+\.?\d*)\|(E|W)\|alt\:(\d+\.?\d*|\?)_source:exif_heading:(\d+\.?\d*|\?)}}'
        cameramatch = re.search(cameraregex, filepage.text)
        exifcameramatch = re.search(exifcameregex, filepage.text)
        heading = None
        # altitude is in the spec, but doesn't seem to be in use

        if not cameramatch and not exifcameramatch:
            return False
        elif cameramatch:
            coordinateText = '%s %s' % (cameramatch.group('lat'), cameramatch.group('lon'), )
            if cameramatch.group('heading') and not cameramatch.group('heading') == '?':
                heading = cameramatch.group('heading')
        elif exifcameramatch:
            lat_dec = round((float(exifcameramatch.group(1)) * 3600.0 + float(exifcameramatch.group(2)) * 60.0 + float(exifcameramatch.group(3)) ) / 3600.0 , 6)
            lon_dec = round((float(exifcameramatch.group(5)) * 3600.0 + float(exifcameramatch.group(6)) * 60.0 + float(exifcameramatch.group(7)) ) / 3600.0 , 6)
            if exifcameramatch.group(4)=='S':
                lat_dec = -lat_dec
            if exifcameramatch.group(8)=='W':
                lon_dec = -lon_dec
            coordinateText = '%s %s' % (lat_dec, lon_dec, )
            if exifcameramatch.group(10) and not exifcameramatch.group(10) == '?':
                heading = exifcameramatch.group(10)

        if coordinateText:
            request = self.site.simple_request(action='wbparsevalue', datatype='globe-coordinate', values=coordinateText)
            try:
                data = request.submit()
            except AssertionError:
                # This will break at some point in the future
                return False
            except pywikibot.exceptions.APIError:
                # The API did not like it at all
                return False
            # Not sure if this works or that I get an exception.
            if data.get('error'):
                return False

            postvalue = data.get(u'results')[0].get('value')

            toclaim = {'mainsnak': { 'snaktype':'value',
                                     'property': 'P1259',
                                     'datavalue': { 'value': postvalue,
                                                    'type' : 'globecoordinate',
                                                    }

                                     },
                       'type': 'statement',
                       'rank': 'normal',
                       }
            if heading:
                try:
                    toclaim['qualifiers'] = {'P7787' : [ {'snaktype': 'value',
                                                          'property': 'P7787',
                                                          'datavalue': { 'value': { 'amount': '+%s' % (float(heading),),
                                                                                    #'unit' : '1',
                                                                                    'unit' : 'http://www.wikidata.org/entity/Q28390',
                                                                                    },
                                                                         'type' : 'quantity',
                                                                         },
                                                          },
                                                         ],
                                             }
                except ValueError:
                    # Weird heading
                    pass
            return [toclaim,]

    def handleObjectCoordinates(self, mediaid, currentdata, filepage):
        """
        Handle the object coordinates on the file page
        :param filepage:
        :return: #
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P9149'):
            return False
        elif currentdata.get('statements') and currentdata.get('statements').get('P625'):
            return self.replaceObjectCoordinates(mediaid, currentdata, filepage)

        objectregex = u'\{\{[oO]bject location(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(\|)?(_?source:[^_]+)?(_?heading\:(?P<heading>\d+(\.\d+)?))?(\|prec\=\d+)?\}\}'
        # I'm afraid this is not going to work if it's not decimal.
        #objectregex = u'\{\{[oO]bject location(\s*dec)?\|(?P<lat>-?\d+\.?\d*)\|(?P<lon>-?\d+\.?\d*)(?P<moreparameters>\|[^\}]+)?\}\}'
        objectmatch = re.search(objectregex, filepage.text)

        if not objectmatch:
            return False

        if objectmatch:
            coordinateText = '%s %s' % (objectmatch.group('lat'), objectmatch.group('lon'), )

            heading = None
            if 'moreparameters' in objectmatch.groupdict():
                headingregex = 'heading\:(?P<heading>\d+(\.\d+)?)'
                headingmatch = re.search(headingregex, objectmatch.group('moreparameters'))
                if headingmatch:
                    heading = headingmatch.group('heading')

            request = self.site.simple_request(action='wbparsevalue', datatype='globe-coordinate', values=coordinateText)
            try:
                data = request.submit()
            except AssertionError:
                # This will break at some point in the future
                return False
            except pywikibot.exceptions.APIError:
                # The API did not like it at all
                return False
            # Not sure if this works or that I get an exception.
            if data.get('error'):
                return False

            postvalue = data.get(u'results')[0].get('value')

            toclaim = {'mainsnak': { 'snaktype':'value',
                                     'property': 'P9149',
                                     'datavalue': { 'value': postvalue,
                                                    'type' : 'globecoordinate',
                                                    }

                                     },
                       'type': 'statement',
                       'rank': 'normal',
                       }
            if heading:
                try:
                    toclaim['qualifiers'] = {'P7787' : [ {'snaktype': 'value',
                                                          'property': 'P7787',
                                                          'datavalue': { 'value': { 'amount': '+%s' % (float(heading),),
                                                                                    #'unit' : '1',
                                                                                    'unit' : 'http://www.wikidata.org/entity/Q28390',
                                                                                    },
                                                                         'type' : 'quantity',
                                                                         },
                                                          },
                                                         ],
                                             }
                except ValueError:
                    # Weird heading
                    pass
            return [toclaim,]

    def replaceObjectCoordinates(self, mediaid, currentdata, filepage):
        """
        We started off this party with coordinate location (P625), but switched to coordinates of depicted place (P9149)
        Replace it
        :param mediaid:
        :param currentdata:
        :param filepage:
        :return:
        """
        if len(currentdata.get('statements').get('P625'))!=1:
            return False

        toclaim = currentdata.get('statements').get('P625')[0]
        idtoremove = toclaim.pop('id')
        toclaim['mainsnak']['property'] = 'P9149'
        oldhash = toclaim['mainsnak'].pop('hash')
        return [{'id' : idtoremove, 'remove':''}, toclaim ]

    def handleCameraMakeModel(self, mediaid, currentdata, filepage):
        """
        Get the exif metadata and see if we can add a camera model
        :param mediaid:
        :param currentdata:
        :param filepage:
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P4082'):
            return False

        try:
            if not filepage.latest_file_info.metadata:
                return False
            metadata = filepage.latest_file_info.metadata
        except (pywikibot.exceptions.PageRelatedError, AttributeError):
            pywikibot.output('No file on %s, skipping' % (filepage.title(),))
            return False

        cameramake = None
        cameramodel = None

        for namevalue in metadata:
            if namevalue.get('name') == 'Make' and namevalue.get('value'):
                cameramake = namevalue.get('value').strip()
            elif namevalue.get('name') == 'Model' and namevalue.get('value'):
                cameramodel = namevalue.get('value').strip()

        if not cameramake or not cameramodel:
            return False

        cameraqid = self.exifCameraMakeModel.get((cameramake, cameramodel))
        if not cameraqid:
            return False
        return self.addClaimJson(mediaid, 'P4082', cameraqid)

    def handleParticipant(self, mediaid, currentdata, filepage):
        """
        Add the participant in based on template usage
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P1344'):
            return False
        for template in filepage.templates():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.participantTemplates:
                qid = self.participantTemplates.get(lowertemplate)
                return self.addClaimJson(mediaid, 'P1344', qid)
        return False

    def handleSponsor(self, mediaid, currentdata, filepage):
        """
        Add the sponsor based on template usage
        :return:
        """
        if currentdata.get('statements') and currentdata.get('statements').get('P859'):
            return False
        for template in filepage.templates():
            lowertemplate = template.title(underscore=False, with_ns=False).lower()
            if lowertemplate in self.sponsorTemplates:
                qid = self.sponsorTemplates.get(lowertemplate)
                return self.addClaimJson(mediaid, 'P859', qid)
        return False

    def addClaimJson(self, mediaid, pid, qid):
        """
        Add a claim to a mediaid

        :param mediaid: The mediaid to add it to
        :param pid: The property P id (including the P)
        :param qid: The item Q id (including the Q)
        :param summary: The summary to add in the edit
        :return: Nothing, edit in place
        """
        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': pid,
                                 'datavalue': { 'value': { 'numeric-id': qid.replace(u'Q', u''),
                                                           'id' : qid,
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return [toclaim,]


def main(*args):
    gen = None
    genFactory = pagegenerators.GeneratorFactory()
    loose = False
    alwaystouch = False
    fileownwork = None
    authorpage = None
    authorname = None
    authorqid = None
    filelicenses = []

    for arg in pywikibot.handle_args(args):
        if arg == '-loose':
            loose = True
        elif arg == '-alwaystouch':
            alwaystouch = True
        elif arg == '-fileownwork':
            fileownwork = True
        elif arg.startswith('-authorpage'):
            authorpage = arg[12:]
        elif arg.startswith('-authorname'):
            authorname = arg[12:]
        elif arg.startswith('-authorqid'):
            authorqid = arg[11:]
        elif arg.startswith('-filelicense'):
            filelicenses.append(arg[13:])
        elif genFactory.handle_arg(arg):
            continue
    gen = pagegenerators.PageClassGenerator(genFactory.getCombinedGenerator(gen, preload=True))

    ownWorkBot = OwnWorkBot(gen, loose, alwaystouch, fileownwork, authorpage, authorname, authorqid, filelicenses)
    ownWorkBot.run()

if __name__ == "__main__":
    main()
