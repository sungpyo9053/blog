/**
 *  공통 JS
 * @method ready
 */
 $(document).ready(function(){
   /**
    *  공통 모달팝업
    * @method modalPopup
    */
    $('[name="modalPopup"]').on("click", function(e) {
         showLoadingBar();
         $("#modalPopupDiv").attr('tabindex','-1');
         $("#modalPopupDiv").attr('role','dialog');

         var targetHref = this.dataset.bsHref;
         switch(targetHref){
            case "/keywordManage/selectKeywordSearchPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable');
                break;
            case "/menuManage/selectSitemapPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-fullscreen');
                $("#modalPopupDiv div:first").css("width" , "100%");
                break;
            case "/mainManage/selectExamCoursePop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog');
                break;
            case "/dtGuide/selectDtGuide02Pop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-lg modal-dialog-centered');
                break;
            case "/myPageManage/selectPersonalConsentPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-lg modal-dialog-centered');
                break;
            case "/commonManage/selectEnglishDrvLicnsPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-lg modal-dialog-centered');
                break;
            case "/photoManage/selectPhotoInserInfoPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-xlg modal-dialog-centered');
                break;
            case "/photoManage/selectPhotoEditPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-xlg modal-dialog-centered');
                break;
            case "/errorRpUtil/errRptPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-xlg modal-dialog-centered');
                break;
            case "/enMenuManage/selectEnSitemapPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-fullscreen');
                $("#modalPopupDiv div:first").css("width" , "100%");
                break;
            default:
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-dialog-centered');
            break;
         }

         $("#modalPopupDiv div div").empty();
         var param  = {"focusId" : $(this).data('bsId') };
         $("#modalPopupDiv .modal-content").load($(this).data('bsHref'), param, function(e){
             $("#modalPopupDiv").modal({
                 show : true});
         });
         hideLoadingBar(); //로딩바 숨기기
         e.preventDefault();
    });

    $('[data-bs-target="#modalPopupDiv"]').on("click", function(e) {
         showLoadingBar();
         $("#modalPopupDiv").attr('tabindex','-1');
         $("#modalPopupDiv").attr('role','dialog');

         var targetHref = this.dataset.bsHref;
         switch(targetHref){
            case "/keywordManage/selectKeywordSearchPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable');
                break;
            case "/menuManage/selectSitemapPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-fullscreen');
                $("#modalPopupDiv div:first").css("width" , "100%");
                break;
            case "/mainManage/selectExamCoursePop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog');
                break;
            case "/dtGuide/selectDtGuide02Pop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-lg modal-dialog-centered');
                break;
            case "/myPageManage/selectPersonalConsentPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-lg modal-dialog-centered');
                break;
            case "/commonManage/selectEnglishDrvLicnsPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-lg modal-dialog-centered');
                break;
            case "/photoManage/selectPhotoInserInfoPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-xlg modal-dialog-centered');
                break;
            case "/photoManage/selectPhotoEditPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-xlg modal-dialog-centered');
                break;
            case "/errorRpUtil/errRptPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-xlg modal-dialog-centered');
                break;
            case "/enMenuManage/selectEnSitemapPop.do":
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-fullscreen');
                $("#modalPopupDiv div:first").css("width" , "100%");
                break;
            default:
                $("#modalPopupDiv div:first").removeClass();
                $("#modalPopupDiv div:first").addClass('modal-dialog modal-dialog-centered');
            break;
         }

         $("#modalPopupDiv div div").empty();
         var param  = {"focusId" : $(this).data('bsId') };
         $("#modalPopupDiv .modal-content").load($(this).data('bsHref'), param, function(e){
             $("#modalPopupDiv").modal({
                 show : true});
         });
         hideLoadingBar(); //로딩바 숨기기
         e.preventDefault();
    });

    $(document).ajaxStart(function(){
        //showLoadingBar(); //로딩바 보이기
    });

    $(document).ajaxStop(function(){
        //hideLoadingBar(); //로딩바 숨기기
    });
});

/**
 * 로딩바 보이기
 * @method showLoadingBar
 * @example
 * showLoadingBar();
 */
function showLoadingBar() {
    var loadingImg="";
    loadingImg+="<div id='progress' style='position:fixed;left:0;right:0;top:0;height:100%;background:transparent;z-index:9000;'>",
    loadingImg+="<div id='loadingImg' style='display:flex;height:100px;align-items:center;justify-content:center;position:relative;top:50%;transform:translateY(-50%);'>",
    loadingImg+="<div class='spinner'>&nbsp;</div>",
    loadingImg+="</div>",
    loadingImg+="</div>",
    $("body").append(loadingImg),
    setTimeout(function() { $("#loadingImg").show();}, 0);
}

/**
 * 로딩바 숨기기
 * @method hideProgress
 * @example
 * hideLoadingBar();
 */
function hideLoadingBar() {
     $('#progress').hide();
     $('#progress').remove();
}

/**
 * 공통 Return 팝업 호출
 * @method fnCommonReturnPopup
 * @param  팝업 호출시 표시되는 메시지
 * @example
 * fnCommonReturnPopup(param);
 */
function fnCommonReturnPopup(param) {
    var param  = { "popUpMsg"  : param };
    //공통 Return 팝업 호출 후 리턴
    fnCommonReturnPopupReturn(param).then(function(result){
        if(result){
            $("#modalReturnDiv").modal("hide");
        }
     });
}

/**
 * 공통 Return 팝업 호출 후 리턴
 * @method fnCommonReturnPopupReturn
 */
