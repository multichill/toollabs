			</div>
		</div>
	</div>
	<div id="column-one">
		<div class="portlet" id="p-logo">
			<a style="background-image: url(http://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Wikimedia_Community_Logo-Toolserver.svg/135px-Wikimedia_Community_Logo-Toolserver.svg.png);" href="http://toolserver.org/~multichill/" title="Home"></a>
		</div>
		<div class='portlet' id='p-navigation'>
			<h5>Tools</h5>
			<div class='pBody'>
				<ul>
				        <li id="n-commonscat"><a href="commonscat.php" title="commonscat">Commonscat</a></li>
					<li id="n-commons_deletion_checker"><a href="commons_deletion_checker.php" title="Commons deletion checker">Commons deletion checker</a></li>
					<li id="n-contribs"><a href="contribs.php">Contribution counter</a></li>
					<li id="n-disambig"><a href="disambig.php">Disambiguation page creator</a></li>
					<li id="n-dupes"><a href="dupes.php">Dupe finding tool</a></li>
					<li id="n-gotsource"><a href="gotsource.php">Got source?</a></li>
					<li id="n-nowcommons"><a href="nowcommons.php">Nowcommons the dupes</a></li>
				</ul>
			</div>
		</div>
	</div>
	<div class="visualClear"></div>
	<div id="footer">
		<ul id="f-list">
			<? if ($modified) { ?><li id="lastmod">This page was last modified <? echo $modified ?>.</li><? } ?>
			<li id="about">This tool is written by <a href="http://nl.wikipedia.org/wiki/Gebruiker:Multichill">Multichill</a>.</li>
		</ul>
	</div>
</div>
</body>
</html>
