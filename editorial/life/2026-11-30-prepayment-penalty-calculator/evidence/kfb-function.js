//공통 함수 ------------------------------------------------------------------------------------------------------

if(location.protocol == "http:")
{
	//jlogos location.href = location.href.replace("http://","https://");
}


/*
if(location.hostname != "www.kfb.or.kr")
{
	location.href = location.href.replace(location.hostname,"www.kfb.or.kr");
}
*/

//사이트 로딩시 실행되는 함수들--------
$(document).ready(function() {

	//브라우저 사이즈 변경시 다시 로딩
	$(window).resize(function (){
		//location.reload();
	})

//상단 주메뉴---------------------
	var gnbHr = $("div[id='TopMenu']");

	gnbHr.find('>ul>li').mouseover(function(){

		//주메뉴 마우스오버시 인덱스
		MainMenu_index = $(this).index();

		//메뉴에 mouseover 시 모든 메뉴 mouseout 이미지로 변경
		for(i=0;i<$("img[name='MainMenuImg']").length;i++) {
			$("img[name='MainMenuImg']").eq(i).attr('src','/images/common/header_menu0'+(i+1)+'.png');
		}
		//선택한 메뉴 mouseover 이미지로 변경
		$("img[name='MainMenuImg']").eq($(this).index()).attr('src','/images/common/header_menu0'+($(this).index() + 1)+'ov.png');

		//모든 메뉴 숨기기
		$($("div[name='topsubMenu']")).not("div[name='topsubMenu']:eq("+MainMenu_index+")").hide();
		//선택한 메뉴 보이기
		$("div[name='topsubMenu']").eq(MainMenu_index).show('slide', {direction : 'up'}, 200);



	})

	gnbHr.find('>ul>li>h2>a').focus(function(){
		$(this).mouseover();
	})

	.end()

	//상단 메뉴 위치에서 이탈시 메뉴 숨기기
	$("div[id='TopMenu']").mouseleave(function(){

			for(i=0;i<$("img[name='MainMenuImg']").length;i++) {
				$("img[name='MainMenuImg']").eq(i).attr('src','/images/common/header_menu0'+(i+1)+'.png');
			}
			$($("div[name='topsubMenu']")).hide('slide', {direction : 'up'}, 150);

	});

	$("a[id='SiteMenuBtn']").focus(function(){
		for(i=0;i<$("img[name='MainMenuImg']").length;i++) {
				$("img[name='MainMenuImg']").eq(i).attr('src','/images/common/header_menu0'+(i+1)+'.png');
			}
		$($("div[name='topsubMenu']")).hide('slide', {direction : 'up'}, 150);
	})



	//상단 주메뉴---------------------


	//서브 탭메뉴 열기----------------------------
	$("#SubTabMenuShow").bind("click", function() {
	//$("#SubTabMenuShow").bind("mouseover", function() {
		$($("ul[id='SubTabMenu']")).toggle('slide', {direction : 'up'}, 150);
	});

	$("#SubTabMenu").mouseleave(function(){
		$($("ul[id='SubTabMenu']")).toggle('slide', {direction : 'up'}, 150);
	});
	//서브 탭메뉴 열기---------------------------





	//하단 바로가기
	$('#FootLink01').click(function(){
		$($("div[id='Link01']")).toggle('slide', {direction : 'down'}, 150);
		$($("div[id='Link02']")).hide('slide', {direction : 'down'}, 150);
	});

	$('#FootLink02').click(function(){
		$($("div[id='Link01']")).hide('slide', {direction : 'down'}, 150);
		$($("div[id='Link02']")).toggle('slide', {direction : 'down'}, 150);
	});

	$('#linkArea').mouseleave(function(){
		$($("div[id='Link01']")).hide('slide', {direction : 'down'}, 150);
		$($("div[id='Link02']")).hide('slide', {direction : 'down'}, 150);
	});
	//하단 바로가기



	//즐겨찾기 메뉴
	var versionType = BrowserVersionCheck();

	if(versionType=="IE") {
		$("#Favorite").show();
	}


	//메인 금리/수수료가 궁금해요, 소비자 정보 제공 메뉴가 궁금해요--------------------------------------------------------------

	var gnbGoods = $("div[id='MainGoods']");

	//gnbGoods.find('>li').mouseover(function(){
	gnbGoods.find($("li[name='MainGoodsTab']")).mouseover(function(){

		gnbGoods_index = $(this).index();

		for(i=0;i<$("img[name='MainGoodsImg']").length;i++) {
			$("img[name='MainGoodsImg']").eq(i).attr('src','/images/main/mzone_tab0'+(i+1)+'.png');
		}
		$("img[name='MainGoodsImg']").eq($(this).index()).attr('src','/images/main/mzone_tab0'+($(this).index() + 1)+'ov.png');

		$($("ul[name='MainGoodsList']")).not("ul[name='MainGoodsList']:eq($(this).index())").hide();
		$("ul[name='MainGoodsList']").eq($(this).index()).show();

	})

	$("li[name='MainGoodsTab']").find('>a').focus(function(){
		$(this).mouseover();
	})

	//메인 금리/수수료가 궁금해요, 소비자 정보 제공 메뉴가 궁금해요--------------------------------------------------------------








});
//사이트 로딩시 실행되는 함수들--------

