<?php
// Probably have to do some cleaning up here
$query = $_GET['query'];
?>
<html>
<frameset rows="10%,90%">
  <frame name="toolbar" src="toolbar.php" />
  <frame name="Europeana" src="http://www.europeana.eu/portal/search.html?query=<?php echo $query ?>" />
</frameset>
</html>
