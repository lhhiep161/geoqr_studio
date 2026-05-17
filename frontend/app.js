function resolveApiBaseUrl() {
  const explicitBase = window.APP_CONFIG?.API_BASE_URL;
  if (typeof explicitBase === "string" && explicitBase.trim() !== "") return explicitBase.trim().replace(/\/+$/, "");

  const { protocol, hostname, port } = window.location;
  const isCapacitorNative = Boolean(window.Capacitor?.isNativePlatform?.() || window.Capacitor);
  const mobileBase = window.APP_CONFIG?.MOBILE_API_BASE_URL;

  // On native WebView (Capacitor), never fall back to localhost:8000.
  // Prefer explicit mobile API base URL to avoid province list load failures.
  if (isCapacitorNative && typeof mobileBase === "string" && mobileBase.trim() !== "") {
    return mobileBase.trim().replace(/\/+$/, "");
  }

  // If frontend is served on a non-8000 port (e.g. :5500), target backend on :8000
  // using the same host so both desktop LAN and mobile LAN work without manual config.
  if (port && port !== "8000") return `${protocol}//${hostname}:8000`;

  // Localhost dev convenience when port is omitted/rewritten.
  if (["localhost", "127.0.0.1"].includes(hostname)) return "http://localhost:8000";

  // Same-origin fallback for production/reverse proxy where /api is served together.
  return "";
}

const API_BASE_URL = resolveApiBaseUrl();
const API_URLS = {
  provinces: `${API_BASE_URL}/api/provinces`,
  convert: `${API_BASE_URL}/api/convert`,
  ocrCoordinates: `${API_BASE_URL}/api/ocr-coordinates`,
  googleMapsQr: `${API_BASE_URL}/api/google-maps-qr`,
};
const MOBILE_API_BASE_URL = (window.APP_CONFIG?.MOBILE_API_BASE_URL || "").trim().replace(/\/+$/, "");

function applyApiBaseUrl(nextBase) {
  const normalized = (nextBase || "").trim().replace(/\/+$/, "");
  API_URLS.provinces = `${normalized}/api/provinces`;
  API_URLS.convert = `${normalized}/api/convert`;
  API_URLS.ocrCoordinates = `${normalized}/api/ocr-coordinates`;
  API_URLS.googleMapsQr = `${normalized}/api/google-maps-qr`;
}

const provinceEl = document.getElementById("province");
const value1El = document.getElementById("value1");
const value2El = document.getElementById("value2");
const inputModeEl = document.getElementById("inputMode");
const provinceStatusTextEl = document.getElementById("provinceStatusText");
const ocrProvinceStatusTextEl = document.getElementById("ocrProvinceStatusText");
const retryProvinceBtnEl = document.getElementById("retryProvinceBtn");
const retryOcrProvinceBtnEl = document.getElementById("retryOcrProvinceBtn");
const convertBtnEl = document.getElementById("convertBtn");
const statusTextEl = document.getElementById("statusText");
const resultCardEl = document.getElementById("resultCard");
const qrBoxEl = document.getElementById("qrBox");
const featureCardEls = Array.from(document.querySelectorAll(".feature-card"));
const toolPanelEls = Array.from(document.querySelectorAll(".tool-panel"));

const captureBtnEl = document.getElementById("captureBtn");
const pickFileBtnEl = document.getElementById("pickFileBtn");
const ocrProvinceEl = document.getElementById("ocrProvince");
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
const multiResultStatusTextEl = document.getElementById("multiResultStatusText");
const ocrResultRawEl = document.getElementById("ocrResultRaw");
const ocrResultProvinceEl = document.getElementById("ocrResultProvince");
const ocrResultLatEl = document.getElementById("ocrResultLat");
const ocrResultLngEl = document.getElementById("ocrResultLng");
const ocrResultMapsEl = document.getElementById("ocrResultMaps");
const ocrResultQrEl = document.getElementById("ocrResultQr");
const ocrQrBoxEl = document.getElementById("ocrQrBox");
const copyAllLatLngBtnEl = document.getElementById("copyAllLatLngBtn");
const downloadCsvBtnEl = document.getElementById("downloadCsvBtn");