function fnCommonReturnPopupReturn(param) {
    $("#modalReturnDiv").attr('tabindex','-1');
    $("#modalReturnDiv").attr('role','dialog');
    return new Promise(function(resolve){
    //팝업 컨텐츠 로드
    $("#modalReturnDiv div div").empty();
    $("#modalReturnDiv .modal-content").load("/commonManage/selectCommonReturnPop.do", param, function(e){
            $("#returnButton").on("click", function(){
                resolve(true);
            });
            $("#modalReturnDiv").modal("show");
        });
    });
}

/**
 * 공통 Return 팝업 호출 > 확인클릭시 HOME으로 이동
 * @method fnCommonReturnHomePopup
 * @param  팝업 호출시 표시되는 메시지
 * @example
 * fnCommonReturnHomePopup(param);
 */
function fnCommonReturnHomePopup(param) {
     var param  = { "popUpMsg"  : param };
    //공통 Return 팝업 호출 후 리턴
    fnCommonReturnHomePopupReturn(param).then(function(result){
        if(result){
            $("#modalReturnHomeDiv").modal("hide");
            location.href="/main.do";
        }
     });
}

/**
 * 공통 Return 팝업 호출 > 확인클릭시 HOME으로 이동
 * @method fnCommonReturnHomePopupReturn
 */
function fnCommonReturnHomePopupReturn(param) {
    $("#modalReturnHomeDiv").attr('tabindex','-1');
    $("#modalReturnHomeDiv").attr('role','dialog');
    return new Promise(function(resolve){
    //팝업 컨텐츠 로드
    $("#modalReturnHomeDiv div div").empty();
    $("#modalReturnHomeDiv .modal-content").load("/commonManage/selectCommonReturnHomePop.do", param, function(e){
            $("#returnHomeButton").on("click", function(){
                resolve(true);
            });
            $("#modalReturnHomeDiv").modal("show");
        });
    });
}

/**
 * 공통 Alert 팝업 호출
 * @method fnCommonAlertPopup
 * @param  팝업 호출시 표시되는 메시지
 * var param  = {
 *           "focusId"     : "eduLocation",   //리턴되는 포커스 ID
 *           "popUpTitle"  : "<c:out value="${title}"/>", //팝업 타이틀
 *           "popUpMsg"    : "<spring:message code="warn.sd0003.msg" javaScriptEscape="true"/>"}; //팝업 메세지
 * @example
 * fnCommonAlertPopup(param);
 */
function fnCommonAlertPopup(param) {
    //공통 Alert 팝업 호출 후 리턴
    fnCommonAlertPopupReturn(param).then(function(result){
        if(result){
            $("#modalAlertDiv").modal("hide");
            setTimeout(function() {
                //console.log($("#"+param.focusId).prop("tagName"));
                if($("#"+param.focusId).prop("tagName") == 'INPUT' || $("#"+param.focusId).prop("tagName") == 'SELECT' || $("#"+param.focusId).prop("tagName") == 'A'){
                    $("#"+param.focusId).focus();
                }
                if($("#"+param.focusId).prop("tagName") == 'BUTTON'){
                    $("#"+param.focusId).attr("autofocus", true);
                    $("#"+param.focusId).focus();
                }
                if($("#"+param.focusId).prop("tagName") == 'DIV'){
                    $("#"+param.focusId).attr("tabindex", 0).focus();
                }
            }, 50);
        }
     });
}

/**
 * 공통 Alert 팝업 호출 후 리턴
 * @method fnCommonAlertPopupReturn
 */
function fnCommonAlertPopupReturn(param) {
    $("#modalAlertDiv").attr('tabindex','-1');
    $("#modalAlertDiv").attr('role','dialog');
    return new Promise(function(resolve){
    //팝업 컨텐츠 로드
    $("#modalAlertDiv div div").empty();
    $("#modalAlertDiv .modal-content").load("/commonManage/selectCommonAlertPop.do", param, function(e){
            $("#alertButton").on("click", function(){
                resolve(true);
            });
            $("#modalAlertDiv").modal("show");
        });
    });
}

/**
 * 공통 Confirm 팝업
 * @method fnCommonConfirmPopup
 * @param  팝업 호출시 표시되는 메시지
 * var param  = {
 *           "popUpTitle"  : "<c:out value="${title}"/>", //팝업 타이틀
 *           "popUpMsg"    : "<spring:message code="warn.sd0003.msg" javaScriptEscape="true"/>"}; //팝업 메세지
 * @example
 * fnCommonConfirmPopup(param);
 */
function fnCommonConfirmPopup(param){
    $("#modalConfirmDiv").attr('tabindex','-1');
    $("#modalConfirmDiv").attr('role','dialog');
    return new Promise(function(resolve){
    //팝업 컨텐츠 로드
    $("#modalConfirmDiv div div").empty();
    $("#modalConfirmDiv .modal-content").load("/commonManage/selectCommonConfirmPop.do", param, function(e){
            $("#confirmButton").on("click", function(){
                resolve(true);
            });

            $("#cancelButton").on("click", function(){
                resolve(false);
            });

            $("#modalConfirmDiv").modal("show");
        });
    });
}

/**
 * 로그인 Alert 팝업 호출
 * @method fnLoginAlertPopup
 * @param  팝업 호출시 표시되는 메시지
 * var param  = {
 *           "focusId"     : "eduLocation",   //리턴되는 포커스 ID
 *           "popUpTitle"  : "<c:out value="${title}"/>", //팝업 타이틀
 *           "popUpMsg"    : "<spring:message code="warn.sd0003.msg" javaScriptEscape="true"/>"}; //팝업 메세지
 * @example
 * fnLoginAlertPopup(param);
 */
