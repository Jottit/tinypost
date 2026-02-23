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
  var textField = document.getElementById("text-color-field");

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

  function luminance(hex) {
    var r = parseInt(hex.slice(1, 3), 16) / 255;
    var g = parseInt(hex.slice(3, 5), 16) / 255;
    var b = parseInt(hex.slice(5, 7), 16) / 255;
    return 0.299 * r + 0.587 * g + 0.114 * b;
  }

  function autoTextColor(bgHex) {
    return luminance(bgHex) > 0.5 ? "#444444" : "#cccccc";
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
    var text = textInput.value.trim();

    if (bg) {
      if (!text) {
        text = autoTextColor(bg);
        textPicker.value = text;
        textInput.value = text;
      }
      preview.style.setProperty("--site-bg", bg);
      layout.style.setProperty("--site-bg", bg);
      document.body.style.background = bg;
      preview.style.setProperty("--site-text", text);
      preview.style.setProperty("--site-text-bright", text);
      preview.style.setProperty("--site-text-muted", "color-mix(in srgb, " + text + " 50%, " + bg + ")");
      preview.style.setProperty("--site-divider", "color-mix(in srgb, " + text + " 15%, " + bg + ")");
      preview.style.setProperty("--site-code-bg", "color-mix(in srgb, " + text + " 8%, " + bg + ")");
    } else {
      preview.style.removeProperty("--site-bg");
      layout.style.removeProperty("--site-bg");
      document.body.style.background = "";
      preview.style.removeProperty("--site-text");
      preview.style.removeProperty("--site-text-bright");
      preview.style.removeProperty("--site-text-muted");
      preview.style.removeProperty("--site-divider");
      preview.style.removeProperty("--site-code-bg");
    }
  }

  function applyTextColor() {
    var bg = bgText.value.trim();
    var text = textInput.value.trim();
    if (bg && text) {
      preview.style.setProperty("--site-text", text);
      preview.style.setProperty("--site-text-bright", text);
      preview.style.setProperty("--site-text-muted", "color-mix(in srgb, " + text + " 50%, " + bg + ")");
      preview.style.setProperty("--site-divider", "color-mix(in srgb, " + text + " 15%, " + bg + ")");
      preview.style.setProperty("--site-code-bg", "color-mix(in srgb, " + text + " 8%, " + bg + ")");
    }
  }

  // Initialize pickers from computed CSS when no custom value is set
  if (!accentText.value) {
    var hex = resolveColor(accentPicker.getAttribute("data-default"));
    if (hex) {
      accentPicker.value = hex;
    }
  }

  if (!bgText.value) {
    var bgHex = resolveColor(bgPicker.getAttribute("data-default"));
    if (bgHex) {
      bgPicker.value = bgHex;
    }
  }

  if (!textInput.value) {
    var textHex = resolveColor(textPicker.getAttribute("data-default"));
    if (textHex) {
      textPicker.value = textHex;
    }
  }

  accentPicker.addEventListener("input", function () {
    accentText.value = accentPicker.value;
    applyAccent();
  });

  accentText.addEventListener("input", function () {
    var val = accentText.value.trim();
    if (/^#[0-9a-fA-F]{6}$/.test(val)) {
      accentPicker.value = val;
    }
    applyAccent();
  });

  bgPicker.addEventListener("input", function () {
    bgText.value = bgPicker.value;
    applyBackground();
  });

  bgText.addEventListener("input", function () {
    var val = bgText.value.trim();
    if (/^#[0-9a-fA-F]{6}$/.test(val)) {
      bgPicker.value = val;
    }
    applyBackground();
  });

  textPicker.addEventListener("input", function () {
    textInput.value = textPicker.value;
    applyTextColor();
  });

  textInput.addEventListener("input", function () {
    var val = textInput.value.trim();
    if (/^#[0-9a-fA-F]{6}$/.test(val)) {
      textPicker.value = val;
    }
    applyTextColor();
  });

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
