function resolveApiBaseUrl() {
  const explicitBase = window.APP_CONFIG?.API_BASE_URL;
  if (typeof explicitBase === "string" && explicitBase.trim() !== "") return explicitBase.trim().replace(/\/+$/, "");
  return ["localhost", "127.0.0.1"].includes(window.location.hostname) ? "http://localhost:8000" : "";
}

const API_BASE_URL = resolveApiBaseUrl();
const API_URLS = {
  provinces: `${API_BASE_URL}/api/provinces`,
  convert: `${API_BASE_URL}/api/convert`,
  ocrCoordinates: `${API_BASE_URL}/api/ocr-coordinates`,
};

const provinceEl = document.getElementById("province");
const value1El = document.getElementById("value1");
const value2El = document.getElementById("value2");
const inputModeEl = document.getElementById("inputMode");
const convertBtnEl = document.getElementById("convertBtn");
const statusTextEl = document.getElementById("statusText");
const resultCardEl = document.getElementById("resultCard");
const qrBoxEl = document.getElementById("qrBox");

const captureBtnEl = document.getElementById("captureBtn");
const pickFileBtnEl = document.getElementById("pickFileBtn");
const ocrImageInputEl = document.getElementById("ocrImageInput");
const ocrImageCaptureInputEl = document.getElementById("ocrImageCaptureInput");
const ocrFileNameTextEl = document.getElementById("ocrFileNameText");
const ocrFastBtnEl = document.getElementById("ocrFastBtn");
const ocrEnhancedBtnEl = document.getElementById("ocrEnhancedBtn");
const ocrEnhancedNoteEl = document.getElementById("ocrEnhancedNote");
const ocrStatusTextEl = document.getElementById("ocrStatusText");
const ocrWarningsEl = document.getElementById("ocrWarnings");
const ocrCandidatesTableWrapEl = document.getElementById("ocrCandidatesTableWrap");
const ocrCandidatesTableBodyEl = document.getElementById("ocrCandidatesTableBody");
const previewSelectedBtnEl = document.getElementById("previewSelectedBtn");
const convertSelectedBtnEl = document.getElementById("convertSelectedBtn");
const ocrBatchPreviewEl = document.getElementById("ocrBatchPreview");
const ocrMetaDetailsEl = document.getElementById("ocrMetaDetails");
const ocrMetaListEl = document.getElementById("ocrMetaList");
const ocrRawDetailsEl = document.getElementById("ocrRawDetails");
const ocrRawTextEl = document.getElementById("ocrRawText");

const multiResultCardEl = document.getElementById("multiResultCard");
const multiResultTableBodyEl = document.getElementById("multiResultTableBody");
const multiResultStatusTextEl = document.getElementById("multiResultStatusText");
const copyAllLatLngBtnEl = document.getElementById("copyAllLatLngBtn");
const downloadCsvBtnEl = document.getElementById("downloadCsvBtn");

const resultLatEl = document.getElementById("resultLat");
const resultLngEl = document.getElementById("resultLng");
const resultOrderEl = document.getElementById("resultOrder");
const resultMapsEl = document.getElementById("resultMaps");
const resultWarningsEl = document.getElementById("resultWarnings");
const resultQrEl = document.getElementById("resultQr");
const downloadQrBtnEl = document.getElementById("downloadQrBtn");
const copyLatLngBtnEl = document.getElementById("copyLatLngBtn");
const copyMapsBtnEl = document.getElementById("copyMapsBtn");
const openMapsBtnEl = document.getElementById("openMapsBtn");

const brandLogoEl = document.getElementById("brandLogo");
const brandFallbackEl = document.getElementById("brandFallback");

const state = { lastLatitude: null, lastLongitude: null, lastMapsUrl: "", multiRows: [] };

brandLogoEl.addEventListener("error", () => {
  brandLogoEl.style.display = "none";
  brandFallbackEl.style.display = "block";
});

function usedOrderToVietnamese(order) {
  if (order === "easting_northing") return "Giá trị 1 là Đông, Giá trị 2 là Bắc";
  if (order === "northing_easting") return "Giá trị 1 là Bắc, Giá trị 2 là Đông";
  return order || "-";
}

function translateWarningText(warning) {
  if (!warning) return "";
  const value = String(warning).trim();
  if (value === "Input order auto-detected as northing/easting (value1/value2 may be swapped).") {
    return "Hệ thống tự nhận diện thứ tự tọa độ là Bắc/Đông. Vui lòng kiểm tra lại giá trị 1 và giá trị 2.";
  }
  return value;
}

