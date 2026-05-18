// Background service worker for handling API requests to the backend

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'ingestVideo') {
    const backendUrl = "http://localhost:8000/ingest";
    
    fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ video_url: request.url })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      sendResponse({ success: true, data: data });
    })
    .catch(error => {
      console.error("Error during ingest:", error);
      sendResponse({ success: false, error: error.message });
    });

    // Return true to indicate we will send a response asynchronously
    return true; 
  }
});
