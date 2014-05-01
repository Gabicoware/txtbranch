var notification_type_messages = {
    'new_branch':"added a branch",
    'edit_branch':"edited a branch"
};

function activeUsername(){
    var index = location.pathname.lastIndexOf("/") + 1;
    return location.pathname.substr(index);
}

function showBranches(){
    $("#contents").empty();
    $.get('/api/v1/branchs?authorname='+activeUsername(), function(data) {
        var jsondata = JSON.parse(data);
        if(jsondata.status == "OK"){
            var branches = jsondata.result;
            for (var i = 0; i < branches.length; i++) {
                var branchHTML = prepareBranchHTML(branches[i]);
                $("#contents").append(branchHTML);
            }
        }
    });

}

function prepareBranchHTML(branch){
    var template = $("#branch_template").html();
    
    template = template.replace(/##branch\.tree_name##/g, branch.tree_name);
    template = template.replace(/##branch\.content##/g, branch.content);
    template = template.replace(/##branch\.link##/g, branch.link);
    template = template.replace(/##branch\.key##/g, branch.key);
    
    return template;
}

function prepareNotificationHTML(notification){
    var template = $("#notification_template").html();
    
    template = template.replace(/##notification\.from_username##/g, notification.from_username);
    
    var message = notification_type_messages[notification.notification_type];
    template = template.replace(/##notification\.message##/g, message);
    
    template = template.replace(/##notification\.tree_name##/g, notification.tree_name);
    template = template.replace(/##notification\.branch##/g, notification.branch);
    template = template.replace(/##notification\.branch_link##/g, notification.branch_link);
    
    return template;
}

function showNotifications(){
    $("#contents").empty();
    $.get('/api/v1/notifications', function(data) {
        var jsondata = JSON.parse(data);
        if(jsondata.status == "OK"){
            var notifications = jsondata.result;
            for (var i = 0; i < notifications.length; i++) {
                var notificationHTML = prepareNotificationHTML(notifications[i]);
                $("#contents").append(notificationHTML);
            }
        }
    });
}

function showActivity(){
    $("#contents").empty();
    $.get('/api/v1/notifications?from_username='+activeUsername(), function(data) {
        var jsondata = JSON.parse(data);
        if(jsondata.status == "OK"){
            var notifications = jsondata.result;
            for (var i = 0; i < notifications.length; i++) {
                var notificationHTML = prepareNotificationHTML(notifications[i]);
                $("#contents").append(notificationHTML);
            }
        }
    });
}

function updateLocation(){
    var section = getParameterByName('section');
    if(section == null || section == ""){
        section = "branches";
    }
    $("#branches_li").removeClass("active");
    $("#notifications_li").removeClass("active");
    $("#activity_li").removeClass("active");
    $("#"+section+"_li").addClass("active");
    
    if(section == "branches"){
        showBranches();
    }else if(section == "notifications"){
        showNotifications();
    }else if(section == "activity"){
        showActivity();
    }
}