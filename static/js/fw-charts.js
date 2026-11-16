/* Small Chart.js helper shared by the data pages. Requires Chart.js to be loaded first. */
(function () {
  var css = getComputedStyle(document.documentElement);
  function color(name) { return css.getPropertyValue(name).trim(); }

  /**
   * fwLineChart(canvas, labels, datasets, opts)
   *   datasets: [{label, data, ...chartjsOverrides}]
   *   opts: {fill: bool, axes: bool, decimals: int}
   */
  window.fwLineChart = function (canvas, labels, datasets, opts) {
    opts = opts || {};
    var palette = [color("--primary"), color("--accent"), "#f59e0b", "#8b5cf6"];
    return new Chart(canvas, {
      type: "line",
      data: {
        labels: labels,
        datasets: datasets.map(function (d, i) {
          return Object.assign({
            borderColor: palette[i % palette.length],
            backgroundColor: "rgba(31, 94, 255, 0.08)",
            fill: !!opts.fill && i === 0,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.25
          }, d);
        })
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: datasets.length > 1, labels: { usePointStyle: true, boxWidth: 8 } },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var d = opts.decimals === undefined ? 2 : opts.decimals;
                return " " + ctx.dataset.label + ": " + Number(ctx.parsed.y).toLocaleString("en-US", {
                  minimumFractionDigits: d, maximumFractionDigits: d
                });
              }
            }
          }
        },
        scales: {
          x: {
            display: opts.axes !== false,
            grid: { display: false },
            ticks: { maxTicksLimit: 7, color: color("--muted") }
          },
          y: {
            display: opts.axes !== false,
            grid: { color: color("--line") },
            ticks: { color: color("--muted") }
          }
        }
      }
    });
  };
})();
