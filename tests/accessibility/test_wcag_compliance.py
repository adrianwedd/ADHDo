"""
WCAG 2.1 AA Compliance Testing for MCP ADHD Server.

Tests automated accessibility using axe-core and custom WCAG rules.
"""
import pytest
from playwright.sync_api import Page, expect
from axe_playwright_python import Axe
import json
from pathlib import Path
from typing import Dict, List, Any


class TestWCAGCompliance:
    """Test WCAG 2.1 AA compliance across the application."""
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    def test_homepage_wcag_compliance(
        self, 
        page: Page, 
        axe_builder: Axe,
        accessibility_results_dir: Path,
        accessibility_config: Dict[str, Any]
    ):
        """Test homepage WCAG 2.1 AA compliance."""
        # Navigate to homepage
        page.goto("/")
        
        # Wait for page to be fully loaded
        page.wait_for_load_state("networkidle")
        
        # Run axe accessibility scan
        results = axe_builder.analyze(page, {
            "tags": accessibility_config["tags"],
            "rules": {
                # WCAG 2.1 AA specific rules
                "color-contrast": {"enabled": True},
                "keyboard-navigation": {"enabled": True},
                "aria-labels": {"enabled": True},
                "heading-order": {"enabled": True},
                "landmark-one-main": {"enabled": True},
                "page-has-heading-one": {"enabled": True},
            }
        })
        
        # Save results
        results_file = accessibility_results_dir / "homepage_wcag_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        # Assert no violations
        violations = results.get("violations", [])
        if violations:
            violation_messages = [
                f"Rule: {v['id']} - {v['description']}\n"
                f"Impact: {v['impact']}\n"
                f"Nodes: {len(v['nodes'])}"
                for v in violations
            ]
            pytest.fail(f"WCAG violations found:\n" + "\n\n".join(violation_messages))
        
        assert len(violations) == 0, f"Found {len(violations)} WCAG violations"
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    @pytest.mark.crisis
    def test_chat_interface_wcag_compliance(
        self, 
        page: Page, 
        axe_builder: Axe,
        accessibility_results_dir: Path,
        accessibility_config: Dict[str, Any]
    ):
        """Test chat interface WCAG compliance (critical for ADHD support)."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Focus on chat interface
        chat_input = page.locator("#chat-input")
        expect(chat_input).to_be_visible()
        
        # Test with different content states
        states_to_test = [
            {"name": "empty_chat", "action": None},
            {"name": "with_message", "action": lambda: page.fill("#chat-input", "Hello")},
        ]
        
        for state in states_to_test:
            if state["action"]:
                state["action"]()
            
            # Run accessibility scan
            results = axe_builder.analyze(page, {
                "tags": accessibility_config["tags"] + ["best-practice"],
                "context": {"include": [".chat-interface, #chat-messages, #chat-input"]},
            })
            
            # Save state-specific results
            results_file = accessibility_results_dir / f"chat_{state['name']}_wcag_results.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            
            violations = results.get("violations", [])
            assert len(violations) == 0, f"Chat interface WCAG violations in {state['name']} state: {[v['id'] for v in violations]}"
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    @pytest.mark.auth
    def test_authentication_wcag_compliance(
        self, 
        page: Page, 
        axe_builder: Axe,
        accessibility_results_dir: Path
    ):
        """Test authentication modals WCAG compliance."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Test login modal
        page.click("button:has-text('Sign In')")
        page.wait_for_selector("#auth-modal", state="visible")
        
        # Run accessibility scan on modal
        results = axe_builder.analyze(page, {
            "tags": ["wcag2a", "wcag2aa", "wcag21aa"],
            "context": {"include": ["#auth-modal"]},
        })
        
        # Save results
        results_file = accessibility_results_dir / "auth_modal_wcag_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        violations = results.get("violations", [])
        
        # Check for common modal accessibility issues
        critical_rules = [
            "aria-dialog-name",
            "focus-order-semantics", 
            "keyboard-navigation",
            "color-contrast"
        ]
        
        critical_violations = [v for v in violations if v["id"] in critical_rules]
        assert len(critical_violations) == 0, f"Critical auth modal violations: {[v['id'] for v in critical_violations]}"
        
        # Switch to register form and test
        page.click("button:has-text('Don\\'t have an account?')")
        page.wait_for_timeout(500)  # Wait for form switch
        
        results = axe_builder.analyze(page, {
            "tags": ["wcag2a", "wcag2aa", "wcag21aa"],
            "context": {"include": ["#auth-modal"]},
        })
        
        violations = results.get("violations", [])
        assert len(violations) == 0, f"Register form WCAG violations: {[v['id'] for v in violations]}"
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    def test_quick_actions_wcag_compliance(
        self, 
        page: Page, 
        axe_builder: Axe,
        accessibility_results_dir: Path
    ):
        """Test quick action buttons WCAG compliance."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Focus on quick actions section
        quick_actions = page.locator(".grid.grid-cols-2.md\\:grid-cols-4")
        expect(quick_actions).to_be_visible()
        
        # Run accessibility scan
        results = axe_builder.analyze(page, {
            "tags": ["wcag2a", "wcag2aa", "wcag21aa", "best-practice"],
            "context": {"include": [".grid.grid-cols-2.md\\:grid-cols-4"]},
        })
        
        # Save results
        results_file = accessibility_results_dir / "quick_actions_wcag_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        violations = results.get("violations", [])
        
        # Quick actions are critical for ADHD users - must be accessible
        assert len(violations) == 0, f"Quick actions WCAG violations (critical for ADHD): {[v['id'] for v in violations]}"
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    @pytest.mark.parametrize("viewport", [
        {"width": 1920, "height": 1080, "name": "desktop"},
        {"width": 768, "height": 1024, "name": "tablet"},
        {"width": 375, "height": 667, "name": "mobile"},
    ])
    def test_responsive_wcag_compliance(
        self, 
        page: Page, 
        axe_builder: Axe,
        accessibility_results_dir: Path,
        viewport: Dict[str, Any]
    ):
        """Test WCAG compliance across different viewport sizes."""
        # Set viewport
        page.set_viewport_size(viewport["width"], viewport["height"])
        
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Run accessibility scan
        results = axe_builder.analyze(page, {
            "tags": ["wcag2a", "wcag2aa", "wcag21aa"],
        })
        
        # Save viewport-specific results
        results_file = accessibility_results_dir / f"responsive_{viewport['name']}_wcag_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        violations = results.get("violations", [])
        
        # Mobile accessibility is critical for ADHD users
        if viewport["name"] == "mobile":
            mobile_critical_rules = ["touch-target-size", "color-contrast", "zoom-and-scale"]
            mobile_violations = [v for v in violations if any(rule in v["id"] for rule in mobile_critical_rules)]
            assert len(mobile_violations) == 0, f"Critical mobile violations: {[v['id'] for v in mobile_violations]}"
        
        assert len(violations) == 0, f"WCAG violations on {viewport['name']}: {[v['id'] for v in violations]}"
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    def test_performance_metrics_accessibility(
        self, 
        page: Page, 
        axe_builder: Axe,
        accessibility_results_dir: Path
    ):
        """Test performance metrics section accessibility."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Focus on performance metrics
        metrics_section = page.locator(".grid.grid-cols-1.md\\:grid-cols-3")
        expect(metrics_section).to_be_visible()
        
        # Run accessibility scan
        results = axe_builder.analyze(page, {
            "tags": ["wcag2a", "wcag2aa", "wcag21aa"],
            "context": {"include": [".grid.grid-cols-1.md\\:grid-cols-3"]},
        })
        
        # Save results
        results_file = accessibility_results_dir / "performance_metrics_wcag_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        violations = results.get("violations", [])
        assert len(violations) == 0, f"Performance metrics WCAG violations: {[v['id'] for v in violations]}"
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    def test_color_contrast_comprehensive(
        self, 
        page: Page, 
        accessibility_config: Dict[str, Any],
        color_contrast_tester
    ):
        """Comprehensive color contrast testing."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize contrast tester
        tester = color_contrast_tester(page)
        contrast_results = tester.check_contrast_ratios()
        
        # Check against ADHD-friendly contrast requirements
        min_ratio = accessibility_config["contrast_ratios"]["normal_text"]
        
        failed_elements = []
        for result in contrast_results:
            if result.get("ratio", 0) < min_ratio:
                failed_elements.append(result["selector"])
        
        assert len(failed_elements) == 0, f"Elements with insufficient contrast: {failed_elements}"
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    def test_keyboard_navigation_comprehensive(
        self, 
        page: Page, 
        keyboard_navigation_tester,
        accessibility_results_dir: Path
    ):
        """Comprehensive keyboard navigation testing."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize keyboard tester
        tester = keyboard_navigation_tester(page)
        
        # Test tab order
        tab_order = tester.test_tab_order()
        assert len(tab_order) > 0, "No focusable elements found"
        
        # Test skip links
        skip_links = tester.test_skip_links()
        
        # Test focus visibility
        focus_visible = tester.test_focus_visible()
        assert focus_visible, "Focus indicators not visible"
        
        # Save keyboard navigation results
        results = {
            "tab_order": tab_order,
            "skip_links": skip_links,
            "focus_visible": focus_visible,
        }
        
        results_file = accessibility_results_dir / "keyboard_navigation_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        # Validate critical keyboard navigation
        critical_elements = ["chat-input", "Send", "Sign In"]
        found_critical = [elem for elem in tab_order if any(crit in elem for crit in critical_elements)]
        assert len(found_critical) >= 2, f"Critical elements not keyboard accessible: {critical_elements}"
    
    @pytest.mark.accessibility
    @pytest.mark.wcag
    def test_screen_reader_compatibility(
        self, 
        page: Page, 
        screen_reader_tester,
        accessibility_results_dir: Path
    ):
        """Test screen reader compatibility."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize screen reader tester
        tester = screen_reader_tester(page)
        
        # Check ARIA labels
        aria_results = tester.check_aria_labels()
        assert len(aria_results["missing_labels"]) == 0, f"Elements missing ARIA labels: {aria_results['missing_labels']}"
        
        # Check heading structure
        heading_results = tester.check_heading_structure()
        assert heading_results["valid"], f"Heading structure issues: {heading_results['issues']}"
        
        # Check landmarks
        landmarks = tester.check_landmarks()
        assert landmarks["main"] >= 1, "Page missing main landmark"
        assert landmarks["navigation"] >= 1, "Page missing navigation landmark"
        
        # Save screen reader results
        results = {
            "aria_labels": aria_results,
            "heading_structure": heading_results,
            "landmarks": landmarks,
        }
        
        results_file = accessibility_results_dir / "screen_reader_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)