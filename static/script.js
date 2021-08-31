function initTableSort() {
  var element = document.getElementById('page-list');
  if (element === null) {
    alert("No table element found!");
    return;
  }

  console.info("Initializing tablesort for " + element);
  new Tablesort(element, { descending: true });
}
