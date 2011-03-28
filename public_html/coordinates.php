<?php
function printSelect($selectList, $selected) {
    foreach ($selectList as $option => $optionText) {
	echo "<option ";
	if($option==$selected){
	     echo "SELECTED ";
	}
	echo "value='" . $option . "'>" . $optionText  . "</option>\n";
    }
}

$typeArray = array (
    "empty"	    => "(empty)",
    "country"	    => "country", 
    "satellite"	    => "satellite",
    "adm1st"	    => "adm1st",
    "adm2nd"	    => "adm2nd",
    "city"	    => "city",
    "airport"	    => "airport",
    "mountain"	    => "mountain",
    "isle"	    => "isle",
    "waterbody"	    => "waterbody",
    "forest"	    => "forest",
    "river"	    => "river",
    "glacier"	    => "glacier",
    "edu"	    => "edu",
    "pass"	    => "pass",
    "railwaystation"=> "railwaystation",
    "landmark"	    => "landmark"
);

$templateArray = array (
    "coordinaten"     => "Coördinaten (NL)",
    "location"        => "Location (Commons)",
    "object_location" => "Object location (Commons)",
    "coord"           => "Coord (EN)",
);

$wikiArray = array (
    "commons.wikimedia.org" => "Commons",
    "nl.wikipedia.org"	    => "nl wikipedia"
);

// Get the config settings:
$config_type = $_GET['type'];
$config_region = $_GET['region'];
$config_template = $_GET['template'];
$config_wiki = $_GET['wiki'];
$config_page = htmlentities($_GET['page']);