function fnLoginAlertPopup(param) {
    //공통 Alert 팝업 호출 후 리턴
    fnLoginAlertPopupReturn(param).then(function(result){
        if(result){
            $("#modalAlertDiv").modal("hide");
            setTimeout(function() {
                //console.log($("#"+param.focusId).prop("tagName"));
                if($("#"+param.focusId).prop("tagName") == 'INPUT' || $("#"+param.focusId).prop("tagName") == 'SELECT' || $("#"+param.focusId).prop("tagName") == 'A'){
                    $("#"+param.focusId).focus();
                }
                if($("#"+param.focusId).prop("tagName") == 'BUTTON'){
                    $("#"+param.focusId).attr("autofocus", true);
                    $("#"+param.focusId).focus();
                }
                if($("#"+param.focusId).prop("tagName") == 'DIV'){
                    $("#"+param.focusId).attr("tabindex", 0).focus();
                }
            }, 50);
        }
     });
}

/**
 * 로그인 Alert 팝업 호출 후 리턴
 * @method fnLoginAlertPopupReturn
 */
function fnLoginAlertPopupReturn(param) {
    $("#modalAlertDiv").attr('tabindex','-1');
    $("#modalAlertDiv").attr('role','dialog');
    return new Promise(function(resolve){
    //팝업 컨텐츠 로드
    $("#modalAlertDiv div div").empty();
    $("#modalAlertDiv .modal-content").load("/loginManage/selectLoginAlertPop.do", param, function(e){
            $("#alertButton").on("click", function(){
                if($("#"+param.focusId).prop("tagName") == 'INPUT' && param.focusId == 'ssoError'){
                    fnSsoErrorAlertConfirm();
                    resolve(true);
                }else{
                    fnAlertConfirm();
                    resolve(true);
                }
            });
            $("#moveButton").on("click", function(){
                //console.log("popUpReturnUrl==>>"+param.popUpReturnUrl);
                //console.log("popUpReturnMenuCd==>>"+param.popUpReturnMenuCd);
                fnMoveConfirm(param.popUpReturnUrl, param.popUpReturnMenuCd);
                resolve(true);
            });
            $("#modalAlertDiv").modal("show");
        });
    });
}

/**
 * 공통 팝업 URL 이동 팝업
 * @method fnCommonReturnUrlPopup
 * @param  팝업 호출시 표시되는 메시지
 * var param  = {
 *           "popUpTitle"  : "<c:out value="${title}"/>", //팝업 타이틀
 *           "popUpMsg"    : "<spring:message code="warn.sd0003.msg" javaScriptEscape="true"/>",
 *           "reMenuCd"    : "MN-PO-1121",
 *           "reMenuUrl"   : "/applyTfcSftEdu/selectApplyTfcSftEduSchedule.do"};
 * @example
 * fnCommonReturnUrlPopup(param);
 */
function fnCommonReturnUrlPopup(param) {
    //공통 팝업 URL 이동 팝업 호출 후 리턴
    fnCommonReturnUrlPopupReturn(param).then(function(result){
        if(result){
            $("#modalReturnUrlDiv").modal("hide");
            setTimeout(function() {
                fnCommonMovePage(param.reMenuUrl, param.reMenuCd);
            }, 50);
        }
     });
}

/**
 * 공통 팝업 URL 이동 팝업 호출 후 리턴
 * @method fnCommonReturnUrlPopupReturn
 */
function fnCommonReturnUrlPopupReturn(param) {
    $("#modalReturnUrlDiv").attr('tabindex','-1');
    $("#modalReturnUrlDiv").attr('role','dialog');
    return new Promise(function(resolve){
    //팝업 컨텐츠 로드
    $("#modalReturnUrlDiv div div").empty();
    $("#modalReturnUrlDiv .modal-content").load("/commonManage/selectCommonReturnUrlPop.do", param, function(e){
            $("#returnUrlButton").on("click", function(){
                resolve(true);
            });
            $("#modalReturnUrlDiv").modal("show");
        });
    });
}

/**
 * 공통 사진적합성 결과 팝업 호출
 * @method fnCommonAlertPopup
 * @param  팝업 호출시 표시되는 메시지
 * var param  = {
 *           "popUpTitle"  : "<c:out value="${title}"/>", //팝업 타이틀
 *           "popUpMsg"    : "<spring:message code="warn.sd0003.msg" javaScriptEscape="true"/>"}; //팝업 메세지
 * @example
 * fnCommonFaceResultPopup(param);
 */
function fnCommonFaceResultPopup(param){
    $("#modalPopupDiv div div").empty();
    $("#modalPopupDiv").children()[0].className = "modal-dialog modal-lg modal-dialog-centered"; //팝업 크기 설정
    $("#modalPopupDiv .modal-content").load("/commonManage/selectCommonPhotoValidateResultPop.do", param, function(e){
        $("#modalPopupDiv").modal("show");
    });
}

/*
 * OZ 보고서 출력
 * @method showReport
 * @param {cpr.core.AppInstance} app 앱인스턴스
 * @param {{jsondata:Object|Array<!-- 리포트에 보낼 JSON 혹은 JSONArray -->,reportname:String<!-- 리포트양식 파일 경로(.ozr확장자 포함) -->,
 * displayname:String<!-- 뷰어에 표시될 리포트명 -->}} poReportParam 오즈관련 파라미터
 * @example
 * showReport();
 */
