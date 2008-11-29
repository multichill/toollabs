<?php 
$title = "Multi wiki contribution counter";
$modified = date ("G:i, n F Y", getlastmod());

include("inc/header.php");
/*

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
 <head>
 <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
  <TITLE>Contribs</TITLE>
 </head>
 <body bgcolor="white">
*/
?>
<H2>Multi wiki contribution counter</H2>
 <form name="Username_form">
  <input type=text name="username" size=20>
  <input type=submit value="Get results">
 </form>
 <textarea rows="100" cols="100">
<?
if(!$_GET['username']==''){

require_once('../database.inc');

#$wikis = array('aa','ab','af','ak','als', de','en','fr','nl');

$wikis = array('aa','ab','af','ak','als','am','an','ang','ar','arc','as','ast','av','ay','az','ba','bar',
'bat-smg','bcl',
'be',
'be-x-old',
'bg','bh','bi','bm','bn','bo','bpy','br','bs','bug','bxr','ca',
'cbk-zam',
'cdo','ce','ceb','ch','chr','chy','co','cr','cs','csb','cu','cv','cy','da','de','diq','dv','dz','ee','el','eml','en','eo','es','et','eu','fa','ff','fi',
'fiu-vro',
'fj','fo','fr','frp','fur','fy','ga','gd','gl','glk','gn','got','gu','gv','ha','hak','haw','he','hi','hr','hsb','ht','hu','hy','hz','ia','id','ie','ig','ik','ilo','io','is','it','iu','ja','jbo','jv','ka','kab','kg','ki','kk','kl','km','kn','ko','ks','ksh','ku','kv','kw','ky','la','lad','lb','lbe','lg','li','lij','lmo','ln','lo','lt','lv',
'map-bms',
'mg','mh','mi','mk','ml','mn','mr','ms','mt','my','mzn','na','nah','nap','nds',
'nds-nl',
'ne','new','ng','nl','nn','no','nov','nrm','nv','ny','oc','om','or','os','pa','pag','pam','pap','pdc','pi','pih','pl','pms','ps','pt','qu','rm','rmy','rn','ro',
'roa-rup',
'roa-tara',
'ru','rw','sa','sc','scn','sco','sd','se','sg','sh',
'si','simple','sk','sl','sm','sn','so','sq','sr','ss','st','su','sv','sw','ta','te','tet','tg','th','ti','tk','tl','tn','to','tpi','tr','ts','tt','tum','tw','ty','udm','ug','uk','ur','uz','ve','vec','vi','vls','vo','wa','war','wo','wuu','xal','xh','yi','yo','za','zea','zh',
'zh-classical',
'zh-min-nan',
'zh-yue',
'zu');

$total=0;

echo "{{#switch: {{{1}}}\n";

for ($i = 0; $i < count($wikis) ; $i++) {


mysql_connect($wikis[$i] . 'wiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);
@mysql_select_db(preg_replace('/-/','_', $wikis[$i]) . 'wiki_p') or print mysql_error();

$username = preg_replace('/ /', '_', mysql_real_escape_string($_GET['username']));

$query = "SELECT user_editcount FROM user WHERE user_name like '" . $username . "' LIMIT 20";

$result = mysql_query($query);
 
if(!$result) Die("ERROR: No result returned.");

while($row = mysql_fetch_assoc($result))
{
    echo "|    " . $wikis[$i] . " = "; 
    echo $row['user_editcount'];
    echo "\n";

$total = $total + $row['user_editcount'];
}
mysql_close();

}

echo "| total =" . $total . "\n";
echo "}}\n";
}
?>
 </textarea>
<?
/*
</body> 
</html>
*/
include("inc/footer.php"); ?>
