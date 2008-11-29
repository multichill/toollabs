<?php 
$title = "Filter categories";
$modified = date ("G:i, n F Y", getlastmod());

$source = $_GET['source'];
$bot = $_GET['bot'];

require_once('../database.inc');

if(!$bot) {
include("inc/header.php");

?>

<H2>Filter categories</H2>
<P>Filter out the redundant parent categories from images at commons.</P>

<H3>Source</H3>
 <form name="Page_form">
  <textarea name="source" id="source" rows='15' cols='80' ><? echo $source ?></textarea>
  <input type=submit value="Filter"><BR/>
 </form>
<?
}

if(!$source == '') {
 // First get a list of current categories
 $cat_regex = "/\[\[Category:([^\]^\|]*)\]\](\r\n)*/";
 $n_current_cats = preg_match_all($cat_regex, $source, &$current_cats);
 
 if($n_current_cats){
  $old_cats = array();
  for($i= 0; $i < $n_current_cats; $i++){
   $old_cats[] = $current_cats[1][$i];
  }
 }

 // Remove all categories from the source
 $source_cats_removed = $source;
 $source_cats_removed = preg_replace  ($cat_regex, "", $source_cats_removed);
 $source_cats_removed = trim($source_cats_removed);  

 // Filter the current categories

 mysql_connect('nlwiki-p.db.ts.wikimedia.org',$toolserver_username,$toolserver_password);

$query = "
SELECT
c1.parent AS c1p,
c2.parent AS c2p,
c3.parent AS c3p,
c4.parent AS c4p,
c5.parent AS c5p,
c6.parent AS c6p,
c7.parent AS c7p,
c8.parent AS c8p
FROM 
cats AS c1 
JOIN cats AS c2 ON c1.parent=c2.child
JOIN cats AS c3 ON c2.parent=c3.child
JOIN cats AS c4 ON c3.parent=c4.child
JOIN cats AS c5 ON c4.parent=c5.child
JOIN cats AS c6 ON c5.parent=c6.child
JOIN cats AS c7 ON c6.parent=c7.child
JOIN cats AS c8 ON c7.parent=c8.child
WHERE ";

for($i= 0; $i < $n_current_cats; $i++){
 $query = $query . "c1.child='" . preg_replace('/ /', '_', mysql_real_escape_string($old_cats[$i])) . "'";
 if($i+1 < $n_current_cats){
  $query =  $query . " OR ";
 }
}

@mysql_select_db('u_multichill') or print mysql_error();

$result = mysql_query($query);

if(!$result) Die("ERROR: No result returned.");

$parent_cats = array();

while($row = mysql_fetch_assoc($result)) {
 if (!in_array(preg_replace('/_/', ' ', $row['c1p']), $parent_cats)){
    $parent_cats[]=preg_replace('/_/', ' ', $row['c1p']);
 }
 if (!in_array(preg_replace('/_/', ' ', $row['c2p']), $parent_cats)){
    $parent_cats[]=preg_replace('/_/', ' ', $row['c2p']);
 }
 if (!in_array(preg_replace('/_/', ' ', $row['c3p']), $parent_cats)){
    $parent_cats[]=preg_replace('/_/', ' ', $row['c3p']);
 }
 if (!in_array(preg_replace('/_/', ' ', $row['c4p']), $parent_cats)){
    $parent_cats[]=preg_replace('/_/', ' ', $row['c4p']);
 }
 if (!in_array(preg_replace('/_/', ' ', $row['c5p']), $parent_cats)){
    $parent_cats[]=preg_replace('/_/', ' ', $row['c5p']);
 }
 if (!in_array(preg_replace('/_/', ' ', $row['c6p']), $parent_cats)){
    $parent_cats[]=preg_replace('/_/', ' ', $row['c6p']);
 }
 if (!in_array(preg_replace('/_/', ' ', $row['c7p']), $parent_cats)){
    $parent_cats[]=preg_replace('/_/', ' ', $row['c7p']);
 }
 if (!in_array(preg_replace('/_/', ' ', $row['c8p']), $parent_cats)){
    $parent_cats[]=preg_replace('/_/', ' ', $row['c8p']);
 }
 /*
 $parent_cats[]=preg_replace('/_/', ' ', $row['c1p']);
 $parent_cats[]=preg_replace('/_/', ' ', $row['c2p']);
 $parent_cats[]=preg_replace('/_/', ' ', $row['c3p']);
 $parent_cats[]=preg_replace('/_/', ' ', $row['c4p']);
 $parent_cats[]=preg_replace('/_/', ' ', $row['c5p']);
 $parent_cats[]=preg_replace('/_/', ' ', $row['c6p']);
 $parent_cats[]=preg_replace('/_/', ' ', $row['c7p']);
 $parent_cats[]=preg_replace('/_/', ' ', $row['c8p']);
 */
}


mysql_close();

//Seems to be broken
//$parent_cats = array_unique($parent_cats);


$new_cats=array();
$filtered_cats=array();


for($i= 0; $i < $n_current_cats; $i++){
 if(array_search($old_cats[$i], $parent_cats)===FALSE){
  $new_cats[]=$old_cats[$i];
 } else {
  $filtered_cats[]=$old_cats[$i];
 }
}

// Add the remaining categories to the filtered source (or uncat if none left?)
$source_filtered = $source_cats_removed;

/*
if(count($filtered_cats)){
 $source_filtered= $source_filtered . "\n<!-- The following categories were removed:\n";
 foreach($filtered_cats as $cat){
  $source_filtered = $source_filtered . "[[Category:" . $cat . "]]\n";
 }
 $source_filtered= $source_filtered . "-->";
}
*/
foreach($new_cats as $cat){
 $source_filtered = $source_filtered . "\n[[Category:" . $cat . "]]";
}

if(!$bot){ 

?>
<H3>Result</H3>
<textarea name="result" id="result" rows='15' cols='80'><? echo $source_filtered ?></textarea>
<?
include("inc/footer.php");
} else {
echo $source_filtered;
}

}
?>