function showReport() {
    var form = document.ozForm;
    var reportObj = form.elements['reportObj'].value;
    var obj = JSON.parse(reportObj);
    var reportname = "";
    Object.entries(obj).forEach(([key, value]) =>{
        if(key == "reportname"){
            reportname = value;
        }
    });
    if(reportname == ""){
        var param  = {
            "popUpMsg"    : "비정상적인 접근입니다."
        };
        fnCommonAlertPopup(param);
    }else{
        var strOption = "";
        //var isMobile = fnCommonMobileChk();
        var isMobile = form.elements['isMobile'].value;
        if (isMobile == "Y"){
            strOption = "width=626 height=800 top="+(screen.height-500)/2+" left="+(screen.width-800)/2+" scrollbars=no menubar=no status=no location=no titlebar=no";
        }else{
            strOption = "width=1200 height=800 top="+(screen.height-500)/2+" left="+(screen.width-800)/2+" scrollbars=yes menubar=no status=no location=no titlebar=no";
        }
        window.open("about:blank","ozViewer",strOption);
        form.target = "ozViewer";
        form.action = fnReportActUrl(isMobile);
        form.submit();
    }
}

/*
 * 리포트 액션URL 리턴
 * @method fnReportActUrl
 * @example
 * fnReportActUrl(isMobile);
 * 현재 URL에 "safedriving.or.kr" 포함이면 운영, 아니면, 개발 서버로 isMobile 여부와 운영/개발 에 맞는 리포트 호출 action URL 을 리턴 한다.
 */
function fnReportActUrl(isMobile){
    var aUrl, strMobile;
    var cUrl = window.location.host;
    var sPort = window.location.port;
    if(sPort != null && sPort != ""){
        sPort = ":"+sPort;
    }else{
        sPort = "";
    }
    isMobile == "Y" ? strMobile = "Mobile" : strMobile = "";
    if(cUrl.toLowerCase().indexOf("safedriving.or.kr") != -1){
        aUrl = "https://report.koroad.or.kr/report/safeDrv"+strMobile+"Viewer.jsp";
    }else{
        aUrl = "https://devreport.koroad.or.kr/sample/safeDrv"+strMobile+"Viewer.jsp";
    }
    return aUrl;
}

/*
 * 연습면허 발급 리포트 액션URL 리턴
 * @method fnIssueReportActUrl
 * @example
 * fnIssueReportActUrl(isMobile);
 * 현재 URL에 "safedriving.or.kr" 포함이면 운영, 아니면, 개발 서버로 isMobile 여부와 운영/개발 에 맞는 리포트 호출 action URL 을 리턴 한다.
 */
function fnIssueReportActUrl(isMobile){
    var aUrl, strMobile;
    var cUrl = window.location.host;
    var sPort = window.location.port;
    if(sPort != null && sPort != ""){
        sPort = ":"+sPort;
    }else{
        sPort = "";
    }
    isMobile == "Y" ? strMobile = "Mobile" : strMobile = "";
    if(cUrl.toLowerCase().indexOf("safedriving.or.kr") != -1){
        aUrl = "https://report.koroad.or.kr/report/safeDrv"+strMobile+"IssueViewer.jsp";
    }else{
        aUrl = "https://devreport.koroad.or.kr/sample/safeDrv"+strMobile+"IssueViewer.jsp";
    }
    return aUrl;
}

/*
 * OZ 보고서 출력(모바일 테스트용_임시_추후삭제)
 * @method showMTestReport
 * @param {cpr.core.AppInstance} app 앱인스턴스
 * @param {{jsondata:Object|Array<!-- 리포트에 보낼 JSON 혹은 JSONArray -->,reportname:String<!-- 리포트양식 파일 경로(.ozr확장자 포함) -->,
 * displayname:String<!-- 뷰어에 표시될 리포트명 -->}} poReportParam 오즈관련 파라미터
 * @example
 * showMTestReport();
 */
function showMTestReport() {
    var form = document.ozForm;
    var strOption = "";
    var isMobile = fnCommonMobileChk();
    isMobile = "Y"; //테스트를 위해 변경
    if (isMobile == "Y"){
        strOption = "width=626 height=800 top="+(screen.height-500)/2+" left="+(screen.width-800)/2+" scrollbars=no menubar=no status=no location=no titlebar=no";
    }else{
        strOption = "width=1200 height=800 top="+(screen.height-500)/2+" left="+(screen.width-800)/2+" scrollbars=yes menubar=no status=no location=no titlebar=no";
    }
    window.open("about:blank","ozViewer",strOption);
    form.target = "ozViewer";
    form.action = fnReportActUrl(isMobile);
    form.submit();
}

/*
 * 모바일 사용자 체크
 * @method fnCommonMobileChk
 * @example
 * fnCommonMobileChk();
 * isMobile="N" 이면 PC사용자, isMobile="Y"이면 모바일 사용자이다.
 */
function fnCommonMobileChk(){
    var varUA = navigator.userAgent;
    varUA = varUA.toLowerCase();
    var phoneArray = new Array('iphone', 'ipod', 'android', 'windows ce', 'blackberry', 'symbian', 'windows phone', 'webos', 'opera mini', 'opera mobi', 'polaris', 'iemobile', 'lgtelecom', 'lgtelcom', 'nokia', 'sonyericsson', 'natebrowser', 'samsung', 'sch-','shw-', 'sph-', 'sgh-', 'lg-', 'canu', 'im-', 'ev-');
    var isMobile = "N";

    for(var i=0; i < phoneArray.length; i++) {
        if(varUA.indexOf(phoneArray[i]) > -1) {
            isMobile = "Y";
        }
    }
    return isMobile;
}

