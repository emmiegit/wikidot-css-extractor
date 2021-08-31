// Wait a bit first
settimeout(100, function() {
  var element = document.getElementById('page-list');
  if (element !== null) {
    // Actually initialize the table sorting
    new Tablesort(element);
  }
});
