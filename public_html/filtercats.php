<?php 
$title = "Filter categories";
$modified = date ("G:i, n F Y", getlastmod());

$source = $_GET['source'];
$bot = $_GET['bot'];

require_once('../database.inc');
require_once('./inc/filtercats_inc.php');
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
$filter_result = filter_categories($old_cats);

$new_cats=$filter_result['new'];
$filtered_cats=$filter_result['filtered'];

// Add the remaining categories to the filtered source (or uncat if none left?)
$source_filtered = $source_cats_removed;

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
