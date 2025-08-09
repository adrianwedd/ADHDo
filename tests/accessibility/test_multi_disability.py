"""
Multi-Disability Intersection Accessibility Testing for MCP ADHD Server.

Tests accessibility for users with ADHD plus additional disabilities,
ensuring the system works for diverse accessibility needs.
"""
import pytest
from playwright.sync_api import Page, expect
import json
from pathlib import Path
from typing import Dict, List, Any


class TestMultiDisabilityAccessibility:
    """Test accessibility for users with multiple disabilities including ADHD."""
    
    @pytest.mark.accessibility
    @pytest.mark.multi_disability
    @pytest.mark.adhd_critical
    def test_screen_reader_plus_adhd(
        self, 
        page: Page, 
        screen_reader_tester,
        adhd_accessibility_tester,
        accessibility_results_dir: Path
    ):
        """Test for users with ADHD who also use screen readers."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize testers
        sr_tester = screen_reader_tester(page)
        adhd_tester = adhd_accessibility_tester(page)
        
        # Test screen reader features with ADHD considerations
        aria_results = sr_tester.check_aria_labels()
        heading_results = sr_tester.check_heading_structure()
        landmark_results = sr_tester.check_landmarks()
        cognitive_results = adhd_tester.check_cognitive_load()
        
        # Screen reader + ADHD requirements
        results = {
            "screen_reader_compatible": True,
            "adhd_cognitive_friendly": True,
            "intersection_issues": [],
        }
        
        # ARIA labels must be concise for ADHD attention spans
        verbose_labels = [label for label in aria_results.get("good_labels", []) 
                         if len(str(label)) > 50]  # Arbitrary threshold
        
        if verbose_labels:
            results["intersection_issues"].append(
                "ARIA labels too verbose for ADHD + screen reader users"
            )
        
        # Heading structure must be logical but not overwhelming
        if len(heading_results.get("levels", [])) > 20:
            results["intersection_issues"].append(
                "Too many headings may overwhelm ADHD + screen reader users"
            )
        
        # Cognitive load must be manageable for dual processing
        if cognitive_results["cognitive_load_score"] > 4.0:  # Lower threshold for dual processing
            results["intersection_issues"].append(
                "Cognitive load too high for ADHD + screen reader dual processing"
            )
        
        # Test quick actions with screen reader
        quick_actions = page.query_selector_all("button[onclick*='quickAction']")
        for button in quick_actions:
            aria_label = button.get_attribute("aria-label")
            text = button.inner_text().strip()
            
            # Quick actions need both visual and screen reader friendly names
            if not aria_label and not text:
                results["intersection_issues"].append(
                    f"Quick action missing accessible name for screen reader + ADHD"
                )
            elif aria_label and len(aria_label) > 30:  # Too verbose for ADHD
                results["intersection_issues"].append(
                    f"Quick action ARIA label too verbose for ADHD attention span"
                )
        
        # Assert no intersection issues
        assert len(results["intersection_issues"]) == 0, \
            f"Screen reader + ADHD intersection issues: {results['intersection_issues']}"
        
        # Save results
        results_file = accessibility_results_dir / "screen_reader_adhd_intersection_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.multi_disability
    @pytest.mark.adhd_critical
    def test_motor_impairment_plus_adhd(
        self, 
        page: Page, 
        keyboard_navigation_tester,
        adhd_accessibility_tester,
        accessibility_results_dir: Path
    ):
        """Test for users with ADHD who also have motor impairments."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize testers
        kb_tester = keyboard_navigation_tester(page)
        adhd_tester = adhd_accessibility_tester(page)
        
        # Test keyboard navigation with ADHD considerations
        tab_order = kb_tester.test_tab_order()
        focus_visible = kb_tester.test_focus_visible()
        cognitive_results = adhd_tester.check_cognitive_load()
        
        results = {
            "keyboard_accessible": True,
            "adhd_friendly": True,
            "intersection_issues": [],
        }
        
        # Tab order must be logical but not too long for ADHD attention
        if len(tab_order) > 25:  # Arbitrary threshold for ADHD + motor impairment
            results["intersection_issues"].append(
                "Tab order too long for ADHD + motor impairment users"
            )
        
        # Test touch target sizes for motor + ADHD (need larger targets)
        interactive_elements = page.query_selector_all("button, a, input, select")
        small_targets = []
        
        for element in interactive_elements:
            box = element.bounding_box()
            if box:
                # Larger minimum for motor + ADHD (easier to hit when distracted)
                if box["width"] < 48 or box["height"] < 48:
                    small_targets.append(element.tag_name)
        
        if small_targets:
            results["intersection_issues"].append(
                f"Touch targets too small for motor + ADHD: {set(small_targets)}"
            )
        
        # Test critical elements (emergency buttons) have extra large targets
        emergency_buttons = page.query_selector_all("button[class*='red'], button[onclick*='overwhelmed']")
        for button in emergency_buttons:
            box = button.bounding_box()
            if box and (box["width"] < 60 or box["height"] < 60):
                results["intersection_issues"].append(
                    "Emergency buttons need extra large targets for motor + ADHD crisis situations"
                )
        
        # Test spacing between interactive elements
        buttons = page.query_selector_all("button")
        if len(buttons) > 1:
            for i in range(len(buttons) - 1):
                box1 = buttons[i].bounding_box()
                box2 = buttons[i + 1].bounding_box()
                
                if box1 and box2:
                    # Calculate distance between buttons
                    distance_x = abs(box1["x"] - box2["x"])
                    distance_y = abs(box1["y"] - box2["y"])
                    
                    # Need more spacing for motor + ADHD (avoid accidental activation)
                    min_spacing = 16  # pixels
                    if distance_x < min_spacing and distance_y < min_spacing:
                        results["intersection_issues"].append(
                            "Insufficient spacing between buttons for motor + ADHD users"
                        )
                        break
        
        # Assert no intersection issues
        assert len(results["intersection_issues"]) == 0, \
            f"Motor impairment + ADHD intersection issues: {results['intersection_issues']}"
        
        # Save results
        results_file = accessibility_results_dir / "motor_impairment_adhd_intersection_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.multi_disability
    @pytest.mark.adhd_critical
    def test_visual_impairment_plus_adhd(
        self, 
        page: Page, 
        color_contrast_tester,
        adhd_accessibility_tester,
        accessibility_results_dir: Path
    ):
        """Test for users with ADHD who also have visual impairments."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize testers
        contrast_tester = color_contrast_tester(page)
        adhd_tester = adhd_accessibility_tester(page)
        
        # Test high contrast + ADHD considerations
        contrast_results = contrast_tester.check_contrast_ratios()
        cognitive_results = adhd_tester.check_cognitive_load()
        
        results = {
            "high_contrast_compatible": True,
            "adhd_friendly": True,
            "intersection_issues": [],
        }
        
        # Higher contrast requirements for visual + ADHD
        enhanced_contrast_min = 7.0  # AAA level for visual + ADHD
        
        low_contrast_elements = [
            result for result in contrast_results 
            if result.get("ratio", 0) < enhanced_contrast_min
        ]
        
        if low_contrast_elements:
            results["intersection_issues"].append(
                f"Insufficient contrast for visual impairment + ADHD: {len(low_contrast_elements)} elements"
            )
        
        # Test zoom compatibility (visual impairment) + cognitive load (ADHD)
        zoom_levels = [150, 200, 250]  # Percent zoom
        
        for zoom in zoom_levels:
            page.evaluate(f"""
                document.body.style.fontSize = '{zoom}%';
                document.body.style.transform = 'scale({zoom/100})';
                document.body.style.transformOrigin = 'top left';
            """)
            
            page.wait_for_timeout(500)
            
            # Check if critical elements still visible and usable
            chat_input = page.query_selector("#chat-input")
            quick_actions = page.query_selector_all("button[onclick*='quickAction']")
            
            if not chat_input or len(quick_actions) == 0:
                results["intersection_issues"].append(
                    f"Critical elements not usable at {zoom}% zoom for visual + ADHD users"
                )
                break
            
            # Check if cognitive load increases with zoom (text reflow issues)
            cognitive_at_zoom = adhd_tester.check_cognitive_load()
            if cognitive_at_zoom["cognitive_load_score"] > cognitive_results["cognitive_load_score"] + 2:
                results["intersection_issues"].append(
                    f"Cognitive load increases too much at {zoom}% zoom"
                )
        
        # Reset zoom
        page.evaluate("document.body.style.fontSize = ''; document.body.style.transform = '';")
        
        # Test color coding alternatives (visual impairment) with ADHD processing
        color_coded_elements = page.query_selector_all(".text-red, .text-green, .bg-red, .bg-green")
        
        for element in color_coded_elements:
            # Must have non-color indicators that are ADHD-processing friendly
            icons = element.query_selector_all("i[class*='fa'], svg")
            text_indicators = element.query_selector_all(".sr-only")
            
            if not icons and not text_indicators:
                results["intersection_issues"].append(
                    "Color-coded elements need visual alternatives for visual + ADHD users"
                )
        
        # Assert no intersection issues
        assert len(results["intersection_issues"]) == 0, \
            f"Visual impairment + ADHD intersection issues: {results['intersection_issues']}"
        
        # Save results
        results_file = accessibility_results_dir / "visual_impairment_adhd_intersection_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.multi_disability
    @pytest.mark.adhd_critical
    def test_hearing_impairment_plus_adhd(
        self, 
        page: Page, 
        adhd_accessibility_tester,
        accessibility_results_dir: Path
    ):
        """Test for users with ADHD who also have hearing impairments."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize ADHD tester
        adhd_tester = adhd_accessibility_tester(page)
        cognitive_results = adhd_tester.check_cognitive_load()
        
        results = {
            "visual_alternatives_present": True,
            "adhd_friendly": True,
            "intersection_issues": [],
        }
        
        # Test visual alternatives for audio feedback
        audio_elements = page.query_selector_all("audio, video, [data-sound]")
        
        for element in audio_elements:
            # Must have visual alternatives (captions, visual feedback)
            captions = element.query_selector_all("[data-captions], .captions, .subtitles")
            visual_feedback = element.query_selector_all(".visual-indicator, .status-indicator")
            
            if not captions and not visual_feedback:
                results["intersection_issues"].append(
                    "Audio elements need visual alternatives for hearing + ADHD users"
                )
        
        # Test notification systems (critical for ADHD users who can't hear audio alerts)
        page.evaluate("""
            // Simulate notification trigger
            if (typeof showNotification === 'function') {
                showNotification('Test notification');
            }
        """)
        
        # Look for visual notifications
        visual_notifications = page.query_selector_all(
            ".notification, .alert, .toast, [role='alert'], [aria-live]"
        )
        
        if len(visual_notifications) == 0:
            results["intersection_issues"].append(
                "Visual notifications required for hearing + ADHD users"
            )
        
        # Test visual notifications don't overwhelm ADHD users
        for notification in visual_notifications:
            # Check if notification has dismiss mechanism
            dismiss_button = notification.query_selector("button, .close, [onclick*='dismiss']")
            if not dismiss_button:
                results["intersection_issues"].append(
                    "Visual notifications need dismiss option for ADHD attention management"
                )
        
        # Test chat interface visual feedback (hearing users rely on visual cues)
        chat_input = page.locator("#chat-input")
        chat_input.fill("test message")
        page.click("button[onclick*='sendMessage']")
        
        # Look for visual feedback that message was sent/received
        page.wait_for_timeout(1000)
        visual_feedback_elements = page.query_selector_all(
            ".thinking, .loading, .status-indicator, [aria-live]"
        )
        
        if len(visual_feedback_elements) == 0:
            results["intersection_issues"].append(
                "Chat needs visual feedback for hearing + ADHD users"
            )
        
        # Test error handling visual clarity
        page.goto("/")  # Reset
        page.click("button:has-text('Sign In')")
        page.wait_for_selector("#auth-modal", state="visible")
        
        # Try empty form submission
        page.click("button[type='submit']")
        
        # Visual error indicators must be clear for hearing + ADHD
        visual_errors = page.query_selector_all(
            ".error, [aria-invalid='true'], .text-red, .border-red"
        )
        
        for error in visual_errors:
            # Visual errors must be prominent for hearing users
            styles = page.evaluate("getComputedStyle(arguments[0])", error)
            # Check if visually distinct (would need proper color analysis)
            if not styles:  # Placeholder check
                results["intersection_issues"].append(
                    "Visual errors must be prominent for hearing + ADHD users"
                )
        
        # Assert no intersection issues
        assert len(results["intersection_issues"]) == 0, \
            f"Hearing impairment + ADHD intersection issues: {results['intersection_issues']}"
        
        # Save results
        results_file = accessibility_results_dir / "hearing_impairment_adhd_intersection_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.multi_disability
    @pytest.mark.adhd_critical
    def test_cognitive_disability_plus_adhd(
        self, 
        page: Page, 
        adhd_accessibility_tester,
        accessibility_results_dir: Path
    ):
        """Test for users with ADHD plus other cognitive disabilities."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize ADHD tester
        adhd_tester = adhd_accessibility_tester(page)
        cognitive_results = adhd_tester.check_cognitive_load()
        
        results = {
            "simple_language": True,
            "clear_navigation": True,
            "intersection_issues": [],
        }
        
        # Extra stringent cognitive load for dual cognitive disabilities
        max_cognitive_score = 3.0  # Much lower for dual cognitive needs
        
        if cognitive_results["cognitive_load_score"] > max_cognitive_score:
            results["intersection_issues"].append(
                f"Cognitive load too high ({cognitive_results['cognitive_load_score']}) for dual cognitive disabilities"
            )
        
        # Test language complexity
        text_elements = page.query_selector_all("p, div, span, h1, h2, h3, button")
        complex_language_elements = []
        
        for element in text_elements:
            text = element.inner_text().strip()
            if text and len(text) > 100:  # Long text may be complex
                word_count = len(text.split())
                if word_count > 20:  # Arbitrary threshold
                    complex_language_elements.append(element.tag_name)
        
        if complex_language_elements:
            results["intersection_issues"].append(
                f"Language too complex for cognitive + ADHD users: {set(complex_language_elements)}"
            )
        
        # Test navigation simplicity
        nav_elements = page.query_selector_all("nav, [role='navigation']")
        for nav in nav_elements:
            nav_items = nav.query_selector_all("a, button")
            if len(nav_items) > 7:  # Miller's rule for cognitive load
                results["intersection_issues"].append(
                    f"Navigation too complex ({len(nav_items)} items) for cognitive + ADHD"
                )
        
        # Test form simplicity
        forms = page.query_selector_all("form")
        for form in forms:
            form_fields = form.query_selector_all("input, select, textarea")
            if len(form_fields) > 5:  # Keep forms simple
                # Check if form has clear sectioning
                sections = form.query_selector_all("fieldset, .section, .step")
                if len(sections) == 0:
                    results["intersection_issues"].append(
                        f"Complex form needs sectioning for cognitive + ADHD users"
                    )
        
        # Test help/explanation availability
        help_elements = page.query_selector_all("[aria-describedby], .help-text, .explanation")
        interactive_elements = page.query_selector_all("button, input, select, a")
        
        help_ratio = len(help_elements) / max(len(interactive_elements), 1)
        if help_ratio < 0.3:  # At least 30% of interactive elements should have help
            results["intersection_issues"].append(
                "Insufficient help/explanation for cognitive + ADHD users"
            )
        
        # Test error prevention and correction
        page.click("button:has-text('Sign In')")
        page.wait_for_selector("#auth-modal", state="visible")
        
        # Check if form has validation hints before submission
        password_field = page.query_selector("#login-password")
        if password_field:
            validation_hint = page.query_selector("[aria-describedby*='password'], .password-requirements")
            if not validation_hint:
                results["intersection_issues"].append(
                    "Forms need validation hints for cognitive + ADHD error prevention"
                )
        
        # Assert no intersection issues
        assert len(results["intersection_issues"]) == 0, \
            f"Cognitive disability + ADHD intersection issues: {results['intersection_issues']}"
        
        # Save results
        results_file = accessibility_results_dir / "cognitive_disability_adhd_intersection_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.accessibility
    @pytest.mark.multi_disability
    @pytest.mark.adhd_critical
    def test_multiple_intersections(
        self, 
        page: Page, 
        adhd_accessibility_tester,
        accessibility_results_dir: Path
    ):
        """Test for users with ADHD plus multiple other disabilities."""
        page.goto("/")
        page.wait_for_load_state("networkidle")
        
        # Initialize ADHD tester
        adhd_tester = adhd_accessibility_tester(page)
        cognitive_results = adhd_tester.check_cognitive_load()
        
        results = {
            "multiple_accommodation_support": True,
            "intersection_issues": [],
        }
        
        # Test accommodation preferences persistence
        # (Users with multiple disabilities need stable accommodations)
        page.evaluate("""
            localStorage.setItem('accessibility_preferences', JSON.stringify({
                'high_contrast': true,
                'reduced_motion': true,
                'large_text': true,
                'simplified_interface': true
            }));
        """)
        
        # Reload and check if preferences persist
        page.reload()
        page.wait_for_load_state("networkidle")
        
        preferences = page.evaluate("JSON.parse(localStorage.getItem('accessibility_preferences') || '{}')")
        if not preferences:
            results["intersection_issues"].append(
                "Accessibility preferences don't persist for multi-disability users"
            )
        
        # Test ultra-simplified mode for multiple disabilities + ADHD
        page.evaluate("""
            document.body.classList.add('ultra-simple-mode');
        """)
        
        # Check if interface becomes more accessible
        # Fewer distractions
        animation_elements = page.query_selector_all("[class*='animate'], [class*='transition']")
        if len(animation_elements) > 2:  # Allow minimal animations only
            results["intersection_issues"].append(
                "Too many animations remain in ultra-simple mode"
            )
        
        # Larger touch targets
        all_buttons = page.query_selector_all("button")
        small_buttons = []
        
        for button in all_buttons:
            box = button.bounding_box()
            if box and (box["width"] < 60 or box["height"] < 60):
                small_buttons.append(button.tag_name)
        
        if small_buttons:
            results["intersection_issues"].append(
                f"Buttons too small in ultra-simple mode: {len(small_buttons)}"
            )
        
        # Test emergency/crisis features work with all accommodations
        emergency_button = page.query_selector("button[onclick*='overwhelmed']")
        if emergency_button:
            # Emergency button must work with all accessibility features
            box = emergency_button.bounding_box()
            if box and (box["width"] < 80 or box["height"] < 80):
                results["intersection_issues"].append(
                    "Emergency button too small for multi-disability + ADHD users"
                )
            
            # Must have multiple identification methods
            aria_label = emergency_button.get_attribute("aria-label")
            text_content = emergency_button.inner_text().strip()
            icons = emergency_button.query_selector_all("i, svg")
            
            identification_methods = sum([
                bool(aria_label),
                bool(text_content),
                len(icons) > 0
            ])
            
            if identification_methods < 2:
                results["intersection_issues"].append(
                    "Emergency button needs multiple identification methods"
                )
        
        # Test comprehensive keyboard navigation for all disabilities
        page.press("body", "Tab")
        focused_element = page.evaluate("document.activeElement.tagName")
        
        if not focused_element or focused_element.lower() == "body":
            results["intersection_issues"].append(
                "Keyboard navigation fails for multi-disability users"
            )
        
        # Assert no intersection issues
        assert len(results["intersection_issues"]) == 0, \
            f"Multiple disability + ADHD intersection issues: {results['intersection_issues']}"
        
        # Save results
        results_file = accessibility_results_dir / "multiple_intersections_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)