const mapsQrInputEl = document.getElementById("mapsQrInput");
const mapsQrBtnEl = document.getElementById("mapsQrBtn");
const mapsQrStatusTextEl = document.getElementById("mapsQrStatusText");
const mapsQrResultCardEl = document.getElementById("mapsQrResultCard");
const mapsQrSourceEl = document.getElementById("mapsQrSource");
const mapsQrLatEl = document.getElementById("mapsQrLat");
const mapsQrLngEl = document.getElementById("mapsQrLng");
const mapsQrLinkEl = document.getElementById("mapsQrLink");
const mapsQrOpenBtnEl = document.getElementById("mapsQrOpenBtn");
const mapsQrCopyBtnEl = document.getElementById("mapsQrCopyBtn");
const mapsQrDownloadBtnEl = document.getElementById("mapsQrDownloadBtn");
const mapsQrImageBoxEl = document.getElementById("mapsQrImageBox");
const mapsQrImageEl = document.getElementById("mapsQrImage");
const mapsQrWarningsEl = document.getElementById("mapsQrWarnings");
const mapsQrResolvedDetailsEl = document.getElementById("mapsQrResolvedDetails");
const mapsQrResolvedTextEl = document.getElementById("mapsQrResolvedText");

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

const state = { lastLatitude: null, lastLongitude: null, lastMapsUrl: "", activeFeature: "convert", ocrSingle: null };
const mapsQrState = { link: "", qrDataUrl: "" };

function toVietnameseCoordinateSource(source) {
  if (source === "plus_code") return "Plus Code";
  if (source === "google_place_data") return "Link Google Maps (điểm địa điểm)";
  if (source === "query_param") return "Link Google Maps (tham số truy vấn)";
  if (source === "viewport_center_fallback") return "Tâm màn hình (fallback)";
  if (source === "plain_text") return "Lat/Long nhập trực tiếp";
  return source || "-";
}

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

function setMapsQrLoading(isLoading) {
  mapsQrBtnEl.disabled = isLoading;
  mapsQrBtnEl.textContent = isLoading ? "Đang tạo QR..." : "Tạo QR Google Maps";
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
  convertSelectedBtnEl.textContent = isLoading ? "Đang chuyển đổi..." : "Tạo Google Maps và QR cho tọa độ đã chọn";
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

function setActiveFeature(feature) {
  state.activeFeature = feature;
  featureCardEls.forEach((card) => card.classList.toggle("feature-card-active", card.dataset.feature === feature));
  toolPanelEls.forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === feature));
}

function readRowValue(input) {
  const value = Number(input.value);
  return Number.isFinite(value) ? value : NaN;
}

function getSelectedOcrCandidate() {
  const picked = document.querySelector(".ocr-select:checked");
  if (!picked) return null;
  const row = picked.closest("tr");
  if (!row) return null;
  const v1Input = row.querySelector(".ocr-value1-input");
  const v2Input = row.querySelector(".ocr-value2-input");
  const label = picked.dataset.label || "-";
  const value1 = readRowValue(v1Input);
  const value2 = readRowValue(v2Input);
  if (!Number.isFinite(value1) || !Number.isFinite(value2)) return null;
  return { point_label: label, value1, value2 };
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
  state.ocrSingle = null;
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
    checkbox.type = "radio";
    checkbox.name = "ocr-candidate";
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
  const selected = getSelectedOcrCandidate();
  if (!selected) {
    const li = document.createElement("li");
    li.textContent = "Chưa chọn cặp nào để xem trước.";
    ocrBatchPreviewEl.appendChild(li);
    return;
  }
  const li = document.createElement("li");
  li.textContent = `Điểm ${selected.point_label}: ${selected.value1} | ${selected.value2}`;
  ocrBatchPreviewEl.appendChild(li);
}

