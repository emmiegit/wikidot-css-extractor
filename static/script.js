function initTableSort() {
  // Init table sort
  var tableElement = document.getElementById('page-list');
  new Tablesort(tableElement, { descending: true });

  // Disable table sort notice
  var noticeElements = document.getElementsByClassName('table-sort-notice');
  for (var i = 0; i < noticeElements.length; i++) {
    noticeElements[i].remove();
  }

  console.info("Initialized tablesort for " + tableElement);
}
