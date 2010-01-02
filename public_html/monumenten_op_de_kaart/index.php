<?php 
header('Content-type: application/vnd.google-earth.kml+xml');

echo '<?xml version="1.0" encoding="UTF-8"?>';
?>

<kml xmlns="http://earth.google.com/kml/2.2">
<Folder>
	<name>Nederlandse rijksmonumenten op de kaart</name>
	<Snippet maxLines="2"></Snippet>
	<description><![CDATA[Link to <a href="http://toolserver.org/~multichill/">Multichill's homepage</a>]]></description>
	<NetworkLink id="MAIN">
		<name>Monumenten</name>
		<Link>
			<href>http://toolserver.org/~multichill/monumenten_op_de_kaart/getMonuments.php</href>
			<viewRefreshMode>onStop</viewRefreshMode>
			<viewRefreshTime>0.5</viewRefreshTime>
			<viewBoundScale>0.9</viewBoundScale>
			<viewFormat>BBOX=[bboxWest],[bboxSouth],[bboxEast],[bboxNorth]</viewFormat>
		</Link>
	</NetworkLink>
	
</Folder>
</kml>
