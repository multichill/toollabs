<?php 
#header('Content-type: application/vnd.google-earth.kml+xml');

function getIcon( $oorspr_functie) {
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
    if (array_key_exists($oorspr_functie, $icons)) {
	return getImage($icons[$oorspr_functie], $size);
    } else {
	return getImage('Gfi-set01-hostel.svg', $size);
    }
}

function getImage($filename, $size) {
    $md5hash=md5(filename);
    $url = "http://upload.wikimedia.org/wikipedia/commons/thumb/" . $md5hash[0] . "/" . $md5hash[0] . $md5hash[1] . "/" . urlencode($filename) . "/" . $size . "px-" . urlencode($filename);
    return $url; 
}
echo '<?xml version="1.0" encoding="UTF-8"?>';

$bbox = $_GET[BBOX];
$coordinaten = preg_split('/,/', $bbox);

require_once('../../database.inc');

mysql_connect('sql.toolserver.org',$toolserver_username,$toolserver_password);
@mysql_select_db('u_multichill') or print mysql_error();

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
     <href><? echo getIcon( $row['oorspr_functie'] )?></href>
     <? #<href>http://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Gfi-set01-hostel.svg/30px-Gfi-set01-hostel.svg.png</href> ?>
    </Icon>
   </IconStyle>
   </Style>
  <Placemark>
   <name><? echo $row['objrijksnr'] ?>, <? echo $row['objectnaam'] ?> (<? echo $row['woonplaats'] ?>)</name>
   <styleUrl>#randomColorIcon</styleUrl>
   <visibility>1</visibility>
   <description>
    <![CDATA[
     <img src="<? echo getImage(str_replace(' ', '_', $row['image']), 200) ?>" />
     <ul>
      <li>objrijksnr - <? echo $row['objrijksnr'] ?></li>
      <li>woonplaats - <? echo $row['woonplaats'] ?></li>
      <li>adres - <? echo $row['adres'] ?></li>
      <li>objectnaam - <? echo $row['objectnaam'] ?></li>
      <li>type_obj - <? echo $row['type_obj'] ?></li>
      <li>oorspr_functie - <? echo $row['oorspr_functie'] ?></li>
      <li>bouwjaar - <? echo $row['bouwjaar'] ?></li>
      <li>architect - <? echo $row['architect'] ?></li>
      <li>cbs_tekst - <? echo $row['cbs_tekst'] ?></li>
      <li>RD_x - <? echo $row['RD_x'] ?></li>
      <li>RD_y - <? echo $row['RD_y'] ?></li>
      <li>lat - <? echo $row['lat'] ?></li>
      <li>lon - <? echo $row['lon'] ?></li>
      <li>image - <? echo $row['image'] ?></li>
      <li>source - <? echo $row['source'] ?></li>
      <li>changed - <? echo $row['changed'] ?></li>
     </ul>
<? echo $bbox;
	       echo "A" . $coordinaten[0] . "\n";
	               echo "B" . $coordinaten[1];
		               echo "C" . $coordinaten[2];
			               echo $coordinaten[3];
?> 
    ]]>
   </description>
   <Point>
    <coordinates><? echo $row['lon'] ?>,<? echo $row['lat'] ?>, 0 </coordinates>
   </Point>
  </Placemark>
 </Document>
</kml>
