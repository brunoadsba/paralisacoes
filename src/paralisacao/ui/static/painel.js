(function () {
  var desde = 0;
  var logEl = document.getElementById("log");

  function tick() {
    fetch("/api/status?desde=" + desde)
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.log || []).forEach(function (item) {
          var div = document.createElement("div");
          div.textContent = item.t;
          logEl.appendChild(div);
        });
        desde = d.log_total || desde;
        var bar = document.getElementById("bar");
        bar.style.width = (d.pct || 0) + "%";
        document.getElementById("phaseTxt").textContent = d.phase || "";
        var tb = document.getElementById("tbLinhas");
        if (d.linhas_html) tb.innerHTML = d.linhas_html;
        var lote = document.querySelector('button[value="lote"]');
        if (lote) lote.disabled = !d.lote_liberado;
        if (d.running) setTimeout(tick, 1000);
      })
      .catch(function () { setTimeout(tick, 2000); });
  }

  tick();
})();
