// UI rendering module for TheArk

class UIService {
    constructor() {
        this.papers = [];
    }

    renderPaperList(papers) {
        const paperList = document.getElementById('paper-list');
        if (!paperList) return;

        paperList.innerHTML = '';
        papers.forEach(paper => {
            const paperElement = this.createPaperElement(paper);
            paperList.appendChild(paperElement);
        });

        // Remove pagination for infinite scroll
        const paginationElement = document.getElementById('pagination');
        if (paginationElement) {
            paginationElement.innerHTML = '';
        }
    }

    createPaperElement(paper) {
        const paperDiv = document.createElement('div');
        paperDiv.className = 'paper-item';
        
        // Add 'unread' class if summary exists and hasn't been read
        // or paper.summary is null
        if ((paper.summary && !paper.summary.is_read) || !paper.summary) {
            paperDiv.classList.add('unread');
        }
        
        // Title row with links, title, and star button
        const titleRow = document.createElement('div');
        titleRow.className = 'paper-title-row';
        
        // Links
        const linksDiv = document.createElement('div');
        linksDiv.className = 'paper-links';
        
        const pdfLink = document.createElement('a');
        pdfLink.href = paper.pdf_url;
        pdfLink.target = '_blank';
        pdfLink.className = 'paper-link';
        pdfLink.textContent = '📄';
        linksDiv.appendChild(pdfLink);
        
        const arxivLink = document.createElement('a');
        arxivLink.href = `https://arxiv.org/abs/${paper.arxiv_id}`;
        arxivLink.target = '_blank';
        arxivLink.className = 'paper-link';
        arxivLink.textContent = '🔗';
        linksDiv.appendChild(arxivLink);
        
        titleRow.appendChild(linksDiv);
        
        // Title with ID
        const titleDiv = document.createElement('div');
        titleDiv.className = 'paper-title';
        
        const idSpan = document.createElement('span');
        idSpan.className = 'paper-id';
        idSpan.textContent = `[${paper.arxiv_id}]`;
        
        const titleText = document.createElement('span');
        titleText.className = 'paper-title-text';
        titleText.textContent = paper.title;
        titleText.title = paper.title;
        
        titleDiv.appendChild(idSpan);
        titleDiv.appendChild(titleText);
        titleRow.appendChild(titleDiv);
        
        // Star button (fixed width)
        const starButton = this.createStarButton(paper);
        titleRow.appendChild(starButton);
        
        paperDiv.appendChild(titleRow);
        
        // Meta
        const metaDiv = document.createElement('div');
        metaDiv.className = 'paper-meta';
        metaDiv.innerHTML = `👥 ${paper.authors.join(', ')}`;
        metaDiv.title = paper.authors.join(', ');
        
        // Create container for meta and delete button
        const metaContainer = document.createElement('div');
        metaContainer.style.display = 'flex';
        metaContainer.style.justifyContent = 'space-between';
        metaContainer.style.alignItems = 'center';
        
        metaContainer.appendChild(metaDiv);
        
        paperDiv.appendChild(metaContainer);
        
        // TLDR Summary with relevance tag
        if (paper.summary) {
            const tldrContainer = document.createElement('div');
            tldrContainer.className = 'tldr-container';
            tldrContainer.style.position = 'relative';
            
            // Add relevance tag if exists
            if (paper.summary.relevance !== undefined && paper.summary.relevance !== null) {
                const relevanceTag = this.createRelevanceTag(paper.summary.relevance, true);
                tldrContainer.appendChild(relevanceTag);
            }
            
            const tldrDiv = document.createElement('div');
            tldrDiv.className = 'paper-tldr korean-text';
            tldrDiv.textContent = this.createTLDR(paper.summary);
            tldrDiv.onclick = () => this.showSummaryModal(paper);
            tldrContainer.appendChild(tldrDiv);
            
            paperDiv.appendChild(tldrContainer);
        }
        
        // Categories and delete button container
        const categoriesContainer = document.createElement('div');
        categoriesContainer.style.display = 'flex';
        categoriesContainer.style.justifyContent = 'space-between';
        categoriesContainer.style.alignItems = 'center';
        
        // Categories
        const categoriesDiv = document.createElement('div');
        categoriesDiv.className = 'paper-categories';
        paper.categories.forEach(cat => {
            const categorySpan = document.createElement('span');
            categorySpan.className = 'paper-category';
            categorySpan.textContent = cat;
            categoriesDiv.appendChild(categorySpan);
        });
        categoriesContainer.appendChild(categoriesDiv);
        
        // Delete button - positioned on the right next to categories
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.innerHTML = '🗑️';
        deleteBtn.title = 'Delete paper';
        deleteBtn.style.cssText = 'background: none; border: none; cursor: pointer; font-size: 1rem; padding: 0.25rem; color: #666; transition: color 0.2s ease; flex-shrink: 0;';
        deleteBtn.onmouseover = () => deleteBtn.style.color = '#ff4444';
        deleteBtn.onmouseout = () => deleteBtn.style.color = '#666';
        deleteBtn.onclick = () => {
            if (window.paperManager) {
                window.paperManager.deletePaper(paper.arxiv_id);
            } else {
                console.error('PaperManager not initialized');
            }
        };
        categoriesContainer.appendChild(deleteBtn);
        
        paperDiv.appendChild(categoriesContainer);
        
        return paperDiv;
    }

