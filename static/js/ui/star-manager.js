// Star management module for TheArk

class StarManager {
    constructor() {
        // Bind methods to maintain context
        this.createStarButton = this.createStarButton.bind(this);
        this.updateAllStarButtons = this.updateAllStarButtons.bind(this);
        this.updateStarButton = this.updateStarButton.bind(this);
        this.addStar = this.addStar.bind(this);
        this.removeStar = this.removeStar.bind(this);
        this.toggleStar = this.toggleStar.bind(this);
        
        // Global star state tracker
        this.starStates = new Map();
    }

    // Initialize star states for papers when they are first loaded
    initializeStarStates(papers) {
        papers.forEach(paper => {
            if (!this.starStates.has(paper.paper_id)) {
                this.starStates.set(paper.paper_id, paper.is_starred || false);
            }
        });
        console.log('📚 Initialized star states for', papers.length, 'papers');
    }

    createStarButton(paper, context = 'paper-item') {
        const starButton = document.createElement('button');
        starButton.className = 'star-button';
        starButton.style.cssText = 'background: none; border: none; cursor: pointer; font-size: 1.2em; padding: 0.2em; min-width: 1.5em; text-align: center;';
        
        // Assign unique ID based on paper ID and context
        const uniqueId = `star-${paper.paper_id}-${context}`;
        starButton.id = uniqueId;
        
        // Get current star state (use global state if available, otherwise use paper's initial state)
        const currentStarState = this.starStates.has(paper.paper_id) 
            ? this.starStates.get(paper.paper_id) 
            : (paper.is_starred || false);
        
        // Set initial state based on current star state
        starButton.textContent = currentStarState ? '⭐' : '☆';
        starButton.title = currentStarState ? 'Remove from favorites' : 'Add to favorites';
        
        if (currentStarState) {
            starButton.classList.add('starred');
        }
        
        // Add click handler
        starButton.onclick = (e) => {
            e.stopPropagation();
            this.toggleStar(starButton, paper);
        };
        
        return starButton;
    }

    async toggleStar(starButton, paper) {
        console.log('⭐ toggleStar called from star manager:', { paperId: paper.paper_id });
        const isCurrentlyStarred = starButton.classList.contains('starred');
        const newStarredState = !isCurrentlyStarred;
        console.log('⭐ Star state change:', { isCurrentlyStarred, newStarredState });
        
        try {
            if (newStarredState) {
                await this.addStar(paper.paper_id);
            } else {
                await this.removeStar(paper.paper_id);
            }
            
            // Update the specific button that was clicked
            this.updateStarButton(starButton, newStarredState);
            
            // Update all other star buttons for this paper
            console.log('⭐ Calling updateAllStarButtons from toggleStar');
            this.updateAllStarButtons(paper.paper_id, newStarredState);
        } catch (error) {
            console.error('Failed to toggle star:', error);
            // Revert to original state on error
            this.updateStarButton(starButton, isCurrentlyStarred);
        }
    }

    updateAllStarButtons(paperId, isStarred) {
        try {
            console.log('🔍 updateAllStarButtons called:', { paperId, isStarred });
            
            // Update global star state tracker
            this.starStates.set(paperId, isStarred);
            console.log('💾 Updated global star state for paper', paperId, 'to', isStarred);
            
            // Update paper-item star button using unique ID
            const paperItemStarId = `star-${paperId}-paper-item`;
            const paperItemStarButton = document.getElementById(paperItemStarId);
            if (paperItemStarButton) {
                console.log('✅ Found and updating paper-item star button:', paperItemStarId);
                this.updateStarButton(paperItemStarButton, isStarred);
            } else {
                console.log('❌ Paper-item star button not found:', paperItemStarId);
            }
            
            // Update modal star button using unique ID
            const modalStarId = `star-${paperId}-modal`;
            const modalStarButton = document.getElementById(modalStarId);
            if (modalStarButton) {
                console.log('✅ Found and updating modal star button:', modalStarId);
                this.updateStarButton(modalStarButton, isStarred);
            } else {
                console.log('❌ Modal star button not found:', modalStarId);
            }
        } catch (error) {
            console.error('❌ Error in updateAllStarButtons:', error);
        }
    }

    updateStarButton(starButton, isStarred) {
        starButton.textContent = isStarred ? '⭐' : '☆';
        
        if (isStarred) {
            starButton.classList.add('starred');
        } else {
            starButton.classList.remove('starred');
        }
        
        starButton.title = isStarred ? 'Remove from favorites' : 'Add to favorites';
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
}

// Export for use in other modules
window.StarManager = StarManager;
