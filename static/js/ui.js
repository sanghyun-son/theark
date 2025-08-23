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
        
        // Title with links on the left
        const titleRow = document.createElement('div');
        titleRow.style.display = 'flex';
        titleRow.style.alignItems = 'flex-start';
        titleRow.style.gap = '0.5rem';
        
        // Links
        const linksDiv = document.createElement('div');
        linksDiv.className = 'paper-links';
        linksDiv.style.flexShrink = '0';
        linksDiv.style.display = 'flex';
        linksDiv.style.alignItems = 'center';
        linksDiv.style.gap = '0.25rem';
        linksDiv.style.marginTop = '0.1rem';
        
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
        titleDiv.style.flex = '1';
        titleDiv.style.marginBottom = '0';
        
        const idSpan = document.createElement('span');
        idSpan.style.color = '#666';
        idSpan.style.fontWeight = 'normal';
        idSpan.style.marginRight = '0.5rem';
        idSpan.textContent = `[${paper.arxiv_id}]`;
        
        const titleText = document.createElement('span');
        titleText.textContent = paper.title;
        titleText.title = paper.title;
        
        titleDiv.appendChild(idSpan);
        titleDiv.appendChild(titleText);
        titleRow.appendChild(titleDiv);
        
        paperDiv.appendChild(titleRow);
        
        // Meta
        const metaDiv = document.createElement('div');
        metaDiv.className = 'paper-meta';
        const publishedDate = paper.published_date ? new Date(paper.published_date).toLocaleDateString() : 'N/A';
        metaDiv.innerHTML = `📅 ${publishedDate} | 👥 ${paper.authors.join(', ')}`;
        metaDiv.title = paper.authors.join(', ');
        
        // Create container for meta and delete button
        const metaContainer = document.createElement('div');
        metaContainer.style.display = 'flex';
        metaContainer.style.justifyContent = 'space-between';
        metaContainer.style.alignItems = 'center';
        
        metaContainer.appendChild(metaDiv);
        
        paperDiv.appendChild(metaContainer);
        
        // TLDR Summary
        if (paper.summary) {
            const tldrDiv = document.createElement('div');
            tldrDiv.className = 'paper-tldr';
            tldrDiv.textContent = this.createTLDR(paper.summary);
            tldrDiv.onclick = () => this.showSummaryModal(paper);
            paperDiv.appendChild(tldrDiv);
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
        
        // Truncate to one line (approximately 100 characters)
        if (tldr.length > 100) {
            tldr = tldr.substring(0, 97) + '...';
        }
        
        return tldr || 'No summary available';
    }

    showSummaryModal(paper) {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        
        // Create modal content
        const modal = document.createElement('div');
        modal.className = 'modal-content';
        
        // Modal header
        const header = document.createElement('div');
        header.className = 'modal-header';
        
        const title = document.createElement('div');
        title.className = 'modal-title';
        title.textContent = paper.title;
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close';
        closeBtn.textContent = '×';
        closeBtn.onclick = () => document.body.removeChild(overlay);
        
        header.appendChild(title);
        header.appendChild(closeBtn);
        
        // Modal body
        const body = document.createElement('div');
        body.className = 'modal-body';
        
        if (paper.summary) {
            const summary = paper.summary;
            body.innerHTML = `
                <h3>📋 Overview</h3>
                <p>${summary.overview || 'Not available'}</p>
                
                <h3>🎯 Motivation</h3>
                <p>${summary.motivation || 'Not available'}</p>
                
                <h3>🔬 Method</h3>
                <p>${summary.method || 'Not available'}</p>
                
                <h3>📊 Results</h3>
                <p>${summary.result || 'Not available'}</p>
                
                <h3>💡 Conclusion</h3>
                <p>${summary.conclusion || 'Not available'}</p>
                
                <h3>⭐ Relevance</h3>
                <p>${summary.relevance || 'Not available'}</p>
                
                ${summary.relevance_score ? `<p><strong>Relevance Score:</strong> ${summary.relevance_score}/10</p>` : ''}
            `;
        } else {
            body.innerHTML = '<p>No summary available for this paper.</p>';
        }
        
        modal.appendChild(header);
        modal.appendChild(body);
        overlay.appendChild(modal);
        
        // Close on overlay click
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
            }
        };
        
        // Close on Escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                document.body.removeChild(overlay);
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
        
        document.body.appendChild(overlay);
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
            
            // Update the specific paper's summary immediately
            if (result && result.arxiv_id) {
                this.updatePaperElement(result.arxiv_id, result);
            }
        } else {
            queueBtn.innerHTML = '✅ Queued!';
            setTimeout(() => {
                queueBtn.innerHTML = '📋';
            }, 2000);
        }
        
        // Reload papers after successful submission
        if (window.paperManager) {
            window.paperManager.loadPapers();
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
        const summarizeBtn = document.getElementById('summarize-btn');
        const queueBtn = document.getElementById('queue-btn');
        const urlInput = document.getElementById('paper-url');

        if (loading) {
            if (summarizeNow) {
                summarizeBtn.disabled = true;
                summarizeBtn.innerHTML = '<span class="loading"></span>⏳';
            } else {
                queueBtn.disabled = true;
                queueBtn.innerHTML = '<span class="loading"></span>⏳';
            }
            urlInput.disabled = true;
        } else {
            summarizeBtn.disabled = false;
            queueBtn.disabled = false;
            summarizeBtn.innerHTML = '⚡';
            queueBtn.innerHTML = '📋';
            urlInput.disabled = false;
        }
    }

    updateButtonStatus(message) {
        const summarizeBtn = document.getElementById('summarize-btn');
        if (summarizeBtn) {
            summarizeBtn.innerHTML = `⏳ ${message}`;
        }
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

    updatePaperElement(arxivId, paperData) {
        // Find the paper element by arXiv ID
        const paperElements = document.querySelectorAll('.paper-item');
        
        for (const paperElement of paperElements) {
            // Find the arXiv ID in the title (it's in the format [arxivId] title)
            const titleElement = paperElement.querySelector('.paper-title');
            if (titleElement && titleElement.textContent.includes(`[${arxivId}]`)) {
                // Remove loading indicator if exists
                const loadingElement = paperElement.querySelector('.summary-loading');
                if (loadingElement) {
                    loadingElement.remove();
                }
                
                // Update the TLDR summary if it exists
                let tldrElement = paperElement.querySelector('.paper-tldr');
                
                if (paperData.summary) {
                    if (tldrElement) {
                        // Update existing TLDR
                        tldrElement.textContent = this.createTLDR(paperData.summary);
                    } else {
                        // Create new TLDR element
                        tldrElement = document.createElement('div');
                        tldrElement.className = 'paper-tldr';
                        tldrElement.textContent = this.createTLDR(paperData.summary);
                        tldrElement.onclick = () => this.showSummaryModal(paperData);
                        
                        // Insert before categories
                        const categoriesContainer = paperElement.querySelector('.paper-categories').parentElement;
                        paperElement.insertBefore(tldrElement, categoriesContainer);
                    }
                }
                break;
            }
        }
    }
}

// Export for use in other modules
window.UIService = UIService;