function normalizeConfidenceText(text) {
  let value = text || "";
  value = value.replace("detected from same OCR row", "Nhận diện từ cùng dòng OCR");
  value = value.replace("corrected by column context", "Đã hiệu chỉnh theo ngữ cảnh cùng cột");
  value = value.replace("detected from nearby OCR numbers (low confidence)", "Nhận diện từ các số OCR gần nhau (độ tin cậy thấp)");
  return value;
}

function setLoading(isLoading) {
  convertBtnEl.disabled = isLoading;
  convertBtnEl.textContent = isLoading ? "Đang chuyển đổi..." : "Chuyển đổi";
}

function setOcrLoading(isLoading, mode = "fast") {
  ocrFastBtnEl.disabled = isLoading;
  ocrEnhancedBtnEl.disabled = isLoading;
  if (!isLoading) {
    ocrFastBtnEl.textContent = "Đọc nhanh tọa độ";
    ocrEnhancedBtnEl.textContent = "Đọc kỹ tọa độ";
    return;
  }
  if (mode === "enhanced") {
    ocrEnhancedBtnEl.textContent = "Đang đọc kỹ tọa độ, vui lòng chờ...";
  } else {
    ocrFastBtnEl.textContent = "Đang đọc nhanh tọa độ...";
  }
}

function setMultiConvertLoading(isLoading) {
  convertSelectedBtnEl.disabled = isLoading;
  convertSelectedBtnEl.textContent = isLoading ? "Đang chuyển đổi..." : "Chuyển đổi các điểm đã chọn";
}

function setOcrStatus(message, type = "default") {
  ocrStatusTextEl.textContent = message;
  ocrStatusTextEl.classList.remove("success", "error");
  if (type === "success") ocrStatusTextEl.classList.add("success");
  if (type === "error") ocrStatusTextEl.classList.add("error");
}

function isSuspiciousValue(value) {
  if (!Number.isFinite(value)) return true;
  const abs = Math.abs(value);
  return abs < 100000 || abs > 10000000;
}

function renderWarnings(warnings) {
  resultWarningsEl.innerHTML = "";
  if (!warnings || warnings.length === 0) {
    const li = document.createElement("li");
    li.style.color = "#64748B";
    li.textContent = "Không có cảnh báo.";
    resultWarningsEl.appendChild(li);
    return;
  }
  warnings.forEach((warning) => {
    const li = document.createElement("li");
    li.textContent = translateWarningText(warning);
    resultWarningsEl.appendChild(li);
  });
}

function renderOcrWarnings(warnings) {
  ocrWarningsEl.innerHTML = "";
  (warnings || []).forEach((warning) => {
    const li = document.createElement("li");
    li.textContent = warning;
    ocrWarningsEl.appendChild(li);
  });
}

function mapOcrErrorMessage(payload) {
  if (!payload || payload.ok !== false) return null;
  if (payload.stage === "image_open") return "Không đọc được file ảnh. Hãy dùng JPG/PNG rõ nét và thử lại.";
  if (payload.error_code === "TESSERACT_UNAVAILABLE" || payload.stage === "tesseract_run") return "Chưa cấu hình được Tesseract OCR. Kiểm tra TESSERACT_CMD/PATH.";
  return payload.message || "OCR thất bại.";
}

function setSelectedFile(file) {
  ocrFileNameTextEl.textContent = file ? `Ảnh đã chọn: ${file.name}` : "Chưa chọn ảnh.";
}

function readRowValue(input) {
  const value = Number(input.value);
  return Number.isFinite(value) ? value : NaN;
}

function getSelectedOcrCandidates() {
  const checked = Array.from(document.querySelectorAll(".ocr-select:checked"));
  const selected = [];
  checked.forEach((checkbox) => {
    const row = checkbox.closest("tr");
    if (!row) return;
    const v1Input = row.querySelector(".ocr-value1-input");
    const v2Input = row.querySelector(".ocr-value2-input");
    const label = checkbox.dataset.label || "-";
    const value1 = readRowValue(v1Input);
    const value2 = readRowValue(v2Input);
    if (Number.isFinite(value1) && Number.isFinite(value2)) selected.push({ point_label: label, value1, value2 });
  });
  const uniq = new Map();
  selected.forEach((item) => {
    const key = `${item.point_label}|${item.value1}|${item.value2}`;
    if (!uniq.has(key)) uniq.set(key, item);
  });
  return Array.from(uniq.values());
}

