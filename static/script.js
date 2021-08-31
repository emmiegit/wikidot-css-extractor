// Wait a bit first
setTimeout(100, function() {
  var element = document.getElementById('page-list');
  if (element !== null) {
    // Actually initialize the table sorting
    console.info("Initializing tablesort for " + element);
    new Tablesort(element);
  }
});
