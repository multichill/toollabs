<?php 
$title = "Disambiguation page creator";
$modified = date ("G:i, n F Y", getlastmod());

include("inc/header.php");
/*
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
 <head>
 <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
  <TITLE>Maak een doorverwijspagina</TITLE>
 </head>
 <body bgcolor="white">
*/
?>
<H2>Disambiguation page creator</H2>
<P>Met dit formulier kan je snel een simpele doorverwijspagina op de Nederlandse wikipedia genereren.
 Check je edits voordat je een pagina daadwerkelijk opslaat.</P>

 <form name="Page_form">
  <input type=text name="page" size=20>
  <input type=submit value="Genereer doorverwijspagina">
 </form>
<?
require_once('../database.inc');

mysql_connect('nlwiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db('nlwiki_p') or print mysql_error();

$page = preg_replace('/ /', '_', mysql_real_escape_string($_GET['page']));

if(!$page == '') {

$query = "SELECT page_title FROM page WHERE page_title like '" . $page . "_(%' AND page_is_redirect=0 AND page_namespace=0 LIMIT 20";
#$query = "SELECT page_title FROM page WHERE page_title like 'Amsterdam_(%' LIMIT 20";

$result = mysql_query($query);
 
if(!$result) Die("ERROR: No result returned.");

?>
  <!-- Start wiki form part -->
  <form action="http://nl.wikipedia.org/w/index.php?title=<?
   echo $page;
  ?>&amp;action=submit" enctype="multipart/form-data" name="Wiki_form" target=_main method=post>
   <BR>
   <input type='hidden' value="<? 

 echo date("YmdHis");
  #20071106194851

?>" name="wpStarttime" />
   <!-- <input type='hidden' value="20071106194851" name="wpEdittime" /> -->
   <input type=hidden name="wpSummary" value="Ik ben zo stom gewenst om mijn edit niet na te kijken">
   <BR>
   <textarea tabindex='1' accesskey="," name="wpTextbox1" id="wpTextbox1" rows='25' cols='80' ><?
echo "{{dpintro}}\n";

while($row = mysql_fetch_assoc($result))
{
    echo "*[[" . preg_replace('/_/', ' ', $row['page_title']) . "]]\n";
}

echo "{{dp}}\n";
echo "\n";
 
mysql_close();
?>
   </textarea></BR>
   <input type=submit value="Laat de pagina op de wikipedia zien" id="wpDiff" name="wpDiff">
  </form>
  <!-- End wiki part -->

<? } 
include("inc/footer.php"); ?>
