// Main JavaScript for TheArk Paper Management Frontend

class PaperManager {
    constructor() {
        this.apiBaseUrl = '/v1/papers';
        this.configApiUrl = '/v1/config';
        this.selectedCategories = new Set();
        this.initializeEventListeners();
        this.loadCategories();
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
    }

    validateUrl() {
        const urlInput = document.getElementById('paper-url');
        const url = urlInput.value.trim();
        
        // Clear previous validation
        this.clearMessages();
        
        if (url && !this.isValidArxivUrl(url)) {
            this.showError('Please enter a valid arXiv URL (e.g., https://arxiv.org/abs/2508.01234)');
            return false;
        }
        
        return true;
    }

    isValidArxivUrl(url) {
        const arxivPattern = /^https?:\/\/arxiv\.org\/(abs|pdf)\/\d{4}\.\d{5}$/;
        return arxivPattern.test(url);
    }

    async submitPaper(summarizeNow = false) {
        const urlInput = document.getElementById('paper-url');
        const url = urlInput.value.trim();

        // Validation
        if (!url) {
            this.showError('Please enter a paper URL');
            return;
        }

        if (!this.validateUrl()) {
            return;
        }

        // Show loading state
        this.setLoadingState(true, summarizeNow);

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

            const response = await fetch(this.apiBaseUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.showSuccess(result, summarizeNow);

        } catch (error) {
            console.error('Error submitting paper:', error);
            this.showError(`Failed to submit paper: ${error.message}`);
        } finally {
            this.setLoadingState(false, summarizeNow);
        }
    }

    setLoadingState(loading, summarizeNow) {
        const summarizeBtn = document.getElementById('summarize-btn');
        const queueBtn = document.getElementById('queue-btn');
        const urlInput = document.getElementById('paper-url');

        if (loading) {
            if (summarizeNow) {
                summarizeBtn.disabled = true;
                summarizeBtn.innerHTML = '<span class="loading"></span>Processing...';
            } else {
                queueBtn.disabled = true;
                queueBtn.innerHTML = '<span class="loading"></span>Adding to Queue...';
            }
            urlInput.disabled = true;
        } else {
            summarizeBtn.disabled = false;
            queueBtn.disabled = false;
            summarizeBtn.innerHTML = 'Summarize Now';
            queueBtn.innerHTML = 'Add to Queue';
            urlInput.disabled = false;
        }
    }

    showSuccess(result, summarizeNow) {
        this.clearMessages();
        
        const message = summarizeNow 
            ? 'Paper processed successfully! Summary is being generated in the background.'
            : 'Paper added to queue successfully!';
        
        this.showMessage(message, 'success');
        this.displayResult(result);
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type) {
        const messageContainer = document.getElementById('message-container');
        if (!messageContainer) return;

        const messageElement = document.createElement('div');
        messageElement.className = `${type}-message`;
        messageElement.textContent = message;
        
        messageContainer.appendChild(messageElement);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.remove();
            }
        }, 5000);
    }

    clearMessages() {
        const messageContainer = document.getElementById('message-container');
        if (messageContainer) {
            messageContainer.innerHTML = '';
        }
    }

    displayResult(result) {
        const resultContainer = document.getElementById('result-container');
        if (!resultContainer) return;

        const resultHtml = `
            <div class="result-item">
                <div class="result-title">${this.escapeHtml(result.title)}</div>
                <div class="result-meta">
                    <strong>arXiv ID:</strong> ${result.arxiv_id} | 
                    <strong>Authors:</strong> ${result.authors.join(', ')} | 
                    <strong>Categories:</strong> ${result.categories.join(', ')}
                </div>
                <div class="result-abstract">${this.escapeHtml(result.abstract)}</div>
                <div class="result-links">
                    <a href="${result.pdf_url}" target="_blank" class="result-link">View PDF</a>
                    <a href="https://arxiv.org/abs/${result.arxiv_id}" target="_blank" class="result-link">View on arXiv</a>
                </div>
            </div>
        `;

        resultContainer.innerHTML = resultHtml;
        resultContainer.classList.remove('hidden');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async loadCategories() {
        try {
            const response = await fetch(`${this.configApiUrl}/categories`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.renderCategoryButtons(data.categories);
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    }

    renderCategoryButtons(categories) {
        const container = document.getElementById('category-buttons');
        if (!container) return;

        container.innerHTML = '';
        
        // Add all categories to selected set by default
        categories.forEach(category => this.selectedCategories.add(category));
        
        categories.forEach(category => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'category-btn'; // Default: active state
            button.textContent = category;
            button.dataset.category = category;
            
            button.addEventListener('click', () => this.toggleCategory(category, button));
            
            container.appendChild(button);
        });
        
        console.log('All categories selected by default:', Array.from(this.selectedCategories));
    }

    toggleCategory(category, button) {
        if (this.selectedCategories.has(category)) {
            this.selectedCategories.delete(category);
            button.classList.add('inactive');
        } else {
            this.selectedCategories.add(category);
            button.classList.remove('inactive');
        }
        
        console.log('Selected categories:', Array.from(this.selectedCategories));
        // TODO: Implement paper filtering based on selected categories
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PaperManager();
});
