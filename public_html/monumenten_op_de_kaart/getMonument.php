<?php 
header('Content-type: application/vnd.google-earth.kml+xml');
#header('Content-type: application/vnd.google-earth.kml+xml');

function getIcon($type_obj, $oorspr_functie) {
    $size = 17;
    $icons = array(
        'Aanlegvoorziening' => 'Gfi-set01-hostel.svg',
        'Appartementengebouw' => 'Gfi-set01-hostel.svg',
        'Bedieningsgebouw' => 'Gfi-set01-hostel.svg',
        'Bedrijfs-,fabriekswoning' => 'Gfi-set01-hostel.svg',
        'Begraafplaats en -onderdl' => 'Japanese_Map_symbol_(Graveyard).svg',
        'Bestuursgebouw en onderdl' => 'Gfi-set01-hostel.svg',
        'Bijgebouwen' => 'Gfi-set01-hostel.svg',
        'Bijgebouwen kastelen enz.' => 'Gfi-set01-hostel.svg',
        'Bijzondere woonvorm' => 'Gfi-set01-hostel.svg',
        'Boerderij' => 'Hooiberg.svg',
        'Bomvrij militair object' => 'Crossed_cannons.svg',
        'Brug' => 'Gfi-set01-hostel.svg',
        'Crematorium' => 'Gfi-set01-hostel.svg',
        'Dienstwoning' => 'Gfi-set01-hostel.svg',
        'Dierenverblijf' => 'Symbool_dierenverblijf.svg',
        'Erfscheiding' => 'Hekje_1a.png',
        'Fort, vesting en -onderdl' => 'Gfi-set01-hostel.svg',
        'Gedenkteken' => 'Map_symbol_memorial.svg',
        'Gemaal' => 'Gfi-set01-hostel.svg',
        'Gerechtsgebouw' => 'Balanced_scales.svg',
        'Gezondheidszorg' => 'Aiga_firstaid_inv.svg',
        'Gracht' => 'Symbol_canal.svg',
        'Grensafbakening' => 'Gfi-set01-hostel.svg',
        'Handel en kantoor' => 'Gfi-set01-hostel.svg',
        'Horeca' => 'Aiga_restaurant_.svg',
        'Industrie' => 'Factory_icon.svg',
        'Industrie- en poldermolen' => 'Map_symbol_windmill.svg',
        'Kapel' => 'Set01-church.svg',
        'Kasteel, buitenplaats' => 'Legenda_zamek.svg',
        'Kazemat' => 'Gfi-set01-hostel.svg',
        'Kerk en kerkonderdeel' => 'Set01-church.svg',
        'Kerkelijke dienstwoning' => 'Gfi-set01-hostel.svg',
        'Klooster, kloosteronderdl' => 'Set01-church.svg',
        'Kust- en oevermarkering' => 'Map_symbol_lighthouse.svg',
        'Militair verblijfsgebouw' => 'Crossed_cannons.svg',
        'Militair wachtgebouw' => 'Crossed_cannons.svg',
        'Militaire opslagplaats' => 'Crossed_cannons.svg',
        'Nijverheid' => 'Gfi-set01-hostel.svg',
        'Nutsbedrijf' => 'Gfi-set01-hostel.svg',
        'Omwalling' => 'Stadtmauer.png',
        'Onderdeel woningen e.d.' => 'Gfi-set01-hostel.svg',
        'Onderwijs en wetenschap' => 'Education_-_Grad_Hat.svg',
        'Open verdedigingswerk' => 'Crossed_cannons.svg',
        'Opslag' => 'Gfi-set01-hostel.svg',
        'Overheidsgebouw' => 'Gfi-set01-hostel.svg',
        'Scheepshulpmiddel' => 'Anchor_pictogram.svg',
        'Sociale zorg, liefdadigh.' => 'Gfi-set01-hostel.svg',
        'Sport en recreatie' => 'Gfi-set01-hostel.svg',
        'Stoep' => 'Gfi-set01-hostel.svg',
        'Straatmeubilair' => 'Lantaarntje.png',
        'Transport' => 'LKW_aus_Zusatzzeichen_1048-12.svg',
        'Tuin, park en plantsoen' => 'Gfi-set01-hatch.png',
        'Vanwege onderdelen kerk' => 'Gfi-set01-hostel.svg',
        'Vergadering en vereniging' => 'Gfi-set01-hostel.svg',
        'Verkeersobject' => 'Verkeersbord.svg',
        'Versperring' => 'Gfi-set01-hostel.svg',
        'Voorwerk' => 'Gfi-set01-hostel.svg',
        'Waarnemingspost' => 'Gfi-set01-hostel.svg',
        'Waterkering en -doorlaat' => 'Map_symbol_dike.svg',
        'Waterweg, werf en haven' => 'Anchor_pictogram.svg',
        'Weg' => 'Gfi-set01-hostel.svg',
        'Welzijn, kunst en cultuur' => 'Gfi-set01-hostel.svg',
        'Werk-woonhuis' => 'Gfi-set01-hostel.svg',
        'Winkel' => 'Gfi-set01-hostel.svg',
        'Woonhuis' => 'Gfi-set01-hostel.svg'
    );
    if ($type_obj=='A') {
	return getImageFromCommons('Map_symbol_archaeology.svg', $size);
    } else {
	if (array_key_exists($oorspr_functie, $icons)) {
	    return getImageFromCommons($icons[$oorspr_functie], $size);
	} else {
	    return getImageFromCommons('Gfi-set01-hostel.svg', $size);
	}
    }
}

