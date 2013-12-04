
function getParameterByName(name){
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/,"\\\]");
    var regex = new RegExp("[\\?&#]" + name + "=([^&#]*)"),
        results = regex.exec(location.hash);
    if (results == null) {
        results = regex.exec(location.search);
    }
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g," "));
}

var active_page_key = null;
var page_cache = {};
var child_key_cache = {};

function toggleLike(page_key,param_value){
    
    var page = page_cache[page_key];
    
    if(page.like_value == param_value){
        param_value = 0;
    }
    
    $.get('/api/v1/likes?page_key='+page_key+'&value='+param_value, function(data) {
        if(data == 'OK'){
            page.like_value = param_value;
            updateLikeInfo(page_key,page.like_value);
        }
    });
}

function updateLikeInfo(page_key,value){
    
    var page = page_cache[page_key];
    
    var like_div = $('#'+page_key+'_like_div');
    var like_count_span = $('#'+page_key+'_like_count_span');
    if(value == 1){
        like_div.addClass("like_active");
        like_div.removeClass("like_inactive");
        like_count_span.text(page.like_count + 1);
    }else{
        like_div.removeClass("like_active");
        like_div.addClass("like_inactive");
        like_count_span.text(page.like_count);
    }
    
    var unlike_div = $('#'+page_key+'_unlike_div');
    var unlike_count_span = $('#'+page_key+'_unlike_count_span');
    if(value == -1){
        unlike_div.addClass("unlike_active");
        unlike_div.removeClass("unlike_inactive");
        unlike_count_span.text(page.unlike_count + 1);
    }else{
        unlike_div.removeClass("unlike_active");
        unlike_div.addClass("unlike_inactive");
        unlike_count_span.text(page.unlike_count);
    }
    
}

function openPage(page_key){
    
    var page = page_cache[page_key];
    
    active_page_key = page_key;
    
    appendPage(page);
    
    updateBranchLinks(page_key);
}
function updateBranchLinks(page_key){
    
    var child_keys = child_key_cache[page_key];
    if(child_keys!= null && 0 < child_keys.length){
        var child_pages = [];
        for(var i = 0; i < child_keys.length; i++){
            child_pages[i] = page_cache[child_keys[i]];
        }
        displayBranchLinks(child_pages);
    }else{
        $("#link_container").empty();
    }

    $.get('/api/v1/pages?parent_page_key='+page_key, function(data,textStatus,xhr) {
        var jsondata = JSON.parse(data);
        
        if(0 < jsondata.result.length){
            
            var child_keys = [];
            
            for(var i =0; i < jsondata.result.length; i++){
                var child_page = jsondata.result[i];
                child_keys[i] = child_page.key;
                page_cache[child_page.key] = child_page;
            }
            child_key_cache[page_key] = child_keys;
        }
        
        displayBranchLinks(jsondata.result);
    });
}

function displayBranchLinks(links){
    $("#link_container").empty();
    if(0 < links.length){
        for(var i =0; i < links.length; i++){
            appendLink(links[i]);
        }
    }else{
        var template = $("#no_links_template").html();
        $("#link_container").append(template);
        
    }
}


