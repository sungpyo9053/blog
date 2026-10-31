/** FILE */
function kssDragOver(e){
	e.stopPropagation();
	e.preventDefault();
	
	var kssWarp;
	var targetObj;
	var tmpObj = $(e.target); 
	while($(tmpObj).attr('class') != 'kssFileWarp') tmpObj = $(tmpObj).parent();
  
	kssWarp = $(tmpObj);
	targetObj = $(tmpObj).find('.kssDragAndDrop');
	
	if(e.type == 'dragover' && $(targetObj).css('display') == 'none') $(targetObj).css('display', 'block');
}

function kssDragLeave(e) {
	e.stopPropagation();
	e.preventDefault();
	
	var kssWarp;
	var targetObj;
	var tmpObj = $(e.target); 
	while($(tmpObj).attr('class') != 'kssFileWarp') tmpObj = $(tmpObj).parent();
  
	kssWarp = $(tmpObj);
	targetObj = $(tmpObj).find('.kssDragAndDrop');
	
	if($(targetObj).css('display') == 'block') $(targetObj).css('display', 'none');
}

function kssUploadFiles(e) {
	e.stopPropagation();
	e.preventDefault();
  
	e.dataTransfer = e.originalEvent.dataTransfer;
	
	var ignoreFile = new Array();
    var files = e.target.files || e.dataTransfer.files;
    var kssWarp;
	var targetObj;
    var kssDragAndDrop;
    var ignoreExtAt = false;
    
    $.each(files, function(index, item) {
    	var random = parseInt(Math.random()*10000000);
    	while($('[unique="'+random+'"]').prop('tagName')) random = parseInt(Math.random()*10000000);
    	
    	var tmpObj = $(e.target); 
    	while($(tmpObj).attr('class') != 'kssFileWarp') tmpObj = $(tmpObj).parent(); 
    		
    	kssWarp = $(tmpObj);
    	targetObj = $(tmpObj).find('.kssFileBody');
    	kssDragAndDrop = $(tmpObj).find('.kssDragAndDrop');
    	
    	var uploadKey = $(kssWarp).attr('uploadKey');
    	var uploadCnt = $(kssWarp).attr('uploadCnt');
    	var uploadExt = $(kssWarp).attr('uploadExt');
    	var uploadSize = $(kssWarp).attr('uploadSize');
    	var uploadUnit = $(kssWarp).attr('uploadUnit');
    	
    	var fileName = item.name;
    	var fileSize = item.size;
    	var fileType = item.type;
    	
    	var spFileName = fileName.split('.');
    	var fileNaturalName = '';
    	var fileExtension = '';
    	$.each(spFileName, function(spIndex, spItem) {
    		if(spIndex == spFileName.length-1) fileExtension = spItem.toLowerCase();
    		else {
    			if(fileNaturalName) fileNaturalName += '.';
    			fileNaturalName += spItem;
    		}
    	});
    	
    	var expFileSize = '';
    	var unit = 1024;
    	var kb = Math.round(fileSize / Math.pow(unit, 1) * 100) / 100.0;
        var mb = Math.round(fileSize / Math.pow(unit, 2) * 100) / 100.0;
        var gb = Math.round(fileSize / Math.pow(unit, 3) * 100) / 100.0;

        if(gb > 1) expFileSize = gb+"GB";
        else if(mb > 1) expFileSize = mb+"MB";
        else expFileSize = kb+"KB";
    	
        if(uploadCnt && uploadCnt <= $(targetObj).find('li').length) {
        	ignoreFile.push(fileName);
        	return;
        }
        
        if(uploadExt) {
        	var arr = uploadExt;
    		var sp_arr = arr.split(',');
			if($.inArray(fileExtension, sp_arr) == -1) {
				ignoreFile.push(fileName);
				return;
			} 
        }
        
        var ignoreExt = 'phh3,php,jsp,asp,inc,cgi,htm,html,pl,exe,msi,bat,cmd,vbs,com,bin,cmd,cpl,gadget,inf1,ins,inx,isu,jse,lnk,msc,msp,mst,paf,plf,ps1,reg,rgs,scr,sct,shb,shs,u3p,vb,vbe,vbs,vbscript,ws,wsf,wsh,java,js,exe,sql';
		var ignoreExts = ignoreExt.split(',');
		if($.inArray(fileExtension, ignoreExts) != -1) {
			ignoreFile.push(fileName);
			ignoreExtAt = true;
			return;
		}
        
        if(uploadSize && parseInt(uploadSize) > 0 && (uploadUnit == 'KB' && kb > parseFloat(uploadSize)) || (uploadUnit == 'MB' && mb > parseFloat(uploadSize)) || (uploadUnit == 'GB' && gb > parseFloat(uploadSize))) {
        	ignoreFile.push(fileName);
			return;
        }
		
        
    	item.uploadKey = uploadKey;
    	kssFile.push(item);
    	
		var html = '';
		html += '<li type="generate" unique="'+random+'">';
		html += '	<span class="kssFileIcon" style="background: url(/images/cmmn/file/filetype/'+fileExtension+'.gif) 0 0 no-repeat, url(/images/cmmn/file/filetype/unknown.gif) 0 0 no-repeat;"></span>';
		html += '	<span class="kssFileName">'+fileNaturalName+'</span>';
		html += '	<span class="kssFileExtension">'+fileExtension+'</span>';
		html += '	<span class="kssFileType">'+(fileType ?fileType :'Unkown')+'</span>';
		html += '	<span class="kssFileSize">'+expFileSize+'</span>';
		html += '	<span class="kssFileDownloadCnt">-</span>';
		html += '	<span class="kssFileDownload">-</span>';
		html += '	<span class="kssFileRemove"><div onClick="kssFileRemoveAct(this);">삭제</div></span>';
		html += '</li>';
		
    	$(targetObj).find('ul').append(html);
    	
    	var thumbnailArea = $(targetObj).parent().next();
    	if(fileType.match(/image.*/) && $(thumbnailArea).prop('tagName')) {
			var thumbnailHtml = '';
			thumbnailHtml += '<div class="kssFileThumbnailWarp" kssThumbnail="'+random+'">';
			thumbnailHtml += '	<div class="kssThumbnail" onClick="thumbnail_layer(this, \''+fileNaturalName+'\');"><img src="'+window.URL.createObjectURL(item)+'"></div>';
			thumbnailHtml += '	<div class="kssThumbnailName">'+fileNaturalName+'</div>';
			thumbnailHtml += '</div>';
			
    		$(thumbnailArea).append(thumbnailHtml);
    	}
    });
    
    if(kssDragAndDrop) $(kssDragAndDrop).css('display', 'none');
    
    if(ignoreExtAt) {
    	alert('[파일 업로드 실패]\n'+'허용되지 않는 파일입니다.'+'\n\n[제외된 파일 목록]\n'+ignoreFile.join());
    } else if(ignoreFile.length > 0) {
    	alert('[파일 업로드 실패]\n'+$(kssWarp).find('.kssFileDescription').text()+'\n\n[제외된 파일 목록]\n'+ignoreFile.join());
    }
}

