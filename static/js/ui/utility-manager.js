// Utility functions module for TheArk

class UtilityManager {
    constructor() {
        // Bind methods to maintain context
        this.showSuccess = this.showSuccess.bind(this);
        this.showError = this.showError.bind(this);
        this.showDeleteSuccess = this.showDeleteSuccess.bind(this);
        this.setLoadingState = this.setLoadingState.bind(this);
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
}

// Export for use in other modules
window.UtilityManager = UtilityManager;