    createTLDR(summary) {
        if (!summary) return '';
        
        let tldr = '';
        if (summary.overview) {
            tldr = summary.overview;
        } else if (summary.motivation) {
            tldr = summary.motivation;
        } else if (summary.conclusion) {
            tldr = summary.conclusion;
        }
        
        // Truncate to one line (approximately 200 characters for more content)
        if (tldr.length > 200) {
            tldr = tldr.substring(0, 197) + '...';
        }
        
        return tldr || 'No summary available';
    }

    async showSummaryModal(paper) {
        const modal = new SummaryModal(paper);
        modal.show();
        
        // Mark summary as read if it exists and hasn't been read
        if (paper.summary && paper.summary.summary_id && !paper.summary.is_read) {
            try {
                const response = await fetch(`/v1/papers/${paper.paper_id}/summary/${paper.summary.summary_id}/read`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to mark summary as read');
                }

                await response.json();
                
                // Update the paper's read status locally
                paper.summary.is_read = true;
                
                // Update the UI to remove 'unread' styling
                const paperElement = this.findPaperElement(paper.arxiv_id);
                if (paperElement) {
                    paperElement.classList.remove('unread');
                }
            } catch (error) {
                console.error('Failed to mark summary as read:', error);
            }
        }
    }

    findPaperElement(arxivId) {
        const paperElements = document.querySelectorAll('.paper-item');
        
        for (const paperElement of paperElements) {
            const idSpan = paperElement.querySelector('.paper-title span');
            if (idSpan && idSpan.textContent === `[${arxivId}]`) {
                return paperElement;
            }
        }
        
        return null;
    }

    createStarButton(paper) {
        const starButton = document.createElement('button');
        starButton.className = 'star-button';
        
        // Set initial state based on paper data
        const isStarred = paper.is_starred || false;
        starButton.textContent = isStarred ? '⭐' : '☆';
        starButton.title = isStarred ? 'Remove from favorites' : 'Add to favorites';
        
        if (isStarred) {
            starButton.classList.add('starred');
        }
        
        // Add click handler
        starButton.onclick = (e) => {
            e.stopPropagation(); // Prevent triggering other click events
            this.toggleStar(paper, starButton);
        };
        
        return starButton;
    }

    async toggleStar(paper, starButton) {
        try {
            const isCurrentlyStarred = starButton.textContent === '⭐';
            
            if (isCurrentlyStarred) {
                // Remove star
                await this.removeStar(paper.paper_id);
                starButton.textContent = '☆';
                starButton.classList.remove('starred');
                starButton.title = 'Add to favorites';
                paper.is_starred = false;
            } else {
                // Add star
                await this.addStar(paper.paper_id);
                starButton.textContent = '⭐';
                starButton.classList.add('starred');
                starButton.title = 'Remove from favorites';
                paper.is_starred = true;
            }
        } catch (error) {
            console.error('Failed to toggle star:', error);
            // Revert visual state on error
            const isCurrentlyStarred = starButton.textContent === '⭐';
            if (isCurrentlyStarred) {
                starButton.textContent = '☆';
                starButton.classList.remove('starred');
                starButton.title = 'Add to favorites';
            } else {
                starButton.textContent = '⭐';
                starButton.classList.add('starred');
                starButton.title = 'Remove from favorites';
            }
        }
    }

