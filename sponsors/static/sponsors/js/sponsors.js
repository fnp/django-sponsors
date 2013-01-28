(function($) {
    $(function() {

        $('.sponsor-logos').each(function() {
            if ($(this).children().length > 1)
                $(this).cycle({timeout: 3000});
        });

    });
})(jQuery);