async function loadProvinces() {
  const setProvinceStatus = (message = "", type = "muted", showRetry = false) => {
    [provinceStatusTextEl, ocrProvinceStatusTextEl].forEach((el) => {
      if (!el) return;
      el.textContent = message;
      el.classList.remove("error", "success");
      if (type === "error") el.classList.add("error");
      if (type === "success") el.classList.add("success");
    });
    [retryProvinceBtnEl, retryOcrProvinceBtnEl].forEach((btn) => {
      if (!btn) return;
      btn.classList.toggle("hidden", !showRetry);
      btn.disabled = false;
    });
  };

  provinceEl.disabled = true;
  ocrProvinceEl.disabled = true;
  provinceEl.innerHTML = '<option value="">Đang tải danh sách tỉnh/thành...</option>';
  ocrProvinceEl.innerHTML = '<option value="">Đang tải danh sách tỉnh/thành...</option>';
  setProvinceStatus("Đang tải danh sách tỉnh/thành...", "muted", false);
  try {
    const candidateUrls = [API_URLS.provinces];
    const prodUrl = MOBILE_API_BASE_URL ? `${MOBILE_API_BASE_URL}/api/provinces` : "";
    if (prodUrl && !candidateUrls.includes(prodUrl)) candidateUrls.push(prodUrl);

    let resp = null;
    let bodyText = "";
    let chosenUrl = "";
    let lastError = null;
    for (const url of candidateUrls) {
      try {
        const currentResp = await fetch(url);
        const currentBody = await currentResp.text();
        if (!currentResp.ok) {
          console.error("[GeoQR] Load provinces failed", {
            url,
            status: currentResp.status,
            body: currentBody?.slice(0, 400),
          });
          lastError = new Error(`HTTP_${currentResp.status}`);
          continue;
        }
        resp = currentResp;
        bodyText = currentBody;
        chosenUrl = url;
        break;
      } catch (err) {
        lastError = err;
        console.error("[GeoQR] Load provinces fetch exception", {
          url,
          error: err?.message || String(err),
        });
      }
    }

    if (!resp || !chosenUrl) throw lastError || new Error("ALL_PROVINCE_ENDPOINTS_FAILED");

    // If fallback endpoint is selected, switch all API calls to this base.
    if (MOBILE_API_BASE_URL && chosenUrl.startsWith(`${MOBILE_API_BASE_URL}/api/`)) {
      applyApiBaseUrl(MOBILE_API_BASE_URL);
      console.info("[GeoQR] Switched API base URL to production fallback:", MOBILE_API_BASE_URL);
    }

    let data = {};
    try {
      data = bodyText ? JSON.parse(bodyText) : {};
    } catch (_err) {
      console.error("[GeoQR] Provinces response is not valid JSON", {
        url: API_URLS.provinces,
        body: bodyText?.slice(0, 400),
      });
      throw new Error("INVALID_JSON");
    }
    const provinceList = Array.isArray(data?.provinces) ? data.provinces : Array.isArray(data) ? data : [];
    if (provinceList.length === 0) throw new Error("EMPTY_PROVINCE_LIST");
    provinceEl.innerHTML = '<option value="">Chọn tỉnh/thành phố</option>';
    ocrProvinceEl.innerHTML = '<option value="">Chọn tỉnh/thành phố</option>';
    provinceList.forEach((province) => {
      const opt1 = document.createElement("option");
      opt1.value = province;
      opt1.textContent = province;
      provinceEl.appendChild(opt1);
      const opt2 = document.createElement("option");
      opt2.value = province;
      opt2.textContent = province;
      ocrProvinceEl.appendChild(opt2);
    });
    const variants = ["TP.Hồ Chí Minh", "TP Hồ Chí Minh", "Thành phố Hồ Chí Minh", "TP.HCM"];
    const options = Array.from(provinceEl.options).map((o) => o.value.trim());
    const found = variants.find((v) => options.includes(v));
    if (found) {
      provinceEl.value = found;
      ocrProvinceEl.value = found;
    }
    provinceEl.disabled = false;
    ocrProvinceEl.disabled = false;
    setProvinceStatus("Đã tải danh sách tỉnh/thành.", "success", false);
  } catch (err) {
    console.error("[GeoQR] Cannot load provinces", {
      url: API_URLS.provinces,
      apiBaseUrl: API_BASE_URL || "same-origin",
      error: err?.message || String(err),
    });
    provinceEl.innerHTML = '<option value="">Chưa có dữ liệu tỉnh/thành</option>';
    ocrProvinceEl.innerHTML = '<option value="">Chưa có dữ liệu tỉnh/thành</option>';
    provinceEl.disabled = true;
    ocrProvinceEl.disabled = true;
    setProvinceStatus("Không tải được danh sách tỉnh/thành. Vui lòng kiểm tra kết nối API rồi thử lại.", "error", true);
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

function renderMapsQrWarnings(warnings) {
  mapsQrWarningsEl.innerHTML = "";
  (warnings || []).forEach((warning) => {
    const li = document.createElement("li");
    li.textContent = warning;
    mapsQrWarningsEl.appendChild(li);
  });
}

async function createMapsQr() {
  const inputText = (mapsQrInputEl.value || "").trim();
  if (!inputText) {
    mapsQrStatusTextEl.textContent = "Vui lòng nhập nội dung trước khi tạo QR.";
    return;
  }

  setMapsQrLoading(true);
  mapsQrStatusTextEl.textContent = "";
  mapsQrResultCardEl.classList.add("hidden");
  mapsQrWarningsEl.innerHTML = "";
  mapsQrResolvedDetailsEl.classList.add("hidden");

  try {
    const resp = await fetch(API_URLS.googleMapsQr, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_text: inputText }),
    });
    const data = await resp.json();
    if (!resp.ok || data?.ok === false) {
      mapsQrStatusTextEl.textContent =
        data?.message ||
        "Không đọc được tọa độ từ nội dung đã dán. Vui lòng kiểm tra lại link hoặc nhập theo dạng: 10.7769,106.7009";
      if (data?.suggestion) renderMapsQrWarnings([data.suggestion]);
      return;
    }

    mapsQrLatEl.textContent = Number(data.latitude).toFixed(12);
    mapsQrLngEl.textContent = Number(data.longitude).toFixed(12);
    mapsQrSourceEl.textContent = toVietnameseCoordinateSource(data.coordinate_source);
    mapsQrLinkEl.href = data.google_maps_url || "#";
    mapsQrLinkEl.textContent = data.google_maps_url || "-";
    mapsQrState.link = data.google_maps_url || "";
    mapsQrState.qrDataUrl = data.qr_png_base64 ? `data:image/png;base64,${data.qr_png_base64}` : "";

    if (mapsQrState.qrDataUrl) {
      mapsQrImageEl.src = mapsQrState.qrDataUrl;
      mapsQrImageBoxEl.classList.remove("hidden");
    } else {
      mapsQrImageEl.removeAttribute("src");
      mapsQrImageBoxEl.classList.add("hidden");
    }

    renderMapsQrWarnings((data.warnings || []).map((w) => translateWarningText(w)));
    if (data.resolved_url) {
      mapsQrResolvedTextEl.textContent = `Link gốc: ${data.source_url || "-"}\nLink đã xử lý: ${data.resolved_url}`;
      mapsQrResolvedDetailsEl.classList.remove("hidden");
    } else {
      mapsQrResolvedDetailsEl.classList.add("hidden");
    }
    mapsQrResultCardEl.classList.remove("hidden");
    mapsQrStatusTextEl.textContent = "Đã tạo QR Google Maps thành công.";
  } catch (_err) {
    mapsQrStatusTextEl.textContent =
      "Không đọc được tọa độ từ nội dung đã dán. Vui lòng kiểm tra lại link hoặc nhập theo dạng: 10.7769,106.7009";
  } finally {
    setMapsQrLoading(false);
  }
}

