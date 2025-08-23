// Main JavaScript for TheArk Paper Management Frontend

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing PaperManager...');
    window.paperManager = new PaperManager();
    console.log('PaperManager initialized:', window.paperManager);
    
    // Dispatch event to notify that PaperManager is ready
    window.dispatchEvent(new CustomEvent('paperManagerReady'));
});
