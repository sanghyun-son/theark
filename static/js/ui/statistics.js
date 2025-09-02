// Statistics component for TheArk
export class StatisticsComponent {
    constructor(apiService) {
        this.apiService = apiService;
        this.stats = null;
        this.updateInterval = null;
        this.element = null;
        this.init();
    }

    init() {
        this.createStatisticsElement();
        this.startAutoUpdate();
        this.loadStatistics();
    }

    createStatisticsElement() {
        // Statistics elements are already in the HTML footer, just find them
        this.element = document.querySelector('.statistics-display');
        if (!this.element) {
            console.error('Statistics display element not found in footer');
        }
    }

    async loadStatistics() {
        try {
            this.stats = await this.apiService.getStatistics();
            this.updateDisplay();
        } catch (error) {
            console.error('Failed to load statistics:', error);
            this.showError();
        }
    }

    updateDisplay() {
        if (!this.stats) return;

        // Update total papers
        const totalPapersEl = document.getElementById('total-papers');
        if (totalPapersEl) {
            totalPapersEl.textContent = this.stats.total_papers.toLocaleString();
        }

        // Update papers with summary
        const papersWithSummaryEl = document.getElementById('papers-with-summary');
        if (papersWithSummaryEl) {
            papersWithSummaryEl.textContent = this.stats.papers_with_summary.toLocaleString();
        }

        // Update coverage percentage
        const coverageEl = document.getElementById('summary-coverage');
        if (coverageEl) {
            coverageEl.textContent = `${this.stats.summary_coverage_percentage}`;
        }

        // Update last updated time
        const lastUpdatedEl = document.getElementById('last-updated');
        if (lastUpdatedEl) {
            const updateTime = new Date(this.stats.last_updated);
            const now = new Date();
            const diffMs = now - updateTime;
            const diffMins = Math.floor(diffMs / (1000 * 60));
            
            if (diffMins < 1) {
                lastUpdatedEl.textContent = 'Just now';
            } else if (diffMins < 60) {
                lastUpdatedEl.textContent = `${diffMins}m ago`;
            } else {
                const diffHours = Math.floor(diffMins / 60);
                lastUpdatedEl.textContent = `${diffHours}h ago`;
            }
        }
    }

    showError() {
        // Show error state
        const totalPapersEl = document.getElementById('total-papers');
        const papersWithSummaryEl = document.getElementById('papers-with-summary');
        const coverageEl = document.getElementById('summary-coverage');
        const lastUpdatedEl = document.getElementById('last-updated');

        if (totalPapersEl) totalPapersEl.textContent = 'Error';
        if (papersWithSummaryEl) papersWithSummaryEl.textContent = 'Error';
        if (coverageEl) coverageEl.textContent = 'Error';
        if (lastUpdatedEl) lastUpdatedEl.textContent = 'Error';
    }

    startAutoUpdate() {
        // Update every minute (60000ms)
        this.updateInterval = setInterval(() => {
            this.loadStatistics();
        }, 60000);
    }

    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    destroy() {
        this.stopAutoUpdate();
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
    }
}
