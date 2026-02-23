(function () {
  var preview = document.getElementById("design-preview");
  var layout = document.querySelector(".design-layout");
  var fontHeader = document.getElementById("font_header");
  var fontBody = document.getElementById("font_body");
  var accentPicker = document.getElementById("color_accent_picker");
  var accentText = document.getElementById("color_accent");
  var bgPicker = document.getElementById("color_bg_picker");
  var bgText = document.getElementById("color_bg");
  var textPicker = document.getElementById("color_text_picker");
  var textInput = document.getElementById("color_text");

  var HEX_RE = /^#[0-9a-fA-F]{6}$/;

  function resolveColor(cssVar) {
    var el = document.createElement("div");
    el.style.color = "var(" + cssVar + ")";
    document.body.appendChild(el);
    var rgb = getComputedStyle(el).color;
    document.body.removeChild(el);
    var match = rgb.match(/(\d+)/g);
    if (!match || match.length < 3) return null;
    return "#" + match.slice(0, 3).map(function (n) {
      return ("0" + parseInt(n).toString(16)).slice(-2);
    }).join("");
  }

  function applyFonts() {
    preview.style.setProperty("--site-font-header", fontHeader.value || "var(--font-sans)");
    preview.style.setProperty("--site-font", fontBody.value || "var(--font-sans)");
  }

  function applyAccent() {
    var val = accentText.value.trim();
    if (val) {
      preview.style.setProperty("--site-accent", val);
    } else {
      preview.style.removeProperty("--site-accent");
    }
  }

  function applyBackground() {
    var bg = bgText.value.trim();

    if (bg) {
      preview.style.setProperty("--site-bg", bg);
      layout.style.setProperty("--site-bg", bg);
      document.body.style.background = bg;
    } else {
      preview.style.removeProperty("--site-bg");
      layout.style.removeProperty("--site-bg");
      document.body.style.background = "";
    }
    applyTextColor();
  }

  function applyTextColor() {
    var bg = bgText.value.trim() || resolveColor("--site-bg") || "#333840";
    var text = textInput.value.trim();
    var derivedProps = ["--site-text", "--site-text-bright", "--site-text-muted", "--site-divider", "--site-code-bg"];

    if (text) {
      preview.style.setProperty("--site-text", text);
      preview.style.setProperty("--site-text-bright", text);
      preview.style.setProperty("--site-text-muted", "color-mix(in srgb, " + text + " 50%, " + bg + ")");
      preview.style.setProperty("--site-divider", "color-mix(in srgb, " + text + " 15%, " + bg + ")");
      preview.style.setProperty("--site-code-bg", "color-mix(in srgb, " + text + " 8%, " + bg + ")");
    } else {
      derivedProps.forEach(function (prop) {
        preview.style.removeProperty(prop);
      });
    }
  }

  function initPicker(picker, textEl) {
    if (textEl.value) return;
    var hex = resolveColor(picker.getAttribute("data-default"));
    if (hex) picker.value = hex;
  }

  function bindColorPair(picker, textEl, applyFn) {
    picker.addEventListener("input", function () {
      textEl.value = picker.value;
      applyFn();
    });
    textEl.addEventListener("input", function () {
      if (HEX_RE.test(textEl.value.trim())) {
        picker.value = textEl.value.trim();
      }
      applyFn();
    });
  }

  initPicker(accentPicker, accentText);
  initPicker(bgPicker, bgText);
  initPicker(textPicker, textInput);

  bindColorPair(accentPicker, accentText, applyAccent);
  bindColorPair(bgPicker, bgText, applyBackground);
  bindColorPair(textPicker, textInput, applyTextColor);

  fontHeader.addEventListener("change", applyFonts);
  fontBody.addEventListener("change", applyFonts);

  var cssFileInput = document.getElementById("css-file-input");
  if (cssFileInput) {
    cssFileInput.addEventListener("change", function () {
      document.getElementById("css-file-name").textContent = this.files[0].name;
      document.getElementById("css-upload-btn").hidden = false;
    });
  }

  applyFonts();
  applyAccent();
  applyBackground();
})();
