// Табы выдачи, окно заказа, выбор языка. Без зависимостей и без внешних запросов.
(function () {
  "use strict";

  // ------------------------------------------------------------- табы выдачи
  var tabs = document.querySelectorAll(".vt a[data-tab]");
  var hits = document.querySelectorAll(".hit[data-kind]");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function (event) {
      event.preventDefault();
      var kind = tab.dataset.tab;
      tabs.forEach(function (other) { other.classList.toggle("on", other === tab); });
      hits.forEach(function (hit) {
        hit.style.display = kind === "all" || hit.dataset.kind === kind ? "" : "none";
      });
    });
  });

  // ------------------------------------------------------------ окно заказа
  var modal = document.getElementById("order");
  if (modal) {
    var openers = document.querySelectorAll('[data-open="order"]');
    var open = function () {
      modal.hidden = false;
      var field = modal.querySelector("input[type=email]");
      if (field) { field.focus(); }
    };
    var close = function () { modal.hidden = true; };
    openers.forEach(function (el) {
      el.addEventListener("click", open);
      el.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); }
      });
    });
    var closeBtn = modal.querySelector(".close");
    if (closeBtn) { closeBtn.addEventListener("click", close); }
    modal.addEventListener("click", function (event) { if (event.target === modal) { close(); } });
    document.addEventListener("keydown", function (event) { if (event.key === "Escape") { close(); } });
    if (window.location.hash === "#order") { open(); }
  }

  // ------------------------------------------------------- закрыть языковой список
  var langbox = document.querySelector(".langbox");
  if (langbox) {
    document.addEventListener("click", function (event) {
      if (langbox.open && !langbox.contains(event.target)) { langbox.open = false; }
    });
  }

  // ------------------------------------------------- смена языка без потери текста
  // Проверка из плана интерфейса (раздел 8, п. 4): введённый текст не теряется.
  var area = document.querySelector('textarea[name="q"]');
  if (area) {
    document.querySelectorAll("a[data-keep-query]").forEach(function (link) {
      link.addEventListener("click", function () {
        var text = (area.value || "").trim();
        if (!text) { return; }
        try {
          var url = new URL(link.getAttribute("href"), window.location.origin);
          url.searchParams.set("q", text);
          link.setAttribute("href", url.pathname + url.search);
        } catch (error) { /* оставляем ссылку как есть */ }
      });
    });
  }

  // ------------------------------------------------------- печать и «поделиться»
  document.querySelectorAll("[data-print]").forEach(function (button) {
    button.addEventListener("click", function () { window.print(); });
  });
  document.querySelectorAll("[data-share]").forEach(function (button) {
    button.addEventListener("click", function () {
      var title = button.getAttribute("data-share-title") || document.title;
      var url = window.location.href;
      var done = function () {
        var original = button.textContent;
        button.textContent = "✓";
        window.setTimeout(function () { button.textContent = original; }, 1600);
      };
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function () { /* отмена — не ошибка */ });
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(done, done);
      }
    });
  });
})();
