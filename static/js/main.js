// Main JavaScript for TheArk Paper Management Frontend
import { PaperManager } from './paper-manager.js';

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing PaperManager...');
    // Instantiate the main controller to start the application
    new PaperManager();
});

