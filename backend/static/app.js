const photoInput = document.getElementById('photo-input');
const startJobBtn = document.getElementById('start-job');
const runEstimateBtn = document.getElementById('run-estimate');
const resultOutput = document.getElementById('result-output');
const photoSelect = document.getElementById('photo-select');
const maskCanvas = document.getElementById('mask-canvas');
const clearMaskBtn = document.getElementById('clear-mask');
const saveMaskBtn = document.getElementById('save-mask');

let jobId = null;
let uploadedPhotos = [];
let jobPhotos = [];
let currentImage = null;
let drawing = false;

const ctx = maskCanvas.getContext('2d');
ctx.lineWidth = 12;
ctx.lineCap = 'round';
ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)';

function resetCanvas() {
  ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
  if (!currentImage) {
    return;
  }
  const scale = Math.min(maskCanvas.width / currentImage.width, maskCanvas.height / currentImage.height);
  const scaledWidth = currentImage.width * scale;
  const scaledHeight = currentImage.height * scale;
  const offsetX = (maskCanvas.width - scaledWidth) / 2;
  const offsetY = (maskCanvas.height - scaledHeight) / 2;
  ctx.drawImage(currentImage, offsetX, offsetY, scaledWidth, scaledHeight);
}

function loadSelectedImage() {
  const selected = photoSelect.value;
  if (!selected) {
    currentImage = null;
    resetCanvas();
    return;
  }
  const file = uploadedPhotos.find((photo) => photo.name === selected);
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const img = new Image();
    img.onload = () => {
      currentImage = img;
      resetCanvas();
    };
    img.src = reader.result;
  };
  reader.readAsDataURL(file);
}

photoInput.addEventListener('change', () => {
  uploadedPhotos = Array.from(photoInput.files || []);
  photoSelect.innerHTML = '';
  uploadedPhotos.forEach((file) => {
    const option = document.createElement('option');
    option.value = file.name;
    option.textContent = file.name;
    photoSelect.appendChild(option);
  });
  loadSelectedImage();
});

photoSelect.addEventListener('change', loadSelectedImage);

maskCanvas.addEventListener('mousedown', (event) => {
  if (!currentImage) return;
  drawing = true;
  ctx.beginPath();
  ctx.moveTo(event.offsetX, event.offsetY);
});

maskCanvas.addEventListener('mousemove', (event) => {
  if (!drawing) return;
  ctx.lineTo(event.offsetX, event.offsetY);
  ctx.stroke();
});

maskCanvas.addEventListener('mouseup', () => {
  drawing = false;
});

maskCanvas.addEventListener('mouseleave', () => {
  drawing = false;
});

clearMaskBtn.addEventListener('click', () => {
  resetCanvas();
});

startJobBtn.addEventListener('click', async () => {
  if (uploadedPhotos.length === 0) {
    resultOutput.textContent = 'Select photos before creating a job.';
    return;
  }
  const formData = new FormData();
  uploadedPhotos.forEach((file) => {
    formData.append('files', file);
  });
  resultOutput.textContent = 'Uploading...';
  const response = await fetch('/jobs', { method: 'POST', body: formData });
  if (!response.ok) {
    resultOutput.textContent = 'Upload failed.';
    return;
  }
  const data = await response.json();
  jobId = data.job_id;
  jobPhotos = data.photos;
  runEstimateBtn.disabled = false;
  resultOutput.textContent = `Job ${jobId} created.`;
});

saveMaskBtn.addEventListener('click', async () => {
  if (!jobId) {
    resultOutput.textContent = 'Create a job first.';
    return;
  }
  const selected = photoSelect.value;
  if (!selected) {
    resultOutput.textContent = 'Select a photo before saving a mask.';
    return;
  }
  const photoIndex = uploadedPhotos.findIndex((file) => file.name === selected);
  const jobPhoto = jobPhotos[photoIndex];
  if (!jobPhoto) {
    resultOutput.textContent = 'Unable to match photo to job.';
    return;
  }
  const blob = await new Promise((resolve) => maskCanvas.toBlob(resolve));
  const formData = new FormData();
  formData.append('file', blob, `${jobPhoto.photo_id}.png`);
  const response = await fetch(`/jobs/${jobId}/mask/${jobPhoto.photo_id}`, { method: 'POST', body: formData });
  if (!response.ok) {
    resultOutput.textContent = 'Mask upload failed.';
    return;
  }
  resultOutput.textContent = 'Mask saved.';
});

runEstimateBtn.addEventListener('click', async () => {
  if (!jobId) {
    resultOutput.textContent = 'Create a job first.';
    return;
  }
  resultOutput.textContent = 'Estimating...';
  const response = await fetch(`/jobs/${jobId}/estimate?debug=true`, { method: 'POST' });
  if (!response.ok) {
    resultOutput.textContent = 'Estimate failed.';
    return;
  }
  const data = await response.json();
  resultOutput.textContent = JSON.stringify(data, null, 2);
});