async function copyText(text, successMessage) {
  if (!text) return void (statusTextEl.textContent = "Không có dữ liệu để sao chép.");
  try {
    await navigator.clipboard.writeText(text);
    statusTextEl.textContent = successMessage;
  } catch (_err) {
    statusTextEl.textContent = "Không sao chép được. Trình duyệt có thể đang chặn clipboard.";
  }
}

function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function updateValueInputStyle(input) {
  const value = Number(input.value);
  input.classList.toggle("value-suspicious", isSuspiciousValue(value));
}

function buildOcrMetaDetails(payload) {
  ocrMetaListEl.innerHTML = "";
  const addItem = (text) => {
    const li = document.createElement("li");
    li.textContent = text;
    ocrMetaListEl.appendChild(li);
  };
  addItem(`Chế độ OCR: ${payload.ocr_mode || "-"}`);
  addItem(`Thời gian xử lý: ${payload.elapsed_seconds ?? "-"} giây`);
  addItem(`Số cặp tọa độ nhận diện: ${payload.candidate_count ?? 0}`);
  if (payload.preprocessing_method) addItem(`Phương pháp tiền xử lý: ${payload.preprocessing_method}`);
  if (payload.ocr_config) addItem(`Cấu hình OCR: ${payload.ocr_config}`);
  if (payload.ocr_language) addItem(`Ngôn ngữ OCR: ${payload.ocr_language}`);
  (payload.warnings || []).forEach((w) => addItem(`Cảnh báo: ${translateWarningText(w)}`));
  (payload.candidates || []).forEach((item) => {
    const confidence = normalizeConfidenceText(item.confidence_note || "");
    if (confidence) addItem(`Điểm ${item.point_label}: ${confidence}`);
    (item.corrections || []).forEach((corr) => addItem(`Điểm ${item.point_label} - Hiệu chỉnh: ${corr}`));
  });
  if (ocrMetaListEl.children.length > 0) ocrMetaDetailsEl.classList.remove("hidden");
  else ocrMetaDetailsEl.classList.add("hidden");
}

function renderOcrCandidates(candidates) {
  ocrCandidatesTableBodyEl.innerHTML = "";
  ocrBatchPreviewEl.innerHTML = "";
  multiResultCardEl.classList.add("hidden");
  state.multiRows = [];
  if (!candidates || candidates.length === 0) {
    ocrCandidatesTableWrapEl.classList.add("hidden");
    return;
  }
  const hasRowBased = candidates.some((c) => !String(c.confidence_note || "").toLowerCase().includes("nearby ocr numbers"));
  const list = hasRowBased ? candidates.filter((c) => !String(c.confidence_note || "").toLowerCase().includes("nearby ocr numbers")) : candidates;
  if (list.length === 0) return void ocrCandidatesTableWrapEl.classList.add("hidden");
  ocrCandidatesTableWrapEl.classList.remove("hidden");

  list.forEach((item) => {
    const tr = document.createElement("tr");
    const tdSelect = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "ocr-select";
    checkbox.dataset.label = item.point_label || "";
    tdSelect.appendChild(checkbox);
    const tdLabel = document.createElement("td");
    tdLabel.textContent = item.point_label || "-";
    const tdV1 = document.createElement("td");
    const inputV1 = document.createElement("input");
    inputV1.type = "number";
    inputV1.step = "any";
    inputV1.value = String(item.value1);
    inputV1.className = "ocr-value-input ocr-value1-input";
    inputV1.addEventListener("input", () => updateValueInputStyle(inputV1));
    updateValueInputStyle(inputV1);
    tdV1.appendChild(inputV1);
    const tdV2 = document.createElement("td");
    const inputV2 = document.createElement("input");
    inputV2.type = "number";
    inputV2.step = "any";
    inputV2.value = String(item.value2);
    inputV2.className = "ocr-value-input ocr-value2-input";
    inputV2.addEventListener("input", () => updateValueInputStyle(inputV2));
    updateValueInputStyle(inputV2);
    tdV2.appendChild(inputV2);
    const tdAction = document.createElement("td");
    const btn = document.createElement("button");
    btn.className = "secondary-btn";
    btn.type = "button";
    btn.textContent = "Dùng";
    btn.addEventListener("click", () => {
      const value1 = readRowValue(inputV1);
      const value2 = readRowValue(inputV2);
      if (!Number.isFinite(value1) || !Number.isFinite(value2)) return void (statusTextEl.textContent = "Giá trị OCR không hợp lệ. Vui lòng chỉnh lại trước khi dùng.");
      value1El.value = String(value1);
      value2El.value = String(value2);
      statusTextEl.textContent = "Đã điền tọa độ từ OCR. Vui lòng kiểm tra và bấm Chuyển đổi.";
    });
    tdAction.appendChild(btn);
    tr.append(tdSelect, tdLabel, tdV1, tdV2, tdAction);
    ocrCandidatesTableBodyEl.appendChild(tr);
  });
}

