$(document).ready(function () {
    "use strict";
    // ---------------------------------------------//
    //  Background
    //--------------------------------------------- //
    $("[data-background]").each(function () {
        $(this).attr('style', 'background-image:url(' + $(this).attr("data-background") + ')');
    });
    // ---------------------------------------------//
    //  Background
    //--------------------------------------------- //
    if ($('.range-slider').length > 0) {
        var nonLinearSlider = $('.range-slider');
        var startMin = parseInt(nonLinearSlider.data('start-min'));
        var startMax = parseInt(nonLinearSlider.data('start-max'));
        var min = parseInt(nonLinearSlider.data('min'));
        var max = parseInt(nonLinearSlider.data('max'));
        var step = parseInt(nonLinearSlider.data('step'));

        var slider = document.getElementById('nouislider');

        noUiSlider.create(slider, {
            connect: true,
            behaviour: 'tap',
            'step': step,
            start: [startMin, startMax],
            tooltips: [true, true],
            range: {
                'min': [min],
                'max': [max]
            },
            pips: {
                mode: 'positions',
                values: [0, 25, 50, 75, 100],
                density: 3
            }
        });
    }
    //-------------------------------------------------------
    // Date Picker
    //-------------------------------------------------------*/
    if ($('.date_range_picker').length > 0) {
        var today = moment();
        $('.date_range_picker').daterangepicker({
            // "autoApply": true,
            "alwaysShowCalendars": true,
            "startDate": today,
            "opens": "center"
        }, function (start, end, label) {
            console.log('New date range selected: ' + start.format('YYYY-MM-DD') + ' to ' + end.format('YYYY-MM-DD') + ' (predefined range: ' + label + ')');
        });
    };
    if ($('.date_picker').length > 0) {
        var today = moment();
        $('.date_picker').daterangepicker({
            "autoApply": true,
            "singleDatePicker": true,
            "alwaysShowCalendars": true,
            "startDate": today,
            "opens": "center"
        }, function (start, end, label) {
            console.log('New date range selected: ' + start.format('YYYY-MM-DD') + ' to ' + end.format('YYYY-MM-DD') + ' (predefined range: ' + label + ')');
        });
    };
    // -------------------------------------------//
    //  Custom Select
    // -------------------------------------------//
   /* if ($("select").length > 0) {
        $('select:not(.ignore)').select2({
            selectionCssClass: ':all:'
        });
        $(".select2-selection--single.wide").parent().addClass("wide");
        $(".selection.wide").parent().addClass("wide");
    }*/

    // ---------------------------------------------//
    // Slick Slider
    // ---------------------------------------------//
    $('.slider').each(function () {
        var play = $(this).data('autoplay');
        var playSpeed = $(this).data('autoplay-speed');
        var nav = $(this).data('nav');
        var dot = $(this).data('dots');
        var slidesToshow = $(this).data('slides-to-show');
        var slidesToscroll = $(this).data('slides-to-scroll');
        var slideCenter = $(this).data('slick-center-mode');
        $(this).slick({
            arrows: nav,
            dots: dot,
            slidesToShow: slidesToshow,
            autoplay: play,
            autoplaySpeed: playSpeed,
            centerMode: slideCenter,
            slidesToScroll: slidesToscroll,
            responsive: [{
                breakpoint: 500,
                settings: {
                    slidesToShow: slidesToshow < 2 ? slidesToshow : 1
                }
            }, {
                breakpoint: 768,
                settings: {
                    slidesToShow: slidesToshow < 2 ? slidesToshow : 3
                }
            }]
        });
    });
    $('.slider-for').each(function () {
        var play = $(this).data('autoplay');
        var playSpeed = $(this).data('autoplay-speed');
        var nav = $(this).data('nav');
        var dot = $(this).data('dots');
        var slidesToshow = $(this).data('slides-to-show');
        var slidesToscroll = $(this).data('slides-to-scroll');
        var slideCenter = $(this).data('slick-center-mode');
        $(this).slick({
            arrows: nav,
            dots: dot,
            slidesToShow: slidesToshow,
            autoplay: play,
            autoplaySpeed: playSpeed,
            centerMode: slideCenter,
            slidesToScroll: slidesToscroll,
            asNavFor: ".slider-nav",
            responsive: [{
                breakpoint: 500,
                settings: {
                    slidesToShow: slidesToshow < 2 ? slidesToshow : 1
                }
            }, {
                breakpoint: 768,
                settings: {
                    slidesToShow: slidesToshow < 2 ? slidesToshow : 3
                }
            }]
        });
    });
    $('.slider-nav').each(function () {
        var play = $(this).data('autoplay');
        var playSpeed = $(this).data('autoplay-speed');
        var nav = $(this).data('nav');
        var dot = $(this).data('dots');
        var slidesToshow = $(this).data('slides-to-show');
        var slidesToscroll = $(this).data('slides-to-scroll');
        var slideCenter = $(this).data('slick-center-mode');
        $(this).slick({
            arrows: nav,
            dots: dot,
            slidesToShow: slidesToshow,
            autoplay: play,
            autoplaySpeed: playSpeed,
            centerMode: slideCenter,
            slidesToScroll: slidesToscroll,
            asNavFor: ".slider-for",
            focusOnSelect: true
        });
    });


    // ---------------------------------------------//
    // add Remove item
    // ---------------------------------------------//
    $('.qty-input i').on('click', function () {
        var val = parseInt($('.qty-input input').val());

        if ($(this).hasClass('less')) {
            val = val - 1;
        } else if ($(this).hasClass('more')) {
            val = val + 1;
        }

        if (val < 1) {
            val = 1;
        }

        $('.qty-input input').val(val);
    })

    // ---------------------------------------------//
    // File Upload name add
    // ---------------------------------------------//
    $('.custom-input-file').each(function () {
        var $input = $(this),
            $label = $input.next('label'),
            labelVal = $label.html();

        $input.on('change', function (e) {
            var fileName = '';

            if (this.files && this.files.length > 1)
                fileName = (this.getAttribute('data-multiple-caption') || '').replace('{count}', this.files.length);
            else if (e.target.value)
                fileName = e.target.value.split('\\').pop();

            if (fileName)
                $label.find('span').html(fileName);
            else
                $label.html(labelVal);
        });

        // Firefox bug fix
        $input
            .on('focus', function () {
                $input.addClass('has-focus');
            })
            .on('blur', function () {
                $input.removeClass('has-focus');
            });
    });

    var websiteWidth = $(document).width();
    $(".header-links-item .header-childrenItem-parent").on("mouseover", function (event) {
        var liparent = $(this.parentElement);
        var ulChild = liparent.find('.header-childrenItem-child-category-links');
        var xOffset = liparent.offset().left;
        var alignRight = ($(document).width() - xOffset) < xOffset;

        if ($(document).width() > websiteWidth) {
            ulChild.addClass("dropdown-menu-right");
        }
    });

    $(".header-search input.custom-search").on("click", function (event) {
        if ($(".search-content .search-product").hasClass("d-none")) {
            $(".search-content").find('.search-product').removeClass('d-none');
            if ($('.search_overlay').length > 0 == false) {
                $("body").append('<div class="search_overlay"></div>');
            }
            $(".header , .announcement-header").css({ "zIndex": "99999" });
            $("body").css({ "overflow": "hidden" });
        } else {
            $(".search-content").find('.search-product').addClass('d-none');
            $("body").find('.search_overlay').remove();
            $(".header , .announcement-header").attr({ "style": "" });
            $("body").attr({ "style": "" });
        }
    });
    $(document).on("click", ".search_overlay", function (event) {
        $(".search-content").find('.search-product').addClass('d-none');
        $("body").find('.search_overlay').remove();
        $(".header , .announcement-header").attr({ "style": "" });
        $("body").attr({ "style": "" });
    });

    $(".open-sidebar").on("click", function (event) {
        $('.menu-sidebar').addClass("show");
        $('.overlay').addClass("show");
    });
    $(".close").on("click", function (event) {
        $('.menu-sidebar').removeClass("show");
        $('.overlay').removeClass("show");
    });
    $(".overlay").on("click", function (event) {
        $('.menu-sidebar').removeClass("show");
        $('.overlay').removeClass("show");
    });

});