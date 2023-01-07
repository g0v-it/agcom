$("#politicianlink").click(function() {
    $("#searching").hide();
    $('#viewdata').hide();
    $("#cercapolitico").show();
    $("#stats").hide();
});

function timeHumanReadable(inminutes) {
    var days = Math.floor(inminutes / 1440);
    remainingMinutes = inminutes % 1440;
    hours = Math.floor(remainingMinutes / 60);
    minutes = remainingMinutes % 60;
    r = "";
    if (days == 0 && hours > 0 && minutes > 0) {
        r = hours + " ore e " + minutes + " minuti";
    }
    if (days == 0 && hours > 0 && minutes == 0) {
        r = hours + " ore";
    }
    if (days == 0 && hours == 0 && minutes == 0) {
        r = "";
    }
    if (days > 0 && hours > 0 && minutes > 0) {
        r = days + " giorni, " + hours + " ore e " + minutes + " minuti";
    }
    if (days > 0 && hours > 0 && minutes == 0) {
        r = days + " giorni, " + hours + " ore";
    }
    if (days > 0 && hours == 0 && minutes == 0) {
        r = days + " giorni";
    }
    return (r);
}

function get_data4calendar(year) {
    return (yearscalendar[year]);
}