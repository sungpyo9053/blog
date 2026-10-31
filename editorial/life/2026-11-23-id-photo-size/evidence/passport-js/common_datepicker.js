$(function(){datepicker_init();});

function datepicker_init() {
	if($(".datepicker").not('.hasDatepicker').size() > 0){
		$(".datepicker").not('.hasDatepicker').datepicker({
			monthNames : [".1",".2",".3",".4",".5",".6",".7",".8",".9",".10",".11",".12"],
			monthNamesShort: ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"],
			dayNamesMin : ["일","월","화","수","목","금","토"],
			dateFormat : "yy-mm-dd",
			minDate: new Date('1930-01-01'),
			yearRange: "-100:+1",
			changeMonth: true,
		    changeYear: true,
		    showButtonPanel: true,
		    closeText: '초기화',
		    onClose: function () {
		        if ($(window.event.srcElement).hasClass('ui-datepicker-close')) {
		            $(this).val('');
		        }
		    }
		});
		
		$(".datepicker.hasDatepicker").attr('readonly', 'readonly');
		$(".datepicker.hasDatepicker").css({'cursor':'pointer'});
	}
}


function datepicker_start(start, end) {
	var date_start = $("#"+start).val();
	var date_end = $("#"+end).val();
	
	var res_date_start = date_start.replace(/[^0-9]/g,"");
	var res_date_end = date_end.replace(/[^0-9]/g,"");
	
	if(res_date_end != "") {
		if(res_date_start>res_date_end) {
			alert("시작일은 종료일 보다 클 수 없습니다.");
			$("#"+start).val(date_end);
			$("#"+start).focus();
			return false;
		}
	}
}

function datepicker_end(start, end) {
	var date_start = $("#"+start).val();
	var date_end = $("#"+end).val();
	
	var res_date_start = date_start.replace(/[^0-9]/g,"");
	var res_date_end = date_end.replace(/[^0-9]/g,"");
	
	if(res_date_start != "") {
		if(res_date_start>res_date_end) {
			alert("종료일은 시작일 보다 작을 수 없습니다.");
			$("#"+end).val(date_start);
			$("#"+end).focus();
			return false;
		}
	} else {
		alert("시작일을 선택해 주세요.");
		$("#"+end).val("");
		return false;
	}
}