async function convertSelectedCandidates() {
  const province = (ocrProvinceEl.value || "").trim();
  if (!province) {
    multiResultStatusTextEl.textContent = "Vui lòng chọn Tỉnh/Thành phố để chuyển đổi chính xác.";
    multiResultCardEl.classList.remove("hidden");
    return;
  }
  const selected = getSelectedOcrCandidate();
  if (!selected) {
    multiResultStatusTextEl.textContent = "Vui lòng chọn một tọa độ trước khi chuyển đổi.";
    multiResultCardEl.classList.remove("hidden");
    return;
  }
  setMultiConvertLoading(true);
  multiResultStatusTextEl.textContent = "";
  try {
    const resp = await fetch(API_URLS.convert, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ province, value1: selected.value1, value2: selected.value2, input_mode: "auto", current_lat: null, current_lng: null }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data?.detail || "Chuyển đổi thất bại.");

    state.ocrSingle = {
      point_label: selected.point_label,
      value1: selected.value1,
      value2: selected.value2,
      province,
      latitude: Number(data.latitude),
      longitude: Number(data.longitude),
      google_maps_url: data.google_maps_url || `https://www.google.com/maps?q=${data.latitude},${data.longitude}`,
      qr_png_base64: data.qr_png_base64 || "",
    };
    ocrResultRawEl.textContent = `${selected.point_label}: ${selected.value1} | ${selected.value2}`;
    ocrResultProvinceEl.textContent = province;
    ocrResultLatEl.textContent = state.ocrSingle.latitude.toFixed(12);
    ocrResultLngEl.textContent = state.ocrSingle.longitude.toFixed(12);
    ocrResultMapsEl.href = state.ocrSingle.google_maps_url;
    ocrResultMapsEl.textContent = state.ocrSingle.google_maps_url;
    if (state.ocrSingle.qr_png_base64) {
      ocrResultQrEl.src = `data:image/png;base64,${state.ocrSingle.qr_png_base64}`;
      ocrQrBoxEl.classList.remove("hidden");
    } else {
      ocrQrBoxEl.classList.add("hidden");
    }
    multiResultStatusTextEl.textContent = "Đã tạo Google Maps và QR cho tọa độ đã chọn.";
    multiResultCardEl.classList.remove("hidden");
    multiResultCardEl.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    multiResultStatusTextEl.textContent = `Lỗi: ${err.message}`;
    multiResultCardEl.classList.remove("hidden");
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
  link.download = "geoqr-studio-google-maps-qr.png";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});
