/* =====================================================
   Gas Sensor Analyzer – frontend logic
   ===================================================== */

(function () {
  "use strict";

  // ---- State -------------------------------------------------------
  let uploadedRows = [];
  let activeChart = "response";
  let activeRowIdx = 0;

  // ---- DOM refs ----------------------------------------------------
  const dropZone        = document.getElementById("dropZone");
  const fileInput       = document.getElementById("fileInput");
  const uploadStatus    = document.getElementById("uploadStatus");
  const resultsSection  = document.getElementById("resultsSection");
  const totalRowsEl     = document.getElementById("totalRows");
  const totalMatsEl     = document.getElementById("totalMaterials");
  const totalGasesEl    = document.getElementById("totalGases");
  const metricsHead     = document.getElementById("metricsHead");
  const metricsBody     = document.getElementById("metricsBody");
  const chartContainer  = document.getElementById("chartContainer");
  const chartLoading    = document.getElementById("chartLoading");
  const rowSelector     = document.getElementById("rowSelector");
  const rowSelectorWrap = document.getElementById("rowSelectorWrapper");

  // ---- Drag & drop -------------------------------------------------
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  // ---- Chart tabs --------------------------------------------------
  document.getElementById("chartTabs").addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    activeChart = btn.dataset.chart;
    rowSelectorWrap.style.display = activeChart === "response" ? "flex" : "none";
    loadChart(activeChart);
  });

  rowSelector.addEventListener("change", () => {
    activeRowIdx = parseInt(rowSelector.value, 10);
    loadChart("response");
  });

  // ---- Upload ------------------------------------------------------
  function handleFile(file) {
    setStatus("loading", `正在上传并解析 "${file.name}" …`);
    const fd = new FormData();
    fd.append("file", file);

    fetch("/upload", { method: "POST", body: fd })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setStatus("error", "❌ " + data.error);
          return;
        }
        uploadedRows = data.rows;
        setStatus("success", `✅ 成功解析 ${data.count} 条测量记录`);
        renderResults();
      })
      .catch((err) => setStatus("error", "❌ 网络错误: " + err.message));
  }

  function setStatus(type, msg) {
    uploadStatus.className = "upload-status " + type;
    uploadStatus.textContent = msg;
    uploadStatus.classList.remove("hidden");
  }

  // ---- Render results table ----------------------------------------
  function renderResults() {
    if (!uploadedRows.length) return;

    // Summary
    const materials = new Set(uploadedRows.map((r) => r.material));
    const gases     = new Set(uploadedRows.map((r) => r.gas));
    totalRowsEl.textContent  = uploadedRows.length;
    totalMatsEl.textContent  = materials.size;
    totalGasesEl.textContent = gases.size;

    // Table headers
    const scalarCols = ["#", "材料", "气体", "浓度(ppm)", "温度(°C)", "湿度(%)"];
    const metricCols = uploadedRows[0].metrics ? Object.keys(uploadedRows[0].metrics) : [];
    const allCols    = scalarCols.concat(metricCols);

    metricsHead.innerHTML = `<tr>${allCols.map((c) => `<th>${c}</th>`).join("")}</tr>`;

    metricsBody.innerHTML = uploadedRows
      .map((row, i) => {
        const scalars = [
          i + 1,
          row.material ?? "-",
          row.gas ?? "-",
          row.concentration ?? "-",
          row.temperature ?? "-",
          row.humidity ?? "-",
        ];
        const metrics = metricCols.map((k) => {
          const v = row.metrics[k];
          return v !== null && v !== undefined ? v : '<span class="null-val">—</span>';
        });
        return `<tr>${[...scalars, ...metrics].map((v) => `<td>${v}</td>`).join("")}</tr>`;
      })
      .join("");

    // Row selector for response curve
    rowSelector.innerHTML = uploadedRows
      .map((r, i) => `<option value="${i}">${i + 1}. ${r.material ?? ""} – ${r.gas ?? ""} ${r.concentration ?? ""}ppm</option>`)
      .join("");
    activeRowIdx = 0;

    resultsSection.classList.remove("hidden");

    // Load default chart
    rowSelectorWrap.style.display = "flex";
    loadChart("response");
  }

  // ---- Chart loading -----------------------------------------------
  window.loadChart = function (chartType) {
    if (!uploadedRows.length) return;
    chartLoading.classList.remove("hidden");

    let url = `/chart/${chartType}`;
    if (chartType === "response") url += `?row=${activeRowIdx}`;

    fetch(url)
      .then((r) => r.json())
      .then((fig) => {
        chartLoading.classList.add("hidden");
        Plotly.react(chartContainer, fig.data, fig.layout, {
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ["sendDataToCloud"],
        });
      })
      .catch((err) => {
        chartLoading.classList.add("hidden");
        chartContainer.innerHTML = `<div class="chart-placeholder">图表加载失败: ${err.message}</div>`;
      });
  };

  // ---- Exports -----------------------------------------------------
  window.exportCSV = function () {
    fetch("/export/csv", { method: "POST" })
      .then((r) => r.blob())
      .then((blob) => triggerDownload(blob, "gas_sensor_metrics.csv"));
  };

  window.exportReport = function () {
    fetch("/export/report", { method: "POST" })
      .then((r) => r.blob())
      .then((blob) => triggerDownload(blob, "gas_sensor_report.txt"));
  };

  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a   = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a);
    try {
      a.click();
    } finally {
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 100);
    }
  }
})();