?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
    <title>Coordinates tool</title>
    <style type="text/css">
      @import url("http://www.google.com/uds/css/gsearch.css");
      @import url("http://www.google.com/uds/solutions/localsearch/gmlocalsearch.css");
    </style>
    <script src="http://maps.google.com/maps?file=api&amp;v=2&amp;key=ABQIAAAAXXocP3iBobL_H8atwhwCxRTewJmMm8R8BffD5cP7aHkxnZlH6hTiDgkZ9T9T6qiGNz4yFDjqmA8eCg"
      type="text/javascript"></script>
    <script src="http://www.google.com/uds/api?file=uds.js&amp;v=1.0" type="text/javascript"></script>
    <script src="http://www.google.com/uds/solutions/localsearch/gmlocalsearch.js" type="text/javascript"></script>
    <script type="text/javascript">

    //<![CDATA[

    function load() {
	if (GBrowserIsCompatible()) {
	    map = new GMap2(document.getElementById("map"), { size: new GSize(800,600) });
	    map.setCenter(new GLatLng(52, 5), 7);
	    map.enableScrollWheelZoom();
	    map.addControl(new GLargeMapControl());
	    map.addControl(new GMapTypeControl());
	    map.addControl(new google.maps.LocalSearch(), new GControlPosition(G_ANCHOR_BOTTOM_RIGHT, new GSize(10,20)));

	    GEvent.addListener(map, 'zoomend', function(oldLevel, newLevel) {
		zoom = newLevel;
		displaycoordinates(map,cur_location,zoom);
	    });

	    GEvent.addListener(map, 'click', function(overlay, latlng, overlaylatlng) {
		if (overlay) {
		    // bla
		} else if (latlng) {
		    isclicked = true;
		    cur_location = latlng;
		    zoom = map.getZoom();
		    if(document.configCoords.region.value=="auto") {
			getregion(latlng.lat(),latlng.lng(),foundregion);
		    } else {
			displaycoordinates(map,cur_location,zoom);
		    }
		}
	    });
	}
    }

    try {
	xhr = XMLHttpRequest ? new XMLHttpRequest() : new ActiveXObject("Microsoft.XMLHTTP");
    }
    catch(e) {
	alert('Unable to create XMLHttpRequest');
    }
    function getregion(lat, long, callback) {
	var path = "http://toolserver.org/~para/region.php?tsv&lat="+lat+"&long="+long;
	xhr.open('GET', path, true); //IE6: needs to be first
	xhr.onreadystatechange = function() {
	    if(xhr.readyState == 4) {
		callback(xhr.responseText.split('\n')[0].split('\t'));
	    }
	}
    xhr.send(null);
    }
    function foundregion(region) {
	if ( region == null || region == "" ) {
	    autoregion = "";
	} else {
	    autoregion = region[2];
	}
	//alert("region found: " + autoregion);
	displaycoordinates(map,cur_location,zoom);
    }
    function menuchanged(){
	displaycoordinates(map,cur_location,zoom);
    }
    function displaycoordinates(map,latlng,zoom){
	if (latlng && isclicked == true) {
	    templateText = getTemplateText(document.configCoords.template.value, latlng.lat(), latlng.lng(), zoom);
	    document.templateCode.output.value = templateText;
	    map.clearOverlays();
	    marker = new GMarker(latlng);
	    markerset = marker;
	    map.addOverlay(marker);

	    // If wiki and page are set open a popup with a direct edit link
	    wiki = document.configCoords.wiki.value
	    page = document.configCoords.page.value

	    if((wiki!="") && (page!="")){
		link = "http://" + wiki + "/w/index.php?title=" + encodeURIComponent(page) + "&action=edit&withJS=MediaWiki:AddCoordinates.js&coordinates=" + encodeURIComponent(templateText);
		popupText = '<A href="' + link + '" target="_blank">Add template</a>';
	    } else {
		popupText ="Set wiki and page to get a direct edit link here! Or just copy the template code from below";
	    }
	    marker.openInfoWindowHtml(popupText, {maxWidth:600});
	}
    }
    function getTemplateText(template, lat, lng, zoom){
	//SCALE = POWER(2, 12 - ZOOM) * 100000
	var scale = Math.round(Math.pow(2, 12 - zoom) * 100000)
	switch(template){
	    case "coordinaten":
		return printCoordinaten(lat, lng, scale);
		break;
	    case "location":
		return printLocation(lat, lng, scale, "c");
		break;
	    case "object_location":
		return printLocation(lat, lng, scale, "o");
		break;
	    case "coord":
		return printLocation(lat, lng, scale, "e");
		break;
	    default:
		return "Unknown template"
		break;
	}
    }

    function getDegrees(dec) {
	return parseInt(Math.abs(dec));
    }

    function getMinutes(dec) {
	return parseInt((Math.abs(dec) - getDegrees(dec)) * 60);
    }

    function getSeconds(dec) {
	return Math.round((((Math.abs(dec) - getDegrees(dec)) * 60 - getMinutes(dec)) * 60) * 100) /100 ;
    }
    function getNS(dec) {
	if(dec>0) {
	    return "N";
	} else {
	    return "S";
	}
    }
    function getEW(dec) {
	if(dec>0) {
	    return "E";
	} else {
	    return "W";
	}
    }

    function printLocation(lat, lng, scale, type){
	lat_deg = getDegrees(lat);
	lat_min = getMinutes(lat);
	lat_sec = getSeconds(lat); 
	lng_deg = getDegrees(lng);
	lng_min = getMinutes(lng);
	lng_sec = getSeconds(lng); 
	if(type == "c") {
	    result = "{{Location|" ;
	} else if (type == "o") {
	    result = "{{Object location|" ;
	} else if (type == "e") {
	    result = "{{Coord|" ;
	}
	result = result + lat_deg + "|" + lat_min + "|" + lat_sec + "|" + getNS(lat) + "|";
	result = result + lng_deg + "|" + lng_min + "|" + lng_sec + "|" + getEW(lng) + "|";
	result = result + "scale:" + scale;
	if(document.configCoords.type.value!="empty") {
	    result = result + "_type:" + document.configCoords.type.value;
	}
	if(document.configCoords.region.value=="auto") {
	    if (autoregion != "") {
		result = result + "_region:" + autoregion;
	    }
	} else {
	    result = result + "_region:" + document.configCoords.region.value;
	}
	if (type == "e") {
	    result = result + "|display=title";
	}
	result = result + "}}";
	return result;
    }

    function printCoordinaten(lat,lng, scale){	
	result = "{{Coördinaten|"
	result = result + getDegrees(lat) + "_" + getMinutes(lat) + "_" + getSeconds(lat) + "_" + getNS(lat) + "_";
	result = result + getDegrees(lng) + "_" + getMinutes(lng) + "_" + getSeconds(lng) + "_" + getEW(lng) + "_";
	result = result + "scale:" + scale;
	if(document.configCoords.type.value!="empty") {
	    result = result + "_type:" + document.configCoords.type.value;
	}
	if(document.configCoords.region.value=="auto") {
	    if (autoregion != "") {
		result = result + "_region:" + autoregion;
	    }
	} else {
	    result = result + "_region:" + document.configCoords.region.value;
	}
	result = result + "|";
	result = result + getDegrees(lat) + "° " + getMinutes(lat) + "' " + Math.round(getSeconds(lat)) + "\" " + getNS(lat) + " ";
	result = result + getDegrees(lng) + "° " + getMinutes(lng) + "' " + Math.round(getSeconds(lng)) + "\" " + getEW(lng) + "}}";
	return result;
    }

    GSearch.setOnLoadCallback(load);
    // global variables to keep state
    mymap=null;
    isclicked = new Boolean(false);
    cur_location = new GLatLng();
    autoregion = "";
    zoom = 0;
    //]]>
    </script>


    <link href="Common.css" rel="stylesheet" type="text/css">
  </head>
  <body onload="load()" onunload="GUnload()">
    <div id="globalWrapper">
      <div id="column-content">
	<div id="content">
	  <div id="bodyContent">
	    <H2>Coordinates tool</H2>
	    <P>Set your options on the left and click the map to see the result.</P>
	    <H3>Map</H3>
	    <div id="map" style="width: 800px; height: 600px"></div>
	    <H3>Output</H3>
	    <div id"template_code" style="width: 800px; height: 50px"><form name="templateCode"><input type=text name="output" style="width: 800px"></form></div>
