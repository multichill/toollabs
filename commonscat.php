<?php 
$title = "Commonscat tool";
$modified = date ("G:i, n F Y", getlastmod());

ini_set('default_charset', 'utf-8');
mb_internal_encoding("UTF-8");

include("inc/header.php"); 

$languages = array (
"af" => array("name" => "Afrikaans", "template" => "CommonsKategorie"),
"als" => array("name" => "Alemannisch", "template" => "Commonscat"),
"az" => array("name" => "Az?rbaycan", "template" => "CommonsKat"),
"bg" => array("name" => "?????????", "template" => "Commonscat"),
"ca" => array("name" => "Català", "template" => "Commonscat"),
"cs" => array("name" => "C(esky", "template" => "Commonscat"),
"da" => array("name" => "Dansk", "template" => "Commonscat"),
"de" => array("name" => "Deutsch", "template" => "Commonscat"),
"en" => array("name" => "English", "template" => "Commons cat"),
"eo" => array("name" => "Esperanto", "template" => "Commonscat"),
"es" => array("name" => "Español", "template" => "Commonscat"),
"eu" => array("name" => "Euskara", "template" => "Commonskat"),
"fi" => array("name" => "Suomi", "template" => "Commonscat"),
"fr" => array("name" => "Français", "template" => "Commonscat"),
"hr" => array("name" => "Hrvatski", "template" => "Commonscat"),
//"hu" => array("name" => "Magyar", "template" => "Közvagyonkat"),
"id" => array("name" => "Bahasa Indonesia", "template" => "Commonscat"),
"io" => array("name" => "Ido", "template" => "Commonscat"),
"is" => array("name" => "Íslenska", "template" => "CommonsCat"),
"it" => array("name" => "Italiano", "template" => "Commonscat"),
"ja" => array("name" => "???", "template" => "Commonscat"),
"ko" => array("name" => "???", "template" => "Commonscat"),
"li" => array("name" => "Limburgs", "template" => "Commonscat"),
"lt" => array("name" => "Lietuviu;", "template" => "Commonscat"),
"lv" => array("name" => "Latviešu", "template" => "Commonscat"),
//"mk" => array("name" => "??????????", "template" => "%D0%A8%D0%B0%D0%B1%D0%BB%D0%BE%D0%BD:%D0%A0%D0%B8%D0%B7%D0%BD%D0%B8%D1%86%D0%B0-%D0%B2%D1%80%D1%81%D0%BA%D0%B0"),
"ms" => array("name" => "Bahasa Melayu", "template" => "Commonscat"),
"nl" => array("name" => "Nederlands", "template" => "Commonscat"),
"nn" => array("name" => "Norsk (nynorsk)", "template" => "Commonscat"),
"no" => array("name" => "Norsk (bokmål)", "template" => "Commonscat"),
"oc" => array("name" => "Occitan", "template" => "Commonscat"),
"os" => array("name" => "??????", "template" => "Commonscat"),
"pl" => array("name" => "Polski", "template" => "Commonscat"),
"pt" => array("name" => "Português", "template" => "Commonscat"),
"ro" => array("name" => "Româna(", "template" => "Commonscat"),
"ru" => array("name" => "???????", "template" => "Commonscat"),
"scn" => array("name" => "Sicilianu", "template" => "Commonscat"),
"sh" => array("name" => "Srpskohrvatski", "template" => "Commonscat"),
"simple" => array("name" => "Simple English", "template" => "Commonscat"),
"sk" => array("name" => "Slovenc(ina", "template" => "Commonscat"),
"sl" => array("name" => "Slovenšc(ina", "template" => "Kategorija_v_Zbirki"),
"sr" => array("name" => "Srpski", "template" => "Commonscat"),
"su" => array("name" => "Basa Sunda", "template" => "Commonscat"),
"sv" => array("name" => "Svenska", "template" => "Commonscat"),
"th" => array("name" => "???", "template" => "Commonscat"),
"tr" => array("name" => "Türkçe", "template" => "CommonsKat"),
"uk" => array("name" => "??????????", "template" => "Commonscat"),
"vi" => array("name" => "Tie^'ng Vie^.t", "template" => "Commonscat"),
"zh" => array("name" => "??", "template" => "Commonscat"),
"zh-yue" => array("name" => "??", "template" => "???"));

require_once('../database.inc');

