<?php
global $wpdb; $m=json_decode(file_get_contents('/tmp/enfig_media.json'),true); $ids=[]; $bad=0; $skip=0;
foreach($m as $id=>$x){
  $p=get_post($id); $c=$p->post_content; $i=strpos($c,'<h2');
  if(strpos($c,'hl-glance')!==false || $i===false){ $skip++; continue; }
  $fig='<figure class="hl-glance wp-block-image"><img src="'.esc_url($x['url']).'" alt="'.esc_attr($x['alt']).'" width="'.$x['w'][0].'" height="'.$x['w'][1].'" loading="lazy" decoding="async"><figcaption>At a glance: the main measured table from this article. Full details below.</figcaption></figure>'."\n";
  $new=substr($c,0,$i).$fig.substr($c,$i);
  $wpdb->update($wpdb->posts,['post_content'=>$new],['ID'=>$id]); clean_post_cache($id);
  $o=apply_filters('the_content',get_post($id)->post_content);
  preg_match_all('#<script type=.application/ld.json.>(.*?)</script>#s',$o,$j); foreach($j[1] as $s){ if(json_decode($s)===null) $bad++; }
  $ids[]=$id;
}
echo implode(',',$ids)."\n"; echo "done ".count($ids)." skip $skip ld_bad $bad\n";
