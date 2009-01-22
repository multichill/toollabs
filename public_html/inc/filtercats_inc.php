<?php 
/*
Released under the GNU General Public License by Multichill
*/

function filter_categories($current_cats){
/*
Function to filter categories at Commons.
The function expects an array containing the current categories and a working mysql connection.

The function returns an array containing the new categories and the categories filtered out.
*/ 
    $n_current_cats = count($current_cats);    
    
    $new_cats=array(); // Array of the new categories to return
    $filtered_cats=array(); // Array of the filtered out categories to return

    @mysql_select_db('u_multichill_commons_categories_p') or print mysql_error();

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
	$query = $query . "c1.child='" . preg_replace('/ /', '_', mysql_real_escape_string($current_cats[$i])) . "'";
	if($i+1 < $n_current_cats){
	    $query =  $query . " OR ";
	}
    }
    $result = mysql_query($query);
    
    // Return nothing
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
    }

    mysql_close();

    for($i= 0; $i < $n_current_cats; $i++){
	if(array_search($current_cats[$i], $parent_cats)===FALSE){
	    $new_cats[]=$current_cats[$i];
	} else {
	    $filtered_cats[]=$current_cats[$i];
	}
    }
    return array(
	'filtered' => $filtered_cats,
	'new' => $new_cats
    );
}
?>
