

$(document).ready(function() {
    $('#btn_calc_bmi').on('click', function() {
        var gender = $('input[name="bmi_gender"]:checked').val();
        var height = parseFloat($('#bmi_height').val());
        var weight = parseFloat($('#bmi_weight').val());
        var waist = parseFloat($('#bmi_waist').val());

        if (!height || !weight || !waist || height <= 0 || weight <= 0 || waist <= 0) {
            alert('올바른 신장, 체중, 허리둘레를 모두 입력해 주세요.');
            return;
        }

        // 1. BMI 계산
        var heightM = height / 100;
        var bmi = weight / (heightM * heightM);
        bmi = Math.round(bmi * 100) / 100;

        // 2. [기준 ①] 복부비만 여부 판정 (남 90 / 여 85)
        var hasAbdominalObesity = false;
        if (gender === 'M' && waist >= 90) {
            hasAbdominalObesity = true;
        } else if (gender === 'F' && waist >= 85) {
            hasAbdominalObesity = true;
        }

        var abdominalStatus = hasAbdominalObesity ? "있음" : "없음";


        // 3. [기준 ②] 비만 동반 질환의 위험도 판정 (남 90 / 여 85)
        var isRiskWaistHigh = false;
        if (gender === 'M' && waist >= 90) {
            isRiskWaistHigh = true;
        } else if (gender === 'F' && waist >= 85) { // 위험도는 엑셀 표 기준인 85 적용
            isRiskWaistHigh = true;
        }


        // 4. BMI 및 위험도 매트릭스 매칭
        var status = "";
        var risk = "";

        if (bmi < 18.5) {
            status = "저체중";
            risk = isRiskWaistHigh ? "보통" : "낮음";
        } else if (bmi >= 18.5 && bmi <= 22.9) {
            status = "정상";
            risk = isRiskWaistHigh ? "약간 높음" : "보통";
        } else if (bmi >= 23 && bmi <= 24.9) {
            status = "비만전단계";
            risk = isRiskWaistHigh ? "높음" : "약간 높음";
        } else if (bmi >= 25 && bmi <= 29.9) {
            status = "1단계 비만";
            risk = isRiskWaistHigh ? "매우 높음" : "높음";
        } else if (bmi >= 30 && bmi <= 34.9) {
            status = "2단계 비만";
            risk = isRiskWaistHigh ? "가장 높음" : "매우 높음";
        } else {
            status = "3단계 비만";
            risk = "가장 높음";
        }

        // 5. 화면에 결과 반영
        $('#bmi_value').text(bmi);
        $('#bmi_status').text(status);
        $('#bmi_risk').text(risk);
        
        // 복부비만 결과 및 스타일 제어
        $('#bmi_abdominal').text(abdominalStatus);
        if (abdominalStatus === "있음") {
            $('#bmi_abdominal').addClass('has-obese');
        } else {
            $('#bmi_abdominal').removeClass('has-obese');
        }

        // 정상일 때 파란색 글씨 처리
        if (status === "정상") {
            $('#bmi_status').addClass('is-normal');
        } else {
            $('#bmi_status').removeClass('is-normal');
        }

        if (risk == "약간 높음" || risk == "높음") {
            $('#bmi_risk').addClass('is-em');
            $('#bmi_risk').removeClass('is-emm');
        } else if(risk == "매우 높음" || risk == "가장 높음"){
            $('#bmi_risk').removeClass('is-em');
            $('#bmi_risk').addClass('is-emm');
        } else{
            $('#bmi_risk').removeClass('is-em');
            $('#bmi_risk').removeClass('is-emm');
        }

        $('.bmi-result-box').slideDown(300);

        // 하단 표 강조
        $('.status-range').removeClass('active');
        $('.status-range').each(function() {
            if ($(this).data('status') === status) {
                $(this).addClass('active');
            }
        });
    });

    $('#bmi_height, #bmi_weight, #bmi_waist').on('keypress', function(e) {
        if (e.keyCode === 13) {
            $('#btn_calc_bmi').trigger('click');
        }
    });
});



