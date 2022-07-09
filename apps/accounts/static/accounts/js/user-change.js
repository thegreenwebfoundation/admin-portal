window.addEventListener('load', function (e) {
  ")
  // A listener on the user change form to
  // make it easier to clear the hosting provider
  // selection
  django.jQuery('#clear-hosting-provider').on('click', function (ev) {
    // we need to trigger the change event after clearing the value
    // for the select2 widget to pick up the change and show
    // the cleared object
    django.jQuery('#id_hostingprovider').val('').trigger('change');
  })
});
