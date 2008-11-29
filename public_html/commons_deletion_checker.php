<?php 
$title = "Commons deletion checker";
$modified = date ("G:i, n F Y", getlastmod());

include("inc/header.php"); 

/*
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
 <head>
 <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
  <TITLE>Compare the articles up for deletion on commons with your home wiki</TITLE>
 </head>
 <body bgcolor="white">
*/
?>
<H2>Commons deletion checker</H2>
<P>Compare the articles up for deletion on commons with your home wiki</P>

 <form name="Page_form">
  <input type=text name="page" size=20>
   <select id="language" name="language">
    <option value="af">af - Afrikaans</option>
    <option value="da">da - Dansk</option>
    <option value="de">de - Deutsch</option>
    <option value="en">en - English</option>
    <option value="eo">eo - Esperanto</option>
    <option value="es">es - Español</option>
    <option value="fi">fi - Suomi</option>
    <option value="fr">fr - Français</option>
    <option value="it">it - Italiano</option>
    <option value="nl">nl - Nederlands</option>
    <option value="nn">nn - Norsk (nynorsk)</option>
    <option value="no">no - Norsk (bokmål)</option>
    <option value="pl">pl - Polski</option>
    <option value="pt">pt - Português</option>
    <option value="sv">sv - Svenska</option>
   </select>
  <input type=submit value="Show the logs">
 </form>
<?
require_once('../database.inc');

mysql_connect('nlwiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db('nlwiki_p') or print mysql_error();

$lang = preg_replace('/ /', '_', mysql_real_escape_string($_GET['language']));

if(!$lang == '') {

$query = "SELECT DISTINCT fa_name FROM " . $lang . "wiki_p.filearchive, commonswiki_p.page, commonswiki_p.templatelinks  WHERE filearchive.fa_name=page.page_title AND page.page_id=templatelinks.tl_from AND page_is_redirect=0 AND page_namespace=6 AND (tl_title='No_source_since' OR tl_title='No_permission_since' OR tl_title='Delete') LIMIT 100";

$result = mysql_query($query);
 
if(!$result) Die("ERROR: No result returned.");
?>
<H3> The following images are up for deletion at commons and are already deleted at the <? echo $lang;
?> wikipedia: </H3>
<ul>
<?

while($row = mysql_fetch_assoc($result))
{

#$image = urlencode(preg_replace('/_/', ' ', $row['fa_name']));
$image = urlencode($row['fa_name']);
?>
<li><A href="http://<?
echo $lang;
?>.wikipedia.org/wiki/Image:<?
    echo $image . "\">" . $image . "</A></li>\n";
}
?></ul><?
$query = "select DISTINCT " . $lang . "wiki_p.filearchive.fa_name, " . $lang . "wiki_p.filearchive.fa_deleted_reason AS lang_deleted_reason, commonswiki_p.filearchive.fa_deleted_reason AS commons_deleted_reason FROM " . $lang . "wiki_p.filearchive JOIN commonswiki_p.filearchive ON " . $lang . "wiki_p.filearchive.fa_name=commonswiki_p.filearchive.fa_name WHERE  commonswiki_p.filearchive.fa_deleted_timestamp>20071015000000 LIMIT 500";

$result = mysql_query($query);
 
 if(!$result) Die("ERROR: No result returned.");
 ?>
<H3>The following images are deleted at commons and also deleted at the  <? echo $lang; ?> wikipedia: </H3>

<table width="80%">
<tr>
<th style="width:20%;" align="left"><? echo $lang; ?> image </th>
<th style="width:20%;" align="left"><? echo $lang; ?> deletion reason </th>
<th style="width:20%;" align="left">Commons image </th>
<th style="width:20%;" align="left">Commons deletion reason</th>
</tr>
<?

while($row = mysql_fetch_assoc($result))
{
$image = urlencode($row['fa_name']);
?>
<tr>
 <td>
  <SMALL><A href="http://nl.wikipedia.org/wiki/Image:<?
    echo $image . "\">" . preg_replace('/_/', ' ', $image) . "</A> ";
    ?></SMALL>
 </td><td>
  <SMALL><A href="http://nl.wikipedia.org/w/index.php?title=Speciaal:Log&page=Image:<?
   echo $image . "\">" . $row['lang_deleted_reason'];
     ?></SMALL>
 </td><td>
     <?
     ?> <SMALL><A href="http://commons.wikimedia.org/wiki/Image:<?
         echo $image . "\">" . preg_replace('/_/', ' ', $image) . "</A> ";
     ?></SMALL>
 </td><td>
  <SMALL><A href="http://commons.wikimedia.org/w/index.php?title=Special:Log&page=Image:<?
    echo $image . "\">" . $row['commons_deleted_reason'];
     ?></SMALL>
 </td>
</tr>
<?
}
?> </table> <?
}
mysql_close();

include("inc/footer.php"); ?>

