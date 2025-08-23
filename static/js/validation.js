// Validation module for TheArk

class ValidationService {
    static isValidArxivUrl(url) {
        const arxivPattern = /^https?:\/\/arxiv\.org\/(abs|pdf)\/\d{4}\.\d{5}$/;
        return arxivPattern.test(url);
    }

    static validatePaperUrl(url) {
        if (!url || url.trim() === '') {
            return { isValid: false, message: 'Please enter a paper URL' };
        }

        if (!this.isValidArxivUrl(url.trim())) {
            return { 
                isValid: false, 
                message: 'Please enter a valid arXiv URL (e.g., https://arxiv.org/abs/2508.01234)' 
            };
        }

        return { isValid: true, message: '' };
    }

    static validatePaperData(paperData) {
        const requiredFields = ['url', 'summarize_now', 'summary_language'];
        
        for (const field of requiredFields) {
            if (paperData[field] === undefined || paperData[field] === null) {
                return { isValid: false, message: `Missing required field: ${field}` };
            }
        }

        const urlValidation = this.validatePaperUrl(paperData.url);
        if (!urlValidation.isValid) {
            return urlValidation;
        }

        return { isValid: true, message: '' };
    }
}

// Export for use in other modules
window.ValidationService = ValidationService;