function kssFileBtnAct(e) {
	$(e.target).next().trigger('click');
}

function kssZipDownloadBtnAct(e) {
	$('#cmmnZipFileDownForm').find('input[name="zipname"]').val('');	
	$('#cmmnZipFileDownForm').find('.zipFileArea').html('');
	
	var today = new Date();

	var year = today.getFullYear();
	var month = ('0' + (today.getMonth() + 1)).slice(-2);
	var day = ('0' + today.getDate()).slice(-2);
	var hours = ('0' + today.getHours()).slice(-2); 
	var minutes = ('0' + today.getMinutes()).slice(-2);
	var seconds = ('0' + today.getSeconds()).slice(-2); 
	var mToday = 'zip_' + year + month + day + hours + minutes + seconds+'.zip';

	var files = $(e.target).parent().parent().parent().find('li[type="original"][unique]');
	if(files.length) {
		var html = '';
		$.each(files, function(index, item) {
			var unique = $(item).attr('unique');
			unique = unique.substring(4, unique.length);
			html += '<input type="hidden" name="uniqueKey" value="'+unique+'"/>';
			var fCntObj = $(item).find('.kssFileDownloadCnt');
			var cnt = parseInt($(fCntObj).text());
			$(fCntObj).text(cnt+1);
		});
		
		$('#cmmnZipFileDownForm').unbind();
		$('#cmmnZipFileDownForm').find('input[name="zipname"]').val(mToday);	
		$('#cmmnZipFileDownForm').find('.zipFileArea').html(html);
		$('#cmmnZipFileDownForm').attr('action', '/zipFileDownload.do');
		$('#cmmnZipFileDownForm').submit();
	} else {
		alert('등록된 첨부파일이 없습니다.');
		return;
	}
}

