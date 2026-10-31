var SnsShare = {
	fbShare : function(url) {

		var href = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url);	
		var fbWindow = window.open(href, "facebookShare", "width=640, height=340, scrollbars=yes, resizable=yes");

	},
	
	twShare : function(text, url) {

		var href = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(text) + "&url="+ encodeURIComponent(url);
		var twWindow = window.open(href, "twitterShare", "width=600, height=455, scrollbars=yes, resizable=yes");

	},
	
   storyShare : function (url){
	   
	   var href ="https://story.kakao.com/share?url=" + encodeURIComponent(url);
	   var storyWindow = window.open(href, "kakaoStoryShare", "width=720, height=600, scrollbars=yes, resizable=yes");

   },

   ggShare : function(url) {
		
		var href = "https://plus.google.com/share?url=" +  encodeURIComponent(url);
		var ggWindow = window.open(href, "ggShare",	"width=400, height=450, scrollbars=yes, resizable=yes");

	},

	blogShare : function(text, url) {
		
		var href = "http://share.naver.com/web/shareView.nhn?url=" +  encodeURIComponent(url) + "&title=" + encodeURIComponent(text);
		var blogWindow = window.open(href, "blogShare", "width=400, height=450, scrollbars=yes, resizable=yes");

	}
};