mysql_connect('nlwiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db('nlwiki_p') or print mysql_error();

$lang = preg_replace('/ /', '_', mysql_real_escape_string($_GET['language']));
$filter = preg_replace('/ /', '_', mysql_real_escape_string($_GET['filter']));
$page =0;
$page = mysql_real_escape_string($_GET['page']);
?>

<H2>Commonscat tool</H2>
<P>Find links to commons categories for your wikipedia. Select your language. Check a suggestion and click the add button add the suggestion.</P>

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
  <input type=submit value="Show suggestions"><BR/>
  (optional) page starting with:
  <input type="text" name="filter" size="10" value="<? echo $filter ?>"></input>
 </form>
<?

if(!$lang == '') {

mysql_close();

mysql_connect($lang . 'wiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db($lang . 'wiki_p') or print mysql_error();

if($lang=='en') {
    $query = "SELECT DISTINCT langpage.page_title AS langcat, cpage.page_title AS commonscat FROM page AS langpage JOIN commonswiki_p.page AS cpage ON langpage.page_title=cpage.page_title WHERE langpage.page_namespace=14 AND langpage.page_is_redirect=0 AND NOT EXISTS (SELECT * FROM templatelinks WHERE tl_from=langpage.page_id AND (tl_title='Commons_cat' OR tl_title='Commonscat' OR tl_title='Commons' OR tl_title='Sisterlinks' OR tl_title='Commonscat1A' OR tl_title='Commoncats' OR tl_title='Commonscat4Ra' OR tl_title='Commonscat1' OR tl_title='Sistercommons' OR tl_title='Commonscat-inline' OR tl_title='Sisterlinkswp' OR tl_title='Category_redirect' OR tl_title='Wikipedia_category' OR tl_title='Tracking_category' OR tl_title='Template_category')) AND cpage.page_namespace=14 AND cpage.page_is_redirect=0";

} else {
    $query = "SELECT DISTINCT langpage.page_title AS langcat, cpage.page_title AS commonscat FROM page AS langpage JOIN langlinks ON langpage.page_id=ll_from JOIN commonswiki_p.page AS cpage ON REPLACE(REPLACE(ll_title, 'Category:',''),' ','_')=cpage.page_title WHERE langpage.page_namespace=14 AND langpage.page_is_redirect=0 AND ll_lang='en' AND NOT EXISTS (SELECT * FROM templatelinks WHERE tl_from=langpage.page_id AND tl_title='" . $languages[$lang]['template']  . "') AND cpage.page_namespace=14 AND cpage.page_is_redirect=0";
}
if($filter) {
    $query = $query . " AND langpage.page_title LIKE '" . $filter . "%' ";
}

$query = $query . " LIMIT " . $page *50 . ", 50";


$result = mysql_query($query);
 
if(!$result) Die("ERROR: No result returned.");
?>
<H3> The following categorylinks are suggested on <? echo $lang;
?> wikipedia: </H3>
<ul>

<table width="80%">
<tr>
<th style="width:20%;" align="left"><? echo $lang; ?> category </th>
<th style="width:20%;" align="left">commons category </th>
<th style="width:20%;" align="left">  </th>
</tr>

<?

while($row = mysql_fetch_assoc($result))
{

#$image = urlencode(preg_replace('/_/', ' ', $row['fa_name']));
$langcat = urlencode($row['langcat']);
$commonscat = urlencode($row['ll_title']);
?>
<tr>
 <td>
  <A href="http://<? echo $lang ?>.wikipedia.org/wiki/Category:<?
    echo urlencode($row['langcat']) . "\">Category:" . preg_replace('/_/', ' ', $row['langcat']) . "</A> ";
    ?>
 </td><td>
  <A href="http://commons.wikimedia.org/wiki/<?
    echo "Category:" . urlencode(preg_replace('/ /', '_', $row['commonscat'])) . "\">Category:" . preg_replace('/_/', ' ', $row['commonscat']) . "</A> ";
    ?>
 </td><td>
     <FORM ACTION="http://<? echo $lang ?>.wikipedia.org/w/index.php?title=Category:<? echo urlencode($row['langcat']) ?>&action=edit&section=new" METHOD=POST>
      <input type='hidden' name='wpTextbox1' value='{{<? echo $languages[$lang]['template'] ?>|<? echo preg_replace('/_/', ' ', $row['commonscat']); ?>}}'>
      <input type='hidden' name='wpStarttime' value='<? echo date ("YmdHis") ?>'>
      <input type='hidden' name='wpMinoredit' value="1" id="wpMinoredit">
      <input type=submit value="Add category link">
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