function previewSelectedCandidates() {
  ocrBatchPreviewEl.innerHTML = "";
  const list = getSelectedOcrCandidates();
  if (list.length === 0) {
    const li = document.createElement("li");
    li.textContent = "Chưa chọn cặp nào để xem trước.";
    ocrBatchPreviewEl.appendChild(li);
    return;
  }
  list.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `Điểm ${item.point_label}: ${item.value1} | ${item.value2}`;
    ocrBatchPreviewEl.appendChild(li);
  });
}

function renderMultiResultTable(rows) {
  multiResultTableBodyEl.innerHTML = "";
  const warningLines = [];
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    const cells = [document.createElement("td"), document.createElement("td"), document.createElement("td"), document.createElement("td"), document.createElement("td"), document.createElement("td")];
    cells[0].textContent = row.point_label || "-";
    cells[1].textContent = String(row.value1);
    cells[2].textContent = String(row.value2);
    if (row.ok) {
      cells[3].textContent = Number(row.latitude).toFixed(12);
      cells[4].textContent = Number(row.longitude).toFixed(12);
      const link = document.createElement("a");
      link.href = row.google_maps_url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Mở";
      cells[5].appendChild(link);
    } else {
      cells[3].textContent = "-";
      cells[4].textContent = "-";
      cells[5].textContent = "Lỗi";
      tr.classList.add("multi-row-error");
      warningLines.push(`Điểm ${row.point_label}: ${row.error_message}`);
    }
    tr.append(...cells);
    multiResultTableBodyEl.appendChild(tr);
  });
  multiResultStatusTextEl.textContent = warningLines.length > 0 ? `Có ${warningLines.length} điểm chuyển đổi thất bại. ${warningLines.join(" | ")}` : "Đã chuyển đổi thành công các điểm đã chọn.";
}

async function loadProvinces() {
  provinceEl.innerHTML = '<option value="">Đang tải danh sách tỉnh/thành...</option>';
  try {
    const resp = await fetch(API_URLS.provinces);
    if (!resp.ok) throw new Error();
    const data = await resp.json();
    provinceEl.innerHTML = '<option value="">Chọn tỉnh/thành phố</option>';
    (data.provinces || []).forEach((province) => {
      const opt = document.createElement("option");
      opt.value = province;
      opt.textContent = province;
      provinceEl.appendChild(opt);
    });
    const variants = ["TP.Hồ Chí Minh", "TP Hồ Chí Minh", "Thành phố Hồ Chí Minh", "TP.HCM"];
    const options = Array.from(provinceEl.options).map((o) => o.value.trim());
    const found = variants.find((v) => options.includes(v));
    if (found) provinceEl.value = found;
  } catch {
    provinceEl.innerHTML = '<option value="">Không tải được danh sách tỉnh/thành</option>';
    statusTextEl.textContent = `Không kết nối được backend (${API_BASE_URL || "same-origin"}).`;
  }
}

