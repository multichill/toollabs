<?php
// FIXME: Put it somewhere less public like mysql key
$wskey = "QYLCOXOPNF";

$query = $_GET['query'];
$link = $_GET['link'];

function getTopOfPage() {
	$result = array();
	$result[] = "<HTML>";
	return implode("\n", $result);
}

function getBottomOfPage() {
	$result = array();
	$result[] = "</HTML>";
	return implode("\n", $result);
}

function buildStartScreen() {
	/* Build a starting search form */
	$result = array();
	$result[] = '<form method="get" accept-charset="UTF-8" name="europeana-search" id="europeana-search">';
	$result[] = '<input class="search-input" name="query" id="query" type="text" title="Search term(s)" value="" maxlength="75"/>';
	$result[] = '<input id="submit_search" type="submit" class="button" value="Search" />';
	$result[] = '</form>';
	return implode("\n", $result);
}

function getRecordMetadata($link, $wskey) {
	/* $link should point to an Europeana XML record */

	$xml = new XMLReader();
	// FIXME: Use record and key
	$xml->open($link);

	$metadata = array();

	while($xml->read() && $xml->name!=="dc:dc");
	$xml->read();

	while($xml->next()){ 
		if ($xml->nodeType==1 && $xml->depth==5) {
			#echo "|" . $xml->name . "=" . $xml->readstring() . "\n";
			// First simple
			if (!isset($metadata[$xml->name])) {
				$metadata[$xml->name] = array();
			}
			$metadata[$xml->name][] = $xml->readstring();

		}
		//echo $xml->value;
		//echo $xml->readString();
	}
	return $metadata;
}

function getTemplateCode ($templateName, $metadata) {
	$result = array();
	$result[] = "{{subst:" . $templateName . "|subst=subst:\n";

	foreach ( $metadata as $key=>$value ){
		$result[]= "|" . $key . "=" . implode(", ", $metadata[$key]) . "\n";
		for ($i = 0; $i <  sizeof($metadata[$key]); $i++) {
			$result[]= "|" . $key . "_" . $i . "=" . $metadata[$key][$i] . "\n";
		}
	}
	return implode($result);
}

function main() {
	$result = array();
	$result[]= getTopOfPage();
	if (isset($link)) {
	        $result[] = getSingleRecordPage($link);
	} elseif (isset($query)) {
	        $result[] = getGalleryPage($query);
	} else {
	        $result[] = buildStartScreen();
	}

	$result[] = getBottomOfPage();
	// Only location in the whole program to output something
	echo implode("\n", $result);
}
main();
/*
	echo buildStartScreen();
$link = "http://www.europeana.eu/portal/record/09428/DA8F6B70E65DD37E7A1D9D550B7D500009E9CC6A.srw?wskey=QYLCOXOPNF";
$metadata = getRecordMetadata($link);
echo getTemplateCode("Europeana bla", $metadata);
//var_dump($metadata)
//
*/
?>
