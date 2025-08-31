// Paper list management module for TheArk

class PaperListManager {
    constructor() {
        this.papers = [];
        
        // Bind methods to maintain context
        this.renderPaperList = this.renderPaperList.bind(this);
        this.createPaperElement = this.createPaperElement.bind(this);
        this.createTLDR = this.createTLDR.bind(this);
        this.findPaperElement = this.findPaperElement.bind(this);
        this.createRelevanceTag = this.createRelevanceTag.bind(this);
        this.renderCategories = this.renderCategories.bind(this);
        this.removePaperElement = this.removePaperElement.bind(this);
        this.addPaperElement = this.addPaperElement.bind(this);
        this.updatePaperElement = this.updatePaperElement.bind(this);
    }

    renderPaperList(papers) {
        const paperList = document.getElementById('paper-list');
        if (!paperList) return;

        // Initialize star states for all papers
        if (window.starManager) {
            window.starManager.initializeStarStates(papers);
        }

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
        
        // Add 'unread' class if paper hasn't been read
        if (!paper.is_read) {
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
        if (window.starManager) {
            const starButton = window.starManager.createStarButton(paper);
            titleRow.appendChild(starButton);
        }
        
        paperDiv.appendChild(titleRow);
        
        // Meta
        const metaDiv = document.createElement('div');
        metaDiv.className = 'paper-meta';
        
        // Handle authors - split by semicolon if it's a string
        let authorsText = paper.authors;
        if (typeof paper.authors === 'string' && paper.authors.includes(';')) {
            authorsText = paper.authors.split(';').map(author => author.trim()).join(', ');
        }
        
        metaDiv.innerHTML = `👥 ${authorsText}`;
        metaDiv.title = authorsText;
        
        paperDiv.appendChild(metaDiv);
        
        // TLDR Summary with relevance tag
        if (paper.summary) {
            const tldrContainer = document.createElement('div');
            tldrContainer.className = 'paper-tldr-container';
            
            // Add relevance tag if exists (positioned at top-left of TLDR)
            if (paper.summary.relevance !== undefined && paper.summary.relevance !== null) {
                const relevanceTag = this.createRelevanceTag(paper.summary.relevance, true);
                tldrContainer.appendChild(relevanceTag);
            }
            
            const tldrContent = this.createTLDR(paper.summary);
            tldrContainer.appendChild(tldrContent);
            
            paperDiv.appendChild(tldrContainer);
        }
        
        // Categories
        if (paper.categories && paper.categories.trim()) {
            const categoriesDiv = this.renderCategories(paper.categories);
            paperDiv.appendChild(categoriesDiv);
        } else {
            // Create empty categories container for delete button positioning
            const categoriesDiv = document.createElement('div');
            categoriesDiv.className = 'paper-categories';
            paperDiv.appendChild(categoriesDiv);
        }
        
        // Add delete button at the bottom-right
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.innerHTML = '🗑️';
        deleteBtn.title = 'Delete paper';
        deleteBtn.onclick = (e) => {
            e.stopPropagation(); // Prevent modal from opening
            if (window.paperManager) {
                window.paperManager.deletePaper(paper.arxiv_id);
            } else {
                console.error('PaperManager not initialized');
            }
        };
        paperDiv.appendChild(deleteBtn);
        
        // Add click handler for modal
        paperDiv.addEventListener('click', (e) => {
            // Don't open modal if clicking on links, star button, or delete button
            if (e.target.closest('.paper-link') || e.target.closest('.star-button') || e.target.closest('.delete-btn')) {
                return;
            }
            
            // Use the showSummaryModal method for proper handling
            this.showSummaryModal(paper);
        });
        
        return paperDiv;
    }

    createTLDR(summary) {
        const tldrDiv = document.createElement('div');
        tldrDiv.className = 'paper-tldr korean-text clickable';
        
        let tldrText = '';
        
        // Try different fields in order of preference
        if (summary.overview) {
            tldrText = summary.overview;
        } else if (summary.motivation) {
            tldrText = summary.motivation;
        } else if (summary.conclusion) {
            tldrText = summary.conclusion;
        } else if (summary.tldr) {
            tldrText = summary.tldr;
        } else if (summary.summary) {
            tldrText = summary.summary;
        } else {
            tldrText = 'No summary available.';
        }
        
        tldrDiv.title = tldrText;
        if (tldrText.length > 200) {
            tldrText = tldrText.substring(0, 197) + '...';
        }
        
        tldrDiv.textContent = tldrText;
        return tldrDiv;
    }

    findPaperElement(arxivId) {
        const paperElements = document.querySelectorAll('.paper-item');
        for (const element of paperElements) {
            const idSpan = element.querySelector('.paper-id');
            if (idSpan && idSpan.textContent === `[${arxivId}]`) {
                return element;
            }
        }
        return null;
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
            scoreText.textContent = score;
            tag.appendChild(scoreText);
        }
        
        tagContainer.appendChild(tag);
        return tagContainer;
    }

    renderCategories(categories) {
        const categoriesDiv = document.createElement('div');
        categoriesDiv.className = 'paper-categories';
        
        // Handle both string (comma-separated) and array formats
        let categoryList;
        if (typeof categories === 'string') {
            categoryList = categories.split(',').map(cat => cat.trim()).filter(cat => cat);
        } else if (Array.isArray(categories)) {
            categoryList = categories;
        } else {
            console.warn('Invalid categories format:', categories);
            return categoriesDiv;
        }
        
        categoryList.forEach(category => {
            const categorySpan = document.createElement('span');
            categorySpan.className = 'paper-category';
            categorySpan.textContent = category;
            categoriesDiv.appendChild(categorySpan);
        });
        
        return categoriesDiv;
    }

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

        const paperList = document.getElementById('paper-list');
        if (!paperList) return;

        const paperElement = this.createPaperElement(paperData);
        
        // Insert at the beginning of the list
        if (paperList.firstChild) {
            paperList.insertBefore(paperElement, paperList.firstChild);
        } else {
            paperList.appendChild(paperElement);
        }
    }

    updatePaperElement(arxivId, paperData) {
        const existingElement = this.findPaperElement(arxivId);
        if (existingElement) {
            const newElement = this.createPaperElement(paperData);
            existingElement.parentNode.replaceChild(newElement, existingElement);
        }
    }

    async showSummaryModal(paper) {
        // Create and show modal
        if (window.ModalManager) {
            const modal = new window.ModalManager(paper);
            modal.show();
        }
        
        // Mark summary as read if it exists and hasn't been read
        if (paper.summary && paper.summary.summary_id && !paper.is_read) {
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
                paper.is_read = true;
                
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
}

// Export for use in other modules
window.PaperListManager = PaperListManager;