function FP_LeaseSearch222() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var INTEREST_TYPE_length = $("input[name='INTEREST_TYPE']:checked").length;
	
	if(INTEREST_TYPE_length<1) {
		alert("금리방식을 선택하세요.");
		return;
	}

	var INTEREST_TYPE = $("input[name='INTEREST_TYPE']:checked").val();


	var REPAY_TYPE_length = $("input[name='REPAY_TYPE']:checked").length;
	
	if(REPAY_TYPE_length<1) {
		alert("상환방식을 선택하세요.");
		return;
	}

	var REPAY_TYPE = $("input[name='REPAY_TYPE']:checked").val();


	var LoanMoney = $("#LoanMoney").val();
	LoanMoney = LoanMoney.replace(/,/gi,"");

	if(LoanMoney=="" || LoanMoney<1000) {
		alert("대출금액은 10,000원 이상 입력하세요.");
		return;
	}

	if(!IsNumber(LoanMoney)) {
		alert("대출금액은 숫자만 입력하세요.");
		return;
	}

	var LoanYear = $("#LoanYear").val();

	if(LoanYear=="" || LoanYear<1 || LoanYear>30) {
		alert("대출기간은 1년 이상 30년 이하로 입력하세요.");
		return;
	}

	if(!IsNumber(LoanYear)) {
		alert("대출기간은 숫자만 입력하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/compare/loan_search_222_search_result.php",
	{ 'INTEREST_TYPE': INTEREST_TYPE,
		'BankValue': $("input[id='BankValue']").val(),
		'REPAY_TYPE': REPAY_TYPE,
		'LoanMoney': LoanMoney,
		'LoanYear': LoanYear
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function FP_LeaseSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var INTEREST_TYPE_length = $("input[name='INTEREST_TYPE']:checked").length;
	var INTEREST_TYPE_value = $("input[name='INTEREST_TYPE']:checked").val();
	if(INTEREST_TYPE_length<1) {
		INTEREST_TYPE_value = $("#INTEREST_TYPE option:selected").val();
		if(INTEREST_TYPE_value=="") {
			alert("금리방식을 선택하세요.");
			return;
		}
	}
	//var INTEREST_TYPE = $("input[name='INTEREST_TYPE']:checked").val();
	var INTEREST_TYPE = INTEREST_TYPE_value;


	var REPAY_TYPE_length = $("input[name='REPAY_TYPE']:checked").length;
	var REPAY_TYPE_value = $("input[name='REPAY_TYPE']:checked").val();
	if(REPAY_TYPE_length<1) {
		REPAY_TYPE_value = $("#REPAY_TYPE option:selected").val();
		if(REPAY_TYPE_value=="") {
			alert("상환방식을 선택하세요.");
			return;
		}
	}
	//var REPAY_TYPE = $("input[name='REPAY_TYPE']:checked").val();
	var REPAY_TYPE = REPAY_TYPE_value;


	var LoanMoney = $("#LoanMoney").val();
	LoanMoney = LoanMoney.replace(/,/gi,"");

	if(LoanMoney=="" || LoanMoney<1000) {
		alert("대출금액은 10,000원 이상 입력하세요.");
		return;
	}

	if(!IsNumber(LoanMoney)) {
		alert("대출금액은 숫자만 입력하세요.");
		return;
	}

	var LoanYear = $("#LoanYear").val();

	if(LoanYear=="" || LoanYear<1 || LoanYear>30) {
		alert("대출기간은 1년 이상 30년 이하로 입력하세요.");
		return;
	}

	if(!IsNumber(LoanYear)) {
		alert("대출기간은 숫자만 입력하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_2_search_result.php",
	{ 'INTEREST_TYPE': INTEREST_TYPE,
		'BankValue': $("input[id='BankValue']").val(),
		'REPAY_TYPE': REPAY_TYPE,
		'LoanMoney': LoanMoney,
		'LoanYear': LoanYear,
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			//console.log(data);
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

//전세자금대출 상품명 검색
function FP_LeaseProdSearch() {

	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var INTEREST_TYPE_length = $("input[name='INTEREST_TYPE']:checked").length;
	var INTEREST_TYPE_value = $("input[name='INTEREST_TYPE']:checked").val();
	if(INTEREST_TYPE_length<1) {
		INTEREST_TYPE_value = $("#INTEREST_TYPE option:selected").val();
		if(INTEREST_TYPE_value=="") {
			INTEREST_TYPE_value = "All";
			//alert("금리방식을 선택하세요.");
			//return;
		}
	}
	//var INTEREST_TYPE = $("input[name='INTEREST_TYPE']:checked").val();
	var INTEREST_TYPE = INTEREST_TYPE_value;


	var REPAY_TYPE_length = $("input[name='REPAY_TYPE']:checked").length;
	var REPAY_TYPE_value = $("input[name='REPAY_TYPE']:checked").val();
	if(REPAY_TYPE_length<1) {
		REPAY_TYPE_value = $("#REPAY_TYPE option:selected").val();
		if(REPAY_TYPE_value=="") {
			REPAY_TYPE_value = "All";
			//alert("상환방식을 선택하세요.");
			//return;
		}
	}
	//var REPAY_TYPE = $("input[name='REPAY_TYPE']:checked").val();
	var REPAY_TYPE = REPAY_TYPE_value;

	//금리방식, 상환방식, 대출금액, 대출기간
	//var INTEREST_TYPE = "All";
	//var REPAY_TYPE = "All";
	
	//대출금액 확인
	var LoanMoney = $("input[id='LoanMoney']").val();
	LoanMoney = LoanMoney.replace(/,/gi,"");
	if (LoanMoney == "") {
		LoanMoney = 10000;
		$("input[id='LoanMoney']").val(LoanMoney);
	}
	
	//대출기간 확인
	var LoanYear = $("input[id='LoanYear']").val();
	if (LoanYear == "") {
		LoanYear = 1;
		$("input[id='LoanYear']").val(LoanYear);
	}

	//상품명
	var productName = $("input[id='productName']").val();
	
	if(productName == "") {
		alert("상품명을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	} else if (productName.length < 2) {
		alert("상품명은 최소 2자리 이상을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	}
	productName = encodeURIComponent(productName);

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/compare/loan_search_2_search_result.php",
	{ 'productName': productName,
	  'searchType': 'productName',
		'INTEREST_TYPE': INTEREST_TYPE,
		'BankValue': $("input[id='BankValue']").val(),
		'REPAY_TYPE': REPAY_TYPE,
		'LoanMoney': LoanMoney,
		'LoanYear': LoanYear 
	},function(data,status){
		setTimeout(function(){
			//console.log(data);
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}

function FP_LeaseSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_LeaseSearch();
	$("input[id='SortType']").val("");
}

//전세자금대출 상품명 검색 정렬
function FP_LeaseProdSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_LeaseProdSearch();
	$("input[id='SortType']").val("");
}

function FP_CreditSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	//alert(order_str);
	FP_CreditSearch();
	$("input[id='SortType']").val("");
}

function FP_CreditSearch() {
	
	 
	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var ProductType_length = $("input[name='ProductType']:checked").length;
	var ProductType_value = $("input[name='ProductType']:checked").val();
	if(ProductType_length<1) {
		ProductType_value = $("#ProductType option:selected").val();
		if(ProductType_value=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}
	var ProductType = ProductType_value;

	
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();
	
	var BankValue = $("input[id='BankValue']").val();
	
	$.post("/compare/loan_search_4_search_result.php",
	{ 'ProductType': ProductType,	
		'BankValue': BankValue,
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

 function CreditExplToggle(i) {

	$("tr[id='Goods_Text_TR2']:eq("+i+")").toggle();
	$("tr[id='Goods_Text_TR3']:eq("+i+")").toggle();
	$("tr[id='Goods_Text_TR4']:eq("+i+")").toggle();
	$("tr[id='Goods_Text_TR5']:eq("+i+")").toggle();
	$("tr[id='Goods_Text_TR6']:eq("+i+")").toggle();

	if($("tr[id='Goods_Text_TR2']:eq("+i+")").css("display") == "none" ) {
		$("td[id='OpenBtn']:eq("+i+")").html('<span class="btnTableIn_view01"><a href="Javascript:CreditExplToggle('+i+')">보기</a></span>');
	}else{
		$("td[id='OpenBtn']:eq("+i+")").html('<span class="btnTableIn_close01"><a href="Javascript:CreditExplToggle('+i+')">닫기</a></span>');
	}

}


//주택담보 대출
function FP_MortgageSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType_length = $("input[name='InterestType']:checked").length;
	var InterestType_value = $("input[name='InterestType']:checked").val();
	if(InterestType_length<1) {
		InterestType_value = $("#InterestType option:selected").val();
		if(InterestType_value=="") {
			alert("주택종류를 선택하세요.");
			return;
		}
	}
	//var InterestType = $("input[name='InterestType']:checked").val();
	var InterestType = InterestType_value;

	var INTEREST_TYPE_length = $("input[name='INTEREST_TYPE']:checked").length;
	var INTEREST_TYPE_value = $("input[name='INTEREST_TYPE']:checked").val();
	if(INTEREST_TYPE_length<1) {
		INTEREST_TYPE_value = $("#INTEREST_TYPE option:selected").val();
		if(INTEREST_TYPE_value=="") {
			alert("금리방식을 선택하세요.");
			return;
		}
	}
	//var INTEREST_TYPE = $("input[name='INTEREST_TYPE']:checked").val();
	var INTEREST_TYPE = INTEREST_TYPE_value;


	var REPAY_TYPE_length = $("input[name='REPAY_TYPE']:checked").length;
	var REPAY_TYPE_value = $("input[name='REPAY_TYPE']:checked").val();
	if(REPAY_TYPE_length<1) {
		REPAY_TYPE_value = $("#REPAY_TYPE option:selected").val();
		if(REPAY_TYPE_value=="") {
			alert("상환방식을 선택하세요.");
			return;
		}
	}
	//var REPAY_TYPE = $("input[name='REPAY_TYPE']:checked").val();
	var REPAY_TYPE = REPAY_TYPE_value;

	var LoanMoney = $("#LoanMoney").val();
	LoanMoney = LoanMoney.replace(/,/gi,"");

	if(LoanMoney=="" || LoanMoney<1000) {
		alert("대출금액은 10,000원 이상 입력하세요.");
		return;
	}

	if(!IsNumber(LoanMoney)) {
		alert("대출금액은 숫자만 입력하세요.");
		return;
	}

	var LoanYear = $("#LoanYear").val();

	if(LoanYear=="" || LoanYear<1 || LoanYear>30) {
		alert("대출기간은 1년 이상 30년 이하로 입력하세요.");
		return;
	}

	if(!IsNumber(LoanYear)) {
		alert("대출기간은 숫자만 입력하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_search_result.php",
	{ 'INTEREST_TYPE': INTEREST_TYPE,
		'BankValue': $("input[id='BankValue']").val(),
		'REPAY_TYPE': REPAY_TYPE,
		'LoanMoney': LoanMoney,
		'LoanYear': LoanYear,
		'InterestType': InterestType,
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

//주택담보대출 상품검색
function FP_MortgageProdSearch() {

	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType_length = $("input[name='InterestType']:checked").length;
	var InterestType = $("input[name='InterestType']:checked").val();
	if(InterestType_length<1) {
		InterestType = $("#InterestType option:selected").val();
		if (InterestType == "") {
			alert("주택종류를 선택하세요.");
			return;
		}
	}

	//금리방식
	var INTEREST_TYPE_length = $("input[name='INTEREST_TYPE']:checked").length;
	var INTEREST_TYPE_value = $("input[name='INTEREST_TYPE']:checked").val();
	if(INTEREST_TYPE_length<1) {
		INTEREST_TYPE_value = $("#INTEREST_TYPE option:selected").val();
		if(INTEREST_TYPE_value=="") {
			INTEREST_TYPE_value = "All";
			//$("#INTEREST_TYPE_0").prop("checked", true);
			//$("#INTEREST_TYPE").val('All').prop("selected", true);
			//return;
		}
	}
	//var INTEREST_TYPE = $("input[name='INTEREST_TYPE']:checked").val();
	var INTEREST_TYPE = INTEREST_TYPE_value;
	
	//상환방식
	var REPAY_TYPE_length = $("input[name='REPAY_TYPE']:checked").length;
	var REPAY_TYPE_value = $("input[name='REPAY_TYPE']:checked").val();
	if(REPAY_TYPE_length<1) {
		REPAY_TYPE_value = $("#REPAY_TYPE option:selected").val();
		if(REPAY_TYPE_value=="") {
			//$("#REPAY_TYPE_0").prop("checked", true);
			//$("#REPAY_TYPE").val('All').prop("selected", true);
			REPAY_TYPE_value = "All";
		}
	}
	var REPAY_TYPE = REPAY_TYPE_value;

	//var INTEREST_TYPE = "All";
	//var REPAY_TYPE = "All";
	
	//대출금액 확인
	var LoanMoney = $("input[id='LoanMoney']").val();
	LoanMoney = LoanMoney.replace(/,/gi,"");
	if (LoanMoney == "") {
		LoanMoney = 10000;
		$("input[id='LoanMoney']").val(LoanMoney);
	}
	
	//대출기간 확인
	var LoanYear = $("input[id='LoanYear']").val();
	if (LoanYear == "") {
		LoanYear = 1;
		$("input[id='LoanYear']").val(LoanYear);
	}
	
	var productName = $("input[id='productName']").val();
	if(productName == "") {
		alert("상품명을 입력하세요.");
		$("input[id='productName']").focus();
		return;
		
	} else if (productName.length < 2) {
		alert("상품명은 최소 2자리 이상을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	}
	productName = encodeURIComponent(productName);
	
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_search_result.php",
	{ 'productName': productName,
	   'searchType': 'productName',
		'INTEREST_TYPE': INTEREST_TYPE,
		'BankValue': $("input[id='BankValue']").val(),
		'REPAY_TYPE': REPAY_TYPE,
		'LoanMoney': LoanMoney,
		'LoanYear': LoanYear,
		'InterestType': InterestType,
		'SortType': SortType 

	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}

function FP_MortgageSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_MortgageSearch();
	$("input[id='SortType']").val("");
}

//주택담보 대출 상품명 검색 정렬
function FP_MortgageProdSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_MortgageProdSearch();
	$("input[id='SortType']").val("");
}

function FP_BankSelectChecked() {

	//radio 길이
	radio_length = $("input[name='BankSelect']").length;

	if($("input[id='AllCheck']:checked").length == 0){
		
		for(var i=1; i<=radio_length; i++){
			$('input[id="Bankselect'+i+'"]').prop('checked',false);
		}

	}else{

		for(var i=1; i<=radio_length; i++){
			$('input[id="Bankselect'+i+'"]').prop('checked',true);
		}

	}

}

function FP_DepositSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType_length = $("input[name='InterestType']:checked").length;
	
	if(InterestType_length<1) {
		alert("이자 계산방식을 선택하세요.");
		return;
	}

var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var InterestType = $("input[name='InterestType']:checked").val();
	var BankValue = $("input[id='BankValue']").val();
	var InterestMonth = $("#InterestMonth option:selected").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();

	$.post("/compare/receiving_deposit_3_search_result.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'InterestMonth': InterestMonth,
		'OrderByType': OrderByType,
		'JOIN_METHOD': JOIN_METHOD,  
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 770 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}
function FP_DepositSearch_new() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType_length = $("input[name='InterestType']:checked").length;
	
	if(InterestType_length<1) {
		alert("이자 계산방식을 선택하세요.");
		return;
	}

var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var InterestType = $("input[name='InterestType']:checked").val();
	var BankValue = $("input[id='BankValue']").val();
	var InterestMonth = $("#InterestMonth option:selected").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
	var EXPIRATION = $("input[name='EXPIRATION']:checked").val();

	$.post("/compare/receiving_deposit_3_search_result_new.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'InterestMonth': InterestMonth,
		'OrderByType': OrderByType,
		'JOIN_METHOD': JOIN_METHOD,  
		'EXPIRATION': EXPIRATION, 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 770 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_DepositSearch_sort2() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType_length = $("input[name='InterestType']:checked").length;
	var InterestType_value = $("input[name='InterestType']:checked").val();
	if(InterestType_length<1) {
		InterestType_value = $("#InterestType option:selected").val();
		if(InterestType_value=="") {
			alert("이자 계산방식을 선택하세요.");
			return;
		}
	}
	var InterestType = InterestType_value;

	//만기
	var EXPIRATION_length = $("input[name='EXPIRATION']:checked").length;
	var EXPIRATION_value = $("input[name='EXPIRATION']:checked").val();
	if(EXPIRATION_length < 1) {
		EXPIRATION_value = $("#EXPIRATION option:selected").val();
		if(EXPIRATION_value=="") {
			alert("가입기간을 선택하세요.");
			return;
		}
	}
	var EXPIRATION = EXPIRATION_value;
	
	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	var JOIN_METHOD_value = $("input[name='JOIN_METHOD']:checked").val();
	if(JOIN_METHOD_length < 1) {
		JOIN_METHOD_value = $("#JOIN_METHOD option:selected").val();
		if(JOIN_METHOD_value=="") {
			alert("가입방식을 선택하세요.");
			return;
		}
	}
	var JOIN_METHOD = JOIN_METHOD_value;
	//console.log("join_method = " + JOIN_METHOD);

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	//var InterestType = $("input[name='InterestType']:checked").val();
	var BankValue = $("input[id='BankValue']").val();
	var InterestMonth = $("#InterestMonth option:selected").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	//var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
	//var EXPIRATION = $("input[name='EXPIRATION']:checked").val();
	//console.log("join_method2 = " + JOIN_METHOD);

	$.post("/compare/receiving_deposit_3_search_result_new2.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'InterestMonth': InterestMonth,
		'OrderByType': OrderByType,
		'JOIN_METHOD': JOIN_METHOD,  
		'EXPIRATION': EXPIRATION, 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 770 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}


function FP_DepositSearch2() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType_length = $("input[name='InterestType']:checked").length;
	
	if(InterestType_length<1) {
		alert("이자 계산방식을 선택하세요.");
		return;
	}

var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var InterestType = $("input[name='InterestType']:checked").val();
	var BankValue = $("input[id='BankValue']").val();
	var InterestMonth = $("#InterestMonth option:selected").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();

	$.post("/compare/receiving_deposit_3_search_result2.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'InterestMonth': InterestMonth,
		'OrderByType': OrderByType,
		'JOIN_METHOD': JOIN_METHOD,  
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 770 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}


function FP_DepositSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_DepositSearch();
	$("input[id='SortType']").val("");
}

function FP_DepositSearch_Sort_new(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_DepositSearch_sort2();
	$("input[id='SortType']").val("");
}


function FP_ReceivingSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);


	var SaveMoney = $("#SaveMoney").val();
	SaveMoney = SaveMoney.replace(/,/gi,"");

	if(SaveMoney=="" || SaveMoney<10000) {
		alert("저축금액을 10,000원 이상 입력하세요.");
		return;
	}

	if(!IsNumber(SaveMoney)) {
		alert("저축금액은 숫자만 입력하세요.");
		return;
	}

	var InterestMonth_length = $("input[name='InterestMonth']:checked").length;
	var InterestMonth_value = $("input[name='InterestMonth']:checked").val();
	if(InterestMonth_length<1) {
		InterestMonth_value = $("#InterestMonth option:selected").val();
		if(InterestMonth_value=="") {
			alert("저축 예정기간을 선택하세요.");
			return;
		}
	}
	var InterestMonth = InterestMonth_value;

	var JOIN_LIMIT_CODE_length = $("input[name='JOIN_LIMIT_CODE']:checked").length;
	var JOIN_LIMIT_CODE_value = $("input[name='JOIN_LIMIT_CODE']:checked").val();
	if(JOIN_LIMIT_CODE_length<1) {
		JOIN_LIMIT_CODE_value = $("#JOIN_LIMIT_CODE option:selected").val();
		if(JOIN_LIMIT_CODE_value=="") {
			alert("가입대상을 선택하세요.");
			return;
		}
	}
	var JOIN_LIMIT_CODE = JOIN_LIMIT_CODE_value;

	var InterestType_length = $("input[name='InterestType']:checked").length;
	var InterestType_value = $("input[name='InterestType']:checked").val();
	if(InterestType_length<1) {
		InterestType_value = $("#InterestType option:selected").val();
		if(InterestType_value=="-1") {		//선택값 -1
			alert("이자 계산방식을 선택하세요.");
			return;
		}
	}
	var InterestType = InterestType_value;

	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	var JOIN_METHOD_value = $("input[name='JOIN_METHOD']:checked").val();
	if(JOIN_METHOD_length<1) {
		JOIN_METHOD_value = $("#JOIN_METHOD option:selected").val();
		if(JOIN_METHOD_value == "-1") {			//선택값 -1
			alert("가입방식을 선택하세요.");
			return;
		}
	}
	var JOIN_METHOD = JOIN_METHOD_value;


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	
	var BankValue = $("input[id='BankValue']").val();
	//var InterestMonth = $("input[name='InterestMonth']:checked").val();
	//var JOIN_LIMIT_CODE = $("input[name='JOIN_LIMIT_CODE']:checked").val();
	//var InterestType = $("input[name='InterestType']:checked").val();
	//var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
	var SortType = $("input[id='SortType']").val();


	$.post("/compare/receiving_neosearch_search_result.php",
	{ 'BankValue': BankValue,
		'SaveMoney': SaveMoney,
		'InterestMonth': InterestMonth,
		'JOIN_LIMIT_CODE': JOIN_LIMIT_CODE,
		'InterestType': InterestType,
		'JOIN_METHOD': JOIN_METHOD, 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 570 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}

//정기예금 상품명 검색
function FP_ReceivingProdSearch() {

	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var SaveMoney = $("#SaveMoney").val();
	SaveMoney = SaveMoney.replace(/,/gi,"");

	if(SaveMoney=="" || SaveMoney<10000) {
		alert("저축금액을 10,000원 이상 입력하세요.");
		return;
	}

	if(!IsNumber(SaveMoney)) {
		alert("저축금액은 숫자만 입력하세요.");
		return;
	}

	var InterestMonth_length = $("input[name='InterestMonth']:checked").length;
	var InterestMonth_value = $("input[name='InterestMonth']:checked").val();
	if(InterestMonth_length<1) {
		InterestMonth_value = $("#InterestMonth option:selected").val();
		if(InterestMonth_value=="") {
			alert("저축 예정기간을 선택하세요.");
			return;
		}
	}
	var InterestMonth = InterestMonth_value;
	
	
	var JOIN_LIMIT_CODE_length = $("input[name='JOIN_LIMIT_CODE']:checked").length;
	var JOIN_LIMIT_CODE_value = $("input[name='JOIN_LIMIT_CODE']:checked").val();
	if(JOIN_LIMIT_CODE_length<1) {
		JOIN_LIMIT_CODE_value = $("#JOIN_LIMIT_CODE option:selected").val();
		if(JOIN_LIMIT_CODE_value=="") {
			JOIN_LIMIT_CODE_value = "1";
			//alert("가입대상을 선택하세요.");
			//return;
		}
	}
	var JOIN_LIMIT_CODE = JOIN_LIMIT_CODE_value;

	var InterestType_length = $("input[name='InterestType']:checked").length;
	var InterestType_value = $("input[name='InterestType']:checked").val();
	if(InterestType_length<1) {
		InterestType_value = $("#InterestType option:selected").val();
		if(InterestType_value=="-1") {		//선택값 -1
			InterestType_value = "";
			//alert("이자 계산방식을 선택하세요.");
			//return;
		}
	}
	var InterestType = InterestType_value;

	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	var JOIN_METHOD_value = $("input[name='JOIN_METHOD']:checked").val();
	if(JOIN_METHOD_length<1) {
		JOIN_METHOD_value = $("#JOIN_METHOD option:selected").val();
		if(JOIN_METHOD_value == "-1") {			//선택값 -1
			JOIN_METHOD_value = "";
			//alert("가입방식을 선택하세요.");
			//return;
		}
	}
	var JOIN_METHOD = JOIN_METHOD_value

	//저축금액 (최소)
	//var SaveMoney = 10000;

	//저축예정기간
	//var InterestMonth = 12;

	//가입대상 (제한없음)
	//var JOIN_LIMIT_CODE = "1";

	//이자계산방식 (전체)
	//var InterestType = "";

	//가입방식 (전체)
	//var JOIN_METHOD = "";

	//상품명
	var productName = $("input[id='productName']").val();
	
	if(productName == "") {
		alert("상품명을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	} else if (productName.length < 2) {
		alert("상품명은 최소 2자리 이상을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	}
	productName = encodeURIComponent(productName);

	var BankValue = $("input[id='BankValue']").val();
	var SortType = $("input[id='SortType']").val();
	
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/compare/receiving_neosearch_search_result.php",
	{ 'productName': productName,
	  'searchType': 'productName',
		'BankValue': BankValue,
		'SaveMoney': SaveMoney,
		'InterestMonth': InterestMonth,
		'JOIN_LIMIT_CODE': JOIN_LIMIT_CODE,
		'InterestType': InterestType,
		'JOIN_METHOD': JOIN_METHOD, 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 570 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}


function FP_ReceivingSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_ReceivingSearch();
	$("input[id='SortType']").val("");
}

//정기예금 상품명검색 정렬
function FP_ReceivingProdSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_ReceivingProdSearch();
	$("input[id='SortType']").val("");
}


function FP_ReceivingSearch2_InterestType1() {
	
	if($("input[name='InterestType1']:checked").val()=="All" || $("input[name='InterestType1']:checked").val()=="1") {
		$("#MonthSaveMoney").prop("disabled",false);
	}
	
	if($("input[name='InterestType1']:checked").val()=="2") {
		$("#MonthSaveMoney").val("");
		$("#TotalSaveMoney").val("");
		$("#MonthSaveMoney").prop("disabled",true);
	}
	
}

function FP_ReceivingSearch2() {

	var Bankvalue2 = "";
	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType1_length = $("input[name='InterestType1']:checked").length;
	var InterestType1_value = $("input[name='InterestType1']:checked").val();	
	if(InterestType1_length<1) {
		InterestType1_value = $("#InterestType1_m option:selected").val();
		if(InterestType1_value=="") {
			alert("적립방식을 선택하세요.");
			return;
		}
	}
	var InterestType1 = InterestType1_value;
	
	var InterestMonth_length = $("input[name='InterestMonth']:checked").length;
	var InterestMonth_value = $("input[name='InterestMonth']:checked").val();	
	if(InterestMonth_length<1) {
		InterestMonth_value = $("#InterestMonth option:selected").val();
		if(InterestMonth_value=="") {
			alert("저축 예정기간을 선택하세요.");
			return;
		}
	}
	var InterestMonth = InterestMonth_value;

	
	//if($("input[name='InterestType1']:checked").val()=="All" || $("input[name='InterestType1']:checked").val()=="1") {
	if(InterestType1=="All" || InterestType1=="1") {		

		var MonthSaveMoney = $("#MonthSaveMoney").val();
		MonthSaveMoney = MonthSaveMoney.replace(/,/gi,"");

		if(MonthSaveMoney=="" || MonthSaveMoney<1000) {
			alert("월 저축금액을 1,000원 이상 입력하세요.");
			return;
		}

		if(!IsNumber(MonthSaveMoney)) {
			alert("월 저축금액은 숫자만 입력하세요.");
			return;
		}
		
		var TotalSaveMoney = MonthSaveMoney * $("input[name='InterestMonth']:checked").val();
		$("#TotalSaveMoney").val(FormatNumber2(TotalSaveMoney));
		/*
		var TotalSaveMoney = $("#TotalSaveMoney").val();

		if(TotalSaveMoney=="" || TotalSaveMoney<1000) {
			alert("총 저축금액을 10,000원 이상 입력하세요.");
			return;
		}

		if(!IsNumber(TotalSaveMoney)) {
			alert("총 저축금액은 숫자만 입력하세요.");
			return;
		}
		*/
		
	}

	var JOIN_LIMIT_CODE_length = $("input[name='JOIN_LIMIT_CODE']:checked").length;
	var JOIN_LIMIT_CODE_value = $("input[name='JOIN_LIMIT_CODE']:checked").val();
	if(JOIN_LIMIT_CODE_length<1) {
		JOIN_LIMIT_CODE_value = $("#JOIN_LIMIT_CODE option:selected").val();
		if (JOIN_LIMIT_CODE_value == "") {
			alert("가입대상을 선택하세요.");
			return;
		}
	}
	var JOIN_LIMIT_CODE = JOIN_LIMIT_CODE_value;


	var InterestType_length = $("input[name='InterestType']:checked").length;
	var InterestType_value = $("input[name='InterestType']:checked").val();
	if(InterestType_length<1) {
		InterestType_value = $("#InterestType option:selected").val();
		if (InterestType_value == "") {
			alert("이자 계산방식을 선택하세요.");
			return;
		}
	}
	var InterestType = InterestType_value;
	

	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	var JOIN_METHOD_value = $("input[name='JOIN_METHOD']:checked").val();
	if(JOIN_METHOD_length<1) {
		JOIN_METHOD_value = $("#JOIN_METHOD option:selected").val();
		if (JOIN_METHOD_value == "-1") {
			alert("가입방식을 선택하세요.");
			return;
		}
	}
	var JOIN_METHOD = JOIN_METHOD_value;


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	
	var BankValue = $("input[id='BankValue']").val();
	//var InterestType1 = $("input[name='InterestType1']:checked").val();
	//var InterestMonth = $("input[name='InterestMonth']:checked").val();
	//var JOIN_LIMIT_CODE = $("input[name='JOIN_LIMIT_CODE']:checked").val();
	//var InterestType = $("input[name='InterestType']:checked").val();
	//var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
	var SortType = $("input[id='SortType']").val();


	$.post("/compare/receiving_neosearch_2_search_result.php",
	{ 'BankValue': BankValue,
		'InterestType1': InterestType1,
		'MonthSaveMoney': MonthSaveMoney,
		'InterestMonth': InterestMonth,
		'TotalSaveMoney': TotalSaveMoney,
		'JOIN_LIMIT_CODE': JOIN_LIMIT_CODE,
		'InterestType': InterestType,
		'JOIN_METHOD': JOIN_METHOD, 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 570 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

//맞춤상품검색 (적금) 상품검색
function FP_ReceivingProdSearch2() {
	
	var Bankvalue2 = "";
	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);
	
	var InterestType1_length = $("input[name='InterestType1']:checked").length;
	var InterestType1_value = $("input[name='InterestType1']:checked").val();	
	if(InterestType1_length<1) {
		InterestType1_value = $("#InterestType1_m option:selected").val();
		if(InterestType1_value=="") {
			InterestType1_value = "All";
			//alert("적립방식을 선택하세요.");
			//return;
		}
	}
	var InterestType1 = InterestType1_value;

	//적립방식 (전체)
	//var InterestType1 = "All";

	//월 저축금액
	if(InterestType1=="All" || InterestType1=="1") {		

		var MonthSaveMoney = $("#MonthSaveMoney").val();
		MonthSaveMoney = MonthSaveMoney.replace(/,/gi,"");

		if(MonthSaveMoney=="" || MonthSaveMoney<1000) {
			alert("월 저축금액을 1,000원 이상 입력하세요.");
			return;
		}

		if(!IsNumber(MonthSaveMoney)) {
			alert("월 저축금액은 숫자만 입력하세요.");
			return;
		}
		
		var TotalSaveMoney = MonthSaveMoney * $("input[name='InterestMonth']:checked").val();
		$("#TotalSaveMoney").val(FormatNumber2(TotalSaveMoney));
	}

	//저축예정기간
	var InterestMonth_length = $("input[name='InterestMonth']:checked").length;
	var InterestMonth = $("input[name='InterestMonth']:checked").val();
	if(InterestMonth_length<1) {
		InterestMonth =  $("#InterestMonth option:selected").val();
		if (InterestMonth == "") {
			alert("저축 예정기간을 선택하세요.");
			return;
		}
	}
	
	var JOIN_LIMIT_CODE_length = $("input[name='JOIN_LIMIT_CODE']:checked").length;
	var JOIN_LIMIT_CODE_value = $("input[name='JOIN_LIMIT_CODE']:checked").val();
	if(JOIN_LIMIT_CODE_length<1) {
		JOIN_LIMIT_CODE_value = $("#JOIN_LIMIT_CODE option:selected").val();
		if (JOIN_LIMIT_CODE_value == "") {
			JOIN_LIMIT_CODE_value = "1";
			//alert("가입대상을 선택하세요.");
			//return;
		}
	}
	var JOIN_LIMIT_CODE = JOIN_LIMIT_CODE_value;


	var InterestType_length = $("input[name='InterestType']:checked").length;
	var InterestType_value = $("input[name='InterestType']:checked").val();
	if(InterestType_length<1) {
		InterestType_value = $("#InterestType option:selected").val();
		if (InterestType_value == "") {
			InterestType_value = "All";
			//alert("이자 계산방식을 선택하세요.");
			//return;
		}
	}
	var InterestType = InterestType_value;
	

	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	var JOIN_METHOD_value = $("input[name='JOIN_METHOD']:checked").val();
	if(JOIN_METHOD_length<1) {
		JOIN_METHOD_value = $("#JOIN_METHOD option:selected").val();
		if (JOIN_METHOD_value == "-1") {
			JOIN_METHOD_value = "";
			//alert("가입방식을 선택하세요.");
			//return;
		}
	}
	var JOIN_METHOD = JOIN_METHOD_value;
	


	//월 저축금액 (최소)
	//var MonthSaveMoney = 1000;

	//총 저축금액 = 저축예정기간 * 월 저축금액
	//var TotalSaveMoney = InterestMonth * MonthSaveMoney;

	//가입대상 (제한없음)
	//var JOIN_LIMIT_CODE = "1";

	//이자계산방식 (전체)
	//var InterestType = "All";

	//가입방식 (전체)
	//var JOIN_METHOD = "";

	var BankValue = $("input[id='BankValue']").val();
	var SortType = $("input[id='SortType']").val();

	//상품명
	var productName = $("input[id='productName']").val();
	if(productName == "") {
		alert("상품명을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	} else if (productName.length < 2) {
		alert("상품명은 최소 2자리 이상을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	}
	productName = encodeURIComponent(productName);
	
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/compare/receiving_neosearch_2_search_result.php",
	{ 'productName': productName,
	  'searchType': 'productName',
		'BankValue': BankValue,
		'InterestType1': InterestType1,
		'MonthSaveMoney': MonthSaveMoney,
		'InterestMonth': InterestMonth,
		'TotalSaveMoney': TotalSaveMoney,
		'JOIN_LIMIT_CODE': JOIN_LIMIT_CODE,
		'InterestType': InterestType,
		'JOIN_METHOD': JOIN_METHOD, 
		'SortType': SortType
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 570 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}


function FP_ReceivingSearch2_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_ReceivingSearch2();
	$("input[id='SortType']").val("");
}

//적금 상품명 검색 정렬
function FP_ReceivingProdSearch2_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_ReceivingProdSearch2();
	$("input[id='SortType']").val("");
}


function FP_ReceivingDepositSearch() {

	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType1_length = $("input[name='InterestType1']:checked").length;
	
	if(InterestType1_length<1) {
		alert("적립방식을 선택하세요.");
		return;
	}

	var InterestType2_length = $("input[name='InterestType2']:checked").length;
	
	if(InterestType2_length<1) {
		alert("이자 계산방식을 선택하세요.");
		return;
	}
	
	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}


	InterestType = $("input[name='InterestType2']:checked").val() + $("input[name='InterestType1']:checked").val();


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var BankValue = $("input[id='BankValue']").val();
	var InterestMonth = $("#InterestMonth option:selected").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();

	$.post("/compare/receiving_neosave_search_result.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'InterestMonth': InterestMonth,
		'OrderByType': OrderByType, 
		'JOIN_METHOD': JOIN_METHOD, 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_ReceivingDepositSearch_new() {

	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType1_length = $("input[name='InterestType1']:checked").length;
	
	if(InterestType1_length<1) {
		alert("적립방식을 선택하세요.");
		return;
	}

	var InterestType2_length = $("input[name='InterestType2']:checked").length;
	
	if(InterestType2_length<1) {
		alert("이자 계산방식을 선택하세요.");
		return;
	}
	
	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}


	InterestType = $("input[name='InterestType2']:checked").val() + $("input[name='InterestType1']:checked").val();


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var BankValue = $("input[id='BankValue']").val();
	var InterestMonth = $("#InterestMonth option:selected").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
	var EXPIRATION = $("input[name='EXPIRATION']:checked").val();

	$.post("/compare/receiving_neosave_search_result_new.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'InterestMonth': InterestMonth,
		'OrderByType': OrderByType, 
		'JOIN_METHOD': JOIN_METHOD, 
		'EXPIRATION': EXPIRATION, 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_ReceivingDepositSearch_new2() {

	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType1_length = $("input[name='InterestType1']:checked").length;
	var InterestType1_value = $("input[name='InterestType1']:checked").val();
	if(InterestType1_length<1) {
		InterestType1_value = $("#InterestType1 option:selected").val();
		if(InterestType1_value=="") {
			alert("적립방식을 선택하세요.");
			return;
		}
	}
	var InterestType1 = InterestType1_value;
	
	var InterestType2_length = $("input[name='InterestType2']:checked").length;
	var InterestType2_value = $("input[name='InterestType2']:checked").val();
	if(InterestType2_length<1) {
		InterestType2_value = $("#InterestType2 option:selected").val();
		if(InterestType2_value=="") {
			alert("이자 계산방식을 선택하세요.");
			return;
		}
	}
	var InterestType2 = InterestType2_value;
	
	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	var JOIN_METHOD_value = $("input[name='JOIN_METHOD']:checked").val();
	if(JOIN_METHOD_length<1) {
		JOIN_METHOD_value = $("#JOIN_METHOD option:selected").val();
		if(JOIN_METHOD_value=="") {
			alert("가입방식을 선택하세요.");
			return;
		}
	}
	var JOIN_METHOD = JOIN_METHOD_value;

	//InterestType = $("input[name='InterestType2']:checked").val() + $("input[name='InterestType1']:checked").val();
	InterestType = InterestType2 + InterestType1;
	
	//만기
	var EXPIRATION_length = $("input[name='EXPIRATION']:checked").length;
	var EXPIRATION_value = $("input[name='EXPIRATION']:checked").val();
	if(EXPIRATION_length<1) {
		EXPIRATION_value = $("#EXPIRATION option:selected").val();
		if(EXPIRATION_value=="") {
			alert("만기를 선택하세요.");
			return;
		}
	}
	var EXPIRATION = EXPIRATION_value;
	

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var BankValue = $("input[id='BankValue']").val();
	var InterestMonth = $("#InterestMonth option:selected").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	//var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
	//var EXPIRATION = $("input[name='EXPIRATION']:checked").val();

	$.post("/compare/receiving_neosave_search_result_new2.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'InterestMonth': InterestMonth,
		'OrderByType': OrderByType, 
		'JOIN_METHOD': JOIN_METHOD, 
		'EXPIRATION': EXPIRATION, 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}


function FP_ReceivingDepositSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_ReceivingDepositSearch();
	$("input[id='SortType']").val("");
}

function FP_ReceivingDepositSearch_Sort2(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_ReceivingDepositSearch_new2();
	$("input[id='SortType']").val("");
}

function FP_MidLoanEndSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_3_3_search_result.php",
	{ 'InterestType': $("input[id='InterestType']").val(),
		'BankValue': $("input[id='BankValue']").val(),
		'InterestMonth': $("#InterestMonth option:selected").val(),
		'OrderByType': $("#OrderByType option:selected").val(),
		'ProductName': $("input[id='ProductName']").val(),
		'BankOrderby': $("input[id='BankOrderby']").val(), 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_MidLoanEndSearch_new() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_3_3_new_search_result.php",
	{ 'InterestType': $("input[id='InterestType']").val(),
		'BankValue': $("input[id='BankValue']").val(),
		'InterestMonth': $("#InterestMonth option:selected").val(),
		'OrderByType': $("#OrderByType option:selected").val(),
		'ProductName': $("input[id='ProductName']").val(),
		'BankOrderby': $("input[id='BankOrderby']").val(), 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_MidLoanEndSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_MidLoanEndSearch();
	$("input[id='SortType']").val("");
}

function FP_MidLoanEndSearch_Sort_new(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_MidLoanEndSearch_new();
	$("input[id='SortType']").val("");
}

function FP_MidLoanSupportSearch_Sort_new(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_MidLoanSupportSearch_new();
	$("input[id='SortType']").val("");
}

function FP_MidLoanSupportSearch_new() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_3_3_3_new_search_result.php",
	{ 'InterestType': $("input[id='InterestType']").val(),
		'BankValue': $("input[id='BankValue']").val(),
		'InterestMonth': $("#InterestMonth option:selected").val(),
		'OrderByType': $("#OrderByType option:selected").val(),
		'ProductName': $("input[id='ProductName']").val(),
		'BankOrderby': $("input[id='BankOrderby']").val(), 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_MidLoanPreSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_3_2_search_result.php",
	{ 'InterestType': $("input[id='InterestType']").val(),
		'BankValue': $("input[id='BankValue']").val(),
		'InterestMonth': $("#InterestMonth option:selected").val(),
		'OrderByType': $("#OrderByType option:selected").val(),
		'ProductName': $("input[id='ProductName']").val(),
		'BankOrderby': $("input[id='BankOrderby']").val(), 
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_MidLoanPreSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_MidLoanPreSearch();
	$("input[id='SortType']").val("");
}


function FP_MidLoanSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}

	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_3_search_result.php",
	{ 'InterestType': $("input[id='InterestType']").val(),
		'BankValue': $("input[id='BankValue']").val(),
		'InterestMonth': $("#InterestMonth option:selected").val(),
		'OrderByType': $("#OrderByType option:selected").val(),
		'ProductName': $("input[id='ProductName']").val(),
		'BankOrderby': $("input[id='BankOrderby']").val(),
		'JOIN_METHOD': JOIN_METHOD,
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_MidLoanSearch_new() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}

	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_3_search_result.php",
	{ 'InterestType': $("input[id='InterestType']").val(),
		'BankValue': $("input[id='BankValue']").val(),
		'InterestMonth': $("#InterestMonth option:selected").val(),
		'OrderByType': $("#OrderByType option:selected").val(),
		'ProductName': $("input[id='ProductName']").val(),
		'BankOrderby': $("input[id='BankOrderby']").val(),
		'JOIN_METHOD': JOIN_METHOD,
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_MidLoanSearch_new2() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	/*
	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}

	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
	*/

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();

	$.post("/compare/loan_search_3_new_search_result.php",
	{ 'InterestType': $("input[id='InterestType']").val(),
		'BankValue': $("input[id='BankValue']").val(),
		'InterestMonth': $("#InterestMonth option:selected").val(),
		'OrderByType': $("#OrderByType option:selected").val(),
		'ProductName': $("input[id='ProductName']").val(),
		'BankOrderby': $("input[id='BankOrderby']").val(),
		//'JOIN_METHOD': JOIN_METHOD,
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_MidLoanSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	FP_MidLoanSearch();
	$("input[id='SortType']").val("");
}

function isMobile() {
	var filter = "win16|win32|win64|mac|macintel";
	if( navigator.platform  ){
		if( filter.indexOf(navigator.platform.toLowerCase())<0 ){
			return true;
		}else{
			return false;
		}
	}
} 

function BrowserVersionCheck() {

	var word;
	var versionOrType = "another";

	var agent = navigator.userAgent.toLowerCase();
	var name = navigator.appName;
 
	/***********************************************
	* IE인 경우 버전 체크
	***********************************************/ 
	// IE old version ( IE 10 or Lower )
	if ( name == "Microsoft Internet Explorer" ){
		word = "msie ";
		versionOrType = "IE";
	}else{
		// IE 11
		if( agent.search("trident") > -1 ) {
			word = "trident/.*rv:";
			versionOrType = "IE";
			// IE 12  ( Microsoft Edge )
		}else if( agent.search("edge/") > -1 ) {
			word = "edge/";
			versionOrType = "Edge";
		}
	}

	/*
	var reg = new RegExp( word + "([0-9]{1,})(\\.{0,}[0-9]{0,1})" );
	if ( reg.exec( agent ) != null )
	versionOrType = RegExp.$1 + RegExp.$2;
	*/
 
	/***********************************************
	* IE가 아닌 경우 브라우저의 종류 체크
	***********************************************/ 
	if( versionOrType == "another" ){
		if (agent.indexOf("chrome") != -1) versionOrType = "Chrome";
		else if (agent.indexOf("opera") != -1) versionOrType = "Opera";
			else if (agent.indexOf("firefox") != -1) versionOrType = "Firefox"; 
				else if (agent.indexOf("safari") != -1) versionOrType = "Safari";
		}

	return versionOrType;
}

function Add_Favorite(url,title) {
	window.external.AddFavorite(url, title);
}


/*세자리마다 자릿수 찍기*/
function FormatNumber2(num){
  if(isNaN(num)) { 
//alert("문자는 사용할 수 없습니다.");
return "" }
  if(num==0) return num
  temp=new Array()
  fl=""
  co=3 
  if(num<0){ num=num*(-1); fl="-" }
  num = new String(num)
  num_len=num.length
  while (num_len>0){
          num_len=num_len-co
          if(num_len<0){co=num_len+co;num_len=0}
          temp.unshift(num.substr(num_len,co))
  }
  return fl+temp.join(",")
}

function NumberValueCheck(str) {
	
	var val = $("input[id='"+str+"']").val();

	val = val.replace(/,/gi,"");

	var val2 = FormatNumber2(val);
	
	$("input[id='"+str+"']").val(val2);
	
}


/* 숫자체크*/
function IsNumber(num){
var x=num;
//var anum=/(^\d+$)|(^\d+\.\d+$)/
var anum=/(^\d+$)|(^\d+$)/
if (anum.test(x))
testresult=true
else{
testresult=false
}
return (testresult)
}

/* 라이오 버튼 체크 */
function hasCheckedRadio(input) {
	if (input.length > 1) {
		for (var inx = 0; inx < input.length; inx++) {
			if (input[inx].checked) return true;
		}
	} else {
		if (input.checked) return true;
	}
	return false;
}

function isContinuedValue(value) {
        //console.log("value = " + value);
        var intCnt1 = 0;
        var intCnt2 = 0;
        var temp0 = "";
        var temp1 = "";
        var temp2 = "";
        var temp3 = "";
 
        for (var i = 0; i < value.length-3; i++) {
            //console.log("=========================");
            temp0 = value.charAt(i);
            temp1 = value.charAt(i + 1);
            temp2 = value.charAt(i + 2);
            temp3 = value.charAt(i + 3);
 
            //console.log(temp0)
            //console.log(temp1)
            //console.log(temp2)
            //console.log(temp3)
 
            if (temp0.charCodeAt(0) - temp1.charCodeAt(0) == 1
                    && temp1.charCodeAt(0) - temp2.charCodeAt(0) == 1
                    && temp2.charCodeAt(0) - temp3.charCodeAt(0) == 1) {
                intCnt1 = intCnt1 + 1;
            }
 
            if (temp0.charCodeAt(0) - temp1.charCodeAt(0) == -1
                    && temp1.charCodeAt(0) - temp2.charCodeAt(0) == -1
                    && temp2.charCodeAt(0) - temp3.charCodeAt(0) == -1) {
                intCnt2 = intCnt2 + 1;
            }
            //console.log("=========================");
        }
 
        //console.log(intCnt1 > 0 || intCnt2 > 0);
        return (intCnt1 > 0 || intCnt2 > 0);
}

//한글체크
function hanCheck(ID) {

var digits="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
var temp;
//alert(MemberID);
for(i=0;i<ID.length;i++){
temp=ID.substring(i,i+1);
if (digits.indexOf(temp)==-1){
return false
	  }
   }
return true
}

//이메일 체크
function chkEmail(str) {

	var reg_email = /^([0-9a-zA-Z_\.-]+)@([0-9a-zA-Z_-]+)(\.[0-9a-zA-Z_-]+){1,2}$/;

	if(!reg_email.test(str)){
		return false;
	}
	return true;
}



//페이지 이동 관련
function pageRun(num)
{
	document.listScriptForm.pg.value = num;
	document.listScriptForm.submit();
}

function readRun(idx)
{
	document.ReadScriptForm.idx.value = idx;
	document.ReadScriptForm.submit();
}

function SearchOk() {

	if(document.searchForm.sw.value=="") {
		alert('검색어를 입력하세요.');
		//document.searchForm.sw.focus();
		return;
	}

	document.searchForm.submit();

}

function SearchOk_epigyny() {

	if(document.searchForm.sw.value=="") {
	//	alert('검색어를 입력하세요.');
		//document.searchForm.sw.focus();
	//	return;
	}

	document.searchForm.submit();

}
function SearchOk_low_birth() {

	if(document.searchForm.sw.value=="") {
	//	alert('검색어를 입력하세요.');
		//document.searchForm.sw.focus();
	//	return;
	}

	document.searchForm.submit();

}

//전체 메뉴 열기
function SiteMenuToggle() {

	$("div[id='topsubMenu']").hide();

	$("#SiteMenu").hide();
	$('html, body').animate({ scrollTop : 0 }, 200);

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height();

	$("div[id='SiteMenu']").css({
		"left": LocWidth-470,
		"z-index":"1000"
	}).show('slide', {direction : 'up'}, 300);

	$("#SiteMenu").focus();

}

function SiteMenuClose() {
	$("#SiteMenu").hide('slide', {direction : 'up'}, 200);
	$("#SiteMenuBtn").focus();
}

//데이터 레이어 닫기
function DataResultClose() {
	$("div[id='Roading']").hide();
	$("div[id='DataResult']").html("");
	$("div[id='DataResult']").hide();
	$("div[id='SysBg_White']").hide();
	$("div[id='SysBg_Black']").hide();

}


function FaqListOpen(faq_idx) {

	var faq_idx_length = $("input[name='faq_idx']").length;

	for(i=0;i<faq_idx_length;i++) {
		if($("input[name='faq_idx']:eq("+i+")").val()==faq_idx) {
			ListView(i);
		}
	}

}


//공통 함수 ------------------------------------------------------------------------------------------------------

//메인 금리/수수료 빠른 검색
function MainCompareSearchSelect(Index) {

	for(i=0;i<$("img[name='MainCompareSearchSelectImg']").length;i++) {
		$("img[name='MainCompareSearchSelectImg']").eq(i).attr('src','/images/main/mzone_cp_cate0'+(i+1)+'.png');
	}
	$("img[name='MainCompareSearchSelectImg']").eq(Index).attr('src','/images/main/mzone_cp_cate0'+(Index + 1)+'ov.png');

	for(i=0;i<$("div[name='MainCompareSearch']").length;i++) {
		$("div[name='MainCompareSearch']").eq(i).hide();
	}
	$("div[name='MainCompareSearch']").eq(Index).show();

}


//신탁상품금리비교 > 연금저축 검색 팝업
function PopupTrust_pension(url) {
	//var currentWidth = $(window).width();
	var currentWidth = screen.width;
	window.open(url,'pension','scrollbars=yes, resizable=yes, left=0, width='+currentWidth+', height=1000');
}

function UserNote(url) {
	window.open(url,'policy1','scrollbars=yes, resizable=no, left=400, width=900, height=900');
}

function Policy(url) {
	window.open(url,'policy2','scrollbars=yes, resizable=no, left=400, width=1000, height=900');
}

function FootLink01() {
	$($("div[id='Link01']")).toggle('slide', {direction : 'down'}, 150);
}

function FootLink02() {
	$($("div[id='Link02']")).toggle('slide', {direction : 'down'}, 150);
}

function FootLink03() {
	$($("div[id='Link03']")).toggle('slide', {direction : 'down'}, 150);
}

function CheckPassword(str) {
	if(!/^[a-zA-Z0-9]{8,20}$/.test(str)){ 
		alert('비밀번호는 숫자와 영문자 조합으로 8~20자리를 사용해야 합니다.'); 
		return false;
	}

	var chk_num = str.search(/[0-9]/g); 
	var chk_eng = str.search(/[a-z]/ig); 

	if(chk_num < 0 || chk_eng < 0){ 
		alert('비밀번호는 숫자와 영문자를 혼용하여야 합니다.'); 
		return false;
	}

	if(/(\w)\1\1\1/.test(str) || isContinuedValue(str)){
		alert('비밀번호에 4자 이상의 연속 또는 반복 문자 및 숫자를 사용하실 수 없습니다.'); 
		return false;
	}

	return true;

}

function isContinuedValue(value) {
        //console.log("value = " + value);
        var intCnt1 = 0;
        var intCnt2 = 0;
        var temp0 = "";
        var temp1 = "";
        var temp2 = "";
        var temp3 = "";
 
        for (var i = 0; i < value.length-3; i++) {
            //console.log("=========================");
            temp0 = value.charAt(i);
            temp1 = value.charAt(i + 1);
            temp2 = value.charAt(i + 2);
            temp3 = value.charAt(i + 3);
 
            //console.log(temp0)
            //console.log(temp1)
            //console.log(temp2)
            //console.log(temp3)
 
            if (temp0.charCodeAt(0) - temp1.charCodeAt(0) == 1
                    && temp1.charCodeAt(0) - temp2.charCodeAt(0) == 1
                    && temp2.charCodeAt(0) - temp3.charCodeAt(0) == 1) {
                intCnt1 = intCnt1 + 1;
            }
 
            if (temp0.charCodeAt(0) - temp1.charCodeAt(0) == -1
                    && temp1.charCodeAt(0) - temp2.charCodeAt(0) == -1
                    && temp2.charCodeAt(0) - temp3.charCodeAt(0) == -1) {
                intCnt2 = intCnt2 + 1;
            }
            //console.log("=========================");
        }
 
        //console.log(intCnt1 > 0 || intCnt2 > 0);
        return (intCnt1 > 0 || intCnt2 > 0);
    }

function SelfMinwonSubmitOk() {

	val = document.Form1;
	
	/*
	if(val.SITETYPE[0].checked == false && val.SITETYPE[1].checked == false) {
		alert("민원구분을 선택하세요.");
		val.SITETYPE[0].focus();
		return;
	}
	*/
	if(val.NAME.value=="") {
		alert("성명을 입력하세요.");
		val.NAME.focus();
		return;
	}
	/*
	if(val.GENDER[0].checked == false && val.GENDER[1].checked == false) {
		alert("성별을 선택하세요.");
		val.GENDER[0].focus();
		return;
	}
	*/
	if(val.EMAIL.value=="") {
		alert("이메일을 입력하세요.");
		val.EMAIL.focus();
		return;
	}

	if(!chkEmail(val.EMAIL.value)) {
		alert("이메일을 정확하게 입력하세요.");
		val.EMAIL.focus();
		return;
	}

	if(val.PWD.value=="") {
		alert("비밀번호를 입력하세요.\n\n비밀번호는 영문, 숫자 조합으로 8자 이상 입력하세요.");
		val.PWD.focus();
		return;
	}

	if (!CheckPassword(val.PWD.value)) {
		val.PWD.focus();
		return;
	}

	if(val.TEL1.value=="") {
		alert("전화번호 지역번호를 입력하세요.");
		val.TEL1.focus();
		return;
	}

	if(!IsNumber(val.TEL1.value)) {
		alert("전화번호 지역번호는 숫자만 입력하세요.");
		val.TEL1.focus();
		return;
	}

	if(val.TEL1.value.length > 3) {
		alert("전화번호 지역번호를 정확하게 입력하세요.");
		val.TEL1.focus();
		return;
	}

	if(val.TEL2.value=="") {
		alert("전화번호 국번을 입력하세요.");
		val.TEL2.focus();
		return;
	}

	if(!IsNumber(val.TEL2.value)) {
		alert("전화번호 국번은 숫자만 입력하세요.");
		val.TEL2.focus();
		return;
	}

	if(val.TEL2.value.length > 4) {
		alert("전화번호 국번을 정확하게 입력하세요.");
		val.TEL2.focus();
		return;
	}

	if(val.TEL3.value=="") {
		alert("전화번호 끝번호를 입력하세요.");
		val.TEL3.focus();
		return;
	}

	if(!IsNumber(val.TEL3.value)) {
		alert("전화번호 끝번호는 숫자만 입력하세요.");
		val.TEL3.focus();
		return;
	}

	if(val.TEL3.value.length > 4) {
		alert("전화번호 끝번호를 정확하게 입력하세요.");
		val.TEL3.focus();
		return;
	}

	if(val.HP1.value=="") {
		alert("휴대전화번호 앞번호를 입력하세요.");
		val.HP1.focus();
		return;
	}

	if(!IsNumber(val.HP1.value)) {
		alert("휴대전화번호 앞번호는 숫자만 입력하세요.");
		val.HP1.focus();
		return;
	}

	if(val.HP1.value.length > 3) {
		alert("휴대전화번호 앞번호를 정확하게 입력하세요.");
		val.HP1.focus();
		return;
	}

	if(val.HP2.value=="") {
		alert("휴대전화번호 중간번호를 입력하세요.");
		val.HP2.focus();
		return;
	}

	if(!IsNumber(val.HP2.value)) {
		alert("휴대전화번호 중간번호는 숫자만 입력하세요.");
		val.HP2.focus();
		return;
	}

	if(val.HP2.value.length > 4) {
		alert("휴대전화번호 중간번호를 정확하게 입력하세요.");
		val.HP2.focus();
		return;
	}

	if(val.HP3.value=="") {
		alert("휴대전화번호 끝번호를 입력하세요.");
		val.HP3.focus();
		return;
	}

	if(!IsNumber(val.HP3.value)) {
		alert("휴대전화번호 끝번호는 숫자만 입력하세요.");
		val.HP3.focus();
		return;
	}

	if(val.HP3.value.length > 4) {
		alert("휴대전화번호 끝번호를 정확하게 입력하세요.");
		val.HP3.focus();
		return;
	}



	if(val.AGREE[0].checked == false && val.AGREE[1].checked == false) {
		alert("개인정보 수집·이용에 동의하여야 신청을 접수할 수 있습니다.");
		val.AGREE[0].focus();
		return;
	}

	if(val.AGREE[0].checked == false) {
		alert("개인정보 수집·이용에 동의하여야 신청을 접수할 수 있습니다.");
		val.AGREE[0].focus();
		return;
	}

	if(val.AGREE2[0].checked == false && val.AGREE2[1].checked == false) {
		alert("개인정보 제3자 제공에 동의하여야 신청을 접수할 수 있습니다.");
		val.AGREE2[0].focus();
		return;
	}

	if(val.AGREE2[0].checked == false) {
		alert("개인정보 제3자 제공에 동의하여야 신청을 접수할 수 있습니다.");
		val.AGREE2[0].focus();
		return;
	}

	if(val.TITLE.value=="") {
		alert("신고제목을 입력하세요.");
		val.TITLE.focus();
		return;
	}

	if(val.TITLE.value.length > 200) {
		alert("신고제목은 200자 이내로 입력하세요.");
		val.TITLE.focus();
		return;
	}

	/*
	if(!hasCheckedRadio(val.BANK_TYPE)) {
		alert("민원 금융회사를 선택하세요");
		val.BANK_TYPE[0].focus();
		return;
	}*/


		if(!hasCheckedRadio(val.BANK_CODE)) {
			alert("민원 금융회사 · 기관을 선택하세요");
			val.BANK_CODE[0].focus();
			return;
		}

	/*
	if(val.BANK_TYPE[1].checked==true) {
		if(val.BANK_NAME_1.value=="") {
			alert("상호저축은행명을 입력하세요.");
			val.BANK_NAME_1.focus();
			return;
		}
	}

	if(val.BANK_TYPE[2].checked==true) {
		if(val.BANK_NAME_2.value=="") {
			alert("신용협동조합명을 입력하세요.");
			val.BANK_NAME_2.focus();
			return;
		}
	}

	if(val.BANK_TYPE[3].checked==true) {
		if(val.BANK_NAME_3.value=="") {
			alert("농/수/산협동조합명을 입력하세요.");
			val.BANK_NAME_3.focus();
			return;
		}
	}

	if(val.BANK_TYPE[4].checked==true) {
		if(val.BANK_NAME_4.value=="") {
			alert("생명보험사명을 입력하세요.");
			val.BANK_NAME_4.focus();
			return;
		}
	}

	if(val.BANK_TYPE[5].checked==true) {
		if(val.BANK_NAME_5.value=="") {
			alert("손해보헙사명을 입력하세요.");
			val.BANK_NAME_5.focus();
			return;
		}
	}

	if(val.BANK_TYPE[6].checked==true) {
		if(val.BANK_NAME_6.value=="") {
			alert("증권사명을 입력하세요.");
			val.BANK_NAME_6.focus();
			return;
		}
	}

	if(val.BANK_TYPE[7].checked==true) {
		if(val.BANK_NAME_7.value=="") {
			alert("신용카드사명을 입력하세요.");
			val.BANK_NAME_7.focus();
			return;
		}
	}

	if(val.BANK_TYPE[8].checked==true) {
		if(val.BANK_NAME_8.value=="") {
			alert("신용정보회사명을 입력하세요.");
			val.BANK_NAME_8.focus();
			return;
		}
	}

	if(val.BANK_TYPE[9].checked==true) {
		if(val.BANK_NAME_9.value=="") {
			alert("법원명을 입력하세요.");
			val.BANK_NAME_9.focus();
			return;
		}
	}

	if(val.BANK_TYPE[10].checked==true) {
		if(val.BANK_NAME_10.value=="") {
			alert("기타 금융기관명을 입력하세요.");
			val.BANK_NAME_10.focus();
			return;
		}
	}
	*/

	if(val.CONTENT.value=="") {
		alert("신고내용을 입력하세요.");
		val.CONTENT.focus();
		return;
	}

	if(val.CONTENT.value.length < 10) {
		alert("신고내용은 10자 이상 입력하세요.");
		val.CONTENT.focus();
		return;
	}

	
	if(val.LOAN_DATE.value == "") {
		alert("대출일시를 입력하세요.");
		val.LOAN_DATE.focus();
		return;
	}
	if(val.LOAN_PLACE.value== "") {
		alert("대출장소를 입력하세요.");
		val.LOAN_PLACE.focus();
		return;
	}	
	
	/*
	if(val.file.value.length > 0) {
		if(!CheckAttemp(val.file.value)) {
			alert("등록하려는 첨부파일에 등록할 수 없는 파일 확장자가 존재합니다.\n\n등록 불가능한 확장자는\n\n============================================================================ \n\n.php, .php3, .exe, .cmd, .htm, .html, .shtml, .inc, .jsp, .js, .cab, .apk, .java, .dll, .cgi\n\n============================================================================\n\n 입니다.");
			return;
		}
	}
	*/


	SubmitConfirm = confirm("작성한 신고내용을 접수하시겠습니까?");

	if(SubmitConfirm==true) {
		$("#BtnSubmit").hide();
		$("#BtnWating").show();
		val.submit();
	}

}
	
	
function MinwonSubmitOk() {

	val = document.Form1;
	/*
	if(val.SITETYPE[0].checked == false && val.SITETYPE[1].checked == false) {
		alert("민원구분을 선택하세요.");
		val.SITETYPE[0].focus();
		return;
	}
	*/
	if(val.NAME.value=="") {
		alert("성명을 입력하세요.");
		val.NAME.focus();
		return;
	}
	/*
	if(val.GENDER[0].checked == false && val.GENDER[1].checked == false) {
		alert("성별을 선택하세요.");
		val.GENDER[0].focus();
		return;
	}
	*/
	if(val.EMAIL.value=="") {
		alert("이메일을 입력하세요.");
		val.EMAIL.focus();
		return;
	}

	if(!chkEmail(val.EMAIL.value)) {
		alert("이메일을 정확하게 입력하세요.");
		val.EMAIL.focus();
		return;
	}

	if(val.PWD.value=="") {
		alert("비밀번호를 입력하세요.\n\n비밀번호는 영문, 숫자 조합으로 8자 이상 입력하세요.");
		val.PWD.focus();
		return;
	}

	if (!CheckPassword(val.PWD.value)) {
		val.PWD.focus();
		return;
	}

	if(val.TEL1.value=="") {
		alert("전화번호 지역번호를 입력하세요.");
		val.TEL1.focus();
		return;
	}

	if(!IsNumber(val.TEL1.value)) {
		alert("전화번호 지역번호는 숫자만 입력하세요.");
		val.TEL1.focus();
		return;
	}

	if(val.TEL1.value.length > 3) {
		alert("전화번호 지역번호를 정확하게 입력하세요.");
		val.TEL1.focus();
		return;
	}

	if(val.TEL2.value=="") {
		alert("전화번호 국번을 입력하세요.");
		val.TEL2.focus();
		return;
	}

	if(!IsNumber(val.TEL2.value)) {
		alert("전화번호 국번은 숫자만 입력하세요.");
		val.TEL2.focus();
		return;
	}

	if(val.TEL2.value.length > 4) {
		alert("전화번호 국번을 정확하게 입력하세요.");
		val.TEL2.focus();
		return;
	}

	if(val.TEL3.value=="") {
		alert("전화번호 끝번호를 입력하세요.");
		val.TEL3.focus();
		return;
	}

	if(!IsNumber(val.TEL3.value)) {
		alert("전화번호 끝번호는 숫자만 입력하세요.");
		val.TEL3.focus();
		return;
	}

	if(val.TEL3.value.length > 4) {
		alert("전화번호 끝번호를 정확하게 입력하세요.");
		val.TEL3.focus();
		return;
	}

	if(val.HP1.value=="") {
		alert("휴대전화번호 앞번호를 입력하세요.");
		val.HP1.focus();
		return;
	}

	if(!IsNumber(val.HP1.value)) {
		alert("휴대전화번호 앞번호는 숫자만 입력하세요.");
		val.HP1.focus();
		return;
	}

	if(val.HP1.value.length > 3) {
		alert("휴대전화번호 앞번호를 정확하게 입력하세요.");
		val.HP1.focus();
		return;
	}

	if(val.HP2.value=="") {
		alert("휴대전화번호 중간번호를 입력하세요.");
		val.HP2.focus();
		return;
	}

	if(!IsNumber(val.HP2.value)) {
		alert("휴대전화번호 중간번호는 숫자만 입력하세요.");
		val.HP2.focus();
		return;
	}

	if(val.HP2.value.length > 4) {
		alert("휴대전화번호 중간번호를 정확하게 입력하세요.");
		val.HP2.focus();
		return;
	}

	if(val.HP3.value=="") {
		alert("휴대전화번호 끝번호를 입력하세요.");
		val.HP3.focus();
		return;
	}

	if(!IsNumber(val.HP3.value)) {
		alert("휴대전화번호 끝번호는 숫자만 입력하세요.");
		val.HP3.focus();
		return;
	}

	if(val.HP3.value.length > 4) {
		alert("휴대전화번호 끝번호를 정확하게 입력하세요.");
		val.HP3.focus();
		return;
	}

	if(val.BRING_UP[0].checked == false && val.BRING_UP[1].checked == false) {
		alert("당해 민원과 관련하여 금융회사에 민원을 제기한 적이 있는지 선택하세요.");
		val.BRING_UP[1].focus();
		return;
	}

	if(val.AGREE[0].checked == false && val.AGREE[1].checked == false) {
		alert("개인정보 수집·이용에 동의하여야 민원신청을 접수할 수 있습니다.");
		val.AGREE[0].focus();
		return;
	}

	if(val.AGREE[0].checked == false) {
		alert("개인정보 수집·이용에 동의하여야 민원신청을 접수할 수 있습니다.");
		val.AGREE[0].focus();
		return;
	}

	if(val.AGREE2[0].checked == false && val.AGREE2[1].checked == false) {
		alert("개인정보 제3자 제공에 동의하여야 민원신청을 접수할 수 있습니다.");
		val.AGREE2[0].focus();
		return;
	}

	if(val.AGREE2[0].checked == false) {
		alert("개인정보 제3자 제공에 동의하여야 민원신청을 접수할 수 있습니다.");
		val.AGREE2[0].focus();
		return;
	}

	if(val.TITLE.value=="") {
		alert("민원제목을 입력하세요.");
		val.TITLE.focus();
		return;
	}

	if(val.TITLE.value.length > 200) {
		alert("민원제목은 200자 이내로 입력하세요.");
		val.TITLE.focus();
		return;
	}

	/*
	if(!hasCheckedRadio(val.BANK_TYPE)) {
		alert("민원 금융회사를 선택하세요");
		val.BANK_TYPE[0].focus();
		return;
	}*/


		if(!hasCheckedRadio(val.BANK_CODE)) {
			alert("시중은행중에서 해당하는 은행을 선택하세요");
			val.BANK_CODE[0].focus();
			return;
		}

	/*
	if(val.BANK_TYPE[1].checked==true) {
		if(val.BANK_NAME_1.value=="") {
			alert("상호저축은행명을 입력하세요.");
			val.BANK_NAME_1.focus();
			return;
		}
	}

	if(val.BANK_TYPE[2].checked==true) {
		if(val.BANK_NAME_2.value=="") {
			alert("신용협동조합명을 입력하세요.");
			val.BANK_NAME_2.focus();
			return;
		}
	}

	if(val.BANK_TYPE[3].checked==true) {
		if(val.BANK_NAME_3.value=="") {
			alert("농/수/산협동조합명을 입력하세요.");
			val.BANK_NAME_3.focus();
			return;
		}
	}

	if(val.BANK_TYPE[4].checked==true) {
		if(val.BANK_NAME_4.value=="") {
			alert("생명보험사명을 입력하세요.");
			val.BANK_NAME_4.focus();
			return;
		}
	}

	if(val.BANK_TYPE[5].checked==true) {
		if(val.BANK_NAME_5.value=="") {
			alert("손해보헙사명을 입력하세요.");
			val.BANK_NAME_5.focus();
			return;
		}
	}

	if(val.BANK_TYPE[6].checked==true) {
		if(val.BANK_NAME_6.value=="") {
			alert("증권사명을 입력하세요.");
			val.BANK_NAME_6.focus();
			return;
		}
	}

	if(val.BANK_TYPE[7].checked==true) {
		if(val.BANK_NAME_7.value=="") {
			alert("신용카드사명을 입력하세요.");
			val.BANK_NAME_7.focus();
			return;
		}
	}

	if(val.BANK_TYPE[8].checked==true) {
		if(val.BANK_NAME_8.value=="") {
			alert("신용정보회사명을 입력하세요.");
			val.BANK_NAME_8.focus();
			return;
		}
	}

	if(val.BANK_TYPE[9].checked==true) {
		if(val.BANK_NAME_9.value=="") {
			alert("법원명을 입력하세요.");
			val.BANK_NAME_9.focus();
			return;
		}
	}

	if(val.BANK_TYPE[10].checked==true) {
		if(val.BANK_NAME_10.value=="") {
			alert("기타 금융기관명을 입력하세요.");
			val.BANK_NAME_10.focus();
			return;
		}
	}
	*/
	if(val.SUMMARY.value=="") {
		alert("민원요지를 입력하세요.");
		val.SUMMARY.focus();
		return;
	}

	if(val.SUMMARY.value.length > 20) {
		alert("민원요지는 20자 이내로 입력하세요.");
		val.SUMMARY.focus();
		return;
	}

	if(val.CONTENT.value=="") {
		alert("민원내용을 입력하세요.");
		val.CONTENT.focus();
		return;
	}

	if(val.CONTENT.value.length < 10) {
		alert("민원내용은 10자 이상 입력하세요.");
		val.CONTENT.focus();
		return;
	}

	/*
	if(val.file.value.length > 0) {
		if(!CheckAttemp(val.file.value)) {
			alert("등록하려는 첨부파일에 등록할 수 없는 파일 확장자가 존재합니다.\n\n등록 불가능한 확장자는\n\n============================================================================ \n\n.php, .php3, .exe, .cmd, .htm, .html, .shtml, .inc, .jsp, .js, .cab, .apk, .java, .dll, .cgi\n\n============================================================================\n\n 입니다.");
			return;
		}
	}
	*/


	SubmitConfirm = confirm("작성한 민원상담 신청내역을 접수하시겠습니까?");

	if(SubmitConfirm==true) {
		$("#BtnSubmit").hide();
		$("#BtnWating").show();
		val.submit();
	}

}

function MinwonSubmit_newOk() {

	val = document.Form1;
	/*
	if(val.SITETYPE[0].checked == false && val.SITETYPE[1].checked == false) {
		alert("민원구분을 선택하세요.");
		val.SITETYPE[0].focus();
		return;
	}
	*/
	if(val.NAME.value=="") {
		alert("성명을 입력하세요.");
		val.NAME.focus();
		return;
	}

	if(val.ID.value=="") {
		alert("아이디를 입력하세요.");
		val.ID.focus();
		return;
	}

	if(val.PWD.value=="") {
		alert("비밀번호를 입력하세요.\n\n비밀번호는 영문, 숫자 조합으로 8자 이상 입력하세요.");
		val.PWD.focus();
		return;
	}

	if (!CheckPassword(val.PWD.value)) {
		val.PWD.focus();
		return;
	}

	if(val.BRING_UP[0].checked == false && val.BRING_UP[1].checked == false) {
		alert("당해 민원과 관련하여 금융회사에 민원을 제기한 적이 있는지 선택하세요.");
		val.BRING_UP[1].focus();
		return;
	}
  /*
	if(val.AGREE[0].checked == false && val.AGREE[1].checked == false) {
		alert("개인정보 수집·이용에 동의하여야 민원신청을 접수할 수 있습니다.");
		val.AGREE[0].focus();
		return;
	}

	if(val.AGREE[0].checked == false) {
		alert("개인정보 수집·이용에 동의하여야 민원신청을 접수할 수 있습니다.");
		val.AGREE[0].focus();
		return;
	}

	if(val.AGREE2[0].checked == false && val.AGREE2[1].checked == false) {
		alert("개인정보 제3자 제공에 동의하여야 민원신청을 접수할 수 있습니다.");
		val.AGREE2[0].focus();
		return;
	}

	if(val.AGREE2[0].checked == false) {
		alert("개인정보 제3자 제공에 동의하여야 민원신청을 접수할 수 있습니다.");
		val.AGREE2[0].focus();
		return;
	}
  */
	if(val.TITLE.value=="") {
		alert("민원제목을 입력하세요.");
		val.TITLE.focus();
		return;
	}

	if(val.TITLE.value.length > 200) {
		alert("민원제목은 200자 이내로 입력하세요.");
		val.TITLE.focus();
		return;
	}

		if(!hasCheckedRadio(val.BANK_CODE)) {
			alert("시중은행중에서 해당하는 은행을 선택하세요");
			val.BANK_CODE[0].focus();
			return;
		}
	if(val.SUMMARY.value=="") {
		alert("민원요지를 입력하세요.");
		val.SUMMARY.focus();
		return;
	}

	if(val.SUMMARY.value.length > 20) {
		alert("민원요지는 20자 이내로 입력하세요.");
		val.SUMMARY.focus();
		return;
	}

	if(val.CONTENT.value=="") {
		alert("민원내용을 입력하세요.");
		val.CONTENT.focus();
		return;
	}

	if(val.CONTENT.value.length < 10) {
		alert("민원내용은 10자 이상 입력하세요.");
		val.CONTENT.focus();
		return;
	}

	SubmitConfirm = confirm("작성한 민원상담 신청내역을 접수하시겠습니까?");

	if(SubmitConfirm==true) {
		$("#BtnSubmit").hide();
		$("#BtnWating").show();
		val.submit();
	}

}

function MinwonLoginOk() {

	val = document.Form1;

	if(val.Email.value=="") {
		alert("이메일을 입력하세요.");
		val.Email.focus();
		return;
	}

	if(val.Pwd.value=="") {
		alert("비밀번호를 입력하세요.");
		val.Pwd.focus();
		return;
	}


	val.submit();

}

function MinwonDropOk() {

val = document.Form1;

if(val.DROP_REASON.value == "") {
	alert("민원 취하 사유를 입력해주세요.");
	val.DROP_REASON.focus();
	return;
}

if(val.DROP_REASON.value.length > 200) {
	alert("민원 취하 사유는 200자 이내로 입력해주세요.");
	val.DROP_REASON.focus();
	return;
}

SubmitConfirm = confirm("현재 민원을 취하 처리하시겠습니까?");

if(SubmitConfirm==true) {
	val.submit();
}

}

//금리/수수료 비교공시 ########################################################################

function CompareBankCheckAll() {

	var BankName_length = $("input[name='BankName']").length;

	for(i=0;i<BankName_length;i++) {
		if($("#BankAll").is(":checked")==true) {
			$("input[name='BankName']:eq("+i+")").prop('checked',true);
		}else{
			$("input[name='BankName']:eq("+i+")").prop('checked',false);
		}
	}

}

function CompareBankCheckEA() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = 0;
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			checked_value = checked_value + 1;
		}
	}

	if(checked_value==BankName_length) {
		$("#BankAll").prop('checked',true);
	}else{
		$("#BankAll").prop('checked',false);
	}

}

//수신상품금리비교++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function ReceivingCateNameSelect(i,goods) {

	$($("a[name='cate_name']")).not("a[name='cate_name']:eq("+i+")").removeClass("show");
	$("a[name='cate_name']:eq("+i+")").addClass("show");

	$("#goods").val(goods);

	$("#SearchResult").html("");

}


function ReceivingSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/compare/receiving_search_result.php",
	{ 'goods': $("#goods").val(),
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function ReceivingExplToggle(i) {

	var row = $("tr[id='Goods_Text_TR']:eq("+i+")");
	row.toggle();
	var cell = $("td[id='OpenBtn']:eq("+i+")");
	var link = cell.find('a');
	// 상품 식별 부분은 유지하고 끝의 보기/닫기 동사만 교체
	var base = (link.attr('aria-label') || '').replace(/(보기|닫기)\s*$/, '');
	if (row.css('display') == 'none') {
		cell.find('span').attr('class', 'btnTableIn_view01');
		link.text('보기').attr('aria-expanded', 'false').attr('aria-label', base + '보기');
	} else {
		cell.find('span').attr('class', 'btnTableIn_close01');
		link.text('닫기').attr('aria-expanded', 'true').attr('aria-label', base + '닫기');
	}

}

function ReceivingExplToggleMid(i, t) {

	$("tr[id='Goods_Text_TR']:eq("+i+")").toggle();

	if($("tr[id='Goods_Text_TR']:eq("+i+")").css("display") == "none" ) {
		$("td[id='OpenBtn']:eq("+i+")").html('<span class="btnTableIn_view01"><a href="Javascript:ReceivingExplToggleMid('+i+', '+t+')">상세보기</a></span>');
		$("td[id='OpenTr']:eq("+t+")").attr('rowspan', '4');
		
	}else{
		$("td[id='OpenBtn']:eq("+i+")").html('<span class="btnTableIn_close01"><a href="Javascript:ReceivingExplToggleMid('+i+', '+t+')">닫기</a></span>');
		$("td[id='OpenTr']:eq("+t+")").attr('rowspan', '5');
	}

}
 

function ReceivingDepositCateNameSelect(i,goods) {

	$($("a[name='cate_name']")).not("a[name='cate_name']:eq("+i+")").removeClass("show");
	$("a[name='cate_name']:eq("+i+")").addClass("show");

	$("#goods").val(goods);

	var SortName = "";

	if(goods==1) {
		SortName = '<select name="sort_name" id="sort_name" class="wid200" title="첫번째 정렬방식 선택">';		
		SortName += '<option value="BANK_HNAME">은행이름</option>';
		SortName += '<option value="GOODS_OPT_1">1개월</option>';
		SortName += '<option value="GOODS_OPT_2">3개월</option>';
		SortName += '<option value="GOODS_OPT_3">6개월</option>';
		SortName += '<option value="GOODS_OPT_4">12개월</option>';
		SortName += '<option value="GOODS_OPT_5">24개월</option>';
		SortName += '<option value="GOODS_OPT_6">36개월</option>';
		SortName += '</select>';
	}
	if(goods==3) {
		SortName = '<select name="sort_name" id="sort_name" class="wid200" title="첫번째 정렬방식 선택">';
		SortName += '<option value="BANK_SORT">사원은행</option>';
		SortName += '<option value="BANK_HNAME">은행이름</option>';
		SortName += '<option value="GOODS_OPT_3">6개월</option>';
		SortName += '<option value="GOODS_OPT_4">12개월</option>';
		SortName += '<option value="GOODS_OPT_5">24개월</option>';
		SortName += '<option value="GOODS_OPT_6">36개월</option>';
		SortName += '<option value="GOODS_OPT_7">48개월</option>';
		SortName += '<option value="GOODS_OPT_8">60개월</option>';
		SortName += '</select>';
	}
	if(goods==7) {
		SortName = '<select name="sort_name" id="sort_name" class="wid200" title="첫번째 정렬방식 선택">';
		SortName += '<option value="BANK_SORT">사원은행</option>';
		SortName += '<option value="BANK_HNAME">은행이름</option>';
		SortName += '<option value="GOODS_OPT_1">5백만</option>';
		SortName += '<option value="GOODS_OPT_2">5백만</option>';
		SortName += '<option value="GOODS_OPT_3">1천만</option>';
		SortName += '<option value="GOODS_OPT_4">3천만</option>';
		SortName += '<option value="GOODS_OPT_5">5천만</option>';
		SortName += '<option value="GOODS_OPT_6">1억</option>';
		SortName += '</select>';
	}
	if(goods==8) {
		SortName = '<select name="sort_name" id="sort_name" class="wid200" title="첫번째 정렬방식 선택">';
		SortName += '<option value="BANK_SORT">사원은행</option>';
		SortName += '<option value="BANK_HNAME">은행이름</option>';
		SortName += '<option value="GOODS_OPT_1">5천만</option>';
		SortName += '<option value="GOODS_OPT_2">5천만</option>';
		SortName += '<option value="GOODS_OPT_3">1억</option>';
		SortName += '<option value="GOODS_OPT_4">5억</option>';
		SortName += '<option value="GOODS_OPT_5">10억</option>';
		SortName += '</select>';
	}

        if(goods==9) {
                SortName = '<select name="sort_name" id="sort_name" class="wid200" title="첫번째 정렬방식 선택">';
                SortName += '<option value="BANK_HNAME">은행이름</option>';
                SortName += '<option value="GOODS_OPT_1">5천만</option>';
                SortName += '<option value="GOODS_OPT_2">5천만</option>';
                SortName += '<option value="GOODS_OPT_3">1억</option>';
                SortName += '<option value="GOODS_OPT_4">5억</option>';
                SortName += '<option value="GOODS_OPT_5">10억</option>';
                SortName += '</select>';
        }


	$("#SortNameHTML").html(SortName);

	$("#sort_state option:eq(0)").attr("selected","selected");

	$("#SearchResult").html("");

	
	$(".titleForGoodsVal").remove();
    if (goods === 3) {
        $("#titleBoxUl").append(`
						<p class="title titleForGoodsVal"><font color='#284679'>상품설명</font></p>
                        <li class="titleForGoodsVal">예금금리 관련 세부내용은 은행연합회 홈페이지 <a href="/compare/receiving.php" style="font-weight: bold; text-decoration: underline;">예금금리에 대한 이해</a> 코너 참조</li>
        `);
    }
	if (goods === 7 || goods === 8 ) {
        $("#titleBoxUl").append(`
						<p class="title titleForGoodsVal"><font color='#284679'>상품설명</font></p>
                        <li class="titleForGoodsVal">MMDA 관련 세부 내용은 은행연합회 홈페이지 <a href="/fingoods/new_receiving_2.php" style="font-weight: bold; text-decoration: underline;">저축성 예금</a> 코너 "MMDA" 참조</li>
                        <li class="titleForGoodsVal">예금금리 관련 세부내용은 은행연합회 홈페이지 <a href="/compare/receiving.php" style="font-weight: bold; text-decoration: underline;">예금금리에 대한 이해</a> 코너 참조</li>
        `);
    }
}

function copySelect (SourceSel, TargetSel) { // SELECT OPTION 복사
	var Source = document.getElementById(SourceSel);
	var Target = document.getElementById(TargetSel);	
	$("select#" + TargetSel + " option" ).remove();			
	for(i=0, k=Source.length; i <k ; i++) {
		Target.add(new Option(Source[i].text, Source[i].value, false, false));		
	}	
	Source.selectedIndex = -1; 		
}	

// 2020.01.05 3자리 단위마다 콤마 생성
function addCommas(x) {
	return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");	
}
// 2020.01.05 모든 콤마 제거
function removeCommas(x) {
	if(!x|| x.length ==0) return "";
	else return x.split(",").join("");
}
                 
                                  
function NewRetireMentCateNameSelect(i,goods) {
	
		 
        $($("a[name='cate_name']")).not("a[name='cate_name']:eq("+i+")").removeClass("show");
        $("a[name='cate_name']:eq("+i+")").addClass("show");

        $("#goods").val(goods);
        $("#SortNameHTML *").remove();

        var SortName = "";        
        
        		
		if(goods == 100) {
				SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
				SortName +="<span><select name='publishdate' id='publishdate' class='wid130' title='조회기준'></select></span>";
				SortName +="<span><BR><BR>퇴직연금 감독규정 시행세칙 제7조 제3항 제3호에 의해 2019년 기준 중장기수익률은 1월 마지막 영업일에 공시됩니다.<BR>2018년 기준 중장기 수익률은 [2019년 이전 공시 보기]를 통하여 확인할 수 있습니다.</span>";
				$("#SortNameHTML").html(SortName);
	       		copySelect("publishdate.100", "publishdate");	         	        
	    } else if(goods == 101) {
		    	SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
				SortName +="<span><select name='publishdate' id='publishdate' class='wid130' title='조회기준'></select></span>";
			    $("#SortNameHTML").html(SortName);
	        	copySelect("publishdate.101", "publishdate");	         
	    } else if(goods == 102) {	    		
	    		SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
				SortName +="<span><select name='publishdate' id='publishdate' class='wid130' title='조회기준'></select></span>";
				SortName +="<span><BR><BR>다른 퇴직연금사업자에 대한 원리금보장상품 제공현황</span>";
				$("#SortNameHTML").html(SortName);
	        	copySelect("publishdate.102", "publishdate");
	        
	    } else if(goods == 103) {
	        SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
	        SortName +="<span class='pr30'><select name='publishdate' id='publishdate' class='wid130' title='조회기준'></select></span>";
	        
	        SortName +="<span class='item01'><label for='type_cd'>가입자구분</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_1' value='1' /> <label for='type_cd_1'>확정급여형(DB)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_2' value='2' /> <label for='type_cd_2'>확정기여형(DC)</label></span> ";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_3' value='3' /> <label for='type_cd_3'>개인형IRP</label></span>";
	        
	        SortName +="<span class='item01'><label for='product_type'>상품유형</label></span>";
	        SortName +="<span class='pr30'><select name = 'product_type' id ='product_type' class='wid200' title='상품유형' ><option value='1'>은행 예적금</option><option value='2'>저축은행 예적금</option><option value='3'>우체국 예적금</option><option value='4'>금리연동형 보험</option><option value='5'>이율보증형 보험</option>";
	        SortName +="<option value='6'>정부보증채</option><option value='7'>원리금보장파생결합사채</option><option value='8'>환매조건부 매수계약</option><option value='9'>발행어음 및 표지어음</option></<select></span>";
					
			$("#SortNameHTML").html(SortName);
	        copySelect("publishdate.103", "publishdate");		        
	                
	    }else if(goods == 107) {
	        SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
	        SortName +="<span class='pr30'><select name='publishdate' id='publishdate' class='wid130' title='조회기준'></select></span>";
	        
	        SortName +="<span class='item01'><label for='type_cd'>가입자구분</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_1' value='1' /> <label for='type_cd_1'>확정급여형(DB)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_2' value='2' /> <label for='type_cd_2'>확정기여형(DC)</label></span> ";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_3' value='3' /> <label for='type_cd_3'>개인형IRP</label></span>";
	        
	        SortName +="<span class='item01'><label for='product_type'>상품유형</label></span>";
	        SortName +="<span class='pr30'><select name = 'product_type' id ='product_type' class='wid200' title='상품유형' ><option value='1'>은행 예적금</option><option value='2'>저축은행 예적금</option><option value='3'>우체국 예적금</option><option value='4'>금리연동형 보험</option><option value='5'>이율보증형 보험</option>";
	        SortName +="<option value='6'>정부보증채</option><option value='7'>원리금보장파생결합사채</option><option value='8'>환매조건부 매수계약</option><option value='9'>발행어음 및 표지어음</option></<select></span>";
					
			$("#SortNameHTML").html(SortName);
	        copySelect("publishdate.103", "publishdate");		        
	                
	    }
	     else if(goods == 115) {
	        //SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
	        SortName ="<span class='pr30' style='display:none'><select name='publishdate' id='publishdate' class='wid130' title='조회기준'></select></span>";
	        
	        SortName +="<span style = 'height:35px' class='item01'><label for='type_cd'>가입자구분</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_1' value='1' /> <label for='type_cd_1'>확정급여형(DB)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_2' value='2' /> <label for='type_cd_2'>확정기여형(DC)</label></span> ";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_3' value='3' /> <label for='type_cd_3'>기업형IRP</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_4' value='4' /> <label for='type_cd_4'>개인형IRP(가입자부담금)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_4X' value='4X' /> <label for='type_cd_4X'>개인형IRP(사용자부담금)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_5' value='5' /> <label for='type_cd_5'>표준형DC</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_6' value='6' /> <label for='type_cd_6'>연금전환특약</label></span><BR>";
	        
	        SortName +="<span style = 'height:35px'  class='item01'><label for='elapsed_year'>장기계약</label></span>";	        
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_1' value='1' /> <label for='elapsed_year_2'>1년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_2' value='2' /> <label for='elapsed_year_2'>2년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_3' value='3' /> <label for='elapsed_year_3'>3년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_4' value='4' /> <label for='elapsed_year_4'>4년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_5' value='5' /> <label for='elapsed_year_5'>5년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_6' value='6' /> <label for='elapsed_year_6'>6년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_7' value='7' /> <label for='elapsed_year_7'>7년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_8' value='8' /> <label for='elapsed_year_8'>8년</label></span><BR>";
	        
	        SortName +="<span  style = 'height:35px' style='width:80px' class='item01'><label for='save_money' >적립금액</label></span>";
	        SortName +="<span  style='width:150px' class='pr30'><input type='text' name ='save_money' id= 'save_money' maxLength='15' style='width:150px;text-align:right' placeholder='0원 초과 금액 입력' numberOnly>&nbsp; (정수로 입력)</span>";
	        SortName +="<span><BR><span style='font-size:15px;font-weight:bold'><font color='red'>*</font> 주의 사항 <font color='red'>*</font> </span> <BR>1. 본 사이트에서는 최신정보 제공을 위해 노력하고 있으나, 금융회사의 수수료율 등 거래조건이 수시로 변경되어 일시적으로 지연 공시될 수 있으므로 거래 전 반드시 해당 금융회사에 정확히 문의하시기 바랍니다.";
	        SortName +="<BR>2. 연간 예상 수수료는 사업자가 제출한 가입자별 수수료율을 바탕으로 예상되는 수수료 수준을 단순 산출할 것으로 상품가입에 따라 추가비용이 발생하는 등 실제 가입조건에 따라 수수료 수준이 상이할 수 있습니다. 사업자가 제공하는 할인 등의 정보는 조회화면의 상세내역을 통해 확인하시고 거래 전 반드시 해당 금융회사에 정확히 문의하시기 바랍니다.<span> ";	
	        						        					
			$("#SortNameHTML").html(SortName);
			
			$("input:text[numberOnly]").on("focus", function() { //숫자에 콤마 넣기
				var x = $(this).val();
				x = removeCommas(x);
				$(this).val(x);		
				 	
			}).on("focusout", function() {
				var x = $(this).val();
				 
				if(x && x.length > 0 ) {
					if(!$.isNumeric(x))  {						 
						x = x.replace(/[^0-9]/g,"");
					}					 
					x = addCommas(x);					
					$(this).val(x);
				}
			}).on("keyup", function() {				
				$(this).val( $(this).val().replace(/[^0-9]/g,"") );				
			});
			
	    }
        $("#sort_state option:eq(0)").attr("selected","selected");
        $("#SearchResult").html("");
}

function NewRetireMentCateNameSelect_imsi(i,goods) {
	
		 		//250716 웹접근성 수정
        //$($("a[name='cate_name']")).not("a[name='cate_name']:eq("+i+")").removeClass("show");
        $($("a[name='cate_name']")).not("a[name='cate_name']:eq("+i+")").removeClass("show").attr("aria-selected", "false");
        //$("a[name='cate_name']:eq("+i+")").addClass("show");
        $("a[name='cate_name']:eq("+i+")").addClass("show").attr("aria-selected", "true");;

        $("#goods").val(goods);
        $("#SortNameHTML *").remove();

        var SortName = "";        
        
        $("#Pt101PastHTML *").remove();
        var Pt101Past = "";    
        		
		if(goods == 100) {
				SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
				SortName +="<span><select name='publishdate' id='publishdate' class='wid150' title='조회기준'></select></span>";
				SortName +="<span><BR><BR >2018년 기준 중장기 수익률은 [2019년 이전 공시 보기]를 통하여 확인할 수 있습니다.</span>";
				SortName +="<span><BR>퇴직연금 감독규정 시행세칙 개정에 따라 중장기수익률은 25년 3분기부터 매 분기말 기준 공시됩니다.</span>";
				$("#SortNameHTML").html(SortName);
	       		copySelect("publishdate.100", "publishdate");	         	        
	    } else if(goods == 101) {
					// SortNameHTML (Desktop)
	        SortName +="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
	        SortName +="<span class='pr30'><select name='publishdate' id='publishdate' class='wid150' title='조회기준'></select></span>";
	        SortName +="<br class='desktop'>";
	        SortName +="<span style = 'height:35px'  class='item01'><label for='type_cd'><br>조회구분</label></span>";
					SortName +="<div class='desktop' style='display: inline-block'>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_1' value='1' onclick='javascript:checkTypeCd();/> <label for='type_cd_1'>수수료 항목별 비용부담률</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_2' value='2' onclick='javascript:checkTypeCd();/> <label for='type_cd_2'>[참고]펀드 판매보수 부담률</label></span> ";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_3' value='3' onclick='javascript:checkTypeCd();/> <label for='type_cd_3'>[참고] 원리금 비보장상품 대상 수수료 감면정책</label></span>";
			SortName +="</div>";

					SortName +="<div class='respond'>";
					SortName +="<select name='type_cd' id='type_cd' onclick='javascript:checkTypeCd(); title='조회구분'>";
					SortName +="<option value='' title='선택'>선택</option>"
					SortName +="<option value='1' title='수수료 항목별 비용부담률'>수수료 항목별 비용부담률</option>"
					SortName +="<option value='2' title='[참고]펀드 판매보수 부담률'>[참고]펀드 판매보수 부담률</option>"
					SortName +="<option value='3' title='[참고] 원리금 비보장상품 대상 수수료 감면정책'>[참고] 원리금 비보장상품 대상 수수료 감면정책</option>"
					SortName +="</select>"
					SortName +="</div>";
	        SortName +="<br class='desktop'>";
	        SortName +="<BR><BR>퇴직연금감독규정 시행세칙 개정에 따라 수수료 항목별 비용부담율은 2024년 기준부터 공시합니다.2019년 ~ 2023년 기준 자료는 ‘총비용부담률’로 공시합니다.<span> ";	

					Pt101Past = "<span class='btnArea'><a href='pt101past_popup.php' target='_blank' class='btn02'>2023년 ~ 2019년 공시 보기</a></span>";
					
					$("#SortNameHTML").html(SortName);
			    $("#Pt101PastHTML").html(Pt101Past);
	        	copySelect("publishdate.101", "publishdate");	         
	    } else if(goods == 102) {	    		
	    		SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
				SortName +="<span><select name='publishdate' id='publishdate' class='wid150' title='조회기준'></select></span>";
				SortName +="<span><BR><BR>다른 퇴직연금사업자에 대한 원리금보장상품 제공현황</span>";
				$("#SortNameHTML").html(SortName);
	        	copySelect("publishdate.102", "publishdate");
	        
	    } else if(goods == 103) {
					// SortNameHTML (Desktop)
	        SortName +="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
	        SortName +="<span class='pr30'><select name='publishdate' id='publishdate' class='wid150' title='조회기준'></select></span>";
	        SortName +="<span class='item01'><label for='type_cd'>가입자구분</label></span>";
					SortName +="<div class='desktop' style='display: inline-block'>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_1' value='1' onclick='javascript:checkTypeCd();/> <label for='type_cd_1'>확정급여형(DB)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_2' value='2' onclick='javascript:checkTypeCd();/> <label for='type_cd_2'>확정기여형(DC)</label></span> ";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_3' value='3' onclick='javascript:checkTypeCd();/> <label for='type_cd_3'>개인형IRP</label></span>";
			SortName +="</div>";

					SortName +="<div class='respond'>";
					SortName +="<select name='type_cd' id='type_cd' onclick='javascript:checkTypeCd(); title='가입자구분'>";
					SortName +="<option value='' title='선택'>선택</option>"
					SortName +="<option value='1' title='확정급여형(DB)'>확정급여형(DB)</option>"
					SortName +="<option value='2' title='확정기여형(DC)'>확정기여형(DC)</option>"
					SortName +="<option value='3' title='개인형IRP'>개인형IRP</option>"
					SortName +="</select>"
					SortName +="</div>";

			SortName +="<br class='desktop'>";
	        SortName +="<span class='item01' style='margin-top: 20px;'><label for='product_type'>상품유형</label></span>";
	        SortName +="<span class='pr30'><select name = 'product_type' id ='product_type' class='wid200' title='상품유형' ><option value='1'>은행 예적금</option><option value='2'>저축은행 예적금</option><option value='3'>우체국 예적금</option><option value='4'>금리연동형 보험</option><option value='5'>이율보증형 보험</option>";
	        SortName +="<option value='6'>정부보증채</option><option value='7'>원리금보장파생결합사채</option><option value='8'>환매조건부 매수계약</option><option value='9'>발행어음 및 표지어음</option></<select></span>";			
			$("#SortNameHTML").html(SortName);
	        copySelect("publishdate.103", "publishdate");		        
	        
        //수수료율
	    }else if(goods == 107) {

					// SortNameHTML (Desktop)
	        SortName +="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
	        SortName +="<span class='pr30'><select name='publishdate' id='publishdate' class='wid150' title='조회기준'></select></span>";	   	            
	        SortName +="<span class='item01'><label for='type_cd'>가입자구분</label></span>";
					SortName +="<div class='desktop' style='display: inline-block'>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_1' value='1' onclick='javascript:checkTypeCd();'/> <label for='type_cd_1'>확정급여형(DB)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_2' value='2' onclick='javascript:checkTypeCd();'/> <label for='type_cd_2'>확정기여형(DC)</label></span> ";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_3' value='3' onclick='javascript:checkTypeCd();'/> <label for='type_cd_3'>개인형IRP</label></span>";    			SortName +="</div>";

					SortName +="<div class='respond'>";
					SortName +="<select name='type_cd' id='type_cd' title='가입자구분'>";
					SortName +="<option value='' title='선택'>선택</option>"
					SortName +="<option value='1' title='확정급여형(DB)'>확정급여형(DB)</option>"
					SortName +="<option value='2' title='확정기여형(DC)'>확정기여형(DC)</option>"
					SortName +="<option value='3' title='기업형IRP'>개인형IRP</option>"
					SortName +="</select>"
					SortName +="</div>";

			    SortName +="<br class='desktop'>";
	        SortName +="<span class='item01' style='margin-top: 20px;'><label for='product_type'>상품유형</label></span>";   
	        /*
	        SortName +="<span class='pr30'><select name = 'product_type' id ='product_type' class='wid200' title='상품유형' ><option value='1'>주식형</option><option value='2'>주식혼합형</option><option value='3'>채권혼합형</option><option value='4'>채권형</option><option value='5'>기타</option></<select></span>";
			*/
			SortName +="<span class='pr30'><select name = 'product_type' id ='product_type' class='wid200' title='상품유형' ><option value='11'>주식형</option><option value='12'>주식혼합형</option><option value='13'>채권혼합형</option><option value='14'>채권형</option><option value='15'>기타형</option><option value='16'>부동산 집</option><option value='17'>특별자산</option><option value='18'>혼합</option><option value='21'>주식형(재간접)</option><option value='22'>혼합형(재간접)</option><option value='23'>채권혼합형(재간접)</option><option value='24'>채권형(재간접)</option><option value='25'>기타형(재간접)</option><option value='26'>부동산(재간접)</option><option value='27'>특별자산(재간접)</option><option value='28'>혼합(재간접)</option></<select></span>";
			$("#SortNameHTML").html(SortName);
	        copySelect("publishdate.107", "publishdate");		        
	       } else if(goods == 115) {

	        //SortName ="<span class='item01'><label for='publishdate'>조회 기준</label></span>";
	        SortName ="<span class='pr30' style='display:none'><select name='publishdate' id='publishdate' class='wid130' title='조회기준'></select></span>";
	        SortName +="<span style = 'height:35px' class='item01'><label for='type_cd'>가입자구분</label></span>";
					SortName +="<div class='desktop'>"
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_1' value='1' onclick='javascript:checkTypeCd();' /> <label for='type_cd_1'>확정급여형(DB)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_2' value='2' onclick='javascript:checkTypeCd();'  /> <label for='type_cd_2'>확정기여형(DC)</label></span> ";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_3' value='3' onclick='javascript:checkTypeCd();'  /> <label for='type_cd_3'>기업형IRP</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_4' value='4' onclick='javascript:checkTypeCd();'  /> <label for='type_cd_4'>개인형IRP(가입자부담금)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_4X' value='4X' onclick='javascript:checkTypeCd();'  /> <label for='type_cd_4X'>개인형IRP(사용자부담금)</label></span>";
	        SortName +="<span class='check'><input type='radio' name='type_cd' id='type_cd_5' value='5' onclick='javascript:checkTypeCd();'  /> <label for='type_cd_5'>표준형DC</label></span>";
	        SortName +="<span class='check''><input type='radio' name='type_cd' id='type_cd_6' value='6' onclick='javascript:checkTypeCd();'  /> <label for='type_cd_6'>연금전환특약</label></span>";
					SortName +="</div>"

					SortName +="<div class='respond'>";
					SortName +="<select name='type_cd' id='type_cd' onchange='javascript:changeTypeCd();' 'title='가입자구분'>";
					SortName +="<option value='' title='선택'>선택</option>"
					SortName +="<option value='1' title='확정급여형(DB)'>확정급여형(DB)</option>"
					SortName +="<option value='2' title='확정기여형(DC)'>확정기여형(DC)</option>"
					SortName +="<option value='3' title='기업형IRP'>기업형IRP</option>"
					SortName +="<option value='4' title='개인형IRP(가입자부담금)'>개인형IRP(가입자부담금)</option>"
					SortName +="<option value='4X' title='개인형IRP(사용자부담금)'>개인형IRP(사용자부담금)</option>"
					SortName +="<option value='5' title='표준형DC'>표준형DC</option>"
					SortName +="<option value='6' title='연금전환특약'>연금전환특약</option>"
					SortName +="</select>"
					SortName +="</div>"

	        SortName +="<br class='desktop'>";
					SortName +="<span style = 'height:35px'  class='item01'><label for='elapsed_year'>장기계약</label></span>";	        
					SortName +="<div class='desktop'>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_1' value='1' onclick='javascript:checkElapsedYear();'  /> <label for='elapsed_year_2'>1년 미만</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_3' value='3' onclick='javascript:checkElapsedYear();'  /> <label for='elapsed_year_3'>3년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_5' value='5' onclick='javascript:checkElapsedYear();'  /> <label for='elapsed_year_5'>5년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_7' value='7' onclick='javascript:checkElapsedYear();'  /> <label for='elapsed_year_7'>7년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_10' value='10' onclick='javascript:checkElapsedYear();'  /> <label for='elapsed_year_10'>10년</label></span>";
	        SortName +="<span class='check'><input type='radio' name='elapsed_year' id='elapsed_year_11' value='11' onclick='javascript:checkElapsedYear();'  /> <label for='elapsed_year_11'>10년 초과</label></span>";
					SortName +="</div>";

					SortName +="<div class='respond'>";
					SortName +="<select name='elapsed_year' id='elapsed_year' onchange='javascript:changeElapsedYear();' title='장기계약'>";
					SortName +="<option value='' title='선택'>선택</option>"
					SortName +="<option value='1' title='1년 미만'>1년 미만</option>"
					SortName +="<option value='3' title='3년'>3년</option>"
					SortName +="<option value='5' title='5년'>5년</option>"
					SortName +="<option value='7' title='7년'>7년</option>"
					SortName +="<option value='10' title='10년'>10년</option>"
					SortName +="<option value='11' title='10년 초과'>10년 초과</option>"
					SortName +="</select>"
					SortName +="</div>";

	        SortName +="<br class='desktop'>";
	        SortName +="<span  style = 'height:35px' style='width:80px' class='item01'><label for='save_money' >적립금액</label></span>";
	        SortName +="<span  style='width:150px' class='pr30'><input type='text' name ='save_money' id= 'save_money' maxLength='15' style='width:150px;text-align:right' placeholder='0원 초과 금액 입력' numberOnly>&nbsp; (정수로 입력)</span>";
	        SortName +="<span><BR><span style='font-size:15px;font-weight:bold'><font color='red'>*</font> 주의 사항 <font color='red'>*</font> </span> <BR>1. 본 사이트에서는 최신정보 제공을 위해 노력하고 있으나, 금융회사의 수수료율 등 거래조건이 수시로 변경되어 일시적으로 지연 공시될 수 있으므로 거래 전 반드시 해당 금융회사에 정확히 문의하시기 바랍니다.";
	        SortName +="<BR>2. 연간 예상 수수료는 사업자가 제출한 가입자별 수수료율을 바탕으로 예상되는 수수료 수준을 단순 산출할 것으로 상품가입에 따라 추가비용이 발생하는 등 실제 가입조건에 따라 수수료 수준이 상이할 수 있습니다. 사업자가 제공하는 할인 등의 정보는 조회화면의 상세내역을 통해 확인하시고 거래 전 반드시 해당 금융회사에 정확히 문의하시기 바랍니다.<span> ";	


	        						        					
			$("#SortNameHTML").html(SortName);
			
			$("input:text[numberOnly]").on("focus", function() { //숫자에 콤마 넣기
				var x = $(this).val();
				x = removeCommas(x);
				$(this).val(x);		
				 	
			}).on("focusout", function() {
				var x = $(this).val();
				 
				if(x && x.length > 0 ) {
					if(!$.isNumeric(x))  {						 
						x = x.replace(/[^0-9]/g,"");
					}					 
					x = addCommas(x);					
					$(this).val(x);
				}
			}).on("keyup", function() {				
				$(this).val( $(this).val().replace(/[^0-9]/g,"") );				
			});
			
	    }
	    if(goods == 101)
	    {
	    	$("#PageTitleArea").html("");
	    	}
        $("#sort_state option:eq(0)").attr("selected","selected");
        $("#SearchResult").html("");
}

//퇴직연금 수수료율 비교용
function changeTypeCd() {	

	//Mobile select box 선택시 PC radio 동기화 처리
	var sidx = $("#type_cd option").index( $("#type_cd option:selected"));	//모바일 선택 순서 (0 부터 시작)

	var cnt = 1;
	$("input[name='type_cd']").each(function() {
		if (sidx == cnt++) {
			$(this).prop("checked", true);											//PC 선택 순서
		}
	});
}

//퇴직연금 수수료율 비교용
function changeElapsedYear() {	

	//Mobile select box 선택시 PC radio 동기화 처리
	var sidx = $("#elapsed_year option").index( $("#elapsed_year option:selected"));	//모바일 선택 순서 (0 부터 시작)

	var cnt = 1;
	$("input[name='elapsed_year']").each(function() {
		if (sidx == cnt++) {
			$(this).prop("checked", true);											//PC 선택 순서
		}
	});
}

//퇴직연금 수수료율 비교용
function checkTypeCd() {		
	//PC radio 선택시 Mobile select box 동기화 처리
	var ridx = $("input[name='type_cd']").index( $("input[name='type_cd']:checked"));	//PC 선택 순서 (1 부터 시작)
		
	//Mobile select box 초기화 후 선택
	var sidx = ridx + 1;
	var cnt = 1;
	$("#type_cd").each(function() {
		$("#type_cd option:eq(" + cnt++ + ")").prop("selected", false);
	});
	$("#type_cd option:eq(" + sidx + ")").prop("selected", true);
}

//퇴직연금 수수료율 비교용
function checkElapsedYear() {		
	//PC radio 선택시 Mobile select box 동기화 처리
	var ridx = $("input[name='elapsed_year']").index( $("input[name='elapsed_year']:checked"));	//PC 선택 순서 (1 부터 시작)
		
	//Mobile select box 초기화 후 선택
	var sidx = ridx + 1;
	var cnt = 1;
	$("#elapsed_year").each(function() {
			$("#elapsed_year option:eq(" + cnt++ + ")").prop("selected", false);
	});
	$("#elapsed_year option:eq(" + sidx + ")").prop("selected", true);
}


function NewRetirementSearch222() { //2019.12.23 신퇴직연금공시.. popuplayer 사용 예

		 
        var BankName_length = $("input[name='BankName']").length;

        var checked_value = "";
        for(i=0;i<BankName_length;i++) {
                if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
                        if(!checked_value) {
                                checked_value = $("input[name='BankName']:eq("+i+")").val();
                        }else{
                                checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
                        }
                }
        } 
		
        if(checked_value=="") {
                alert("검색하려는 은행을 선택하세요.");
                return;
        } 
        
        var goods = $("#goods").val();
        var publishdate = $("#publishdate").val();
        var product_type  = $("#product_type").val();
        var type_cd       = "";
        var sort_name     = $("#sort_name").val();
        var sort_state    = $("#sort_state").val();
        var type_cd_checked = $('input:radio[name=type_cd]').is(':checked');
        
        if(goods=="103" && type_cd_checked == false) 
		{			
			alert("검색하려는 제도유형을 선택하세요.");
			return false;
		} else {
			type_cd = $(':radio[name="type_cd"]:checked').val();
		}
		 
        alert(checked_value);
        
        var currentWidth = $(window).width();
        var LocWidth = (currentWidth / 2);
        var body_width =  screen.width-20;
        var body_height =  $('html body').height()+100;

        $("div[id='SysBg_White']").css({
                "width": body_width,
                "height": body_height,
                "opacity":"0.4",
                "position": "absolute",
                "z-index":"99"
        }).show();

        $("div[id='Roading']").css({
                "top": "450px",
                "left": LocWidth-10,
                "opacity":"0.8",
                "position": "absolute",
                "z-index":"200"
        }).show();
		 
        var cols = "";
        var cols_length = $("#cols").length;

        if(cols_length>0) {
                cols = $("#cols").val();
        }
		

        $.post("/compare/new_retirement_search_result.php",
        { 'goods': goods,
                'str': checked_value,
                'publishdate': publishdate,
                'product_type': product_type,
                'type_cd': type_cd,
                'sort_name': sort_name,
                'sort_state': sort_state,
                'cols':cols
        },function(data,status){
                setTimeout(function(){
                        $("#DataResult").html(data);
                        //$('html, body').animate({ scrollTop : 270 }, 500);
                        $("div[id='Roading']").hide();
                        //$("div[id='SysBg_White']").hide();
                        $("div[id='DataResult']").css({
			                "top": "0px",
			                //"left": LocWidth-10,
			                "left": "0px",
			                "opacity":"1.0",
			                "position": "absolute",
			                "z-index":"1000"
        }).show();
                },500);
        });

}

function NewRetirementSearch() { //2019.12.23 신퇴직연금공시

		 
        var BankName_length = $("input[name='BankName']").length;

        var checked_value = "";
        for(i=0;i<BankName_length;i++) {
                if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
                        if(!checked_value) {
                                checked_value = $("input[name='BankName']:eq("+i+")").val();
                        }else{
                                checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
                        }
                }
        } 
		
        if(checked_value=="") {
                alert("검색하려는 은행을 선택하세요.");
                return;
        } 
        
        var goods = $("#goods").val();
        var publishdate = $("#publishdate").val();
        var product_type  = $("#product_type").val();
        var type_cd       = "";
        var sort_name     = $("#sort_name").val();
        var sort_state    = $("#sort_state").val();
        var type_cd_checked = $('input:radio[name=type_cd]').is(':checked');
        var elapsed_year = "";
        var elapsed_year_checked = $('input:radio[name=elapsed_year]').is(':checked');
        var save_money    = $("#save_money").val();
 
         if(goods=="101" ) 
        {			
			//alert(type_cd_checked);
        	if (type_cd_checked == false) {
				type_cd = $("#type_cd option:selected").val();
				if (type_cd == "") {				
					alert("검색하려는 조회구분을 선택하세요.");
					return false;
				}
			} else {
				type_cd = $(':radio[name="type_cd"]:checked').val();
				//alert("type_cd = " + type_cd);
			}
		}
		                      
        if(goods=="103" ) 
        {			
			//alert(type_cd_checked);
        	if (type_cd_checked == false) {
				type_cd = $("#type_cd option:selected").val();
				if (type_cd == "") {				
					alert("검색하려는 가입자구분을 선택하세요.");
					return false;
				}
			} else {
				type_cd = $(':radio[name="type_cd"]:checked').val();
				//alert("type_cd = " + type_cd);
			}
		}
		
        if(goods=="107" ) 
        {			
			//alert(type_cd_checked);
        	if (type_cd_checked == false) {
				type_cd = $("#type_cd option:selected").val();
				if (type_cd == "") {				
					alert("검색하려는 가입자구분을 선택하세요.");
					return false;
				}
			} else {
				type_cd = $(':radio[name="type_cd"]:checked').val();
				//alert("type_cd = " + type_cd);
			}
		}		 
		
		if(goods=="115") 
		{
			if(type_cd_checked == false) 
			{			
				type_cd = $("#type_cd option:selected").val();
				if (type_cd == "") {	
					alert("검색하려는 가입자구분을 선택하세요.");
					return false;
				}
			} else {
				type_cd = $(':radio[name="type_cd"]:checked').val();
			}
			
			if(elapsed_year_checked == false) 
			{		
				elapsed_year = $("#elapsed_year option:selected").val();
				if (elapsed_year == "") {			
					alert("검색하려는 장기계약 기간(년)을 선택하세요.");
					return false;
				}
			} else {
				elapsed_year = $(':radio[name="elapsed_year"]:checked').val();
			}
			//type_cd = $(':radio[name="type_cd"]:checked').val();
			//elapsed_year = $(':radio[name="elapsed_year"]:checked').val();
			
			if(save_money== null || save_money==""  || save_money=="0") {
        		alert("적립금액을 입력하세요.(0원 입력 불가)");
            	return;
        	}
        	save_money = save_money.replace(/,/gi,'');			

		} 
		
        
        var currentWidth = $(window).width();
        var LocWidth = (currentWidth / 2);
        var body_width =  screen.width-20;
        var body_height =  $('html body').height()+100;

        $("div[id='SysBg_White']").css({
                "width": body_width,
                "height": body_height,
                "opacity":"0.4",
                "position": "absolute",
                "z-index":"99"
        }).show();

        $("div[id='Roading']").css({
                "top": "450px",
                "left": LocWidth-10,
                "opacity":"0.8",
                "position": "absolute",
                "z-index":"200"
        }).show();
		 
        var cols = "";
        var cols_length = $("#cols").length;

        if(cols_length>0) {
                cols = $("#cols").val();
        }
		

        $.post("/compare/new_retirement_search_result.php",
        { 'goods': goods,
                'str': checked_value,
                'publishdate': publishdate,
                'product_type': product_type,
                'type_cd': type_cd,
                'elapsed_year': elapsed_year,
                'save_money': save_money,                                
                'sort_name': sort_name,
                'sort_state': sort_state,
                'cols':cols
        },function(data,status){
                setTimeout(function(){
                        $("#SearchResult").html(data);
                        $('html, body').animate({ scrollTop : 270 }, 500);
                        $("div[id='Roading']").hide();
                        $("div[id='SysBg_White']").hide();
                },500);
        });

}

function NewRetirementSearch2() { //2019.12.23 신퇴직연금공시

		 
        var BankName_length = $("input[name='BankName']").length;

        var checked_value = "";
        for(i=0;i<BankName_length;i++) {
                if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
                        if(!checked_value) {
                                checked_value = $("input[name='BankName']:eq("+i+")").val();
                        }else{
                                checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
                        }
                }
        } 
		
        if(checked_value=="") {
                alert("검색하려는 은행을 선택하세요.");
                return;
        } 
        
        var goods = $("#goods").val();
        var publishdate = $("#publishdate").val();
        var product_type  = $("#product_type").val();
        var type_cd       = "";
        var sort_name     = $("#sort_name").val();
        var sort_state    = $("#sort_state").val();
        var type_cd_checked = $('input:radio[name=type_cd]').is(':checked');
        var elapsed_year = "";
        var elapsed_year_checked = $('input:radio[name=elapsed_year]').is(':checked');
        var save_money    = $("#save_money").val();
                       
        if(goods=="103" ) 
        {			
        	if (type_cd_checked == false) {
				alert("검색하려는 제도유형을 선택하세요.");
				return false;
			} else {
				type_cd = $(':radio[name="type_cd"]:checked').val();
			}
		} 
		
		if(goods=="115") 
		{
			if(type_cd_checked == false) 
			{			
				alert("검색하려는 제도유형을 선택하세요.");
				return false;
			}
			if(elapsed_year_checked == false) 
			{			
				alert("검색하려는 장기계약 기간(년)을 선택하세요.");
				return false;
			} 
			type_cd = $(':radio[name="type_cd"]:checked').val();
			elapsed_year = $(':radio[name="elapsed_year"]:checked').val();
			
			if(save_money== null || save_money==""  || save_money=="0") {
        		alert("적립금액을 입력하세요.(0원 입력 불가)");
            	return;
        	}
        	save_money        = save_money.replace(/,/gi,'');			
		} 
		
        
        var currentWidth = $(window).width();
        var LocWidth = (currentWidth / 2);
        var body_width =  screen.width-20;
        var body_height =  $('html body').height()+100;

        $("div[id='SysBg_White']").css({
                "width": body_width,
                "height": body_height,
                "opacity":"0.4",
                "position": "absolute",
                "z-index":"99"
        }).show();

        $("div[id='Roading']").css({
                "top": "450px",
                "left": LocWidth-10,
                "opacity":"0.8",
                "position": "absolute",
                "z-index":"200"
        }).show();
		 
        var cols = "";
        var cols_length = $("#cols").length;

        if(cols_length>0) {
                cols = $("#cols").val();
        }
		

        $.post("/compare/new_retirement_search_result2.php",
        { 'goods': goods,
                'str': checked_value,
                'publishdate': publishdate,
                'product_type': product_type,
                'type_cd': type_cd,
                'elapsed_year': elapsed_year,
                'save_money': save_money,                                
                'sort_name': sort_name,
                'sort_state': sort_state,
                'cols':cols
        },function(data,status){
                setTimeout(function(){
                        $("#SearchResult").html(data);
                        $('html, body').animate({ scrollTop : 270 }, 500);
                        $("div[id='Roading']").hide();
                        $("div[id='SysBg_White']").hide();
                },500);
        });

}

function PensionSavingCateNameSelect(i,goods) {

        $($("a[name='cate_name']")).not("a[name='cate_name']:eq("+i+")").removeClass("show");
        $("a[name='cate_name']:eq("+i+")").addClass("show");

        $("#goods").val(goods);

        var SortName = "";

        if(goods==1) {
                $("#retrieve_condition").show();
                $("#outline1").show();
                $("#outline2").hide();
                SortName = '<select name="sort_name" id="sort_name" class="wid200" title="첫번째 정렬방식 선택">';
                SortName += '<option value="BANK_HNAME">은행이름</option>'
                SortName += '</select>';
        }
        if(goods==3) {
                $("#retrieve_condition").hide();
                $("#outline2").show();
                $("#outline1").hide();
                SortName = '<select name="sort_name" id="sort_name" class="wid200" title="첫번째 정렬방식 선택">';
                SortName += '<option value="BANK_HNAME">은행이름</option>';
                SortName += '</select>';
        }

        $("#SortNameHTML").html(SortName);

        $("#sort_state option:eq(0)").attr("selected","selected");

        $("#SearchResult").html("");

}


function AnnouncMembmerCateNameSelect(i,goods) {

        $($("a[name='cate_name']")).not("a[name='cate_name']:eq("+i+")").removeClass("show");
        $("a[name='cate_name']:eq("+i+")").addClass("show");

        $("#goods").val(goods);

        var SortName = "";

        if(goods==1) {
                $("#itemAreaDiv").show();
                $("#itemAreaDiv2").hide();
                //$("#itemAreaSearch").show();
                //$("#itemAreaSearch2").hide();
                
        }
        if(goods==2) {
        	      $("#itemAreaDiv").show();
                $("#itemAreaDiv2").hide();  
                //$("#itemAreaSearch").show();
                //$("#itemAreaSearch2").hide();              
        }
        
        if(goods==3) {
                $("#retrieve_condition").hide();
                $("#itemAreaDiv2").show();
                $("#itemAreaDiv").hide();
                //$("#itemAreaSearch2").show();
                //$("#itemAreaSearch").hide();
                
        }

        $("#SortNameHTML").html(SortName);

        $("#sort_state option:eq(0)").attr("selected","selected");

        $("#SearchResult").html("");

}

function ReceivingDepositSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var goods = $("#goods").val();
	var sort_name = $("#sort_name").val();
	var sort_state = $("#sort_state").val();
  var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
  
	var cols = "";
	var cols_length = $("#cols").length;

	if(cols_length>0) {
		cols = $("#cols").val();
	}


	$.post("/compare/receiving_deposit_search_result.php",
	{ 'goods': goods,
		'str': checked_value,
		'sort_name': sort_name,
		'sort_state': sort_state,
		'JOIN_METHOD': JOIN_METHOD,
		'cols':cols
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function PensionSavingSearch() {

        var BankName_length = $("input[name='BankName']").length;

        var checked_value = "";
        for(i=0;i<BankName_length;i++) {
                if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
                        if(!checked_value) {
                                checked_value = $("input[name='BankName']:eq("+i+")").val();
                        }else{
                                checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
                        }
                }
        }

        if(checked_value=="") {
                alert("검색하려는 은행을 선택하세요.");
                return;
        }

        var currentWidth = $(window).width();
        var LocWidth = (currentWidth / 2);
        var body_width =  screen.width-20;
        var body_height =  $('html body').height()+100;

        $("div[id='SysBg_White']").css({
                "width": body_width,
                "height": body_height,
                "opacity":"0.4",
                "position": "absolute",
                "z-index":"99"
        }).show();

        $("div[id='Roading']").css({
                "top": "450px",
                "left": LocWidth-10,
                "opacity":"0.8",
                "position": "absolute",
                "z-index":"200"
        }).show();

        var goods = $("#goods").val();
        var sort_name = $("#sort_name").val();
        var sort_state = $("#sort_state").val();
        
        var year   = $("#year").val();
        var month  = $("#month").val();
        var saleok = $("#saleok").val();
        var principalgurantee  = $("#principalgurantee").val();
        var withdraw  = $("#withdraw").val();
        var chargestructure  = $("#chargestructure").val();
        var rcvperiod  = $("#rcvperiod").val();
        var pastyear   = $("#pastyear").val(); 


        var cols = "";
        var cols_length = $("#cols").length;

        if(cols_length>0) {
                cols = $("#cols").val();
        }


        $.post("/compare/pension_saving_search_result.php",
        { 'goods': goods,
                'str': checked_value,
                'year': year,
                'month': month,
                'saleok': saleok,
                'principalgurantee': principalgurantee,
                'withdraw': withdraw,
                'chargestructure': chargestructure,
                'rcvperiod': rcvperiod,
                'sort_state': sort_state,
                'pastyear': pastyear,
                'cols':cols
        },function(data,status){
                setTimeout(function(){
                        $("#SearchResult").html(data);
                        $('html, body').animate({ scrollTop : 270 }, 500);
                        $("div[id='Roading']").hide();
                        $("div[id='SysBg_White']").hide();
                },500);
        });

}

function PensionSavingSearch_new() {

        var BankName_length = $("input[name='BankName']").length;

        var checked_value = "";
        for(i=0;i<BankName_length;i++) {
                if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
                        if(!checked_value) {
                                checked_value = $("input[name='BankName']:eq("+i+")").val();
                        }else{
                                checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
                        }
                }
        }

        if(checked_value=="") {
                alert("검색하려는 은행을 선택하세요.");
                return;
        }

        var currentWidth = $(window).width();
        var LocWidth = (currentWidth / 2);
        var body_width =  screen.width-20;
        var body_height =  $('html body').height()+100;

        $("div[id='SysBg_White']").css({
                "width": body_width,
                "height": body_height,
                "opacity":"0.4",
                "position": "absolute",
                "z-index":"99"
        }).show();

        $("div[id='Roading']").css({
                "top": "450px",
                "left": LocWidth-10,
                "opacity":"0.8",
                "position": "absolute",
                "z-index":"200"
        }).show();

        var goods = $("#goods").val();
        var sort_name = $("#sort_name").val();
        var sort_state = $("#sort_state").val();
        
        var year   = $("#year").val();
        var month  = $("#month").val();
        var rcvperiod  = $("#rcvperiod").val();


        var cols = "";
        var cols_length = $("#cols").length;

        if(cols_length>0) {
                cols = $("#cols").val();
        }


        $.post("/compare/pension_saving_search_result_new.php",
        { 'goods': goods,
                'str': checked_value,
                'year': year,
                'month': month,
                'rcvperiod': rcvperiod,
                'sort_state': sort_state,
                'cols':cols
        },function(data,status){
                setTimeout(function(){
                        $("#SearchResult").html(data);
                        $('html, body').animate({ scrollTop : 270 }, 500);
                        $("div[id='Roading']").hide();
                        $("div[id='SysBg_White']").hide();
                },500);
        });

}


function ReceivingArmySearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var ordertype = $("#ordertype").val();


	$.post("/compare/receiving_army_search_result.php",
	{ 'ordertype': ordertype,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function ReceivingArmySearch_new() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var ordertype = $("#ordertype").val();


	$.post("/compare/receiving_army_search_result_new.php",
	{ 'ordertype': ordertype,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function ReceivingYouthSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var ordertype = $("#ordertype").val();


	$.post("/compare/receiving_youth_leap_search_result_new.php",
	{ 'ordertype': ordertype,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function ReceivingYouthSearchNew() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var ordertype = $("#ordertype").val();


	$.post("/compare/receiving_youth_leap_search_result.php",
	{ 'ordertype': ordertype,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function ReceivingYouthNewSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var ordertype = $("#ordertype").val();


	$.post("/compare/receiving_youth_search_result_new.php",
	{ 'ordertype': ordertype,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function ReceivingYoungSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var ordertype = $("#ordertype").val();


	$.post("/compare/receiving_young_search_result.php",
	{ 'ordertype': ordertype,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function ReceivingYouthFutureSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
		
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var ordertype = $("#ordertype").val();


	$.post("/compare/receiving_youth_future_search_result.php",
	{ 'ordertype': ordertype,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

//수신상품금리비교++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

//대출상품금리비교++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function LoanHouseholdSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}

	var detail_length = $("input[name='detail']").length;
	var detail = $("input[name='detail']:checked").val();
	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		detail = $("#detail option:selected").val();
		if(detail=="") {
			alert("상세구분을 선택하세요.");
			return;
		}
	}
	

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	//var detail = $("input[name='detail']:checked").val();

	var ym = year + month;
	

	
	if(ym<201509){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_2.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 201907){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015.9월 ~ 2019.6월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_5.php";
		}else{
			Form1.reset();
		}
	}else if(ym > 202101){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2021.2월 이후)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_new.php";
		}else{
			Form1.reset();
		}
	}
	
		




	$.post("/compare/loan_household_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanHouseholdNewSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {		
			alert("대출종류를 선택하세요.");
			return;
		}
	}
	
	var detail_length = $("input[name='detail']").length;
	var detail = $("input[name='detail']:checked").val();
	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		detail = $("#detail option:selected").val();
		if(detail=="") {	
			alert("상세구분을 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	
	//var opt_1 = $("input[name='opt_1']:checked").val();
	//var detail = $("input[name='detail']:checked").val();

	var ym = year + month;

	
	if(ym<201509){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_2.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 201907){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015.9월 ~ 2019.6월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_5.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 202102){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2019.7월 ~ 2021.1월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household.php";
		}else{
			Form1.reset();
		}
	}
	
	$.post("/compare/loan_household_new_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanHouseholdNewSearch_lys() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;

	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		alert("대출종류를 선택하세요.");
		return;
	}

	var detail_length = $("input[name='detail']").length;

	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		alert("상세구분을 선택하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	var opt_1 = $("input[name='opt_1']:checked").val();
	var detail = $("input[name='detail']:checked").val();

	var ym = year + month;
	

	
	if(ym<201509){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_2.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 201907){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015.9월 ~ 2019.6월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_5.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 202102){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2019.7월 ~ 2021.1월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household.php";
		}else{
			Form1.reset();
		}
	}

	$.post("/compare/loan_household_new_search_result_lys.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

//가계대출금리
function LoanHouseholdNewSearch_cur() {

	var BankName_length = $("input[name='BankName']").length;
	var year = $("#year").val();
	var month = $("#month").val();
	var opt_1 = $("input[name='opt_1']:checked").val();
	var detail = $("input[name='detail']:checked").val();
	var select_new_balance = $("input[name='select_new_balance']:checked").val();

	var ym = year + month;
	
	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_1_length = $("input[name='opt_1']").length;
	
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		} 
	}
	
	if(opt_1_checked_value==0) {	
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		} 
	}

	var detail_length = $("input[name='detail']").length;
	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		detail = $("#detail option:selected").val();
		if (detail == "") {
			alert("상세구분을 선택하세요.");
			return;
		}
	}
		
	var select_new_balance_length = $("input[name='select_new_balance']").length;

	var select_new_balance_checked_value = 0;
	for(i=0;i<select_new_balance_length;i++) {
		if($("input[name='select_new_balance']:eq("+i+")").is(":checked")==true) {
			select_new_balance_checked_value = select_new_balance_checked_value + 1;
		}
	}

	if(select_new_balance_checked_value==0) {
		select_new_balance = $("#select_new_balance option:selected").val();
		if(select_new_balance=="") {
			alert("공시기준을 선택하세요.");
			return;
		}
	}	

		if(ym < 202307)
		{
			if(select_new_balance=="2") {
		alert("잔액기준은 2023년 7월 공시부터 조회 가능합니다.");
		return;
						}
						
			if(opt_1=="5" || opt_1=="6" ) {
		alert("전세대출,가계대출은 2023년 7월 공시부터 조회가능합니다.");
		return;
						}						
						
			}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	
	if(ym<201509){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_2.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 201907){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015.9월 ~ 2019.6월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_5.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 202102){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2019.7월 ~ 2021.1월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household.php";
		}else{
			Form1.reset();
		}
	}
	
	//alert(year);
	//alert(month);
	//alert(opt_1);
	//alert(detail);
	//alert(select_new_balance);

	if(ym < 202307)
	{
			$.post("/compare/loan_household_new_search_result_lys.php",
			{ 'year': year,
				'month': month,
				'opt_1': opt_1,
				'detail': detail,
				'str': checked_value
			},function(data,status){
				setTimeout(function(){
					//console.log(data);
					$("#SearchResult").html(data);
					$('html, body').animate({ scrollTop : 270 }, 500);
					$("div[id='Roading']").hide();
					$("div[id='SysBg_White']").hide();
				},500);
			}); 		
		}
	else
		{
				if(select_new_balance =="1")
				{
						$.post("/compare/loan_household_new_search_result_new.php",
						{ 'year': year,
							'month': month,
							'opt_1': opt_1,
							'detail': detail,
							'str': checked_value,
							'select_new_balance': select_new_balance
						},function(data,status){
							setTimeout(function(){
								//console.log(data);
								$("#SearchResult").html(data);
								$('html, body').animate({ scrollTop : 270 }, 500);
								$("div[id='Roading']").hide();
								$("div[id='SysBg_White']").hide();
							},500);
						}); 
				}
				else
				{
						$.post("/compare/loan_household_new_search_result_cur.php",
						{ 'year': year,
							'month': month,
							'opt_1': opt_1,
							'detail': detail,
							'str': checked_value,
							'select_new_balance': select_new_balance
						},function(data,status){
							
							setTimeout(function(){
								//console.log(data);
								$("#SearchResult").html(data);
								$('html, body').animate({ scrollTop : 270 }, 500);
								$("div[id='Roading']").hide();
								$("div[id='SysBg_White']").hide();
							},500);
						}); 		
					}			
			}

	
}

function LoanHouseholdNewImsiSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;

	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		alert("대출종류를 선택하세요.");
		return;
	}

	var detail_length = $("input[name='detail']").length;

	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		alert("상세구분을 선택하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	var opt_1 = $("input[name='opt_1']:checked").val();
	var detail = $("input[name='detail']:checked").val();

	var ym = year + month;
	

	
	if(ym<201509){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_2.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 201907){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015.9월 ~ 2019.6월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_5.php";
		}else{
			Form1.reset();
		}
	}else if(ym < 202102){
		MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2019.7월 ~ 2021.1월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household.php";
		}else{
			Form1.reset();
		}
	}

	$.post("/compare/loan_household_new_imsi_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanHouseholdSearch_fss() {

        var BankName_length = $("input[name='BankName']").length;

        var checked_value = "";
        for(i=0;i<BankName_length;i++) {
                if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
                        if(!checked_value) {
                                checked_value = $("input[name='BankName']:eq("+i+")").val();
                        }else{
                                checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
                        }
                }
        }

        if(checked_value=="") {
                alert("검색하려는 은행을 선택하세요.");
                return;
        }


        var opt_1_length = $("input[name='opt_1']").length;

        var opt_1_checked_value = 0;
        for(i=0;i<opt_1_length;i++) {
                if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
                        opt_1_checked_value = opt_1_checked_value + 1;
                }
        }

        if(opt_1_checked_value==0) {
                alert("대출종류를 선택하세요.");
                return;
        }

        var detail_length = $("input[name='detail']").length;

        var detail_checked_value = 0;
        for(i=0;i<detail_length;i++) {
                if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
                        detail_checked_value = detail_checked_value + 1;
                }
        }

        if(detail_checked_value==0) {
                alert("상세구분을 선택하세요.");
                return;
        }


        var currentWidth = $(window).width();
        var LocWidth = (currentWidth / 2);
        var body_width =  screen.width-20;
        var body_height =  $('html body').height()+100;

        $("div[id='SysBg_White']").css({
                "width": body_width,
                "height": body_height,
                "opacity":"0.4",
                "position": "absolute",
                "z-index":"99"
        }).show();

        $("div[id='Roading']").css({
                "top": "450px",
                "left": LocWidth-10,
                "opacity":"0.8",
                "position": "absolute",
                "z-index":"200"
        }).show();

        var year = $("#year").val();
        var month = $("#month").val();
        var opt_1 = $("input[name='opt_1']:checked").val();
        var detail = $("input[name='detail']:checked").val();

        var ym = year + month;



        if(ym<201509){
                MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
                if(MoveConfirm==true){
                        location.href="/compare/loan_household_2.php";
                }else{
                        Form1.reset();
                }
        }else if(ym < 201907){
                MoveConfirm = confirm("해당 검색은\n\n[은행별 비교공시(2015.9월 ~ 2019.6월)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
                if(MoveConfirm==true){
                        location.href="/compare/loan_household_5.php";
                }else{
                        Form1.reset();
                }
        }






        $.post("/compare/loan_household_search_resultfss.php",
        { 'year': year,
                'month': month,
                'opt_1': opt_1,
                'detail': detail,
                'str': checked_value
        },function(data,status){
                setTimeout(function(){
                        $("#SearchResult").html(data);
                        $('html, body').animate({ scrollTop : 270 }, 500);
                        $("div[id='Roading']").hide();
                        $("div[id='SysBg_White']").hide();
                },500);
        });

}


function LoanHouseholdSearchfix() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}

	var detail_length = $("input[name='detail']").length;
	var detail = $("input[name='detail']:checked").val();
	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		detail = $("#detail option:selected").val();
		if(detail=="") {
			alert("상세구분을 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	
	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	//var detail = $("input[name='detail']:checked").val();

	var ym = year + month;

	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_2.php";
		}else{
			Form1.reset();
		}
	}
	

//김수범
	$.post("/compare/loan_household_search_result_fix.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanHouseholdSearchfss() {

        var BankName_length = $("input[name='BankName']").length;

        var checked_value = "";
        for(i=0;i<BankName_length;i++) {
                if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
                        if(!checked_value) {
                                checked_value = $("input[name='BankName']:eq("+i+")").val();
                        }else{
                                checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
                        }
                }
        }

        if(checked_value=="") {
                alert("검색하려는 은행을 선택하세요.");
                return;
        }


        var opt_1_length = $("input[name='opt_1']").length;

        var opt_1_checked_value = 0;
        for(i=0;i<opt_1_length;i++) {
                if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
                        opt_1_checked_value = opt_1_checked_value + 1;
                }
        }

        if(opt_1_checked_value==0) {
                alert("대출종류를 선택하세요.");
                return;
        }

        var detail_length = $("input[name='detail']").length;

        var detail_checked_value = 0;
        for(i=0;i<detail_length;i++) {
                if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
                        detail_checked_value = detail_checked_value + 1;
                }
        }

        if(detail_checked_value==0) {
                alert("상세구분을 선택하세요.");
                return;
        }


        var currentWidth = $(window).width();
        var LocWidth = (currentWidth / 2);
        var body_width =  screen.width-20;
        var body_height =  $('html body').height()+100;

        $("div[id='SysBg_White']").css({
                "width": body_width,
                "height": body_height,
                "opacity":"0.4",
                "position": "absolute",
                "z-index":"99"
        }).show();

        $("div[id='Roading']").css({
                "top": "450px",
                "left": LocWidth-10,
                "opacity":"0.8",
                "position": "absolute",
                "z-index":"200"
        }).show();


        var year = $("#year").val();
        var month = $("#month").val();
        var opt_1 = $("input[name='opt_1']:checked").val();
        var detail = $("input[name='detail']:checked").val();

        var ym = year + month;

        if(ym<201509){
                MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
                if(MoveConfirm==true){
                        location.href="/compare/loan_household_2.php";
                }else{
                        Form1.reset();
                }
        }

        $.post("/compare/loan_household_search_result_fss.php",
        { 'year': year,
                'month': month,
                'opt_1': opt_1,
                'detail': detail,
                'str': checked_value
        },function(data,status){
                setTimeout(function(){
                        $("#SearchResult").html(data);
                        $('html, body').animate({ scrollTop : 270 }, 500);
                        $("div[id='Roading']").hide();
                        $("div[id='SysBg_White']").hide();
                },500);
        });

}



function LoanHouseholdSearchExpl(i) {
	$($("ul[name='Expl']")).not("ul[name='Expl']:eq("+i+")").hide();
	$("ul[name='Expl']:eq("+i+")").show();
}

function LoanHouseholdSearchExpl2(i) {
	$($("ul[name='Expl']")).not("ul[name='Expl']:eq("+i+")").hide();
	$("ul[name='Expl']:eq("+i+")").show();

	$($("li[name='Expl2']")).not("li[name='Expl2']:eq("+i+")").hide();
	$("li[name='Expl2']:eq("+i+")").show();
}

function LoanHouseholdSearch2() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}
	
	
	var detail_length = $("input[name='detail']").length;
	var detail = $("input[name='detail']:checked").val();
	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		detail = $("#detail option:selected").val();
		if(detail=="") {
			alert("상세구분을 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	//var detail = $("input[name='detail']:checked").val();
	
	var ym = year + month;
	
	if(ym>201508){
		MoveConfirm = confirm("2015년 9월 이후 검색은\n\n [은행별 비교공시(2015년 9월 이후)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household.php";
		}else{
			Form1.reset();
		}
	}


	$.post("/compare/loan_household_2_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanHouseholdSearch2_1_fix() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	
	var ym = year + month;
	
	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [금리구간별 취급비중(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_4.php";
		}else{
			Form1.reset();
		}
	}


	$.post("/compare/loan_household_3_search_result_fix.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function LoanHouseholdSearch2_1() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	
	var ym = year + month;
	
	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [금리구간별 취급비중(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_4.php";
		}else{
			Form1.reset();
		}
	}


	$.post("/compare/loan_household_3_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function LoanHouseholdSearch2_1_new() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;

	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		alert("대출종류를 선택하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	var opt_1 = $("input[name='opt_1']:checked").val();
	
	var ym = year + month;
	
	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [금리구간별 취급비중(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_4.php";
		}else{
			Form1.reset();
		}
	}


	$.post("/compare/loan_household_new_3_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanHouseholdSearch2_1_new_cur() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}
	

	var select_new_balance_length = $("input[name='select_new_balance']").length;
	var select_new_balance = $("input[name='select_new_balance']:checked").val();
	var select_new_balance_checked_value = 0;
	for(i=0;i<select_new_balance_length;i++) {
		if($("input[name='select_new_balance']:eq("+i+")").is(":checked")==true) {
			select_new_balance_checked_value = select_new_balance_checked_value + 1;
		}
	}

	if(select_new_balance_checked_value==0) {
		select_new_balance = $("#select_new_balance option:selected").val();
		if(select_new_balance=="") {
			alert("공시기준을 선택하세요.");
			return;
		}
	}	
	
	//var select_new_balance = $("input[name='select_new_balance']:checked").val();
	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	var ym = year + month;
	
		if(ym < 202307)
		{
			if(select_new_balance=="2") {
		alert("잔액기준은 2023년 7월 공시부터 조회 가능합니다.");
		return;
						}
						
			if(opt_1=="5" || opt_1=="6" ) {
		alert("전세대출,가계대출은 2023년 7월 공시부터 조회가능합니다.");
		return;
						}						
						
			}
				
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();


	
	
	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [금리구간별 취급비중(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_4.php";
		}else{
			Form1.reset();
		}
	}
	if(ym>= 202307)
	{
		if(select_new_balance =="1")
		{
				$.post("/compare/loan_household_new_3_search_result_new.php",
				{ 'year': year,
					'month': month,
					'opt_1': opt_1,
					'str': checked_value,
					'select_new_balance': select_new_balance
				},function(data,status){
					setTimeout(function(){
						$("#SearchResult").html(data);
						$('html, body').animate({ scrollTop : 270 }, 500);
						$("div[id='Roading']").hide();
						$("div[id='SysBg_White']").hide();
					},500);
				});		
			}
			else
				{
				$.post("/compare/loan_household_new_3_search_result_cur.php",
				{ 'year': year,
					'month': month,
					'opt_1': opt_1,
					'str': checked_value,
					'select_new_balance': select_new_balance
				},function(data,status){
					setTimeout(function(){
						$("#SearchResult").html(data);
						$('html, body').animate({ scrollTop : 270 }, 500);
						$("div[id='Roading']").hide();
						$("div[id='SysBg_White']").hide();
					},500);
				});						
					}		
		}
		else
			{
				$.post("/compare/loan_household_new_3_search_result.php",
				{ 'year': year,
					'month': month,
					'opt_1': opt_1,
					'str': checked_value
				},function(data,status){
					setTimeout(function(){
						$("#SearchResult").html(data);
						$('html, body').animate({ scrollTop : 270 }, 500);
						$("div[id='Roading']").hide();
						$("div[id='SysBg_White']").hide();
					},500);
				});					
				
				}



}


function LoanHouseholdSearch2_1_newImsi() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;

	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		alert("대출종류를 선택하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	var opt_1 = $("input[name='opt_1']:checked").val();
	
	var ym = year + month;
	
	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [금리구간별 취급비중(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_4.php";
		}else{
			Form1.reset();
		}
	}


	$.post("/compare/loan_household_new_3_imsi_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}




function LoanHouseholdSearch2_2() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	
	var ym = year + month;
	
	if(ym>201508){
		MoveConfirm = confirm("2015년 9월 이후 검색은\n\n [금리구간별 취급비중(2015년 9월 이후)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_household_3.php";
		}else{
			Form1.reset();
		}
	}


	$.post("/compare/loan_household_4_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function LoanSnmindustrySearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_0_length = $("input[name='opt_0']").length;

	var opt_0_checked_value = 0;
	for(i=0;i<opt_0_length;i++) {
		if($("input[name='opt_0']:eq("+i+")").is(":checked")==true) {
			opt_0_checked_value = opt_0_checked_value + 1;
		}
	}

	if(opt_0_checked_value==0) {
		alert("대출구분을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;

	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		alert("대출종류를 선택하세요.");
		return;
	}

	var detail_length = $("input[name='detail']").length;

	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		alert("상세구분을 선택하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	var opt_0 = $("input[name='opt_0']:checked").val();
	var opt_1 = $("input[name='opt_1']:checked").val();
	var detail = $("input[name='detail']:checked").val();
	
	var ym = year + month;
	
	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_snmindustry_2.php";
		}else{
			Form1.reset();
		}
	}


	$.post("/compare/loan_snmindustry_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_0': opt_0,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}
function LoanSnmindustrySearch_cur() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_0_length = $("input[name='opt_0']").length;
	var opt_0 = $("input[name='opt_0']:checked").val();
	var opt_0_checked_value = 0;
	for(i=0;i<opt_0_length;i++) {
		if($("input[name='opt_0']:eq("+i+")").is(":checked")==true) {
			opt_0_checked_value = opt_0_checked_value + 1;
		}
	}

	if(opt_0_checked_value==0) {
		opt_0 = $("#opt_0 option:selected").val();
		if(opt_0=="") {
			alert("대출구분을 선택하세요.");
			return;
		}
	}

	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}

	var detail_length = $("input[name='detail']").length;
	var detail = $("input[name='detail']:checked").val();
	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		detail = $("#detail option:selected").val();
		if(detail=="") {
			alert("상세구분을 선택하세요.");
			return;
		}
	}

	var select_new_balance_length = $("input[name='select_new_balance']").length;
	var select_new_balance = $("input[name='select_new_balance']:checked").val();
	var select_new_balance_checked_value = 0;
	for(i=0;i<select_new_balance_length;i++) {
		if($("input[name='select_new_balance']:eq("+i+")").is(":checked")==true) {
			select_new_balance_checked_value = select_new_balance_checked_value + 1;
		}
	}
	
	if(select_new_balance_checked_value==0) {
		select_new_balance = $("#select_new_balance option:selected").val();
		if(select_new_balance=="") {
			alert("공시기준을 선택하세요.");
			return;
		}
	}	
		
	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_0 = $("input[name='opt_0']:checked").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	//var detail = $("input[name='detail']:checked").val();
	//var select_new_balance = $("input[name='select_new_balance']:checked").val();
	var ym = year + month;
			
		if(ym < 202307)
		{
			if(select_new_balance=="2") {
		alert("잔액기준은 2023년 7월 공시부터 조회 가능합니다.");
		return;
						}		
					}
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();


	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_snmindustry_2.php";
		}else{
			Form1.reset();
		}
	}

	if(ym>202306)
	{
			$.post("/compare/loan_snmindustry_search_result_cur.php",
			{ 'year': year,
				'month': month,
				'opt_0': opt_0,
				'opt_1': opt_1,
				'detail': detail,
				'select_new_balance': select_new_balance,
				'str': checked_value
			},function(data,status){
				setTimeout(function(){
					$("#SearchResult").html(data);
					$('html, body').animate({ scrollTop : 270 }, 500);
					$("div[id='Roading']").hide();
					$("div[id='SysBg_White']").hide();
				},500);
			});		
		}
	else
		{
						$.post("/compare/loan_snmindustry_search_result.php",
						{ 'year': year,
							'month': month,
							'opt_0': opt_0,
							'opt_1': opt_1,
							'detail': detail,
							'str': checked_value
						},function(data,status){
							setTimeout(function(){
								$("#SearchResult").html(data);
								$('html, body').animate({ scrollTop : 270 }, 500);
								$("div[id='Roading']").hide();
								$("div[id='SysBg_White']").hide();
							},500);
						});				
			}


}


function LoanSnmindustrySearchfix() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_0_length = $("input[name='opt_0']").length;
	var opt_0 = $("input[name='opt_0']:checked").val();
	var opt_0_checked_value = 0;
	for(i=0;i<opt_0_length;i++) {
		if($("input[name='opt_0']:eq("+i+")").is(":checked")==true) {
			opt_0_checked_value = opt_0_checked_value + 1;
		}
	}

	if(opt_0_checked_value==0) {
		opt_0 = $("#opt_0 option:selected").val();
		if(opt_0=="") {
			alert("대출구분을 선택하세요.");
			return;
		}
	}


	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}

	var detail_length = $("input[name='detail']").length;
	var detail = $("input[name='detail']:checked").val();
	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		detail = $("#detail option:selected").val();
		if(detail=="") {
			alert("상세구분을 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_0 = $("input[name='opt_0']:checked").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	//var detail = $("input[name='detail']:checked").val();
	
	var ym = year + month;
	
	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_snmindustry_2.php";
		}else{
			Form1.reset();
		}
	}


	$.post("/compare/loan_snmindustry_search_result_fix.php",
	{ 'year': year,
		'month': month,
		'opt_0': opt_0,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanSnmindustrySearch_fix() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_0_length = $("input[name='opt_0']").length;

	var opt_0_checked_value = 0;
	for(i=0;i<opt_0_length;i++) {
		if($("input[name='opt_0']:eq("+i+")").is(":checked")==true) {
			opt_0_checked_value = opt_0_checked_value + 1;
		}
	}

	if(opt_0_checked_value==0) {
		alert("대출구분을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;

	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		alert("대출종류를 선택하세요.");
		return;
	}

	var detail_length = $("input[name='detail']").length;

	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		alert("상세구분을 선택하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	var opt_0 = $("input[name='opt_0']:checked").val();
	var opt_1 = $("input[name='opt_1']:checked").val();
	var detail = $("input[name='detail']:checked").val();
	
	var ym = year + month;
	
	if(ym<201509){
		MoveConfirm = confirm("2015년 8월 이전 검색은\n\n [은행별 비교공시(2015년 8월 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_snmindustry_2.php";
		}else{
			Form1.reset();
		}
	}

//수범
	$.post("/compare/loan_snmindustry_search_result_fix.php",
	{ 'year': year,
		'month': month,
		'opt_0': opt_0,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanSnmindustrySearch2() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}

	var detail_length = $("input[name='detail']").length;
	var detail = $("input[name='detail']:checked").val();
	var detail_checked_value = 0;
	for(i=0;i<detail_length;i++) {
		if($("input[name='detail']:eq("+i+")").is(":checked")==true) {
			detail_checked_value = detail_checked_value + 1;
		}
	}

	if(detail_checked_value==0) {
		detail = $("#detail option:selected").val();
		if(detail=="") {
			alert("상세구분을 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	//var detail = $("input[name='detail']:checked").val();

	var ym = year + month;
	
	if(ym>201508){
		MoveConfirm = confirm("2015년 9월 이후 검색은\n\n [은행별 비교공시(2015년 9월 이후)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="/compare/loan_snmindustry.php";
		}else{
			Form1.reset();
		}
	}

	$.post("/compare/loan_snmindustry_2_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_1': opt_1,
		'detail': detail,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanSnmindustrySearch3() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_0_length = $("input[name='opt_0']").length;

	var opt_0_checked_value = 0;
	for(i=0;i<opt_0_length;i++) {
		if($("input[name='opt_0']:eq("+i+")").is(":checked")==true) {
			opt_0_checked_value = opt_0_checked_value + 1;
		}
	}

	if(opt_0_checked_value==0) {
		alert("대출구분을 선택하세요.");
		return;
	}


	var opt_1_length = $("input[name='opt_1']").length;

	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		alert("상환방식을 선택하세요.");
		return;
	}


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var year = $("#year").val();
	var month = $("#month").val();
	var opt_0 = $("input[name='opt_0']:checked").val();
	var opt_1 = $("input[name='opt_1']:checked").val();


	$.post("/compare/loan_snmindustry_3_search_result.php",
	{ 'year': year,
		'month': month,
		'opt_0': opt_0,
		'opt_1': opt_1,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanSnmindustrySearch3_cur() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var opt_0_length = $("input[name='opt_0']").length;
	var opt_0 = $("input[name='opt_0']:checked").val();
	var opt_0_checked_value = 0;
	for(i=0;i<opt_0_length;i++) {
		if($("input[name='opt_0']:eq("+i+")").is(":checked")==true) {
			opt_0_checked_value = opt_0_checked_value + 1;
		}
	}

	if(opt_0_checked_value==0) {
		opt_0 = $("#opt_0 option:selected").val();
		if(opt_0=="") {
			alert("대출구분을 선택하세요.");
			return;
		}
	}

	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("상환방식을 선택하세요.");
			return;
		}
	}
	
	var select_new_balance_length = $("input[name='select_new_balance']").length;
	var select_new_balance = $("input[name='select_new_balance']:checked").val();
	var select_new_balance_checked_value = 0;
	for(i=0;i<select_new_balance_length;i++) {
		if($("input[name='select_new_balance']:eq("+i+")").is(":checked")==true) {
			select_new_balance_checked_value = select_new_balance_checked_value + 1;
		}
	}
	
	if(select_new_balance_checked_value==0) {
		select_new_balance = $("#select_new_balance option:selected").val();
	}
	//alert(select_new_balance);
	
	var year = $("#year").val();
	var month = $("#month").val();
	//var opt_0 = $("input[name='opt_0']:checked").val();
	//var opt_1 = $("input[name='opt_1']:checked").val();
	//var select_new_balance = select_new_balance;
	var ym = 	year + month;
	
	if(ym < 202307)
		{
			if(select_new_balance=="2") {
		alert("잔액기준은 2023년 7월 공시부터 조회 가능합니다.");
		return;
						}
					}
							
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/compare/loan_snmindustry_3_search_result_cur.php",
	{ 'year': year,
		'month': month,
		'opt_0': opt_0,
		'opt_1': opt_1,
		'select_new_balance': select_new_balance,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanOverdueSearchExpl(i) {

	$($("ul[name='Expl2']")).not("ul[name='Expl2']:eq("+i+")").hide();
	$("ul[name='Expl2']:eq("+i+")").show();
}

function LoanOverdueSearch() {

	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("예시구분을 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	//var opt_1 = $("input[name='opt_1']:checked").val();

	$.post("/compare/loan_overdue_2_search_result.php",
	{ 'opt_1': opt_1
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}
//대출상품금리비교++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



//개인종합자산관리계좌(ISA) 금리비교++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function IsaSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var sort_name = $("#sort_name").val();
	var sort_state = $("#sort_state").val();

	var cols = "";
	var cols_length = $("#cols").length;

	if(cols_length>0) {
		cols = $("#cols").val();
	}


	$.post("/compare/isa_search_result.php",
	{
		'str': checked_value,
		'sort_name': sort_name,
		'sort_state': sort_state,
		'cols':cols
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


//개인종합자산관리계좌(ISA) 금리비교++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



//은행수수료비교++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function CommissionDepositSortSelect() {

	var sort_name = $("#sort_name").val();

	$("#sort_state option").remove();

	if(sort_name=="bank_hname") {
		$("#sort_state").append('<option value="asc" selected>ㄱ부터정렬</option>');
		$("#sort_state").append('<option value="desc">ㅎ부터정렬</option>');
	}else{
		$("#sort_state").append('<option value="asc" selected>낮은 순서부터</option>');
		$("#sort_state").append('<option value="desc">높은 순서부터</option>');
	}

}

function CommissionDepositSearch() {


	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var sort_name = $("#sort_name").val();
	var sort_state = $("#sort_state").val();
	var fee_bank = $("#fee_bank").val();
	var sw = $("#sw").val();

	if(sw=="") {
		alert("송금 금액을 입력하세요.");
		$("#sw").focus();
		return;
	}
	if(IsNumber(sw)==false) {
		alert("송금 금액은 숫자만 입력하세요.");
		$("#sw").focus();
		return;
	}
	if(sw > 100000000 && fee_bank == "2") {
		alert("타행이체 송금수수료 이체한도는 1억까지만 조회하실 수 있습니다.");
		$("#sw").focus();
		return;
	}
	if(sw < 1) {
		alert("금액은 반드시 1원 이상을 입력하세요.");
		$("#sw").focus();
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/compare/commission_deposit_search_result.php",
	{
		'str': checked_value,
		'sort_name': sort_name,
		'sort_state': sort_state,
		'fee_bank':fee_bank,
		'sw':sw
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function CommissionDeposit2Search() {


	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var sort_name = $("#sort_name").val();
	var sort_state = $("#sort_state").val();


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/compare/commission_deposit_2_search_result.php",
	{
		'str': checked_value,
		'sort_name': sort_name,
		'sort_state': sort_state
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function CommissionDeposit3Search(i) {

	$($("a[name='FeeKind']")).not("a[name='FeeKind']:eq("+i+")").removeClass('show');
	$("a[name='FeeKind']:eq("+i+")").addClass('show');

	kind = i + 1;


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/compare/commission_deposit_3_search_result.php",
	{
		'kind': kind
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function CommissionExchangeExc(i) {

	$($("a[name='ExcLink']")).not("a[name='ExcLink']:eq("+i+")").removeClass('show');
	$("a[name='ExcLink']:eq("+i+")").addClass('show');

	exc = i + 1;
	$("#exc").val(exc);

	if(exc==1) {
		$("ul[name='Expl']").hide();
		$("ul[name='Expl']:eq(0)").show();
	}else if(exc==6) {
		$("ul[name='Expl']").hide();
		$("ul[name='Expl']:eq(1)").show();
	}else{
		$("ul[name='Expl']").hide();
	}

	$("#SearchResult").html("");

}

function CommissionExchangeSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var exc = $("#exc").val();


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/compare/commission_exchange_search_result.php",
	{
		'exc': exc,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function CommissionExchange2Exc(i) {

	$($("a[name='ExcLink']")).not("a[name='ExcLink']:eq("+i+")").removeClass('show');
	$("a[name='ExcLink']:eq("+i+")").addClass('show');

	exc = i + 1;
	$("#exc").val(exc);

	$("#SearchResult").html("");

}

function CommissionExchange2Search() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var exc = $("#exc").val();


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/compare/commission_exchange2_search_result.php",
	{
		'exc': exc,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function CommissionSpreadBranch(i) {

	$($("a[name='BranchLink']")).not("a[name='BranchLink']:eq("+i+")").removeClass('show');
	$("a[name='BranchLink']:eq("+i+")").addClass('show');

	$("#type").val(i);

	$("#SearchResult").html("");

}

function CommissionSpreadSearch() {

	var type = $("#type").val();
	var select_option = $("#select_option").val();
	var sort_state = $("#sort_state").val();

	var money_checked_length = $("input[name='money']:checked").length;

	if(money_checked_length<1) {
		alert("검색할 화폐를 선택하세요.");
		return;
	}

	var money_checked_value = $("input[name='money']:checked").val();;


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/compare/commission_spread_search_result.php",
	{
		'type': type,
		'select_option': select_option,
		'sort_state': sort_state,
		'money': money_checked_value 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}
//은행수수료비교++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


//민원공시  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function AnnounceMemberSearch(Code) {

	jQuery('#itemAreaDiv').css("display", "block");
	if(Code!="") {
		$("#BankCode").val(Code);
	}

	var standard = $("#standard").val();
	var BankCode = $("#BankCode").val();


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/minwon/announce_member_result.php",
	{
		'standard': standard,
		'BankCode': BankCode 
	},function(data,status){
		setTimeout(function(){

			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();



			var comma_separator_number_step = $.animateNumber.numberStepFactories.separator(',');
			$('#chart_number01').animateNumber(
				{
				number: $("#chart_number01_value").val(),
				numberStep: comma_separator_number_step
				},2000
			);

			var s1 = $("#Chart01_value01").val();
			var s2 = $("#Chart01_value02").val();
			var s3 = $("#Chart01_value03").val();
			var s4 = $("#Chart01_value04").val();
			var s5 = $("#Chart01_value05").val();
			var s6 = $("#Chart01_value06").val();

			printChart(s1,s2,s3,s4,s5,s6);


		},500);
	});



}


//민원공시  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function AnnounceMemberSearch_TEST(Code, Gubun) {

var Gubun2   = $("#goods").val();
	
if(Gubun2!=3){
	//jQuery('#itemAreaDiv').css("display", "block");
	if(Code!="") {
		$("#BankCode").val(Code);
	}
	
	
	var standard = $("#standard").val();
	var BankCode = $("#BankCode").val();
	

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/minwon/announce_member_result_test.php",
	{
		'standard': standard,
		'BankCode': BankCode, 
		'Gubun'   : Gubun2, 
	},function(data,status){
		setTimeout(function(){

			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();



			var comma_separator_number_step = $.animateNumber.numberStepFactories.separator(',');
			$('#chart_number01').animateNumber(
				{
				number: $("#chart_number01_value").val(),
				numberStep: comma_separator_number_step
				},2000
			);

			var s1 = $("#Chart01_value01").val();
			var s2 = $("#Chart01_value02").val();
			var s3 = $("#Chart01_value03").val();
			var s4 = $("#Chart01_value04").val();
			var s5 = $("#Chart01_value05").val();
			var s6 = $("#Chart01_value06").val();

			printChart(s1,s2,s3,s4,s5,s6);


		},500);
	});
}else{
  	  //jQuery('#itemAreaDiv').css("display", "block");
	if(Code!="") {
		$("#BankCode").val(Code);
	}

	var standard2 = $("#standard2").val();
	var BankCode = $("#BankCode").val();


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/minwon/announce_member_result2_test.php",
	{
		'standard2': standard2,
		'BankCode': BankCode 
	},function(data,status){
		setTimeout(function(){

			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();



			var comma_separator_number_step = $.animateNumber.numberStepFactories.separator(',');
			$('#chart_number01').animateNumber(
				{
				number: $("#chart_number01_value").val(),
				numberStep: comma_separator_number_step
				},2000
			);

			var s1 = $("#Chart01_value01").val();
			var s2 = $("#Chart01_value02").val();
			var s3 = $("#Chart01_value03").val();
			var s4 = $("#Chart01_value04").val();
			var s5 = $("#Chart01_value05").val();
			var s6 = $("#Chart01_value06").val();

			printChart(s1,s2,s3,s4,s5,s6);


		},500);
	});
  	
  	
  }


}



function AnnounceCategorySearch() {

	var standard = $("#standard").val();

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();


	$.post("/minwon/announce_category_result.php",
	{
		'standard': standard
	},function(data,status){
		setTimeout(function(){

			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();

			var comma_separator_number_step = $.animateNumber.numberStepFactories.separator(',');
			$('#chart_number01').animateNumber(
				{
				number: $("#chart_number01_value").val(),
				numberStep: comma_separator_number_step
				},2000
			);

			var s1 = $("#Chart01_value01").val();
			var s2 = $("#Chart01_value02").val();
			var s3 = $("#Chart01_value03").val();
			var s4 = $("#Chart01_value04").val();
			var s5 = $("#Chart01_value05").val();
			var s6 = $("#Chart01_value06").val();

			printChart(s1,s2,s3,s4,s5,s6);


		},500);
	});


}


function AnnounceCategorySearch2() {

	var standard = $("#standard").val();

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();


	$.post("/minwon/announce_category_result_2.php",
	{
		'standard': standard
	},function(data,status){
		setTimeout(function(){

			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();


		},500);
	});


}

function AnnounceCategorySearch3() {

	var standard = $("#standard").val();

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();


	$.post("/minwon/announce_category_result_3.php",
	{
		'standard': standard
	},function(data,status){
		setTimeout(function(){

			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();


		},500);
	});


}

function AnnounceCategorySearch3_TEST() {

	var standard = $("#standard").val();

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();


	$.post("/minwon/announce_category_result_3_test.php",
	{
		'standard': standard
	},function(data,status){
		setTimeout(function(){

			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();


		},500);
	});


}

//민원공시  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

//신탁상품 연금저축  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
function TrustPensionYearSelect(max_yyyymm) {

	var YearSelected_value = $("#year").val();

	if(YearSelected_value=="2012") {

		$("#month option").remove();
		$("#month").append('<option value="09" selected>09월</option>');
		$("#month").append('<option value="12" >12월</option>');

	}else if(YearSelected_value=="2019"){

                $("#month option").remove();
                if(max_yyyymm >= YearSelected_value + "03"){
                        $("#month").append('<option value="03" >03월</option>');
                }
                if(max_yyyymm >= YearSelected_value + "06"){
                        $("#month").append('<option value="06" >06월</option>');
                }
                if(max_yyyymm >= YearSelected_value + "09"){
                        $("#month").append('<option value="09" >09월</option>');
                }


        }else{

		$("#month option").remove();

		if(max_yyyymm >= YearSelected_value + "03"){
			$("#month").append('<option value="03" >03월</option>');
		}
		if(max_yyyymm >= YearSelected_value + "06"){
			$("#month").append('<option value="06" >06월</option>');
		}
		if(max_yyyymm >= YearSelected_value + "09"){
			$("#month").append('<option value="09" >09월</option>');
		}
		if(max_yyyymm >= YearSelected_value + "12"){
			$("#month").append('<option value="12" >12월</option>');
		}

	}

}

function TrustPensionYearSelect_new(max_yyyymm) {

        var YearSelected_value = $("#year").val();

        if(YearSelected_value=="2019") {

                $("#month option").remove();
                $("#month").append('<option value="12" >12월</option>');

        }else{

                $("#month option").remove();

                if(max_yyyymm >= YearSelected_value + "03"){
                        $("#month").append('<option value="03" >03월</option>');
                }
                if(max_yyyymm >= YearSelected_value + "06"){
                        $("#month").append('<option value="06" >06월</option>');
                }
                if(max_yyyymm >= YearSelected_value + "09"){
                        $("#month").append('<option value="09" >09월</option>');
                }
                if(max_yyyymm >= YearSelected_value + "12"){
                        $("#month").append('<option value="12" >12월</option>');
                }

        }

}


function TrustPension2() {

	Form1.submit();

}


function PopupTrust_pension2(i) {

	var pro_name = $("input[name='pro_name']").eq(i).val();
	var fund = $("input[name='fund']").eq(i).val();
	var st_year = $("select[name='st_year']").eq(i).val();
	var st_month = $("select[name='st_month']").eq(i).val();
	var bank_code = $("select[name='bank_code']").eq(i).val();

	$("#pro_name2").val(pro_name);
	$("#fund2").val(fund);
	$("#st_year2").val(st_year);
	$("#st_month2").val(st_month);
	$("#bank_code2").val(bank_code);

	//var currentWidth = $(window).width();
	var currentWidth = screen.width;
	pension = window.open('','pension','scrollbars=yes, resizable=yes, left=0, width='+currentWidth+', height=1000');
	document.Form2.target = "pension";
	Form2.submit();
}


function TrustSearchFundSelect() {

	var pro_name2 = $("select[name='pro_name2']").val();

	if(pro_name2=="개인연금신탁") {
		$("span[id='fund_select']").hide();
		$("select[id='fund2']").prop("disabled",true);
	}else{
		$("span[id='fund_select']").show();
		$("select[id='fund2']").prop("disabled",false);
	}

}

//신탁상품 연금저축  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

//퇴직연금 금리비교  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function RetirementRegularSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var sort_name = $("#sort_name").val();
	var sort_state = $("#sort_state").val();

	var cols = "";
	var cols_length = $("#cols").length;

	if(cols_length>0) {
		cols = $("#cols").val();
	}


	$.post("/compare/retirement_regular_search_result.php",
	{  'str': checked_value,
		'sort_name': sort_name,
		'sort_state': sort_state,
		'cols':cols
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function RetirementSearchExpl(i) {
	$($("div[id='Expl']")).not("div[id='Expl']:eq("+i+")").hide();
	$("div[id='Expl']:eq("+i+")").show();
}

function RetirementSearch() {


	var opt_1_length = $("input[name='opt_1']").length;
	var opt_1 = $("input[name='opt_1']:checked").val();
	var opt_1_checked_value = 0;
	for(i=0;i<opt_1_length;i++) {
		if($("input[name='opt_1']:eq("+i+")").is(":checked")==true) {
			opt_1_checked_value = opt_1_checked_value + 1;
		}
	}

	if(opt_1_checked_value==0) {
		opt_1 = $("#opt_1 option:selected").val();
		if(opt_1=="") {
			alert("제도유형을 선택하세요.");
			return;
		}
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "550px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	//var opt_1 = $("input[name='opt_1']:checked").val();

	var gd = "";
	var gd_length = $("#gd").length;

	if(gd_length>0) {
		gd = $("#gd").val();
	}

	var gg = "";
	var gg_length = $("#gg").length;

	if(gg_length>0) {
		gg = $("#gg").val();
	}

	var yg = gd + gg;

	if(yg!="") {
		if(yg<20142){
			MoveConfirm = confirm("2014년 1/4분기 이전 검색은\n\n [은행별 비교공시(2014년 1/4분기 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
			if(MoveConfirm==true){
				location.href="/compare/retirement_2.php";
			}else{
				$("div[id='Roading']").hide();
				$("div[id='SysBg_White']").hide();
				//Form1.reset();
				return;
			}
		}
	}


	$.post("/compare/retirement_search_result.php",
	{ 'opt_1': opt_1,
		'gd': gd,
		'gg': gg
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function RetirementSearch2() {


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "550px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	var gd = "";
	var gd_length = $("#gd").length;

	if(gd_length>0) {
		gd = $("#gd").val();
	}

	var gg = "";
	var gg_length = $("#gg").length;

	if(gg_length>0) {
		gg = $("#gg").val();
	}


	var yg = gd + gg;

	if(yg!="") {
		if(yg>20141){
			MoveConfirm = confirm("2014년 2/4분기 이후 검색은\n\n [은행별 비교공시(2014년 2/4분기 이후)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
			if(MoveConfirm==true){
				location.href="/compare/retirement.php";
			}else{
				$("div[id='Roading']").hide();
				$("div[id='SysBg_White']").hide();
				//Form1.reset();
				return;
			}
		}

		if(yg<20123){
			MoveConfirm = confirm("2012년 2/4분기 이전 검색은\n\n [은행별 비교공시(2012년 2/4분기 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
			if(MoveConfirm==true){
				location.href="/compare/retirement_3.php";
			}else{
				$("div[id='Roading']").hide();
				$("div[id='SysBg_White']").hide();
				//Form1.reset();
				return;
			}
		}
	}


	$.post("/compare/retirement_2_search_result.php",
	{
		'gd': gd,
		'gg': gg
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function RetirementSearch3() {


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "550px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	var gd = "";
	var gd_length = $("#gd").length;

	if(gd_length>0) {
		gd = $("#gd").val();
	}

	var gg = "";
	var gg_length = $("#gg").length;

	if(gg_length>0) {
		gg = $("#gg").val();
	}

	var yg = gd + gg;

	if(yg!="") {
		if(yg>20122){
			MoveConfirm = confirm("2012년 3/4분기 이후 검색은\n\n [은행별 비교공시(2014년 1/4분기 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
			if(MoveConfirm==true){
				location.href="/compare/retirement_2.php";
			}else{
				$("div[id='Roading']").hide();
				$("div[id='SysBg_White']").hide();
				//Form1.reset();
				return;
			}
		}

		if(yg<20103){
			MoveConfirm = confirm("2010년 2/4분기 이전 검색은\n\n [은행별 비교공시(2010년 2/4분기 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
			if(MoveConfirm==true){
				location.href="/compare/retirement_4.php";
			}else{
				$("div[id='Roading']").hide();
				$("div[id='SysBg_White']").hide();
				//Form1.reset();
				return;
			}
		}
	}


	$.post("/compare/retirement_3_search_result.php",
	{
		'gd': gd,
		'gg': gg
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function OpenWinHtml(str) {
	
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+150;

	$("div[id='SysBg_Black']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"1000"
	}).show();

	$("div[id='Roading']").css({  
			"top": "1350px",  
			"left": LocWidth,
			"opacity":"0.8",
			"position": "absolute",
			"z-index":"200"
		}).show();

	$("#DataResult").load("/popup/"+str,
	{ 'img_url': '1'
	},function(){

		$("div[id='Roading']").hide();
		$("div[id='DataResult']").css({  
			"top": "500px",  
			"left": (body_width/2)-400,
			"opacity":"1.0",
			"position": "absolute",
			"z-index":"1000"
		}).show();
		$('html, body').animate({ scrollTop : 450 }, 700);

	});
	
}


function RetirementSearch4() {


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "550px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	var gd = "";
	var gd_length = $("#gd").length;

	if(gd_length>0) {
		gd = $("#gd").val();
	}

	var gg = "";
	var gg_length = $("#gg").length;

	if(gg_length>0) {
		gg = $("#gg").val();
	}

	var yg = gd + gg;

	if(yg!="") {
		if(yg>20102){
			MoveConfirm = confirm("2010년 3/4분기 이후 검색은\n\n [은행별 비교공시(2012년 2/4분기 이전)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
			if(MoveConfirm==true){
				location.href="/compare/retirement_3.php";
			}else{
				$("div[id='Roading']").hide();
				$("div[id='SysBg_White']").hide();
				//Form1.reset();
				return;
			}
		}
	}



	$.post("/compare/retirement_4_search_result.php",
	{
		'gd': gd,
		'gg': gg
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

//퇴직연금 금리비교  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


function FP_CompareSearchForm01() {
	
	
	var str_goods01 = $("#str_goods01").val();
	
	if(str_goods01=="1") {
		CompareSearchForm01.action="/compare/receiving_deposit_3.php";
	}else{
		CompareSearchForm01.action="/compare/receiving_deposit.php";
	}
	
	CompareSearchForm01.submit();
}


//은행전화번호 진위확인 서비스  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function BankPhoneNumber() {
	
	var s_que1 = $("#s_que1").val();
	var s_que2 = $("#s_que2").val();
	
	
	if(s_que1=="") {
		alert("검색하려는 은행을 선택하세요.");
		document.searchForm.s_que1.focus();
		return;
	}

	if(document.searchForm.s_que2.value=="") {
		alert('전화번호를 입력하세요.');
		document.searchForm.s_que2.focus();
		return;
	}
	
	if(s_que2.length < 6){
	  alert('전화번호를 6자리이상 입력하세요.');
	}

        if(/[^0123456789-]/.test(s_que2)) {
                alert("전화번호는 숫자와 특수문자'-'만 입력이 가능합니다.");
                document.searchForm.s_que2.focus();
                return;
        }
	document.searchForm.submit();

}

//은행전화번호 진위확인 서비스  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

function BankPhoneNumber2() {
	
	var s_que1 = $("#s_que1").val();
	var s_que2 = $("#s_que2").val();
	
	
	if(s_que1=="") {
		alert("검색하려는 은행을 선택하세요.");
		document.searchForm.s_que1.focus();
		return;
	}

	if(document.searchForm.s_que2.value=="") {
		alert('전화번호를 입력하세요.');
		document.searchForm.s_que2.focus();
		return;
	}

  if(s_que2.length < 6){
	  alert('전화번호를 6자리이상 입력하세요.');
	  return;
	}

        if(/[^0123456789-]/.test(s_que2)) {
                alert("전화번호는 숫자와 특수문자'-'만 입력이 가능합니다.");
                document.searchForm.s_que2.focus();
                return;
        }
	
	$.post("/voice/bankphonenumber_result.php",
	{ 's_que1': s_que1,
		's_que2': s_que2
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},300);
	});
	
}

function DepositLoanGapSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2); 
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	var str_year = $("#str_year").val();
	var str_month = $("#str_month").val();

	var end_year = $("#end_year").val();
	var end_month = $("#end_month").val();

	var str_cal = (str_year) + (str_month);
	var end_cal = (end_year) + (end_month);
	
	var diff = end_cal - str_cal;
	

	if(diff > 100 ) {
		alert("최대 조회기간은 1년 입니다.");
		return;
		
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10, 
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();


	}


	$.post("/compare/deposit_loan_gap_search_result.php",
	{ 'str_year': str_year,
		'str_month': str_month,
		'end_year': end_year,
		'end_month': end_month,
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function DepositLoanGapSortSearch_new() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2); 
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	var str_year = $("#str_year").val();
	var str_month = $("#str_month").val();

	var end_year = $("#end_year").val();
	var end_month = $("#end_month").val();

	var end_year = $("#end_year").val();
	var end_month = $("#end_month").val();
	
	var sort_year = $("#sort_year").val();
	var sort_month = $("#sort_month").val();
	var sort_name = $("#sort_name").val();
	var OrderByType = $("#OrderByType").val();
	var select_new_balance = $("#select_new_balance").val();
				
	var str_cal = (str_year) + (str_month);
	var end_cal = (end_year) + (end_month);
	
	var diff = end_cal - str_cal;
	var strym = str_year + str_month;
	
  if(strym < 202207 )
  {
		alert("2022년 7월 이후부터 조회가능합니다.");
		return;
  }
  
	if(diff > 100 ) {
		alert("최대 조회기간은 1년 입니다.");
		return;
	}
	
	if(sort_name != 1 )
	{
		if((sort_year) == 0 || (sort_month) == 0)
		{
			alert("정렬년월을 선택해주세요 .");
			return;
		}
	}	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10, 
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();




	$.post("/compare/deposit_loan_gap_search_result_sort_new.php",
	{ 'str_year': str_year,
		'str_month': str_month,
		'end_year': end_year,
		'end_month': end_month,
		'sort_year': sort_year,
		'sort_month': sort_month,
		'sort_name': sort_name,	
		'OrderByType': OrderByType,			
		'str': checked_value,
		'select_new_balance': select_new_balance
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function DepositLoanGapSortSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2); 
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	var str_year = $("#str_year").val();
	var str_month = $("#str_month").val();

	var end_year = $("#end_year").val();
	var end_month = $("#end_month").val();

	var end_year = $("#end_year").val();
	var end_month = $("#end_month").val();
	
	var sort_year = $("#sort_year").val();
	var sort_month = $("#sort_month").val();
	var sort_name = $("#sort_name").val();
	var OrderByType = $("#OrderByType").val();
				
	var str_cal = (str_year) + (str_month);
	var end_cal = (end_year) + (end_month);
	
	var diff = end_cal - str_cal;
	var strym = str_year + str_month;
	
  if(strym < 202207 )
  {
		alert("2022년 7월 이후부터 조회가능합니다.");
		return;
  }
  
	if(diff > 100 ) {
		alert("최대 조회기간은 1년 입니다.");
		return;
	}
	
	if(sort_name != 1 )
	{
		if((sort_year) == 0 || (sort_month) == 0)
		{
			alert("정렬년월을 선택해주세요 .");
			return;
		}
	}	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10, 
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();




	$.post("/compare/deposit_loan_gap_search_result_sort.php",
	{ 'str_year': str_year,
		'str_month': str_month,
		'end_year': end_year,
		'end_month': end_month,
		'sort_year': sort_year,
		'sort_month': sort_month,
		'sort_name': sort_name,	
		'OrderByType': OrderByType,			
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanReduceSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	if(!isNaN(sort_name)) {
		alert("정렬방식을 다시 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2); 
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	var sort_name = $("#sort_name").val();
	var OrderByType = $("#OrderByType").val();	
	var year = $("#year").val();
	var month = $("#month").val();
	var yearmonth = (year) + (month);	
	
	
		if(yearmonth ==20221){
			MoveConfirm = confirm("2022년 상반기 검색은\n\n [은행별 금리인하요구권(2022년 상반기)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
			if(MoveConfirm==true){
				location.href="/compare/loan_reduce.php";
			}else{
				$("div[id='Roading']").hide();
				$("div[id='SysBg_White']").hide();
				//Form1.reset();
				return;
			}
		}
  	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10, 
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/compare/loan_reduce_result.php",
	{ 
		'sort_name': sort_name,	
		'year': year,
		'month': month,
		'OrderByType': OrderByType,			
		'OrderByType': OrderByType,		
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

function LoanReduceSearch2() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2); 
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	var sort_name = $("#sort_name").val();
	var OrderByType = $("#OrderByType").val();	
	var year = $("#year").val();
	var month = $("#month").val();
	var yearmonth = (year) + (month);	
	
	
		if(yearmonth ==20221){
			MoveConfirm = confirm("2022년 상반기 검색은\n\n [은행별 금리인하요구권(2022년 상반기)]에서 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
			if(MoveConfirm==true){
				location.href="/compare/loan_reduce.php";
			}else{
				$("div[id='Roading']").hide();
				$("div[id='SysBg_White']").hide();
				//Form1.reset();
				return;
			}
		}
  	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10, 
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/compare/loan_reduce_result2.php",
	{ 
		'sort_name': sort_name,	
		'year': year,
		'month': month,
		'OrderByType': OrderByType,			
		'OrderByType': OrderByType,		
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function DebtAdjustSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2); 
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	var OrderByType = $("#OrderByType").val();	
	var year = $("#year").val();
	var month = $("#month").val();
	var yearmonth = (year) + (month);	
  	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10, 
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/minwon/debt_adjust_result.php",
	{ 
		'year': year,
		'month': month,
		'OrderByType': OrderByType,		
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function DebtSellSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2); 
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	var OrderByType = $("#OrderByType").val();	
	var year = $("#year").val();
	var month = $("#month").val();
	var yearmonth = (year) + (month);	
  	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10, 
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();



	$.post("/minwon/debt_sell_result.php",
	{ 
		'year': year,
		'month': month,
		'OrderByType': OrderByType,		
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}


function DebtGiveupSearch() {

	var BankName_length = $("input[name='BankName']").length;

	var checked_value = "";
	for(i=0;i<BankName_length;i++) {
		if($("input[name='BankName']:eq("+i+")").is(":checked")==true) {
			if(!checked_value) {
				checked_value = $("input[name='BankName']:eq("+i+")").val();
			}else{
				checked_value = checked_value + "|" + $("input[name='BankName']:eq("+i+")").val();
			}
		}
	}

	if(checked_value=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2); 
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	var OrderByType = $("#OrderByType").val();	
	var year = $("#year").val();
	var month = $("#month").val();
	var yearmonth = (year) + (month);	
  	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10, 
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/minwon/debt_giveup_result.php",
	{ 
		'year': year,
		'month': month,
		'OrderByType': OrderByType,		
		'str': checked_value
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}


//차세대 레이퍼 팝업(22.12) JS

	function closeWin() {
	    if ( document.notice_form.chkbox.checked ){
	        setCookie( "maindiv", "done" , 1 );
	    }
	    document.all['divpop'].style.visibility = "hidden";
	}

	function setCookie(name, value, expiredays) {
	    var todayDate = new Date();
	    todayDate.setDate(todayDate.getDate() + expiredays);
	    document.cookie = name + "=" + escape(value) + "; path=/; expires=" + todayDate.toGMTString() + ";"
	}
	
function deposit_loan_gap_popup() {
	
	var str_year = $("#st_year2").val();
	var str_month = $("#st_month2").val();
	var bank_name = $("#bank_code2").val();
	
	var strym = str_year + str_month;
	
	$.post("/compare/gap_popup_result.php",
	{ 
		'strym': strym,	
		'bank_name': bank_name

	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}	

function pt101past_popup() {
	
	var year = $("#year").val();

	$.post("/compare/pt101past_popup_result.php",
	{ 
		'year': year,	
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 270 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}	

	//예대금리차 보기팝업
function PopupDepositLoanGap(url,selected_yymm,selected_bank) {
	var currentWidth = screen.width;
	url = url + "?selected_yymm=" + selected_yymm + "&selected_bank=" + selected_bank;
	window.open(url,'gap','scrollbars=yes, resizable=yes, left=0, width=800, height=800');
}

function FP_FreeDepositSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType_length = $("input[name='InterestType']:checked").length;
	
	if(InterestType_length<1) {
		alert("이자 계산방식을 선택하세요.");
		return;
	}

var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	
	if(JOIN_METHOD_length<1) {
		alert("가입방식을 선택하세요.");
		return;
	}

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var InterestType = $("input[name='InterestType']:checked").val();
	var BankValue = $("input[id='BankValue']").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();

	$.post("/compare/free_deposit_search_result.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'OrderByType': OrderByType,
		'JOIN_METHOD': JOIN_METHOD,  
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 770 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});


}

function FP_FreeDepositSearch_sort() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var InterestType_length = $("input[name='InterestType']:checked").length;
	var InterestType_value = $("input[name='InterestType']:checked").val();
	if(InterestType_length<1) {
		InterestType_value = $("#InterestType option:selected").val();
		if(InterestType_value=="") {
			alert("이자 지급방식을 선택하세요.");
			return;
		}
	}
	var InterestType = InterestType_value;

	var JOIN_METHOD_length = $("input[name='JOIN_METHOD']:checked").length;
	var JOIN_METHOD_value = $("input[name='JOIN_METHOD']:checked").val();
	if(JOIN_METHOD_length<1) {
		JOIN_METHOD_value = $("#JOIN_METHOD option:selected").val();
		if(JOIN_METHOD_value=="") {
			alert("가입방식을 선택하세요.");
			return;
		}
	}
	var JOIN_METHOD = JOIN_METHOD_value;

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	//var InterestType = $("input[name='InterestType']:checked").val();
	var BankValue = $("input[id='BankValue']").val();
	var OrderByType = $("#OrderByType option:selected").val();
	var SortType = $("input[id='SortType']").val();
	//var JOIN_METHOD = $("input[name='JOIN_METHOD']:checked").val();
	var InterestMonth = $("#InterestMonth option:selected").val();
	
	$.post("/compare/free_deposit_search_result_sort.php",
	{ 'InterestType': InterestType,
		'BankValue': BankValue,
		'InterestMonth' : InterestMonth,
		'OrderByType': OrderByType,
		'JOIN_METHOD': JOIN_METHOD,  
		'SortType': SortType 
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 770 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}

function KFB_BranchSearch() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var BankValue = $("input[id='BankValue']").val();
	var SortType = $("input[id='SortType']").val();
  var standard = $("#standard").val();
  
	$.post("/minwon/compare_close_shop_result.php",
	{ 
		'BankValue': BankValue,
		'standard' : standard,
		'SortType' : SortType,		
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 770 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}

function KFB_BranchSearch_Sort(order_str) {
	$("input[id='SortType']").val(order_str);
	KFB_BranchSearch();
	$("input[id='SortType']").val("");
}

function KFB_BranchSearch_Detail() {


	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);


	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "450px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var BankValue = $("input[id='BankValue']").val();
  var standard = $("#standard").val();
  var closed_address = $("#closed_address").val();
  
	$.post("/minwon/compare_close_shop_detail_result.php",
	{ 
		'BankValue': BankValue,
		'standard' : standard,
		'closed_address' : closed_address
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 770 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}

//jlogos 중도상환수수료율 분리
function FP_CommissionLoanSearch() {

	//기준 연도
	var standard = $("#standard").val();

	//기준연도가 2024년일 경우에는 이전 중도상환수수료울 조회
	if (standard == '2024') {
		MoveConfirm = confirm("2025년 1월 12일 이전 공시자료는\n\n 과거 페이지에서만 검색하실 수 있습니다.\n\n해당 페이지로 이동하시겠습니까?");
		if(MoveConfirm==true){
			location.href="commission_loan_3.php";
			return false;
		}else{
			Form1.reset();
			return;
		}		

	}
	
	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2=="") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();
	var BankValue = $("input[id='BankValue']").val();

	$.post("/compare/commission_loan_search_result.php",
	{ 'standard': standard,	
		'BankValue': BankValue,
		'SortType': SortType
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

const getDeviceType = () => {
  const userAgent = navigator.userAgent;

  // iOS 기기 판별
  if (/iPad|iPhone|iPod/.test(userAgent)) {
    if (/CriOS/.test(userAgent)) {
      return "iOS Chrome";
    } else if (/Safari/.test(userAgent) && !/CriOS/.test(userAgent)) {
      return "iOS Safari";
    } else if (/KAKAOTALK/.test(userAgent)) {
      return "iOS Kakao";
    } else {
      return "iOS";
    }
  }

  // Android 기기 판별
  if (/android/i.test(userAgent)) {
    if (/Chrome/.test(userAgent)) {
      return "Android Chrome";
    } else if (/SamsungBrowser/.test(userAgent)) {
      return "Android Samsung Browser";
    } else if (/KAKAOTALK/.test(userAgent)) {
      return "Android Kakao";
    } else {
      return "Android";
    }
  }
  
  // 웹 브라우저 판별
  return "Web";
};

		
$(document).ready(function() {
	
	//개인사업자 자금용도 
	/*
	//console.log($("input[id^='useFund']").length);
	$("input[id^='useFund']").click(function() {
		
		//console.log($(this).attr('id') + " : " + $(this).val());
		
		var useFund = $(this).attr('id');
		useFundId = useFund.substring(0, useFund.length -1);
		useFundIdVal = Number(useFund.substring(useFund.length -1));
		//console.log(useFundIdVal);
		
		//var useFundId = Number($(this).val());
		if (useFundIdVal <= 4) {
			useFundIdVal = useFundIdVal + 4;
			useFundId = "#useFund" + useFundIdVal;
		} else if (useFundIdVal > 4) {
			useFundIdVal = useFundIdVal - 4;
			useFundId = "#useFund" + useFundIdVal;
		}			
		
		if ($(this).is(":checked")) {
			//console.log($(this).attr('id') + " : checked");
			//console.log(useFundId + " checked");
			$(useFundId).prop("checked", true);

		} else {
			//console.log($(this).attr('id') + " : unchecked");	
			//console.log(useFundId + " unchecked");
			$(useFundId).prop("checked", false);						
		}
	});
	*/
});	

//jlogos 개인사업자 대출
function FP_PerBizSearch() {
	
	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2 == "") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);
	
	//자금용도 (useFund)
	var useFundValue = "";
	var useFund_length = $("input[name='useFund']").length;
		
	//for(var i = 1; i <= useFund_length; i++){
	for(var i = 1; i <= 4; i++){		
	
		console.log("checked : " + $("#useFund" + i ).is(":checked"));
		
		//if($('input[id="useFund'+i+'"]:checked').length > 0) {
		if ($("#useFund" + i).is(":checked")) {			
			if(useFundValue == "") {
				useFundValue = $('input[id="useFund'+i+'"]:checked').val();
			}else{
				useFundValue = useFundValue+"|"+$('input[id="useFund'+i+'"]:checked').val();
			}
		}
	}

	//console.log("useFundValue : " + useFundValue);
	if(useFundValue == "") {
		alert("자금용도를 선택하세요.");
		return;
	}
	
	//상품구분 (productTypeCode)
	var productTypeCode_length = $("input[name='productTypeCode']:checked").length;
	var productTypeCodeValue = $("input[name='productTypeCode']:checked").val();
	console.log("radio : " + productTypeCodeValue);
	if (productTypeCode_length < 1) {
		productTypeCodeValue = $("#productTypeCode option:selected").val();
		console.log("select : " + productTypeCodeValue);
		if (productTypeCodeValue == "") {
			alert("상품구분을 선택하세요.");
			return;
		}
	}
	
	//가입대상 (joinTarget)
	var joinTargetValue = "";
	var joinTarget_length = $("input[name='joinTarget']").length;
	var joinTargetAllValue = "";
	if ($("input[name='joinTargetAll']:checked").length == 1) {
		joinTargetAllValue = $("input[name='joinTargetAll']:checked").val();
	}
	//alert(joinTargetAllValue);
	
	//for(var i = 1; i <= joinTarget_length; i++){
	for(var i = 1; i <= 8; i++){				
	
		//if($('input[id="joinTarget'+i+'"]:checked').length > 0) {
		if ($("#joinTarget" + i).is(":checked")) {					
			if(joinTargetValue == "") {
				joinTargetValue = $('input[id="joinTarget'+i+'"]:checked').val();
			}else{
				joinTargetValue = joinTargetValue +"|"+$('input[id="joinTarget'+i+'"]:checked').val();
			}
		}
	}
	if(joinTargetValue == "") {
		alert("가입대상을 선택하세요.");
		return;
	}
	//console.log("joinTargetAllValue : " + joinTargetAllValue);
	//console.log("joinTargetValue : " + joinTargetValue);
	
	//개별 선택 전체 해제
	if (joinTargetValue != "") {
		joinTargetAllValue = "";
	}
	
	 
	//대출필요금액 (maxCode)
	var maxCodeValue = "";
	var maxCode_length = $("input[name='maxCode']").length;
	var maxCodeAllValue = "";
	if ($("input[name='maxCodeAll']:checked").length == 1) {
		maxCodeAllValue = $("input[name='maxCodeAll']:checked").val();
	}
	//alert(maxCodeAllValue);
	
	//for(var i = 1; i <= maxCode_length; i++){
	for(var i = 1; i <= 6; i++){	
		//if($('input[id="maxCode'+i+'"]:checked').length > 0) {
		if ($("#maxCode" + i).is(":checked")) {	
			if(maxCodeValue == "") {
				maxCodeValue = $('input[id="maxCode'+i+'"]:checked').val();
			}else{
				maxCodeValue = maxCodeValue+"|"+$('input[id="maxCode'+i+'"]:checked').val();
			}
		}
	}
	if(maxCodeValue == "") {
		alert("대출필요금액을 선택하세요.");
		return;
	}
	
	//개별 선택 전체 해제
	if (maxCodeValue != "") {
		maxCodeAllValue = "";
	}
	

	//대출종류
	var typeLoan_length = $("input[name='typeLoan']:checked").length;
	var typeLoanValue = $("input[name='typeLoan']:checked").val();
	if(typeLoan_length < 1) {
		typeLoanValue = $("#typeLoan option:selected").val();
		if (typeLoanValue == "") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}
	
	//금리방식 (interestTypeCode)
	var interestTypeCodeValue = $("input[name='interestTypeCode']:checked").val();
	var interestTypeCode_length = $("input[name='interestTypeCode']:checked").length;
	if(interestTypeCode_length < 1) {
		interestTypeCodeValue = $("#interestTypeCode option:selected").val();
		if (interestTypeCode == "") {
			alert("금리방식을 선택하세요.");
			return;
		}
	}

		
	//상환방식 (repayMethod)
	var repayMethodValue = "";
	var repayMethod_length = $("input[name='repayMethod']").length;
	var repayMethodAllValue = "";
	if ($("input[name='repayMethodAll']:checked").length == 1) {
		repayMethodAllValue = $("input[name='repayMethodAll']:checked").val();
	}
	//alert(repayMethodAllValue);
	
	//for(var i = 1; i <= repayMethod_length; i++){
	for(var i = 1; i <= 4; i++){	
		//if($('input[id="repayMethod'+i+'"]:checked').length > 0) {
		if ($("#repayMethod" + i).is(":checked")) {				
			if(repayMethodValue == "") {
				repayMethodValue = $('input[id="repayMethod'+i+'"]:checked').val();
			}else{
				repayMethodValue = repayMethodValue+"|"+$('input[id="repayMethod'+i+'"]:checked').val();
			}
		}
	}
	if(repayMethodValue == "") {
		alert("상환방식을 선택하세요.");
		return;
	}
	
	//개별 선택 전체 해제
	if (repayMethodValue != "") {
		repayMethodAllValue = "";
	}
	
	//가입방법 (joinMethod)
	var joinMethodValue = "";
	var joinMethod_length = $("input[name='joinMethod']").length;
	var joinMethodAllValue = "";
	if ($("input[name='joinMethodAll']:checked").length == 1) {
		joinMethodAllValue = $("input[name='joinMethodAll']:checked").val();
	}
	//alert(joinMethodAllValue);
	
	//for(var i = 1; i <= joinMethod_length; i++){
	for(var i = 1; i <= 6; i++){		
		//if($('input[id="joinMethod'+i+'"]:checked').length > 0) {
		if ($("#joinMethod" + i).is(":checked")) {				
			if(joinMethodValue == "") {
				joinMethodValue = $('input[id="joinMethod'+i+'"]:checked').val();
			}else{
				joinMethodValue = joinMethodValue+"|"+$('input[id="joinMethod'+i+'"]:checked').val();
			}
		}
	}
	if(joinMethodValue == "") {
		alert("가입방법을 선택하세요.");
		return;
	}
	
	//개별 선택 전체 해제
	if (joinMethodValue != "") {
		joinMethodAllValue = "";
	}
	
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();
	
	var BankValue = $("input[id='BankValue']").val();
	
	$.post("/compare/loan_search_5_search_result.php",
	{ 'ProductType': $("input[name='ProductType']:checked").val(),	
		'BankValue': BankValue,
		'SortType': SortType,
		'useFund': useFundValue,
		'productTypeCode': productTypeCodeValue,
		'joinTarget': joinTargetValue,
		'joinTargetAll': joinTargetAllValue,
		'maxCode': maxCodeValue,
		'maxCodeAll': maxCodeAllValue,
		'typeLoan': typeLoanValue,
		'interestTypeCode': interestTypeCodeValue,
		
		'repayMethod': repayMethodValue,
		'repayMethodAll': repayMethodAllValue,
		'joinMethod': joinMethodValue,
		'joinMethodAll': joinMethodAllValue
		
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});

}

//jlogos 개인사업자 대출 (상품명 검색)
function FP_PerBizProdSearch() {
 
	var Bankvalue2 = "";

	radio_length = $("input[name='BankSelect']").length;

	for(var i=1; i<=radio_length; i++){
		if($('input[id="Bankselect'+i+'"]:checked').length>0) {
			if(Bankvalue2=="") {
				Bankvalue2 = $('input[id="Bankselect'+i+'"]:checked').val();
			}else{
				Bankvalue2 = Bankvalue2+"|"+$('input[id="Bankselect'+i+'"]:checked').val();
			}
		}
	}

	if(Bankvalue2 == "") {
		alert("검색하려는 은행을 선택하세요.");
		return;
	}

	$("input[id='BankValue']").val(Bankvalue2);
	

	//자금용도 (useFund)
	var useFundValue = "";
	var useFund_length = $("input[name='useFund']").length;
		
	//for(var i = 1; i <= useFund_length; i++){
	for(var i = 1; i <= 4; i++){		
	
		//console.log("checked : " + $("#useFund" + i ).is(":checked"));
		
		//if($('input[id="useFund'+i+'"]:checked').length > 0) {
		if ($("#useFund" + i).is(":checked")) {			
			if(useFundValue == "") {
				useFundValue = $('input[id="useFund'+i+'"]:checked').val();
			}else{
				useFundValue = useFundValue+"|"+$('input[id="useFund'+i+'"]:checked').val();
			}
		}
	}

	//console.log("useFundValue : " + useFundValue);
	if(useFundValue == "") {
		alert("자금용도를 선택하세요.");
		return;
	}
	
	//자금용도 (useFund)
	/*
	var useFundValue = "";
	var useFund_length = $("input[name='useFund']").length;
	
	for(var i = 1; i <= useFund_length; i++){
		if($('input[id="useFund'+i+'"]:checked').length > 0) {
			if(useFundValue == "") {
				useFundValue = $('input[id="useFund'+i+'"]:checked').val();
			}else{
				useFundValue = useFundValue+"|"+$('input[id="useFund'+i+'"]:checked').val();
			}
		}
	}
	if(useFundValue == "") {
		alert("자금용도를 선택하세요.");
		return;
	}
	*/
	
	//상품구분 (productTypeCode)
	var productTypeCode_length = $("input[name='productTypeCode']:checked").length;
	var productTypeCodeValue = $("input[name='productTypeCode']:checked").val();
	if (productTypeCode_length < 1) {
		productTypeCodeValue = $("#productTypeCode option:selected").val();
		if (productTypeCodeValue == "") {
			alert("상품구분을 선택하세요.");
			return;
		}
	}
	
	//가입대상 (joinTarget)
	var joinTargetValue = "";
	var joinTarget_length = $("input[name='joinTarget']").length;
	var joinTargetAllValue = "";
	if ($("input[name='joinTargetAll']:checked").length == 1) {
		joinTargetAllValue = $("input[name='joinTargetAll']:checked").val();
	}
	//alert(joinTargetAllValue);
	
	for(var i = 1; i <= 8; i++){				
		//if($('input[id="joinTarget'+i+'"]:checked').length > 0) {
		if ($("#joinTarget" + i).is(":checked")) {	
			if(joinTargetValue == "") {
				joinTargetValue = $('input[id="joinTarget'+i+'"]:checked').val();
			}else{
				joinTargetValue = joinTargetValue +"|"+$('input[id="joinTarget'+i+'"]:checked').val();
			}
		}
	}
	if(joinTargetValue == "") {
		alert("가입대상을 선택하세요.");
		return;
	}
	
	//개별 선택 전체 해제
	if (joinTargetValue != "") {
		joinTargetAllValue = "";
	}
	
	 
	//대출필요금액 (maxCode)
	var maxCodeValue = "";
	var maxCode_length = $("input[name='maxCode']").length;
	var maxCodeAllValue = "";
	if ($("input[name='maxCodeAll']:checked").length == 1) {
		maxCodeAllValue = $("input[name='maxCodeAll']:checked").val();
	}
	//alert(maxCodeAllValue);
	
	for(var i = 1; i <= 6; i++){	
		//if($('input[id="maxCode'+i+'"]:checked').length > 0) {
		if ($("#maxCode" + i).is(":checked")) {	
			if(maxCodeValue == "") {
				maxCodeValue = $('input[id="maxCode'+i+'"]:checked').val();
			}else{
				maxCodeValue = maxCodeValue+"|"+$('input[id="maxCode'+i+'"]:checked').val();
			}
		}
	}
	if(maxCodeValue == "") {
		alert("대출필요금액을 선택하세요.");
		return;
	}
	
	//개별 선택 전체 해제
	if (maxCodeValue != "") {
		maxCodeAllValue = "";
	}

	//대출종류
	var typeLoan_length = $("input[name='typeLoan']:checked").length;
	var typeLoanValue = $("input[name='typeLoan']:checked").val();
	if(typeLoan_length < 1) {
		typeLoanValue = $("#typeLoan option:selected").val();
		if (typeLoanValue == "") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}
	
	//금리방식 (interestTypeCode)
	var interestTypeCodeValue = $("input[name='interestTypeCode']:checked").val();
	var interestTypeCode_length = $("input[name='interestTypeCode']:checked").length;
	if(interestTypeCode_length < 1) {
		interestTypeCodeValue = $("#interestTypeCode option:selected").val();
		if (interestTypeCode == "") {
			alert("금리방식을 선택하세요.");
			return;
		}
	}
		
	//상환방식 (repayMethod)
	var repayMethodValue = "";
	var repayMethod_length = $("input[name='repayMethod']").length;
	var repayMethodAllValue = "";
	if ($("input[name='repayMethodAll']:checked").length == 1) {
		repayMethodAllValue = $("input[name='repayMethodAll']:checked").val();
	}
	//alert(repayMethodAllValue);
	
	for(var i = 1; i <= 4; i++){	
		//if($('input[id="repayMethod'+i+'"]:checked').length > 0) {
		if ($("#repayMethod" + i).is(":checked")) {			
			if(repayMethodValue == "") {
				repayMethodValue = $('input[id="repayMethod'+i+'"]:checked').val();
			}else{
				repayMethodValue = repayMethodValue+"|"+$('input[id="repayMethod'+i+'"]:checked').val();
			}
		}
	}
	if(repayMethodValue == "") {
		alert("상환방식을 선택하세요.");
		return;
	}
	
	//개별 선택 전체 해제
	if (repayMethodValue != "") {
		repayMethodAllValue = "";
	}
	
	//가입방법 (joinMethod)
	var joinMethodValue = "";
	var joinMethod_length = $("input[name='joinMethod']").length;
	var joinMethodAllValue = "";
	if ($("input[name='joinMethodAll']:checked").length == 1) {
		joinMethodAllValue = $("input[name='joinMethodAll']:checked").val();
	}
	//alert(joinMethodAllValue);
	
	for(var i = 1; i <= 6; i++){		
		//if($('input[id="joinMethod'+i+'"]:checked').length > 0) {
		if ($("#joinMethod" + i).is(":checked")) {				
			if(joinMethodValue == "") {
				joinMethodValue = $('input[id="joinMethod'+i+'"]:checked').val();
			}else{
				joinMethodValue = joinMethodValue+"|"+$('input[id="joinMethod'+i+'"]:checked').val();
			}
		}
	}
	if(joinMethodValue == "") {
		alert("가입방법을 선택하세요.");
		return;
	}
	
	//개별 선택 전체 해제
	if (joinMethodValue != "") {
		joinMethodAllValue = "";
	}
	
	
	/* 2025.03.13 -> 기본 선택이 되어 있으므로 선택된 항목 중에서 상품명 검색으로 변경
	//자금용도 (useFund)
	var useFundValue = "1|2|3|4";
	
	//상품구분 (productTypeCode)
	var productTypeCodeValue = "1";	//일반대출상품
	
	//가입대상 (joinTarget)
	var joinTargetValue = "1|2|3|4|5|6|7|8";
	var joinTargetAllValue = "All";
	 
	//대출필요금액 (maxCode)
	var maxCodeValue = "1|2|3|4|5|6";
	var maxCodeAllValue = "All";

	//금리방식 (interestTypeCode)
	var interestTypeCodeValue = "2";		//변동금리
		
	//상환방식 (repayMethod)
	var repayMethodValue = "1|2|3|4";
	var repayMethodAllValue = "All";
		
	//가입방법 (joinMethod)
	var joinMethodValue = "1|2|3|4|5|9";
	var joinMethodAllValue = "All";

 	//대출종류
	var typeLoan_length = $("input[name='typeLoan']:checked").length;
	var typeLoanValue = $("input[name='typeLoan']:checked").val();
	if(typeLoan_length < 1) {
		typeLoanValue =  $("#typeLoan option:selected").val();
		if (typeLoanValue == "") {
			alert("대출종류를 선택하세요.");
			return;
		}
	}
	*/
	
	var productName = $("input[id='productName']").val();
	if(productName == "") {
		alert("상품명을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	} else if (productName.length < 2) {
		alert("상품명은 최소 2자리 이상을 입력하세요.");
		$("input[id='productName']").focus();
		return;
	}
	
	productName = encodeURIComponent(productName);
	
	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	var SortType = $("input[id='SortType']").val();
	var BankValue = $("input[id='BankValue']").val();

	$.post("/compare/loan_search_5_search_result.php",
	{ 'productName': productName,
	  'typeLoan': typeLoanValue,
	  'searchType': 'productName',
		'BankValue': BankValue,
		'SortType': SortType,
		'useFund': useFundValue,
		'productTypeCode': productTypeCodeValue,
		'joinTarget': joinTargetValue,
		'joinTargetAll': joinTargetAllValue,
		'maxCode': maxCodeValue,
		'maxCodeAll': maxCodeAllValue,
		'typeLoan': typeLoanValue,
		'interestTypeCode': interestTypeCodeValue,
		
		'repayMethod': repayMethodValue,
		'repayMethodAll': repayMethodAllValue,
		'joinMethod': joinMethodValue,
		'joinMethodAll': joinMethodAllValue
		
	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
	

}


//jlogos 개인사업자 대출 / 가입대상 전체 선택
function FP_JoinTargetChecked() {

	//radio 길이
	radio_length = $("input[name='joinTarget']").length;
	console.log("radio_length : " + radio_length);
	console.log($("input[id='joinTargetAll']:checked").length);

	if($("input[id='joinTargetAll']:checked").length == 0){
		
		for(var i=1; i<= radio_length; i++){
			$('input[id="joinTarget'+i+'"]').prop('checked',false);
		}

	}else{

		for(var i=1; i<=radio_length; i++){
			$('input[id="joinTarget'+i+'"]').prop('checked',true);
		}

	}
}

//jlogos 개인사업자 대출 / 가입대상 개별 선택
function CompareJoinTargetCheckEA() {

	var joinTarget_length = $("input[name='joinTarget']").length;
	console.log("joinTarget_length : " + joinTarget_length);

	var checked_value = 0;
	for(i=0; i < joinTarget_length; i++) {
	//for(i=0; i < 8; i++) {		
		if($("input[name='joinTarget']:eq("+i+")").is(":checked") == true) {
			checked_value = checked_value + 1;
			$("#joinTarget" + i).prop('checked',true);
		}
	}
	
	console.log("checked_value : " + checked_value);

	//개별선택갯수 = 전체 비교
	if(checked_value == joinTarget_length) {
		$("#joinTargetAll").each(function () {
			$("#joinTargetAll").prop('checked',true);			
		});
	}else{
		
		$("#joinTargetAll").prop('checked',false);
	}

}

//jlogos 개인사업자 대출 / 대출필요금액 전체 선택
function FP_MaxCodeChecked() {

	//radio 길이
	radio_length = $("input[name='maxCode']").length;
	//console.log("radio_length : " + radio_length);

	if($("input[id='maxCodeAll']:checked").length == 0){
		
		for(var i=1; i<= radio_length; i++){
			$('input[id="maxCode'+i+'"]').prop('checked',false);
		}

	}else{

		for(var i=1; i<=radio_length; i++){
			$('input[id="maxCode'+i+'"]').prop('checked',true);
		}

	}
}

//jlogos 개인사업자 대출 / 대출필요금액 개별 선택
function CompareMaxCodeCheckEA() {

	var maxCode_length = $("input[name='maxCode']").length;
	//console.log("maxCode_length : " + maxCode_length);

	var checked_value = 0;
	for(i=0; i < maxCode_length; i++) {
		if($("input[name='maxCode']:eq("+i+")").is(":checked") == true) {
			checked_value = checked_value + 1;
		}
	}

	if(checked_value == maxCode_length) {
		$("#maxCodeAll").prop('checked',true);
	}else{
		$("#maxCodeAll").prop('checked',false);
	}

}

//jlogos 개인사업자 대출 / 상환방식 전체 선택
function FP_RepayMethodChecked() {

	//radio 길이
	radio_length = $("input[name='repayMethod']").length;
	//console.log("radio_length : " + radio_length);

	if($("input[id='repayMethodAll']:checked").length == 0){
		
		for(var i=1; i<= radio_length; i++){
			$('input[id="repayMethod'+i+'"]').prop('checked',false);
		}

	}else{

		for(var i=1; i<=radio_length; i++){
			$('input[id="repayMethod'+i+'"]').prop('checked',true);
		}

	}
}

//jlogos 개인사업자 대출 / 상환방식 개별 선택
function CompareRepayMethodCheckEA() {

	var repayMethod_length = $("input[name='repayMethod']").length;
	//console.log("repayMethod_length : " + repayMethod_length);

	var checked_value = 0;
	for(i=0; i < repayMethod_length; i++) {
		if($("input[name='repayMethod']:eq("+i+")").is(":checked") == true) {
			checked_value = checked_value + 1;
		}
	}

	if(checked_value == repayMethod_length) {
		$("#repayMethodAll").prop('checked',true);
	}else{
		$("#repayMethodAll").prop('checked',false);
	}

}

//jlogos 개인사업자 대출 / 가입방법 전체 선택
function FP_JoinMethodChecked() {

	//radio 길이
	radio_length = $("input[name='joinMethod']").length;
	//console.log("radio_length : " + radio_length);

	if($("input[id='joinMethodAll']:checked").length == 0){
		
		for(var i=1; i<= radio_length; i++){
			$('input[id="joinMethod'+i+'"]').prop('checked',false);
		}

	}else{

		for(var i=1; i<=radio_length; i++){
			$('input[id="joinMethod'+i+'"]').prop('checked',true);
		}

	}
}

//jlogos 개인사업자 대출 / 상환방식 개별 선택
function CompareJoinMethodCheckEA() {

	var joinMethod_length = $("input[name='joinMethod']").length;
	console.log("joinMethod_length : " + joinMethod_length);

	var checked_value = 0;
	for(i=0; i < joinMethod_length; i++) {
		if($("input[name='joinMethod']:eq("+i+")").is(":checked") == true) {
			checked_value = checked_value + 1;
		}
	}

	if(checked_value == joinMethod_length) {
		$("#joinMethodAll").prop('checked',true);
	}else{
		$("#joinMethodAll").prop('checked',false);
	}
}

//Coifx 통계 검색
function FP_CofixSearch() {

	var BasicYear = $("#BasicYear option:selected").val();

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/compare/cofix_search_result.php",
	{ 
		'BasicYear': BasicYear

	},function(data,status){
		setTimeout(function(){
			$("#SearchResult").html(data);
			//$('html, body').animate({ scrollTop : 700 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}

//단기 Coifx 통계 검색
function FP_CofixSearch2() {

	var BasicYear_W = $("#BasicYear_W option:selected").val();

	var currentWidth = $(window).width();
	var LocWidth = (currentWidth / 2);
	var body_width =  screen.width-20;
	var body_height =  $('html body').height()+100;
	
	$("div[id='SysBg_White']").css({
		"width": body_width,
		"height": body_height,
		"opacity":"0.4",
		"position": "absolute",
		"z-index":"99"
	}).show();

	$("div[id='Roading']").css({  
		"top": "420px",  
		"left": LocWidth-10,
		"opacity":"0.8",
		"position": "absolute",
		"z-index":"200"
	}).show();

	$.post("/compare/cofix_search_result2.php",
	{ 
		'BasicYear_W': BasicYear_W

	},function(data,status){
		setTimeout(function(){
			$("#SearchResult2").html(data);
			//$('html, body').animate({ scrollTop : 1200 }, 500);
			$("div[id='Roading']").hide();
			$("div[id='SysBg_White']").hide();
		},500);
	});
}

function anonymitySubmit_newOk() {

	val = document.Form1;
	/*
	if(val.SITETYPE[0].checked == false && val.SITETYPE[1].checked == false) {
		alert("민원구분을 선택하세요.");
		val.SITETYPE[0].focus();
		return;
	}
	*/
	
	if(val.ID.value=="") {
		alert("아이디를 입력하세요.");
		val.ID.focus();
		return;
	}

	if(val.PWD.value=="") {
		alert("비밀번호를 입력하세요.\n\n비밀번호는 영문, 숫자 조합으로 8자 이상 입력하세요.");
		val.PWD.focus();
		return;
	}

	if (!CheckPassword(val.PWD.value)) {
		val.PWD.focus();
		return;
	}

	
	if(val.TITLE.value=="") {
		alert("제목을 입력하세요.");
		val.TITLE.focus();
		return;
	}

	if(val.TITLE.value.length > 200) {
		alert("제목은 200자 이내로 입력하세요.");
		val.TITLE.focus();
		return;
	}
		
	if(val.SUMMARY.value=="") {
		alert("요지를 입력하세요.");
		val.SUMMARY.focus();
		return;
	}

	if(val.SUMMARY.value.length > 20) {
		alert("요지는 20자 이내로 입력하세요.");
		val.SUMMARY.focus();
		return;
	}

	if(val.CONTENT.value=="") {
		alert("내용을 입력하세요.");
		val.CONTENT.focus();
		return;
	}

	if(val.CONTENT.value.length < 10) {
		alert("내용은 10자 이상 입력하세요.");
		val.CONTENT.focus();
		return;
	}

	SubmitConfirm = confirm("작성한 신청내역을 등록하시겠습니까?");

	if(SubmitConfirm==true) {
		$("#BtnSubmit").hide();
		$("#BtnWating").show();
		val.submit();
	}

}