    async addStar(paperId) {
        const response = await fetch(`/v1/papers/${paperId}/star`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ note: null }),
        });

        if (!response.ok) {
            throw new Error('Failed to add star');
        }

        return await response.json();
    }

    async removeStar(paperId) {
        const response = await fetch(`/v1/papers/${paperId}/star`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error('Failed to remove star');
        }

        return await response.json();
    }

    createRelevanceTag(score, isPaper = false) {
        const tagContainer = document.createElement('div');
        const tag = document.createElement('div');
        
        // Set CSS classes based on type
        const containerClass = isPaper ? 'paper-relevance-tag-container' : 'relevance-tag-container';
        const tagClass = isPaper ? 'paper-relevance-tag' : 'relevance-tag';
        
        tagContainer.className = containerClass;
        
        // Handle score 0 (error case)
        if (score === 0 || score === null || score === undefined) {
            tag.className = `${tagClass} score-0`;
            const scoreText = document.createElement('span');
            scoreText.textContent = '-';
            tag.appendChild(scoreText);
        } else {
            // Add CSS class based on score
            tag.className = `${tagClass} score-${score}`;
            const scoreText = document.createElement('span');
            scoreText.textContent = score.toString();
            tag.appendChild(scoreText);
        }
        
        tagContainer.appendChild(tag);
        
        return tagContainer;
    }

    renderCategories(categories) {
        const categoryButtons = document.getElementById('category-buttons');
        if (!categoryButtons) return;

        categoryButtons.innerHTML = '';
        categories.forEach(category => {
            const button = document.createElement('button');
            button.className = 'category-btn active';
            button.textContent = category;
            button.onclick = (event) => {
                if (window.paperManager) {
                    window.paperManager.toggleCategory(category, event);
                } else {
                    console.error('PaperManager not initialized');
                }
            };
            categoryButtons.appendChild(button);
        });
    }

    showLoadingIndicator() {
        const paperList = document.getElementById('paper-list');
        if (!paperList) return;

        // Remove existing loading indicator
        this.hideLoadingIndicator();

        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'loading-indicator';
        loadingDiv.style.cssText = 'text-align: center; padding: 1rem; color: #666;';
        loadingDiv.innerHTML = '⏳ Loading more papers...';
        paperList.appendChild(loadingDiv);
    }

    hideLoadingIndicator() {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }

    showSuccess(summarizeNow, result) {
        // Update button text to show success
        const summarizeBtn = document.getElementById('summarize-btn');
        const queueBtn = document.getElementById('queue-btn');
        
        if (summarizeNow) {
            summarizeBtn.innerHTML = '✅ Success!';
            setTimeout(() => {
                summarizeBtn.innerHTML = '⚡';
            }, 2000);
            
            // For streaming, the paper handling is done in handleStreamingData
            // This is just for button state update
            console.log('Streaming success for paper:', result?.arxiv_id);
        } else {
            queueBtn.innerHTML = '✅ Queued!';
            setTimeout(() => {
                queueBtn.innerHTML = '📋';
            }, 2000);
            
            // For queued papers, reload the list to show the new paper
            if (window.paperManager) {
                window.paperManager.loadPapers();
            }
        }
    }

    showError(message, summarizeNow = false) {
        // Update button text to show error
        const summarizeBtn = document.getElementById('summarize-btn');
        const queueBtn = document.getElementById('queue-btn');
        
        summarizeBtn.innerHTML = '❌ Error';
        setTimeout(() => {
            summarizeBtn.innerHTML = '⚡';
        }, 3000);
    }

    showDeleteSuccess(arxivId) {
        // Show a temporary success message
        const message = document.createElement('div');
        message.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #4CAF50; color: white; padding: 1rem; border-radius: 4px; z-index: 1000;';
        message.textContent = `✅ Paper ${arxivId} deleted successfully`;
        document.body.appendChild(message);
        
        setTimeout(() => {
            if (document.body.contains(message)) {
                document.body.removeChild(message);
            }
        }, 3000);
    }

    setLoadingState(loading, summarizeNow) {
        // 로딩 상태를 표시하지 않고 버튼을 비활성화하지 않음
        // 사용자가 연속으로 제출할 수 있도록 함
        return;
    }

    // updateButtonStatus method removed - no longer needed for concurrent submissions

    removePaperElement(arxivId) {
        const paperElements = document.querySelectorAll('.paper-item');
        for (const element of paperElements) {
            const idSpan = element.querySelector('.paper-title span');
            if (idSpan && idSpan.textContent === `[${arxivId}]`) {
                element.remove();
                break;
            }
        }
    }

    addPaperElement(paperData) {
        // Ensure DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.addPaperElement(paperData);
            });
            return;
        }
        
        // Create the paper element
        const paperElement = this.createPaperElement(paperData);
        
        // Add it to the beginning of the papers container
        const papersContainer = document.getElementById('paper-list');
        
        if (papersContainer && paperElement) {
            // Insert at the beginning
            papersContainer.insertBefore(paperElement, papersContainer.firstChild);
            

        }
    }

    updatePaperElement(arxivId, paperData) {
        // Find the paper element by arXiv ID
        const paperElements = document.querySelectorAll('.paper-item');
        
        for (const paperElement of paperElements) {
            // Find the arXiv ID in the idSpan within the title
            const idSpan = paperElement.querySelector('.paper-title span');
            
            if (idSpan && idSpan.textContent === `[${arxivId}]`) {
                // Remove loading indicator if exists
                const loadingElement = paperElement.querySelector('.summary-loading');
                if (loadingElement) {
                    loadingElement.remove();
                }
                
                // Update 'unread' class on the paper item based on is_read status
                if (paperData.summary && !paperData.summary.is_read) {
                    paperElement.classList.add('unread');
                } else {
                    paperElement.classList.remove('unread');
                }
                
                // Update the TLDR summary if it exists
                let tldrContainer = paperElement.querySelector('.tldr-container');
                let tldrElement = paperElement.querySelector('.paper-tldr');
                
                if (paperData.summary) {
                    if (tldrElement) {
                        // Update existing TLDR
                        tldrElement.textContent = this.createTLDR(paperData.summary);
                        
                        // Update relevance tag if exists
                        const existingRelevanceTag = tldrContainer.querySelector('.paper-relevance-tag-container');
                        if (existingRelevanceTag) {
                            existingRelevanceTag.remove();
                        }
                        
                        if (paperData.summary.relevance !== undefined && paperData.summary.relevance !== null) {
                            const relevanceTag = this.createRelevanceTag(paperData.summary.relevance, true);
                            tldrContainer.insertBefore(relevanceTag, tldrElement);
                        }
                    } else {
                        // Create new TLDR container and element
                        tldrContainer = document.createElement('div');
                        tldrContainer.className = 'tldr-container';
                        tldrContainer.style.position = 'relative';
                        
                        // Add relevance tag if exists
                        if (paperData.summary.relevance !== undefined && paperData.summary.relevance !== null) {
                            const relevanceTag = this.createRelevanceTag(paperData.summary.relevance, true);
                            tldrContainer.appendChild(relevanceTag);
                        }
                        
                        tldrElement = document.createElement('div');
                        tldrElement.className = 'paper-tldr korean-text';
                        tldrElement.textContent = this.createTLDR(paperData.summary);
                        tldrElement.onclick = () => this.showSummaryModal(paperData);
                        tldrContainer.appendChild(tldrElement);
                        
                        // Insert before categories
                        const categoriesContainer = paperElement.querySelector('.paper-categories').parentElement;
                        paperElement.insertBefore(tldrContainer, categoriesContainer);
                    }
                }
                break;
            }
        }
    }
}

