<?php 
$title = "Dupe finding tool";
$modified = date ("G:i, n F Y", getlastmod());

include("inc/header.php"); 
/*
$languages = array (
"als" => array("name" => "Alemannisch", "template" => "NowCommons"),
"ca" => array("name" => "Català", "template" => "AraCommons"),
"cs" => array("name" => "C(esky", "template" => "NowCommons"),
"da" => array("name" => "Dansk", "template" => "NowCommons"),
"de" => array("name" => "Deutsch", "template" => "NowCommons"),
"en" => array("name" => "English", "template" => "Subst:Ncd"),
"eo" => array("name" => "Esperanto", "template" => "Nun en komunejo"),
"es" => array("name" => "Español", "template" => "EnCommons"),
"fi" => array("name" => "Suomi", "template" => "NowCommons"),
"fr" => array("name" => "Français", "template" => "Image sur Commons"),
"hr" => array("name" => "Hrvatski", "template" => "NowCommons"),
"hu" => array("name" => "Magyar", "template" => "Azonnali-commons"),
"id" => array("name" => "Bahasa Indonesia", "template" => "NowCommons"),
"it" => array("name" => "Italiano", "template" => "NowCommons"),
"ja" => array("name" => "???", "template" => "NowCommons"),
"ko" => array("name" => "???", "template" => "NowCommons"),
"mk" => array("name" => "??????????", "template" => "NowCommons"),
"ms" => array("name" => "Bahasa Melayu", "template" => "NowCommons"),
"nl" => array("name" => "Nederlands", "template" => "NuCommons"),
"nn" => array("name" => "Norsk (nynorsk)", "template" => "NowCommons"),
"no" => array("name" => "Norsk (bokmål)", "template" => "NowCommons"),
"pl" => array("name" => "Polski", "template" => "NowCommons"),
"pt" => array("name" => "Português", "template" => "NowCommons"),
"ro" => array("name" => "Româna(", "template" => "AcumCommons"),
"ru" => array("name" => "???????", "template" => "NowCommons"),
"simple" => array("name" => "Simple English", "template" => "NowCommons"),
"sk" => array("name" => "Slovenc(ina", "template" => "NowCommons"),
"sl" => array("name" => "Sloven~Zc(ina", "template" => "NowCommons"),
"sr" => array("name" => "Srpski", "template" => "NowCommons"),
"sv" => array("name" => "Svenska", "template" => "NowCommons"),
"tr" => array("name" => "Türkçe", "template" => "NowCommons"),
"uk" => array("name" => "??????????", "template" => "NowCommons"),
"vi" => array("name" => "Tie^'ng Vie^.t", "template" => "NowCommons"),
"zh" => array("name" => "??", "template" => "NowCommons"),
"zh-yue" => array("name" => "??", "template" => "NowCommons"));
*/

$languages = array (
"commons" => array("name" => "Commons", "templatestart" => "{{Duplicate|", "templateend" => "}}"),
"el" => array("name" => "Greek", "templatestart" => "{{?????????|", "templateend" => "}}"),
"en" => array("name" => "English", "templatestart" => "{{Duplicate|Image:", "templateend" => "}}"),
"it" => array("name" => "Italiano", "templatestart" => "{{cancella subito|Duplicato dell immagine [[:Immagine:", "templateend" => "]]}}"),
"nl" => array("name" => "Nederlands", "templatestart" => "{{Nuweg|Duplicaat van [[:Afbeelding:", "templateend" => "]]}}"));

require_once('../database.inc');

