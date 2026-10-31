/** SITE */
var kssFile = new Array();
var kssRemoveFileUniqe = new Array();
var kssRemoveFileRename = new Array();
$('.kssFileWarp').on('dragover', kssDragOver).on('dragleave', kssDragOver).on('drop', kssUploadFiles);
$('.kssDragAndDrop').on('dragleave', kssDragLeave);
$('.kssZipDownloadBtn').on('click', kssZipDownloadBtnAct);
$('.kssFileBtn').on('click', kssFileBtnAct);
$('.kssFileHidden').on('change', kssFileInputAct);

$('form').on('submit', function(event) {
	show_loader();
	
	if(kssFile.length > 0 || kssRemoveFileUniqe.length > 0) {
		event.preventDefault();
		
		var action = $(this).attr('action');
		var form = new FormData($(this)[0]);
		
		if(kssFile.length > 0) {
			$.each(kssFile, function(index, item) {
				var uploadKey = item.uploadKey;
				form.append(uploadKey, item);
			});	
		}
		
		if(kssRemoveFileUniqe.length > 0) {
			$.each(kssRemoveFileUniqe, function(index, item) {
				form.append('fileDataRmList', item);
			});	
			
			if(kssRemoveFileRename.length > 0) {
				$.each(kssRemoveFileRename, function(index, item) {
					form.append('fileDataNameRmList', item);
				});		
			}
		}
		
		var request = new XMLHttpRequest();
		request.open("POST", action, true);
		request.onload = function(oEvent) {
			if (request.status == 200) {
				var popupWindow = window.open('', '_self');
				popupWindow.document.write(request.response);
				popupWindow.document.close();
			}
			else console.log("Error " + request.status + " occurred when trying to upload your file.");
		}
		request.send(form);
	}
});
$('[menu_delete="Y"]').remove();
$('input:checkbox').css({'cursor':'pointer'});
$('#checkbox_all').on('click', function() {
	if($('#checkbox_all').is(':checked')) $('.checkbox_child').prop("checked", true);
	else $('.checkbox_child').prop("checked", false);
});
$('.checkbox_child').on('click', function() {
	if($('.checkbox_child:checked').length == $('.checkbox_child').length) $('#checkbox_all').prop("checked", true);
	else $('#checkbox_all').prop("checked", false);
});

$(".join_select1").select2();

$('.vali_phone').on('keydown', function(event) {
	$(this).val($(this).val().replace(/[^0-9 -]/gi, ''));
});
$('.vali_phone').on('keyup', function(event) {
	$(this).val($(this).val().replace(/[^0-9 -]/gi, ''));
	
	var value = $(this).val(), addValue = [];
	value = value.replace(/-/gi, '');
	
	if (value.length >= 3) { 
		if (value.substring(0, 2) == '02') { // 서울 번호를 체크하기 위한 조건
			addValue.push(value.substring(0, 2)); 
		
			if (value.length >= 3) { 
				var endKey = (value.length >= 10 ? 6 : 5); // 00-000-000, 00-0000-0000 처리 
				addValue.push(value.substring(2, endKey)); 
				
				if (value.length >= 6) { 
					if (value.length >= 10) { // 10자리 이상 입력 방지
						value = value.substring(0, 10); 
					}
					addValue.push(value.substring(endKey, value.length)); 
				}
			}
		} else { 
			addValue.push(value.substring(0, 3)); 
			
			if (value.length >= 4) { 
				var endKey = (value.length >= 11 ? 7 : 6); // 000-000-0000, 000-0000-0000 처리 
		        addValue.push(value.substring(3, endKey)); 
				
				if (value.length >= 7) { 
					if (value.length >= 11) { // 11자리 이상 입력 방지
						value = value.substring(0, 11); 
					}
					addValue.push(value.substring(endKey, value.length)); 
				}
			}
		}
			
		$(this).val(addValue.join('-')); 
	}
});
/** SITE */

/** EDITOR */
var oEditors = [];
$.each($('textarea[editor=Y]'), function(index, item) {
	nhn.husky.EZCreator.createInIFrame({
		oAppRef: oEditors,
		elPlaceHolder: $(item).attr('id'),
		/*sSkinURI: "/resources/editor/SmartEditor2/SmartEditor2Skin.html",*/
		sSkinURI: "/siteManager/home/kor/editor/index.do",
		fCreator: "createSEditor2"
	});
});
/** EDITOR */

/** PCIKER MAP */
if($('#pickerMap').length && $('#latitude').length && $('#longitude').length) {
	var lat = $('#latitude').val(), lng = $('#longitude').val();
	lat = lat? lat :37.4665249749087;
	lng = lng? lng :127.094905760935;

	var pickerMapContainer = document.getElementById('pickerMap'), 
	pickerMapOption = { center: new kakao.maps.LatLng(lat, lng), level: 4 };

	var pickerMap = new kakao.maps.Map(pickerMapContainer, pickerMapOption);
	var pickerMarker = new kakao.maps.Marker({ position: new kakao.maps.LatLng(lat, lng) });
	pickerMarker.setMap(pickerMap);

	var pickerGeocoder = new kakao.maps.services.Geocoder();
	kakao.maps.event.addListener(pickerMap, 'click', function(mouseEvent) {        
	    var latlng = mouseEvent.latLng;
	    
	    pickerGeocoder.coord2Address(latlng.getLng(), latlng.getLat(), function(result, status) {
			 if (status === kakao.maps.services.Status.OK) {
				 var dataAddress = result[0];
				 
				 var data = dataAddress.address;
				 var main_address_no = data.main_address_no;
				 var sub_address_no = data.sub_address_no;
				 var address_name = data.address_name;
				 
				 var zip_code = main_address_no + (sub_address_no ?'-'+sub_address_no :'');
				 if($('#zipCode').length) $('#zipCode').val('');
				 if($('#address').length) $('#address').val(address_name);
				 if($('#addressDetail').length) $('#addressDetail').val('');
				 if($('#latitude').length) $('#latitude').val(latlng.getLat());
				 if($('#longitude').length) $('#longitude').val(latlng.getLng());
			 }
		});
		
		pickerMarker.setMap(null);
	   	pickerMarker = new kakao.maps.Marker({ position: latlng });
			pickerMarker.setMap(pickerMap);
	});	
}
/** PCIKER MAP */

/** IMG THUMBNAIL */
$(document).ready(function() {
	$.each($('img'), function(index, item) { resizeImage($(item)); });	
});
/** IMG THUMBNAIL */