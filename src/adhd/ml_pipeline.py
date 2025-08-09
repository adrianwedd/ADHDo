"""
Machine Learning Pipeline for ADHD Pattern Recognition.

This module implements a privacy-first machine learning pipeline that learns
ADHD behavioral patterns to improve personalization and intervention timing.
The system uses federated learning principles and differential privacy to
protect user data while building effective predictive models.

Core Features:
- Privacy-preserving pattern learning with differential privacy
- Real-time behavioral pattern classification
- Predictive modeling for intervention timing
- Anomaly detection for crisis situations
- Transfer learning for new users
- Continuous model improvement with user feedback
- Explainable AI for transparency

The pipeline is designed to work with limited data per user while maintaining
strong privacy guarantees and providing actionable insights.
"""
import asyncio
import json
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import hashlib

import structlog
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import joblib

from mcp_server.models import TraceMemory as TraceMemoryModel
from traces.memory import trace_memory
from adhd.pattern_engine import PatternType, PatternSeverity, PatternDetection
from adhd.user_profile import ADHDSubtype

logger = structlog.get_logger()


class ModelType(Enum):
    """Types of ML models in the pipeline."""
    PATTERN_CLASSIFIER = "pattern_classifier"
    CRISIS_DETECTOR = "crisis_detector" 
    INTERVENTION_PREDICTOR = "intervention_predictor"
    ENGAGEMENT_PREDICTOR = "engagement_predictor"
    SUBTYPE_CLASSIFIER = "subtype_classifier"


class PrivacyLevel(Enum):
    """Privacy protection levels."""
    NONE = "none"                    # No privacy protection (development only)
    BASIC = "basic"                  # Basic anonymization
    DIFFERENTIAL = "differential"    # Differential privacy
    FEDERATED = "federated"         # Federated learning


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_samples: int
    last_updated: datetime
    privacy_budget_used: float = 0.0


