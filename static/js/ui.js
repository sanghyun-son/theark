// UI rendering module for TheArk
import { StarManager } from './ui/star-manager.js';
import { LoadingIndicators } from './ui/loading-indicators.js';
import { PaperListManager } from './ui/paper-list-manager.js';
import { UtilityManager } from './ui/utility-manager.js';
import { ModalManager } from './ui/modal-manager.js';

export class UIService {
    constructor(apiService, paperManager) {
        this.apiService = apiService;
        this.paperManager = paperManager;
        
        // Initialize specialized managers
        this.starManager = new StarManager();
        this.loadingIndicators = new LoadingIndicators();
        this.paperListManager = new PaperListManager(this.starManager, this.apiService, this.paperManager);
        this.utilityManager = new UtilityManager();
    }

    // Method to create and show a modal
    showModal(paper) {
        const modal = new ModalManager(paper, this.starManager);
        modal.show();
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