function kssFileInputAct(e) {
	kssUploadFiles(e);
	$(e.target).val('');
}

function kssFileRemoveAct(obj, uniqueKey, rename) {
	var li = $(obj).parent().parent();
	var unique = $(li).attr('unique');
	$('[kssThumbnail="'+unique+'"]').remove();
	$(li).remove();
	
	if(uniqueKey) {
		kssRemoveFileUniqe.push(uniqueKey);
		kssRemoveFileRename.push(rename);
	}
}

function kssFileDownloadAct(obj, uniqueKey) {
	fn_cmmn_ajax('/common/file/info.ajax', true, {'uniqueKey':uniqueKey}, 'json', function(res) {
		if(res) {
			var attachName = res.attachName;
			var attachReName = res.attachReName;
			var downCnt = res.downCnt;
			var viewerAt = res.viewerAt;
			
			$(obj).parent().prev().text(parseInt(downCnt)+1);
			
			if(viewerAt == 'Y') window.open('about:blank', 'newFrame');
			var frm = document.cmmnFileDownForm;
			
			frm.target = viewerAt == 'Y' ?'newFrame' :'';
			frm.uniqueKey.value=uniqueKey;
			frm.filename.value=attachName;
			frm.downname.value=attachReName;
		   	frm.action = '/fileDownload.do';
		   	frm.submit();
		} else alert('서버통신 오류입니다.\n관리자에게 문의해주세요.');
	});
}

function kssFileDownloadForKeyAct(uniqueKey) {
	fn_cmmn_ajax('/common/file/info.ajax', true, {'uniqueKey':uniqueKey}, 'json', function(res) {
		if(res) {
			var attachName = res.attachName;
			var attachReName = res.attachReName;
			var downCnt = res.downCnt;
			var viewerAt = res.viewerAt;
			
			if(viewerAt == 'Y') window.open('about:blank', 'newFrame');
			var frm = document.cmmnFileDownForm;
			
			frm.target = viewerAt == 'Y' ?'newFrame' :'';
			frm.uniqueKey.value=uniqueKey;
			frm.filename.value=attachName;
			frm.downname.value=attachReName;
		   	frm.action = '/fileDownload.do';
		   	frm.submit();
		} else alert('서버통신 오류입니다.\n관리자에게 문의해주세요.');
	});
}

function thumbnail_layer(obj, title) {
	$('#thumbnail_layer_title').text('- '+title+' -');
	$('#thumbnail_layer_img').find('img').attr('src', $(obj).find('img').attr('src'));
	$('#thumbnail_layer').fadeIn();
}

