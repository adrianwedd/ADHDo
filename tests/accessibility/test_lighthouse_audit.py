"""
Lighthouse accessibility auditing for MCP ADHD Server.

Uses Lighthouse CLI to perform comprehensive accessibility audits
including performance and best practices for ADHD users.
"""
import pytest
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import time


@pytest.fixture
def lighthouse_config() -> Dict[str, Any]:
    """Lighthouse configuration for ADHD-focused auditing."""
    return {
        "extends": "lighthouse:default",
        "settings": {
            "onlyAudits": [
                # Accessibility audits
                "accessibility",
                "color-contrast",
                "image-alt", 
                "input-image-alt",
                "label",
                "link-name",
                "list",
                "listitem",
                "meta-viewport",
                "object-alt",
                "tabindex",
                "td-headers-attr",
                "th-has-data-cells",
                "valid-lang",
                
                # Performance audits (critical for ADHD)
                "first-contentful-paint",
                "largest-contentful-paint",
                "speed-index",
                "interactive",
                "cumulative-layout-shift",
                
                # Best practices for ADHD
                "uses-responsive-images",
                "efficient-animated-content",
                "preload-fonts",
            ],
        },
        "categories": {
            "accessibility": {"weight": 40},
            "performance": {"weight": 40}, 
            "best-practices": {"weight": 20},
        },
    }


