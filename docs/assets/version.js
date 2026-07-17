// Show the SAME version as the app — 0.1.<commit-count> — computed live from
// the GitHub API, so it matches without baking the number into the repo (no
// commit-back, no drift). If the API is unreachable/rate-limited, the static
// value already in the page is kept.
(function () {
  "use strict";
  var OWNER_REPO = "BastienPasdeloup/MtG-Goldfish-Simulator";
  var BASE = "0.1"; // keep in sync with __version_base__ in src/mtg_goldfish/__init__.py
  fetch("https://api.github.com/repos/" + OWNER_REPO + "/commits?sha=main&per_page=1")
    .then(function (r) {
      // The "Link" header's rel="last" page number == the total commit count.
      var link = r.headers.get("Link") || "";
      var last = link.split(",").filter(function (s) { return /rel="last"/.test(s); })[0];
      var m = last && last.match(/[?&]page=(\d+)/);
      if (!m) return;
      var v = "v" + BASE + "." + m[1];
      document.querySelectorAll(".ver").forEach(function (el) { el.textContent = v; });
    })
    .catch(function () { /* offline / rate-limited — keep the static fallback */ });
})();
