function initTableSort() {
  var tableElement = document.getElementById('page-list');
  new Tablesort(tableElement, { descending: true });

  var noticeElement = document.getElementById('table-sort-notice');
  noticeElement.remove();

  console.info("Initializing tablesort for " + tableElement);
}
