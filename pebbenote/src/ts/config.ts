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

function buildConfigPage(current: string) {
  return `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pebbenote</title>
<style>
  body { font-family: sans-serif; margin: 16px; }
  input { width: 100%; box-sizing: border-box; padding: 8px; font-size: 16px; }
  button { margin-top: 12px; padding: 10px 16px; font-size: 16px; }
</style>
</head>
<body>
<h2>Backend URL</h2>
<input id="url" type="url" placeholder="${DEFAULT_BASE}" value="${current.replace(/"/g, "&quot;")}">
<br>
<button id="save">Save</button>
<button id="reset">Reset to default</button>
<script>
  var returnTo = new URLSearchParams(location.search).get("return_to") || "pebblejs://close#";
  function done(url) {
    location.href = returnTo + encodeURIComponent(JSON.stringify({ backendUrl: url }));
  }
  document.getElementById("save").onclick = function () {
    done(document.getElementById("url").value.trim());
  };
  document.getElementById("reset").onclick = function () { done(""); };
</script>
</body>
</html>`;
}

export function configPageUrl() {
  const stored = localStorage.getItem(STORAGE_KEY) || "";
  return (
    "data:text/html;charset=utf-8," +
    encodeURIComponent(buildConfigPage(stored))
  );
}
