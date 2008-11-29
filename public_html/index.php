<?php 
$title = "Index";
$modified = date ("G:i, n F Y", getlastmod());

include("inc/header.php"); ?>
<H2>Multichill's tools</H2>
<P>Page with tools created by Multichill. Most tools are still Beta and are far from finished</P>

<h3><span class="mw-headline"><a href="commonscat.php" title="Commonscat tool">Commonscat tool</a></span></h3>
<P>With this tool you can find links to commons categories for your wikipedia.</P>
<h3><span class="mw-headline"><a href="commons_deletion_checker.php" title="Commons deletion checker">Commons deletion checker</a></span></h3>
<P>With this tool you can find pictures moved from wikipedia to commons which were deleted. Maybe you can save some pictures from oblivion!</P>
<h3><span class="mw-headline"><a href="contribs.php" title="Contribution counter">Contribution counter</a></span></h3>
<P>With this tool you can find on which wikipedia a user is active and the amount of contributions.</P>
<h3><span class="mw-headline"><a href="disambig.php" title="Disambiguation page creator">Disambiguation page creator</a></span></h3>
<P>With this tool you can create disambiguation pages. At the moment it only works at the nl wikipedia.</P>
<h3><span class="mw-headline"><a href="dupes.php" title="Dupe finding tool">Dupe finding tool</a></span></h3>
<P>With this tool you can find images at your wiki which are uploaded more than once.</P>
<h3><span class="mw-headline"><a href="gotsource.php" title="Got source?">Got source?</a></span></h3>
<P>With this tool you can find the source of an image.</P>
<h3><span class="mw-headline"><a href="nowcommons.php" title="Nowcommons all the dupes">Nowcommons all the dupes</a></span></h3>
<P>With this tool you can find images at your wikipedia which are already present at commons. </P>
<?php include("inc/footer.php"); ?>
