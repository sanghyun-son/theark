// Infinite scroll module for TheArk

export class InfiniteScrollService {
    constructor(apiService, uiService) {
        this.apiService = apiService;
        this.uiService = uiService;
        this.currentPage = 0;
        this.pageSize = 10;
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
        
        // Show loading indicator
        this.uiService.showLoadingIndicator('⏳ Loading more papers...');
        
        try {
            const language = document.getElementById('summary-language').value;
            const prioritizeSummaries = document.getElementById('prioritize-summaries').checked;
            const sortByRelevance = document.getElementById('sort-by-relevance').checked;
            const data = await this.apiService.getPapers(this.pageSize, this.currentPage * this.pageSize, language, prioritizeSummaries, sortByRelevance);
            
            // Append new papers to existing array
            this.papers = this.papers.concat(data.papers);
            this.hasMore = data.has_more;
            
            // Render all papers
            this.uiService.renderPaperList(this.papers);
            
            // Update bottom indicator based on hasMore status
            if (this.hasMore) {
                this.uiService.showLoadMoreButton();
            } else {
                this.uiService.showRefreshButton();
            }
        } catch (error) {
            console.error('Error loading more papers:', error);
            this.currentPage--; // Revert page increment
            this.uiService.showErrorIndicator('❌ Failed to load more papers');
        } finally {
            this.isLoading = false;
        }
    }

    async loadPapers() {
        try {
            this.isLoading = true;
            const language = document.getElementById('summary-language').value;
            const prioritizeSummaries = document.getElementById('prioritize-summaries').checked;
            const sortByRelevance = document.getElementById('sort-by-relevance').checked;
            const data = await this.apiService.getPapers(this.pageSize, this.currentPage * this.pageSize, language, prioritizeSummaries, sortByRelevance);
            
            this.papers = data.papers; // Store papers
            this.hasMore = data.has_more;
            this.uiService.renderPaperList(this.papers);
            
            // Update bottom indicator based on hasMore status
            if (this.hasMore) {
                this.uiService.showLoadMoreButton();
            } else {
                this.uiService.showRefreshButton();
            }
        } catch (error) {
            console.error('Error loading papers:', error);
            this.uiService.showErrorIndicator('❌ Failed to load papers');
        } finally {
            this.isLoading = false;
        }
    }

    reset() {
        this.currentPage = 0;
        this.papers = [];
        this.hasMore = true;
        this.isLoading = false;
        this.uiService.hideBottomIndicator();
    }

    getPapers() {
        return this.papers;
    }

    setPapers(papers) {
        this.papers = papers;
    }
}

