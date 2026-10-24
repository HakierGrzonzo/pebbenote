export const DEFAULT_BASE = "http://localhost:8000";
const STORAGE_KEY = "backendUrl";

export function getBaseUrl(): string {
  const stored = localStorage.getItem(STORAGE_KEY);
  return (stored || DEFAULT_BASE).replace(/\/+$/, "");
}

export function setBaseUrl(url: string) {
  if (url) {
    localStorage.setItem(STORAGE_KEY, url);
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function isValidUrl(url: string) {
  return /^https?:\/\/\S+$/.test(url);
}

export type ConfigNote = {
  note_id: string;
  content: string;
  is_default: boolean;
};

export type ConfigResult = {
  backendUrl: string;
  newNotes: string[];
  // an existing note id, "new:<index>" for a pending note, or null for no change
  defaultId: string | null;
};

// Safe to embed inside an inline <script>
function jsonForScript(value: unknown) {
  return JSON.stringify(value)
    .replace(/</g, "\\u003c")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}

function buildConfigPage(current: string, notes: ConfigNote[] | null) {
  return `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pebbenote</title>
<style>
  body { font-family: sans-serif; margin: 16px; }
  input[type=url], input[type=text] { width: 100%; box-sizing: border-box; padding: 8px; font-size: 16px; }
  button { margin-top: 12px; padding: 10px 16px; font-size: 16px; }
  label { display: block; padding: 6px 0; }
</style>
</head>
<body>
<h2>Backend URL</h2>
<input id="url" type="url" placeholder="${DEFAULT_BASE}" value="${current.replace(/"/g, "&quot;")}">
<h2>Notes</h2>
<div id="notes"></div>
<input id="newText" type="text" placeholder="New note">
<button id="add">Add note</button>
<br>
<button id="save">Save</button>
<button id="reset">Reset URL to default</button>
<script>
  var returnTo = new URLSearchParams(location.search).get("return_to") || "pebblejs://close#";
  var notes = ${jsonForScript(notes)};
  var pending = [];
  var defaultId = null;
  var initialDefault = null;
  (notes || []).forEach(function (n) { if (n.is_default) { defaultId = initialDefault = n.note_id; } });

  function label(text, suffix) {
    var first = (text.split("\\n")[0] || "").trim() || "(empty)";
    return (first.length > 40 ? first.slice(0, 40) + "…" : first) + suffix;
  }
  function render() {
    var box = document.getElementById("notes");
    box.textContent = "";
    if (notes === null) {
      box.textContent = "Backend unreachable - notes unavailable.";
      return;
    }
    var rows = notes.map(function (n) { return { id: n.note_id, text: label(n.content, "") }; })
      .concat(pending.map(function (t, i) { return { id: "new:" + i, text: label(t, " (new)") }; }));
    rows.forEach(function (r) {
      var l = document.createElement("label");
      var radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "default";
      radio.checked = r.id === defaultId;
      radio.onchange = function () { defaultId = r.id; };
      l.appendChild(radio);
      l.appendChild(document.createTextNode(" " + r.text + (r.id === defaultId ? " - default" : "")));
      box.appendChild(l);
    });
  }
  function done(url) {
    var result = {
      backendUrl: url,
      newNotes: pending,
      defaultId: defaultId !== initialDefault ? defaultId : null
    };
    location.href = returnTo + encodeURIComponent(JSON.stringify(result));
  }
  document.getElementById("add").onclick = function () {
    var input = document.getElementById("newText");
    var text = input.value.trim();
    if (!text) return;
    pending.push(text);
    input.value = "";
    render();
  };
  document.getElementById("save").onclick = function () {
    done(document.getElementById("url").value.trim());
  };
  document.getElementById("reset").onclick = function () { done(""); };
  render();
</script>
</body>
</html>`;
}

export function configPageUrl(notes: ConfigNote[] | null) {
  const stored = localStorage.getItem(STORAGE_KEY) || "";
  return (
    "data:text/html;charset=utf-8," +
    encodeURIComponent(buildConfigPage(stored, notes))
  );
}
