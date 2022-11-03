window.addEventListener('load', function (e) {
    // A listener on the user change form to
    // make it easier to clear the hosting provider
    // selection
  
    // We use the version of jQuery that is bundled in django admin,
    // under the django namespace
    django.jQuery('#clear-hosting-provider').on('click', function (ev) {
      // we need to trigger the change event after clearing the value
      // for the select2 widget to pick up the change and show
      // the cleared object
  
      // See more below:
      // https://stackoverflow.com/questions/42951172/how-to-clear-select2-dropdown
      // https://select2.org/programmatic-control/add-select-clear-items#clearing-selections
  
      django.jQuery('#id_hostingprovider').val('').trigger('change');
    })
  });