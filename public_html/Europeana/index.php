<?php
$title = "Europeana search tool";
$modified = date ("G:i, n F Y", getlastmod());

$config = array();
// FIXME: Put it somewhere less public like mysql key
$config['wskey'] = "QYLCOXOPNF";
$config['query'] = urlencode($_GET['query']);
$config['record'] = $_GET['record'];

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

function buildStartScreen($query) {
	/* Build a starting search form */
	$result = array();
	$result[] = "<H2>Europeana search tool query</H2>";
	$result[] = '<img alt="File:Europeana logo 3 eu black.png" src="http://upload.wikimedia.org/wikipedia/commons/b/be/Europeana_logo_3_eu_black.png" width="128" height="70" />';
	$result[] = '<p>With this tool you can find images in Europeana to be uploaded to Wikimedia Commons.</p>';
	$result[] = '<p><b>Be careful to check if the file is <a href="https://secure.wikimedia.org/wikipedia/commons/wiki/Commons:Licensing">free</a> before you upload it!</b></p>';
	$result[] = '<form method="get" accept-charset="UTF-8" name="europeana-search" id="europeana-search">';
	$result[] = '<input class="search-input" name="query" id="query" type="text" title="Search term(s)" value="' . urldecode($query) . '" maxlength="75"/>';
	$result[] = '<input id="submit_search" type="submit" class="button" value="Search" />';
	$result[] = '</form>';
	return implode("\n", $result);
}

function getGalleryPage($query) {
	$result = array();
	//$result[] = '<ul class="gallery">';
	$result[]= buildStartScreen($query);

	global $config;
	$url = "http://api.europeana.eu/api/opensearch.rss?searchTerms=" . $query . "&wskey=" . $config['wskey'];
	//echo $url;
	$xml = new XMLReader();

	$xml->open($url);

	while($xml->read() && $xml->name!=="channel");
	$xml->read();
	while($xml->read()){
		//echo "|" . $xml->name . "=" . $xml->readstring() . $xml->depth . "\n";
		if ($xml->depth==2) {
		    //echo "|" . $xml->name . "=" . $xml->readstring() . $xml->depth . "\n";
		    if ($xml->nodeType==1 && $xml->name=="description") {
			    $result[] = "<H2>" . $xml->readstring() . "</H2>";
		    } elseif ($xml->nodeType==1 && $xml->name=="opensearch:totalResults") {
			    $result[] = "<p>Total number of files found:" . $xml->readstring() . '</p><ul class="gallery">';
		    } elseif ($xml->nodeType==1 && $xml->name=="item") {
			    $result[] = getGalleryItem($xml);
		    }
		}
	}
	//if ($xml->nodeType==1 && $xml->depth==5)
	$result[] = "</ul>";
	return implode("\n", $result);
}

function getGalleryItem($xml) {
	$record = "";
	$image = "";
	$title = "";

	while($xml->read() && $xml->depth!==3);
	while($xml->read() && ($xml->depth==3 || $xml->depth==4)) {
		//echo "|" . $xml->name . "=" . $xml->readstring() . $xml->depth . "\n";
		if ($xml->depth==3) {
			if ($xml->nodeType==1 && $xml->name=="title") {
				$title = $xml->readstring();
			} elseif ($xml->nodeType==1 && $xml->name=="link") {
				$link = $xml->readstring();
				// Do somethign with explode
				$pieces = explode(".srw?wskey", $link);
				$record = str_replace("http://www.europeana.eu/portal/record/", "", $pieces[0]);
			} elseif ($xml->nodeType==1 && $xml->name=="enclosure") {
				$image = $xml->getAttribute("url");
			}
		}
	}

	$result = array();
	$result[] = "";

	$result[] = '<li class="gallerybox" style="width: 155px">';
	$result[] = '<div style="width: 155px">';
	$result[] = '<div class="thumb" style="width: 150px; height: 150px;">';
	$result[] = '<div style="margin:15px auto;"><a href=?record=' . $record . ' class="image"><img alt="" src="' . $image . '" height="120" /></a></div>';
	$result[] = '</div>';
	$result[] = '<div class="gallerytext">';
	$result[] = '<p>' . $title . '</p>';
	$result[] = '</div>';
	$result[] = '</div>';
	$result[] = '</li>';

	return implode("\n", $result);
}