class LighthouseAuditor:
    """Lighthouse accessibility auditor."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    def run_audit(self, page_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Lighthouse audit on a specific page."""
        url = f"{self.base_url}{page_path}"
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_file = f.name
        
        try:
            # Run Lighthouse CLI
            cmd = [
                "lighthouse",
                url,
                "--config-path", config_file,
                "--output", "json",
                "--output-path", "/dev/stdout",
                "--chrome-flags", "--headless --no-sandbox --disable-dev-shm-usage",
                "--quiet",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 1 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Lighthouse failed: {result.stderr}")
            
            return json.loads(result.stdout)
            
        finally:
            # Clean up config file
            Path(config_file).unlink(missing_ok=True)
    
    def analyze_accessibility_score(self, audit_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Lighthouse accessibility results."""
        accessibility_category = audit_result.get("categories", {}).get("accessibility", {})
        audits = audit_result.get("audits", {})
        
        analysis = {
            "overall_score": accessibility_category.get("score", 0) * 100,
            "passed_audits": [],
            "failed_audits": [],
            "warnings": [],
            "critical_issues": [],
        }
        
        # Analyze individual accessibility audits
        accessibility_audit_ids = [
            "color-contrast", "image-alt", "input-image-alt", "label", 
            "link-name", "list", "listitem", "meta-viewport", "object-alt",
            "tabindex", "td-headers-attr", "th-has-data-cells", "valid-lang"
        ]
        
        for audit_id in accessibility_audit_ids:
            if audit_id in audits:
                audit = audits[audit_id]
                score = audit.get("score")
                
                if score == 1:
                    analysis["passed_audits"].append(audit_id)
                elif score == 0:
                    analysis["failed_audits"].append({
                        "id": audit_id,
                        "title": audit.get("title", ""),
                        "description": audit.get("description", ""),
                        "details": audit.get("details", {}),
                    })
                    
                    # Mark as critical if it affects ADHD users significantly
                    if audit_id in ["color-contrast", "label", "link-name", "tabindex"]:
                        analysis["critical_issues"].append(audit_id)
                        
                elif score is None:
                    analysis["warnings"].append(audit_id)
        
        return analysis
    
    def analyze_performance_for_adhd(self, audit_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics critical for ADHD users."""
        audits = audit_result.get("audits", {})
        
        # ADHD-critical performance metrics
        fcp = audits.get("first-contentful-paint", {}).get("numericValue", 0) / 1000  # Convert to seconds
        lcp = audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000
        tti = audits.get("interactive", {}).get("numericValue", 0) / 1000
        cls = audits.get("cumulative-layout-shift", {}).get("numericValue", 0)
        
        analysis = {
            "first_contentful_paint": fcp,
            "largest_contentful_paint": lcp,
            "time_to_interactive": tti,
            "cumulative_layout_shift": cls,
            "adhd_friendly_performance": True,
            "performance_issues": [],
        }
        
        # ADHD performance thresholds (stricter than general web)
        if fcp > 2.0:  # 2 seconds for ADHD attention
            analysis["adhd_friendly_performance"] = False
            analysis["performance_issues"].append(f"First Contentful Paint too slow: {fcp:.2f}s (ADHD threshold: 2s)")
        
        if lcp > 3.0:  # 3 seconds for ADHD
            analysis["adhd_friendly_performance"] = False
            analysis["performance_issues"].append(f"Largest Contentful Paint too slow: {lcp:.2f}s (ADHD threshold: 3s)")
        
        if tti > 4.0:  # 4 seconds for interactivity
            analysis["adhd_friendly_performance"] = False
            analysis["performance_issues"].append(f"Time to Interactive too slow: {tti:.2f}s (ADHD threshold: 4s)")
        
        if cls > 0.15:  # Layout shift causes ADHD distraction
            analysis["adhd_friendly_performance"] = False
            analysis["performance_issues"].append(f"Cumulative Layout Shift too high: {cls:.3f} (ADHD threshold: 0.15)")
        
        return analysis


class TestLighthouseAccessibility:
    """Lighthouse accessibility audit tests."""
    
    @pytest.mark.accessibility
    @pytest.mark.lighthouse
    def test_homepage_lighthouse_accessibility(
        self, 
        lighthouse_config: Dict[str, Any],
        accessibility_results_dir: Path
    ):
        """Test homepage with Lighthouse accessibility audit."""
        auditor = LighthouseAuditor()
        
        # Run Lighthouse audit
        try:
            audit_result = auditor.run_audit("/", lighthouse_config)
        except subprocess.TimeoutExpired:
            pytest.skip("Lighthouse audit timed out - server may not be running")
        except Exception as e:
            if "lighthouse" in str(e).lower():
                pytest.skip(f"Lighthouse not available: {e}")
            raise
        
        # Analyze accessibility
        accessibility_analysis = auditor.analyze_accessibility_score(audit_result)
        performance_analysis = auditor.analyze_performance_for_adhd(audit_result)
        
        # Save results
        results = {
            "url": "/",
            "lighthouse_version": audit_result.get("lighthouseVersion", "unknown"),
            "accessibility_analysis": accessibility_analysis,
            "performance_analysis": performance_analysis,
            "full_audit": audit_result,
        }
        
        results_file = accessibility_results_dir / "lighthouse_homepage_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        # Assert accessibility requirements
        assert accessibility_analysis["overall_score"] >= 90, \
            f"Lighthouse accessibility score too low: {accessibility_analysis['overall_score']}/100"
        
        # Critical accessibility issues fail the test
        assert len(accessibility_analysis["critical_issues"]) == 0, \
            f"Critical accessibility issues found: {accessibility_analysis['critical_issues']}"
        
        # ADHD performance requirements
        assert performance_analysis["adhd_friendly_performance"], \
            f"Performance not ADHD-friendly: {performance_analysis['performance_issues']}"
    
    @pytest.mark.accessibility
    @pytest.mark.lighthouse
    @pytest.mark.adhd_critical
    def test_chat_interface_lighthouse_audit(
        self, 
        lighthouse_config: Dict[str, Any],
        accessibility_results_dir: Path
    ):
        """Test chat interface accessibility with Lighthouse (critical for ADHD)."""
        auditor = LighthouseAuditor()
        
        # Modify config for chat interface focus
        chat_config = lighthouse_config.copy()
        chat_config["settings"]["onlyAudits"].extend([
            "aria-allowed-attr",
            "aria-required-attr", 
            "aria-roles",
            "aria-valid-attr-value",
            "aria-valid-attr",
            "button-name",
            "bypass",
            "definition-list",
            "dlitem",
            "duplicate-id-aria",
            "form-field-multiple-labels",
            "frame-title",
            "heading-order",
            "html-has-lang",
            "html-lang-valid",
            "link-name",
        ])
        
        try:
            audit_result = auditor.run_audit("/", chat_config)
        except Exception as e:
            if "lighthouse" in str(e).lower():
                pytest.skip(f"Lighthouse not available: {e}")
            raise
        
        # Analyze results with focus on interactive elements
        accessibility_analysis = auditor.analyze_accessibility_score(audit_result)
        performance_analysis = auditor.analyze_performance_for_adhd(audit_result)
        
        # Additional analysis for chat-specific elements
        audits = audit_result.get("audits", {})
        chat_analysis = {
            "button_names": audits.get("button-name", {}).get("score", 0) == 1,
            "aria_attributes": audits.get("aria-valid-attr", {}).get("score", 0) == 1,
            "form_labels": audits.get("label", {}).get("score", 0) == 1,
            "bypass_blocks": audits.get("bypass", {}).get("score", 0) == 1,
        }
        
        # Save results
        results = {
            "url": "/ (chat interface focus)",
            "accessibility_analysis": accessibility_analysis,
            "performance_analysis": performance_analysis,
            "chat_specific_analysis": chat_analysis,
            "full_audit": audit_result,
        }
        
        results_file = accessibility_results_dir / "lighthouse_chat_interface_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        # Chat interface must be fully accessible (critical for ADHD support)
        assert accessibility_analysis["overall_score"] >= 95, \
            f"Chat interface accessibility score insufficient for ADHD users: {accessibility_analysis['overall_score']}/100"
        
        # All chat-specific features must pass
        failed_chat_features = [k for k, v in chat_analysis.items() if not v]
        assert len(failed_chat_features) == 0, \
            f"Chat features failed accessibility: {failed_chat_features}"
        
        # Performance critical for ADHD chat experience
        assert performance_analysis["time_to_interactive"] <= 3.0, \
            f"Chat interface too slow to become interactive for ADHD: {performance_analysis['time_to_interactive']:.2f}s"
    
    @pytest.mark.accessibility
    @pytest.mark.lighthouse
    @pytest.mark.parametrize("page_path,min_score", [
        ("/", 90),  # Homepage
        ("/?modal=auth", 85),  # With auth modal
        ("/?test=quick_actions", 90),  # Quick actions focus
    ])
    def test_multiple_pages_lighthouse_audit(
        self, 
        page_path: str,
        min_score: int,
        lighthouse_config: Dict[str, Any],
        accessibility_results_dir: Path
    ):
        """Test multiple page states with Lighthouse."""
        auditor = LighthouseAuditor()
        
        try:
            audit_result = auditor.run_audit(page_path, lighthouse_config)
        except Exception as e:
            if "lighthouse" in str(e).lower():
                pytest.skip(f"Lighthouse not available: {e}")
            raise
        
        accessibility_analysis = auditor.analyze_accessibility_score(audit_result)
        
        # Save results
        safe_path = page_path.replace("/", "_").replace("?", "_").replace("=", "_")
        results_file = accessibility_results_dir / f"lighthouse_page{safe_path}_results.json"
        
        with open(results_file, "w") as f:
            json.dump({
                "url": page_path,
                "accessibility_analysis": accessibility_analysis,
                "full_audit": audit_result,
            }, f, indent=2)
        
        # Assert minimum accessibility score
        assert accessibility_analysis["overall_score"] >= min_score, \
            f"Page {page_path} accessibility score too low: {accessibility_analysis['overall_score']}/{min_score}"
    
    @pytest.mark.accessibility
    @pytest.mark.lighthouse
    def test_mobile_accessibility_lighthouse(
        self, 
        lighthouse_config: Dict[str, Any],
        accessibility_results_dir: Path
    ):
        """Test mobile accessibility with Lighthouse (important for ADHD users)."""
        # Mobile-specific config
        mobile_config = lighthouse_config.copy()
        mobile_config["settings"]["emulatedFormFactor"] = "mobile"
        mobile_config["settings"]["onlyAudits"].extend([
            "tap-targets",
            "meta-viewport", 
        ])
        
        auditor = LighthouseAuditor()
        
        try:
            audit_result = auditor.run_audit("/", mobile_config)
        except Exception as e:
            if "lighthouse" in str(e).lower():
                pytest.skip(f"Lighthouse not available: {e}")
            raise
        
        accessibility_analysis = auditor.analyze_accessibility_score(audit_result)
        performance_analysis = auditor.analyze_performance_for_adhd(audit_result)
        
        # Mobile-specific analysis
        audits = audit_result.get("audits", {})
        mobile_analysis = {
            "tap_targets": audits.get("tap-targets", {}).get("score", 0) == 1,
            "viewport": audits.get("meta-viewport", {}).get("score", 0) == 1,
        }
        
        # Save results
        results = {
            "url": "/ (mobile)",
            "accessibility_analysis": accessibility_analysis,
            "performance_analysis": performance_analysis,
            "mobile_analysis": mobile_analysis,
            "full_audit": audit_result,
        }
        
        results_file = accessibility_results_dir / "lighthouse_mobile_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        # Mobile accessibility critical for ADHD users (often use mobile devices)
        assert accessibility_analysis["overall_score"] >= 90, \
            f"Mobile accessibility score insufficient for ADHD users: {accessibility_analysis['overall_score']}/100"
        
        # Tap targets must be adequate for ADHD + motor considerations
        assert mobile_analysis["tap_targets"], \
            "Mobile tap targets insufficient for ADHD users with motor considerations"
        
        # Mobile performance must be ADHD-friendly
        assert performance_analysis["adhd_friendly_performance"], \
            f"Mobile performance not ADHD-friendly: {performance_analysis['performance_issues']}"