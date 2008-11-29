<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en" dir="ltr">
<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
	<title><?php
	if ($title) {
		echo $title;
	} else {
		echo "One of Multichill's tools";
	}
	?></title>
	<link href="Common.css" rel="stylesheet" type="text/css">
</head>
<body>
<div id="globalWrapper">
	<div id="column-one">
		<div class="portlet" id="p-logo">
			<a style="background-image: url(http://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Wikimedia_Community_Logo-Toolserver.svg/135px-Wikimedia_Community_Logo-Toolserver.svg.png);" href="http://tools.wikimedia.org/~multichill/" title="Home"></a>
		</div>
		<div class='portlet' id='p-navigation'>
			<h5>Tools</h5>
			<div class='pBody'>
				<ul>
					<li id="n-commons_deletion_checker"><a href="commons_deletion_checker.php" title="commons deletion checker">commons deletion checker</a></li>
					<li id="n-contribs"><a href="contribs.php">Contribution counter</a></li>
					<li id="n-doorverwijspagina"><a href="doorverwijspagina.php">Doorverwijspagina</a></li>
				</ul>
			</div>
		</div>
	</div>
	<div id="column-content">
		<div id="content">
			<div id="bodyContent">