function getImageFromCommons($filename, $size) {
    $md5hash=md5(filename);
    $url = "http://upload.wikimedia.org/wikipedia/commons/thumb/" . $md5hash[0] . "/" . $md5hash[0] . $md5hash[1] . "/" . urlencode($filename) . "/" . $size . "px-" . urlencode($filename);
    return $url; 
}

function getName($row) {
    /* Build the title for the item */
    $result = "";
    if ($row['objectnaam']!="") {
	$result = processWikitext($row['objectnaam'], 0);
    } else {
	$result = $row['objrijksnr'];
    }    
    if ($row['woonplaats']!="") {
	$result = $result . ", " . $row['woonplaats'];
    }
    return $result;
}

function processWikitext($text, $links) {
    /* Process the wikitext.
     * If links is true, make html links
     * If links is false, remove wikitext to produce normal text without links
     */
    $result = $text;
    $differentLinkRegex="/\[\[([^\|]*)\|([^\]]*)\]\]/";
    $simpleLinkRegex="/\[\[([^\]]*)\\]\]/";
    $differentLinkReplace = "'<a href=http://nl.wikipedia.org/wiki/' . rawurlencode('$1') . '>$2</a>'";
    $simpleLinkReplace = "'<a href=http://nl.wikipedia.org/wiki/' . rawurlencode('$1') . '>$1</a>'";
    if ( $links ) {
	$result = preg_replace($differentLinkRegex . "e", $differentLinkReplace, $result);
	$result = preg_replace($simpleLinkRegex . "e", $simpleLinkReplace, $result);
	$result = $result;
    } else {
	$result = preg_replace($differentLinkRegex, "$2", $result);
	$result = preg_replace($simpleLinkRegex, "$1", $result);
    }
    return $result;
}

function getImage($row) {
    /* Return an image to be used or a request for an image */
    if ($row['image'] != '') {
	$result = '<a href="http://commons.wikimedia.org/wiki/File:' . rawurlencode($row['image']) . '">';
	$result = $result . '<img src="' .  getImageFromCommons(str_replace(' ', '_', $row['image']), 200) . '" align="right" />';
	$result = $result . '</a>';
    } else {
	$result = '<a href="' . makeUploadLink($row) .'" title="Upload een zelfgemaakte foto van dit monument naar Commons" target="_blank">';
	$result = $result . '<img src="' .  getImageFromCommons('Crystal_Clear_app_lphoto.png', 100) . '" align="right" />';
	$result = $result . '</a>';
    }
    return $result;
}
function makeUploadLink($row) {
    /* Make an upload link with as much information as possible */
    $result = 'http://commons.wikimedia.org/wiki/Commons:Upload';
    $result = 'http://commons.wikimedia.org/w/index.php?title=Special:Upload&uploadformstyle=basic';
    if ( $row['objectnaam']!='' ) {
	if ( $row['woonplaats']!='' ) {
	    $description = $row['objectnaam'] . ', ' . $row['woonplaats'] . ' (rijksmonument ' . $row['objrijksnr'] . ')';
	} else {
	    $description = $row['objectnaam'] . ' (rijksmonument ' . $row['objrijksnr'] . ')';
	}
    } else {
	if ( $row['woonplaats']!='' ) {
	    if ( $row['adres']!='' ) {
		$description = 'Rijksmonument ' . $row['objrijksnr'] . ' (' . $row['adres'] . ' ' . $row['woonplaats'] . ')';
	    } else {
		$description = 'Rijksmonument ' . $row['objrijksnr'] . ' (' . $row['woonplaats'] . ')';	
	    }
	} else {
	    $description = 'Rijksmonument ' . $row['objrijksnr'];
	}
    }
    $wpDestFile = $description . '.jpg';
    $wpUploadDescription = '{{Information \n';
    $wpUploadDescription = $wpUploadDescription . '|Description={{nl|1=' . $description . '}}\n';
    $wpUploadDescription = $wpUploadDescription . '|Source={{own}}\n';
    $wpUploadDescription = $wpUploadDescription . '|Date=~~~~~ (upload date)\n';
    $wpUploadDescription = $wpUploadDescription . '|Author=~~~\n';
    $wpUploadDescription = $wpUploadDescription . '|Permission=\n';
    $wpUploadDescription = $wpUploadDescription . '|other_versions=\n';
    $wpUploadDescription = $wpUploadDescription . '}}\n';
    $wpUploadDescription = $wpUploadDescription . '{{Object location dec|' . $row['lat'] . '|' . $row['lon'] . '}}\n';
    $wpUploadDescription = $wpUploadDescription . '<!-- Information produced by http://toolserver.org/~multichill/monumenten_op_de_kaart/ from ' . $row['source'] . '-->\n';  
    $wpUploadDescription = urlencode($wpUploadDescription);
    $wpUploadDescription = str_replace('%5Cn', '%0A', $wpUploadDescription); 
    $result = $result . '&wpDestFile=' . urlencode($wpDestFile);
    $result = $result . '&wpUploadDescription=' . $wpUploadDescription;
    //$wpDestFile = '';
    //$wpUploadDescription = '';
    return $result;
}
echo '<?xml version="1.0" encoding="UTF-8"?>';