// SummaryModal class for object-based modal management
class SummaryModal {
    constructor(paper) {
        this.paper = paper;
        this.overlay = null;
        this.modal = null;
        this.handleEscape = this.handleEscape.bind(this);
    }

    show() {
        this.createModal();
        this.setupEventListeners();
        document.body.appendChild(this.overlay);
    }

    createModal() {
        // Create modal overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        
        // Create modal content
        this.modal = document.createElement('div');
        this.modal.className = 'modal-content';
        
        // Create header
        const header = this.createHeader();
        
        // Create body
        const body = this.createBody();
        
        // Create container for relevance tag and star button
        const tagContainer = this.createTagContainer();
        
        this.modal.appendChild(header);
        this.modal.appendChild(body);
        this.modal.appendChild(tagContainer);
        this.overlay.appendChild(this.modal);
    }

    createTagContainer() {
        const container = document.createElement('div');
        container.className = 'modal-tag-container';
        container.style.position = 'relative';
        container.style.width = '0';
        container.style.height = '0';
        
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
        const starButton = document.createElement('button');
        starButton.className = 'modal-star-button';
        
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
        try {
            const isCurrentlyStarred = starButton.classList.contains('starred');
            
            if (isCurrentlyStarred) {
                // Remove star
                await this.removeModalStar();
                starButton.textContent = '☆';
                starButton.classList.remove('starred');
                starButton.title = 'Add to favorites';
                this.paper.is_starred = false;
            } else {
                // Add star
                await this.addModalStar();
                starButton.textContent = '⭐';
                starButton.classList.add('starred');
                starButton.title = 'Remove from favorites';
                this.paper.is_starred = true;
            }
        } catch (error) {
            console.error('Failed to toggle star in modal:', error);
            // Revert visual state on error
            const isCurrentlyStarred = starButton.classList.contains('starred');
            if (isCurrentlyStarred) {
                starButton.textContent = '☆';
                starButton.classList.remove('starred');
                starButton.title = 'Add to favorites';
            } else {
                starButton.textContent = '⭐';
                starButton.classList.add('starred');
                starButton.title = 'Remove from favorites';
            }
        }
    }

