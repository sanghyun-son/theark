// API communication module for TheArk

export class ApiService {
    constructor() {
        this.apiBaseUrl = '/v1/papers';
        this.configApiUrl = '/v1/config';
    }

    async getPapers(limit = 20, offset = 0, language = 'Korean') {
        const response = await fetch(`${this.apiBaseUrl}/lightweight?limit=${limit}&offset=${offset}&language=${language}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    async getPaperSummary(paperId, language = 'Korean') {
        const response = await fetch(`${this.apiBaseUrl}/${paperId}/summary?language=${language}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get paper summary');
        }
        
        return await response.json();
    }

    async createPaper(paperData) {
        const response = await fetch(this.apiBaseUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(paperData),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create paper');
        }

        return await response.json();
    }

    async createPaperWithStreaming(paperData) {
        const response = await fetch(`${this.apiBaseUrl}/stream-summary`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(paperData),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create paper with streaming');
        }

        return response.body;
    }

    async deletePaper(arxivId) {
        const response = await fetch(`${this.apiBaseUrl}/${arxivId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete paper');
        }

        return await response.json();
    }

    async getCategories() {
        const response = await fetch(this.configApiUrl + '/categories');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    async markSummaryAsRead(paperId, summaryId) {
        const response = await fetch(`${this.apiBaseUrl}/${paperId}/summary/${summaryId}/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to mark summary as read');
        }

        return await response.json();
    }

    async getStatistics() {
        const response = await fetch('/v1/statistics');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
}

