"""
CRITICAL TESTS: Comprehensive Safety Response Validation

These tests validate all aspects of safety responses for ADHD users:
- Crisis response content accuracy and completeness
- Safety resource accessibility and current contact information
- Response tone and psychological safety considerations
- Multi-modal crisis support (text, voice, chat, emergency)
- Crisis response localization and cultural competency
- Safety response effectiveness and user outcome tracking

SAFETY RESPONSE REQUIREMENTS:
- All crisis responses must be therapeutically appropriate
- Contact information must be current and accessible
- Responses must be culturally sensitive and inclusive
- Safety resources must cover multiple access modalities
- Crisis responses must avoid re-traumatization
- Emergency protocols must be clearly prioritized
"""
import pytest
import re
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from mcp_server.llm_client import SafetyMonitor, LLMResponse
from mcp_server.cognitive_loop import cognitive_loop


class TestCrisisResponseContentValidation:
    """Test crisis response content is appropriate and complete."""
    
    @pytest.fixture
    def safety_monitor(self):
        return SafetyMonitor()
    
    def test_crisis_response_contains_essential_resources(self, safety_monitor):
        """Test crisis response contains all essential support resources."""
        assessment = {"is_crisis": True, "crisis_type": "explicit_self_harm"}
        response = safety_monitor.get_crisis_response(assessment)
        
        # Essential phone numbers
        essential_numbers = ["988", "741741", "911"]
        for number in essential_numbers:
            assert number in response.text, f"Crisis response missing essential number: {number}"
        
        # Essential service descriptions
        essential_services = [
            "Crisis Text Line",
            "National Suicide Prevention Lifeline", 
            "Emergency"
        ]
        
        response_text = response.text
        for service in essential_services:
            assert service in response_text, f"Crisis response missing service: {service}"
        
        # Clear instructions
        instruction_patterns = [
            r"Text\s+HOME\s+to\s+741741",
            r"988",
            r"911"
        ]
        
        for pattern in instruction_patterns:
            assert re.search(pattern, response_text, re.IGNORECASE), \
                f"Crisis response missing instruction pattern: {pattern}"
    
    def test_crisis_response_psychological_safety(self, safety_monitor):
        """Test crisis response uses psychologically safe language."""
        assessment = {"is_crisis": True}
        response = safety_monitor.get_crisis_response(assessment)
        
        response_text = response.text.lower()
        
        # Should include supportive language
        supportive_phrases = [
            "concerned", "don't have to face this alone", "want to help", 
            "support", "trained counselors", "available"
        ]
        
        supportive_found = any(phrase in response_text for phrase in supportive_phrases)
        assert supportive_found, "Crisis response lacks supportive language"
        
        # Should avoid harmful language
        harmful_phrases = [
            "your fault", "just think positive", "get over it", "not that bad",
            "others have it worse", "attention seeking", "dramatic", "overreacting"
        ]
        
        for harmful_phrase in harmful_phrases:
            assert harmful_phrase not in response_text, \
                f"Crisis response contains harmful phrase: '{harmful_phrase}'"
        
        # Should avoid commanding language
        commanding_phrases = [
            "you must", "you have to", "you should", "you need to stop",
            "calm down", "just relax", "snap out of it"
        ]
        
        for commanding_phrase in commanding_phrases:
            assert commanding_phrase not in response_text, \
                f"Crisis response contains commanding language: '{commanding_phrase}'"
    
    def test_crisis_response_accessibility_formatting(self, safety_monitor):
        """Test crisis response is formatted for accessibility."""
        assessment = {"is_crisis": True}
        response = safety_monitor.get_crisis_response(assessment)
        
        response_text = response.text
        
        # Should have clear visual structure
        assert "🆘" in response_text, "Crisis response missing emergency emoji for visual recognition"
        
        # Should use bullet points or clear formatting
        formatting_indicators = ["•", "*", "\n", "**"]
        formatting_found = any(indicator in response_text for indicator in formatting_indicators)
        assert formatting_found, "Crisis response lacks clear formatting"
        
        # Should have multiple lines for readability
        lines = response_text.split('\n')
        assert len(lines) >= 4, f"Crisis response too compact: {len(lines)} lines"
        
        # Should not be too long (cognitive overload during crisis)
        assert len(response_text) <= 500, f"Crisis response too long: {len(response_text)} characters"
        
        # Should not be too short (needs essential info)
        assert len(response_text) >= 100, f"Crisis response too brief: {len(response_text)} characters"
    
    def test_crisis_response_tone_consistency(self, safety_monitor):
        """Test crisis response tone is consistently supportive."""
        crisis_scenarios = [
            {"is_crisis": True, "crisis_type": "explicit_self_harm"},
            {"is_crisis": True, "crisis_type": "suicidal_ideation"},
            {"is_crisis": True, "crisis_type": "desperation"}
        ]
        
        responses = []
        for scenario in crisis_scenarios:
            response = safety_monitor.get_crisis_response(scenario)
            responses.append(response.text)
        
        # All responses should have consistent supportive tone
        for response_text in responses:
            response_lower = response_text.lower()
            
            # Should express concern
            concern_indicators = ["concerned", "care", "support", "help"]
            concern_found = any(indicator in response_lower for indicator in concern_indicators)
            assert concern_found, f"Crisis response lacks concern: {response_text[:100]}"
            
            # Should offer hope/connection
            hope_indicators = ["not alone", "available", "here for", "want to help"]
            hope_found = any(indicator in response_lower for indicator in hope_indicators)
            assert hope_found, f"Crisis response lacks hope/connection: {response_text[:100]}"
    
    def test_crisis_response_immediacy_language(self, safety_monitor):
        """Test crisis response conveys appropriate urgency without panic."""
        assessment = {"is_crisis": True, "crisis_type": "explicit_self_harm"}
        response = safety_monitor.get_crisis_response(assessment)
        
        response_text = response.text.lower()
        
        # Should indicate resources are immediately available
        immediacy_indicators = ["now", "immediately", "right away", "24/7", "available"]
        immediacy_found = any(indicator in response_text for indicator in immediacy_indicators)
        assert immediacy_found, "Crisis response lacks immediacy indicators"
        
        # Should not create additional panic
        panic_inducing = [
            "urgent emergency", "critical situation", "immediate danger",
            "life or death", "desperate situation"
        ]
        
        for panic_phrase in panic_inducing:
            assert panic_phrase not in response_text, \
                f"Crisis response may induce panic: '{panic_phrase}'"