function appendPage(page){
    var template = $("#page_template").html();
    
    template = template.replace(/##page\.content##/g,page.content);
    template = template.replace(/##page\.link##/g,page.link);
    template = template.replace(/##page\.key##/g,page.key);
    template = template.replace(/##page\.child_count##/g,page.child_count);
    
    var author_info;
    
    if(page["author_name"] != null){
        
        var href = "javascript:window.open('/user?user_key=" +page["author_info"]+ "', '_blank');";
        
        author_info = "by <a href=\""+href+"\">"+page["author_name"]+"</a>";
    }else{
        author_info = "by Anonymous";
    }
    
    template = template.replace("##author_info##",author_info);
    
    template = template.replace("##page_div_id##",page.key+"_page_div");
    template = template.replace("##like_div_id##",page.key+"_like_div");
    template = template.replace("##unlike_div_id##",page.key+"_unlike_div");
    
    template = template.replace("##like_count_span_id##",page.key+"_like_count_span");
    template = template.replace("##unlike_count_span_id##",page.key+"_unlike_count_span");
    
    $("#content_container").append(template);
    
    updateLikeInfo(page.key,page.like_value);
}

function appendLink(page){
    var template = $("#branch_link_template").html();
    var branch_link = template;
    branch_link = branch_link.replace(/##page\.link##/g,page.link);
    branch_link = branch_link.replace(/##page\.key##/g,page.key);
    branch_link = branch_link.replace(/##page\.score##/g,(page.child_count + page.like_count - page.unlike_count));
    $("#link_container").append(branch_link);
}
function returnToPage(page_key){
    resetToPage(page_key);
    showAddPageLink();
}
function resetToPage(page_key){
    active_page_key = page_key;
    $('#'+page_key+'_page_div').nextAll('div').remove();
    updateBranchLinks(page_key);
}
function showAddPageLink(){
    
    $('#add_page_link').addClass('add_page_active');
    $('#add_page_link').removeClass('add_page_inactive');
    
    $('#add_page_div').addClass('add_page_inactive');
    $('#add_page_div').removeClass('add_page_active');
    
    $("#add_page_div").empty();
}
function showAddPageForm(){
    
    var page = page_cache[active_page_key];
    
    $('#add_page_link').addClass('add_page_inactive');
    $('#add_page_link').removeClass('add_page_active');
    
    $('#add_page_div').addClass('add_page_active');
    $('#add_page_div').removeClass('add_page_inactive');
    
    $("#add_page_div").empty();
    
    var template = $("#add_branch_form_template").html();
    
    template = template.replace(/##page\.key##/g,page.key);
    
    $("#add_page_div").append(template);
    
    
    var form = $("#"+page.key+"_child_add_page_form");
    
    form.ajaxForm({
        type : 'post',
        success : function(data, status, xhr){
            var response = JSON.parse(data);
            if(response.status == "OK"){
                showAddPageLink();
                
                var added_page = response.result;
                
                page_cache[added_page.key] = added_page;
                
                openPage(added_page.key);
            }else{
                resetToPage(page.key);
                for(var key in response.result){
                    if(response.result.hasOwnProperty(key) && messages[key] != null){
                        $("#add_page_div").empty();
                        var template = $("#has_links_template").html();
                        template = template.replace(/##message##/g,messages[key]);
                        $("#add_page_div").append(template);
                    }
                }
            }
        }
    });
    
    var linkId = "#"+page.key+"_child_link";
    var contentId = "#"+page.key+"_child_content";
    
    form.submit(function() {
        
        var hasValidLink = 0 < $(linkId).val().length && $(linkId).val().length < config.link_max;
        var hasValidContent = 0 < $(contentId).val().length && $(contentId).val().length < config.content_max;
        
        if(!hasValidLink){
            $(linkId).addClass('invalid');
        }
        if(!hasValidContent){
            $(contentId).addClass('invalid');
        }
        return hasValidLink && hasValidContent;
    });
    var form_textareas=[{
        textareaId:linkId,
        maxCharacters: config.link_max, // Characters limit  
        statusClass: "chars_left", // The class on the status div 
        notificationClass: "invalid", 
        statusText: "", // The status text 
    },{
        textareaId:contentId,
        maxCharacters: config.content_max, // Characters limit  
        statusClass: "chars_left", // The class on the status div 
        notificationClass: "invalid", 
        statusText: "", // The status text 
    }];
    
    for(var i =0; i < form_textareas.length; i++){ var 
        textarea = form_textareas[i];  
        $(textarea.textareaId).maxlength(textarea);  
    } 
    
}
var messages = {
    'has_branches':'The branch could not be added. You can not create any more branches for this page.',
    'has_identical_link':'The branch could not be added. A branch with an identical link already exists.',
    'unauthenticated':'The branch could not be added. You are not logged in.',
};

