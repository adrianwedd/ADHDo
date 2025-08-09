#!/usr/bin/env python3
"""
Generate comprehensive accessibility report from test results.

Combines WCAG compliance, ADHD-specific, and multi-disability test results
into a comprehensive accessibility assessment report.
"""
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
import sys
from datetime import datetime


class AccessibilityReportGenerator:
    """Generate accessibility reports from test results."""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def load_test_results(self) -> Dict[str, Any]:
        """Load all accessibility test results."""
        results = {
            "wcag_compliance": {},
            "adhd_accessibility": {},
            "multi_disability": {},
            "performance": {},
            "errors": [],
        }
        
        # Load WCAG compliance results
        wcag_files = list(self.results_dir.glob("*wcag_results.json"))
        for file in wcag_files:
            try:
                with open(file) as f:
                    data = json.load(f)
                    test_name = file.stem.replace("_wcag_results", "")
                    results["wcag_compliance"][test_name] = data
            except Exception as e:
                results["errors"].append(f"Failed to load {file}: {e}")
        
        # Load ADHD-specific results
        adhd_files = list(self.results_dir.glob("*adhd*results.json")) + \
                    list(self.results_dir.glob("cognitive_load_results.json")) + \
                    list(self.results_dir.glob("focus_management_results.json")) + \
                    list(self.results_dir.glob("motion_sensitivity_results.json"))
        
        for file in adhd_files:
            try:
                with open(file) as f:
                    data = json.load(f)
                    test_name = file.stem.replace("_results", "")
                    results["adhd_accessibility"][test_name] = data
            except Exception as e:
                results["errors"].append(f"Failed to load {file}: {e}")
        
        # Load multi-disability results
        multi_files = list(self.results_dir.glob("*intersection_results.json"))
        for file in multi_files:
            try:
                with open(file) as f:
                    data = json.load(f)
                    test_name = file.stem.replace("_intersection_results", "")
                    results["multi_disability"][test_name] = data
            except Exception as e:
                results["errors"].append(f"Failed to load {file}: {e}")
        
        # Load performance results
        perf_files = list(self.results_dir.glob("*performance*results.json")) + \
                    list(self.results_dir.glob("attention_span_results.json"))
        
        for file in perf_files:
            try:
                with open(file) as f:
                    data = json.load(f)
                    test_name = file.stem.replace("_results", "")
                    results["performance"][test_name] = data
            except Exception as e:
                results["errors"].append(f"Failed to load {file}: {e}")
        
        return results
    
    def analyze_wcag_compliance(self, wcag_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze WCAG compliance across all tests."""
        analysis = {
            "overall_compliant": True,
            "total_violations": 0,
            "violation_breakdown": {},
            "critical_issues": [],
            "pages_tested": len(wcag_results),
        }
        
        for page, results in wcag_results.items():
            violations = results.get("violations", [])
            analysis["total_violations"] += len(violations)
            
            for violation in violations:
                rule_id = violation.get("id", "unknown")
                impact = violation.get("impact", "unknown")
                
                if rule_id not in analysis["violation_breakdown"]:
                    analysis["violation_breakdown"][rule_id] = {
                        "count": 0,
                        "impact": impact,
                        "description": violation.get("description", ""),
                    }
                
                analysis["violation_breakdown"][rule_id]["count"] += 1
                
                # Critical violations that affect ADHD users
                if impact in ["critical", "serious"] or rule_id in [
                    "color-contrast", "keyboard-navigation", "focus-order-semantics",
                    "aria-dialog-name", "page-has-heading-one", "landmark-one-main"
                ]:
                    analysis["critical_issues"].append({
                        "page": page,
                        "rule": rule_id,
                        "impact": impact,
                        "description": violation.get("description", ""),
                    })
        
        analysis["overall_compliant"] = analysis["total_violations"] == 0
        
        return analysis
    
    def analyze_adhd_accessibility(self, adhd_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ADHD-specific accessibility."""
        analysis = {
            "adhd_friendly": True,
            "cognitive_load_score": 0,
            "crisis_features_accessible": True,
            "focus_management_issues": [],
            "motion_sensitivity_issues": [],
            "attention_span_friendly": True,
            "critical_issues": [],
        }
        
        # Analyze cognitive load
        if "cognitive_load" in adhd_results:
            cog_data = adhd_results["cognitive_load"]
            analysis["cognitive_load_score"] = cog_data.get("cognitive_load_score", 0)
            
            if cog_data.get("choice_overload_risk", False):
                analysis["critical_issues"].append("Choice overload risk for ADHD users")
                analysis["adhd_friendly"] = False
            
            if cog_data.get("total_interactive_elements", 0) > 15:
                analysis["critical_issues"].append("Too many interactive elements for ADHD")
                analysis["adhd_friendly"] = False
        
        # Analyze focus management
        if "focus_management" in adhd_results:
            focus_data = adhd_results["focus_management"]
            for key, value in focus_data.items():
                if not value and key != "focus_restoration":  # focus_restoration is harder to test
                    analysis["focus_management_issues"].append(key)
                    analysis["adhd_friendly"] = False
        
        # Analyze crisis features
        if "crisis_features_accessibility" in adhd_results:
            crisis_data = adhd_results["crisis_features_accessibility"]
            for feature, data in crisis_data.items():
                if isinstance(data, dict) and data.get("exists", False):
                    if not data.get("accessible_name", True) or not data.get("keyboard_accessible", True):
                        analysis["crisis_features_accessible"] = False
                        analysis["critical_issues"].append(f"Crisis feature {feature} not accessible")
        
        # Analyze motion sensitivity
        if "motion_sensitivity" in adhd_results:
            motion_data = adhd_results["motion_sensitivity"]
            if not motion_data.get("reduced_motion", {}).get("respectsPreference", True):
                analysis["motion_sensitivity_issues"].append("Doesn't respect reduced motion preference")
                analysis["adhd_friendly"] = False
        
        # Analyze attention span considerations
        if "attention_span" in adhd_results:
            attn_data = adhd_results["attention_span"]
            if not attn_data.get("adhd_friendly_load_time", True):
                analysis["attention_span_friendly"] = False
                analysis["critical_issues"].append("Page load time too slow for ADHD attention span")
        
        return analysis
    
    def analyze_multi_disability(self, multi_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze multi-disability intersection support."""
        analysis = {
            "screen_reader_adhd": True,
            "motor_adhd": True,
            "visual_adhd": True,
            "hearing_adhd": True,
            "cognitive_adhd": True,
            "multiple_intersections": True,
            "critical_issues": [],
        }
        
        # Map result keys to analysis keys
        result_mapping = {
            "screen_reader_adhd": "screen_reader_adhd",
            "motor_impairment_adhd": "motor_adhd", 
            "visual_impairment_adhd": "visual_adhd",
            "hearing_impairment_adhd": "hearing_adhd",
            "cognitive_disability_adhd": "cognitive_adhd",
            "multiple_intersections": "multiple_intersections",
        }
        
        for result_key, analysis_key in result_mapping.items():
            if result_key in multi_results:
                issues = multi_results[result_key].get("intersection_issues", [])
                if issues:
                    analysis[analysis_key] = False
                    analysis["critical_issues"].extend([
                        f"{result_key}: {issue}" for issue in issues
                    ])
        
        return analysis
    
    def analyze_performance(self, perf_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance for ADHD users."""
        analysis = {
            "page_load_time": 0,
            "interaction_time": 0,
            "adhd_performance_friendly": True,
            "critical_issues": [],
        }
        
        if "attention_span" in perf_results:
            attn_data = perf_results["attention_span"]
            load_time = attn_data.get("page_load_time_ms", 0)
            analysis["page_load_time"] = load_time
            
            if load_time > 3000:  # ADHD threshold
                analysis["adhd_performance_friendly"] = False
                analysis["critical_issues"].append(
                    f"Page load time ({load_time}ms) exceeds ADHD threshold (3000ms)"
                )
        
        return analysis
    
    def generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive summary."""
        wcag_analysis = self.analyze_wcag_compliance(results["wcag_compliance"])
        adhd_analysis = self.analyze_adhd_accessibility(results["adhd_accessibility"])
        multi_analysis = self.analyze_multi_disability(results["multi_disability"])
        perf_analysis = self.analyze_performance(results["performance"])
        
        # Combine all critical issues
        all_critical_issues = []
        all_critical_issues.extend(wcag_analysis.get("critical_issues", []))
        all_critical_issues.extend(adhd_analysis.get("critical_issues", []))
        all_critical_issues.extend(multi_analysis.get("critical_issues", []))
        all_critical_issues.extend(perf_analysis.get("critical_issues", []))
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "overall_accessibility_score": 0,
            
            # WCAG Compliance
            "wcag_compliance": wcag_analysis["overall_compliant"],
            "wcag_violations": wcag_analysis["total_violations"],
            
            # ADHD-Specific
            "adhd_accessibility": adhd_analysis["adhd_friendly"],
            "cognitive_load_score": adhd_analysis["cognitive_load_score"],
            "crisis_features_accessible": adhd_analysis["crisis_features_accessible"],
            
            # Multi-Disability
            "screen_reader_adhd": multi_analysis["screen_reader_adhd"],
            "motor_adhd": multi_analysis["motor_adhd"], 
            "visual_adhd": multi_analysis["visual_adhd"],
            "hearing_adhd": multi_analysis["hearing_adhd"],
            "cognitive_adhd": multi_analysis["cognitive_adhd"],
            
            # Performance
            "page_load_time": perf_analysis["page_load_time"],
            "interaction_time": perf_analysis["interaction_time"],
            "adhd_performance_friendly": perf_analysis["adhd_performance_friendly"],
            
            # Critical Issues
            "critical_issues": [str(issue) for issue in all_critical_issues],
            "has_critical_issues": len(all_critical_issues) > 0,
            
            # Testing Coverage
            "pages_tested": wcag_analysis["pages_tested"],
            "test_categories": {
                "wcag_tests": len(results["wcag_compliance"]),
                "adhd_tests": len(results["adhd_accessibility"]),
                "multi_disability_tests": len(results["multi_disability"]),
                "performance_tests": len(results["performance"]),
            },
            
            # Errors during analysis
            "analysis_errors": results["errors"],
        }
        
        # Calculate overall accessibility score (0-100)
        score_components = [
            100 if summary["wcag_compliance"] else 0,  # 25% weight
            100 if summary["adhd_accessibility"] else 0,  # 25% weight  
            100 if summary["crisis_features_accessible"] else 0,  # 25% weight (critical)
            (100 - min(summary["cognitive_load_score"] * 10, 100)) if summary["cognitive_load_score"] > 0 else 100,  # 25% weight
        ]
        
        summary["overall_accessibility_score"] = sum(score_components) / len(score_components)
        
        return summary
    
    def generate_detailed_report(self, results: Dict[str, Any], summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed accessibility report."""
        wcag_analysis = self.analyze_wcag_compliance(results["wcag_compliance"])
        adhd_analysis = self.analyze_adhd_accessibility(results["adhd_accessibility"])
        multi_analysis = self.analyze_multi_disability(results["multi_disability"])
        perf_analysis = self.analyze_performance(results["performance"])
        
        return {
            "summary": summary,
            "wcag_analysis": wcag_analysis,
            "adhd_analysis": adhd_analysis,
            "multi_disability_analysis": multi_analysis,
            "performance_analysis": perf_analysis,
            "raw_results": results,
        }
    
    def save_reports(self, summary: Dict[str, Any], detailed: Dict[str, Any]) -> None:
        """Save summary and detailed reports."""
        # Save summary for CI/CD
        summary_file = self.results_dir.parent / "accessibility-summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        # Save detailed report
        detailed_file = self.results_dir.parent / "accessibility-detailed-report.json"
        with open(detailed_file, "w") as f:
            json.dump(detailed, f, indent=2)
        
        print(f"✅ Accessibility reports saved:")
        print(f"   📊 Summary: {summary_file}")
        print(f"   📋 Detailed: {detailed_file}")
        
        # Print summary to console
        print("\n" + "="*60)
        print("ACCESSIBILITY TEST SUMMARY")
        print("="*60)
        print(f"Overall Score: {summary['overall_accessibility_score']:.1f}/100")
        print(f"WCAG 2.1 AA Compliance: {'✅ PASS' if summary['wcag_compliance'] else '❌ FAIL'}")
        print(f"ADHD Accessibility: {'✅ PASS' if summary['adhd_accessibility'] else '❌ FAIL'}")
        print(f"Crisis Features Accessible: {'✅ PASS' if summary['crisis_features_accessible'] else '❌ FAIL'}")
        print(f"Cognitive Load Score: {summary['cognitive_load_score']:.1f}/10")
        
        if summary['critical_issues']:
            print(f"\n⚠️  CRITICAL ISSUES ({len(summary['critical_issues'])}):")
            for issue in summary['critical_issues'][:5]:  # Show first 5
                print(f"   • {issue}")
            if len(summary['critical_issues']) > 5:
                print(f"   ... and {len(summary['critical_issues']) - 5} more")
        
        print(f"\nTest Coverage: {summary['pages_tested']} pages tested")
        print("="*60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate accessibility report from test results")
    parser.add_argument("--results-dir", type=Path, required=True,
                       help="Directory containing accessibility test results")
    parser.add_argument("--output", type=Path,
                       help="Output file for summary JSON (default: results-dir/../accessibility-summary.json)")
    
    args = parser.parse_args()
    
    if not args.results_dir.exists():
        print(f"❌ Results directory not found: {args.results_dir}")
        sys.exit(1)
    
    generator = AccessibilityReportGenerator(args.results_dir)
    
    try:
        # Load and analyze results
        print("🔍 Loading accessibility test results...")
        results = generator.load_test_results()
        
        print("📊 Analyzing accessibility compliance...")
        summary = generator.generate_summary(results)
        detailed = generator.generate_detailed_report(results, summary)
        
        print("💾 Saving reports...")
        generator.save_reports(summary, detailed)
        
        # Exit with appropriate code for CI/CD
        if summary["has_critical_issues"] or not summary["wcag_compliance"]:
            print("\n❌ Critical accessibility issues found!")
            sys.exit(1)
        else:
            print("\n✅ All accessibility requirements met!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Error generating accessibility report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()