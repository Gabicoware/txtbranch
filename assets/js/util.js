function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regex = new RegExp("[\\?&#]" + name + "=([^&#]*)"), results = regex.exec(location.hash);
    if (results == null) {
        results = regex.exec(location.search);
    }
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function currentUsername(){
    if($.cookie('_simpleauth_sess') != null || $.cookie('dev_appserver_login')){
        return $.cookie('username');
    }
    return null;
}