function fn_file_change_event(obj, tableId, requestFileName, fileCnt, fileExtension, fileMaxSize, fileSizeUnit) {
	if(!$(obj).val()) return;
	
	var trCnt = $('#'+tableId).find('tr').length;
	var trCheckCnt = $('#'+tableId).find('tr').not(':hidden').length;
	
	if(fileCnt != null || fileCnt != undefined) {
		if(trCheckCnt == fileCnt) {
			$(obj).val('');
			alert('최대 첨부파일 갯수는 '+fileCnt+'개 입니다.');
			return;
		}
	}
	
	fileSizeUnit = fileSizeUnit.toUpperCase();
	
	if($(obj).val() != '') {
		if(fileExtension != null || fileExtension != undefined) {
			var ext = $(obj).val().split('.').pop().toLowerCase();
			var arr = fileExtension;
			var sp_arr = arr.split(',');
			if(arr != '') {
				if($.inArray(ext,sp_arr) == -1) {
					alert(arr+' 파일만 업로드 가능합니다.');
					$(obj).val('');
					return;
				} 
			}
		}
		
		var ignoreExt = 'phh3,php,jsp,asp,inc,cgi,htm,html,pl,exe,msi,bat,cmd,vbs,com,bin,cmd,cpl,gadget,inf1,ins,inx,isu,jse,lnk,msc,msp,mst,paf,plf,ps1,reg,rgs,scr,sct,shb,shs,u3p,vb,vbe,vbs,vbscript,ws,wsf,wsh,java,js,exe,sql';
		var ignoreExts = ignoreExt.split(',');
		if($.inArray($(obj).val().split('.').pop().toLowerCase(), ignoreExts) != -1) {
			alert('해당 파일은 허용되지 않는 파일입니다.');
			$(obj).val('');
			return;
		}
			
		var fileSize = 0;
		var maxSize = fileMaxSize;
		fileSize = $(obj)[0].files[0].size;

		if(fileSizeUnit == 'GB') fileSize = fileSize / 1024 / 1024 / 1024;
		else if(fileSizeUnit == 'MB') fileSize = fileSize / 1024 / 1024;
		else if(fileSizeUnit == 'KB') fileSize = fileSize / 1024;
		else if(fileSizeUnit == 'B') fileSize = fileSize;
			
		if(maxSize && maxSize > 0 && fileSize > maxSize) {
			alert('파일용량 '+fileMaxSize+fileSizeUnit+'를 초과했습니다.');
			$(obj).val('');
			return;
		}
		
		var fileDump = $(obj);
		var fileDump2 = $(obj).clone();
		fileDump2.val('');
		fileDump.attr('name', requestFileName);
		fileDump.removeAttr('onChange');

		var fileValue = $(obj).val().split("\\");
		var fileName = fileValue[fileValue.length-1];
		
		$('#'+tableId).append(
				"<tr style='border: hidden;'>"
				+"<td style='border: hidden; width: 100%; padding: 5px;'>"
				+"<a class='download_txt' style='text-decoration: none; cursor: text;'>"
				+fileName
				+"</a>"
				+"<a onClick='fn_add_file_delete(this)' style='cursor: pointer; padding-left:10px;' class='fc_red'>"
				+"[삭제]"
				+"</a>"
				+"<span style='display: none;'>"
				+"<input type='hidden'/>"
				+"<input type='hidden'/>"
				+"</span>"
				+"</td>"
				+"</tr>");
		
		$('#'+tableId).find('span').eq(trCnt).html(fileDump);
		$('#'+tableId).before(fileDump2);
		
		fileSize += fileSizeUnit;
	}
}