function getSingleRecordPage($record) {
	$result = array();
	$metadata = getRecordMetadata($record);
	$result[] = "<H2>" . $metadata['dc:title'][0] . "</H2>";
	$result[] = '<a href=' . $metadata['europeana:isShownAt'][0] . ' class="image"><img alt="Download the original image" target="_blank" src="' . $metadata['europeana:object'][0] . '" height="120" /><p><small>(click thumbnail to download the original)</small></p></a>';
	$result[] = '<p>' . $metadata['dc:description'][0] . '</p>';
	$result[] = '<p><b>Be careful to check if the file is <a href="https://secure.wikimedia.org/wikipedia/commons/wiki/Commons:Licensing">free</a> before you upload it!</b></p>';
	$result[] = '<a href="' . makeUploadLink($metadata) .'" title="Upload this file to Wikimedia Commons" target="_blank">Upload this file to Wikimedia Commons</a>';
	//$result[] = getTemplateCode("Europeana bla", $metadata);
	return implode("\n", $result);
}

function makeUploadLink($metadata) {
	$result = array();
	$result[] = "https://secure.wikimedia.org/wikipedia/commons/w/index.php?title=Special:Upload&uploadformstyle=basic";
	//FIXME: Figure out the extension
	$wpDestFile = $metadata['dc:title'][0] . '.jpg';
	$wpUploadDescription = getTemplateCode ("Europeana upload", $metadata);
	$wpUploadDescription = urlencode($wpUploadDescription);
	$wpUploadDescription = str_replace('%5Cn', '%0A', $wpUploadDescription); 
	$result[] = '&wpDestFile=' . urlencode($wpDestFile);
	$result[] =  '&wpUploadDescription=' . $wpUploadDescription;
	return implode($result);
}

function getRecordMetadata($record) {
	/* $link should point to an Europeana XML record */
	$link = "http://www.europeana.eu/portal/record/" .$record . ".srw?wskey=QYLCOXOPNF";

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
	//$result[] = "{{subst:" . $templateName . "|subst=subst:";
	$result[] = "{{" . $templateName;

	foreach ( $metadata as $key=>$value ){
		if (strpos($key, "enrichment") !== 0) {
			$result[]= "|" . $key . "=" . implode(", ", $metadata[$key]) . "\n";
			for ($i = 0; $i <  sizeof($metadata[$key]); $i++) {
				$result[]= "|" . $key . "_" . $i . "=" . $metadata[$key][$i];
			}
		}
	}
	$result[] = "}}";
	return implode("\n", $result);
}

function main($config) {
	$result = array();
	//$result[]= getTopOfPage();
	//include("../inc/header.php");
	if (!empty($config['record'])) {
	        $result[] = getSingleRecordPage($config['record']);
	} elseif (!empty($config['query'])) {
	        $result[] = getGalleryPage($config['query']);
	} else {
	        $result[] = buildStartScreen("");
	}

	//$result[] = getBottomOfPage();
	// Only location in the whole program to output something
	echo implode("\n", $result);
	//include("../inc/footer.php");
}
include("../inc/header.php");
main($config);
include("../inc/footer.php");
/*
	echo buildStartScreen();
$link = "http://www.europeana.eu/portal/record/09428/DA8F6B70E65DD37E7A1D9D550B7D500009E9CC6A.srw?wskey=QYLCOXOPNF";
$metadata = getRecordMetadata($link);
echo getTemplateCode("Europeana bla", $metadata);
//var_dump($metadata)
//
*/
?>
