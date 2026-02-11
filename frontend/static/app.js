const photoInput = document.getElementById('photoInput');
const uploadBtn = document.getElementById('uploadBtn');
const jobStatus = document.getElementById('jobStatus');
const maskSection = document.getElementById('maskSection');
const maskList = document.getElementById('maskList');
const estimateSection = document.getElementById('estimateSection');
const estimateBtn = document.getElementById('estimateBtn');
const estimateOutput = document.getElementById('estimateOutput');
const debugToggle = document.getElementById('debugToggle');

let currentJobId = null;
let photoEntries = [];

const createMaskRow = (photo) => {
  const row = document.createElement('div');
  row.className = 'mask-row';

  const label = document.createElement('span');
  label.textContent = photo.filename || photo.photo_id;

  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';

  const button = document.createElement('button');
  button.textContent = 'Upload mask';
  button.addEventListener('click', async () => {
    if (!input.files.length) {
      alert('Select a mask image first.');
      return;
    }

    const formData = new FormData();
    formData.append('mask', input.files[0]);

    const response = await fetch(`/jobs/${currentJobId}/mask/${photo.photo_id}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      alert('Failed to upload mask.');
      return;
    }

    button.textContent = 'Mask uploaded';
    button.disabled = true;
  });

  row.appendChild(label);
  row.appendChild(input);
  row.appendChild(button);

  return row;
};

uploadBtn.addEventListener('click', async () => {
  if (!photoInput.files.length) {
    alert('Please select at least one photo.');
    return;
  }

  const formData = new FormData();
  Array.from(photoInput.files).forEach((file) => formData.append('photos', file));

  jobStatus.textContent = 'Uploading...';

  const response = await fetch('/jobs', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    jobStatus.textContent = 'Failed to create job.';
    return;
  }

  const data = await response.json();
  currentJobId = data.job_id;
  photoEntries = data.photos || [];

  jobStatus.textContent = `Job created: ${currentJobId}`;
  maskList.innerHTML = '';
  photoEntries.forEach((photo) => maskList.appendChild(createMaskRow(photo)));
  maskSection.hidden = false;
  estimateSection.hidden = false;
});

estimateBtn.addEventListener('click', async () => {
  if (!currentJobId) {
    alert('Create a job first.');
    return;
  }

  estimateOutput.textContent = 'Estimating...';
  const formData = new FormData();
  formData.append('debug', debugToggle.checked ? 'true' : 'false');

  const response = await fetch(`/jobs/${currentJobId}/estimate`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    estimateOutput.textContent = 'Failed to estimate.';
    return;
  }

  const data = await response.json();
  estimateOutput.textContent = JSON.stringify(data, null, 2);
});