async function runOcr(mode) {
  const file = (ocrImageInputEl.files && ocrImageInputEl.files[0]) || (ocrImageCaptureInputEl.files && ocrImageCaptureInputEl.files[0]);
  if (!file) return void setOcrStatus("Vui lòng chọn ảnh trước khi OCR.", "error");

  setOcrStatus("");
  renderOcrWarnings([]);
  ocrCandidatesTableBodyEl.innerHTML = "";
  ocrBatchPreviewEl.innerHTML = "";
  ocrMetaListEl.innerHTML = "";
  ocrCandidatesTableWrapEl.classList.add("hidden");
  ocrMetaDetailsEl.classList.add("hidden");
  ocrRawDetailsEl.classList.add("hidden");
  multiResultCardEl.classList.add("hidden");
  ocrEnhancedNoteEl.classList.toggle("hidden", mode !== "enhanced");
  setOcrLoading(true, mode);

  try {
    const form = new FormData();
    form.append("image", file);
    const url = `${API_URLS.ocrCoordinates}?mode=${encodeURIComponent(mode)}`;
    console.log("[OCR] API_BASE_URL =", API_BASE_URL);
    console.log("[OCR] OCR upload URL =", url);
    console.log("[OCR] file =", { name: file.name, size: file.size, type: file.type });

    const resp = await fetch(url, { method: "POST", body: form });
    const rawBody = await resp.text();
    let data = {};
    try {
      data = rawBody ? JSON.parse(rawBody) : {};
    } catch (_err) {
      data = { message: rawBody || "Empty response body." };
    }
    if (!resp.ok || data?.ok === false) {
      const friendly = mapOcrErrorMessage(data);
      const stage = data?.stage ? ` [giai đoạn: ${data.stage}]` : "";
      const suggestion = data?.suggestion ? ` Gợi ý: ${data.suggestion}` : "";
      const bodyMessage = data?.message || data?.detail || rawBody || "Yêu cầu OCR thất bại.";
      setOcrStatus(`${friendly}${stage}. HTTP ${resp.status}.${suggestion}`.trim(), "error");
      renderOcrWarnings([`HTTP ${resp.status}: ${bodyMessage}`]);
      return;
    }

    setOcrStatus("OCR hoàn tất. Hãy xác minh kết quả trước khi dùng.", "success");
    renderOcrWarnings((data.warnings || []).map((w) => translateWarningText(w)));
    renderOcrCandidates(data.candidates || []);
    buildOcrMetaDetails(data);
    ocrRawTextEl.textContent = data.raw_text || "";
    ocrRawDetailsEl.classList.remove("hidden");
  } catch (err) {
    setOcrStatus(`Không kết nối được API OCR. URL: ${API_URLS.ocrCoordinates}`, "error");
    renderOcrWarnings([err?.message || "Network error"]);
  } finally {
    setOcrLoading(false);
  }
}

async function convertCoordinates() {
  const province = provinceEl.value.trim();
  const value1 = Number(value1El.value);
  const value2 = Number(value2El.value);
  const inputMode = inputModeEl.value;
  if (!province) return void (statusTextEl.textContent = "Vui lòng chọn tỉnh/thành phố.");
  if (!Number.isFinite(value1) || !Number.isFinite(value2)) return void (statusTextEl.textContent = "Vui lòng nhập đầy đủ 2 giá trị tọa độ hợp lệ.");
  setLoading(true);
  statusTextEl.textContent = "";
  try {
    const resp = await fetch(API_URLS.convert, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ province, value1, value2, input_mode: inputMode, current_lat: null, current_lng: null }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data?.detail || "Chuyển đổi thất bại.");
    state.lastLatitude = Number(data.latitude);
    state.lastLongitude = Number(data.longitude);
    state.lastMapsUrl = data.google_maps_url || "";
    resultLatEl.textContent = state.lastLatitude.toFixed(12);
    resultLngEl.textContent = state.lastLongitude.toFixed(12);
    resultOrderEl.textContent = usedOrderToVietnamese(data.used_order);
    resultMapsEl.href = state.lastMapsUrl || "#";
    resultMapsEl.textContent = state.lastMapsUrl || "-";
    if (data.qr_png_base64) {
      resultQrEl.src = `data:image/png;base64,${data.qr_png_base64}`;
      qrBoxEl.classList.remove("hidden");
    } else {
      qrBoxEl.classList.add("hidden");
    }
    renderWarnings(data.warnings || []);
    resultCardEl.classList.remove("hidden");
    resultCardEl.scrollIntoView({ behavior: "smooth", block: "start" });
    statusTextEl.textContent = "Chuyển đổi thành công.";
  } catch (err) {
    statusTextEl.textContent = `Lỗi: ${err.message}`;
  } finally {
    setLoading(false);
  }
}

