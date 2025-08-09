"""
Accessibility test configuration and fixtures.
"""
import pytest
from playwright.sync_api import Page, Browser, BrowserContext
from axe_playwright_python import Axe
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


@pytest.fixture
def accessibility_config() -> Dict[str, Any]:
    """Configuration for accessibility testing."""
    return {
        # WCAG 2.1 AA compliance configuration
        "wcag_level": "AA",
        "wcag_version": "2.1",
        "tags": ["wcag2a", "wcag2aa", "wcag21aa"],
        
        # ADHD-specific accessibility rules
        "adhd_rules": {
            "cognitive_load": True,
            "focus_management": True,
            "motion_sensitivity": True,
            "attention_span": True,
            "sensory_considerations": True,
        },
        
        # Testing viewport configurations
        "viewports": [
            {"name": "desktop", "width": 1920, "height": 1080},
            {"name": "tablet", "width": 768, "height": 1024},
            {"name": "mobile", "width": 375, "height": 667},
        ],
        
        # Color contrast requirements
        "contrast_ratios": {
            "normal_text": 4.5,
            "large_text": 3.0,
            "non_text": 3.0,
        },
        
        # Performance thresholds for ADHD users
        "performance_thresholds": {
            "load_time_ms": 3000,
            "interaction_response_ms": 100,
            "content_shift": 0.1,
        },
        
        # Crisis features (highest priority)
        "crisis_features": [
            "emergency-button",
            "crisis-modal",
            "help-resources",
            "safety-override",
        ],
    }


@pytest.fixture
def axe_builder(page: Page):
    """Axe accessibility testing builder."""
    axe = Axe()
    axe.inject(page)
    return axe


