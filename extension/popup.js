// Attempt to get the video URL from the current active tab
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const currentTab = tabs[0];
  const urlInput = document.getElementById('videoUrl');
  const analyzeBtn = document.getElementById('analyzeBtn');

  if (currentTab && currentTab.url) {
    urlInput.value = currentTab.url;
    // Enable the button if it's a URL (for simplicity, we assume we can attempt to ingest any URL)
    analyzeBtn.disabled = false;
  } else {
    urlInput.value = "Unable to detect video URL.";
  }
});

document.getElementById('dashboardBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: 'http://localhost:5173/' });
});

document.getElementById('analyzeBtn').addEventListener('click', () => {
  const url = document.getElementById('videoUrl').value;
  if (!url) return;

  const btn = document.getElementById('analyzeBtn');
  const loader = document.getElementById('loader');
  const statusMsg = document.getElementById('statusMsg');

  btn.disabled = true;
  loader.style.display = 'block';
  statusMsg.textContent = '';
  statusMsg.className = 'status';

  // Send a message to the background script to perform the API call
  chrome.runtime.sendMessage({ action: 'ingestVideo', url: url }, (response) => {
    loader.style.display = 'none';
    if (response && response.success) {
      statusMsg.textContent = "✨ Analysis Started! Opening dashboard...";
      statusMsg.className = 'status success';
      btn.textContent = "Processing...";
      
      // Open the Alexandria frontend dashboard
      setTimeout(() => {
        chrome.tabs.create({ url: 'http://localhost:5173/' });
      }, 1000);
    } else {
      const errorMsg = response ? response.error : "Backend not reachable. Ensure server is running on port 8000.";
      statusMsg.textContent = "❌ " + errorMsg;
      statusMsg.className = 'status error';
      btn.disabled = false;
      btn.textContent = "Try Again";
    }
  });
});
