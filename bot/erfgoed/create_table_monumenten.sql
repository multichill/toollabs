/* Create table statement for the monumenten database */
connect u_multichill sql.toolserver.org;
CREATE TABLE `monumenten` (
  `objrijksnr` int(11) NOT NULL DEFAULT '0',
  `woonplaats` varchar(255) NOT NULL DEFAULT '',
  `adres` varchar(255) NOT NULL DEFAULT '',
  `objectnaam` varchar(255) NOT NULL DEFAULT '',
  `type_obj` ENUM('G', 'A'),
  `oorspr_functie` varchar(128) NOT NULL DEFAULT '',
  `bouwjaar`  varchar(255) NOT NULL DEFAULT '',
  `architect` varchar(255) NOT NULL DEFAULT '',
  `cbs_tekst` varchar(255) NOT NULL DEFAULT '',
  `RD_x` double NOT NULL DEFAULT '0',
  `RD_y` double NOT NULL DEFAULT '0',
  `lat` double NOT NULL DEFAULT '0',
  `lon` double NOT NULL DEFAULT '0',
  `image` varchar(255) NOT NULL DEFAULT '',
  `source` varchar(255) NOT NULL DEFAULT '',
  `changed` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`objrijksnr`),
  KEY `latitude` (`lat`),
  KEY `longitude` (`lon`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
