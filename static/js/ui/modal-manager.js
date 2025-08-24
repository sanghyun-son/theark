// Modal management module for TheArk

class ModalManager {
    constructor(paper) {
        this.paper = paper;
        this.modal = null;
        this.overlay = null;
        
        // Bind methods to maintain context
        this.show = this.show.bind(this);
        this.close = this.close.bind(this);
        this.handleEscape = this.handleEscape.bind(this);
        this.toggleModalStar = this.toggleModalStar.bind(this);
        
        this.createModal();
        this.setupEventListeners();
    }

    show() {
        document.body.appendChild(this.overlay);
        this.overlay.style.display = 'flex';
        this.modal.style.display = 'block';
        
        // Focus on modal for accessibility
        this.modal.focus();
    }

    createModal() {
        // Create modal overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        
        // Create modal content
        this.modal = document.createElement('div');
        this.modal.className = 'modal-content';
        
        // Store paper ID for synchronization
        this.modal.setAttribute('data-paper-id', this.paper.paper_id);
        
        // Create header
        const header = this.createHeader();
        
        // Create body
        const body = this.createBody();
        
        // Create footer
        const footer = this.createFooter();
        
        // Create container for relevance tag and star button
        const tagContainer = this.createTagContainer();
        
        this.modal.appendChild(header);
        this.modal.appendChild(body);
        this.modal.appendChild(footer);
        this.modal.appendChild(tagContainer);
        this.overlay.appendChild(this.modal);
    }

    createTagContainer() {
        const container = document.createElement('div');
        container.className = 'modal-tag-container';
        
        // Add relevance tag if exists
        if (this.paper.summary && this.paper.summary.relevance !== undefined && this.paper.summary.relevance !== null) {
            const relevanceTag = this.createModalRelevanceTag(this.paper.summary.relevance);
            container.appendChild(relevanceTag);
        }
        
        // Add star button
        const starButton = this.createModalStarButton();
        container.appendChild(starButton);
        
        return container;
    }

    createHeader() {
        const header = document.createElement('div');
        header.className = 'modal-header';
        
        const title = document.createElement('div');
        title.className = 'modal-title';
        title.textContent = this.paper.title;
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close';
        closeBtn.textContent = '×';
        closeBtn.onclick = () => this.close();
        
        header.appendChild(title);
        header.appendChild(closeBtn);
        
        return header;
    }

    createModalStarButton() {
        // Use the centralized star manager to create the star button
        if (window.starManager) {
            const starButton = window.starManager.createStarButton(this.paper, 'modal');
            
            // Add modal-specific class for styling
            starButton.classList.add('modal-star-button');
            
            // Override the click handler to use modal-specific logic
            starButton.onclick = (e) => {
                e.stopPropagation();
                this.toggleModalStar(starButton);
            };
            
            return starButton;
        }
        
        // Fallback if star manager is not available
        const starButton = document.createElement('button');
        starButton.className = 'modal-star-button';
        starButton.id = `star-${this.paper.paper_id}-modal`;
        
        // Set initial state based on paper data
        const isStarred = this.paper.is_starred || false;
        starButton.textContent = isStarred ? '⭐' : '☆';
        starButton.title = isStarred ? 'Remove from favorites' : 'Add to favorites';
        
        if (isStarred) {
            starButton.classList.add('starred');
        }
        
        // Add click handler
        starButton.onclick = (e) => {
            e.stopPropagation();
            this.toggleModalStar(starButton);
        };
        
        return starButton;
    }

    async toggleModalStar(starButton) {
        console.log('🎭 toggleModalStar called');
        const isCurrentlyStarred = starButton.classList.contains('starred');
        const newStarredState = !isCurrentlyStarred;
        console.log('🎭 Star state change:', { isCurrentlyStarred, newStarredState, paperId: this.paper.paper_id });
        
        try {
            // Use the centralized star manager for API calls
            if (window.starManager) {
                console.log('🎭 Using star manager for API call');
                if (newStarredState) {
                    await window.starManager.addStar(this.paper.paper_id);
                } else {
                    await window.starManager.removeStar(this.paper.paper_id);
                }
                
                // Update the specific button that was clicked
                window.starManager.updateStarButton(starButton, newStarredState);
                
                // Update all other star buttons for this paper
                console.log('🎭 Calling updateAllStarButtons');
                window.starManager.updateAllStarButtons(this.paper.paper_id, newStarredState);
            } else {
                console.error('🎭 Star manager not available!');
            }
        } catch (error) {
            console.error('Failed to toggle star in modal:', error);
            // Revert to original state on error
            if (window.starManager) {
                window.starManager.updateStarButton(starButton, isCurrentlyStarred);
            }
        }
    }

    createBody() {
        const body = document.createElement('div');
        body.className = 'modal-body';
        
        if (this.paper.summary) {
            const summary = this.paper.summary;
            
            const summaryContent = this.createSummaryContent(summary);
            body.appendChild(summaryContent);
        } else {
            const noSummaryMsg = document.createElement('p');
            noSummaryMsg.textContent = 'No summary available for this paper.';
            body.appendChild(noSummaryMsg);
        }
        
        return body;
    }

