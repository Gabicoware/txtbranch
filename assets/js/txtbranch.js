
function getParameterByName(name){
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/,"\\\]");
    var regex = new RegExp("[\\?&#]" + name + "=([^&#]*)"),
        results = regex.exec(location.hash);
    if (results == null) {
        results = regex.exec(location.search);
    }
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g," "));
}

var tree_name = null;
var active_branch_key = null;
var branch_cache = {};
var edited_branch_key = null;
var child_key_cache = {};

function toggleLike(branch_key,param_value){
    
    var branch = branch_cache[branch_key];
    
    if(branch.like_value == param_value){
        param_value = 0;
    }
    
    $.get('/api/v1/likes?branch_key='+branch_key+'&value='+param_value, function(data) {
        var jsondata = JSON.parse(data);
        if(jsondata.status == 'OK'){
            branch.like_value = param_value;
            updateLikeInfo(branch_key,branch.like_value);
        }
    });
}

function updateLikeInfo(branch_key,value){
    
    var branch = branch_cache[branch_key];
    
    var like_div = $('#'+branch_key+'_like_div');
    if(value == 1){
        like_div.addClass("like_active");
        like_div.removeClass("like_inactive");
    }else{
        like_div.removeClass("like_active");
        like_div.addClass("like_inactive");
    }
    
    var unlike_div = $('#'+branch_key+'_unlike_div');
    if(value == -1){
        unlike_div.addClass("unlike_active");
        unlike_div.removeClass("unlike_inactive");
    }else{
        unlike_div.removeClass("unlike_active");
        unlike_div.addClass("unlike_inactive");
    }
    var score_span = $('#'+branch_key+'_score_span');
    score_span.text(branch.like_count - branch.unlike_count + branch.child_count + value);
    
}

function showConventions(){
    $("#show_conventions_div").hide();
    $("#hide_conventions_div").show();
    $("#conventions_div").show();
    $.cookie("conventions_show_"+tree_name,"1");
}

function hideConventions(){
    $("#show_conventions_div").show();
    $("#hide_conventions_div").hide();
    $("#conventions_div").hide();
    $.cookie("conventions_show_"+tree_name,"0");
}

function openBranch(branch_key){
    
    var branch = branch_cache[branch_key];
    
    tree_name = branch.tree_name;
    
    active_branch_key = branch_key;
    
    appendBranch(branch);
    
    updateBranchLinks(branch_key);
    
    loadParent(branch);
    
    if(!hasAddBranchFormContent()){
        showAddBranchLink();
    }
    window.location.hash = "branch_key="+branch_key;
    
    updateOptions(false);
    
    
}

function reloadBranch(branch_key){
    
    var branch = branch_cache[branch_key];
    
    $("#"+branch_key+"_branch_div").replaceWith(prepareBranchHTML(branch));
    
}


function updateOptions(isEditing){
    
    var branch = branch_cache[active_branch_key];
    var username = $.cookie("username");
    if(branch.authorname == username && !isEditing){
        $("#current_branch_options_div").show();
    }else{
        $("#current_branch_options_div").hide();
    }
    
}