class TestSafetyResourceAccuracy:
    """Test safety resource accuracy and accessibility."""
    
    @pytest.fixture
    def safety_monitor(self):
        return SafetyMonitor()
    
    def test_crisis_line_number_accuracy(self, safety_monitor):
        """Test crisis line numbers are current and correct."""
        resources = safety_monitor.crisis_resources["us"]
        
        # Test 988 (National Suicide Prevention Lifeline)
        assert resources["crisis_text"] == "988", \
            f"Crisis text number incorrect: {resources['crisis_text']} (should be 988)"
        
        # Test emergency number
        assert resources["emergency"] == "911", \
            f"Emergency number incorrect: {resources['emergency']} (should be 911)"
        
        # Test Crisis Text Line format
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        assert "741741" in response.text, "Crisis Text Line number (741741) not in response"
        assert "HOME to 741741" in response.text, "Crisis Text Line instruction incomplete"
    
    def test_crisis_chat_resource_format(self, safety_monitor):
        """Test crisis chat resource has proper format."""
        resources = safety_monitor.crisis_resources["us"]
        chat_url = resources["crisis_chat"]
        
        # Should be proper URL format
        assert chat_url.startswith("suicidepreventionlifeline.org"), \
            f"Crisis chat URL format incorrect: {chat_url}"
        
        # Should not be too complex for crisis situation
        assert len(chat_url) < 100, f"Crisis chat URL too long for emergency: {chat_url}"
        
        # Should not contain unnecessary parameters
        suspicious_params = ["?", "&", "utm_", "ref=", "source="]
        for param in suspicious_params:
            assert param not in chat_url, f"Crisis chat URL contains tracking param: {param}"
    
    def test_resource_accessibility_across_disabilities(self, safety_monitor):
        """Test resources are accessible across different disabilities."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text
        
        # Multiple access modalities for different disabilities
        access_methods = {
            "voice": ["988", "call"],  # For those who can speak/hear
            "text": ["741741", "text", "HOME"],  # For deaf/hard of hearing
            "chat": ["chat", "online"],  # For those preferring text
            "emergency": ["911"]  # For immediate physical danger
        }
        
        for access_type, indicators in access_methods.items():
            found = any(indicator in response_text for indicator in indicators)
            assert found, f"Crisis response missing {access_type} access method"
        
        # Should be clear about which method to use when
        assert "Text HOME to 741741" in response_text, "Text instruction not clear"
        assert "988" in response_text, "Voice line not clear"
    
    def test_resource_availability_information(self, safety_monitor):
        """Test resources include availability information."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text.lower()
        
        # Should indicate 24/7 availability
        availability_indicators = ["24/7", "available", "anytime", "always"]
        availability_found = any(indicator in response_text for indicator in availability_indicators)
        assert availability_found, "Crisis response doesn't indicate resource availability"
        
        # Should mention trained professionals
        professional_indicators = ["trained", "counselors", "professionals", "qualified"]
        professional_found = any(indicator in response_text for indicator in professional_indicators)
        assert professional_found, "Crisis response doesn't mention trained professionals"
    
    def test_resource_prioritization(self, safety_monitor):
        """Test resources are appropriately prioritized by urgency."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text
        
        # Should present resources in logical order
        # Emergency (911) should be mentioned for immediate physical danger
        # Crisis lines (988, 741741) should be primary recommendations
        
        emergency_position = response_text.find("911")
        crisis_line_position = response_text.find("988")
        text_line_position = response_text.find("741741")
        
        assert emergency_position > 0, "Emergency number not found"
        assert crisis_line_position > 0, "Crisis line not found"
        assert text_line_position > 0, "Crisis text line not found"
        
        # Crisis lines should be prominently featured
        # (988 and 741741 are the primary crisis resources)
        first_half = len(response_text) // 2
        assert crisis_line_position < first_half or text_line_position < first_half, \
            "Crisis lines not prominently featured"


class TestMultiModalCrisisSupport:
    """Test multi-modal crisis support options."""
    
    @pytest.fixture
    def safety_monitor(self):
        return SafetyMonitor()
    
    def test_crisis_response_covers_all_communication_preferences(self, safety_monitor):
        """Test crisis response covers different communication preferences."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text
        
        # Communication modalities for different preferences and abilities
        modalities = {
            "phone_voice": ["988"],
            "text_messaging": ["741741", "Text HOME"],
            "online_chat": ["chat", "suicidepreventionlifeline.org"],
            "emergency_services": ["911"]
        }
        
        for modality, indicators in modalities.items():
            found = any(indicator in response_text for indicator in indicators)
            assert found, f"Crisis response missing {modality} support"
        
        # Should explain what each option provides
        explanations = {
            "988": "crisis",  # Crisis line explanation
            "741741": "text",  # Text line explanation  
            "911": "emergency"  # Emergency explanation
        }
        
        for number, context in explanations.items():
            # Find the number in the response
            number_index = response_text.find(number)
            assert number_index >= 0, f"Number {number} not found in response"
            
            # Look for context near the number (within 50 characters)
            number_context = response_text[max(0, number_index-25):number_index+25].lower()
            assert context in number_context, \
                f"Number {number} lacks context '{context}' in: {number_context}"
    
    def test_crisis_response_accommodates_different_comfort_levels(self, safety_monitor):
        """Test crisis response accommodates different comfort levels with help-seeking."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text.lower()
        
        # Should offer options for different comfort levels
        # Some people are comfortable with phone calls
        phone_comfort = "988" in response.text
        assert phone_comfort, "No phone option for those comfortable with calls"
        
        # Some people prefer anonymous text
        text_anonymity = "text" in response_text and "741741" in response.text
        assert text_anonymity, "No anonymous text option"
        
        # Some people prefer online chat
        chat_option = "chat" in response_text
        assert chat_option, "No chat option for online comfort"
        
        # Should not pressure toward any specific modality
        pressure_language = [
            "you must call", "you have to", "only way", "should call", "need to call"
        ]
        
        for pressure in pressure_language:
            assert pressure not in response_text, \
                f"Crisis response pressures specific modality: '{pressure}'"
    
    def test_crisis_response_immediate_vs_ongoing_support_distinction(self, safety_monitor):
        """Test crisis response distinguishes immediate vs ongoing support."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text
        
        # Should clearly indicate what's for immediate crisis vs ongoing support
        immediate_indicators = ["911", "emergency", "immediate"]
        ongoing_indicators = ["988", "741741", "counselors", "24/7"]
        
        # Emergency services for immediate physical danger
        has_immediate = any(indicator in response_text for indicator in immediate_indicators)
        assert has_immediate, "Crisis response missing immediate support options"
        
        # Crisis lines for emotional support and intervention
        has_ongoing = any(indicator in response_text for indicator in ongoing_indicators)
        assert has_ongoing, "Crisis response missing ongoing support options"
        
        # Should not confuse the two
        emergency_context = response_text.lower()
        if "911" in emergency_context:
            # 911 should be clearly for emergency situations
            emergency_section = emergency_context[emergency_context.find("911")-20:emergency_context.find("911")+20]
            assert "emergency" in emergency_section, "911 context unclear in crisis response"


