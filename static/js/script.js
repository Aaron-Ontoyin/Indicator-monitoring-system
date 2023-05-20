// Search (filter) variables script
$(document).ready(function(){
$("#search-input").on("keyup", function() {
    var value = $(this).val().toLowerCase();
    $("#variables li").filter(function() {
    $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
    });
});
});