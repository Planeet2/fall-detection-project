const API_URL = "http://localhost:8000/predict-video";

const videoInput = document.getElementById("videoInput");
const chooseFileButton = document.getElementById("chooseFileButton");
const fileName = document.getElementById("fileName");
const videoPreview = document.getElementById("videoPreview");
const analyzeButton = document.getElementById("analyzeButton");

const loadingBlock = document.getElementById("loadingBlock");

const emptyState = document.getElementById("emptyState");
const resultSection = document.getElementById("resultSection");
const resultCard = document.getElementById("resultCard");
const resultLabel = document.getElementById("resultLabel");
const resultMessage = document.getElementById("resultMessage");

const probabilityText = document.getElementById("probabilityText");
const probabilityBar = document.getElementById("probabilityBar");

const statusValue = document.getElementById("statusValue");
const framesValue = document.getElementById("framesValue");
const windowsValue = document.getElementById("windowsValue");

const errorSection = document.getElementById("errorSection");
const errorMessage = document.getElementById("errorMessage");

let selectedFile = null;

chooseFileButton.addEventListener("click", () => {
  videoInput.click();
});

videoInput.addEventListener("change", () => {
  const file = videoInput.files[0];

  resetResult();
  hideError();

  if (!file) {
    selectedFile = null;
    fileName.textContent = "Файл пока не выбран";
    analyzeButton.disabled = true;
    videoPreview.hidden = true;
    videoPreview.removeAttribute("src");
    return;
  }

  selectedFile = file;

  fileName.textContent = `Выбран файл: ${file.name}`;
  analyzeButton.disabled = false;

  const previewUrl = URL.createObjectURL(file);
  videoPreview.src = previewUrl;
  videoPreview.hidden = false;
});

analyzeButton.addEventListener("click", async () => {
  if (!selectedFile) {
    showError("Сначала выберите видеофайл.");
    return;
  }

  resetResult();
  hideError();
  setLoading(true);

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
    showError(
      error.message ||
      "Не удалось подключиться к backend. Проверьте, что сервер запущен на http://localhost:8000"
    );
  } finally {
    setLoading(false);
  }
});

function showResult(data) {
  emptyState.hidden = true;
  resultSection.hidden = false;

  const status = data.status || "safe";
  const probability = Number(data.fall_probability || 0);
  const percentage = Math.round(probability * 1000) / 10;

  resultCard.classList.remove("safe", "fall");
  probabilityBar.classList.remove("safe", "fall");

  if (status === "fall") {
    resultCard.classList.add("fall");
    probabilityBar.classList.add("fall");
  } else {
    resultCard.classList.add("safe");
    probabilityBar.classList.add("safe");
  }

  resultLabel.textContent = data.label || status.toUpperCase();
  resultMessage.textContent = data.message || "Analysis completed";

  probabilityText.textContent = `${percentage}%`;
  probabilityBar.style.width = `${Math.min(percentage, 100)}%`;

  statusValue.textContent = status;
  framesValue.textContent = data.frames_processed ?? "—";
  windowsValue.textContent = data.windows_analyzed ?? "—";
}

function resetResult() {
  emptyState.hidden = false;
  resultSection.hidden = true;

  resultCard.classList.remove("safe", "fall");
  probabilityBar.classList.remove("safe", "fall");

  resultLabel.textContent = "—";
  resultMessage.textContent = "—";
  probabilityText.textContent = "—";
  probabilityBar.style.width = "0%";
  statusValue.textContent = "—";
  framesValue.textContent = "—";
  windowsValue.textContent = "—";
}

function showError(message) {
  errorSection.hidden = false;
  errorMessage.textContent = message;
}

function hideError() {
  errorSection.hidden = true;
}

function setLoading(isLoading) {
  loadingBlock.hidden = !isLoading;
  analyzeButton.disabled = isLoading || !selectedFile;
  chooseFileButton.disabled = isLoading;
}