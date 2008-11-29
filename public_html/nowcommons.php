<?php 
$title = "Nowcommons tool";
$modified = date ("G:i, n F Y", getlastmod());

include("inc/header.php"); 

$languages = array (
"af" => array("name" => "Afrikaans", "template" => "NowCommons"),
"als" => array("name" => "Alemannisch", "template" => "NowCommons"),
"ar" => array("name" => "Arabic", "template" => "NowCommons"),
"bar" => array("name" => "Boarisch", "template" => "NowCommons"),
"bg" => array("name" => "Bulgarian", "template" => "NowCommons"),
"ca" => array("name" => "Català", "template" => "AraCommons"),
"cs" => array("name" => "C(esky", "template" => "NowCommons"),
"da" => array("name" => "Dansk", "template" => "NowCommons"),
"de" => array("name" => "Deutsch", "template" => "NowCommons"),
// 1 plaatje "dsb" => array("name" => "Dolnoserbski", "template" => "NowCommons"),
"en" => array("name" => "English", "template" => "Subst:Ncd"),
"eo" => array("name" => "Esperanto", "template" => "Nun en komunejo"),
// es is al leeg
"es" => array("name" => "Español", "template" => "EnCommons"),
"fa" => array("name" => "Farsi", "template" => "NowCommons"),
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
"vo" => array("name" => "Volapük", "template" => "NowCommons"),
"zh" => array("name" => "??", "template" => "NowCommons"),
"zh-yue" => array("name" => "??", "template" => "NowCommons"));

require_once('../database.inc');

mysql_connect('nlwiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db('nlwiki_p') or print mysql_error();

$lang = preg_replace('/ /', '_', mysql_real_escape_string($_GET['language']));
$page =0;
$page = mysql_real_escape_string($_GET['page']);
?>

<H2>Nowcommons all the dupes</H2>
<P>Find dupes. </P>
This is a tool to find images at your wikipedia which are already present at commons. Please check the image at commons to see if all the required information (author, source and licence) is present.
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

$query = "SELECT langimage.img_name AS lang_image, commonsimage.img_name AS commons_image FROM image AS langimage JOIN commonswiki_p.image AS commonsimage ON langimage.img_sha1=commonsimage.img_sha1 AND NOT langimage.img_sha1='' AND langimage.img_size=commonsimage.img_size AND langimage.img_width=commonsimage.img_width AND langimage.img_height=commonsimage.img_height";
//AND NOT EXISTS (SELECT * FROM templatelinks JOIN page ON tl_from=page_id WHERE page_title=langimage.img_name AND tl_title='" . $languages[$lang]['template']  . "')";

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
<th style="width:20%;" align="left"><? echo $lang; ?> image </th>
<th style="width:20%;" align="left">commons image </th>
<th style="width:20%;" align="left">  </th>
</tr>

<?

while($row = mysql_fetch_assoc($result))
{

?>
<tr>
 <td>
  <A href="http://<? echo $lang ?>.wikipedia.org/wiki/Image:<?
    echo urlencode($row['lang_image']) . "\">Image:" . preg_replace('/_/', ' ', $row['lang_image']) . "</A> ";
    ?>
 </td><td>
  <A href="http://commons.wikimedia.org/wiki/<?
    echo "Image:" . urlencode(preg_replace('/ /', '_', $row['commons_image'])) . "\">Image:" . preg_replace('/_/', ' ', $row['commons_image']) . "</A> ";
    ?>
 </td><td>
     <FORM ACTION="http://<? echo $lang ?>.wikipedia.org/w/index.php?title=Image:<? echo urlencode($row['lang_image']) ?>&action=edit&section=new" METHOD=POST>
      <? if($row['lang_image']==$row['commons_image']) { ?>
        <input type='hidden' name='wpTextbox1' value='{{<? echo $languages[$lang]['template'] ?>}}'>
      <? } else { ?>
        <input type='hidden' name='wpTextbox1' value='{{<? echo $languages[$lang]['template'] ?>|<? echo preg_replace('/_/', ' ', $row['commons_image']); ?>}}'>
      <? } ?>
      <input type='hidden' name='wpStarttime' value='<? echo date ("YmdHis") ?>'>
      <input type=submit value="Add nowcommons">
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
