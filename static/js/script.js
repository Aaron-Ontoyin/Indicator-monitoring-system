// Search (filter) variables script
$(document).ready(function(){
$("#search-input").on("keyup", function() {
    var value = $(this).val().toLowerCase();
    $("#variables li").filter(function() {
    $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
    });
});
});

$(".alert").delay(4000).slideUp(200, function() {
    $(this).alert('close');
});

// // Handle variable selection for data entry
// $(document).on('click', '.variable', function() {
//     var variableId = $(this).data('id');

//     $.ajax({
//         url: '/get_variable_details/',
//         type: 'GET',
//         data: { variable_id: variableId },
//         success: function(response) {
//             // Update the work area with the retrieved details
//             $('#workarea').html(response);
//         },
//         error: function(xhr, textStatus, error) {
//             // Handle error
//             console.log(error);
//         }
//     });
// });
