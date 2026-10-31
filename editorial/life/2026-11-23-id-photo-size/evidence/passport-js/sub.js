$(function(){
    // 상세 검색기 여닫힘
	$(".det_btn .btn").on('click', function(){
		var $detailBox = $('.details_sch .sch_box .box').eq(1);
        var openState = $detailBox.hasClass('on');
        if(openState){
			$(this).removeClass('on').attr('aria-expanded',false);
			$detailBox.removeClass('on').slideUp(500, 'easeInOutCubic');
		} else {
			$(this).addClass('on').attr('aria-expanded',true);
			$detailBox.addClass('on').slideDown(500, 'easeInOutCubic');
		}
	});



	$('#tab li button').click(function(){
		var tab_id = $(this).closest('li').attr('data-tab');
		if($(this).data('is-link')){
			return ;
		}
		
		$('#tab li button').attr('aria-selected',false);
		$(this).attr('aria-selected',true);
		
		
		$('#tab li').closest('li').removeClass('current')
		$('.tab_cont_box').removeClass('current');

		$(this).closest('li').addClass('current');
		$("#"+tab_id).addClass('current');
	});
	
	
	$('#tab li.tab_on').attr('onclick', '');

	$('.scroll_list_area .area > .list > li > a').click(function (){
		if (this.hash !== "") {
			event.preventDefault();
			var hash = this.hash;
			$('html, body').animate({scrollTop: $(hash).offset().top - 200}, 800, function(){
			window.location.hash = hash;
		  });
		} 
    });

	$(".info_list_area > .list > li .title").click(function(){
		$(this).closest('li').addClass('on');
		$(this).closest('li').siblings().removeClass('on');

		$(".info_list_area").find("a").attr('aria-expanded','false');
		$(this).attr('aria-expanded','true');
		
		if($(this).closest('li').hasClass('on')){
			$(this).next().slideDown(1000);
		} else{
			$(this).next().stop().slideUp(1000);
		}
	});

	$('.img_box .exp_btn').on('click', function(){
		$('.info_popup_box').show();
	});

	$('.info_colse_btn').on('click', function(){
		$(this).closest('.info_popup_box').hide();
	});
	
	$('.inadequate_popup_area .btn').on('click', function(){
		$(this).closest('.inadequate_popup_area').hide();
	});

	$('.right_nav .btn').on('click', function(){
		$(this).addClass('on').parents('.item').siblings('.item').find('.btn').removeClass('on');
	});
	$('.safe_slider').slick({
		slidesToShow: 1, 
		slidesToScroll: 1,
		infinite: true, 
		dots: false, 
		speed: 500,
		arrows: true,
		autoplay: false,
		responsive: [
			{
				breakpoint: 768,
				settings: {
					appendArrows: $('.control')	
				}
			}	
		]
		
	});
	
    //사실증명 구문/영문 같은 버튼
	$('.pho_btn_box .list li .btn').on('click', function(){
		$(this).closest('li').addClass('on');
		$(this).closest('li').siblings('li').removeClass('on');
		
		$('.pho_btn_box .list li .btn').attr("aria-pressed",false);
		$(this).attr("aria-pressed",true);
		
		if($(this).closest('li.on').hasClass('kor')){
			$('.img_container .img_box.kor').addClass('on');
			$('.img_container .img_box.en').removeClass('on');
		} else if($(this).closest('li.on').hasClass('en')){
			$('.img_container .img_box.en').addClass('on');
			$('.img_container .img_box.kor').removeClass('on');
		}
	});
	
	//네비게이션 바로가기
	$('.bread_crumbs .depth_menu > .btn').on('click', function(){
		
		var $this =  $(this);
		var $parent = $this.closest('li.depth_menu');
		var $targetList = $this.siblings('.depth_list');
		var isExpaned = $this.attr('aria-expanded') ==='true';
		$this.attr('aria-expanded',!isExpaned);
		$targetList.toggleClass('on').slideToggle();
		$parent.toggleClass('on');
		var $otherMenus = $parent.siblings('li.depth_menu');
		$otherMenus.find('.depth_list').removeClass('on').slideUp();
		$otherMenus.find('> .btn').attr('aria-expanded','false');
		$otherMenus.removeClass('on');
	});
	
	$(window).on('click', function(e){
		if($(e.target).parents('.bread_list').length <= 0){
			$('.bread_crumbs .depth_list').slideUp();
		};
	});
	
	// Define click event on gallery item
    $('.img_container .img_box').click(function(event) {
    // Init empty gallery array
    var container = [];

		item = {
			src: $(this).find('img').attr('src'),
			w: $(this).find('img').data('width'),
			h: $(this).find('img').data('height'),
		};
		container.push(item);

    $('#real_contents').addClass('zoom-mode');
    // Prevent location change
    event.preventDefault();

    // Define object and gallery options
    var $pswp = $('.pswp')[0],
        options = {
            index: $(this).parents('.page-wrapper').index(),
            bgOpacity: 0.85,
            showHideOpacity: true,
        };
    // Initialize PhotoSwipe
    var gallery = new PhotoSwipe($pswp, PhotoSwipeUI_Default, container, options);
    gallery.init();
});

$('.pswp__button--close').on('click', function(){
	$('.pswp__item .pswp__zoom-wrap img').attr('src', '');
});


$(".footnote").click(function(event){         
	event.preventDefault();
	$('html,body').animate({scrollTop:$(this.hash).offset().top - 100}, 500);
});

});