<?php include("inc/sidebar.php"); ?>
<div class='portlet' id='p-configuration'>
    <h5>Configuration</h5>
    <div class='pBody'>
	<table>
	<form name="configCoords">
	    <tr><td>Type:</td></tr>
	    <tr><td>
		<select id="type" name="type" style="width:120px" onchange="menuchanged()">
		    <?php printSelect($typeArray, $config_type); ?>
		</select>
	    </td></tr>
	    <!-- This list appears to cause some problems, removed for the moment -->
	    <tr><td>Region:</td></tr>
	    <tr><td>
		<select id="region" name="region" style="width:120px" onchange="menuchanged()">
		    <option SELECTED value="auto">(auto)</option>
		    <option value="AD">Andorra</option>
		    <option value="AF">Afghanistan</option>
		    <option value="AX">Åand Islands</option>
		    <option value="AL">Albania</option>
		    <option value="DZ">Algeria</option>
		    <option value="AS">American Samoa</option>
		    <option value="AO">Angola</option>
		    <option value="AI">Anguilla</option>
		    <option value="AQ">Antarctica</option>
		    <option value="AG">Antigua and Barbuda</option>
		    <option value="AR">Argentina</option>
		    <option value="AM">Armenia</option>
		    <option value="AW">Aruba</option>
		    <option value="AU">Australia</option>
		    <option value="AT">Austria</option>
		    <option value="AZ">Azerbaijan</option>
		    <option value="BH">Bahrain</option>
		    <option value="BD">Bangladesh</option>
		    <option value="BB">Barbados</option>
		    <option value="BY">Belarus</option>
		    <option value="BE">Belgium</option>
		    <option value="BZ">Belize</option>
		    <option value="BJ">Benin</option>
		    <option value="BM">Bermuda</option>
		    <option value="BT">Bhutan</option>
		    <option value="BO">Bolivia</option>
		    <option value="BA">Bosnia and Herzegovina</option>
		    <option value="BW">Botswana</option>
		    <option value="BV">Bouvet Island</option>
		    <option value="BR">Brazil</option>
		    <option value="IO">British Indian Ocean Territory</option>
		    <option value="VG">British Virgin Islands</option>
		    <option value="BN">Brunei</option>
		    <option value="BG">Bulgaria</option>
		    <option value="BF">Burkina Faso</option>
		    <option value="MM">Burma</option>
		    <option value="BI">Burundi</option>
		    <option value="KH">Cambodia</option>
		    <option value="CM">Cameroon</option>
		    <option value="CA">Canada</option>
		    <option value="CV">Cape Verde</option>
		    <option value="KY">Cayman Islands</option>
		    <option value="CF">Central African Republic</option>
		    <option value="TD">Chad</option>
		    <option value="CL">Chile</option>
		    <option value="CX">Christmas Island</option>
		    <option value="CC">Cocos (Keeling) Islands</option>
		    <option value="CO">Colombia</option>
		    <option value="KM">Comoros</option>
		    <option value="CK">Cook Islands</option>
		    <option value="CR">Costa Rica</option>
		    <option value="CI">Côd'Ivoire</option>
		    <option value="HR">Croatia</option>
		    <option value="CU">Cuba</option>
		    <option value="CY">Cyprus</option>
		    <option value="CZ">Czech Republic</option>
		    <option value="CD">Democratic Republic of the Congo</option>
		    <option value="DK">Denmark</option>
		    <option value="DJ">Djibouti</option>
		    <option value="DM">Dominica</option>
		    <option value="DO">Dominican Republic</option>
		    <option value="TL">East Timor</option>
		    <option value="EC">Ecuador</option>
		    <option value="EG">Egypt</option>
		    <option value="SV">El Salvador</option>
		    <option value="GQ">Equatorial Guinea</option>
		    <option value="ER">Eritrea</option>
		    <option value="EE">Estonia</option>
		    <option value="ET">Ethiopia</option>
		    <option value="FK">Falkland Islands</option>
		    <option value="FO">Faroe Islands</option>
		    <option value="FM">Federated States of Micronesia</option>
		    <option value="FJ">Fiji</option>
		    <option value="FI">Finland</option>
		    <option value="FR">France</option>
		    <option value="GF">French Guiana</option>
		    <option value="PF">French Polynesia</option>
		    <option value="TF">French Southern and Antarctic Lands</option>
		    <option value="GA">Gabon</option>
		    <option value="GE">Georgia (country)</option>
		    <option value="DE">Germany</option>
		    <option value="GH">Ghana</option>
		    <option value="GI">Gibraltar</option>
		    <option value="GR">Greece</option>
		    <option value="GL">Greenland</option>
		    <option value="GD">Grenada</option>
		    <option value="GP">Guadeloupe</option>
		    <option value="GU">Guam</option>
		    <option value="GT">Guatemala</option>
		    <option value="GG">Guernsey</option>
		    <option value="GN">Guinea</option>
		    <option value="GW">Guinea-Bissau</option>
		    <option value="GY">Guyana</option>
		    <option value="HT">Haiti</option>
		    <option value="HM">Heard Island and McDonald Islands</option>
		    <option value="HN">Honduras</option>
		    <option value="HK">Hong Kong</option>
		    <option value="HU">Hungary</option>
		    <option value="IS">Iceland</option>
		    <option value="IN">India</option>
		    <option value="ID">Indonesia</option>
		    <option value="IR">Iran</option>
		    <option value="IQ">Iraq</option>
		    <option value="IM">Isle of Man</option>
		    <option value="IL">Israel</option>
		    <option value="IT">Italy</option>
		    <option value="JM">Jamaica</option>
		    <option value="JP">Japan</option>
		    <option value="JE">Jersey</option>
		    <option value="JO">Jordan</option>
		    <option value="KZ">Kazakhstan</option>
		    <option value="KE">Kenya</option>
		    <option value="KI">Kiribati</option>
		    <option value="KW">Kuwait</option>
		    <option value="KG">Kyrgyzstan</option>
		    <option value="LA">Laos</option>
		    <option value="LV">Latvia</option>
		    <option value="LB">Lebanon</option>
		    <option value="LS">Lesotho</option>
		    <option value="LR">Liberia</option>
		    <option value="LY">Libya</option>
		    <option value="LI">Liechtenstein</option>
		    <option value="LT">Lithuania</option>
		    <option value="LU">Luxembourg</option>
		    <option value="MO">Macau</option>
		    <option value="MG">Madagascar</option>
		    <option value="MW">Malawi</option>
		    <option value="MY">Malaysia</option>
		    <option value="MV">Maldives</option>
		    <option value="ML">Mali</option>
		    <option value="MT">Malta</option>
		    <option value="MH">Marshall Islands</option>
		    <option value="MQ">Martinique</option>
		    <option value="MR">Mauritania</option>
		    <option value="MU">Mauritius</option>
		    <option value="YT">Mayotte</option>
		    <option value="MX">Mexico</option>
		    <option value="MD">Moldova</option>
		    <option value="MC">Monaco</option>
		    <option value="MN">Mongolia</option>
		    <option value="ME">Montenegro</option>
		    <option value="MS">Montserrat</option>
		    <option value="MA">Morocco</option>
		    <option value="MZ">Mozambique</option>
		    <option value="NA">Namibia</option>
		    <option value="NR">Nauru</option>
		    <option value="NP">Nepal</option>
		    <option value="NL">Netherlands</option>
		    <option value="AN">Netherlands Antilles</option>
		    <option value="NC">New Caledonia</option>
		    <option value="NZ">New Zealand</option>
		    <option value="NI">Nicaragua</option>
		    <option value="NE">Niger</option>
		    <option value="NG">Nigeria</option>
		    <option value="NU">Niue</option>
		    <option value="NF">Norfolk Island</option>
		    <option value="KP">North Korea</option>
		    <option value="MP">Northern Mariana Islands</option>
		    <option value="NO">Norway</option>
		    <option value="OM">Oman</option>
		    <option value="PK">Pakistan</option>
		    <option value="PW">Palau</option>
		    <option value="PS">Palestinian territories</option>
		    <option value="PA">Panama</option>
		    <option value="PG">Papua New Guinea</option>
		    <option value="PY">Paraguay</option>
		    <option value="CN">People's Republic of China</option>
		    <option value="PE">Peru</option>
		    <option value="PH">Philippines</option>
		    <option value="PN">Pitcairn Islands</option>
		    <option value="PL">Poland</option>
		    <option value="PT">Portugal</option>
		    <option value="PR">Puerto Rico</option>
		    <option value="QA">Qatar</option>
		    <option value="TW">Republic of China</option>
		    <option value="IE">Republic of Ireland</option>
		    <option value="MK">Republic of Macedonia</option>
		    <option value="CG">Republic of the Congo</option>
		    <option value="RE">Réion</option>
		    <option value="RO">Romania</option>
		    <option value="RU">Russia</option>
		    <option value="RW">Rwanda</option>
		    <option value="BL">Saint Barthémy</option>
		    <option value="SH">Saint Helena</option>
		    <option value="KN">Saint Kitts and Nevis</option>
		    <option value="LC">Saint Lucia</option>
		    <option value="MF">Saint Martin (France)</option>
		    <option value="PM">Saint Pierre and Miquelon</option>
		    <option value="VC">Saint Vincent and the Grenadines</option>
		    <option value="WS">Samoa</option>
		    <option value="SM">San Marino</option>
		    <option value="ST">SãToménd Príipe</option>
		    <option value="SA">Saudi Arabia</option>
		    <option value="SN">Senegal</option>
		    <option value="RS">Serbia</option>
		    <option value="SC">Seychelles</option>
		    <option value="SL">Sierra Leone</option>
		    <option value="SG">Singapore</option>
		    <option value="SK">Slovakia</option>
		    <option value="SI">Slovenia</option>
		    <option value="SB">Solomon Islands</option>
		    <option value="SO">Somalia</option>
		    <option value="ZA">South Africa</option>
		    <option value="GS">South Georgia and the South Sandwich Islands</option>
		    <option value="KR">South Korea</option>
		    <option value="ES">Spain</option>
		    <option value="LK">Sri Lanka</option>
		    <option value="SD">Sudan</option>
		    <option value="SR">Suriname</option>
		    <option value="SJ">Svalbard and Jan Mayen</option>
		    <option value="SZ">Swaziland</option>
		    <option value="SE">Sweden</option>
		    <option value="CH">Switzerland</option>
		    <option value="SY">Syria</option>
		    <option value="TJ">Tajikistan</option>
		    <option value="TZ">Tanzania</option>
		    <option value="TH">Thailand</option>
		    <option value="BS">The Bahamas</option>
		    <option value="GM">The Gambia</option>
		    <option value="TG">Togo</option>
		    <option value="TK">Tokelau</option>
		    <option value="TO">Tonga</option>
		    <option value="TT">Trinidad and Tobago</option>
		    <option value="TN">Tunisia</option>
		    <option value="TR">Turkey</option>
		    <option value="TM">Turkmenistan</option>
		    <option value="TC">Turks and Caicos Islands</option>
		    <option value="TV">Tuvalu</option>
		    <option value="UG">Uganda</option>
		    <option value="UA">Ukraine</option>
		    <option value="AE">United Arab Emirates</option>
		    <option value="GB">United Kingdom</option>
		    <option value="US">United States</option>
		    <option value="UM">United States Minor Outlying Islands</option>
		    <option value="VI">United States Virgin Islands</option>
		    <option value="UY">Uruguay</option>
		    <option value="UZ">Uzbekistan</option>
		    <option value="VU">Vanuatu</option>
		    <option value="VA">Vatican City</option>
		    <option value="VE">Venezuela</option>
		    <option value="VN">Vietnam</option>
		    <option value="WF">Wallis and Futuna</option>
		    <option value="EH">Western Sahara</option>
		    <option value="YE">Yemen</option>
		    <option value="ZM">Zambia</option>
		    <option value="ZW">Zimbabwe</option>
		</select>
	    </td></tr>
	    <tr><td>Template:</td></tr>
	    <tr><td>
		<select id="template" name="template" style="width:120px" onchange="menuchanged()">
		    <?php printSelect($templateArray, $config_template); ?>
		</select>
	    </td></tr>
	    <tr><td>Wiki:</td></tr>
	    <tr><td>
		<select id="wiki" name="wiki" style="width:120px" onchange="menuchanged()">
		    <?php printSelect($wikiArray, $config_wiki); ?>
		</select>
	    </td></tr>
	    <!-- <tr><td><input type=text name="wiki" value="<?php echo $config_wiki ?>" style="width:120px"></td></tr> -->
	    <tr><td>Page:</td></tr>
	    <tr><td><input type=text name="page" value="<?php echo $config_page ?>" style="width:120px"></td></tr>
	</form>
	</table>
    </div>
</div>
<?php include("inc/footerbare.php"); ?>
