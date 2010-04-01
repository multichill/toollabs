<?php 
header('Content-type: application/vnd.google-earth.kml+xml');

echo '<?xml version="1.0" encoding="UTF-8"?>';

require_once('../../database.inc');

mysql_connect('sql.toolserver.org',$toolserver_username,$toolserver_password);
@mysql_select_db('p_erfgoed_p') or print mysql_error();

$bbox = $_GET[BBOX];
$coordinaten = preg_split('/,/', $bbox);

#echo  $_GET['BBOX'];

$latitude_top= $coordinaten[3];
$latitude_bottom= $coordinaten[1];
$longitude_left= $coordinaten[0];
$longitude_right= $coordinaten[2];

$latitude_top=50;
$latitude_bottom=40;



$query = "SELECT objrijksnr FROM monumenten WHERE lat BETWEEN " . $coordinaten[1]  . " AND " . $coordinaten[3] . " AND lon  BETWEEN " . $coordinaten[0]  . " AND " . $coordinaten[2] . "  ORDER BY RAND() LIMIT 100";

$result = mysql_query($query);

if(!$result) Die("ERROR: No result returned.");
?>

<kml xmlns="http://earth.google.com/kml/2.2">
<Folder>
	<name>Val op stom ding<? echo $bbox;
	echo $coordinaten;
	echo $coordinaten[0];
	echo $coordinaten[1];
	echo $coordinaten[2];
	echo $coordinaten[3];
	
	?></name>
<?
while($row = mysql_fetch_assoc($result))
{
?>
	<NetworkLink>
		<visibility>1</visibility>
		<open>1</open>
		<Link>
			<href>http://toolserver.org/~multichill/monumenten_op_de_kaart/getMonument.php?objrijksnr=<? echo urlencode($row['objrijksnr'])?></href>
			<viewRefreshMode>onStop</viewRefreshMode>
			<viewRefreshTime>0.5</viewRefreshTime>
			<viewBoundScale>0.9</viewBoundScale>
			<viewFormat>BBOX=[bboxWest],[bboxSouth],[bboxEast],[bboxNorth]</viewFormat>
		</Link>
	</NetworkLink><?
}
?>
</Folder>
</kml>