/*
 * 전화번호 포맷 변경
 * @method showReport
 * @param {string} tmpTelNo 포맷하고자 하는 전화번호
 * @example
 * fnCommonMakeTelno(tmpTelNo);
 */
function fnCommonMakeTelno(tmpTelNo){
    var rtnFormatTelNo = tmpTelNo;
    if(/[^0123456789]/g.test(tmpTelNo)) {
       //fnCommonAlertPopup("숫자가 아닙니다.\n\n0-9의 숫자만 입력해 주시기 바랍니다.");
       //tmpTelNo=tmpTelNo.replace(/(\,|\.|\-|\/|\:)/g,"");  // 문자입력시 제거
       tmpTelNo=tmpTelNo.replace(/[^0-9]/g,"");  // 문자입력시 제거
    }

    if(isNaN(tmpTelNo)){
        rtnFormatTelNo = tmpTelNo;
    }else{
        if(tmpTelNo.length <= 3){
            rtnFormatTelNo = tmpTelNo;
        }else if(tmpTelNo.length >= 4 && tmpTelNo.length <= 7){
            rtnFormatTelNo = tmpTelNo.substring(0,3)+"-"+tmpTelNo.substring(3);
        }else if(tmpTelNo.length >= 8 && tmpTelNo.length <= 11){
            rtnFormatTelNo = tmpTelNo.substring(0,3)+"-"+tmpTelNo.substring(3,7)+"-"+tmpTelNo.substring(7);
        }else{
            rtnFormatTelNo = tmpTelNo.substring(0,3)+"-"+tmpTelNo.substring(3,7)+"-"+tmpTelNo.substring(7,11);
        }
    }
    //console.log("====>"+rtnFormatTelNo);
    return rtnFormatTelNo;
 }

/*
 * 주민등록번호 포맷 변경
 * @method fnCommonMakeRdrgNo
 * @param {string} tmpRdrgNo 포맷하고자 하는 주민등록번호
 * @example
 * fnCommonMakeRdrgNo(tmpRdrgNo);
 */
function fnCommonMakeRdrgNo(tmpRdrgNo){
    var rtnFormatNo = tmpRdrgNo;
    if(/[^0123456789]/g.test(tmpRdrgNo)) {
       tmpRdrgNo=tmpRdrgNo.replace(/[^0-9]/g,"");  // 문자입력시 제거
    }

    if(isNaN(tmpRdrgNo)){
        rtnFormatNo = tmpRdrgNo;
    }else{
        if(tmpRdrgNo.length <= 6){
            rtnFormatNo = tmpRdrgNo;
        }else if(tmpRdrgNo.length >= 7 && tmpRdrgNo.length <= 13){
            rtnFormatNo = tmpRdrgNo.substring(0,6)+"-"+tmpRdrgNo.substring(6);
        }else{
            rtnFormatNo = tmpRdrgNo.substring(0,6)+"-"+tmpRdrgNo.substring(6,13);
        }
    }
    //console.log("====>"+rtnFormatNo);
    return rtnFormatNo;
}

 /*
 * 날짜 포맷 변경
 * @method fnCommonMakeYmd
 * @param {string} tempDate 포맷하고자 하는 날짜
 * @example
 * fnCommonMakeYmd(tempDate);
 */
function fnCommonMakeYmd(tempDate){
    var rtnFormatDate = tempDate;
    if(/[^0123456789]/g.test(tempDate)) {
       tempDate=tempDate.replace(/[^0-9]/g,"");  // 문자입력시 제거
    }

    if(isNaN(tempDate)){
        rtnFormatDate = tempDate;
    }else{
        if(tempDate.length <= 4){
            rtnFormatDate = tempDate;
        }else if(tempDate.length >= 5 && tempDate.length <= 6){
            rtnFormatDate = tempDate.substring(0,4)+"-"+tempDate.substring(4);
        }else if(tempDate.length >= 7 && tempDate.length <= 8){
            rtnFormatDate = tempDate.substring(0,4)+"-"+tempDate.substring(4,6)+"-"+tempDate.substring(6);
        }else{
            rtnFormatDate = tempDate.substring(0,4)+"-"+tempDate.substring(4,6)+"-"+tempDate.substring(6,8);
        }
    }
    //console.log("====>"+rtnFormatDate);
    return rtnFormatDate;
 }

/*
 * 페이지 이동
 * @method fnCommonMovePage
 * @param {string} url 이동하고자하는 페이지
 *        {string} menuCd 메뉴코드
 * @example
 * fnCommonMovePage(url, menuCd);
 */
function fnCommonMovePage(url, menuCd){
    showLoadingBar();
    var form = document.commonForm;
    form.elements['menuCd'].value = menuCd;
    form.target="_self";
    form.action = url;
    form.submit();
}

/*
 * 브레드크럼 페이지 이동
 * @method fnForwardMovePage
 * @param {string} url 이동하고자하는 페이지
 * @example
 * fnForwardMovePage(url);
 */
function fnForwardMovePage(url){
    showLoadingBar();
    var form = document.commonForm;
    form.elements['menuCd'].value = url.split('?menuCd=')[1];
    form.target="_self";
    form.action = url.split('?menuCd=')[0];
    form.submit();
}

/*
 * 페이지 오픈
 * @method fnCommonOpenPage
 * @param {string} url 오픈하고자하는 페이지
 *        {string} menuCd 메뉴코드
 * @example
 * fnCommonOpenPage(url, menuCd);
 */