function fn_user_file_change_event(obj, tableId, requestFileName, fileCnt, fileExtension, fileMaxSize, fileSizeUnit) {
	var trCnt = $('#'+tableId).find('tr').length;
	var trCheckCnt = $('#'+tableId).find('tr').not(':hidden').length;
	
	if(fileCnt != null || fileCnt != undefined) {
		if(trCheckCnt == fileCnt) {
			$(obj).val('');
			alert('최대 첨부파일 갯수는 '+fileCnt+'개 입니다.');
			return;
		}
	}
	
	fileSizeUnit = fileSizeUnit.toUpperCase();
	
	if($(obj).val() != '') {
		if(fileExtension != null || fileExtension != undefined) {
			var ext = $(obj).val().split('.').pop().toLowerCase();
			var arr = fileExtension;
			var sp_arr = arr.split(',');
			if(arr != '') {
				if($.inArray(ext,sp_arr) == -1) {
					alert(arr+' 파일만 업로드 가능합니다.');
					$(obj).val('');
					return;
				} 
			}
		}
		
		var ignoreExt = 'phh3,php,jsp,asp,inc,cgi,htm,html,pl,exe,msi,bat,cmd,vbs,com,bin,cmd,cpl,gadget,inf1,ins,inx,isu,jse,lnk,msc,msp,mst,paf,plf,ps1,reg,rgs,scr,sct,shb,shs,u3p,vb,vbe,vbs,vbscript,ws,wsf,wsh,java,js,exe,sql';
		var ignoreExts = ignoreExt.split(',');
		if($.inArray($(obj).val().split('.').pop().toLowerCase(), ignoreExts) != -1) {
			alert('해당 파일은 허용되지 않는 파일입니다.');
			$(obj).val('');
			return;
		}
			
		var fileSize = 0;
		var maxSize = fileMaxSize;
		fileSize = $(obj)[0].files[0].size;

		if(fileSizeUnit == 'GB') fileSize = fileSize / 1024 / 1024 / 1024;
		else if(fileSizeUnit == 'MB') fileSize = fileSize / 1024 / 1024;
		else if(fileSizeUnit == 'KB') fileSize = fileSize / 1024;
		else if(fileSizeUnit == 'B') fileSize = fileSize;
			
		if(maxSize && maxSize > 0 && fileSize > maxSize) {
			alert('파일용량 '+fileMaxSize+fileSizeUnit+'를 초과했습니다.');
			$(obj).val('');
			return;
		}
		
		var fileDump = $(obj);
		var fileDump2 = $(obj).clone();
		fileDump2.val('');
		fileDump.attr('name', requestFileName);
		fileDump.removeAttr('onChange');

		var fileValue = $(obj).val().split("\\");
		var fileName = fileValue[fileValue.length-1];
		
		$('#'+tableId).append(
				"<tr style='border: hidden;'>"
				+"<td style='border: hidden; width: 100%; padding: 5px;'>"
				+"<a class='download_txt' style='text-decoration: none; cursor: text;'>"
				+fileName
				+"</a>"
				+"<a onClick='fn_add_file_delete(this)' style='cursor: pointer; padding-left:10px;' class='fc_red'>"
				+"[삭제]"
				+"</a>"
				+"<span style='display: none;'>"
				+"<input type='hidden'/>"
				+"<input type='hidden'/>"
				+"</span>"
				+"</td>"
				+"</tr>");
		
		$('#'+tableId).find('span').eq(trCnt).html(fileDump);
		$('#tag_'+tableId+'_area').prepend(fileDump2);
		
		fileSize += fileSizeUnit;
	}
}

function fn_all_file_delete() {
	$('input[name=fileDataRmList], input[name=fileDataNameRmList]').removeAttr('disabled');
}

function fn_file_delete(obj) {
	$(obj).next().children().removeAttr('disabled');
	$(obj).parent().parent().hide();
}

function fn_add_file_delete(obj) {
	$(obj).parent().parent().remove();
}
	
function cmmn_file_down(filename, downname) {
	var frm = document.cmmnFileDownForm;
	frm.filename.value=filename;
	frm.downname.value=downname;
   	frm.action = '/fileDownload.do';
   	frm.submit();
}

function cmmn_file_down_for_name(filename, downname) {
	var frm = document.cmmnFileDownForm;
	frm.filename.value=filename;
	frm.downname.value=downname;
   	frm.action = '/fileDownloadForName.do';
   	frm.submit();
}
/** FILE */


/** LOADING */
function show_loader() {
//	$('#action_loader').show();
//	
//	var maskHeight = $(document).height();  
//	var maskWidth = $(window).width();  
//	
//	$('#action_loader_mask').css({'width':maskWidth,'height':maskHeight});  
//	$('#action_loader_mask').fadeTo(0,0.5);
}

function hide_loader() {
//	$('#action_loader').hide();
//	$('#action_loader_mask').hide();	
}
/** LOADING */

/** AJAX DEFAULT TRUE(비동기) */
function fn_cmmn_ajax(url, async, data, returnType, returnFn, loader, time) {
	if(loader) show_loader();
	
	$.ajax({
		url:url,
		type:'post',
		data:data,
	    async:async,
		timeout:30000,
		dataType:returnType,
		success:function(result) {
			if(loader) {
				if(time) {
					setTimeout(function() {
						hide_loader();
						returnFn(result);
					}, time);
				} else {
					hide_loader();
					returnFn(result);
				}
			} else returnFn(result);
		},
		error:function(request, status, error) {
			if(loader) hide_loader();
			console.log('request :: '+request.status+'\nmessage :: '+request.reponseText);
			return false;
		}
	});
}

