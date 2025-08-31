// UI rendering module for TheArk

class UIService {
    constructor() {
        this.papers = [];
        
        // Initialize specialized managers
        this.starManager = new window.StarManager();
        this.loadingIndicators = new window.LoadingIndicators();
        this.paperListManager = new window.PaperListManager();
        this.utilityManager = new window.UtilityManager();
        
        // Make managers globally available for other modules
        window.starManager = this.starManager;
        window.loadingIndicators = this.loadingIndicators;
        window.paperListManager = this.paperListManager;
        window.utilityManager = this.utilityManager;
    }

    // Delegate to specialized managers
    renderPaperList(papers) {
        return this.paperListManager.renderPaperList(papers);
    }

    createPaperElement(paper) {
        return this.paperListManager.createPaperElement(paper);
    }

    createStarButton(paper) {
        return this.starManager.createStarButton(paper);
    }

    updateAllStarButtons(paperId, isStarred) {
        return this.starManager.updateAllStarButtons(paperId, isStarred);
    }

    updateStarButton(starButton, isStarred) {
        return this.starManager.updateStarButton(starButton, isStarred);
    }

    addStar(paperId) {
        return this.starManager.addStar(paperId);
    }

    removeStar(paperId) {
        return this.starManager.removeStar(paperId);
    }

    createRelevanceTag(score, isPaper = false) {
        return this.paperListManager.createRelevanceTag(score, isPaper);
    }

    renderCategories(categories) {
        return this.paperListManager.renderCategories(categories);
    }

    showLoadingIndicator(message = '⏳ Loading more papers...') {
        return this.loadingIndicators.showLoadingIndicator(message);
    }

    showLoadMoreButton() {
        return this.loadingIndicators.showLoadMoreButton();
    }

    showRefreshButton() {
        return this.loadingIndicators.showRefreshButton();
    }

    showErrorIndicator(message) {
        return this.loadingIndicators.showErrorIndicator(message);
    }

    hideBottomIndicator() {
        return this.loadingIndicators.hideBottomIndicator();
    }

    hideLoadingIndicator() {
        return this.loadingIndicators.hideLoadingIndicator();
    }

    showSuccess(summarizeNow, result) {
        return this.utilityManager.showSuccess(summarizeNow, result);
    }

    showError(message, summarizeNow = false) {
        return this.utilityManager.showError(message, summarizeNow);
    }

    showDeleteSuccess(arxivId) {
        return this.utilityManager.showDeleteSuccess(arxivId);
    }

    setLoadingState(loading, summarizeNow) {
        return this.utilityManager.setLoadingState(loading, summarizeNow);
    }

    removePaperElement(arxivId) {
        return this.paperListManager.removePaperElement(arxivId);
    }

    addPaperElement(paperData) {
        return this.paperListManager.addPaperElement(paperData);
    }

    updatePaperElement(arxivId, paperData) {
        return this.paperListManager.updatePaperElement(arxivId, paperData);
    }

    findPaperElement(arxivId) {
        return this.paperListManager.findPaperElement(arxivId);
    }

    createTLDR(summary) {
        return this.paperListManager.createTLDR(summary);
    }

    createOverview(paper) {
        return this.paperListManager.createOverview(paper);
    }
}

// Export for use in other modules
window.UIService = UIService;
