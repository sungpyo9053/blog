<?php
// biggest <table> per published EN post + the heading right before it
$out=[];
foreach(get_posts(["post_type"=>"hunt_en","post_status"=>"publish","numberposts"=>-1]) as $p){
  $c=$p->post_content; if(strpos($c,'hl-glance')!==false) continue;
  if(!preg_match_all('#<table.*?</table>#s',$c,$m,PREG_OFFSET_CAPTURE)) continue;
  $best=null; foreach($m[0] as $t){ $n=substr_count($t[0],'<td'); if(!$best||$n>$best[2]) $best=[$t[0],$t[1],$n]; }
  $pre=substr($c,0,$best[1]); preg_match_all('#<h[23][^>]*>(.*?)</h[23]>#s',$pre,$h);
  $out[]=["id"=>$p->ID,"title"=>$p->post_title,"heading"=>$h[1]?wp_strip_all_tags(end($h[1])):$p->post_title,"table"=>$best[0]];
}
echo json_encode($out);
