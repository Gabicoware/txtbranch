var messages = {
    'valid_tree_name':"Names must be between 4 and 20 characters, and contain only numbers, letters, dashes, and underscores.",
    'invalid_name':"Names must be between 4 and 20 characters, and contain only numbers, letters, dashes, and underscores.",
    'tree_exists':"There is already a tree with this name."
};

var textareas = null;

function loadForm(){
    
    $.get('/api/v1/userinfos', function(data) {
        var jsondata = JSON.parse(data);
        if(jsondata.status == "OK"){
            var userinfo = jsondata.result;
            var components = location.pathname.split("/");
            var action = components[components.length - 1];
            
            if(action == "edit"){
                var treename = components[components.length - 2];
                $.get('/api/v1/trees?name='+treename, function(data) {
                    var jsondata = JSON.parse(data);
                    if(jsondata.status == "OK"){
                        var tree = jsondata.result;
                        if(tree.moderator == userinfo.usernam){
                            showEditTreeForm(tree);
                        }else{
                            showNotModerator();
                        }
                    }else{
                        showNoTree();
                    }
                });
            }else{
                showNewForm();
            }
        }else{
            showMustLogin();
        }
    });
    
}

function showMustLogin(){
    $("#main_div").html($("#needs_login_template").text());
}
function showNotModerator(){
    $("#main_div").html($("#not_moderator_template").text());
}
function showNoTree(){
    $("#main_div").html($("#no_tree_template").text());
}
function showEditTreeForm(tree){
    $("#main_div").html($("#edit_tree_form_template").text());
    
    $("#tree_name_label").html(tree.name);
    $("#tree_name").val(tree.name);
    $("#link_max").val(tree.link_max);
    $("#link_prompt").val(tree.link_prompt);
    $("#content_max").val(tree.content_max);
    $("#content_prompt").val(tree.content_prompt);
    $("#branch_max").val(tree.branch_max);
    $("#conventions").text(tree.conventions);
        
    setupEditFormHandlers();
}
function showNewForm(){
    
    $("#main_div").html($("#add_tree_form_template").text());
    
    setupTreeNameField();
    
    setupTypeField();
    
    setupTextareas();
    
    setupNewFormHandlers();
    
}
function showAddBranchLink(){
    document.getElementById('add_branch_div').className='add_branch_active';
    document.getElementById('add_branch_link').className='add_branch_inactive';
}

function setupTreeNameField(){
    $("#tree_name").focusin(function(value) {
        updateTreenameError(true);
    });
    
    $("#tree_name").focusout(function() {
        
        var treename = $('#tree_name').val();
        
        var isvalid = (/^[\d\w_\-]+$/.test(treename) && 4 <= treename.length && treename.length <= 20) || treename.length == 0;
        updateTreenameError(isvalid);
    });
    
    $("#tree_name").keyup(function() {
        
        var treename = $('#tree_name').val();
        
        var isvalid = (/^[\d\w_\-]+$/.test(treename) && treename.length <= 20) || treename.length == 0;
        updateTreenameError(isvalid);
    });
    
    var message = messages['valid_tree_name'];
    
    $("#tree_name_message").text(message);
    
}

function setupTypeField(){
                    
    setPrompts(false);
                
    var eventHandler = function(){
        if($("#content_moderator_only_on").prop('checked')){
            if( $("#link_prompt").val() == $("#default_link_prompt_0").text() && $("#content_prompt").val() == $("#default_content_prompt_0").text()){
                setPrompts(true);
            }
        }else{
            if( $("#link_prompt").val() == $("#default_link_prompt_1").text() && $("#content_prompt").val() == $("#default_content_prompt_1").text()){
                setPrompts(false);
            }
        }
        
    };
    
    $("#content_moderator_only_on").change(eventHandler);

    $("#content_moderator_only_off").change(eventHandler);
    
}

function setPrompts(moderator_only){
    if(moderator_only){
        $("#link_prompt").val($("#default_link_prompt_1").text());
        $("#content_prompt").val($("#default_content_prompt_1").text());
        
        $("#root_branch_link_hint").text($("#default_link_prompt_1").text());
        $("#root_branch_content_hint").text($("#default_content_prompt_1").text());
    }else{
        $("#link_prompt").val($("#default_link_prompt_0").text());
        $("#content_prompt").val($("#default_content_prompt_0").text());
        
        $("#root_branch_link_hint").text($("#default_link_prompt_0").text());
        $("#root_branch_content_hint").text($("#default_content_prompt_0").text());
    }
}

function updateTreenameError(isvalid){
    if(isvalid){
        
        $("#tree_name_message").text(messages['valid_tree_name']);
        $("#tree_name_message").removeClass('invalid_message');
        $("#tree_name_message").addClass('message');
        $("#tree_name").removeClass('invalid');
    }else{
        $("#tree_name_message").text(messages['valid_tree_name']);
        $("#tree_name_message").addClass('invalid_name');
        $("#tree_name_message").removeClass('message');
        $("#tree_name").addClass('invalid');
    }
    
}

