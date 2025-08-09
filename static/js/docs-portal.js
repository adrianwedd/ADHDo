/**
 * ADHD-Friendly Documentation Portal JavaScript
 * 
 * Features:
 * - Smooth interactions with minimal cognitive load
 * - Keyboard navigation support
 * - Progressive enhancement
 * - Clear visual feedback
 * - Error handling with user-friendly messages
 */

class DocsPortal {
    constructor() {
        this.apiData = {};
        this.currentSection = 'quick-start';
        this.searchDebounceTimer = null;
        this.preferredLanguage = 'python';
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        this.setupKeyboardNavigation();
        this.loadApiData();
        this.restoreUserPreferences();
    }
    
    setupEventListeners() {
        // Navigation tab clicks
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.showSection(e.target.getAttribute('data-section') || this.extractSectionFromOnclick(e.target));
            });
        });
        
        // Search functionality with debouncing
        const searchBox = document.getElementById('endpoint-search');
        if (searchBox) {
            searchBox.addEventListener('input', (e) => {
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = setTimeout(() => {
                    this.filterEndpoints(e.target.value);
                }, 300); // 300ms debounce for better UX
            });
        }
        
        // Language selector
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('language-selector')) {
                this.preferredLanguage = e.target.value;
                this.updateCodeExamples();
                this.saveUserPreferences();
            }
        });
        
        // Copy code button functionality
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('copy-code-btn')) {
                this.copyCodeToClipboard(e.target);
            }
        });
        
        // Try it now buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('try-it-button')) {
                const action = e.target.getAttribute('data-action');
                if (action) {
                    this.handleTryItAction(action, e.target);
                }
            }
        });
    }
    
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+K or Cmd+K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchBox = document.getElementById('endpoint-search');
                if (searchBox) {
                    searchBox.focus();
                    this.showVisualFeedback('Search focused', 'info');
                }
            }
            
            // Tab navigation between sections
            if (e.key === 'Tab' && e.shiftKey) {
                // Allow normal tab navigation
            } else if (e.key === 'Tab') {
                // Allow normal tab navigation
            }
            
            // Escape to close modals or clear search
            if (e.key === 'Escape') {
                const searchBox = document.getElementById('endpoint-search');
                if (searchBox && searchBox.value) {
                    searchBox.value = '';
                    this.filterEndpoints('');
                    this.showVisualFeedback('Search cleared', 'info');
                }
            }
        });
    }
    
    async loadApiData() {
        try {
            this.showLoadingState();
            
            const response = await fetch('/docs-portal/api/endpoints');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.apiData = await response.json();
            this.renderApiCategories(this.apiData.categories);
            this.showVisualFeedback('API documentation loaded', 'success');
            
        } catch (error) {
            console.error('Failed to load API data:', error);
            this.renderApiError(error.message);
            this.showVisualFeedback('Failed to load API data', 'error');
        }
    }
    
    showSection(sectionId) {
        // Update URL without page reload
        if (history.pushState) {
            history.pushState(null, '', `#${sectionId}`);
        }
        
        // Hide all sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Remove active class from all tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Show selected section
        const targetSection = document.getElementById(sectionId);
        const targetTab = document.querySelector(`[onclick*="${sectionId}"], [data-section="${sectionId}"]`);
        
        if (targetSection) {
            targetSection.classList.add('active');
            targetSection.classList.add('fade-in');
            this.currentSection = sectionId;
        }
        
        if (targetTab) {
            targetTab.classList.add('active');
        }
        
        // Load section-specific data
        this.loadSectionData(sectionId);
        
        // Announce to screen readers
        this.announceToScreenReader(`Switched to ${sectionId.replace('-', ' ')} section`);
    }
    
    async loadSectionData(sectionId) {
        switch (sectionId) {
            case 'examples':
                await this.loadCodeExamples();
                break;
            case 'integrations':
                await this.loadIntegrationExamples();
                break;
            default:
                // Section already has static content
                break;
        }
    }
    
    async loadCodeExamples() {
        try {
            const examplesContainer = document.getElementById('examples-content');
            if (!examplesContainer) return;
            
            examplesContainer.innerHTML = '<div class="loading">Loading code examples...</div>';
            
            // Load examples for different categories
            const categories = ['chat', 'authentication', 'health', 'tasks'];
            const examplesHtml = [];
            
            for (const category of categories) {
                try {
                    const response = await fetch(`/docs-portal/api/examples/${category}?language=${this.preferredLanguage}`);
                    if (response.ok) {
                        const data = await response.json();
                        examplesHtml.push(this.renderCategoryExamples(category, data));
                    }
                } catch (error) {
                    console.warn(`Failed to load examples for ${category}:`, error);
                }
            }
            
            examplesContainer.innerHTML = examplesHtml.join('');
            this.addCopyButtons();
            
        } catch (error) {
            console.error('Failed to load code examples:', error);
            document.getElementById('examples-content').innerHTML = 
                '<div class="error">Failed to load code examples. Please try again later.</div>';
        }
    }
    
    renderCategoryExamples(category, data) {
        const categoryIcon = this.getCategoryIcon(category);
        
        let html = `
            <div class="category-examples">
                <h3>${categoryIcon} ${this.capitalizeFirst(category)} Examples</h3>
                <div class="examples-grid">
        `;
        
        Object.entries(data.examples).forEach(([key, example]) => {
            html += `
                <div class="example-card">
                    <h4>${example.title}</h4>
                    <p class="example-description">${example.explanation}</p>
                    <div class="code-example" data-language="${data.language}">
                        <button class="copy-code-btn" title="Copy to clipboard">📋</button>
                        <pre><code>${this.escapeHtml(example.code)}</code></pre>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
                <div class="adhd-tips">
                    <h4>💡 ADHD-Friendly Tips</h4>
                    <ul>
                        ${data.adhd_tips.map(tip => `<li>${tip}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
        
        return html;
    }
    
    renderApiCategories(categories) {
        const container = document.getElementById('api-categories');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.values(categories).forEach(category => {
            const categoryCard = this.createCategoryCard(category);
            container.appendChild(categoryCard);
        });
    }
    
    createCategoryCard(category) {
        const card = document.createElement('div');
        card.className = 'category-card';
        card.setAttribute('data-category', category.name.toLowerCase());
        
        const difficultyClass = `difficulty-${category.difficulty}`;
        const responseTime = this.estimateResponseTime(category.name);
        
        card.innerHTML = `
            <div class="category-header">
                <span class="category-icon">${category.icon || this.getCategoryIcon(category.name)}</span>
                <span class="category-title">${category.name}</span>
                <span class="difficulty-badge ${difficultyClass}">${category.difficulty}</span>
            </div>
            <p class="category-description">${category.description}</p>
            <div class="category-stats">
                <span class="stat-item">
                    <strong>${category.endpoints.length}</strong> endpoints
                </span>
                <span class="stat-item">
                    <strong>${responseTime}</strong> avg response
                </span>
            </div>
            <div class="category-actions">
                <button class="try-it-button btn-primary" data-action="explore-category" data-category="${category.name}">
                    Explore Endpoints
                </button>
                <button class="try-it-button btn-success" data-action="test-category" data-category="${category.name}">
                    Try Examples
                </button>
            </div>
        `;
        
        return card;
    }
    
    filterEndpoints(searchTerm) {
        const term = searchTerm.toLowerCase().trim();
        const categoryCards = document.querySelectorAll('.category-card');
        let visibleCount = 0;
        
        categoryCards.forEach(card => {
            const title = card.querySelector('.category-title').textContent.toLowerCase();
            const description = card.querySelector('.category-description').textContent.toLowerCase();
            const category = card.getAttribute('data-category') || '';
            
            const matches = !term || 
                           title.includes(term) || 
                           description.includes(term) ||
                           category.includes(term);
            
            if (matches) {
                card.style.display = 'block';
                card.classList.add('slide-in');
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });
        
        // Show search results summary
        this.updateSearchResultsSummary(term, visibleCount);
    }
    
    updateSearchResultsSummary(term, count) {
        let summaryElement = document.querySelector('.search-results-summary');
        
        if (!summaryElement) {
            summaryElement = document.createElement('div');
            summaryElement.className = 'search-results-summary';
            const searchBox = document.getElementById('endpoint-search');
            if (searchBox && searchBox.parentNode) {
                searchBox.parentNode.insertBefore(summaryElement, searchBox.nextSibling);
            }
        }
        
        if (term) {
            summaryElement.innerHTML = `
                <p class="search-summary">
                    Found <strong>${count}</strong> ${count === 1 ? 'category' : 'categories'} 
                    matching "<em>${this.escapeHtml(term)}</em>"
                </p>
            `;
            summaryElement.style.display = 'block';
        } else {
            summaryElement.style.display = 'none';
        }
    }
    
    async handleTryItAction(action, button) {
        const originalText = button.textContent;
        const category = button.getAttribute('data-category');
        
        try {
            button.textContent = 'Testing...';
            button.disabled = true;
            
            switch (action) {
                case 'test-health':
                    await this.testHealthEndpoint();
                    break;
                case 'test-chat':
                    await this.testChatEndpoint();
                    break;
                case 'explore-category':
                    this.showCategoryDetails(category);
                    break;
                case 'test-category':
                    await this.testCategoryEndpoint(category);
                    break;
                default:
                    throw new Error(`Unknown action: ${action}`);
            }
            
            this.showVisualFeedback('Test completed successfully', 'success');
            
        } catch (error) {
            console.error('Test action failed:', error);
            this.showVisualFeedback(`Test failed: ${error.message}`, 'error');
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }
    
    async testHealthEndpoint() {
        const response = await fetch('/health');
        const data = await response.json();
        
        this.showResultModal('Health Check Result', {
            status: data.status,
            timestamp: data.timestamp,
            details: JSON.stringify(data, null, 2)
        });
    }
    
    async testChatEndpoint() {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: "Hello! This is a test message from the documentation portal.",
                context: { source: "docs_portal_test" }
            })
        });
        
        const data = await response.json();
        
        this.showResultModal('Chat Test Result', {
            response: data.response,
            processing_time: data.processing_time || 'N/A',
            safety_level: data.safety_level || 'N/A',
            details: JSON.stringify(data, null, 2)
        });
    }
    
    showCategoryDetails(categoryName) {
        const category = Object.values(this.apiData.categories || {})
            .find(cat => cat.name === categoryName);
        
        if (!category) {
            this.showVisualFeedback('Category not found', 'error');
            return;
        }
        
        this.showResultModal(`${category.name} Endpoints`, {
            description: category.description,
            difficulty: category.difficulty,
            endpoint_count: category.endpoints.length,
            endpoints: category.endpoints.map(ep => ({
                path: ep.path,
                method: ep.method,
                summary: ep.summary
            }))
        });
    }
    
    showResultModal(title, data) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('result-modal');
        if (!modal) {
            modal = this.createResultModal();
            document.body.appendChild(modal);
        }
        
        // Update modal content
        const titleElement = modal.querySelector('.modal-title');
        const contentElement = modal.querySelector('.modal-content');
        
        titleElement.textContent = title;
        contentElement.innerHTML = this.formatModalContent(data);
        
        // Show modal
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        
        // Focus management
        const closeButton = modal.querySelector('.modal-close');
        if (closeButton) {
            closeButton.focus();
        }
    }
    
    createResultModal() {
        const modal = document.createElement('div');
        modal.id = 'result-modal';
        modal.className = 'modal';
        modal.setAttribute('aria-hidden', 'true');
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-labelledby', 'modal-title');
        
        modal.innerHTML = `
            <div class="modal-backdrop" onclick="this.parentNode.classList.remove('active'); this.parentNode.setAttribute('aria-hidden', 'true');"></div>
            <div class="modal-dialog">
                <div class="modal-header">
                    <h3 id="modal-title" class="modal-title"></h3>
                    <button class="modal-close" onclick="this.closest('.modal').classList.remove('active'); this.closest('.modal').setAttribute('aria-hidden', 'true');" aria-label="Close">×</button>
                </div>
                <div class="modal-body">
                    <div class="modal-content"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn-primary" onclick="this.closest('.modal').classList.remove('active'); this.closest('.modal').setAttribute('aria-hidden', 'true');">Close</button>
                </div>
            </div>
        `;
        
        return modal;
    }
    
    formatModalContent(data) {
        let html = '';
        
        Object.entries(data).forEach(([key, value]) => {
            const label = this.capitalizeFirst(key.replace(/_/g, ' '));
            
            if (Array.isArray(value)) {
                html += `<div class="modal-field">
                    <strong>${label}:</strong>
                    <ul>${value.map(item => `<li>${typeof item === 'object' ? JSON.stringify(item, null, 2) : item}</li>`).join('')}</ul>
                </div>`;
            } else if (typeof value === 'object') {
                html += `<div class="modal-field">
                    <strong>${label}:</strong>
                    <pre><code>${JSON.stringify(value, null, 2)}</code></pre>
                </div>`;
            } else {
                html += `<div class="modal-field">
                    <strong>${label}:</strong>
                    <span>${this.escapeHtml(String(value))}</span>
                </div>`;
            }
        });
        
        return html;
    }
    
    addCopyButtons() {
        document.querySelectorAll('.code-example').forEach(codeBlock => {
            if (!codeBlock.querySelector('.copy-code-btn')) {
                const button = document.createElement('button');
                button.className = 'copy-code-btn';
                button.textContent = '📋';
                button.title = 'Copy to clipboard';
                button.setAttribute('aria-label', 'Copy code to clipboard');
                codeBlock.appendChild(button);
            }
        });
    }
    
    copyCodeToClipboard(button) {
        const codeBlock = button.closest('.code-example');
        const code = codeBlock.querySelector('code') || codeBlock.querySelector('pre');
        
        if (!code) return;
        
        const text = code.textContent;
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.showCopyFeedback(button, 'Copied!');
            }).catch(() => {
                this.fallbackCopyToClipboard(text, button);
            });
        } else {
            this.fallbackCopyToClipboard(text, button);
        }
    }
    
    fallbackCopyToClipboard(text, button) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
            this.showCopyFeedback(button, 'Copied!');
        } catch {
            this.showCopyFeedback(button, 'Failed to copy');
        } finally {
            document.body.removeChild(textarea);
        }
    }
    
    showCopyFeedback(button, message) {
        const originalText = button.textContent;
        button.textContent = message;
        button.classList.add('copy-success');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copy-success');
        }, 2000);
    }
    
    showVisualFeedback(message, type = 'info') {
        // Create or update toast notification
        let toast = document.getElementById('toast-notification');
        
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toast-notification';
            toast.className = 'toast-notification';
            document.body.appendChild(toast);
        }
        
        toast.className = `toast-notification toast-${type} active`;
        toast.textContent = message;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            toast.classList.remove('active');
        }, 3000);
    }
    
    announceToScreenReader(message) {
        const announcer = document.getElementById('screen-reader-announcer') || 
            this.createScreenReaderAnnouncer();
        
        announcer.textContent = message;
        
        // Clear after announcement
        setTimeout(() => {
            announcer.textContent = '';
        }, 1000);
    }
    
    createScreenReaderAnnouncer() {
        const announcer = document.createElement('div');
        announcer.id = 'screen-reader-announcer';
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.style.position = 'absolute';
        announcer.style.left = '-9999px';
        announcer.style.width = '1px';
        announcer.style.height = '1px';
        announcer.style.overflow = 'hidden';
        document.body.appendChild(announcer);
        return announcer;
    }
    
    saveUserPreferences() {
        const preferences = {
            preferredLanguage: this.preferredLanguage,
            currentSection: this.currentSection
        };
        
        try {
            localStorage.setItem('docsPortalPreferences', JSON.stringify(preferences));
        } catch (error) {
            console.warn('Failed to save user preferences:', error);
        }
    }
    
    restoreUserPreferences() {
        try {
            const saved = localStorage.getItem('docsPortalPreferences');
            if (saved) {
                const preferences = JSON.parse(saved);
                this.preferredLanguage = preferences.preferredLanguage || 'python';
                
                // Restore section from URL hash or saved preference
                const hashSection = window.location.hash.replace('#', '');
                if (hashSection && document.getElementById(hashSection)) {
                    this.showSection(hashSection);
                } else if (preferences.currentSection && document.getElementById(preferences.currentSection)) {
                    this.showSection(preferences.currentSection);
                }
            }
        } catch (error) {
            console.warn('Failed to restore user preferences:', error);
        }
    }
    
    // Utility functions
    extractSectionFromOnclick(element) {
        const onclick = element.getAttribute('onclick');
        if (onclick) {
            const match = onclick.match(/showSection\(['"]([^'"]+)['"]\)/);
            return match ? match[1] : null;
        }
        return null;
    }
    
    getCategoryIcon(category) {
        const icons = {
            'authentication': '🔐',
            'chat': '💬',
            'health': '🏥',
            'users': '👥',
            'tasks': '✅',
            'webhooks': '🔗',
            'beta': '🧪',
            'evolution': '🧬',
            'github automation': '🐙',
            'documentation': '📄'
        };
        return icons[category.toLowerCase()] || '📄';
    }
    
    estimateResponseTime(category) {
        const times = {
            'Health': '< 100ms',
            'Chat': '< 3s',
            'Authentication': '< 500ms',
            'Tasks': '< 1s',
            'Users': '< 1s'
        };
        return times[category] || '< 1s';
    }
    
    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    showLoadingState() {
        const container = document.getElementById('api-categories');
        if (container) {
            container.innerHTML = `
                <div class="loading-placeholder">
                    <div class="loading-spinner"></div>
                    <p>Loading API documentation...</p>
                </div>
            `;
        }
    }
    
    renderApiError(errorMessage) {
        const container = document.getElementById('api-categories');
        if (container) {
            container.innerHTML = `
                <div class="error-placeholder">
                    <h3>⚠️ Unable to Load API Documentation</h3>
                    <p>Error: ${this.escapeHtml(errorMessage)}</p>
                    <p>Please ensure the server is running and try refreshing the page.</p>
                    <button class="btn-primary" onclick="location.reload()">
                        Refresh Page
                    </button>
                </div>
            `;
        }
    }
}

// Initialize the documentation portal when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.docsPortal = new DocsPortal();
});

// Global functions for backward compatibility with onclick handlers
function showSection(sectionId) {
    if (window.docsPortal) {
        window.docsPortal.showSection(sectionId);
    }
}

async function testHealth() {
    if (window.docsPortal) {
        await window.docsPortal.handleTryItAction('test-health', event.target);
    }
}

async function testChat() {
    if (window.docsPortal) {
        await window.docsPortal.handleTryItAction('test-chat', event.target);
    }
}