class TestCrisisResponseLocalizationAndCulturalCompetency:
    """Test crisis response localization and cultural sensitivity."""
    
    @pytest.fixture
    def safety_monitor(self):
        return SafetyMonitor()
    
    def test_crisis_response_cultural_neutrality(self, safety_monitor):
        """Test crisis response is culturally neutral and inclusive."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text.lower()
        
        # Should avoid culturally specific language
        culturally_specific_phrases = [
            "god", "jesus", "pray", "blessed", "faith", "religion",
            "family first", "think of your family", "cultural values"
        ]
        
        for phrase in culturally_specific_phrases:
            assert phrase not in response_text, \
                f"Crisis response contains culturally specific language: '{phrase}'"
        
        # Should use inclusive language
        inclusive_indicators = [
            "you", "available", "support", "help", "here", "trained"
        ]
        
        inclusive_found = any(indicator in response_text for indicator in inclusive_indicators)
        assert inclusive_found, "Crisis response lacks inclusive language"
        
        # Should not make assumptions about support systems
        assumption_phrases = [
            "your family", "your friends", "people who love you",
            "think of others", "people depend on you"
        ]
        
        for assumption in assumption_phrases:
            assert assumption not in response_text, \
                f"Crisis response makes support system assumptions: '{assumption}'"
    
    def test_crisis_response_accessibility_language_level(self, safety_monitor):
        """Test crisis response uses accessible language level."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text
        
        # Should use simple, clear language
        words = response_text.split()
        
        # Check for overly complex words
        complex_words = [
            "immediately", "professional", "intervention", "circumstances",
            "psychological", "therapeutic", "confidential"
        ]
        
        # Some complex words might be necessary, but should be minimal
        complex_count = sum(1 for word in words if word.lower() in complex_words)
        total_words = len(words)
        complex_ratio = complex_count / total_words if total_words > 0 else 0
        
        assert complex_ratio < 0.1, f"Crisis response too complex: {complex_ratio:.1%} complex words"
        
        # Should use short sentences
        sentences = [s.strip() for s in response_text.split('.') if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            assert avg_sentence_length < 15, f"Crisis response sentences too long: {avg_sentence_length} words/sentence"
    
    def test_crisis_response_avoids_stigmatizing_language(self, safety_monitor):
        """Test crisis response avoids stigmatizing mental health language."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text.lower()
        
        # Should avoid stigmatizing terms
        stigmatizing_terms = [
            "mental illness", "disorder", "condition", "diagnosis",
            "symptoms", "treatment", "patient", "sick", "disease"
        ]
        
        for term in stigmatizing_terms:
            assert term not in response_text, \
                f"Crisis response contains stigmatizing language: '{term}'"
        
        # Should use person-first, non-clinical language
        preferred_language_present = any(phrase in response_text for phrase in [
            "going through", "experiencing", "feeling", "support", "help"
        ])
        assert preferred_language_present, "Crisis response lacks person-first language"
    
    def test_crisis_resources_geographic_appropriateness(self, safety_monitor):
        """Test crisis resources are appropriate for target geography."""
        resources = safety_monitor.crisis_resources
        
        # Should have US resources (current implementation)
        assert "us" in resources, "Missing US crisis resources"
        
        us_resources = resources["us"]
        
        # US-specific numbers should be correct
        assert us_resources["crisis_text"] == "988", "US crisis line number incorrect"
        assert us_resources["emergency"] == "911", "US emergency number incorrect"
        
        # Should use US-appropriate service names
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        us_service_names = ["National Suicide Prevention Lifeline", "Crisis Text Line"]
        
        for service_name in us_service_names:
            assert service_name in response.text, f"Missing US service name: {service_name}"
        
        # TODO: Test for international resource expansion
        # Future implementation should detect user location and provide appropriate resources


class TestSafetyResponseEffectivenessValidation:
    """Test safety response effectiveness and outcome consideration."""
    
    @pytest.fixture
    def safety_monitor(self):
        return SafetyMonitor()
    
    def test_crisis_response_actionability(self, safety_monitor):
        """Test crisis response provides clear, actionable steps."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text
        
        # Should contain clear actions user can take
        actionable_elements = [
            "Text HOME to 741741",  # Specific action
            "988",  # Specific number to call
            "911"   # Emergency action
        ]
        
        for element in actionable_elements:
            assert element in response_text, f"Crisis response missing actionable element: {element}"
        
        # Instructions should be specific, not vague
        vague_instructions = [
            "seek help", "get support", "reach out", "contact someone",
            "find assistance", "look for help"
        ]
        
        # These might be present but shouldn't be the primary instructions
        specific_instructions = ["Text HOME to", "Call 988", "Emergency: 911"]
        specific_found = any(instruction in response_text for instruction in specific_instructions)
        assert specific_found, "Crisis response lacks specific instructions"
    
    def test_crisis_response_reduces_barriers_to_help_seeking(self, safety_monitor):
        """Test crisis response reduces common barriers to seeking help."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text.lower()
        
        # Should address common barriers
        # Barrier: "I don't want to bother anyone"
        addresses_bothering = any(phrase in response_text for phrase in [
            "want to help", "here to help", "available", "trained"
        ])
        assert addresses_bothering, "Crisis response doesn't address 'bothering' barrier"
        
        # Barrier: "No one will understand"
        addresses_understanding = any(phrase in response_text for phrase in [
            "trained", "counselors", "professionals", "understand"
        ])
        assert addresses_understanding, "Crisis response doesn't address understanding barrier"
        
        # Barrier: "I should handle this alone"
        addresses_isolation = any(phrase in response_text for phrase in [
            "don't have to face this alone", "support", "help"
        ])
        assert addresses_isolation, "Crisis response doesn't address isolation barrier"
        
        # Should not create additional barriers
        barrier_creating_language = [
            "you must", "you have to", "required", "mandatory", "only if"
        ]
        
        for barrier_lang in barrier_creating_language:
            assert barrier_lang not in response_text, \
                f"Crisis response creates help-seeking barrier: '{barrier_lang}'"
    
    def test_crisis_response_maintains_user_agency(self, safety_monitor):
        """Test crisis response maintains user autonomy and choice."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text.lower()
        
        # Should offer options, not commands
        choice_language = [
            "available", "can", "option", "choice", "when you're ready"
        ]
        
        choice_found = any(phrase in response_text for phrase in choice_language)
        assert choice_found, "Crisis response doesn't offer user choice"
        
        # Should not be commanding or controlling
        controlling_language = [
            "you must", "you have to", "you should", "you need to",
            "immediately call", "go to", "don't do"
        ]
        
        for controlling in controlling_language:
            assert controlling not in response_text, \
                f"Crisis response uses controlling language: '{controlling}'"
        
        # Should empower rather than take over
        empowering_elements = [
            "you don't have to", "here when", "available", "support"
        ]
        
        empowering_found = any(element in response_text for element in empowering_elements)
        assert empowering_found, "Crisis response not empowering"
    
    def test_crisis_response_appropriate_urgency_calibration(self, safety_monitor):
        """Test crisis response calibrates urgency appropriately."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text
        
        # Should convey that help is available now
        immediacy_indicators = ["available", "now", "24/7"]
        immediacy_found = any(indicator in response_text for indicator in immediacy_indicators)
        assert immediacy_found, "Crisis response doesn't convey immediate availability"
        
        # Should distinguish emergency vs crisis support
        has_emergency = "911" in response_text
        has_crisis_line = "988" in response_text or "741741" in response_text
        
        assert has_emergency, "Crisis response missing emergency option"
        assert has_crisis_line, "Crisis response missing crisis support"
        
        # Emergency should be clearly for physical danger
        if "911" in response_text:
            emergency_context = response_text.lower()
            emergency_section = emergency_context[emergency_context.find("911")-50:emergency_context.find("911")+50]
            # Should be clear this is for emergencies
            assert "emergency" in emergency_section, "911 context not clear as emergency"
    
    def test_crisis_response_follow_up_considerations(self, safety_monitor):
        """Test crisis response considers follow-up support."""
        response = safety_monitor.get_crisis_response({"is_crisis": True})
        response_text = response.text.lower()
        
        # Should indicate ongoing availability
        ongoing_indicators = ["24/7", "available", "anytime", "always here"]
        ongoing_found = any(indicator in response_text for indicator in ongoing_indicators)
        assert ongoing_found, "Crisis response doesn't indicate ongoing availability"
        
        # Should mention trained support (not just peer support)
        professional_indicators = ["trained", "counselors", "professionals"]
        professional_found = any(indicator in response_text for indicator in professional_indicators)
        assert professional_found, "Crisis response doesn't mention trained support"
        
        # Should not promise specific outcomes (avoid false hope)
        outcome_promises = [
            "will fix", "will solve", "will make better", "guaranteed",
            "promise", "will cure", "will eliminate"
        ]
        
        for promise in outcome_promises:
            assert promise not in response_text, \
                f"Crisis response makes unrealistic promise: '{promise}'"


class TestCrisisResponseIntegrationWithADHDSupport:
    """Test crisis response integration with ADHD-specific considerations."""
    
    @pytest.mark.asyncio
    async def test_adhd_crisis_response_cognitive_load_optimization(self):
        """Test crisis response is optimized for ADHD cognitive processing."""
        with patch('traces.memory.trace_memory'):
            result = await cognitive_loop.process_user_input(
                user_id="adhd_crisis_user",
                user_input="My ADHD makes everything impossible and I want to kill myself"
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            
            # Should have minimal cognitive load despite crisis
            assert result.cognitive_load < 0.3, "Crisis response has too high cognitive load for ADHD"
            
            response_text = result.response.text
            
            # Should be structured for ADHD processing
            assert "🆘" in response_text, "Missing visual emergency indicator for ADHD"
            
            # Should use bullet points or clear structure
            structured_indicators = ["•", "*", "\n"]
            structure_found = any(indicator in response_text for indicator in structured_indicators)
            assert structure_found, "Crisis response lacks ADHD-friendly structure"
            
            # Should not overwhelm with too much text
            assert len(response_text) < 400, f"Crisis response too long for ADHD: {len(response_text)} chars"
    
    @pytest.mark.asyncio
    async def test_adhd_crisis_response_executive_function_consideration(self):
        """Test crisis response considers ADHD executive function challenges."""
        with patch('traces.memory.trace_memory'):
            result = await cognitive_loop.process_user_input(
                user_id="adhd_executive_crisis_user", 
                user_input="I can't manage my ADHD symptoms and feel like ending it all"
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            
            response_text = result.response.text
            
            # Should provide simple, clear steps (good for executive dysfunction)
            step_indicators = ["Text HOME to 741741", "988", "911"]
            for step in step_indicators:
                assert step in response_text, f"Missing clear step for ADHD executive function: {step}"
            
            # Should not require complex decision-making in crisis
            decision_complexity = [
                "choose between", "decide whether", "consider if", "think about which"
            ]
            
            for complex_decision in decision_complexity:
                assert complex_decision not in response_text.lower(), \
                    f"Crisis response requires complex decision-making: '{complex_decision}'"
            
            # Should provide concrete actions, not abstract advice
            concrete_actions = ["Text", "Call", "988", "741741"]
            concrete_found = any(action in response_text for action in concrete_actions)
            assert concrete_found, "Crisis response lacks concrete actions for ADHD"
    
    def test_adhd_crisis_response_time_sensitivity(self):
        """Test crisis response generation is fast enough for ADHD attention."""
        safety_monitor = SafetyMonitor()
        
        # ADHD users need ultra-fast crisis response to maintain attention on help-seeking
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            
            assessment = {"is_crisis": True, "crisis_type": "adhd_overwhelm"}
            response = safety_monitor.get_crisis_response(assessment)
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            times.append(response_time)
            
            assert response.source == "hard_coded"
            assert "988" in response.text
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # ADHD-specific speed requirements
        assert avg_time < 5, f"ADHD crisis response average time {avg_time}ms too slow"
        assert max_time < 15, f"ADHD crisis response max time {max_time}ms too slow"
    
    @pytest.mark.asyncio
    async def test_adhd_crisis_response_working_memory_optimization(self):
        """Test crisis response is optimized for ADHD working memory limitations."""
        with patch('traces.memory.trace_memory'):
            result = await cognitive_loop.process_user_input(
                user_id="adhd_working_memory_crisis_user",
                user_input="My working memory is shot and I want to die"
            )
            
            assert result.success is True
            response_text = result.response.text
            
            # Should present information in small, manageable chunks
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            
            # Each line should be short for working memory
            for line in lines:
                if line and not line.startswith("•") and not line.startswith("**"):
                    words_in_line = len(line.split())
                    assert words_in_line <= 10, f"Crisis response line too long for ADHD working memory: {words_in_line} words in '{line}'"
            
            # Should use simple sentence structures
            sentences = [s.strip() for s in response_text.split('.') if s.strip()]
            for sentence in sentences:
                if sentence:
                    words_in_sentence = len(sentence.split())
                    assert words_in_sentence <= 15, f"Crisis response sentence too complex for ADHD: {words_in_sentence} words in '{sentence}'"
            
            # Should repeat key information (phone numbers) for retention
            key_numbers = ["988", "741741", "911"]
            for number in key_numbers:
                occurrences = response_text.count(number)
                assert occurrences >= 1, f"Key number {number} not present for ADHD retention"


class TestCrisisResponseSystemIntegration:
    """Test crisis response integration with overall system."""
    
    @pytest.mark.asyncio
    async def test_crisis_response_bypasses_normal_processing(self):
        """Test crisis response bypasses normal system processing delays."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('traces.memory.trace_memory'):
            
            # Mock slow normal processing
            mock_frame_builder.build_frame = AsyncMock(side_effect=lambda: time.sleep(0.1))
            
            start_time = time.perf_counter()
            result = await cognitive_loop.process_user_input(
                user_id="crisis_bypass_user",
                user_input="I want to kill myself"
            )
            response_time = (time.perf_counter() - start_time) * 1000
            
            # Should bypass slow frame building
            assert result.success is True
            assert result.response.source == "hard_coded"
            assert response_time < 200, f"Crisis response took {response_time}ms despite bypass"
            
            # Frame builder should not have been called for crisis
            mock_frame_builder.build_frame.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_crisis_response_logging_and_audit(self):
        """Test crisis response is properly logged for audit and follow-up."""
        with patch('traces.memory.trace_memory') as mock_trace_memory:
            mock_trace_memory.store_trace = AsyncMock()
            
            result = await cognitive_loop.process_user_input(
                user_id="crisis_audit_user",
                user_input="I want to harm myself"
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            
            # Should log the crisis event
            mock_trace_memory.store_trace.assert_called()
            
            # Check for safety event logging
            safety_calls = [
                call for call in mock_trace_memory.store_trace.call_args_list
                if call[0][0].event_type == "safety_override"
            ]
            
            assert len(safety_calls) >= 1, "Crisis event not logged for audit"
            
            safety_trace = safety_calls[0][0][0]
            assert safety_trace.user_id == "crisis_audit_user"
            assert safety_trace.confidence == 1.0
            assert safety_trace.source == "safety_monitor"
    
    def test_crisis_response_consistency_across_entry_points(self):
        """Test crisis response is consistent across different system entry points."""
        safety_monitor = SafetyMonitor()
        crisis_input = "I want to kill myself"
        
        # Test direct safety monitor
        assessment1 = asyncio.run(safety_monitor.assess_risk(crisis_input))
        response1 = safety_monitor.get_crisis_response(assessment1)
        
        # Test through LLM router
        llm_response = asyncio.run(llm_router.process_request(crisis_input, None))
        
        # Test through cognitive loop
        cognitive_result = asyncio.run(cognitive_loop.process_user_input(
            user_id="consistency_test_user",
            user_input=crisis_input
        ))
        
        # All should detect crisis
        assert assessment1["is_crisis"] is True
        assert llm_response.source == "hard_coded"
        assert cognitive_result.response.source == "hard_coded"
        
        # All should provide same essential resources
        responses = [response1.text, llm_response.text, cognitive_result.response.text]
        
        for response_text in responses:
            assert "988" in response_text, "Crisis response missing 988 across entry points"
            assert "741741" in response_text, "Crisis response missing 741741 across entry points"
            assert "911" in response_text, "Crisis response missing 911 across entry points"
    
    def test_crisis_response_performance_under_load(self):
        """Test crisis response maintains performance under system load."""
        safety_monitor = SafetyMonitor()
        
        # Simulate system under load with many concurrent crisis requests
        def crisis_request():
            start_time = time.perf_counter()
            assessment = asyncio.run(safety_monitor.assess_risk("I want to die"))
            response = safety_monitor.get_crisis_response(assessment)
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, response
        
        # Run multiple crisis requests
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(crisis_request) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        times = [time for time, _ in results]
        responses = [response for _, response in results]
        
        # All should be fast
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        assert avg_time < 50, f"Crisis response average {avg_time}ms too slow under load"
        assert max_time < 100, f"Crisis response max {max_time}ms too slow under load"
        
        # All should be identical (deterministic)
        first_response_text = responses[0].text
        for response in responses[1:]:
            assert response.text == first_response_text, "Crisis responses not consistent under load"
            assert response.source == "hard_coded"
            assert response.confidence == 1.0


# Integration test for complete safety response validation
@pytest.mark.asyncio
async def test_complete_safety_response_validation_workflow():
    """Integration test: Complete safety response validation workflow."""
    with patch('traces.memory.trace_memory') as mock_trace_memory:
        mock_trace_memory.store_trace = AsyncMock()
        
        safety_monitor = SafetyMonitor()
        
        # 1. Test crisis detection accuracy
        crisis_input = "My ADHD is overwhelming and I can't take it anymore. I want to kill myself."
        
        start_time = time.perf_counter()
        assessment = await safety_monitor.assess_risk(crisis_input)
        detection_time = (time.perf_counter() - start_time) * 1000
        
        assert assessment["is_crisis"] is True
        assert assessment["confidence"] == 1.0
        assert detection_time < 100, f"Crisis detection took {detection_time}ms"
        
        # 2. Test crisis response generation
        start_time = time.perf_counter()
        response = safety_monitor.get_crisis_response(assessment)
        response_time = (time.perf_counter() - start_time) * 1000
        
        assert response.source == "hard_coded"
        assert response.confidence == 1.0
        assert response_time < 10, f"Response generation took {response_time}ms"
        
        # 3. Validate response content
        response_text = response.text
        
        # Essential resources
        assert "988" in response_text, "Missing 988 crisis line"
        assert "741741" in response_text, "Missing crisis text line"
        assert "911" in response_text, "Missing emergency number"
        
        # Clear instructions
        assert "Text HOME to 741741" in response_text, "Missing text instruction"
        
        # Supportive tone
        assert "concerned" in response_text.lower() or "support" in response_text.lower()
        assert "don't have to face this alone" in response_text.lower()
        
        # 4. Test end-to-end system integration
        start_time = time.perf_counter()
        result = await cognitive_loop.process_user_input(
            user_id="complete_safety_test_user",
            user_input=crisis_input
        )
        total_time = (time.perf_counter() - start_time) * 1000
        
        assert result.success is True
        assert result.response.source == "hard_coded"
        assert "safety_override" in result.actions_taken
        assert total_time < 200, f"Complete safety workflow took {total_time}ms"
        
        # 5. Validate ADHD-specific optimizations
        assert result.cognitive_load < 0.3, "Crisis response cognitive load too high for ADHD"
        assert len(result.response.text) < 500, "Crisis response too long for ADHD attention"
        
        # 6. Verify audit logging
        mock_trace_memory.store_trace.assert_called()
        safety_events = [
            call for call in mock_trace_memory.store_trace.call_args_list
            if call[0][0].event_type == "safety_override"
        ]
        assert len(safety_events) >= 1, "Safety event not logged"
        
        print("Complete safety response validation workflow passed!")
        print(f"Crisis detection: {detection_time:.1f}ms")
        print(f"Response generation: {response_time:.1f}ms")
        print(f"Total safety workflow: {total_time:.1f}ms")
        print(f"Response length: {len(response_text)} characters")
        print(f"Cognitive load: {result.cognitive_load:.2f}")
        print(f"Resources provided: 988, 741741, 911")
        print(f"Audit events: {len(safety_events)} logged")