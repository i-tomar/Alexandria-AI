// content.js - Runs in the context of the web page
// We can use this to extract specific LMS video URLs or metadata if needed in the future.
console.log("Alexandria content script loaded.");

// Example: send the video source URL to the extension if it's an HTML5 player
function findVideoSource() {
    const video = document.querySelector('video');
    return video ? video.src : window.location.href;
}

// Just an example stub - currently the popup directly grabs the tab URL