mysql_connect('nlwiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db('nlwiki_p') or print mysql_error();

$lang = preg_replace('/ /', '_', mysql_real_escape_string($_GET['language']));
$page =0;
$page = mysql_real_escape_string($_GET['page']);
?>

<H2>Dupe finding tool</H2>
<P>Find all dupes on a wiki.</P>
This is a tool to find images at your wiki which are uploaded more than once. 
  <form name="Page_form">
  <select id="language" name="language">
  <?
  reset($languages);
  while ($language = current ($languages)){
   echo "<option ";
   if($lang==key($languages)){
       echo "SELECTED ";
   }
   echo "value='" . key($languages) . "'>" . key($languages) . " - " . $language['name']  . "</option>\n";
   next($languages);
   }
  ?>
   </select>
  <input type=submit value="Show me the dupes"><BR/>
 </form>
<?

if(!$lang == '') {

mysql_close();

mysql_connect($lang . 'wiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db($lang . 'wiki_p') or print mysql_error();

//$query = "SELECT langimage.img_name AS lang_image, commonsimage.img_name AS commons_image FROM image AS langimage JOIN commonswiki_p.image AS commonsimage ON langimage.img_sha1=commonsimage.img_sha1 AND NOT langimage.img_sha1=''";
//AND NOT EXISTS (SELECT * FROM templatelinks JOIN page ON tl_from=page_id WHERE page_title=langimage.img_name AND tl_title='" . $languages[$lang]['template']  . "')";
$query = "SELECT image1.img_name AS img1_name, image2.img_name AS img2_name FROM image AS image1 JOIN image AS image2 ON image1.img_sha1=image2.img_sha1 AND NOT image1.img_sha1='' AND NOT image1.img_name=image2.img_name AND image1.img_name<image2.img_name";

if($filter) {
    $query = $query . " AND langpage.page_title LIKE '" . $filter . "%' ";
}

$query = $query . " LIMIT " . $page *50 . ", 50";

$result = mysql_query($query);
 
if(!$result) Die("ERROR: No result returned.");
?>
<H3> The following images seem to be duplicates on the <? echo $lang;
?> wikipedia: </H3>
<ul>

<table width="80%">
<tr>
<th style="width:20%;" align="left"><? echo $lang; ?> image A</th>
<th style="width:20%;" align="left"><? echo $lang; ?> image B</th>
<th style="width:20%;" align="left">  </th>
<th style="width:20%;" align="left">  </th>
</tr>

<?

if($lang==commons) {
  $site="wikimedia";
} else {
  $site="wikipedia";
}

while($row = mysql_fetch_assoc($result))
{

?>
<tr>
 <td>
  <A href="http://<? echo $lang ?>.<? echo $site ?>.org/wiki/Image:<?
    echo urlencode($row['img1_name']) . "\">Image:" . preg_replace('/_/', ' ', $row['img1_name']) . "</A> ";
    ?>
 </td><td>
  <A href="http://<? echo $lang ?>.<? echo $site ?>.org/wiki/<?
    echo "Image:" . urlencode(preg_replace('/ /', '_', $row['img2_name'])) . "\">Image:" . preg_replace('/_/', ' ', $row['img2_name']) . "</A> ";
    ?>
 </td><td>
     <FORM ACTION="http://<? echo $lang ?>.<? echo $site ?>.org/w/index.php?title=Image:<? echo urlencode($row['img1_name']) ?>&action=edit&section=new" METHOD=POST>
        <input type='hidden' name='wpTextbox1' value='<? echo $languages[$lang]['templatestart']; echo preg_replace('/_/', ' ', $row['img2_name']); echo $languages[$lang]['templateend'];?>'>
      <input type='hidden' name='wpStarttime' value='<? echo date ("YmdHis") ?>'>
      <input type=submit value="Mark first picture as duplicate">
     </FORM>
 </td><td>
     <FORM ACTION="http://<? echo $lang ?>.<? echo $site ?>.org/w/index.php?title=Image:<? echo urlencode($row['img2_name']) ?>&action=edit&section=new" METHOD=POST>
       <input type='hidden' name='wpTextbox1' value='<? echo $languages[$lang]['templatestart']; echo preg_replace('/_/', ' ', $row['img1_name']); echo $languages[$lang]['templateend'];?>'>
       <input type='hidden' name='wpStarttime' value='<? echo date ("YmdHis") ?>'>
       <input type=submit value="Mark second picture as duplicate">
     </FORM>
  </td>
</tr>
<?
}
?> </table> 

<form name="Next_page">
 <input type='hidden' name='language' value='<? echo $lang ?>'>
 <input type='hidden' name='page' value='<? echo $page+1 ?>'>
 <input type='hidden' name='filter' value='<? echo $filter ?>'>
 <input type='submit' value='Next page'>
</form>
<?
}
mysql_close();

include("inc/footer.php"); ?>