copyAllLatLngBtnEl.addEventListener("click", async () => {
  if (!state.ocrSingle) return void (multiResultStatusTextEl.textContent = "Chưa có kết quả OCR để sao chép.");
  await copyText(`${state.ocrSingle.latitude},${state.ocrSingle.longitude}`, "Đã sao chép Lat/Long từ OCR.");
});
downloadCsvBtnEl.addEventListener("click", () => {
  if (!state.ocrSingle?.qr_png_base64) return void (multiResultStatusTextEl.textContent = "Chưa có ảnh QR để tải.");
  const link = document.createElement("a");
  link.href = `data:image/png;base64,${state.ocrSingle.qr_png_base64}`;
  link.download = "geoqr-studio-ocr-google-maps-qr.png";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

mapsQrBtnEl.addEventListener("click", createMapsQr);
mapsQrOpenBtnEl.addEventListener("click", () => {
  if (!mapsQrState.link) return;
  window.open(mapsQrState.link, "_blank", "noopener");
});
mapsQrCopyBtnEl.addEventListener("click", async () => {
  if (!mapsQrState.link) return;
  await copyText(mapsQrState.link, "Đã sao chép link Google Maps.");
});
mapsQrDownloadBtnEl.addEventListener("click", () => {
  if (!mapsQrState.qrDataUrl.startsWith("data:image/png;base64,")) return;
  const link = document.createElement("a");
  link.href = mapsQrState.qrDataUrl;
  link.download = "geoqr-studio-google-maps-qr.png";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

featureCardEls.forEach((card) => {
  card.addEventListener("click", () => setActiveFeature(card.dataset.feature));
});
retryProvinceBtnEl?.addEventListener("click", loadProvinces);
retryOcrProvinceBtnEl?.addEventListener("click", loadProvinces);

setActiveFeature(state.activeFeature);
loadProvinces();

