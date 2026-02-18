(function () {
  var list = document.getElementById("nav-items");
  if (!list) return;

  var dragged = null;

  list.addEventListener("dragstart", function (e) {
    var item = e.target.closest(".nav-item");
    if (!item) return;
    dragged = item;
    item.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  });

  list.addEventListener("dragend", function () {
    if (dragged) dragged.classList.remove("dragging");
    var items = list.querySelectorAll(".nav-item");
    for (var i = 0; i < items.length; i++) {
      items[i].classList.remove("drag-over");
    }
    dragged = null;
  });

  list.addEventListener("dragover", function (e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    var item = e.target.closest(".nav-item");
    if (!item || item === dragged) return;
    var items = list.querySelectorAll(".nav-item");
    for (var i = 0; i < items.length; i++) {
      items[i].classList.remove("drag-over");
    }
    item.classList.add("drag-over");
  });

  list.addEventListener("drop", function (e) {
    e.preventDefault();
    var target = e.target.closest(".nav-item");
    if (!target || target === dragged) return;
    var rect = target.getBoundingClientRect();
    var after = e.clientY > rect.top + rect.height / 2;
    if (after) {
      target.parentNode.insertBefore(dragged, target.nextSibling);
    } else {
      target.parentNode.insertBefore(dragged, target);
    }
    saveOrder();
  });

  function saveOrder() {
    var items = list.querySelectorAll(".nav-item");
    var order = [];
    for (var i = 0; i < items.length; i++) {
      order.push(parseInt(items[i].dataset.id, 10));
    }
    fetch("/settings/navigation/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order: order }),
    });
  }
})();
