
/*
 * 날짜 입력 시 형식 제한
 *
 * @method getRemoveFormat
 * @param  val 구분자 제거할 데이터
 */
function fnCommonMakeDate(dateNo)
{
    var formatDateNo = dateNo;
    if(/[^0123456789]/g.test(dateNo)) {
       dateNo=dateNo.replace(/[^0-9]/g,"");  //문자 입력 시 제거
    }
    if(isNaN(dateNo)){
        formatDateNo = dateNo;
    }else{ //날짜 입력 시 '2024-01-01' 형식으로 변환
        if(dateNo.length <= 4){
            formatDateNo = dateNo;
        }else if(dateNo.length >= 5 && dateNo.length <= 6){
            formatDateNo = dateNo.substring(0,4)+"-"+dateNo.substring(4);
        }else if(dateNo.length >= 7 && dateNo.length <= 8){
            formatDateNo = dateNo.substring(0,4)+"-"+dateNo.substring(4,6)+"-"+dateNo.substring(6);
        }else{
            formatDateNo = dateNo.substring(0,4)+"-"+dateNo.substring(4,6)+"-"+dateNo.substring(6,8);
        }
    }
    return formatDateNo;
 }

/*
 * 이메일 도메인 주소 선택 onChange
 *
 * @method selectDomain
 * @param  selectObj 이메일도메인값
 */
function selectDomainNm(selectObj)
{
    if (selectObj == "etc") {
        setTimeout(function(){$("#emlDminNm").focus();}, 50);
        $("#emlDminNm").val("");
        $("#emlDminNm").attr("readonly", false);
    }else{
        $("#emlDminNm").val(selectObj);
        $("#emlDminNm").attr("readonly", true);
    }
}

/**
 * 날짜체크
 *
 * @method isDate
 * @param  control 체크할 데이터
 * @param  msg 메시지
 */
function isDate(control, msg) {
    // '/'나 '-' 구분자 제거
    var val = getRemoveFormat(control);
    var focusId = '';
    if(msg == "출국일자")
    {
        focusId = '#datepicker1';
    }
    else if(msg == "예상종료일")
    {
        focusId = '#datepicker2';
    }
    // 숫자, length 확인
    if (isNumber(val, msg) && val.length == 8) {
        var year = val.substring(0,4);
        var month = val.substring(4,6);
        var day = val.substring(6,8);

        // 유효날짜 확인
        if(checkDate(year,month,day,msg)){
            return true;
        } else {
            return false;
        }
    } else {
        return false;
    }
}

/**
 * 구분자 제거
 *
 * @method getRemoveFormat
 * @param  val 구분자 제거할 데이터
 */
function getRemoveFormat(val) {
    if(val.length == 10) {
        var arrDate = new Array(3);
        arrDate = val.split("/");
        if(arrDate.length != 3) {
            arrDate = val.split("-");
        }
        return arrDate[0] + arrDate[1] + arrDate[2];
    } else {
        return val;
    }
}

/**
 * 입력값에 숫자만 있는지 체크
 *
 * @method isNumber
 * @param  val 문자열 체크할 input 객체
 */
function isNumber(val) {
    var regExp = /^[0-9]*$/;
    return regExp.test(val);
}

/**
 * 입력값에서 -를 없앤다.
 *
 * @method removeDash
 * @param  val 변경할 문자열
 */
function removeDash(val) {
    return val.replace(/-/gi,"");
}

/**
 * 유효날짜 확인
 *
 * @method checkDate
 * @param  varCk1 유효체크할 년
 * @param  varCk2 유효체크할 월
 * @param  varCk3 유효체크할 일
 * @param  msg 메시지
 */
function checkDate(varCk1, varCk2, varCk3, msg) {
    if (varCk1>="0001" && varCk1<="9999" && varCk2>="01" && varCk2<="12") {
        febDays = "29";
        if ((parseInt(varCk1,10) % 4) == 0) {
            if ((parseInt(varCk1,10) % 100) == 0 && (parseInt(varCk1,10) % 400) != 0){
                febDays = "28";
            }
        }else{
            febDays = "28";
        }
        if (varCk2=="01" && varCk3>="01" && varCk3<="31") return true;
        if (varCk2=="02" && varCk3>="01" && varCk3<=febDays) return true;
        if (varCk2=="03" && varCk3>="01" && varCk3<="31") return true;
        if (varCk2=="04" && varCk3>="01" && varCk3<="30") return true;
        if (varCk2=="05" && varCk3>="01" && varCk3<="31") return true;
        if (varCk2=="06" && varCk3>="01" && varCk3<="30") return true;
        if (varCk2=="07" && varCk3>="01" && varCk3<="31") return true;
        if (varCk2=="08" && varCk3>="01" && varCk3<="31") return true;
        if (varCk2=="09" && varCk3>="01" && varCk3<="30") return true;
        if (varCk2=="10" && varCk3>="01" && varCk3<="31") return true;
        if (varCk2=="11" && varCk3>="01" && varCk3<="30") return true;
        if (varCk2=="12" && varCk3>="01" && varCk3<="31") return true;
    }
    return false;
}