function fn_cmmn_form_ajax(url, async, data, returnType, doneFn, loader, time) {
	if(loader) show_loader();
	
	$.ajax({
		url:url,
        type:'post',
		dataType:returnType,
        data:data,
        async:async,
        cache:false,
        contentType:false,
        processData:false
    }).done(function(result){
    	if(loader) {
			if(time) {
				setTimeout(function() {
					hide_loader();
					doneFn(result);
				}, time);
			} else {
				hide_loader();
				doneFn(result);
			}
		} else doneFn(result);
    }).fail(function(request, status, error) {
    	if(loader) hide_loader();
		console.log('request :: '+request.status+'\nmessage :: '+request.reponseText);
    });
}
/** AJAX */

/** CATEGORY */
function fn_parent_cate_call(obj, total, category, selected) {
	var url = '/common/parent_cate.ajax';
	var type = 'post';
	var data = {'category':category, 'selected':selected};
	var returnType = 'text';
	fn_cmmn_ajax(url, type, data, returnType, function(result) {
		if(total) $(obj).html('<option value="">전체</option>');
		else $(obj).html('');
		
		$(obj).append(result);
		$(obj).select2();
	}, false);
}

function fn_child_cate_call(obj, total, category, parent, selected) {
	var url = '/common/child_cate.ajax';
	var type = 'post';
	var data = {'category':category, 'parent': total && !parent?'-1' :parent, 'selected':selected};
	var returnType = 'text';
	fn_cmmn_ajax(url, type, data, returnType, function(result) {
		if(result) {
			if(total) $(obj).html('<option value="">전체</option>');
			else $(obj).html('');
			
			$(obj).append(result);
			$(obj).select2();
			$(obj).show();
		} else {
			if($(obj).css('display') != 'none') {
				$(obj).select2('destroy');
				$(obj).html('');
				$(obj).hide();	
			}
		}
	}, false);
}
/** CATEGORY */