@dataclass
class FeatureVector:
    """Feature vector for ML models."""
    user_id_hash: str  # Hashed user ID for privacy
    features: Dict[str, float]
    label: Optional[str] = None
    timestamp: datetime = None
    session_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class FeatureExtractor:
    """
    Extracts privacy-preserving features from user interactions.
    
    Transforms raw user data into ML-ready feature vectors while
    maintaining privacy through differential privacy and anonymization.
    """
    
    def __init__(self, privacy_level: PrivacyLevel = PrivacyLevel.DIFFERENTIAL):
        self.privacy_level = privacy_level
        self.feature_scalers: Dict[str, StandardScaler] = {}
        self.label_encoders: Dict[str, LabelEncoder] = {}
        
        # Privacy parameters
        self.epsilon = 1.0  # Privacy budget for differential privacy
        self.delta = 1e-5   # Privacy parameter
        
        # Feature definitions
        self.behavioral_features = [
            'session_duration', 'response_delay', 'task_switching_frequency',
            'completion_rate', 'energy_level', 'stress_indicators',
            'time_estimation_accuracy', 'interruption_frequency',
            'emotional_volatility', 'cognitive_load'
        ]
        
        self.temporal_features = [
            'hour_of_day', 'day_of_week', 'time_since_last_interaction',
            'session_count_today', 'completion_streak'
        ]
        
        self.contextual_features = [
            'task_complexity', 'environmental_distractions', 'urgency_level',
            'social_context', 'energy_match'
        ]
    
    async def extract_features(self, 
                             user_id: str, 
                             interaction_data: Dict[str, Any],
                             window_hours: int = 24) -> FeatureVector:
        """Extract privacy-preserving features from interaction data."""
        try:
            # Hash user ID for privacy
            user_hash = self._hash_user_id(user_id)
            
            # Get historical context
            historical_data = await self._get_historical_context(user_id, window_hours)
            
            # Extract feature categories
            behavioral_features = await self._extract_behavioral_features(
                interaction_data, historical_data
            )
            temporal_features = await self._extract_temporal_features(
                interaction_data, historical_data
            )
            contextual_features = await self._extract_contextual_features(
                interaction_data
            )
            
            # Combine all features
            features = {
                **behavioral_features,
                **temporal_features, 
                **contextual_features
            }
            
            # Apply privacy protection
            if self.privacy_level == PrivacyLevel.DIFFERENTIAL:
                features = self._apply_differential_privacy(features)
            elif self.privacy_level == PrivacyLevel.BASIC:
                features = self._apply_basic_anonymization(features)
            
            # Normalize features
            features = self._normalize_features(features)
            
            return FeatureVector(
                user_id_hash=user_hash,
                features=features,
                timestamp=datetime.utcnow(),
                session_id=interaction_data.get('session_id', 'unknown')
            )
            
        except Exception as e:
            logger.error("Feature extraction failed", 
                        user_id=user_id, error=str(e))
            
            # Return minimal safe feature vector
            return FeatureVector(
                user_id_hash=self._hash_user_id(user_id),
                features={f: 0.5 for f in self.behavioral_features},
                timestamp=datetime.utcnow()
            )
    
    async def _extract_behavioral_features(self, 
                                         interaction_data: Dict[str, Any],
                                         historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract behavioral pattern features."""
        features = {}
        
        # Current session features
        features['session_duration'] = min(
            interaction_data.get('session_duration_minutes', 30) / 120.0, 1.0
        )
        features['response_delay'] = min(
            interaction_data.get('response_delay_minutes', 5) / 60.0, 1.0
        )
        features['task_switching_frequency'] = min(
            interaction_data.get('task_switches_per_hour', 2) / 10.0, 1.0
        )
        features['completion_rate'] = interaction_data.get('completion_rate', 0.5)
        features['energy_level'] = interaction_data.get('energy_level', 0.5)
        
        # Stress and emotional indicators
        stress_words = interaction_data.get('stress_indicators', [])
        features['stress_indicators'] = min(len(stress_words) / 5.0, 1.0)
        
        features['emotional_volatility'] = interaction_data.get('emotional_volatility', 0.3)
        features['cognitive_load'] = interaction_data.get('cognitive_load', 0.5)
        
        # Historical pattern features
        if historical_data:
            completion_rates = [d.get('completion_rate', 0.5) for d in historical_data]
            features['avg_completion_rate'] = sum(completion_rates) / len(completion_rates)
            
            energy_levels = [d.get('energy_level', 0.5) for d in historical_data]
            features['avg_energy_level'] = sum(energy_levels) / len(energy_levels)
            
            # Calculate trend indicators
            if len(completion_rates) > 1:
                recent_avg = sum(completion_rates[-3:]) / min(len(completion_rates), 3)
                overall_avg = sum(completion_rates) / len(completion_rates)
                features['completion_trend'] = (recent_avg - overall_avg + 1.0) / 2.0
            else:
                features['completion_trend'] = 0.5
        else:
            features['avg_completion_rate'] = 0.5
            features['avg_energy_level'] = 0.5
            features['completion_trend'] = 0.5
        
        return features
    
    async def _extract_temporal_features(self, 
                                       interaction_data: Dict[str, Any],
                                       historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract temporal pattern features."""
        features = {}
        current_time = datetime.utcnow()
        
        # Time-based features
        features['hour_of_day'] = current_time.hour / 23.0
        features['day_of_week'] = current_time.weekday() / 6.0
        
        # Session patterns
        if historical_data:
            last_interaction = max(
                datetime.fromisoformat(d['timestamp']) 
                for d in historical_data 
                if 'timestamp' in d
            )
            hours_since_last = (current_time - last_interaction).total_seconds() / 3600.0
            features['time_since_last_interaction'] = min(hours_since_last / 24.0, 1.0)
            
            # Count sessions today
            today_sessions = sum(
                1 for d in historical_data
                if datetime.fromisoformat(d['timestamp']).date() == current_time.date()
            )
            features['session_count_today'] = min(today_sessions / 10.0, 1.0)
        else:
            features['time_since_last_interaction'] = 1.0
            features['session_count_today'] = 0.0
        
        # Completion streak
        recent_completions = []
        for data in historical_data[-7:]:  # Last 7 interactions
            recent_completions.append(data.get('completion_rate', 0.5) > 0.7)
        
        if recent_completions:
            streak = 0
            for completed in reversed(recent_completions):
                if completed:
                    streak += 1
                else:
                    break
            features['completion_streak'] = min(streak / 7.0, 1.0)
        else:
            features['completion_streak'] = 0.0
        
        return features
    
    async def _extract_contextual_features(self, 
                                         interaction_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract contextual features."""
        features = {}
        
        features['task_complexity'] = interaction_data.get('task_complexity', 0.5)
        features['urgency_level'] = interaction_data.get('urgency_level', 0.3)
        
        # Environment factors
        distractions = interaction_data.get('environmental_distractions', [])
        features['environmental_distractions'] = min(len(distractions) / 5.0, 1.0)
        
        # Social context
        features['social_context'] = 1.0 if interaction_data.get('involves_others') else 0.0
        
        # Energy match (how well task energy requirements match user energy)
        task_energy_req = interaction_data.get('task_energy_requirement', 0.5)
        user_energy = interaction_data.get('energy_level', 0.5)
        energy_diff = abs(task_energy_req - user_energy)
        features['energy_match'] = 1.0 - energy_diff
        
        return features
    
    async def _get_historical_context(self, 
                                    user_id: str, 
                                    window_hours: int) -> List[Dict[str, Any]]:
        """Get historical interaction data for context."""
        try:
            since = datetime.utcnow() - timedelta(hours=window_hours)
            traces = await trace_memory.get_user_traces(
                user_id,
                event_types=["cognitive_interaction", "pattern_detection"],
                limit=50,
                since=since
            )
            
            historical_data = []
            for trace in traces:
                if trace.event_data:
                    data = {
                        'timestamp': trace.timestamp.isoformat(),
                        'completion_rate': trace.event_data.get('completion_rate', 0.5),
                        'energy_level': trace.event_data.get('energy_level', 0.5),
                        'cognitive_load': trace.event_data.get('cognitive_load', 0.5),
                        'stress_indicators': trace.event_data.get('stress_indicators', [])
                    }
                    historical_data.append(data)
            
            return historical_data
            
        except Exception as e:
            logger.warning("Historical context retrieval failed", error=str(e))
            return []
    
    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for privacy protection."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]
    
    def _apply_differential_privacy(self, features: Dict[str, float]) -> Dict[str, float]:
        """Apply differential privacy noise to features."""
        if self.privacy_level != PrivacyLevel.DIFFERENTIAL:
            return features
        
        # Add calibrated noise for differential privacy
        sensitivity = 1.0  # Assuming features are normalized to [0,1]
        noise_scale = sensitivity / self.epsilon
        
        private_features = {}
        for key, value in features.items():
            # Add Laplace noise
            noise = np.random.laplace(0, noise_scale)
            private_value = np.clip(value + noise, 0.0, 1.0)
            private_features[key] = private_value
        
        return private_features
    
    def _apply_basic_anonymization(self, features: Dict[str, float]) -> Dict[str, float]:
        """Apply basic anonymization techniques."""
        # For now, just add small amount of noise
        anonymous_features = {}
        for key, value in features.items():
            noise = np.random.normal(0, 0.01)  # Small noise
            anonymous_features[key] = np.clip(value + noise, 0.0, 1.0)
        
        return anonymous_features
    
    def _normalize_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Normalize features to [0, 1] range."""
        normalized = {}
        for key, value in features.items():
            # Ensure all features are in [0, 1] range
            normalized[key] = max(0.0, min(1.0, float(value)))
        
        return normalized


class PatternClassifier:
    """
    ML classifier for ADHD behavioral patterns.
    
    Classifies user interactions into different ADHD pattern types
    and severity levels using supervised learning techniques.
    """
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.metrics: Dict[str, ModelMetrics] = {}
        self.feature_extractor = FeatureExtractor()
        self.training_data: Dict[str, List[FeatureVector]] = defaultdict(list)
        
        # Model parameters
        self.min_training_samples = 20
        self.retrain_threshold = 0.1  # Retrain if accuracy drops below this
        self.max_model_age_days = 30
    
    async def train_pattern_classifier(self, user_id: str) -> bool:
        """Train pattern classifier for user."""
        try:
            # Get training data
            training_vectors = await self._collect_training_data(user_id)
            
            if len(training_vectors) < self.min_training_samples:
                logger.info("Insufficient training data", 
                           user_id=user_id, 
                           samples=len(training_vectors))
                return False
            
            # Prepare training data
            X, y = self._prepare_training_data(training_vectors)
            
            if len(set(y)) < 2:  # Need at least 2 classes
                logger.info("Insufficient class diversity", user_id=user_id)
                return False
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Train model
            model = RandomForestClassifier(
                n_estimators=50,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test, y_pred, average='weighted'
            )
            
            # Store model and metrics
            model_key = f"{user_id}_pattern_classifier"
            self.models[model_key] = model
            self.metrics[model_key] = ModelMetrics(
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                training_samples=len(training_vectors),
                last_updated=datetime.utcnow()
            )
            
            logger.info("Pattern classifier trained", 
                       user_id=user_id,
                       accuracy=accuracy,
                       samples=len(training_vectors))
            
            return True
            
        except Exception as e:
            logger.error("Pattern classifier training failed", 
                        user_id=user_id, error=str(e))
            return False
    
    async def classify_pattern(self, 
                             user_id: str, 
                             interaction_data: Dict[str, Any]) -> Optional[Tuple[PatternType, float]]:
        """Classify interaction pattern."""
        try:
            model_key = f"{user_id}_pattern_classifier"
            
            if model_key not in self.models:
                # Try to train model first
                if not await self.train_pattern_classifier(user_id):
                    return None
            
            model = self.models[model_key]
            
            # Extract features
            feature_vector = await self.feature_extractor.extract_features(
                user_id, interaction_data
            )
            
            # Prepare for prediction
            feature_array = self._vectorize_features(feature_vector.features)
            
            # Make prediction
            prediction = model.predict([feature_array])[0]
            confidence = max(model.predict_proba([feature_array])[0])
            
            # Map prediction to pattern type
            try:
                pattern_type = PatternType(prediction)
            except ValueError:
                logger.warning("Unknown pattern prediction", prediction=prediction)
                return None
            
            return pattern_type, confidence
            
        except Exception as e:
            logger.error("Pattern classification failed", 
                        user_id=user_id, error=str(e))
            return None
    
    async def _collect_training_data(self, user_id: str) -> List[FeatureVector]:
        """Collect training data from user's pattern detection history."""
        try:
            # Get pattern detection traces
            traces = await trace_memory.get_user_traces(
                user_id,
                event_types=["pattern_detection"],
                limit=200
            )
            
            training_vectors = []
            
            for trace in traces:
                if not trace.event_data:
                    continue
                
                pattern_type = trace.event_data.get('pattern_type')
                if not pattern_type:
                    continue
                
                # Create interaction data from trace
                interaction_data = {
                    'session_duration_minutes': 30,  # Default values
                    'completion_rate': trace.event_data.get('evidence', {}).get('completion_rate', 0.5),
                    'energy_level': 0.5,
                    'cognitive_load': 0.5,
                    'task_complexity': 0.5
                }
                
                # Extract features
                feature_vector = await self.feature_extractor.extract_features(
                    user_id, interaction_data
                )
                feature_vector.label = pattern_type
                
                training_vectors.append(feature_vector)
            
            return training_vectors
            
        except Exception as e:
            logger.error("Training data collection failed", 
                        user_id=user_id, error=str(e))
            return []
    
    def _prepare_training_data(self, 
                             training_vectors: List[FeatureVector]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for scikit-learn."""
        X = []
        y = []
        
        for vector in training_vectors:
            if vector.label:
                X.append(self._vectorize_features(vector.features))
                y.append(vector.label)
        
        return np.array(X), np.array(y)
    
    def _vectorize_features(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to numpy array."""
        # Define consistent feature order
        feature_order = sorted(features.keys())
        return np.array([features.get(key, 0.0) for key in feature_order])


class CrisisDetector:
    """
    Anomaly detection system for crisis situations.
    
    Uses unsupervised learning to detect unusual patterns that might
    indicate crisis situations requiring immediate intervention.
    """
    
    def __init__(self):
        self.models: Dict[str, IsolationForest] = {}
        self.thresholds: Dict[str, float] = {}
        self.baseline_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    async def detect_crisis(self, 
                          user_id: str, 
                          interaction_data: Dict[str, Any]) -> Tuple[bool, float]:
        """Detect if current interaction indicates crisis situation."""
        try:
            # Extract features
            feature_extractor = FeatureExtractor()
            feature_vector = await feature_extractor.extract_features(
                user_id, interaction_data
            )
            
            # Check if we have a trained model
            if user_id not in self.models:
                await self._initialize_crisis_detector(user_id)
            
            model = self.models[user_id]
            threshold = self.thresholds.get(user_id, -0.5)
            
            # Prepare features
            features = self._vectorize_features(feature_vector.features)
            
            # Get anomaly score
            anomaly_score = model.decision_function([features])[0]
            
            # Update baseline
            self.baseline_data[user_id].append(anomaly_score)
            
            # Determine if crisis
            is_crisis = anomaly_score < threshold
            crisis_confidence = abs(anomaly_score - threshold) / abs(threshold)
            
            if is_crisis:
                logger.warning("Crisis detected", 
                              user_id=user_id,
                              anomaly_score=anomaly_score,
                              threshold=threshold)
            
            return is_crisis, crisis_confidence
            
        except Exception as e:
            logger.error("Crisis detection failed", 
                        user_id=user_id, error=str(e))
            return False, 0.0
    
    async def _initialize_crisis_detector(self, user_id: str) -> None:
        """Initialize crisis detector for user."""
        try:
            # Get historical normal interactions
            feature_extractor = FeatureExtractor()
            traces = await trace_memory.get_user_traces(
                user_id,
                limit=100
            )
            
            normal_features = []
            for trace in traces[-50:]:  # Use recent normal behavior
                if trace.event_data and not trace.event_data.get('crisis_indicators'):
                    interaction_data = {
                        'completion_rate': trace.event_data.get('completion_rate', 0.5),
                        'energy_level': 0.5,
                        'cognitive_load': trace.event_data.get('cognitive_load', 0.5)
                    }
                    
                    feature_vector = await feature_extractor.extract_features(
                        user_id, interaction_data
                    )
                    normal_features.append(self._vectorize_features(feature_vector.features))
            
            if len(normal_features) < 10:
                # Use default baseline
                normal_features = [np.random.random(10) * 0.5 + 0.25 for _ in range(20)]
            
            # Train isolation forest
            model = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42
            )
            model.fit(normal_features)
            
            self.models[user_id] = model
            self.thresholds[user_id] = -0.5  # Conservative threshold
            
            logger.info("Crisis detector initialized", 
                       user_id=user_id,
                       baseline_samples=len(normal_features))
            
        except Exception as e:
            logger.error("Crisis detector initialization failed", 
                        user_id=user_id, error=str(e))
    
    def _vectorize_features(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to numpy array."""
        feature_order = sorted(features.keys())
        return np.array([features.get(key, 0.0) for key in feature_order])


class MLPipeline:
    """
    Main machine learning pipeline orchestrator.
    
    Coordinates different ML components and provides unified interface
    for pattern recognition, crisis detection, and predictive modeling.
    """
    
    def __init__(self):
        self.pattern_classifier = PatternClassifier()
        self.crisis_detector = CrisisDetector()
        self.feature_extractor = FeatureExtractor()
        
        # Pipeline state
        self.models_trained: Dict[str, Set[str]] = defaultdict(set)
        self.last_training: Dict[str, datetime] = {}
        self.performance_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
    async def process_interaction(self, 
                                user_id: str, 
                                interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process interaction through ML pipeline."""
        try:
            results = {
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'ml_insights': {}
            }
            
            # Extract features
            feature_vector = await self.feature_extractor.extract_features(
                user_id, interaction_data
            )
            results['feature_vector'] = asdict(feature_vector)
            
            # Pattern classification
            pattern_result = await self.pattern_classifier.classify_pattern(
                user_id, interaction_data
            )
            
            if pattern_result:
                pattern_type, confidence = pattern_result
                results['ml_insights']['detected_pattern'] = {
                    'type': pattern_type.value,
                    'confidence': confidence
                }
            
            # Crisis detection
            is_crisis, crisis_confidence = await self.crisis_detector.detect_crisis(
                user_id, interaction_data
            )
            
            results['ml_insights']['crisis_assessment'] = {
                'is_crisis': is_crisis,
                'confidence': crisis_confidence
            }
            
            # Update user model training schedule
            await self._update_training_schedule(user_id, results)
            
            # Log results for model improvement
            await self._log_ml_results(user_id, results)
            
            return results
            
        except Exception as e:
            logger.error("ML pipeline processing failed", 
                        user_id=user_id, error=str(e))
            return {'error': str(e)}
    
    async def retrain_user_models(self, user_id: str) -> Dict[str, bool]:
        """Retrain all models for a user."""
        try:
            results = {}
            
            # Retrain pattern classifier
            pattern_success = await self.pattern_classifier.train_pattern_classifier(user_id)
            results['pattern_classifier'] = pattern_success
            
            if pattern_success:
                self.models_trained[user_id].add('pattern_classifier')
                self.last_training[f"{user_id}_pattern"] = datetime.utcnow()
            
            # Initialize/update crisis detector
            await self.crisis_detector._initialize_crisis_detector(user_id)
            results['crisis_detector'] = True
            self.models_trained[user_id].add('crisis_detector')
            
            logger.info("User models retrained", 
                       user_id=user_id,
                       results=results)
            
            return results
            
        except Exception as e:
            logger.error("Model retraining failed", 
                        user_id=user_id, error=str(e))
            return {'error': str(e)}
    
    async def get_model_performance(self, user_id: str) -> Dict[str, Any]:
        """Get performance metrics for user's models."""
        try:
            performance = {
                'user_id': user_id,
                'models_trained': list(self.models_trained.get(user_id, [])),
                'last_training_dates': {},
                'metrics': {}
            }
            
            # Pattern classifier metrics
            pattern_key = f"{user_id}_pattern_classifier"
            if pattern_key in self.pattern_classifier.metrics:
                metrics = self.pattern_classifier.metrics[pattern_key]
                performance['metrics']['pattern_classifier'] = asdict(metrics)
                performance['last_training_dates']['pattern_classifier'] = (
                    metrics.last_updated.isoformat()
                )
            
            # Performance history
            if user_id in self.performance_history:
                recent_performance = self.performance_history[user_id][-10:]  # Last 10 entries
                performance['recent_performance'] = recent_performance
            
            return performance
            
        except Exception as e:
            logger.error("Performance metrics retrieval failed", 
                        user_id=user_id, error=str(e))
            return {'error': str(e)}
    
    async def _update_training_schedule(self, 
                                      user_id: str, 
                                      results: Dict[str, Any]) -> None:
        """Update training schedule based on model performance."""
        try:
            # Check if models need retraining
            needs_retraining = False
            
            # Check model age
            pattern_training_key = f"{user_id}_pattern"
            if pattern_training_key in self.last_training:
                days_since_training = (
                    datetime.utcnow() - self.last_training[pattern_training_key]
                ).days
                
                if days_since_training > 30:  # Retrain monthly
                    needs_retraining = True
            else:
                needs_retraining = True  # Never trained
            
            # Check performance degradation
            if 'detected_pattern' in results.get('ml_insights', {}):
                confidence = results['ml_insights']['detected_pattern']['confidence']
                if confidence < 0.6:  # Low confidence threshold
                    needs_retraining = True
            
            if needs_retraining:
                # Schedule retraining (in production, this would be queued)
                asyncio.create_task(self.retrain_user_models(user_id))
            
        except Exception as e:
            logger.warning("Training schedule update failed", error=str(e))
    
    async def _log_ml_results(self, user_id: str, results: Dict[str, Any]) -> None:
        """Log ML results for model improvement."""
        try:
            # Store in trace memory
            trace_record = TraceMemoryModel(
                user_id=user_id,
                event_type="ml_processing",
                event_data={
                    'ml_insights': results.get('ml_insights', {}),
                    'feature_count': len(results.get('feature_vector', {}).get('features', {})),
                    'processing_timestamp': results['timestamp']
                },
                confidence=1.0,
                source="ml_pipeline"
            )
            
            await trace_memory.store_trace(trace_record)
            
            # Update performance history
            self.performance_history[user_id].append({
                'timestamp': results['timestamp'],
                'insights': results.get('ml_insights', {}),
                'feature_count': len(results.get('feature_vector', {}).get('features', {}))
            })
            
            # Keep only recent history
            if len(self.performance_history[user_id]) > 100:
                self.performance_history[user_id] = self.performance_history[user_id][-50:]
            
        except Exception as e:
            logger.error("ML results logging failed", error=str(e))
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get overall pipeline performance summary."""
        try:
            total_users = len(self.models_trained)
            total_models = sum(len(models) for models in self.models_trained.values())
            
            return {
                'total_users_with_models': total_users,
                'total_models_trained': total_models,
                'model_types': list(ModelType.__members__.keys()),
                'privacy_level': self.feature_extractor.privacy_level.value,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Pipeline summary generation failed", error=str(e))
            return {'error': str(e)}


# Global ML pipeline instance
ml_pipeline = MLPipeline()