/**
 * 입력값이 사용자가 정의한 포맷 형식인지 체크
 * 자세한 format 형식은 자바스크립트의 'regular expression!'을 참조
 *
 * @method isValidFormat
 * @param  value 체크할 문자열 값
 * @param  format 포맷양식
 */
function isValidFormat(value,format)
{
    return format.test(value);
}

/**
 * 입력값이 전화번호 형식(숫자-숫자-숫자)인지 체크
 *
 * @method isValidPhone
 * @param  input 체크할 문자열
 */
function isValidPhone(input) {
    var format = /^(\d+)-(\d+)-(\d+)$/;
    return isValidFormat(input,format);
}

/**
 * 입력값이 이메일 형식인지 체크
 *
 * @method isValidEmailFst
 * @param  val 체크할 문자열
 */
function isValidEmailFst(val) {
    var regExp = /^((\w|[\-\.])+)$/;
    return regExp.test(val);
}

/**
 * 입력값이 이메일 형식인지 체크
 *
 * @method isValidEmailLst
 * @param  val 체크할 문자열
 */
function isValidEmailLst(val) {
    var regExp = /^((\w|[\-\.])+)\.([A-Za-z]+)$/;
    return regExp.test(val);
}

/*
 * 숫자만 입력가능 하도록
 * @method showReport
 * @param  tmpTelNo 포맷하고자 하는 전화번호
 */
function fnCommonMakeNum(tmpTelNo){
    var rtnFormatTelNo = tmpTelNo;
    if(/[^0123456789]/g.test(tmpTelNo)) {
       tmpTelNo=tmpTelNo.replace(/[^0-9]/g,"");  // 문자입력시 제거
    }
    rtnFormatTelNo = tmpTelNo;

    return rtnFormatTelNo;
}

/*
 * 숫자 입력불가능 하도록
 * @method fnCommonNoNum
 * @param  tmpTxt 포맷하고자 하는 텍스트
 */
function fnCommonNoNum(tmpTxt){
    var rtnFormatTmpTxt = tmpTxt;
    if(/[0123456789]/g.test(tmpTxt)) {
       tmpTxt=tmpTelNo.replace(/[0-9]/g,"");  // 문자입력시 제거
    }
    rtnFormatTmpTxt = tmpTxt;

    return rtnFormatTmpTxt;
 }

/*
 * 숫자 입력불가능 하도록
 * @method fnPreventNumKey
 * @param  event
 */
 function fnPreventNumKey(event)
 {
    if((event.key >= '0' && event.key<= '9'))
    {
        event.preventDefault();
    }
 }

/*
 * 값 비교
 * @method checkValue
 * @param  checker 비교값1
 * @param  checkee 비교값2
 */
function checkValue(checker, checkee) {
    var er = parseInt(checker);
    var ee = parseInt(checkee);
    if (er > ee) {
        return 1;
    }
    if (er == ee) {
        return 0;
    }
    return -1;
}
/*
 * YYYY년 MM월 DD일 형식으로 변경
 * @method addStr
 * @param  input YYYYMMDD형식
 */
function addStr(input) {
    return input.substring(0, 4) + '년 ' + input.substring(4, 6) + '월 ' + input.substring(6, 8) + '일';
}

/*
 * 날짜가 토요일인지 확인
 * @method isSaturday
 * @param  ymd
 */
function isSaturday(ymd) {
    var year = ymd.substr(0, 4);
    var month = ymd.substr(4, 2);
    var day = ymd.substr(6, 2);

    var holiday = new Date(year, month-1, day);

    if (holiday.getDay() == 6) {
        return true;
    } else {
        return false;
    }
}

/*
 * 날짜가 일요일인지 확인
 * @method isSunday
 * @param  ymd
 */