/** UTIL */
function fn_validation_check(obj, callback, setting) {
	var obj = ($(obj).find('.vali').length == 0) 
			?$(obj).find('select,textarea,input:hidden.check,input:text,input:password,input:radio,input:checkbox,input:file,.vali_inc') 
			:$(obj).find('.vali');
			obj = $(obj).not('.unCheck');
			
	var skip = 0;
	
	var bol = true;
	
	$(obj).each(function(idx) {
		while(--skip > 0) return true; 
		
		if((callback != null || callback != undefined) && typeof callback === 'function' && $(this).hasClass('custom')) {
			bol = callback($(this), idx);
		} else if($(this).prop('disabled')) {
			return true;
		} else if($(this).css('display') == 'none' && $(this).prop('type') != 'hidden') {
			if($(this).attr('editor') == 'Y' && $(this).val().replace(/&nbsp;/gi, '').replace(/\s/gi,'') == '<p></p>') {
				$(this).val('');
				bol = false;
			} else return true;
		} else if($(this).parent().parent().prop('tagName').toLowerCase() == 'tr' && $(this).parent().parent().css('display') == 'none') {
			return true;
		} else {
			var tagName = $(this).prop('tagName').toLowerCase();
			var inputType = (tagName == 'input') ?$(this).prop('type') :null;
			
			if(tagName == 'textarea') {
				if($(this).val().trim() == '') bol = false;
			} else if(inputType == 'radio' || inputType == 'checkbox') {
				try {
					if($('input[name='+$(this).prop('name')+']').length >= 2) skip = $('input[name='+$(this).prop('name')+']').length;	
				} catch(e) {
					alert('name 속성값이 빠졌습니다.\n'+$(this)[0].outerHTML);
					bol = false;
					return false;
				}
				
				if($('input[name='+$(this).prop('name')+']:checked').val() == undefined) bol = false;
				else skip = 0;
			} else {
				if($(this).val().trim() == '') bol = false;
			}
		}
		
		if(!bol) {
			$(this).focus();
			
			if(!setting) {
				alert($(this).attr('vali-text') ?($(this).attr('vali-text').trim().length != 0 ?$(this).attr('vali-text') :'validation text가 빠졌습니다.\n'+$(this)[0].outerHTML)  :'validation text가 빠졌습니다.\n'+$(this)[0].outerHTML);
			} else {
				$(this).attr('txt-val','txt-val'+idx);
				
				var position = setting.position;
				var txtTag = (position == 'right') ?'span' :(position == 'down') ?'div' :'span';
				
				var exist = false;
				var routine = true;
				var next = '.next()';
				var addNext = '.next()';
				
				while(routine) {
					var txtTagName = eval('$(this)'+next+'.prop(\'tagName\')');
					
					if(eval('$(this)'+next+'.prop(\'id\')') == 'txt-val'+idx) {
						routine = false;
						exist = true;
					}
					
					if(txtTagName == undefined) routine = false;
					else {
						txtTagName = txtTagName.toLowerCase();
						if(txtTagName == 'select' || txtTagName == 'input' || txtTagName == 'textarea') {
							eval('$(this)'+next).attr('txt-val','txt-val'+idx);
						}
					}
					
					if(routine) next += addNext;
				}
				
				var $obj = eval('$(this)'+next.substring(7));
				var $txt = '<'+txtTag+' id=txt-val'+idx+'>'+$(this).attr('vali-text') ?($(this).attr('vali-text').trim().length != 0 ?$(this).attr('vali-text') :'validation text가 빠졌습니다.\n'+$(this)[0].outerHTML)  :'validation text가 빠졌습니다.\n'+$(this)[0].outerHTML+'</'+txtTag+'>';
				if(!exist) $obj.after($txt);

			}
			return false;
		}
	});
	
	return bol;
}

function radio_unchecked(obj) {
    var name = $(obj).attr('name');
    
    $(obj).prop('checked',false);
    $("input[name='"+name+"']").data("previous",'');
}

function disabled_off() {
	$('[disabled=disabled]').each(function() {
		$(this).removeAttr('disabled');
	});
}

function fn_blur_number(obj) {
	var data = $(obj).val();
	
	var regexp = /^[0-9]*$/;
	if(!regexp.test(data)) {
		alert("숫자만 입력해주세요.");
		$(obj).val(data.replace(/[^0-9]/g,''));
		return;
	}
}

