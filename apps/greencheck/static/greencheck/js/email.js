(function($) {
    $(document).ready(function() {
        $('.sendEmail').click(function(e) {
            let parent = e.target.parentElement.parentElement.parentElement;
            let selected_value = $(parent).find('option:selected').val();
            let query = "?email=" + selected_value;
            let url = e.target.attributes.href.value + query;
            $(e.target).attr("href", url);
        });
    });
})(django.jQuery);
