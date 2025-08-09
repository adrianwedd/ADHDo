"""
ADHD-Specific Accessibility Testing for MCP ADHD Server.

Tests accessibility features specifically designed for ADHD and neurodivergent users.
"""
import pytest
from playwright.sync_api import Page, expect
import json
from pathlib import Path
from typing import Dict, List, Any


class TestADHDAccessibility:
    """Test ADHD-specific accessibility features and considerations."""
    
    @pytest.mark.accessibility
    @pytest.mark.adhd_critical
    def test_cognitive_load_management(
        self, 
        page: Page, 
        adhd_accessibility_tester,
        accessibility_results_dir: Path,
        accessibility_config: Dict[str, Any]
    ):
        """Test cognitive load management for ADHD users."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize ADHD tester
        tester = adhd_accessibility_tester(page)
        
        # Check cognitive load factors
        cognitive_load = tester.check_cognitive_load()
        
        # ADHD-specific thresholds
        max_interactive_elements = 15  # Avoid choice overload
        max_simultaneous_content = 2   # Reduce distraction
        max_cognitive_score = 6.0      # Keep cognitive load manageable
        
        # Assert cognitive load limits
        assert cognitive_load["total_interactive_elements"] <= max_interactive_elements, \
            f"Too many interactive elements ({cognitive_load['total_interactive_elements']}) - may overwhelm ADHD users"
        
        assert cognitive_load["simultaneous_content"] <= max_simultaneous_content, \
            f"Too much simultaneous content ({cognitive_load['simultaneous_content']}) - distracting for ADHD users"
        
        assert cognitive_load["cognitive_load_score"] <= max_cognitive_score, \
            f"Cognitive load score too high ({cognitive_load['cognitive_load_score']}) for ADHD users"
        
        assert not cognitive_load["choice_overload_risk"], \
            "Choice overload risk detected - simplify interface for ADHD users"
        
        # Save results
        results_file = accessibility_results_dir / "cognitive_load_results.json"
        with open(results_file, "w") as f:
            json.dump(cognitive_load, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.adhd_critical
    def test_focus_management(
        self, 
        page: Page, 
        adhd_accessibility_tester,
        accessibility_results_dir: Path
    ):
        """Test focus management critical for ADHD users."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize ADHD tester
        tester = adhd_accessibility_tester(page)
        
        # Check focus management
        focus_results = tester.check_focus_management()
        
        # All focus management features are critical for ADHD
        assert focus_results["clear_focus_indicators"], \
            "Clear focus indicators required for ADHD attention management"
        
        assert focus_results["logical_focus_order"], \
            "Logical focus order essential for ADHD cognitive processing"
        
        # Test modal focus trap (critical for ADHD attention)
        page.click("button:has-text('Sign In')")
        page.wait_for_selector("#auth-modal", state="visible")
        
        # Focus should be trapped in modal
        modal_focus_results = tester.check_focus_management()
        assert modal_focus_results["focus_traps_in_modals"], \
            "Focus traps in modals required to prevent ADHD attention wandering"
        
        # Close modal and check focus restoration
        page.click("button[onclick='closeAuthModal()']")
        page.wait_for_selector("#auth-modal", state="hidden")
        
        # Save results
        results_file = accessibility_results_dir / "focus_management_results.json"
        with open(results_file, "w") as f:
            json.dump(focus_results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.adhd_critical
    def test_motion_sensitivity_accommodations(
        self, 
        page: Page, 
        adhd_accessibility_tester,
        accessibility_results_dir: Path
    ):
        """Test motion sensitivity accommodations for ADHD users."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize ADHD tester
        tester = adhd_accessibility_tester(page)
        
        # Check motion sensitivity features
        motion_results = tester.check_motion_sensitivity()
        
        # Test with reduced motion preference
        page.emulate_media({"prefers-reduced-motion": "reduce"})
        page.reload()
        page.wait_for_load_state("networkidle")
        
        reduced_motion_results = tester.check_motion_sensitivity()
        
        # Animations should be reduced/disabled when user prefers reduced motion
        assert reduced_motion_results.get("respectsPreference", False), \
            "Must respect prefers-reduced-motion for ADHD sensory sensitivity"
        
        # Save results
        results = {
            "normal": motion_results,
            "reduced_motion": reduced_motion_results,
        }
        
        results_file = accessibility_results_dir / "motion_sensitivity_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.crisis
    @pytest.mark.adhd_critical
    def test_crisis_features_accessibility(
        self, 
        page: Page, 
        adhd_accessibility_tester,
        accessibility_results_dir: Path,
        accessibility_config: Dict[str, Any]
    ):
        """Test accessibility of crisis support features (highest priority)."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize ADHD tester
        tester = adhd_accessibility_tester(page)
        
        # Check crisis features accessibility
        crisis_results = tester.check_crisis_features_accessibility()
        
        # Crisis features are life-critical and must be fully accessible
        crisis_features = accessibility_config["crisis_features"]
        
        for feature in crisis_features:
            feature_selector = f".{feature}"
            if feature_selector in crisis_results and crisis_results[feature_selector]["exists"]:
                feature_result = crisis_results[feature_selector]
                
                assert feature_result["accessible_name"], \
                    f"Crisis feature {feature} must have accessible name - life-critical"
                
                assert feature_result["keyboard_accessible"], \
                    f"Crisis feature {feature} must be keyboard accessible - life-critical"
                
                assert feature_result["high_contrast"], \
                    f"Crisis feature {feature} must have high contrast - life-critical visibility"
        
        # Test emergency actions accessibility
        emergency_buttons = page.query_selector_all("button[class*='red'], button[class*='emergency'], button[class*='crisis']")
        
        for button in emergency_buttons:
            # Emergency buttons must be large enough for motor impairments
            box = button.bounding_box()
            if box:
                assert box["width"] >= 44 and box["height"] >= 44, \
                    f"Emergency button too small - must be 44x44px minimum for motor accessibility"
            
            # Must have clear accessible name
            aria_label = button.get_attribute("aria-label")
            text_content = button.inner_text().strip()
            assert aria_label or text_content, \
                "Emergency buttons must have clear accessible names"
        
        # Save results
        results_file = accessibility_results_dir / "crisis_features_accessibility_results.json"
        with open(results_file, "w") as f:
            json.dump(crisis_results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.adhd_critical
    def test_attention_span_considerations(
        self, 
        page: Page, 
        accessibility_results_dir: Path
    ):
        """Test attention span considerations for ADHD users."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Test page load performance (critical for ADHD attention)
        navigation_start = page.evaluate("performance.timing.navigationStart")
        dom_complete = page.evaluate("performance.timing.domComplete")
        load_time = dom_complete - navigation_start
        
        # ADHD users need fast load times to maintain attention
        max_load_time = 3000  # 3 seconds max
        assert load_time <= max_load_time, \
            f"Page load time ({load_time}ms) exceeds ADHD attention threshold ({max_load_time}ms)"
        
        # Test content chunking (check for logical sections)
        sections = page.query_selector_all("section, article, .card, .section")
        assert len(sections) >= 3, "Content should be chunked into digestible sections for ADHD"
        
        # Test for progress indicators on long forms/processes
        forms = page.query_selector_all("form")
        for form in forms:
            form_inputs = form.query_selector_all("input, select, textarea")
            if len(form_inputs) > 3:  # Long forms need progress indication
                progress_indicators = form.query_selector_all(".progress, [role='progressbar'], .step-indicator")
                assert len(progress_indicators) > 0, \
                    "Long forms need progress indicators for ADHD attention management"
        
        # Save performance results
        results = {
            "page_load_time_ms": load_time,
            "content_sections": len(sections),
            "adhd_friendly_load_time": load_time <= max_load_time,
        }
        
        results_file = accessibility_results_dir / "attention_span_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.adhd_critical
    def test_error_handling_accessibility(
        self, 
        page: Page, 
        accessibility_results_dir: Path
    ):
        """Test error handling accessibility for ADHD users."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Test form validation errors (ADHD users need clear, immediate feedback)
        page.click("button:has-text('Sign In')")
        page.wait_for_selector("#auth-modal", state="visible")
        
        # Try to submit empty form
        page.click("button[type='submit']")
        
        # Check for accessible error messages
        error_elements = page.query_selector_all(".error, [aria-invalid='true'], [role='alert']")
        
        results = {
            "error_elements_found": len(error_elements),
            "errors_have_aria_labels": [],
            "errors_associated_with_inputs": [],
        }
        
        for error in error_elements:
            # Check if error has accessible name
            aria_label = error.get_attribute("aria-label")
            text_content = error.inner_text().strip()
            has_accessible_name = bool(aria_label or text_content)
            results["errors_have_aria_labels"].append(has_accessible_name)
            
            # Check if error is associated with input
            aria_describedby = error.get_attribute("aria-describedby")
            for_attr = error.get_attribute("for")
            is_associated = bool(aria_describedby or for_attr)
            results["errors_associated_with_inputs"].append(is_associated)
        
        # ADHD users need immediate, clear error feedback
        if error_elements:
            assert all(results["errors_have_aria_labels"]), \
                "All error messages must have accessible names for ADHD clarity"
        
        # Test connection error simulation
        page.goto("/nonexistent-endpoint")
        
        # Should show user-friendly error page
        error_page_content = page.content()
        assert "error" in error_page_content.lower() or "not found" in error_page_content.lower(), \
            "Error pages must be clear and accessible for ADHD users"
        
        # Save results
        results_file = accessibility_results_dir / "error_handling_accessibility_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.adhd_critical
    def test_sensory_considerations(
        self, 
        page: Page, 
        accessibility_results_dir: Path
    ):
        """Test sensory considerations for ADHD users."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Check for sensory-friendly design elements
        results = {
            "auto_playing_media": 0,
            "flashing_elements": 0,
            "high_contrast_available": False,
            "font_size_adjustable": False,
            "color_coding_alternatives": 0,
        }
        
        # Check for auto-playing media (problematic for ADHD)
        auto_media = page.query_selector_all("video[autoplay], audio[autoplay]")
        results["auto_playing_media"] = len(auto_media)
        
        # Auto-playing media is problematic for ADHD attention/sensory processing
        assert len(auto_media) == 0, \
            "Auto-playing media can overwhelm ADHD users - require user initiation"
        
        # Check for potentially flashing/strobing elements
        animated_elements = page.query_selector_all("[class*='animate'], [class*='flash'], [class*='blink']")
        results["flashing_elements"] = len(animated_elements)
        
        # Check color-only information (ADHD users may have comorbid color vision differences)
        color_coded_elements = page.query_selector_all(".text-red, .text-green, .bg-red, .bg-green")
        
        # Each color-coded element should have alternative indicators
        for element in color_coded_elements:
            icons = element.query_selector_all("i, svg, .icon")
            text_indicators = element.query_selector_all(".sr-only, [aria-label]")
            
            if icons or text_indicators:
                results["color_coding_alternatives"] += 1
        
        # Test font size accessibility
        page.evaluate("""
            document.body.style.fontSize = '150%';
        """)
        
        # Page should remain usable at 150% zoom (ADHD reading accommodation)
        page.wait_for_timeout(1000)
        
        # Check if content is still accessible
        chat_input = page.locator("#chat-input")
        expect(chat_input).to_be_visible()
        results["font_size_adjustable"] = True
        
        # Save results
        results_file = accessibility_results_dir / "sensory_considerations_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.adhd_critical
    def test_quick_actions_adhd_accessibility(
        self, 
        page: Page, 
        accessibility_results_dir: Path
    ):
        """Test quick action buttons ADHD-specific accessibility."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Quick actions are critical for ADHD executive function support
        quick_action_buttons = page.query_selector_all("button[onclick*='quickAction']")
        
        results = {
            "total_quick_actions": len(quick_action_buttons),
            "accessible_names": [],
            "visual_clarity": [],
            "touch_targets": [],
        }
        
        assert len(quick_action_buttons) > 0, "Quick actions essential for ADHD support"
        
        for button in quick_action_buttons:
            # Check accessible naming
            aria_label = button.get_attribute("aria-label")
            text_content = button.inner_text().strip()
            has_name = bool(aria_label or text_content)
            results["accessible_names"].append(has_name)
            
            # Check visual clarity (icons + text for ADHD processing)
            icons = button.query_selector_all("i, svg")
            has_icon_and_text = len(icons) > 0 and bool(text_content)
            results["visual_clarity"].append(has_icon_and_text)
            
            # Check touch target size (motor considerations)
            box = button.bounding_box()
            if box:
                adequate_size = box["width"] >= 44 and box["height"] >= 44
                results["touch_targets"].append(adequate_size)
            else:
                results["touch_targets"].append(False)
        
        # All quick actions must be accessible (critical for ADHD)
        assert all(results["accessible_names"]), \
            "All quick actions must have accessible names - critical for ADHD screen reader users"
        
        assert all(results["visual_clarity"]), \
            "Quick actions need both icons and text for ADHD visual processing"
        
        assert all(results["touch_targets"]), \
            "Quick action touch targets must be 44x44px minimum for motor accessibility"
        
        # Save results
        results_file = accessibility_results_dir / "quick_actions_adhd_accessibility_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.adhd_critical 
    def test_chat_interface_adhd_accessibility(
        self, 
        page: Page, 
        accessibility_results_dir: Path
    ):
        """Test chat interface ADHD-specific accessibility."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Chat interface is core ADHD support - must be fully accessible
        chat_input = page.locator("#chat-input")
        expect(chat_input).to_be_visible()
        
        results = {
            "input_clearly_labeled": False,
            "send_button_accessible": False,
            "response_area_identified": False,
            "thinking_indicator_accessible": False,
        }
        
        # Check input labeling
        input_element = page.query_selector("#chat-input")
        input_label = page.query_selector("label[for='chat-input']")
        input_aria_label = input_element.get_attribute("aria-label") if input_element else None
        input_placeholder = input_element.get_attribute("placeholder") if input_element else None
        
        results["input_clearly_labeled"] = bool(input_label or input_aria_label or input_placeholder)
        
        # Check send button
        send_button = page.query_selector("button[onclick*='sendMessage']")
        if send_button:
            send_aria_label = send_button.get_attribute("aria-label")
            send_text = send_button.inner_text().strip()
            results["send_button_accessible"] = bool(send_aria_label or send_text)
        
        # Check response area
        messages_area = page.query_selector("#chat-messages")
        if messages_area:
            area_aria_label = messages_area.get_attribute("aria-label")
            area_role = messages_area.get_attribute("role")
            results["response_area_identified"] = bool(area_aria_label or area_role == "log")
        
        # Test thinking indicator accessibility
        chat_input.fill("test message")
        page.click("button[onclick*='sendMessage']")
        
        # Look for thinking indicator
        page.wait_for_timeout(500)  # Brief wait for thinking indicator
        thinking_elements = page.query_selector_all(".thinking, [aria-live], [role='status']")
        results["thinking_indicator_accessible"] = len(thinking_elements) > 0
        
        # All chat interface elements must be accessible for ADHD users
        assert results["input_clearly_labeled"], \
            "Chat input must be clearly labeled for ADHD screen reader users"
        
        assert results["send_button_accessible"], \
            "Send button must be accessible for ADHD users"
        
        assert results["response_area_identified"], \
            "Chat response area must be identified for ADHD screen reader users"
        
        # Save results
        results_file = accessibility_results_dir / "chat_interface_adhd_accessibility_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)