function fnCommonOpenPage(url, menuCd){
    var form = document.commonForm;
    form.elements['menuCd'].value = menuCd;
    var width = 1200;
    var xPos = (document.body.offsetWidth/2) - (width/2);
    xPos += window.screenLeft;
    var pop;
    var strOption = "";
    strOption = "width=1200 height=750 top=100 left="+xPos+" scrollbars=yes resizable=yes";
    window.open("about:blank","pop",strOption);
    form.target = "pop";
    form.action = url;
    form.submit();
}

/*
 * 새창으로 페이지 이동
 * @method fnCommonMoveNewPage
 * @param {string} url 이동하고자하는 페이지
 * @example
 * fnCommonMoveNewPage(url);
 */
function fnCommonMoveNewPage(url){
    var form = document.commonForm;
    form.target="_blank";
    form.action = url;
    form.submit();
}

/*
 * 페이지 이동(이전 페이지 포함)
 * @method fnCommonBackPage
 * @param {string} url 이동하고자하는 페이지
 *        {string} menuCd 메뉴코드
 *        {string} reMenuUrl 되돌아가고자하는 페이지
 *        {string} reMenuCd 이전 메뉴코드
 * @example
 * fnCommonBackPage(url, menuCd, reUrl, reMenuCd);
 */
function fnCommonBackPage(url, menuCd, reMenuUrl, reMenuCd){
    showLoadingBar();
    var form = document.commonForm;
    form.elements['menuCd'].value = menuCd;
    form.elements['reMenuUrl'].value = reMenuUrl;
    form.elements['reMenuCd'].value = reMenuCd;
    form.target="_self";
    form.action = url;
    form.submit();
}

/*
 * 페이지 이동(영문페이지)
 * @method fnCommonMoveEngPage
 * @param {string} url 이동하고자하는 페이지
 *        {menuCd} 메뉴코드
 *        {langFlag} 다국어 구분 : en(영문), ko(국문)
 * @example
 * fnCommonMoveEngPage(url, menuCd, langFlag);
 */
function fnCommonMoveEngPage(url, menuCd, langFlag){
    showLoadingBar();
    var form = document.commonForm;
    form.elements['langFlag'].value = langFlag;
    form.elements['menuCd'].value = menuCd;
    form.target="_self";
    form.action = url;
    form.submit();
}

/*
 * 위임장 다운로드 페이지 이동
 * @method fnTmpltDownloadPage
 * @param {string} reMenuUrl 되돌아가고자하는 페이지
 *        {string} reMenuCd 이전 메뉴코드
 * @example
 * fnTmpltDownloadPage(reMenuUrl, reMenuCd);
 */
function fnTmpltDownloadPage(reMenuUrl, reMenuCd){
    showLoadingBar();
    var form = document.commonForm;
    form.elements['menuCd'].value   = "MN-PO-1715"; //관련서식내려받기
    form.elements['bbscttSn'].value = "1381";
    form.elements['reMenuUrl'].value = reMenuUrl;
    form.elements['reMenuCd'].value = reMenuCd;
    form.action = "/boardManage/selectTmpltBoard.do"; //위임장 다운로드 페이지이동
    form.submit();
}

/*
 * 탭 이동
 * @method fnCommonMoveTab
 * @param {string} url 이동하고자하는 페이지
 *        {string} menuCd 메뉴코드
 * @example
 * fnCommonMoveTab(url);
 */
function fnCommonMoveTab(url, menuCd){
    showLoadingBar();
    var form = document.commonForm;
    form.elements['menuCd'].value = menuCd;
    form.target="_self";
    form.action = url;
    form.submit();
}

/*
 * 챗봇 배너링크 팝업
 * @method fnChatbotPopup
 * @example
 * fnChatbotPopup();
 */
function fnChatbotPopup(){
    showLoadingBar();
    var form = document.commonForm;
    window.open("", "chatbot_popup", "width=550, height=800");
    form.action = "https://chatbot.ips.go.kr/chatbotPop.ndo";
    form.target = "chatbot_popup";
    form.method = "post";
    form.submit();
    hideLoadingBar();
}

/*
 * 모바일 화면 팝업
 * @method fnMobilePopup
 * @example
 * fnMobilePopup(url);
 */
function fnMobilePopup(url){
    showLoadingBar();
    var form = document.commonForm;
    window.open("", "mobilePopup", "width=470px;, height=800px;");
    form.action = url
    form.target = "mobilePopup";
    form.method = "post";
    form.submit();
    hideLoadingBar();
}

/**
 * 허용되는 사진 규격 팝업
 * @method fnCommonPhotoRule
 * @example
 * fnCommonPhotoRule();
 */
function fnCommonPhotoRule(focusId){
    var param  = {"focusId" : focusId };
    $("#modalPopupDiv").attr('tabindex','-1');
    $("#modalPopupDiv").attr('role','dialog');
    return new Promise(function(resolve){
    $("#modalPopupDiv").children()[0].className = "modal-dialog modal-lg modal-dialog-centered";
    $("#modalPopupDiv .modal-content").load("/commonManage/selectCommonPhotoRulePop.do", param, function(e){
            $("#modalPopupDiv").modal("show");
        });
    });
}

/**
 * 신분증 인정 범위 팝업
 * @method fnCommonIdAcceptRange
 * @example
 * fnCommonIdAcceptRange();
 */
