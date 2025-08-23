// Main controller for TheArk Paper Management

class PaperManager {
    constructor() {
        // Initialize services
        this.apiService = new ApiService();
        this.uiService = new UIService();
        this.infiniteScrollService = new InfiniteScrollService(this.apiService, this.uiService);
        
        // State
        this.selectedCategories = new Set();
        
        // Initialize
        this.initializeEventListeners();
        this.loadCategories();
        
        // Load papers after PaperManager is fully initialized
        window.addEventListener('paperManagerReady', () => {
            this.infiniteScrollService.loadPapers();
        }, { once: true });
    }

    initializeEventListeners() {
        // Form submission
        const form = document.getElementById('paper-form');
        if (form) {
            form.addEventListener('submit', (e) => e.preventDefault());
        }

        // Button event listeners
        const summarizeBtn = document.getElementById('summarize-btn');
        const queueBtn = document.getElementById('queue-btn');

        if (summarizeBtn) {
            summarizeBtn.addEventListener('click', () => this.submitPaper(true));
        }

        if (queueBtn) {
            queueBtn.addEventListener('click', () => this.submitPaper(false));
        }

        // URL input validation and Enter key support
        const urlInput = document.getElementById('paper-url');
        if (urlInput) {
            urlInput.addEventListener('input', () => this.validateUrl());
            
            // Add Enter key support for URL input
            urlInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.submitPaper(true);
                }
            });
        }
        
        // Language selection change
        const languageSelect = document.getElementById('summary-language');
        if (languageSelect) {
            languageSelect.addEventListener('change', () => {
                this.infiniteScrollService.reset();
                this.infiniteScrollService.loadPapers();
            });
        }
    }

    validateUrl() {
        const urlInput = document.getElementById('paper-url');
        const url = urlInput.value.trim();
        
        const validation = ValidationService.validatePaperUrl(url);
        if (!validation.isValid) {
            this.uiService.showError(validation.message);
            return false;
        }
        
        return true;
    }

    async submitPaper(summarizeNow = false) {
        const urlInput = document.getElementById('paper-url');
        const url = urlInput.value.trim();

        // Validation
        const validation = ValidationService.validatePaperUrl(url);
        if (!validation.isValid) {
            this.uiService.showError(validation.message, summarizeNow);
            return;
        }

        // Show loading state
        this.uiService.setLoadingState(true, summarizeNow);

        try {
            const languageSelect = document.getElementById('summary-language');
            const selectedLanguage = languageSelect ? languageSelect.value : 'Korean';
            
            const requestData = {
                url: url,
                summarize_now: summarizeNow,
                force_refresh_metadata: false,
                force_resummarize: false,
                summary_language: selectedLanguage
            };

            if (summarizeNow) {
                // Use streaming API for real-time updates
                await this.submitPaperWithStreaming(requestData);
            } else {
                // Use regular API for queue submission
                const result = await this.apiService.createPaper(requestData);
                this.uiService.showSuccess(false, result);
            }

            // Clear input
            urlInput.value = '';
            
        } catch (error) {
            this.uiService.showError(error.message, summarizeNow);
        } finally {
            this.uiService.setLoadingState(false, summarizeNow);
        }
    }

    async submitPaperWithStreaming(requestData) {
        try {
            const responseBody = await this.apiService.createPaperWithStreaming(requestData);
            const reader = responseBody.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            this.handleStreamingData(data);
                        } catch (e) {
                            console.error('Error parsing streaming data:', e);
                        }
                    }
                }
            }
        } catch (error) {
            throw new Error(`Streaming failed: ${error.message}`);
        }
    }

    handleStreamingData(data) {
        switch (data.type) {
            case 'status':
                this.uiService.updateButtonStatus(data.message);
                break;
            case 'complete':
                this.uiService.showSuccess(true, data.paper);
                break;
            case 'error':
                this.uiService.showError(data.message, true);
                break;
        }
    }

    async loadCategories() {
        try {
            const data = await this.apiService.getCategories();
            this.uiService.renderCategories(data.categories);
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    }

    toggleCategory(category, event) {
        const button = event.target;
        
        if (this.selectedCategories.has(category)) {
            this.selectedCategories.delete(category);
            button.classList.remove('active');
        } else {
            this.selectedCategories.add(category);
            button.classList.add('active');
        }

        // TODO: Implement paper filtering based on selected categories
    }

    async deletePaper(arxivId) {
        if (!confirm(`Are you sure you want to delete paper ${arxivId}?`)) {
            return;
        }
        
        try {
            const result = await this.apiService.deletePaper(arxivId);
            // Remove the paper element from the UI
            this.uiService.removePaperElement(arxivId);
            // Show success message
            this.uiService.showDeleteSuccess(arxivId);
            
            // Remove from papers array
            const papers = this.infiniteScrollService.getPapers();
            const updatedPapers = papers.filter(paper => paper.arxiv_id !== arxivId);
            this.infiniteScrollService.setPapers(updatedPapers);
            
        } catch (error) {
            this.uiService.showError(`Error deleting paper: ${error.message}`, false);
        }
    }

    // Public methods for external access
    getPapers() {
        return this.infiniteScrollService.getPapers();
    }

    loadPapers() {
        return this.infiniteScrollService.loadPapers();
    }
}

// Export for use in other modules
window.PaperManager = PaperManager;