async function convertSelectedCandidates() {
  const province = provinceEl.value.trim();
  if (!province) return void (statusTextEl.textContent = "Vui lòng chọn tỉnh/thành phố trước khi chuyển đổi nhiều điểm.");
  const selected = getSelectedOcrCandidates();
  if (selected.length === 0) {
    multiResultStatusTextEl.textContent = "Vui lòng chọn ít nhất 1 điểm OCR hợp lệ.";
    multiResultCardEl.classList.remove("hidden");
    return;
  }
  setMultiConvertLoading(true);
  multiResultStatusTextEl.textContent = "";
  try {
    const rows = await Promise.all(selected.map(async (item) => {
      try {
        const resp = await fetch(API_URLS.convert, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ province, value1: item.value1, value2: item.value2, input_mode: "auto", current_lat: null, current_lng: null }),
        });
        const data = await resp.json();
        if (!resp.ok) return { ...item, ok: false, error_message: data?.detail || "Chuyển đổi thất bại." };
        return { ...item, ok: true, latitude: Number(data.latitude), longitude: Number(data.longitude), google_maps_url: data.google_maps_url || `https://www.google.com/maps?q=${data.latitude},${data.longitude}` };
      } catch (err) {
        return { ...item, ok: false, error_message: err.message || "Lỗi kết nối." };
      }
    }));
    state.multiRows = rows;
    renderMultiResultTable(rows);
    multiResultCardEl.classList.remove("hidden");
    multiResultCardEl.scrollIntoView({ behavior: "smooth", block: "start" });
  } finally {
    setMultiConvertLoading(false);
  }
}

captureBtnEl.addEventListener("click", () => ocrImageCaptureInputEl.click());
pickFileBtnEl.addEventListener("click", () => ocrImageInputEl.click());
ocrImageCaptureInputEl.addEventListener("change", () => setSelectedFile(ocrImageCaptureInputEl.files?.[0] || null));
ocrImageInputEl.addEventListener("change", () => setSelectedFile(ocrImageInputEl.files?.[0] || null));
convertBtnEl.addEventListener("click", convertCoordinates);
ocrFastBtnEl.addEventListener("click", () => runOcr("fast"));
ocrEnhancedBtnEl.addEventListener("click", () => runOcr("enhanced"));
previewSelectedBtnEl.addEventListener("click", previewSelectedCandidates);
convertSelectedBtnEl.addEventListener("click", convertSelectedCandidates);

copyLatLngBtnEl.addEventListener("click", async () => {
  if (state.lastLatitude == null || state.lastLongitude == null) return void (statusTextEl.textContent = "Chưa có kết quả để sao chép Lat/Long.");
  await copyText(`${state.lastLatitude},${state.lastLongitude}`, "Đã sao chép Lat/Long.");
});
copyMapsBtnEl.addEventListener("click", async () => {
  if (!state.lastMapsUrl) return void (statusTextEl.textContent = "Chưa có link Google Maps để sao chép.");
  await copyText(state.lastMapsUrl, "Đã sao chép link Google Maps.");
});
openMapsBtnEl.addEventListener("click", () => {
  if (!state.lastMapsUrl) return void (statusTextEl.textContent = "Chưa có link Google Maps để mở.");
  window.open(state.lastMapsUrl, "_blank", "noopener");
});
downloadQrBtnEl.addEventListener("click", () => {
  const src = resultQrEl.getAttribute("src") || "";
  if (!src.startsWith("data:image/png;base64,")) return void (statusTextEl.textContent = "Chưa có ảnh QR để tải.");
  const link = document.createElement("a");
  link.href = src;
  link.download = "vietinbank-vn2000-google-maps-qr.png";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});
copyAllLatLngBtnEl.addEventListener("click", async () => {
  const rows = state.multiRows.filter((r) => r.ok);
  if (rows.length === 0) return void (multiResultStatusTextEl.textContent = "Chưa có dòng thành công để sao chép.");
  await copyText(rows.map((r) => `${r.point_label},${r.latitude},${r.longitude}`).join("\n"), "Đã sao chép tất cả Lat/Long.");
});
downloadCsvBtnEl.addEventListener("click", () => {
  const rows = state.multiRows.filter((r) => r.ok);
  if (rows.length === 0) return void (multiResultStatusTextEl.textContent = "Chưa có dòng thành công để tải CSV.");
  const header = "point_label,value1,value2,latitude,longitude,google_maps_url";
  const body = rows.map((r) => `"${String(r.point_label).replaceAll('"', '""')}",${r.value1},${r.value2},${r.latitude},${r.longitude},"${String(r.google_maps_url).replaceAll('"', '""')}"`);
  downloadTextFile("vietinbank-vn2000-multi-convert.csv", [header, ...body].join("\n"), "text/csv;charset=utf-8;");
});

loadProvinces();
