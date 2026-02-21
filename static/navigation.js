(function () {
  var nav = document.querySelector(".page-nav[data-owner]");
  if (!nav) return;

  // ── Add ──────────────────────────────
  var addWrap = nav.querySelector(".page-nav-add-wrap");
  var addBtn = addWrap.querySelector(".page-nav-add");
  var addInput = addWrap.querySelector(".page-nav-add-input");

  addBtn.addEventListener("mousedown", function (e) {
    e.preventDefault();
  });

  addBtn.addEventListener("click", function () {
    if (addInput.classList.contains("active")) {
      cancelAdd();
      return;
    }
    addInput.classList.add("active");
    addInput.value = "";
    addInput.focus();
  });

  function cancelAdd() {
    addInput.classList.remove("active");
  }

  addInput.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      cancelAdd();
      return;
    }
    if (e.key !== "Enter") return;
    e.preventDefault();
    var title = addInput.value.trim();
    if (!title) return;
    fetch("/settings/navigation/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title }),
    }).then(function (res) {
      if (res.ok) window.location.reload();
    });
  });

  addInput.addEventListener("blur", function () {
    cancelAdd();
  });

  // ── Reorder (HTML5 DnD) ─────────────
  var dragged = null;

  nav.addEventListener("dragstart", function (e) {
    var item = e.target.closest(".page-nav-item");
    if (!item) return;
    dragged = item;
    item.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  });

  nav.addEventListener("dragend", function () {
    if (dragged) dragged.classList.remove("dragging");
    dragged = null;
  });

  nav.addEventListener("dragover", function (e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  });

  nav.addEventListener("drop", function (e) {
    e.preventDefault();
    if (!dragged) return;
    var target = e.target.closest(".page-nav-item");
    if (!target || target === dragged) return;
    var rect = target.getBoundingClientRect();
    var after = e.clientX > rect.left + rect.width / 2;
    if (after) {
      nav.insertBefore(dragged, target.nextSibling);
    } else {
      nav.insertBefore(dragged, target);
    }
    nav.appendChild(addWrap);
    fixSeparators();
    saveOrder();
  });

  function saveOrder() {
    var items = nav.querySelectorAll(".page-nav-item");
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

  function createSep() {
    var sep = document.createElement("span");
    sep.className = "page-nav-sep";
    sep.innerHTML = "&middot;";
    return sep;
  }

  function ensureSep(el, shouldHave) {
    var sep = el.querySelector(".page-nav-sep");
    if (shouldHave && !sep) {
      el.insertBefore(createSep(), el.firstChild);
    } else if (!shouldHave && sep) {
      sep.remove();
    }
  }

  function fixSeparators() {
    var items = nav.querySelectorAll(".page-nav-item");
    var hasHome = !!nav.querySelector(":scope > a");
    for (var i = 0; i < items.length; i++) {
      ensureSep(items[i], i > 0 || hasHome);
    }
    ensureSep(addWrap, items.length > 0 || hasHome);
  }
})();