function isSunday(ymd) {
    var year = ymd.substr(0, 4);
    var month = ymd.substr(4, 2);
    var day = ymd.substr(6, 2);

    var holiday = new Date(year, month-1, day);

    if (holiday.getDay() == 0) {
        return true;
    } else {
        return false;
    }
}

/*
 * 음력 공휴일 지정
 * @method isLunarHoliday
 * @param  ymd
 */
function isLunarHoliday(ymd) {
    var i;
    var lunarHoliday = new Array("1229","1230", "0101", "0102", "0408", "0814", "0815", "0816");
    var monthday = ymd.substring(4, 8);

    for (i = 0; i < lunarHoliday.length; i++) {
        if (lunarHoliday[i] == monthday) {
            return true;
        }
    }
    return false;
}

function isSecondSaturday(ymd) {  // 음력 공휴일 지정
    var i;
    var secondSaturday = new Array("0309");

    var monthday = ymd.substring(4, 8);

    for (i = 0; i < secondSaturday.length; i++) {
        if (secondSaturday[i] == monthday) {
            return true;
        }
    }

    return false;
}

/*
 * 양력 공휴일 지정
 * @method isSolarHoliday
 * @param  ymd
 */
function isSolarHoliday(ymd) {
    var i;
    var solarHoliday = new Array("0101", "0301", "0501", "0505", "0606", "0717", "0815", "1003", "1009", "1225", "1005", "0209", "0503", "0719", "0816");
    var monthday = ymd.substring(4, 8);

    for (i = 0; i < solarHoliday.length; i++) {
        if (solarHoliday[i] == monthday) {
            return true;
        }
    }
    return false;
}

/*
 * 유효한 날짜 인지 확인
 * @method isValidYmd
 * @param  ymd
 */
function isValidYmd(ymd) {
    var result = false;
    $.ajax({
        async:false,
        cache:false,
        type:'POST',
        dataType:"json",
        url:  "/commonManage/selectIsValidYmdAx.do",
        data : {ymd : ymd},
        success:function(data){
            if(data.returnMessage == 'success'){
                if(data.validYn == 'Y'){
                    result = true;
                }else{
                    result = false;
                }
            }else{
                result = false;
            }
        },
        error:function(){
           result = false;
        }
    });

    return result;
}




/*
 * 양력 <-> 음력 변환 함수
 * @method isSolarHoliday
 * @param  year
 * @param  month
 * @param  day
 * @param  type : 1 - 양력 -> 음력
 *                2 - 음력 -> 양력
 * @param  leapmonth : 0 - 평달
 * @param              1 - 윤달 (type = 2 일때만 유효)
 */
