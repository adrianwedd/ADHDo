/**
 * Mobile Gesture Support for ADHD-Optimized Interface
 * Provides swipe gestures, haptic feedback, and touch interactions
 * Designed specifically for neurodivergent users
 */

class MobileGestureManager {
    constructor() {
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        this.minSwipeDistance = 50;
        this.maxSwipeTime = 300;
        this.touchStartTime = 0;
        this.gestureHandlers = new Map();
        this.isScrolling = false;
        this.scrollTimeout = null;
        
        // Haptic feedback support
        this.hapticSupported = 'vibrate' in navigator;
        
        // Initialize gesture handling
        this.initializeGestures();
        this.initializeHapticFeedback();
        this.initializeTouchOptimizations();
    }

    initializeGestures() {
        // Add touch event listeners for gesture detection
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        
        // Handle scroll detection
        document.addEventListener('scroll', this.handleScroll.bind(this), { passive: true });
        
        // Prevent default touch behaviors on specific elements
        this.initializePreventDefaults();
    }

    initializePreventDefaults() {
        // Prevent pull-to-refresh on mobile browsers
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length > 1) return; // Allow pinch-to-zoom
            
            // Prevent pull-to-refresh when at top of page
            if (window.scrollY === 0 && e.touches[0].clientY > 0) {
                const element = e.target.closest('.mobile-prevent-refresh');
                if (element || document.body.scrollTop === 0) {
                    // Allow very small movements for scrolling
                    let preventRefresh = false;
                    const touchStartY = e.touches[0].clientY;
                    
                    const touchMoveHandler = (moveEvent) => {
                        const touchY = moveEvent.touches[0].clientY;
                        const deltaY = touchY - touchStartY;
                        
                        if (deltaY > 10) {  // Pulling down
                            preventRefresh = true;
                            moveEvent.preventDefault();
                        }
                    };
                    
                    const touchEndHandler = () => {
                        document.removeEventListener('touchmove', touchMoveHandler);
                        document.removeEventListener('touchend', touchEndHandler);
                    };
                    
                    document.addEventListener('touchmove', touchMoveHandler, { passive: false });
                    document.addEventListener('touchend', touchEndHandler);
                }
            }
        }, { passive: false });
    }

    handleTouchStart(e) {
        this.touchStartX = e.touches[0].clientX;
        this.touchStartY = e.touches[0].clientY;
        this.touchStartTime = Date.now();
        this.isScrolling = false;
        
        // Clear any existing scroll timeout
        if (this.scrollTimeout) {
            clearTimeout(this.scrollTimeout);
            this.scrollTimeout = null;
        }
    }

    handleTouchMove(e) {
        // Detect if user is scrolling vertically
        const currentX = e.touches[0].clientX;
        const currentY = e.touches[0].clientY;
        const deltaX = Math.abs(currentX - this.touchStartX);
        const deltaY = Math.abs(currentY - this.touchStartY);
        
        if (deltaY > deltaX && deltaY > 10) {
            this.isScrolling = true;
        }
    }

    handleTouchEnd(e) {
        // Skip if user was scrolling
        if (this.isScrolling) {
            return;
        }
        
        this.touchEndX = e.changedTouches[0].clientX;
        this.touchEndY = e.changedTouches[0].clientY;
        
        const touchDuration = Date.now() - this.touchStartTime;
        
        // Only process gestures within time limit
        if (touchDuration <= this.maxSwipeTime) {
            this.processSwipeGesture(e.target);
            this.processTapGesture(e.target);
        }
    }

    handleScroll() {
        this.isScrolling = true;
        
        // Reset scrolling flag after scroll stops
        if (this.scrollTimeout) {
            clearTimeout(this.scrollTimeout);
        }
        
        this.scrollTimeout = setTimeout(() => {
            this.isScrolling = false;
        }, 150);
    }

    processSwipeGesture(target) {
        const deltaX = this.touchEndX - this.touchStartX;
        const deltaY = this.touchEndY - this.touchStartY;
        const absDeltaX = Math.abs(deltaX);
        const absDeltaY = Math.abs(deltaY);

        // Determine swipe direction
        if (absDeltaX > this.minSwipeDistance && absDeltaX > absDeltaY) {
            // Horizontal swipe
            const direction = deltaX > 0 ? 'right' : 'left';
            this.triggerSwipeGesture(direction, target, { deltaX, deltaY });
        } else if (absDeltaY > this.minSwipeDistance && absDeltaY > absDeltaX) {
            // Vertical swipe
            const direction = deltaY > 0 ? 'down' : 'up';
            this.triggerSwipeGesture(direction, target, { deltaX, deltaY });
        }
    }

    processTapGesture(target) {
        const deltaX = Math.abs(this.touchEndX - this.touchStartX);
        const deltaY = Math.abs(this.touchEndY - this.touchStartY);
        
        // Consider it a tap if movement is minimal
        if (deltaX < 10 && deltaY < 10) {
            this.triggerTapGesture(target);
        }
    }

    triggerSwipeGesture(direction, target, details) {
        // Find the closest element with swipe handlers
        const swipeElement = target.closest('[data-swipe]');
        if (swipeElement) {
            const swipeHandlers = swipeElement.dataset.swipe.split(',');
            if (swipeHandlers.includes(direction)) {
                this.handleSwipeAction(direction, swipeElement, details);
            }
        }

        // Trigger global swipe handlers
        this.gestureHandlers.forEach((handler, key) => {
            if (key.startsWith(`swipe-${direction}`)) {
                handler(target, details);
            }
        });
    }

    triggerTapGesture(target) {
        // Enhanced tap handling for ADHD users
        const tapElement = target.closest('.mobile-tap-enhanced');
        if (tapElement) {
            this.provideTapFeedback(tapElement);
        }
    }

    handleSwipeAction(direction, element, details) {
        const actionMap = {
            'left': () => this.handleSwipeLeft(element, details),
            'right': () => this.handleSwipeRight(element, details),
            'up': () => this.handleSwipeUp(element, details),
            'down': () => this.handleSwipeDown(element, details)
        };

        const action = actionMap[direction];
        if (action) {
            action();
            this.provideFeedback('light'); // Light haptic feedback for successful gesture
        }
    }

    handleSwipeLeft(element, details) {
        // Default swipe left actions
        if (element.classList.contains('mobile-card-swipeable')) {
            this.dismissCard(element, 'left');
        } else if (element.classList.contains('mobile-modal-container')) {
            this.closeModal(element);
        } else if (element.classList.contains('mobile-chat-message')) {
            this.showMessageActions(element, 'left');
        }
        
        // Custom swipe left handler
        const customHandler = element.dataset.swipeLeftAction;
        if (customHandler) {
            this.executeCustomAction(customHandler, element, details);
        }
    }

    handleSwipeRight(element, details) {
        // Default swipe right actions
        if (element.classList.contains('mobile-card-swipeable')) {
            this.favoriteCard(element);
        } else if (element.classList.contains('mobile-chat-message')) {
            this.showMessageActions(element, 'right');
        }
        
        // Custom swipe right handler
        const customHandler = element.dataset.swipeRightAction;
        if (customHandler) {
            this.executeCustomAction(customHandler, element, details);
        }
    }

    handleSwipeUp(element, details) {
        // Default swipe up actions
        if (element.classList.contains('mobile-quick-action')) {
            this.expandQuickAction(element);
        }
        
        // Custom swipe up handler
        const customHandler = element.dataset.swipeUpAction;
        if (customHandler) {
            this.executeCustomAction(customHandler, element, details);
        }
    }

    handleSwipeDown(element, details) {
        // Default swipe down actions
        if (element.classList.contains('mobile-modal-container')) {
            this.closeModal(element);
        }
        
        // Custom swipe down handler
        const customHandler = element.dataset.swipeDownAction;
        if (customHandler) {
            this.executeCustomAction(customHandler, element, details);
        }
    }

    executeCustomAction(actionName, element, details) {
        // Execute custom actions defined in data attributes
        switch (actionName) {
            case 'quick-task':
                this.triggerQuickTask(element);
                break;
            case 'emergency':
                this.triggerEmergency();
                break;
            case 'dismiss':
                this.dismissElement(element);
                break;
            case 'favorite':
                this.toggleFavorite(element);
                break;
            default:
                // Try to find and execute a function by name
                if (window[actionName] && typeof window[actionName] === 'function') {
                    window[actionName](element, details);
                }
        }
    }

    // ADHD-specific gesture actions
    dismissCard(element, direction) {
        element.style.transform = `translateX(${direction === 'left' ? '-' : ''}100%)`;
        element.style.opacity = '0';
        element.style.transition = 'all 0.3s ease';
        
        setTimeout(() => {
            element.remove();
        }, 300);
    }

    favoriteCard(element) {
        element.classList.toggle('mobile-card-favorited');
        const icon = element.querySelector('.favorite-icon');
        if (icon) {
            icon.textContent = element.classList.contains('mobile-card-favorited') ? '❤️' : '🤍';
        }
    }

    closeModal(element) {
        const modal = element.closest('.mobile-modal-overlay');
        if (modal) {
            this.closeModalWithAnimation(modal);
        }
    }

    showMessageActions(element, direction) {
        // Show contextual actions for chat messages
        const actionsPanel = element.querySelector('.mobile-message-actions');
        if (actionsPanel) {
            actionsPanel.classList.toggle('mobile-actions-visible');
        }
    }

    expandQuickAction(element) {
        element.classList.add('mobile-quick-action-expanded');
        this.provideFeedback('medium');
    }

    // Haptic feedback system
    initializeHapticFeedback() {
        // Feature detection for different haptic APIs
        this.hasVibrationAPI = 'vibrate' in navigator;
        this.hasHapticAPI = 'getGamepads' in navigator && navigator.getGamepads().some(pad => pad && pad.vibrationActuator);
        
        // ADHD-optimized haptic patterns
        this.hapticPatterns = {
            light: [10],                    // Quick confirmation
            medium: [20, 50, 20],          // Action feedback
            strong: [50, 100, 50],         // Important notification
            success: [20, 50, 20, 50, 20], // Task completion
            error: [100, 50, 100],         // Error or warning
            emergency: [200, 100, 200, 100, 200] // Crisis/emergency
        };
    }

    provideFeedback(type = 'light') {
        this.provideHapticFeedback(type);
        this.provideVisualFeedback(type);
        this.provideAudioFeedback(type);
    }

    provideHapticFeedback(type) {
        if (!this.hasVibrationAPI) return;
        
        const pattern = this.hapticPatterns[type] || this.hapticPatterns.light;
        
        try {
            navigator.vibrate(pattern);
        } catch (error) {
            console.log('Haptic feedback not available:', error);
        }
    }

    provideVisualFeedback(type) {
        // Create visual feedback for interactions
        const feedbackColors = {
            light: 'rgba(59, 130, 246, 0.3)',
            medium: 'rgba(16, 185, 129, 0.4)',
            strong: 'rgba(245, 158, 11, 0.4)',
            success: 'rgba(34, 197, 94, 0.4)',
            error: 'rgba(239, 68, 68, 0.4)',
            emergency: 'rgba(220, 38, 38, 0.6)'
        };

        const color = feedbackColors[type] || feedbackColors.light;
        document.body.style.setProperty('--feedback-color', color);
        document.body.classList.add('mobile-visual-feedback');
        
        setTimeout(() => {
            document.body.classList.remove('mobile-visual-feedback');
        }, 200);
    }

    provideAudioFeedback(type) {
        // Optional audio feedback for ADHD users who prefer it
        if (!window.audioFeedbackEnabled) return;
        
        const audioContext = this.getAudioContext();
        if (!audioContext) return;
        
        const frequencies = {
            light: 800,
            medium: 600,
            strong: 400,
            success: [600, 800, 1000],
            error: [400, 200],
            emergency: 200
        };
        
        this.playTone(frequencies[type] || frequencies.light, 100);
    }

    getAudioContext() {
        if (!this.audioContext) {
            try {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            } catch (error) {
                console.log('Audio context not available:', error);
                return null;
            }
        }
        return this.audioContext;
    }

    playTone(frequency, duration) {
        const audioContext = this.getAudioContext();
        if (!audioContext) return;
        
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration / 1000);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + duration / 1000);
    }

    provideTapFeedback(element) {
        // Enhanced tap feedback for ADHD users
        element.classList.add('mobile-tap-active');
        this.provideFeedback('light');
        
        setTimeout(() => {
            element.classList.remove('mobile-tap-active');
        }, 150);
    }

    // Touch optimization methods
    initializeTouchOptimizations() {
        // Optimize touch targets
        this.optimizeTouchTargets();
        
        // Add touch-friendly scrolling
        this.optimizeScrolling();
        
        // Handle device orientation changes
        this.handleOrientationChanges();
    }

    optimizeTouchTargets() {
        // Find and enhance small touch targets
        const smallTargets = document.querySelectorAll('button, a, [role="button"], input[type="submit"], input[type="button"]');
        
        smallTargets.forEach(target => {
            const rect = target.getBoundingClientRect();
            if (rect.width < 44 || rect.height < 44) {
                target.classList.add('mobile-touch-target');
            }
        });
    }

    optimizeScrolling() {
        // Add momentum scrolling for iOS
        document.body.style.webkitOverflowScrolling = 'touch';
        
        // Optimize scroll containers
        const scrollContainers = document.querySelectorAll('.mobile-scroll-container, .mobile-modal-body');
        scrollContainers.forEach(container => {
            container.style.webkitOverflowScrolling = 'touch';
            container.style.overflowScrolling = 'touch';
        });
    }

    handleOrientationChanges() {
        window.addEventListener('orientationchange', () => {
            // Delay to ensure the orientation change is complete
            setTimeout(() => {
                this.optimizeTouchTargets();
                this.adjustModalSizing();
            }, 100);
        });
    }

    adjustModalSizing() {
        // Adjust modal sizing after orientation change
        const modals = document.querySelectorAll('.mobile-modal-container');
        modals.forEach(modal => {
            // Force recalculation of modal dimensions
            modal.style.height = window.innerHeight + 'px';
        });
    }

    // ADHD-specific helper methods
    triggerQuickTask(element) {
        const taskType = element.dataset.quickTask;
        if (window.quickAction && typeof window.quickAction === 'function') {
            window.quickAction(taskType);
        }
    }

    triggerEmergency() {
        // Trigger emergency/crisis support
        this.provideFeedback('emergency');
        if (window.showEmergencyModal && typeof window.showEmergencyModal === 'function') {
            window.showEmergencyModal();
        }
    }

    dismissElement(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(-20px)';
        element.style.transition = 'all 0.3s ease';
        
        setTimeout(() => {
            element.style.display = 'none';
        }, 300);
    }

    toggleFavorite(element) {
        const isFavorited = element.classList.toggle('mobile-favorited');
        this.provideFeedback(isFavorited ? 'success' : 'light');
    }

    closeModalWithAnimation(modal) {
        modal.classList.add('mobile-modal-closing');
        
        setTimeout(() => {
            modal.classList.add('hidden');
            modal.classList.remove('mobile-modal-closing');
            document.body.classList.remove('mobile-modal-open');
        }, 200);
    }

    // Public API for custom gesture handlers
    registerGestureHandler(name, handler) {
        this.gestureHandlers.set(name, handler);
    }

    removeGestureHandler(name) {
        this.gestureHandlers.delete(name);
    }

    // Enable/disable features for ADHD customization
    setHapticEnabled(enabled) {
        this.hapticSupported = enabled && ('vibrate' in navigator);
    }

    setAudioFeedbackEnabled(enabled) {
        window.audioFeedbackEnabled = enabled;
    }

    setVisualFeedbackEnabled(enabled) {
        window.visualFeedbackEnabled = enabled;
    }
}

// Initialize gesture manager when DOM is loaded
let mobileGestureManager = null;

document.addEventListener('DOMContentLoaded', () => {
    mobileGestureManager = new MobileGestureManager();
    
    // Make it globally available
    window.mobileGestures = mobileGestureManager;
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobileGestureManager;
}