    async addModalStar() {
        const response = await fetch(`/v1/papers/${this.paper.paper_id}/star`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ note: null }),
        });

        if (!response.ok) {
            throw new Error('Failed to add star');
        }

        return await response.json();
    }

    async removeModalStar() {
        const response = await fetch(`/v1/papers/${this.paper.paper_id}/star`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error('Failed to remove star');
        }

        return await response.json();
    }

    createBody() {
        const body = document.createElement('div');
        body.className = 'modal-body';
        
        if (this.paper.summary) {
            const summary = this.paper.summary;
            
            const summaryContent = this.createSummaryContent(summary);
            body.appendChild(summaryContent);
            
            // Add AI model info at the bottom
            if (summary.model) {
                const modelInfo = this.createModelInfo(summary.model);
                body.appendChild(modelInfo);
            }
        } else {
            const noSummaryMsg = document.createElement('p');
            noSummaryMsg.textContent = 'No summary available for this paper.';
            body.appendChild(noSummaryMsg);
        }
        
        return body;
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
            scoreText.textContent = score.toString();
            tag.appendChild(scoreText);
        }
        
        tagContainer.appendChild(tag);
        
        return tagContainer;
    }

    createSummaryContent(summary) {
        const sections = [
            { title: '📋 Overview', content: summary.overview },
            { title: '🎯 Motivation', content: summary.motivation },
            { title: '🔬 Method', content: summary.method },
            { title: '📊 Results', content: summary.result },
            { title: '💡 Conclusion', content: summary.conclusion }
        ];

        const container = document.createElement('div');
        
        sections.forEach(section => {
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'summary-section';
            
            const title = document.createElement('h3');
            title.textContent = section.title;
            
            const content = document.createElement('p');
            content.textContent = section.content || 'Not available';
            
            sectionDiv.appendChild(title);
            sectionDiv.appendChild(content);
            container.appendChild(sectionDiv);
        });

        return container;
    }



    createModelInfo(model) {
        const modelContainer = document.createElement('div');
        modelContainer.className = 'model-info-container';
        
        const modelText = document.createElement('p');
        modelText.className = 'model-info';
        modelText.innerHTML = `by 🤖 ${model}`;
        
        modelContainer.appendChild(modelText);
        
        return modelContainer;
    }

    setupEventListeners() {
        // Close on overlay click
        this.overlay.onclick = (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        };
        
        // Close on Escape key
        document.addEventListener('keydown', this.handleEscape);
    }

    handleEscape(e) {
        if (e.key === 'Escape') {
            this.close();
        }
    }

    close() {
        if (this.overlay && this.overlay.parentNode) {
            document.body.removeChild(this.overlay);
        }
        document.removeEventListener('keydown', this.handleEscape);
    }
}

// Export for use in other modules
window.UIService = UIService;
window.SummaryModal = SummaryModal;