function lunarCalc(year, month, day, type, leapmonth)
{
    // 음력 데이터 (평달 - 작은달 :1,  큰달:2 )
    // (윤달이 있는 달 - 평달이 작고 윤달도 작으면 :3 , 평달이 작고 윤달이 크면 : 4)
    // (윤달이 있는 달 - 평달이 크고 윤달이 작으면 :5,  평달과 윤달이 모두 크면 : 6)
    var lunarMonthTable = [
    [2, 1, 1, 2, 1, 1, 2, 1, 2, 2, 2, 1],
    [2, 2, 1, 1, 2, 1, 1, 2, 1, 2, 2, 1],
    [2, 2, 1, 5, 2, 1, 1, 2, 1, 2, 1, 2],   /* 2001 */
    [2, 2, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1],
    [2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2],
    [1, 5, 2, 2, 1, 2, 1, 2, 1, 2, 1, 2],
    [1, 2, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1],
    [2, 1, 2, 1, 2, 1, 5, 2, 2, 1, 2, 2],
    [1, 1, 2, 1, 1, 2, 1, 2, 2, 2, 1, 2],
    [2, 1, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2],
    [2, 2, 1, 1, 5, 1, 2, 1, 2, 1, 2, 2],
    [2, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 2],
    [2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 1],   /* 2011 */
    [2, 1, 2, 5, 2, 2, 1, 1, 2, 1, 2, 1],
    [2, 1, 2, 2, 1, 2, 1, 2, 1, 2, 1, 2],
    [1, 2, 1, 2, 1, 2, 1, 2, 5, 2, 1, 2],
    [1, 2, 1, 1, 2, 1, 2, 2, 2, 1, 2, 1],
    [2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 2],
    [1, 2, 1, 2, 1, 4, 1, 2, 1, 2, 2, 2],
    [1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 2, 2],
    [2, 1, 2, 1, 2, 1, 1, 2, 1, 1, 2, 2],
    [2, 1, 2, 5, 2, 1, 1, 2, 1, 2, 1, 2],
    [1, 2, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1],   /* 2021 */
    [2, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 2],
    [1, 5, 2, 1, 2, 1, 2, 2, 1, 2, 1, 2],
    [1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 2, 1],
    [2, 1, 2, 1, 1, 5, 2, 1, 2, 2, 2, 1],
    [2, 1, 2, 1, 1, 2, 1, 2, 1, 2, 2, 2],
    [1, 2, 1, 2, 1, 1, 2, 1, 1, 2, 2, 1],
    [2, 2, 2, 1, 5, 1, 2, 1, 1, 2, 2, 1],
    [2, 2, 1, 2, 2, 1, 1, 2, 1, 1, 2, 2],
    [1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 2, 1],
    [2, 1, 5, 2, 1, 2, 2, 1, 2, 1, 2, 1],   /* 2031 */
    [2, 1, 1, 2, 1, 2, 2, 1, 2, 2, 1, 2],
    [1, 2, 1, 1, 2, 1, 2, 1, 2, 2, 5, 2],
    [1, 2, 1, 1, 2, 1, 2, 1, 2, 2, 1, 2],
    [2, 1, 2, 1, 1, 2, 1, 1, 2, 2, 1, 2],
    [2, 2, 1, 2, 1, 4, 1, 1, 2, 2, 1, 2],
    [2, 2, 1, 2, 1, 1, 2, 1, 1, 2, 1, 2],
    [2, 2, 1, 2, 1, 2, 1, 2, 1, 1, 2, 1],
    [2, 2, 1, 2, 5, 2, 1, 2, 1, 2, 1, 1],
    [2, 1, 2, 2, 1, 2, 1, 2, 2, 1, 2, 1],
    [2, 1, 1, 2, 1, 2, 2, 1, 2, 2, 1, 2],   /* 2041 */
    [1, 5, 1, 2, 1, 2, 1, 2, 2, 1, 2, 2],
    [1, 2, 1, 1, 2, 1, 1, 2, 2, 1, 2, 2],
    [2, 1, 2, 1, 1, 2, 3, 2, 1, 2, 2, 2],
    [2, 1, 2, 1, 1, 2, 1, 1, 2, 1, 2, 2],
    [2, 1, 2, 1, 2, 1, 2, 1, 1, 2, 1, 2],
    [2, 1, 2, 2, 4, 1, 2, 1, 1, 2, 1, 2],
    [1, 2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1],
    [2, 1, 2, 1, 2, 2, 1, 2, 2, 1, 2, 1],
    [1, 2, 4, 1, 2, 1, 2, 2, 1, 2, 2, 1],
    [2, 1, 1, 2, 1, 1, 2, 2, 1, 2, 2, 2],   /* 2051 */
    [1, 2, 1, 1, 2, 1, 1, 5, 2, 2, 2, 2],
    [1, 2, 1, 1, 2, 1, 1, 2, 1, 2, 2, 2],
    [1, 2, 2, 1, 1, 2, 1, 1, 2, 1, 2, 2],
    [1, 2, 2, 1, 2, 4, 1, 1, 2, 1, 2, 1],
    [2, 2, 2, 1, 2, 1, 2, 1, 1, 2, 1, 2],
    [1, 2, 2, 1, 2, 1, 2, 2, 1, 1, 2, 1],
    [2, 1, 2, 4, 2, 1, 2, 1, 2, 2, 1, 1],
    [2, 1, 2, 1, 2, 1, 2, 2, 1, 2, 2, 1],
    [2, 1, 1, 2, 1, 1, 2, 2, 1, 2, 2, 1],
    [2, 2, 3, 2, 1, 1, 2, 1, 2, 2, 2, 1],   /* 2061 */
    [2, 2, 1, 1, 2, 1, 1, 2, 1, 2, 2, 1],
    [2, 2, 1, 2, 1, 2, 3, 2, 1, 2, 1, 2],
    [2, 2, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1],
    [2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2],
    [1, 2, 1, 2, 5, 2, 1, 2, 1, 2, 1, 2],
    [1, 2, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1],
    [2, 1, 2, 1, 1, 2, 2, 1, 2, 2, 1, 2],
    [1, 2, 1, 5, 1, 2, 1, 2, 2, 2, 1, 2],
    [2, 1, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2],
    [2, 1, 2, 1, 2, 1, 1, 5, 2, 1, 2, 2],   /* 2071 */
    [2, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 2],
    [2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 1],
    [2, 1, 2, 2, 1, 5, 2, 1, 2, 1, 2, 1],
    [2, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 2],
    [1, 2, 1, 2, 1, 2, 1, 2, 2, 1, 2, 1],
    [2, 1, 2, 3, 2, 1, 2, 2, 2, 1, 2, 1],
    [2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 2],
    [1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 2, 2],
    [2, 1, 5, 2, 1, 1, 2, 1, 2, 1, 2, 2],
    [1, 2, 2, 1, 2, 1, 1, 2, 1, 1, 2, 2],   /* 2081 */
    [1, 2, 2, 2, 1, 2, 3, 2, 1, 1, 2, 2],
    [1, 2, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1],
    [2, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 2],
    [1, 2, 1, 1, 6, 1, 2, 2, 1, 2, 1, 2],
    [1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 2, 1],
    [2, 1, 2, 1, 1, 2, 1, 2, 1, 2, 2, 2],
    [1, 2, 1, 5, 1, 2, 1, 1, 2, 2, 2, 1],
    [2, 2, 1, 2, 1, 1, 2, 1, 1, 2, 2, 1],
    [2, 2, 2, 1, 2, 1, 1, 5, 1, 2, 2, 1],
    [2, 2, 1, 2, 1, 2, 1, 2, 1, 1, 2, 1],   /* 2091 */
    [2, 2, 1, 2, 2, 1, 2, 1, 2, 1, 2, 1],
    [1, 2, 2, 1, 2, 4, 2, 1, 2, 1, 2, 1],
    [2, 1, 1, 2, 1, 2, 2, 1, 2, 2, 1, 2],
    [1, 2, 1, 1, 2, 1, 2, 1, 2, 2, 2, 1],
    [2, 1, 2, 3, 2, 1, 1, 2, 2, 2, 1, 2],
    [2, 1, 2, 1, 1, 2, 1, 1, 2, 2, 1, 2],
    [2, 2, 1, 2, 1, 1, 2, 1, 1, 2, 1, 2],
    [2, 5, 2, 2, 1, 1, 2, 1, 1, 2, 1, 2],
    [2, 2, 1, 2, 1, 2, 1, 2, 1, 1, 2, 1],
    [2, 2, 1, 2, 2, 1, 5, 2, 1, 1, 2, 1]];

    var solYear, solMonth, solDay;
    var lunYear, lunMonth, lunDay;
    var lunLeapMonth, lunMonthDay;
    var i, lunIndex;
    var result;

    var solMonthDay = [31, 0, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    /* range check */
    if (year < 2000 || year > 2101)
    {
       return "SD.W.0214";
    }
    /* 속도 개선을 위해 기준 일자를 여러개로 한다 */
    if (year >= 2080)
    {
        /* 기준일자 양력 2080년 1월 1일 (음력 2079년 12월 10일) */
        solYear = 2080;
        solMonth = 1;
        solDay = 1;
        lunYear = 2079;
        lunMonth = 12;
        lunDay = 10;
        lunLeapMonth = 0;

        solMonthDay[1] = 29; /* 2080 년 2월 28일 */
        lunMonthDay = 30; /* 2079년 12월 */
    }
    else if (year >= 2060)
    {
        /* 기준일자 양력 2060년 1월 1일 (음력 2059년 11월 28일) */
        solYear = 2060;
        solMonth = 1;
        solDay = 1;
        lunYear = 2059;
        lunMonth = 11;
        lunDay = 28;
        lunLeapMonth = 0;

        solMonthDay[1] = 29; /* 2060 년 2월 28일 */
        lunMonthDay = 30; /* 2059년 11월 */
    }
    else if (year >= 2040)
    {
        /* 기준일자 양력 2040년 1월 1일 (음력 2039년 11월 17일) */
        solYear = 2040;
        solMonth = 1;
        solDay = 1;
        lunYear = 2039;
        lunMonth = 11;
        lunDay = 17;
        lunLeapMonth = 0;

        solMonthDay[1] = 29; /* 2040 년 2월 28일 */
        lunMonthDay = 29; /* 2039년 11월 */
    }
    else if (year >= 2020)
    {
        /* 기준일자 양력 2020년 1월 1일 (음력 2019년 12월 7일) */
        solYear = 2020;
        solMonth = 1;
        solDay = 1;
        lunYear = 2019;
        lunMonth = 12;
        lunDay = 7;
        lunLeapMonth = 0;

        solMonthDay[1] = 29; /* 2020 년 2월 28일 */
        lunMonthDay = 30; /* 2019년 12월 */
    }
    else if (year >= 2000)
    {
        /* 기준일자 양력 2000년 1월 1일 (음력 1999년 11월 25일) */
        solYear = 2000;
        solMonth = 1;
        solDay = 1;
        lunYear = 1999;
        lunMonth = 11;
        lunDay = 25;
        lunLeapMonth = 0;

        solMonthDay[1] = 29; /* 2000 년 2월 28일 */
        lunMonthDay = 30; /* 1999년 11월 */
    }


    lunIndex = lunYear - 1999;

    while (true)
    {
        if (type == 1 && year == solYear && month == solMonth && day == solDay)
        {
            result = lunYear;

            if(lunMonth<10) result = result + "0" + lunMonth;
            else result = result + "" + lunMonth;

            if(lunDay<10) result = result + "0" + lunDay;
            else result = result + "" + lunDay;

            return result;
        }
        else if (type == 2 && year == lunYear && month == lunMonth && day == lunDay && leapmonth == lunLeapMonth)
        {
            result = solYear;

            if(solMonth<10) result = result + "0" + solMonth;
            else result = result + "" + solMonth;

            if(solDay<10) result = result + "0" + solDay;
            else result = result + "" + solDay;

            return result;
        }

        /* add a day of solar calendar */
        if (solMonth == 12 && solDay == 31)
        {
            solYear++;
            solMonth = 1;
            solDay = 1;

            /* set monthDay of Feb */
            if (solYear % 400 == 0)
                solMonthDay[1] = 29;
            else if (solYear % 100 == 0)
                solMonthDay[1] = 28;
            else if (solYear % 4 == 0)
                solMonthDay[1] = 29;
            else
                solMonthDay[1] = 28;

        }
        else if (solMonthDay[solMonth - 1] == solDay)
        {
            solMonth++;
            solDay = 1;
        }
        else
            solDay++;

        /* add a day of lunar calendar */
        if (lunMonth == 12 &&  ((lunarMonthTable[lunIndex][lunMonth - 1] == 1 && lunDay == 29) || (lunarMonthTable[lunIndex][lunMonth - 1] == 2 && lunDay == 30)))
        {
            lunYear++;
            lunMonth = 1;
            lunDay = 1;

            if (lunYear > 2101) {
                return "SD.W.0215";
                break;
            }

            lunIndex = lunYear - 1999;

            if (lunarMonthTable[lunIndex][lunMonth - 1] == 1)
                lunMonthDay = 29;
            else if (lunarMonthTable[lunIndex][lunMonth - 1] == 2)
                lunMonthDay = 30;
        }
        else if (lunDay == lunMonthDay)
        {
            if (lunarMonthTable[lunIndex][lunMonth - 1] >= 3 && lunLeapMonth == 0)
            {
                lunDay = 1;
                lunLeapMonth = 1;
            }
            else
            {
                lunMonth++;
                lunDay = 1;
                lunLeapMonth = 0;
            }

            if (lunarMonthTable[lunIndex][lunMonth - 1] == 1)
                lunMonthDay = 29;
            else if (lunarMonthTable[lunIndex][lunMonth - 1] == 2)
                lunMonthDay = 30;
            else if (lunarMonthTable[lunIndex][lunMonth - 1] == 3)
                lunMonthDay = 29;
            else if (lunarMonthTable[lunIndex][lunMonth - 1] == 4 && lunLeapMonth == 0)
                lunMonthDay = 29;
            else if (lunarMonthTable[lunIndex][lunMonth - 1] == 4 && lunLeapMonth == 1)
                lunMonthDay = 30;
            else if (lunarMonthTable[lunIndex][lunMonth - 1] == 5 && lunLeapMonth == 0)
                lunMonthDay = 30;
            else if (lunarMonthTable[lunIndex][lunMonth - 1] == 5 && lunLeapMonth == 1)
                lunMonthDay = 29;
            else if (lunarMonthTable[lunIndex][lunMonth - 1] == 6)
                lunMonthDay = 30;
        }
        else
            lunDay++;
    }
}



