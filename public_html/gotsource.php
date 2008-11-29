<?php 
$title = "Got source?";
$modified = date ("G:i, n F Y", getlastmod());

include("inc/header.php"); 
require_once('../database.inc');

$sources = array (
"ca" => "ca",
"de" => "de",
"en" => "en",
"eo" => "eo",
"es" => "es",
"fi" => "fi",
"fr" => "fr",
"it" => "it",
"ja" => "ja",
"nl" => "nl",
"no" => "no",
"pl" => "pl",
"pt" => "pt",
"ro" => "ro",
"ru" => "ru",
"sv" => "sv",
"tr" => "tr",
"vo" => "vo",
"uk" => "uk",
"zh" => "zh",
);

$imagetype = array (
"gif" => ".gif",
"jpeg" => ".jpg",
"ogg" => ".ogg",
"png" => ".png",
"pdf" => ".pdf",
"svg+xml" => ".svg");

mysql_connect('nlwiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db('nlwiki_p') or print mysql_error();

$lang = preg_replace('/ /', '_', mysql_real_escape_string($_GET['language']));
$project = preg_replace('/ /', '_', mysql_real_escape_string($_GET['project']));
$name = preg_replace('/ /', '_', mysql_real_escape_string($_GET['image_name']));

?>

<H2>Got source?</H2>
<P>Find the source of an image.</P>
This is a tool to find the source of an image. You can enter the location of the image you want to find the source of and this tool will look if it can find the image at another wiki.
  <form name="Page_form">
   <input type=text name="language" size=10 value='<? echo $lang ?>'>   
   <!-- <select id="project" name="project" value='<? echo $project ?>'>
    <option value='Commons'>Commons</option>
    <option value='Wikipedia'>Wikipedia</option>
   </select> -->
   <input type=text name="image_name" size=30 value='<? echo $name ?>'>
  <input type=submit value="Find the source"><BR/>
 </form>
<?

if(!($lang == '' || $name=='')) {

mysql_connect($lang . 'wiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db($lang . 'wiki_p') or print mysql_error();


$query1 = "SELECT img_name, img_description, img_user_text, img_timestamp, img_minor_mime, img_sha1 FROM image WHERE img_name = '" . $name . "'";

$result1 = mysql_query($query1);

if(!$result1) Die("ERROR: No result returned. Did you enter a valid language code and a right image name?");

while($row = mysql_fetch_assoc($result1)){
$img_sha1 = $row['img_sha1'];
$img_minor_mime = $row['img_minor_mime'];
?>
<H3>Image information</H3>
<P>
<ul>
<li>image name : <a href="http://<? echo key($sources) ?>.wikipedia.org/wiki/Image:<? echo $row['img_name'] . "\">" . $row['img_name'] ?></a></li>
<li>image description :  <? echo $row['img_description'] ?></li>
<li>image uploader :  <a href="http://<? echo key($sources) ?>.wikipedia.org/wiki/User:<? echo $row['img_user_text'] . "\">" . $row['img_user_text'] ?></a></li>
<li>image upload time :  <a href="http://<? echo key($sources) ?>.wikipedia.org/w/index.php?title=Special:Log&page=Image:<? echo $row['img_name'] . "\">" . date("H:i, j F Y (e)",strtotime($row['img_timestamp'])) ?></a></li>
<li>image type : <? echo $row['img_minor_mime'] ?></li>
<li>image hash : <? echo $row['img_sha1'] ?></li>
</ul>
</P>
<?
 }
 if(!$img_sha1==''){
  reset($sources);
  while ($source = current ($sources)){
   echo "<small>Working on " . key($sources) . ".wikipedia</small><BR/>\n";
   mysql_connect(key($sources) . 'wiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
   @mysql_select_db(key($sources) . 'wiki_p') or print mysql_error();

   $query2 = "SELECT img_name, img_description, img_user_text, img_timestamp FROM image WHERE img_sha1 = '" . $img_sha1 . "'";
 
   $result2 = mysql_query($query2);

   if(!$result2) Die("ERROR: No result returned.");

    while($row = mysql_fetch_assoc($result2)){
     ?>
<H3>Found <? echo $row['img_name'] ?> at <? echo key($sources) ?>.wikipedia </H3>
<P>
<ul>
<li>image name : <a href="http://<? echo key($sources) ?>.wikipedia.org/wiki/Image:<? echo $row['img_name'] . "\">" . $row['img_name'] ?></a></li>
<li>image description :  <? echo $row['img_description'] ?></li>
<li>image uploader :  <a href="http://<? echo key($sources) ?>.wikipedia.org/wiki/User:<? echo $row['img_user_text'] . "\">" . $row['img_user_text'] ?></a></li>
<li>image upload time :  <a href="http://<? echo key($sources) ?>.wikipedia.org/w/index.php?title=Special:Log&page=Image:<? echo $row['img_name'] . "\">" . date("H:i, j F Y (e)",strtotime($row['img_timestamp'])) ?></a></li>
</ul>
</P>
<?
   }
   $query3 = "SELECT fa_name, fa_deleted_user, fa_deleted_timestamp, fa_deleted_reason, fa_user_text, fa_timestamp FROM filearchive WHERE fa_storage_key='" . $img_sha1 . $imagetype[$img_minor_mime]  . "'";
   $result3 = mysql_query($query3);
   if(!$result3) Die("ERROR: No result returned.");

   while($row = mysql_fetch_assoc($result3)){
   ?>
   <H3>Found <? echo $row['fa_name'] ?> (deleted) at <? echo key($sources) ?>.wikipedia </H3>
   <P>
   <ul>
   <li>image name : <a href="http://<? echo key($sources) ?>.wikipedia.org/wiki/Image:<? echo $row['fa_name'] . "\">" . $row['fa_name'] ?></a></li>
   <li>image uploader :  <a href="http://<? echo key($sources) ?>.wikipedia.org/wiki/User:<? echo $row['fa_user_text'] . "\">" . $row['fa_user_text'] ?></a></li>
   <li>image upload time :  <a href="http://<? echo key($sources) ?>.wikipedia.org/w/index.php?title=Special:Log&page=Image:<? echo $row['fa_name'] . "\">" . date("H:i, j F Y (e)",strtotime($row['fa_timestamp'])) ?></a></li>
   <li>image deletion reason : <? echo $row['fa_deleted_reason'] ?></li>
   <li>image deletion time : <a href="http://<? echo key($sources) ?>.wikipedia.org/w/index.php?title=Special:Log&page=Image:<? echo $row['fa_name'] . "\">" . date("H:i, j F Y (e)",strtotime($row['fa_deleted_timestamp'])) ?></a></li>
   </ul>
   </P>
   <?

   }
   next($sources);
  }
 }
}

mysql_close();

include("inc/footer.php"); ?>