function fnCommonIdAcceptRange(focusId){
    var param  = {"focusId" : focusId };
    $("#modalPopupDiv").attr('tabindex','-1');
    $("#modalPopupDiv").attr('role','dialog');
    return new Promise(function(resolve){
    $("#modalPopupDiv").children()[0].className = "modal-dialog modal-lg modal-dialog-centered";
    $("#modalPopupDiv .modal-content").load("/commonManage/selectCommonIdAcceptRangePop.do", param, function(e){
            $("#modalPopupDiv").modal("show");
        });
    });
}

/**
 * 사진 등록 시 유의사항 팝업
 * @method fnCommonPhotoNote
 * @example
 * fnCommonPhotoNote();
 */
function fnCommonPhotoNote(focusId){
    var param  = {"focusId" : focusId };
    $("#modalPopupDiv").attr('tabindex','-1');
    $("#modalPopupDiv").attr('role','dialog');
    return new Promise(function(resolve){
    $("#modalPopupDiv").children()[0].className = "modal-dialog modal-lg modal-dialog-centered";
    $("#modalPopupDiv .modal-content").load("/commonManage/selectCommonPhotoNotePop.do", param, function(e){
            $("#modalPopupDiv").modal("show");
        });
    });
}

/**
 * 사진적합성 결과 팝업
 * @method fnPhotoFaceResultPopup
 * @example
 * fnPhotoFaceResultPopup();
 */
function fnPhotoFaceResultPopup(param){
    $("#modalFaceResultDiv div div").empty();
    $("#modalFaceResultDiv").children()[0].className = "modal-dialog modal-lg modal-dialog-centered"; //팝업 크기 설정
    $("#modalFaceResultDiv .modal-content").load("/commonManage/selectCommonPhotoValidateResultPop.do", param, function(e){
        $("#modalFaceResultDiv").modal("show");
    });
}

/**
 * 전국시험장/교육장보기 팝업
 * @method fnExamCoursePopup
 * @example
 * fnExamCoursePopup();
 */
function fnExamCoursePopup(focusId){
    var param  = {"focusId" : focusId };
    $("#modal-main-map .modal-content").load("/mainManage/selectExamCoursePop.do", param, function(e){
        $("#modal-main-map").modal("show");
    });
}

/**
 * 모바일 검색어 지우기
 * @method fnSearchMobileDel
 * @example
 * fnSearchMobileDel();
 */
function fnSearchMobileDel(){
    $("#searchMobileNm").val("").focus();
    fnMenuSearchMobile();
    const searchDel = document.querySelector(".sch-input .search-del");
    searchDel.classList.remove("on");
}

/**
 * (영문) 모바일 검색어 지우기
 * @method fnSearchEnMobileDel
 * @example
 * fnSearchEnMobileDel();
 */
function fnSearchEnMobileDel(){
    $("#searchEnMobileNm").val("").focus();
    fnEnMenuSearchMobile();
    const searchDel = document.querySelector(".sch-input .search-del");
    searchDel.classList.remove("on");
}

/**
 * 넷퍼넬 체크
 * @method fnNetFunnelAction
 * @param {url} url 이동하고자하는 페이지
 *        {menuCd} 메뉴코드
 *        {opt} 메뉴에 대한 정의
 * @example
 * fnNetFunnelAction(url, menuCd, opt);
 */
function fnNetFunnelAction(url, menuCd, opt){
    NetFunnel_Action(
            {action_id : opt},{
                success:function(ev, ret){
                    showLoadingBar();
                    var form = document.commonForm;
                    var bypassFlag = NetFunnel.TS_BYPASS;
                    if(bypassFlag){
                        form.elements['netfunnelYn'].value = "N";
                    } else {
                        form.elements['netfunnelYn'].value = "Y";
                    }
                    var netFunnelKey = ret.data.key;
                    form.elements['netfunnelKey'].value = netFunnelKey;
                    form.elements['actionId'].value = opt;
                    form.elements['menuCd'].value = menuCd;
                    form.target="_self";
                    form.action = url;
                    form.submit();
                }, error:function (ev, ret){
                    //console.log(ev);
                    //console.log(ret);
                }
            }
    );
}

/**
 * 메인팝업 오늘하루 열지않음 클릭
 * @method fnMainPopupClose
 * @example
 * fnMainPopupClose();
 */
function fnMainPopupClose(){
    if($("#popupX").is(":checked")){
         setCookie("mainPopupList" ,"popupEnd", 1);
    }
    $("#main-pop").modal("hide");
}


/**
 * 쿠키 설정하기
 * @method setCookie
 * @param {cname} 쿠키명
 *        {value} 쿠키값
 *        {expire} 쿠키만료일
 * @example
 * setCookie(cname ,value, expire);
 */
function setCookie(cname ,value, expire){
    var todayValue= new Date();
    todayValue.setHours(00);
    todayValue.setMinutes(00);
    todayValue.setSeconds(00);
    todayValue.setDate(todayValue.getDate() + expire);
    document.cookie = cname + '=' + encodeURI(value) + ' ; path=/ ' + ' ;expires=' + todayValue.toGMTString() + ';';
}

/**
 * 쿠키 가져오기
 * @method getCookie
 * @param {cname} 쿠키명
 * @example
 * getCookie(cName);
 */
function getCookie(cName){
    cName = cName + "=";
    var cookieData = document.cookie;
    var start = cookieData.indexOf(cName);
    var cValue = "";
    if(start != -1){
        start += cName.length;
        var end = cookieData.indexOf(';' , start);
        if(end == -1) end = cookieData.length;
        cValue = cookieData.substring(start , end);
    }
    return cValue;
}

