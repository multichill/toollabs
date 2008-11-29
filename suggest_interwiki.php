<?php 
$title = "Suggest interwiki";
$modified = date ("G:i, n F Y", getlastmod());

include("inc/header.php"); 

require_once('../database.inc');

// First get all variables
mysql_connect('nlwiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);

$fromlang= mysql_real_escape_string($_GET['fromlang']);
$tolang= mysql_real_escape_string($_GET['tolang']);
$typequery= mysql_real_escape_string($_GET['typequery']);
$catquery= mysql_real_escape_string($_GET['catquery']);
$cats = urldecode($_GET['cats']);
list($fromcat, $tocat)=split("\|", $cats, 2);
$fromcat=preg_replace('/ /', '_', mysql_real_escape_string($fromcat));
$tocat = preg_replace('/ /', '_', mysql_real_escape_string($tocat));
list($category, $tocat)=split(":", $tocat, 2);

@mysql_select_db('toolserver') or print mysql_error();
$query_langs = "SELECT lang FROM wiki WHERE family='wikipedia'";

$result_langs = mysql_query($query_langs);

while($row = mysql_fetch_assoc($result_langs)){
 $langs[]= $row['lang'];
}
sort($langs);

mysql_close();
?>
<H2>Suggest interwiki</H2>
<P>Get interwiki suggestions for categories. Select the languages to work on and the parent categories to work on.</P>
<H3>Languages and query</H3>
<form name="Query_form">
 <select id="fromlang" name="fromlang">
  <?
   foreach ($langs as $key => $val) {
    echo "<option ";
    if($fromlang==$val){
     echo "SELECTED ";
    }
    echo "value='" . $val . "'>" . $val   . "</option>\n";
  }
  ?>
 </select>
 <select id="tolang" name="tolang">
  <?
   foreach ($langs as $key => $val) {
    echo "<option ";
    if($tolang==$val){
     echo "SELECTED ";
    }   
    echo "value='" . $val . "'>" . $val   . "</option>\n";
   }     
  ?>
 </select>
 <select ip="typequery" name="typequery">
  <option <? if ($typequery=='begin'){?>SELECTED <? } ?>value='begin'>The parentcategory to work on starts with:</option>
  <option <? if ($typequery=='contains'){?>SELECTED <? } ?>value='contains'>The parentcategory to work on contains:</option>
  <option <? if ($typequery=='end'){?>SELECTED <? } ?>value='end'>The parentcategory to work on ends with:</option>
 </select>
 <input type=text name="catquery" value='<? echo $catquery; ?>' size=20>
 <input type=submit value="Show categories to work on"><BR/>
</form>
<?
// From lang achterhalen
// To lang achterhalen
// Query in een box stoppen
// Begin/midden/eind

if(!($fromlang == '' || $tolang == '')) {

if($typequery=='begin'){
 $finalcatquery = $catquery . '%';
} elseif ($typequery=='contains') {
 $finalcatquery = '%' . $catquery . '%';
} elseif ($typequery=='end'){
  $finalcatquery = '%' . $catquery;
}

mysql_connect($fromlang . 'wiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db(preg_replace('/-/', '_', $fromlang) . 'wiki_p') or print mysql_error();

$query_start = "SELECT page_title, ll_title FROM page JOIN langlinks ON page_id=ll_from WHERE page_namespace=14 AND page_title LIKE '" . preg_replace('/ /', '_', $finalcatquery) . "' AND ll_lang='" . $tolang . "' LIMIT 250";
echo $query_start;
$result_start = mysql_query($query_start);

?>

<H3>Select category to work on</H3>
<P></P>

 <form name="Page_form">
  <input type='hidden' name='fromlang' value='<? echo $fromlang; ?>'>
  <input type='hidden' name='tolang' value='<? echo $tolang; ?>'>
  <input type='hidden' name='typequery' value='<? echo $typequery; ?>'>
  <input type='hidden' name='catquery' value='<? echo $catquery; ?>'>
  <select id="cats" name="cats">
  <?
  while($row = mysql_fetch_assoc($result_start)){
   echo "<option ";
   if($fromcat==$row['page_title']){
   	echo "SELECTED ";
   }
   echo "value='" . urlencode($row['page_title']) . "|" . urlencode($row['ll_title']) . "'>" . preg_replace('/_/', ' ', $row['page_title'])   . "</option>\n";
   }
  ?>
   </select>
  <input type=submit value="Show suggestions"><BR/>
 </form>
<?
mysql_close();


if(!($fromcat == '' || $tocat == '')) {

$tocats = array();

mysql_connect($tolang . 'wiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db($tolang . 'wiki_p') or print mysql_error();

$query_to= "SELECT page_title FROM page JOIN categorylinks ON page_id=cl_from WHERE page_namespace=14 AND page_is_redirect=0 AND cl_to ='" . $tocat . "' AND NOT EXISTS(SELECT * FROM langlinks WHERE ll_from=page_id AND ll_lang='" . $fromlang . "')";

$result_to = mysql_query($query_to);
if(!$result_to) Die("ERROR: No result returned.");

while($row = mysql_fetch_assoc($result_to)){
 $tocats[]= $row['page_title'];
 //echo $row['page_title'] . "\n";
 }
sort($tocats);
/*
foreach ($tocats as $key => $val) {
    echo  $val . "\n";
}
*/
mysql_close();

mysql_connect($fromlang . 'wiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db(preg_replace('/-/', '_', $fromlang) . 'wiki_p') or print mysql_error();

$query_from= "SELECT page_title FROM page JOIN categorylinks ON page_id=cl_from WHERE page_namespace=14 AND page_is_redirect=0 AND cl_to ='" . $fromcat . "' AND NOT EXISTS(SELECT * FROM langlinks WHERE ll_from=page_id)";
$result_from = mysql_query($query_from);

if(!$result_from) Die("ERROR: No result returned.");
 
?>
<H3> The following interwikilinks are suggested from <? echo $fromlang; ?> to <? echo $tolang; ?></H3>
<ul>

<table width="80%">
<tr>
<th style="width:20%;" align="left"><? echo $fromlang; ?> category </th>
<th style="width:20%;" align="left"><? echo $tolang; ?> category </th>
</tr>

<?

while($row = mysql_fetch_assoc($result_from))
{

$langcat = urlencode($row['langcat']);
$commonscat = urlencode($row['ll_title']);
?>
<tr>
 <td>
  <A href="http://<? echo $fromlang ?>.wikipedia.org/wiki/Category:<?
    echo urlencode($row['page_title']) . "\">Category:" . preg_replace('/_/', ' ', $row['page_title']) . "</A> ";
    ?>
 </td>
 <td>
     <FORM ACTION="http://<? echo $fromlang ?>.wikipedia.org/w/index.php?title=Category:<? echo urlencode($row['page_title']) ?>&action=edit&section=new" METHOD=POST>
        <select id="wpTextbox1" name="wpTextbox1">
	  <?
	  foreach ($tocats as $key => $val) {
	      echo "<option value='[[" . $tolang . ":Category:" . preg_replace('/_/', ' ', $val) . "]]'>" . preg_replace('/_/', ' ', $val)  . "</option>\n";
	  }
	  ?>
	 </select>
      <input type='hidden' name='wpStarttime' value='<? echo date ("YmdHis") ?>'>
      <input type='hidden' name='wpMinoredit' value="1" id="wpMinoredit">
      <input type=submit value="Add interwiki link">
     </FORM>
 </td>
</tr>
<?
}
?> </table> 

<?
mysql_close();
}
}
include("inc/footer.php"); ?>