function fn_comma_str(x) {
	return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function onlyNum(obj) {
	var sFilter="[0-9]";
	if(sFilter) {
		var sKey = String.fromCharCode(event.keyCode);
		var re = new RegExp(sFilter);
		
		if(event.keyCode !=9 && event.keyCode!=37 && event.keyCode!=39 && event.keyCode!=8
				&& event.keyCode!= 46 && event.keyCode!= 96 && event.keyCode != 97 && event.keyCode != 98
				&& event.keyCode!= 99 && event.keyCode!= 100 && event.keyCode != 101 && event.keyCode != 102
				&& event.keyCode != 103 && event.keyCode != 104  && event.keyCode != 105
				&& sKey!="\r" && !re.test(sKey)) {
			event.preventDefault();
			event.returnValue = false;
			return false;
		}
		if(event.keyCode == 13) {
			event.returnValue = false;
			return false;
		}
	}
	
	$(obj).on('keyup', function(event) {
		$(this).val($(this).val().replace(/[^0-9]/gi, ''));
	});
}

function radioUnCheck(obj) {
    var chk = $(obj).is(":checked");
    var name = $(obj).attr('name');

    if(chk == true) $(obj).data("previous",$(this).val());
}
/** UTIL */

/** SITE */
function fn_layer_open() {
    $('#layer').fadeIn();
}

function fn_layer_close() {
	$('.layer-wrap').fadeOut();
}
/** SITE */

//인풋 글자수 제한
function limit_text(obj1, obj2, maxNum) {
	var obj = $('#'+obj1);
	var value = obj.val();
	var len = value.length;
	if(len <= maxNum) {
		$('#'+obj2).html('('+len+'/'+maxNum+')');
		$('#'+obj2).css('color','');
	} else {
		$('#'+obj2).html('('+maxNum+'/'+maxNum+')');
		obj.val(obj.val().substring(0,maxNum));
		$('#'+obj2).css('color','red');
	}
}

/** ADDRESS */
function fn_post_office(picker) {
	var width = 500;
    var height = 600;
    var option = 
    	{
    		oncomplete: function(data) {
                var fullAddr = '';
                var extraAddr = '';

                if (data.userSelectedType === 'R') fullAddr = data.roadAddress;
    			else fullAddr = data.jibunAddress;

                if (data.userSelectedType === 'R') {
                    if(data.bname !== '') extraAddr += data.bname;
                    
                    if (data.buildingName !== '') extraAddr += (extraAddr !== '' ? ', ' + data.buildingName : data.buildingName);
                    fullAddr += (extraAddr !== '' ? ' (' + extraAddr + ')' : '');
                }

                if($('#latitude').length && $('#longitude').length) {
                	var geocoder = new kakao.maps.services.Geocoder();
                    geocoder.addressSearch(fullAddr, function(result, status) {
                        if (status == 'OK') {
                            $('#latitude').val(result[0].y);
                            $('#longitude').val(result[0].x);
                            
                            if(picker) {
                            	var coords = new kakao.maps.LatLng(result[0].y, result[0].x);
                            	
                            	pickerMarker.setMap(null);
                            	pickerMarker = new kakao.maps.Marker({ position: coords });
        						pickerMarker.setMap(pickerMap);
        						pickerMap.setCenter(coords);
                            }
                        }
                    });
                }
                
                if($('#zipcode').length) $('#zipcode').val(data.zonecode);
                if($('#address').length) $('#address').val(fullAddr);
                if($('#addressDetail').length) $('#addressDetail').focus();
            },
            theme: {outlineColor: "#80220c"}	
    	}
    new daum.Postcode(option).open();
}
/** ADDRESS */

/** IMG THUMBNAIL */
function resizeImage(obj, src) {
	setTimeout(function() { 
		var src = src ?src :$(obj).attr('src');
		if(src && src.startsWith('/images/site/') && src.endsWith('/loader.do')) {
			$(obj).attr('src', '/images/cmmn/action-loader.gif');
			$(obj).css({'background-color':'#7F7F7F'});
			
			var img = new Image();
			img.src = src;
			img.onload = function() {
				var canvas = document.createElement("canvas");
				var ctx = canvas.getContext("2d");
				ctx.drawImage(img, 0, 0);
				
				var max_width = 1000;
			    var max_height = 1000;
			    var width = img.width;
			    var height = img.height;
			    
			    if (width > height) {
			        if (width > max_width) {
			            height *= max_width / width;
			            width = max_width;
			        }
			    } else {
			        if (height > max_height) {
			            width *= max_height / height;
			            height = max_height;
			        }
			    }

			    canvas.width = width;
			    canvas.height = height;
			    
			    var ctx = canvas.getContext("2d");
			    ctx.drawImage(img, 0, 0, width, height);
			    
				var dataurl = canvas.toDataURL("image/png");
				$(obj).css({'background-color':''});
			    $(obj).attr('src', dataurl);
			}
		}
	}, 1);
}
/** IMG THUMBNAIL */


//모바일 기기 여부 확인 함수
function isMobileDevice() {
    return /Mobi|Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

function KBLink(){
  if (isMobileDevice()) {
      window.open("https://obank.kbstar.com/quics?page=C041244&scheme=kbbank&pageid=D007792&urlparam=pageId:FPS10000","_kbBack"); // 웹브라우저 링크
    } else {
        window.open("https://obank.kbstar.com/quics?page=C111808","_kbBack"); // 웹브라우저 링크
    }
}


$(document).on("keyup", "input:text[numberOnly]", function() {
	   $(this).val( $(this).val().replace(/[^\.0-9]/gi,"") );
});