/*
 * 마이페이지에서 사진수정화면으로 이동
 * @method fnPhotoExchangePage
 * @param {string} url 이동하고자하는 페이지
 *        {string} menuCd 메뉴코드
 * @example
 * fnPhotoExchangePage(url, menuCd);
 */
function fnPhotoExchangePage(url, menuCd, lcnsNo){
    showLoadingBar();
    var form = document.commonForm;
    form.elements['menuCd'].value = menuCd;
    form.elements['jobType'].value = "myPage";
    form.elements['lcnsNo'].value = lcnsNo;
    form.target="_self";
    form.action = url;
    form.submit();
}

/*
 * base64 to blob 변환
 * @method base64ToBlob
 * @param {base64ToBlob} base64 이미지
 * @example
 * base64ToBlob(data);
 */
function base64ToBlob(data) {
    var rImageType = /data:(image\/.+);base64,/;
    var mimeString = '';
    var raw, uInt8Array, i;
    raw = data.replace(rImageType, function (header, imageType) {
        mimeString = imageType;
        return '';
    });
    raw = atob(raw);
    var rawLength = raw.length;
    uInt8Array = new Uint8Array(rawLength); // eslint-disable-line

    for (i = 0; i < rawLength; i += 1) {
        uInt8Array[i] = raw.charCodeAt(i);
    }

    return new Blob([uInt8Array], {
        type: mimeString
    });
}

/*
 * 사업자등록번호 포맷 변경
 * @method fnCommonMakeBnsno
 * @param {string} tmpBnsno 포맷하고자 하는 사업자등록번호
 * @example
 * fnCommonMakeBnsno(tmpBnsno);
 */
function fnCommonMakeBnsno(tmpBnsno){
    var rtnFormatBnsno = tmpBnsno;
    if(/[^0123456789]/g.test(tmpBnsno)) {
        tmpBnsno=tmpBnsno.replace(/[^0-9]/g,"");  //문자입력시 제거
    }
    if(isNaN(tmpBnsno)){
        rtnFormatBnsno = tmpBnsno;
    }else{
        if(tmpBnsno.length <= 3){
               rtnFormatBnsno = tmpBnsno;
        }else if(tmpBnsno.length >= 4 && tmpBnsno.length <= 5){
               rtnFormatBnsno = tmpBnsno.substring(0,3)+"-"+tmpBnsno.substring(3);
        }else if(tmpBnsno.length >= 6 && tmpBnsno.length <= 8){
               rtnFormatBnsno = tmpBnsno.substring(0,3)+"-"+tmpBnsno.substring(3,5)+"-"+tmpBnsno.substring(5);
        }else{
           rtnFormatBnsno = tmpBnsno.substring(0,3)+"-"+tmpBnsno.substring(3,5)+"-"+tmpBnsno.substring(5,10);
        }
    }
    return rtnFormatBnsno;
}

/**
 * 학과시험 방문시간 예약 안내 팝업
 * @method fnReserSubExamBtnPop
 * @example
 * fnReserSubExamBtnPop();
 */
function fnReserSubExamBtnPop(focusId){
    var param  = {"focusId" : focusId };
    //팝업 크기 설정
    $("#modalPopupDiv").children()[0].className = "modal-dialog modal-lg modal-dialog-centered";
    $("#modalPopupDiv div div").empty();
    $("#modalPopupDiv .modal-content").load("/dtGuide/selectDtGuide02Pop.do", param);
    $("#modalPopupDiv").modal("show");
}

/*
 * 오류등록 팝업
 * @method fnErrRptPopup
 * @example
 * fnErrRptPopup(sType);
 */
function fnErrRptPopup(sType){
    showLoadingBar();
    var form = document.commonForm;
    window.open("", "ErrRptPopup", "width=1300, height=650");
    var titleNm = document.title;
    titleNm = titleNm.replace("| 한국도로교통공단 안전운전 통합민원", "");
    var url = "";
    if(sType == "prod"){
        url = "https://admin.safedriving.or.kr/errRpt.do?menuNm="+titleNm;
    }else{
        url = "https://safeadmin.koroad.or.kr/errRpt.do?menuNm="+titleNm;
    }
    form.action = url;
    form.target = "ErrRptPopup";
    form.method = "post";
    form.submit();
    hideLoadingBar();
}


/*
 * 크로스사이트 스크립팅 치환 필터(<br> 태그는 치환에서 제외)
 * @method xssFilter
 * @example
 * xssFilter(str);
 */
function xssFilter(str) {
    //1.빈값일 경우 리턴
    if(str == null){
        return "";
    }

    //2. 전체 치환
    var result = String(str);
    //console.log("치환전 result :: " + result);
    result = result.replace(/&/g, "&amp;");
    result = result.replace(/</, "&lt;");
    result = result.replace(/>/, "&gt;");
    result = result.replace(/"/g, "&quot;");
    result = result.replace(/'/g, "&#39;");
    result = result.replace(/\//g, "&#x2F;");
    //console.log("전체치환후 result :: " + result);

    //<br> 태그만 복원
    result = result.replace(/&lt;br\s*\/?&gt;/gi, "<br>");
    //console.log("전체치환후 <br> 태그만 복원result :: " + result);

    return result;
}

/*
 * 달력(datepicker) 연도 선택 selectBox에 "년" 추가
 * @method addYearText
 * @example
 * addYearText();
 */
function addYearText(){
    setTimeout(function(){
        $('.ui-datepicker-year option').each(function (){
            if(!$(this).text().includes("년")){
                $(this).text($(this).text() + "년");
            }
        })
        $("#ui-datepicker-div").attr("tabindex", "0").focus();
    }, 1);
}