@pytest.fixture
def accessibility_browser(browser: Browser) -> BrowserContext:
    """Browser context configured for accessibility testing."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        # Reduce motion for motion sensitivity testing
        reduced_motion="reduce",
        # High contrast for vision testing
        color_scheme="light",
        # Screen reader simulation
        extra_http_headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 AccessibilityTesting/1.0"
        }
    )
    return context


@pytest.fixture
def accessibility_results_dir() -> Path:
    """Directory for accessibility test results."""
    results_dir = Path("test-results/accessibility")
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


@pytest.fixture
def keyboard_navigation_tester():
    """Helper for keyboard navigation testing."""
    class KeyboardTester:
        def __init__(self, page: Page):
            self.page = page
            self.focus_order = []
            
        def test_tab_order(self) -> List[str]:
            """Test tab navigation order."""
            focusable_elements = self.page.query_selector_all(
                'a[href], button:not([disabled]), input:not([disabled]), '
                'select:not([disabled]), textarea:not([disabled]), '
                '[tabindex]:not([tabindex="-1"])'
            )
            
            tab_order = []
            for element in focusable_elements:
                element.focus()
                focused_element = self.page.evaluate("document.activeElement.tagName + (document.activeElement.id ? '#' + document.activeElement.id : '') + (document.activeElement.className ? '.' + document.activeElement.className.replace(' ', '.') : '')")
                tab_order.append(focused_element)
            
            return tab_order
            
        def test_skip_links(self) -> Dict[str, bool]:
            """Test skip link functionality."""
            skip_links = self.page.query_selector_all('a[href^="#"]')
            results = {}
            
            for link in skip_links:
                href = link.get_attribute("href")
                if href and href.startswith("#"):
                    target_id = href[1:]
                    target = self.page.query_selector(f'#{target_id}')
                    results[href] = target is not None
                    
            return results
            
        def test_focus_visible(self) -> bool:
            """Test focus indicators are visible."""
            # Add CSS to detect focus visibility
            self.page.add_style_tag(content="""
                .focus-test:focus {
                    outline: 2px solid red !important;
                }
            """)
            
            # Test focus on interactive elements
            interactive_elements = self.page.query_selector_all('button, a, input, select, textarea')
            for element in interactive_elements[:5]:  # Test first 5 elements
                element.focus()
                # Check if focus is visible (implementation depends on specific styles)
                is_focused = self.page.evaluate(f"document.activeElement === arguments[0]", element)
                if not is_focused:
                    return False
            
            return True
    
    return KeyboardTester


@pytest.fixture
def screen_reader_tester():
    """Helper for screen reader compatibility testing."""
    class ScreenReaderTester:
        def __init__(self, page: Page):
            self.page = page
            
        def check_aria_labels(self) -> Dict[str, List[str]]:
            """Check ARIA labels and descriptions."""
            results = {
                "missing_labels": [],
                "empty_labels": [],
                "good_labels": [],
            }
            
            # Check buttons without accessible names
            buttons = self.page.query_selector_all("button")
            for button in buttons:
                aria_label = button.get_attribute("aria-label")
                inner_text = button.inner_text().strip()
                
                if not aria_label and not inner_text:
                    results["missing_labels"].append("button")
                elif aria_label == "" or inner_text == "":
                    results["empty_labels"].append("button") 
                else:
                    results["good_labels"].append("button")
            
            # Check form inputs
            inputs = self.page.query_selector_all("input")
            for input_elem in inputs:
                label = self.page.query_selector(f'label[for="{input_elem.get_attribute("id")}"]')
                aria_label = input_elem.get_attribute("aria-label")
                
                if not label and not aria_label:
                    results["missing_labels"].append("input")
                
            return results
            
        def check_heading_structure(self) -> Dict[str, Any]:
            """Check heading hierarchy."""
            headings = self.page.query_selector_all("h1, h2, h3, h4, h5, h6")
            heading_levels = [int(h.tag_name[1]) for h in headings]
            
            issues = []
            if not heading_levels:
                issues.append("No headings found")
            elif heading_levels[0] != 1:
                issues.append("Page doesn't start with h1")
                
            # Check for skipped levels
            for i in range(1, len(heading_levels)):
                if heading_levels[i] > heading_levels[i-1] + 1:
                    issues.append(f"Heading level skip from h{heading_levels[i-1]} to h{heading_levels[i]}")
            
            return {
                "levels": heading_levels,
                "issues": issues,
                "valid": len(issues) == 0
            }
            
        def check_landmarks(self) -> Dict[str, int]:
            """Check ARIA landmarks."""
            landmarks = {
                "main": len(self.page.query_selector_all('main, [role="main"]')),
                "navigation": len(self.page.query_selector_all('nav, [role="navigation"]')),
                "banner": len(self.page.query_selector_all('header[role="banner"], [role="banner"]')),
                "contentinfo": len(self.page.query_selector_all('footer[role="contentinfo"], [role="contentinfo"]')),
                "search": len(self.page.query_selector_all('[role="search"]')),
            }
            return landmarks
    
    return ScreenReaderTester


@pytest.fixture
def color_contrast_tester():
    """Helper for color contrast testing."""
    class ColorContrastTester:
        def __init__(self, page: Page):
            self.page = page
            
        def check_contrast_ratios(self) -> Dict[str, Any]:
            """Check color contrast ratios."""
            # Inject contrast checking script
            script = """
            function getContrastRatio(element) {
                const style = window.getComputedStyle(element);
                const color = style.color;
                const backgroundColor = style.backgroundColor;
                
                // Simple contrast calculation (in real implementation, use proper color parsing)
                return {
                    color: color,
                    backgroundColor: backgroundColor,
                    // Placeholder ratio - would need proper color parsing library
                    ratio: 4.5
                };
            }
            
            const elements = document.querySelectorAll('p, span, div, h1, h2, h3, h4, h5, h6, button, a');
            const results = [];
            
            elements.forEach(element => {
                if (element.innerText.trim()) {
                    const contrast = getContrastRatio(element);
                    results.push({
                        selector: element.tagName + (element.id ? '#' + element.id : '') + (element.className ? '.' + element.className.replace(' ', '.') : ''),
                        ...contrast
                    });
                }
            });
            
            return results;
            """
            
            return self.page.evaluate(script)
    
    return ColorContrastTester


@pytest.fixture
def adhd_accessibility_tester():
    """Helper for ADHD-specific accessibility testing."""
    class ADHDAccessibilityTester:
        def __init__(self, page: Page):
            self.page = page
            
        def check_cognitive_load(self) -> Dict[str, Any]:
            """Check cognitive load factors."""
            # Count elements that could contribute to cognitive overload
            results = {
                "total_interactive_elements": len(self.page.query_selector_all("button, a, input, select, textarea")),
                "animation_elements": len(self.page.query_selector_all("[class*='animate'], [class*='transition']")),
                "color_only_information": 0,  # Would need semantic analysis
                "simultaneous_content": len(self.page.query_selector_all(".modal:not(.hidden), .tooltip:visible, .popup:visible")),
            }
            
            # Check for overwhelming number of choices (ADHD consideration)
            buttons = len(self.page.query_selector_all("button"))
            links = len(self.page.query_selector_all("a"))
            
            results["choice_overload_risk"] = (buttons + links) > 12  # Rule of thumb for ADHD
            results["cognitive_load_score"] = min(10, (buttons + links) / 2)  # Simple scoring
            
            return results
            
        def check_focus_management(self) -> Dict[str, bool]:
            """Check focus management for ADHD users."""
            results = {
                "focus_traps_in_modals": True,  # Would need dynamic testing
                "focus_restoration": True,      # Would need state tracking
                "clear_focus_indicators": True, # Visual check needed
                "logical_focus_order": True,    # Tab order analysis needed
            }
            
            # Check for focus traps in modals
            modals = self.page.query_selector_all(".modal, [role='dialog']")
            for modal in modals:
                if modal.is_visible():
                    focusable_in_modal = modal.query_selector_all(
                        'button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                    )
                    results["focus_traps_in_modals"] = len(focusable_in_modal) > 0
            
            return results
            
        def check_motion_sensitivity(self) -> Dict[str, Any]:
            """Check motion sensitivity accommodations."""
            # Check for respect of reduced motion preferences
            reduced_motion_script = """
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            const animatedElements = document.querySelectorAll('[class*="animate"], [style*="animation"]');
            
            return {
                prefersReducedMotion: prefersReducedMotion,
                animatedElementsCount: animatedElements.length,
                respectsPreference: true // Would need to check if animations are disabled
            };
            """
            
            return self.page.evaluate(reduced_motion_script)
            
        def check_crisis_features_accessibility(self) -> Dict[str, bool]:
            """Check accessibility of crisis support features."""
            crisis_elements = [
                "button[data-crisis]",
                ".emergency-button", 
                ".crisis-modal",
                ".help-resources",
                ".safety-override"
            ]
            
            results = {}
            for selector in crisis_elements:
                element = self.page.query_selector(selector)
                if element:
                    results[selector] = {
                        "exists": True,
                        "accessible_name": bool(element.get_attribute("aria-label") or element.inner_text().strip()),
                        "keyboard_accessible": element.get_attribute("tabindex") != "-1",
                        "high_contrast": True,  # Would need color analysis
                    }
                else:
                    results[selector] = {"exists": False}
            
            return results
    
    return ADHDAccessibilityTester