function setupTextareas(){
    var eventHandler = function(event){
        var item = $($(event.currentTarget).prop("target"));
        item.prop("maxCharacters",event.currentTarget.value);
        item.trigger('keyup');
    };
    
    $("#link_max").prop("target",'#root_branch_link');
    $("#content_max").prop("target",'#root_branch_content');
    
    textareas={
        "link":{
            maxlengthInputId:'#link_max',
            textareaId:'#root_branch_link',
            maxCharacters: 64, // Characters limit  
            statusClass: "chars_left", // The class on the status div 
            maxCharactersFunction:function(){ return $("#root_branch_link").prop("maxCharacters"); },
            notificationClass: "invalid", 
            statusText: "", // The status text 
        },
        "content":{
            maxlengthInputId:'#content_max',
            textareaId:'#root_branch_content',
            maxCharacters: 256, // Characters limit  
            statusClass: "chars_left", // The class on the status div 
            maxCharactersFunction:function(){ return $("#root_branch_content").prop("maxCharacters"); },
            notificationClass: "invalid", 
            statusText: "", // The status text 
        }
    };
    
    for(var key in textareas){
        if(textareas.hasOwnProperty(key)){
            var textarea = textareas[key];  
            $(textarea.maxlengthInputId).change(eventHandler);
            $(textarea.maxlengthInputId).keyup(eventHandler);
            $(textarea.textareaId).prop("maxCharacters",textarea.maxCharacters);
            setupTextArea(textarea);
        }
    }
    
    $('#link_prompt').keyup(function(event){
        $("#root_branch_link_hint").html($(event.currentTarget).val());
    });
    $('#content_prompt').keyup(function(event){
        $("#root_branch_content_hint").html($(event.currentTarget).val());
    });
    
}

function setupNewFormHandlers(){
    $("#new_tree_form").ajaxForm({
        type : 'post',
        success : function(data, status, xhr){
            var response = JSON.parse(data);
            if(response.status == "OK"){
                
                window.location.href = "/tree/"+response["result"]["name"];
                //forward to 
            }else{
                //display errors
            }
        }
    });
    $("#new_tree_form").submit(function() {
        
        var getValidation = function(elementId,maxCharacters){
            
            var hasValidText = 0 < $(elementId).val().length && $(elementId).val().length < maxCharacters ;
            if(!hasValidText){
                $(elementId).addClass('invalid');
            }else{
                $(elementId).removeClass('invalid');
            }
            return hasValidText;
        };
        
        var hasValidLink = getValidation('#root_branch_link', textareas["link"].maxCharactersFunction() );
        var hasValidContent = getValidation('#root_branch_content', textareas["content"].maxCharactersFunction() );
        var hasValidLinkPrompt = getValidation('#link_prompt', textareas["link"].maxCharactersFunction() );
        var hasValidContentPrompt = getValidation('#content_prompt', textareas["content"].maxCharactersFunction() );
        
        var treename = $('#tree_name').val();
        var hasValidTreename = (/^[\d\w_\-]+$/.test(treename) && 4 <= treename.length && treename.length <= 20) || treename.length == 0;
        updateTreenameError(hasValidTreename);
        
        return hasValidTreename && hasValidLink && hasValidContent && hasValidLinkPrompt && hasValidContentPrompt;
    });
}

var request = false;

function setupEditFormHandlers(){
    $("#edit_tree_form").submit(function(event) {
        
        var getValidation = function(elementId,maxCharacters){
            
            var hasValidText = 0 < $(elementId).val().length && $(elementId).val().length < maxCharacters ;
            if(!hasValidText){
                $(elementId).addClass('invalid');
            }else{
                $(elementId).removeClass('invalid');
            }
            return hasValidText;
        };
        
        var hasValidLinkPrompt = getValidation('#link_prompt', $("#link_max").val() );
        var hasValidContentPrompt = getValidation('#content_prompt', $("#content_max").val() );
        
        if( hasValidLinkPrompt && hasValidContentPrompt){
            
            if (request) {
                request.abort();
            }
            // setup some local variables
            var $form = $(this);
            // let's select and cache all the fields
            var $inputs = $form.find("input, select, button, textarea");
            // serialize the data in the form
            var serializedData = $form.serialize();
        
            // let's disable the inputs for the duration of the ajax request
            // Note: we disable elements AFTER the form data has been serialized.
            // Disabled form elements will not be serialized.
            $inputs.prop("disabled", true);
        
            // fire off the request to /form.php
            request = $.ajax({
                url: "/api/v1/trees",
                type: "put",
                data: serializedData
            });
        
            // callback handler that will be called on success
            request.done(function (data, textStatus, jqXHR){
                // log a message to the console
                var response = JSON.parse(data);
                if(response.status == "OK"){
                    //forward to 
                    window.location.href = "/tree/"+response["result"]["name"];
                }else{
                    //display errors
                }
            });
        
            // callback handler that will be called on failure
            request.fail(function (jqXHR, textStatus, errorThrown){
                // log the error to the console
                console.error(
                    "The following error occured: "+
                    textStatus, errorThrown
                );
            });
        
            // callback handler that will be called regardless
            // if the request failed or succeeded
            request.always(function () {
                // reenable the inputs
                $inputs.prop("disabled", false);
            });
                    
        }
        
        // prevent default posting of form
        event.preventDefault();
        return false;
    });
}