"use strict";
var state = {
  obszar: [], temat: [], radny: [], typ: [], status: [], rok: []
};
var docs = [];
var query = "";

function esc(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

var collator = new Intl.Collator("pl", { numeric: true, sensitivity: "base" });

function uniqValues(key) {
  var out = [];
  docs.forEach(function (d) {
    var value = d[key];
    if (Array.isArray(value)) value.forEach(function (v) { if (v && out.indexOf(v) < 0) out.push(v); });
    else if (value && out.indexOf(value) < 0) out.push(value);
  });
  return out.sort(collator.compare);
}

function fieldValues(doc, key) {
  var value = key === "rok" ? (doc.data || "").slice(0, 4) : doc[key];
  if (Array.isArray(value)) return value;
  return value ? [value] : [];
}

function buildFilters() {
  var groups = document.querySelectorAll(".filter-group");
  Array.prototype.forEach.call(groups, function (group) {
    var key = group.getAttribute("data-filter");
    var values;
    if (key === "rok") {
      var years = {};
      docs.forEach(function (d) {
        var year = (d.data || "").slice(0, 4);
        if (year) years[year] = true;
      });
      values = Object.keys(years).sort().reverse();
    } else {
      values = uniqValues(key);
    }
    var html = '<span class="filter-label">' + esc(group.getAttribute("data-label")) + "</span>";
    values.forEach(function (value) {
      html += '<button type="button" class="chip" data-value="' + esc(value) + '">' + esc(value) + "</button>";
    });
    group.innerHTML = html;
    group.addEventListener("click", function (event) {
      var chip = event.target;
      while (chip && chip !== group && !chip.classList.contains("chip")) chip = chip.parentNode;
      if (!chip || chip === group) return;
      var value = chip.getAttribute("data-value");
      var index = state[key].indexOf(value);
      if (index >= 0) state[key].splice(index, 1);
      else state[key].push(value);
      render();
    });
  });
}

function visible(doc) {
  var keys = Object.keys(state);
  for (var index = 0; index < keys.length; index++) {
    var key = keys[index];
    if (state[key].length === 0) continue;
    var allowed = state[key];
    var values = fieldValues(doc, key);
    var match = values.some(function (value) { return allowed.indexOf(value) >= 0; });
    if (!match) return false;
  }
  if (query) {
    var haystack = [doc.temat, doc.radny, doc.podsumowanie, doc.typ, doc.numer,
      (doc.obszary || []).join(" "), (doc.tematy || []).join(" "),
      (doc.radny || "").toLowerCase()].join(" ").toLowerCase();
    if (haystack.indexOf(query) < 0) return false;
  }
  return true;
}

function render() {
  var filtered = docs.filter(visible);
  var count = document.getElementById("count");
  count.textContent = "Dokumentów: " + filtered.length + " z " + docs.length;

  var list = document.getElementById("list");
  list.innerHTML = filtered.map(function (doc) {
    var label = (doc.typ || "?") + " nr " + (doc.numer || "?");
    var badges = '<span class="badge ' + (doc.status === "udzielono" ? "answered" : "pending") + '">' +
      (doc.status === "udzielono" ? "odpowiedź" : "bez odpowiedzi") + "</span>";
    var chips = (doc.obszary || []).concat(doc.tematy || [])
      .map(function (value) { return '<span class="mini-chip">' + esc(value) + "</span>"; }).join("");
    return '<li class="document-card"><a href="' + esc(doc.pisma_url || doc.pismo_url) + '">' +
      '<div class="card-top"><span class="doc-label">' + esc(label) + '</span>' +
      '<span class="doc-date">' + esc(doc.data || "") + "</span>" + badges + "</div>" +
      '<p class="doc-title">' + esc(doc.temat || "") + "</p>" +
      '<p class="doc-meta">' + esc(doc.radny || "") + "</p>" +
      (chips ? '<div class="chips">' + chips + "</div>" : "") +
      (doc.podsumowanie ? '<p class="doc-mini">' + esc(doc.podsumowanie) + "</p>" : "") +
      "</a></li>";
  }).join("");

  Array.prototype.forEach.call(document.querySelectorAll(".filter-group"), function (group) {
    var key = group.getAttribute("data-filter");
    Array.prototype.forEach.call(group.querySelectorAll(".chip"), function (chip) {
      var active = state[key].indexOf(chip.getAttribute("data-value")) >= 0;
      chip.classList.toggle("active", active);
    });
  });

  var params = new URLSearchParams();
  Object.keys(state).forEach(function (key) {
    state[key].forEach(function (value) { params.append(key, value); });
  });
  if (query) params.append("q", query);
  var suffix = params.toString();
  window.history.replaceState(null, "", suffix ? "?" + suffix : window.location.pathname);
}

function init() {
  fetch("data/index.json").then(function (response) { return response.json(); }).then(function (data) {
    docs = data;
    buildFilters();
    var params = new URLSearchParams(window.location.search);
    Object.keys(state).forEach(function (key) {
      state[key] = params.getAll(key).filter(Boolean);
    });
    var search = document.getElementById("search");
    query = (params.get("q") || "").toLowerCase();
    search.value = params.get("q") || "";
    search.addEventListener("input", function (event) {
      query = event.target.value.trim().toLowerCase();
      render();
    });
    document.getElementById("clear").addEventListener("click", function () {
      Object.keys(state).forEach(function (key) { state[key] = []; });
      query = "";
      search.value = "";
      render();
    });
    render();
  });
}

init();
