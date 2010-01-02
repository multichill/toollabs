<?php 
#header('Content-type: application/vnd.google-earth.kml+xml');
echo '<?xml version="1.0" encoding="UTF-8"?>';

$bbox = $_GET[BBOX];
$coordinaten = preg_split('/,/', $bbox);

require_once('../../database.inc');

mysql_connect('sql.toolserver.org',$toolserver_username,$toolserver_password);
@mysql_select_db('u_multichill') or print mysql_error();

$objrijksnr = mysql_real_escape_string(urldecode($_GET['objrijksnr']));

#echo $article;

#$query = "SELECT page_title, latitude, longitude, zoom, type, region, image, text FROM kmltest WHERE page_title='" . $article . "' LIMIT 1";

$query = "SELECT objrijksnr, woonplaats, adres, objectnaam, type_obj, oorspr_functie, bouwjaar, architect, cbs_tekst, RD_x, RD_y, lat, lon, source, changed FROM monumenten WHERE objrijksnr='" . $objrijksnr . "' LIMIT 1";

$result = mysql_query($query);

if(!$result) Die("ERROR: No result returned.");

$row = mysql_fetch_assoc($result);
?>

<kml xmlns="http://earth.google.com/kml/2.2">
<Placemark>
	<name><? echo $row['objrijksnr'] ?>, <? echo $row['objectnaam'] ?> (<? echo $row['woonplaats'] ?>)</name>
	<visibility>1</visibility>
	<description><![CDATA[<ul>
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
<li>source - <? echo $row['source'] ?></li>
<li>changed - <? echo $row['changed'] ?></li>
</ul>
<? echo $bbox;
	       echo "A" . $coordinaten[0] . "\n";
	               echo "B" . $coordinaten[1];
		               echo "C" . $coordinaten[2];
			               echo $coordinaten[3];
	
	
	
	
	?> ]]></description>
	<Point>
	 <coordinates><? echo $row['lon'] ?>,<? echo $row['lat'] ?>, 0 </coordinates>
	</Point>
</Placemark>
</kml>
