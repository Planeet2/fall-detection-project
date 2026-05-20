const API_URL = "http://localhost:8000/predict-video";

const videoInput = document.getElementById("videoInput");
const fileName = document.getElementById("fileName");
const videoPreview = document.getElementById("videoPreview");
const analyzeButton = document.getElementById("analyzeButton");
const loadingText = document.getElementById("loadingText");

const resultSection = document.getElementById("resultSection");
const resultBox = document.getElementById("resultBox");
const resultLabel = document.getElementById("resultLabel");
const resultMessage = document.getElementById("resultMessage");
const probabilityValue = document.getElementById("probabilityValue");
const framesValue = document.getElementById("framesValue");
const windowsValue = document.getElementById("windowsValue");

const errorSection = document.getElementById("errorSection");
const errorMessage = document.getElementById("errorMessage");

let selectedFile = null;

videoInput.addEventListener("change", () => {
  const file = videoInput.files[0];

  hideResult();
  hideError();

  if (!file) {
    selectedFile = null;
    fileName.textContent = "Файл не выбран";
    analyzeButton.disabled = true;
    videoPreview.hidden = true;
    videoPreview.removeAttribute("src");
    return;
  }

  selectedFile = file;
  fileName.textContent = `Выбран файл: ${file.name}`;
  analyzeButton.disabled = false;

  const videoUrl = URL.createObjectURL(file);
  videoPreview.src = videoUrl;
  videoPreview.hidden = false;
});

analyzeButton.addEventListener("click", async () => {
  if (!selectedFile) {
    showError("Сначала выберите видеофайл.");
    return;
  }

  hideResult();
  hideError();

  analyzeButton.disabled = true;
  loadingText.hidden = false;

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);

      if (errorData && errorData.detail) {
        throw new Error(errorData.detail);
      }

      throw new Error(`Backend вернул ошибку: ${response.status}`);
    }

    const data = await response.json();

    showResult(data);
  } catch (error) {
    showError(error.message || "Не удалось подключиться к backend.");
  } finally {
    analyzeButton.disabled = false;
    loadingText.hidden = true;
  }
});

function showResult(data) {
  resultSection.hidden = false;

  const status = data.status;
  const probability = data.fall_probability;
  const percent = Math.round(probability * 1000) / 10;

  resultBox.classList.remove("safe", "fall");

  if (status === "fall") {
    resultBox.classList.add("fall");
  } else {
    resultBox.classList.add("safe");
  }

  resultLabel.textContent = data.label || status.toUpperCase();
  resultMessage.textContent = data.message || "";

  probabilityValue.textContent = `${percent}%`;
  framesValue.textContent = data.frames_processed ?? "—";
  windowsValue.textContent = data.windows_analyzed ?? "—";
}

function hideResult() {
  resultSection.hidden = true;
}

function showError(message) {
  errorSection.hidden = false;
  errorMessage.textContent = message;
}

function hideError() {
  errorSection.hidden = true;
}