function editActiveBranch(shouldEdit){
    $("#edit_branch_div").empty();
        
    updateOptions(shouldEdit);
    if(shouldEdit){
        $('#'+active_branch_key+'_branch_div').hide();
            
        var branch = branch_cache[active_branch_key];
        
        $('#edit_branch_div').show();
        
        
        var template = $("#edit_branch_form_template").html();
        
        template = template.replace(/##branch\.key##/g,branch.key);
        template = template.replace(/##branch\.content##/g,branch.content);
        template = template.replace(/##branch\.link##/g,branch.link);
        
        $("#edit_branch_div").append(template);
        
        var formId = "#"+branch.key+"_edit_branch_form";
        var form = $(formId);
        
        form.ajaxForm({
            type : 'put',
            success : updateBranchCompleteHandler
        });
        
        linkId = "#"+branch.key+"_link";
        contentId = "#"+branch.key+"_content";
        
        setupForm( formId, linkId, contentId );
        
        edited_branch_key = active_branch_key;
    
    }else{
        $('#edit_branch_div').hide();
        $('#'+active_branch_key+'_branch_div').show();
    }
}

function updateBranchCompleteHandler(data, status, xhr){
    branchCompleteHandler(data,status,xhr);
    editActiveBranch(false);
    updateOptions(false);
}


function branchCompleteHandler(data, status, xhr){
    var response = JSON.parse(data);
    if(response.status == "OK"){
        showAddBranchLink();
        
        var added_branch = response.result;
        
        branch_cache[added_branch.key] = added_branch;
        
        if( edited_branch_key == added_branch.key){
            edited_branch_key = null;
            reloadBranch(added_branch.key);
        }else{
            openBranch(added_branch.key);
        }
    }else{
        resetToBranch(branch.key);
        for(var key in response.result){
            if(response.result.hasOwnProperty(key) && add_branch_messages[key] != null){
                //$("#add_branch_div").empty();
                var template = $("#has_links_template").html();
                template = template.replace(/##message##/g,add_branch_messages[key]);
                $("#add_branch_div").prepend(template);
            }
        }
    }
}

function openParentBranch(parent_branch_key){
    
    var branch = branch_cache[parent_branch_key];
    
    prependBranch(branch);
    
    loadParent(branch);
}

function loadParent(branch){
    
    $("#parent_container").empty();
        
    if(branch["parent_branch"] == null){
        $("#parent_container").hide();
    }else{
        
        var div_id = branch.parent_branch+"_branch_div";
        
        if(0 == $("#"+div_id).length){
            
            var parent_branch = branch_cache[branch.parent_branch];
            
            if(parent_branch == null){
                $.get('/api/v1/branchs?branch_key='+branch.parent_branch, function(data,textStatus,xhr) {
                    var jsondata = JSON.parse(data);
                    
                    if(jsondata.status == 'OK' && 0 < jsondata.result.length){
                        var parent_branch = jsondata.result[0];
                        branch_cache[parent_branch.key] = parent_branch;
                        showParent(parent_branch);
                    }
                });
            }else{
                showParent(parent_branch);
            }
        }
    }
}

function showParent(parent_branch){
    var parentBranchHTML = prepareParentBranchHTML(parent_branch);
    $("#parent_container").empty();
    $("#parent_container").append(parentBranchHTML);
}

function updateBranchLinks(branch_key){
    
    $("#branch_count_span").empty();
    
    var child_keys = child_key_cache[branch_key];
    if(child_keys!= null && 0 < child_keys.length){
        var child_branchs = [];
        for(var i = 0; i < child_keys.length; i++){
            child_branchs[i] = branch_cache[child_keys[i]];
        }
        showBranchLinks(child_branchs);
    }else{
        $("#link_container").empty();
    }

    $.get('/api/v1/branchs?parent_branch_key='+branch_key, function(data,textStatus,xhr) {
        var jsondata = JSON.parse(data);
        
        if(jsondata.status == 'OK' && 0 < jsondata.result.length){
            
            var child_keys = [];
            
            for(var i =0; i < jsondata.result.length; i++){
                var child_branch = jsondata.result[i];
                child_keys[i] = child_branch.key;
                branch_cache[child_branch.key] = child_branch;
            }
            child_key_cache[branch_key] = child_keys;
        }
        
        showBranchLinks(jsondata.result);
    });
}

function showBranchLinks(links){
    $("#link_container").empty();
    if(0 < links.length){
        for(var i =0; i < links.length; i++){
            var branch = links[i];
            appendLink(branch);
            updateLikeInfo(branch.key,branch.like_value);

        }
    }else{
        var template = $("#no_links_template").html();
        $("#link_container").append(template);
        
    }
    $("#branch_count_span").empty();
    $("#branch_count_span").append(links.length);
}


function appendBranch(branch){
    var branchHTML = prepareBranchHTML(branch);
    $("#content_container").append(branchHTML);
    updateLikeInfo(branch.key,branch.like_value);
}

function prependBranch(branch){
    var branchHTML = prepareBranchHTML(branch);
    $("#content_container").prepend(branchHTML);
    updateLikeInfo(branch.key,branch.like_value);
}

function prepareParentBranchHTML(branch){
    var template = $("#parent_branch_template").html();
    
    template = template.replace(/##branch\.link##/g,branch.link);
    template = template.replace(/##branch\.key##/g,branch.key);
    
    return template;
}

function prepareBranchHTML(branch){
    var template = $("#branch_template").html();
    
    template = template.replace(/##branch\.content##/g,branch.content);
    template = template.replace(/##branch\.link##/g,branch.link);
    template = template.replace(/##branch\.key##/g,branch.key);
    template = template.replace(/##branch\.score##/g,(branch.child_count + branch.like_count - branch.unlike_count));
    
    var href = "javascript:window.open('/user/" +branch["authorname"]+ "', '_blank');";
        
    var author_info = "by <a href=\""+href+"\">"+branch["authorname"]+"</a>";
    
    template = template.replace("##author_info##",author_info);
    
    template = template.replace("##branch_div_id##",branch.key+"_branch_div");
    template = template.replace("##like_div_id##",branch.key+"_like_div");
    template = template.replace("##unlike_div_id##",branch.key+"_unlike_div");
    
    template = template.replace("##score_span_id##",branch.key+"_score_span");
    
    return template;
}

function appendLink(branch){
    var template = $("#branch_link_template").html();
    template = template.replace(/##branch\.link##/g,branch.link);
    template = template.replace(/##branch\.key##/g,branch.key);
    template = template.replace(/##branch\.score##/g,(branch.child_count + branch.like_count - branch.unlike_count));
    template = template.replace("##like_div_id##",branch.key+"_like_div");
    template = template.replace("##unlike_div_id##",branch.key+"_unlike_div");
    $("#link_container").append(template);
}
function returnToBranch(branch_key){
    resetToBranch(branch_key);
    showAddBranchLink();
}
function resetToBranch(branch_key){
    active_branch_key = branch_key;
    $('#'+branch_key+'_branch_div').nextAll('div').remove();
    updateBranchLinks(branch_key);
}
function showAddBranchLink(){
    
    $('#add_branch_div').hide();
    $('#add_branch_link').show();
        
    $("#add_branch_div").empty();
}

function updateAddBranchDiv(){
    if(!isLoggedIn()){
        showNeedLoginMessage();
    }else if(hasChildBranchs()){
        showHasChildBranchs();
    }else{
        showAddBranchForm();
    }
}

function hasChildBranchs(){

    var username = $.cookie("username");
    
    var branch_count = 0;
    
    var child_keys = child_key_cache[active_branch_key];
    
    if (child_keys != null){
        for(var i = 0; i < child_keys.length; i++){
            var child_branch = branch_cache[child_keys[i]];
            if(child_branch && child_branch.authorname == username){
                branch_count++;
            }
        }
    }

    return 2 <= branch_count;
}

function showHasChildBranchs(){
    
    $('#add_branch_link').hide();
    $('#add_branch_div').show();
    
    var template = $('#has_child_branchs_template').html();
    
    $("#add_branch_div").empty();
    $("#add_branch_div").append(template);
}

function showNeedLoginMessage(){
    $('#add_branch_link').hide();
    $('#add_branch_div').show();
    
    var template = $('#must_login_template').html();
    
    $("#add_branch_div").empty();
    $("#add_branch_div").append(template);
}

var linkId = null;
var contentId = null;

function hasAddBranchFormContent(){
    
    var linkValue = linkId != null ? $(linkId).val() : null;
    var contentValue = contentId != null ? $(contentId).val() : null;
    
    return linkValue != null && contentValue != null && (0 < contentValue.length || 0 < linkValue.length);
}

function showAddBranchForm(){
    
    var branch = branch_cache[active_branch_key];
    
    $('#add_branch_link').hide();
    $('#add_branch_div').show();
    
    $("#add_branch_div").empty();
    
    var template = $("#add_branch_form_template").html();
    
    template = template.replace(/##branch\.key##/g,branch.key);
    
    $("#add_branch_div").append(template);
    
    var formId = "#"+branch.key+"_child_add_branch_form";
    
    var form = $(formId);
    
    form.ajaxForm({
        type : 'post',
        success : branchCompleteHandler
    });
    
    linkId = "#"+branch.key+"_child_link";
    contentId = "#"+branch.key+"_child_content";
    
    setupForm( formId, linkId, contentId );
        
    if( $.cookie("conventions_show_"+tree_name) == "0" ){
        hideConventions();
    }else{
        showConventions();
    }
    
    $("html, body").animate({scrollTop:$(document).height()},1000);
    
}

function setupForm(formId,linkId,contentId){
    var form = $(formId);
    
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
        setupTextArea(textarea);
    }
}

function setupTextArea(textarea){
    $(textarea.textareaId).maxlength(textarea);  
    var hintId = textarea.textareaId+"_hint";
    if($(textarea.textareaId).val().length == 0){
        $(textarea.textareaId).focus(function(){
            $(hintId).css('visibility','hidden');
        });
    }else{
        $(hintId).css('visibility','hidden');
    }
}

var add_branch_messages = {
    'has_branches':'The branch could not be added. You can not create any more branches for this branch.',
    'has_identical_link':'The branch could not be added. A branch with an identical link already exists.',
    'unauthenticated':'The branch could not be added. You are not logged in.'
};

var authentication_messages = {
    'add_branch':'You must be logged in to add a branch'
};

var active_branch_info = null;

function branchInfoClickHandler(event){
    if(active_branch_info != null){
        $(active_branch_info).removeClass('active_branch_info');
    }
    if(active_branch_info != event.currentTarget){
        $(event.currentTarget).addClass('active_branch_info');
        active_branch_info = event.currentTarget;
    }else{
        active_branch_info = null;
    }
}
