// Infinite scroll module for TheArk

class InfiniteScrollService {
    constructor(apiService, uiService) {
        this.apiService = apiService;
        this.uiService = uiService;
        this.currentPage = 0;
        this.pageSize = 20;
        this.papers = [];
        this.isLoading = false;
        this.hasMore = true;
        
        this.initializeScrollListener();
    }

    initializeScrollListener() {
        const content = document.querySelector('.content');
        if (content) {
            content.addEventListener('scroll', () => {
                this.handleScroll();
            });
        }
    }

    handleScroll() {
        const content = document.querySelector('.content');
        if (!content || this.isLoading || !this.hasMore) return;

        const scrollTop = content.scrollTop;
        const scrollHeight = content.scrollHeight;
        const clientHeight = content.clientHeight;

        // Load more when user is near bottom (within 100px)
        if (scrollTop + clientHeight >= scrollHeight - 100) {
            this.loadMorePapers();
        }
    }

    async loadMorePapers() {
        if (this.isLoading || !this.hasMore) return;
        
        this.isLoading = true;
        this.currentPage++;
        
        try {
            const language = document.getElementById('summary-language').value;
            const data = await this.apiService.getPapers(this.pageSize, this.currentPage * this.pageSize, language);
            
            // Append new papers to existing array
            this.papers = this.papers.concat(data.papers);
            this.hasMore = data.has_more;
            
            // Render all papers
            this.uiService.renderPaperList(this.papers);
            
            // Show loading indicator at bottom
            this.uiService.showLoadingIndicator();
        } catch (error) {
            console.error('Error loading more papers:', error);
            this.currentPage--; // Revert page increment
        } finally {
            this.isLoading = false;
        }
    }

    async loadPapers() {
        try {
            this.isLoading = true;
            const language = document.getElementById('summary-language').value;
            const data = await this.apiService.getPapers(this.pageSize, this.currentPage * this.pageSize, language);
            
            this.papers = data.papers; // Store papers
            this.hasMore = data.has_more;
            this.uiService.renderPaperList(this.papers);
            this.uiService.hideLoadingIndicator();
        } catch (error) {
            console.error('Error loading papers:', error);
        } finally {
            this.isLoading = false;
        }
    }

    reset() {
        this.currentPage = 0;
        this.papers = [];
        this.hasMore = true;
        this.isLoading = false;
    }

    getPapers() {
        return this.papers;
    }

    setPapers(papers) {
        this.papers = papers;
    }
}

// Export for use in other modules
window.InfiniteScrollService = InfiniteScrollService;
