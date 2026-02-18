(function () {
  var nav = document.querySelector(".page-nav[data-owner]");
  if (!nav) return;

  // ── Add ──────────────────────────────
  var addWrap = nav.querySelector(".page-nav-add-wrap");
  var addBtn = addWrap.querySelector(".page-nav-add");
  var addInput = addWrap.querySelector(".page-nav-add-input");

  addBtn.addEventListener("click", function () {
    addBtn.hidden = true;
    addInput.hidden = false;
    addInput.value = "";
    addInput.focus();
  });

  function cancelAdd() {
    addInput.hidden = true;
    addBtn.hidden = false;
  }

  addInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      var title = addInput.value.trim();
      if (!title) return;
      addInput.disabled = true;
      fetch("/settings/navigation/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title }),
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (result) {
          if (result.ok) {
            window.location.href = "/edit-page/" + result.data.slug;
          } else {
            alert(result.data.error || "Failed to add page");
            addInput.disabled = false;
            addInput.focus();
          }
        });
    }
    if (e.key === "Escape") {
      cancelAdd();
    }
  });

  addInput.addEventListener("blur", function () {
    cancelAdd();
  });

  // ── Delete ───────────────────────────
  nav.addEventListener("click", function (e) {
    var btn = e.target.closest(".page-nav-delete");
    if (!btn) return;
    var item = btn.closest(".page-nav-item");
    var link = item.querySelector("a");
    var title = link ? link.textContent : "this page";
    if (!confirm("Delete " + title + "?")) return;
    var id = item.dataset.id;
    fetch("/settings/navigation/delete/" + id, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    }).then(function (res) {
      if (res.ok) {
        item.remove();
        fixSeparators();
      }
    });
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
    // Keep add-wrap at end
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

  function fixSeparators() {
    var items = nav.querySelectorAll(".page-nav-item");
    for (var i = 0; i < items.length; i++) {
      var sep = items[i].querySelector(".page-nav-sep");
      if (i === 0) {
        if (sep) sep.remove();
      } else {
        if (!sep) {
          sep = document.createElement("span");
          sep.className = "page-nav-sep";
          sep.innerHTML = "&middot;";
          items[i].insertBefore(sep, items[i].firstChild);
        }
      }
    }
    // Handle add-wrap separator
    var addSep = addWrap.querySelector(".page-nav-sep");
    if (items.length === 0) {
      if (addSep) addSep.remove();
    } else {
      if (!addSep) {
        addSep = document.createElement("span");
        addSep.className = "page-nav-sep";
        addSep.innerHTML = "&middot;";
        addWrap.insertBefore(addSep, addWrap.firstChild);
      }
    }
  }
})();