$bbox = $_GET[BBOX];
$coordinaten = preg_split('/,/', $bbox);

require_once('../../database.inc');

mysql_connect('sql.toolserver.org',$toolserver_username,$toolserver_password);
@mysql_select_db('p_erfgoed_p') or print mysql_error();

$objrijksnr = mysql_real_escape_string(urldecode($_GET['objrijksnr']));

#echo $article;

#$query = "SELECT page_title, latitude, longitude, zoom, type, region, image, text FROM kmltest WHERE page_title='" . $article . "' LIMIT 1";

$query = "SELECT objrijksnr, woonplaats, adres, objectnaam, type_obj, oorspr_functie, bouwjaar, architect, cbs_tekst, RD_x, RD_y, lat, lon, image, source, changed FROM monumenten WHERE objrijksnr='" . $objrijksnr . "' LIMIT 1";

$result = mysql_query($query);

if(!$result) Die("ERROR: No result returned.");

$row = mysql_fetch_assoc($result);
?>

<kml xmlns="http://earth.google.com/kml/2.2">
 <Document>
  <Style id="randomColorIcon">
   <IconStyle>
    <color>ff00eedd</color>
    <colorMode>random</colorMode>
    <scale>1.2</scale>
    <Icon>
     <href><? echo getIcon($row['type_obj'], $row['oorspr_functie'] )?></href>
     <? #<href>http://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Gfi-set01-hostel.svg/30px-Gfi-set01-hostel.svg.png</href> ?>
    </Icon>
   </IconStyle>
   </Style>
  <Placemark>
   <name><? echo getName($row); ?></name>
   <styleUrl>#randomColorIcon</styleUrl>
   <visibility>1</visibility>
   <description>
    <![CDATA[
     <? echo getImage($row); ?>
     <ul>
      <? if ($row['objectnaam'] != '') { ?>
      <li>Naam - <? echo processWikitext($row['objectnaam'], 1); ?></li>
      <? } ?>
      <li>Rijksmonument  - <? echo $row['objrijksnr'] ?></li>
      <? if ($row['adres'] != '') { ?>
      <li>Adres - <? echo $row['adres'] ?></li>
      <? } ?>
      <li>Plaats - <? echo $row['woonplaats'] ?></li>
      <li>Type object - <? if ($row['type_obj']=='A') {
      ?>Archeologisch monument<?
      } else {
      ?>Gebouw<?
      }?>
      <li>Oorspr functie - <? echo $row['oorspr_functie'] ?></li>
      <? if ($row['bouwjaar'] != '') { ?>
      <li>Bouwjaar - <? echo $row['bouwjaar'] ?></li>
      <? } if ($row['architect'] != '') { ?>
      <li>Architect - <? echo $row['architect'] ?></li>
      <? } if ($row['cbs_tekst'] != '') { ?>
      <li>CBS tekst - <? echo $row['cbs_tekst'] ?></li>
      <? } ?>
      <li>Rijksdriehoekscoordinaten - <? echo $row['RD_x'] ?>, <? echo $row['RD_y'] ?></li>
      <li>Lengtegraad - <? echo $row['lat'] ?></li>
      <li>Breedtegraad - <? echo $row['lon'] ?></li>
      <li>Bron van deze informatie - <? echo $row['source'] ?></li>
      <li>Laatste wijziging - <? echo $row['changed'] ?></li>
     </ul>
    ]]>
   </description>
   <Point>
    <coordinates><? echo $row['lon'] ?>,<? echo $row['lat'] ?>, 0 </coordinates>
   </Point>
  </Placemark>
 </Document>
</kml>
