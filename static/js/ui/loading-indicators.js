// Loading indicators module for TheArk

class LoadingIndicators {
    constructor() {
        // Bind methods to maintain context
        this.showLoadingIndicator = this.showLoadingIndicator.bind(this);
        this.showLoadMoreButton = this.showLoadMoreButton.bind(this);
        this.showRefreshButton = this.showRefreshButton.bind(this);
        this.showErrorIndicator = this.showErrorIndicator.bind(this);
        this.hideBottomIndicator = this.hideBottomIndicator.bind(this);
        this.hideLoadingIndicator = this.hideLoadingIndicator.bind(this);
    }

    showLoadingIndicator(message = '⏳ Loading more papers...') {
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) return;

        // Remove existing bottom indicator
        this.hideBottomIndicator();

        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'bottom-indicator';
        loadingDiv.style.cssText = 'text-align: center; padding: 1rem; color: #666;';
        loadingDiv.innerHTML = message;
        paginationElement.appendChild(loadingDiv);
    }

    showLoadMoreButton() {
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) return;

        // Remove existing bottom indicator
        this.hideBottomIndicator();

        const loadMoreDiv = document.createElement('div');
        loadMoreDiv.id = 'bottom-indicator';
        loadMoreDiv.style.cssText = 'text-align: center;';
        
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.className = 'btn btn-secondary';
        loadMoreBtn.innerHTML = '📄 Load More Papers';
        loadMoreBtn.onclick = () => {
            if (window.paperManager && window.paperManager.infiniteScrollService) {
                window.paperManager.infiniteScrollService.loadMorePapers();
            }
        };
        
        loadMoreDiv.appendChild(loadMoreBtn);
        paginationElement.appendChild(loadMoreDiv);
    }

    showRefreshButton() {
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) return;

        // Remove existing bottom indicator
        this.hideBottomIndicator();

        const refreshDiv = document.createElement('div');
        refreshDiv.id = 'bottom-indicator';
        refreshDiv.style.cssText = 'text-align: center; color: #666;';

        const wrapper = document.createElement("div");
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "center";
        wrapper.style.justifyContent = "center";  // 가운데 정렬
        wrapper.style.gap = "10px";
        wrapper.style.cursor = "pointer";
        wrapper.style.userSelect = "none";        // 텍스트 드래그 방지 (선택적)

        wrapper.onclick = () => window.paperManager.loadPapers();

        const leftIcon = document.createElement("span");
        leftIcon.textContent = "🔄";
        leftIcon.style.fontSize = "1.2rem";

        const msg = document.createElement("span");
        msg.textContent = "All papers loaded";
        msg.style.fontSize = "1rem";

        const rightIcon = document.createElement("span");
        rightIcon.textContent = "🔄";
        rightIcon.style.fontSize = "1.2rem";

        wrapper.appendChild(leftIcon);
        wrapper.appendChild(msg);
        wrapper.appendChild(rightIcon);

        refreshDiv.appendChild(wrapper);
        paginationElement.appendChild(refreshDiv);
    }

    showErrorIndicator(message) {
        const paginationElement = document.getElementById('pagination');
        if (!paginationElement) return;

        // Remove existing bottom indicator
        this.hideBottomIndicator();

        const errorDiv = document.createElement('div');
        errorDiv.id = 'bottom-indicator';
        errorDiv.style.cssText = 'text-align: center; padding: 1rem; color: #d32f2f;';
        errorDiv.innerHTML = `
            <p style="margin-bottom: 1rem;">${message}</p>
            <button class="btn btn-secondary" onclick="window.paperManager.loadPapers()">
                🔄 Try Again
            </button>
        `;
        paginationElement.appendChild(errorDiv);
    }

    hideBottomIndicator() {
        const bottomIndicator = document.getElementById('bottom-indicator');
        if (bottomIndicator) {
            bottomIndicator.remove();
        }
    }

    // Legacy method for backward compatibility
    hideLoadingIndicator() {
        this.hideBottomIndicator();
    }
}

// Export for use in other modules
window.LoadingIndicators = LoadingIndicators;