    createFooter() {
        const footer = document.createElement('div');
        footer.className = 'modal-footer';
        
        // Add AI model info if available
        if (this.paper.summary && this.paper.summary.model) {
            const modelInfo = this.createModelInfo(this.paper.summary.model);
            footer.appendChild(modelInfo);
        }
        
        return footer;
    }

    createModalRelevanceTag(score) {
        const tagContainer = document.createElement('div');
        const tag = document.createElement('div');
        
        tagContainer.className = 'relevance-tag-container';
        tag.className = 'relevance-tag';
        
        // Handle score 0 (error case)
        if (score === 0 || score === null || score === undefined) {
            tag.className = 'relevance-tag score-0';
            const scoreText = document.createElement('span');
            scoreText.textContent = '-';
            tag.appendChild(scoreText);
        } else {
            // Add CSS class based on score
            tag.className = `relevance-tag score-${score}`;
            const scoreText = document.createElement('span');
            scoreText.textContent = score;
            tag.appendChild(scoreText);
        }
        
        tagContainer.appendChild(tag);
        return tagContainer;
    }

    createSummaryContent(summary) {
        const container = document.createElement('div');
        container.className = 'summary-content';
        
        // Overview section
        if (summary.overview) {
            const overviewSection = document.createElement('div');
            overviewSection.className = 'summary-section';
            
            const overviewTitle = document.createElement('h3');
            overviewTitle.textContent = '📋 Overview';
            overviewSection.appendChild(overviewTitle);
            
            const overviewContent = document.createElement('p');
            overviewContent.textContent = summary.overview;
            overviewSection.appendChild(overviewContent);
            
            container.appendChild(overviewSection);
        }
        
        // Motivation section
        if (summary.motivation) {
            const motivationSection = document.createElement('div');
            motivationSection.className = 'summary-section';
            
            const motivationTitle = document.createElement('h3');
            motivationTitle.textContent = '🎯 Motivation';
            motivationSection.appendChild(motivationTitle);
            
            const motivationContent = document.createElement('p');
            motivationContent.textContent = summary.motivation;
            motivationSection.appendChild(motivationContent);
            
            container.appendChild(motivationSection);
        }
        
        // Method section
        if (summary.method) {
            const methodSection = document.createElement('div');
            methodSection.className = 'summary-section';
            
            const methodTitle = document.createElement('h3');
            methodTitle.textContent = '🔬 Method';
            methodSection.appendChild(methodTitle);
            
            const methodContent = document.createElement('p');
            methodContent.textContent = summary.method;
            methodSection.appendChild(methodContent);
            
            container.appendChild(methodSection);
        }
        
        // Results section
        if (summary.result) {
            const resultSection = document.createElement('div');
            resultSection.className = 'summary-section';
            
            const resultTitle = document.createElement('h3');
            resultTitle.textContent = '📊 Results';
            resultSection.appendChild(resultTitle);
            
            const resultContent = document.createElement('p');
            resultContent.textContent = summary.result;
            resultSection.appendChild(resultContent);
            
            container.appendChild(resultSection);
        }
        
        // Conclusion section
        if (summary.conclusion) {
            const conclusionSection = document.createElement('div');
            conclusionSection.className = 'summary-section';
            
            const conclusionTitle = document.createElement('h3');
            conclusionTitle.textContent = '💡 Conclusion';
            conclusionSection.appendChild(conclusionTitle);
            
            const conclusionContent = document.createElement('p');
            conclusionContent.textContent = summary.conclusion;
            conclusionSection.appendChild(conclusionContent);
            
            container.appendChild(conclusionSection);
        }
        
        // Fallback for old format
        if (summary.tldr) {
            const tldrSection = document.createElement('div');
            tldrSection.className = 'summary-section';
            
            const tldrTitle = document.createElement('h3');
            tldrTitle.textContent = 'TL;DR';
            tldrSection.appendChild(tldrTitle);
            
            const tldrContent = document.createElement('p');
            tldrContent.textContent = summary.tldr;
            tldrSection.appendChild(tldrContent);
            
            container.appendChild(tldrSection);
        }
        
        return container;
    }

    createModelInfo(model) {
        const modelInfo = document.createElement('div');
        modelInfo.className = 'model-info';
        
        const modelText = document.createElement('p');
        // put emoji in the prefix
        const prefix = 'Generated by: 🤖';
        // Handle both string and object model formats
        if (typeof model === 'string') {
            modelText.textContent = `${prefix} ${model}`;
        } else if (model && model.name) {
            modelText.textContent = `${prefix} ${model.name} (${model.version || 'v1'})`;
        } else {
            modelText.textContent = `${prefix} AI Model`;
        }
        modelInfo.appendChild(modelText);
        
        return modelInfo;
    }

    setupEventListeners() {
        // Close modal when clicking overlay
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        });
        
        // Close modal with Escape key
        document.addEventListener('keydown', this.handleEscape);
    }

    handleEscape(e) {
        if (e.key === 'Escape') {
            this.close();
        }
    }

    close() {
        if (this.overlay && this.overlay.parentNode) {
            this.overlay.parentNode.removeChild(this.overlay);
        }
        
        // Remove event listener
        document.removeEventListener('keydown', this.handleEscape);
    }
}

// Export for use in other modules
window.ModalManager = ModalManager;
