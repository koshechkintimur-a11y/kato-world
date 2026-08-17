# brain_core/metacognition.py
"""
Metacognition v2: Uncertainty monitoring, confidence calibration, error awareness.
Based on Fleming & Dolan (2012), Shea et al. (2014), Bang & Fleming (2018),
Maniscalco & Lau (2012), Rouault et al. (2018).

Core ideas:
- Metacognition = cognition about cognition
- Type 1: object-level performance (accuracy, speed)
- Type 2: meta-level judgments (confidence, uncertainty)
- Good metacognition: confidence tracks accuracy (metacognitive sensitivity)
- Calibration: confidence matches true probability correct
- Error awareness: detecting own mistakes before external feedback
"""
from __future__ import annotations
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from enum import Enum
import random

class ConfidenceLevel(Enum):
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9

@dataclass
class DecisionRecord:
    """Record of a decision with metacognitive tags"""
    timestamp: float
    decision_id: str
    context: Dict[str, Any]
    
    # Type 1: Object-level
    chosen_action: str
    alternatives: List[str]
    outcome: Optional[str] = None          # success/failure/neutral
    outcome_value: float = 0.0             # reward/punishment
    correctness: Optional[bool] = None     # was it the right choice?
    
    # Type 2: Meta-level
    confidence: float = 0.5                # 0-1, before outcome
    uncertainty: float = 0.5               # 1 - confidence (but distinct)
    expected_value: float = 0.0            # expected outcome value
    risk_estimate: float = 0.0             # estimated variance
    
    # Post-decision
    confidence_post: Optional[float] = None
    error_detected: bool = False
    surprise: float = 0.0
    learning_signal: float = 0.0

@dataclass
class MetacognitiveBelief:
    """A belief about own cognitive processes"""
    domain: str                           # e.g., "navigation", "social", "learning"
    accuracy_estimate: float = 0.5        # "How good am I at this?"
    confidence_calibration: float = 0.5   # "Does my confidence match reality?"
    uncertainty_awareness: float = 0.5    # "Do I know when I don't know?"
    error_detection_rate: float = 0.5     # "Do I catch my mistakes?"
    last_updated: float = 0.0
    evidence_count: int = 0

class MetacognitionEngine:
    """
    Metacognitive monitoring and control for Kato.
    
    Two-level architecture:
    - Level 1 (Object): Decisions, actions, perceptions
    - Level 2 (Meta): Confidence, uncertainty, error monitoring, control
    
    Key functions:
    1. Monitor: Track confidence calibration per domain
    2. Control: Adjust decision thresholds based on uncertainty
    3. Learn: Update metacognitive beliefs from outcomes
    4. Report: Verbalizable self-assessment ("I'm not sure about this")
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # Decision history
        self.decisions: deque = deque(maxlen=1000)
        self.pending_decisions: Dict[str, DecisionRecord] = {}
        
        # Metacognitive beliefs (per domain)
        self.beliefs: Dict[str, MetacognitiveBelief] = {}
        self._init_default_beliefs()
        
        # Calibration tracking
        self.confidence_bins: Dict[int, List[Tuple[float, bool]]] = {i: [] for i in range(10)}
        
        # Error awareness
        self.recent_errors: deque = deque(maxlen=50)
        self.error_detection_latency: deque = deque(maxlen=20)  # ticks to detect
        
        # Control parameters
        self.confidence_threshold = 0.6       # below this → seek help / deliberate more
        self.uncertainty_threshold = 0.5      # above this → gather info
        self.error_awareness_threshold = 0.3  # surprise needed to trigger error detection
        
        # Metrics
        self.metrics = {
            "total_decisions": 0,
            "calibration_slope": 0.0,         # meta-d' / d' equivalent
            "overconfidence_bias": 0.0,        # mean(confidence - accuracy)
            "resolution": 0.0,                 # AUC of confidence-accuracy curve
            "error_detection_rate": 0.0,
            "metacognitive_efficiency": 0.0,   # meta-performance / performance
        }
        
        # Brain reference
        self._brain = None
    
    def _init_default_beliefs(self):
        domains = ["navigation", "social", "learning", "memory", "planning", 
                   "exploration", "communication", "self_assessment"]
        for d in domains:
            self.beliefs[d] = MetacognitiveBelief(domain=d)
    
    def set_brain_ref(self, brain_server_module):
        self._brain = brain_server_module
    
    # ============================================================
    # PRE-DECISION: Confidence & Uncertainty Estimation
    # ============================================================
    
    def estimate_confidence(self, domain: str, context: Dict, 
                           action_values: Dict[str, float]) -> Tuple[float, float]:
        """
        Estimate confidence and uncertainty BEFORE decision.
        Returns (confidence, uncertainty) in [0, 1].
        """
        belief = self.beliefs.get(domain, MetacognitiveBelief(domain=domain))
        
        # Base confidence from metacognitive belief
        base_confidence = belief.accuracy_estimate * belief.confidence_calibration
        
        # Adjust for context uncertainty
        context_uncertainty = self._assess_context_uncertainty(context)
        
        # Adjust for action value spread (more spread = more confident in best)
        if action_values:
            values = list(action_values.values())
            if len(values) > 1:
                best = max(values)
                second = sorted(values)[-2] if len(values) > 1 else 0
                spread = best - second
                value_confidence = min(1.0, spread * 2)  # larger gap = more confident
            else:
                value_confidence = 0.5
        else:
            value_confidence = 0.5
        
        # Combined confidence (weighted)
        confidence = (base_confidence * 0.4 + 
                     (1 - context_uncertainty) * 0.3 + 
                     value_confidence * 0.3)
        
        # Uncertainty is not just 1-confidence; it's distinct
        uncertainty = (context_uncertainty * 0.5 + 
                      (1 - belief.uncertainty_awareness) * 0.3 +
                      (1 - value_confidence) * 0.2)
        
        return max(0.0, min(1.0, confidence)), max(0.0, min(1.0, uncertainty))
    
    def _assess_context_uncertainty(self, context: Dict) -> float:
        """Assess how uncertain the current context is"""
        uncertainty = 0.3  # baseline
        
        # Novelty increases uncertainty
        if context.get("novelty", 0) > 0.6:
            uncertainty += 0.2
        
        # Conflict increases uncertainty
        if context.get("conflict", 0) > 0.5:
            uncertainty += 0.2
        
        # Low memory match increases uncertainty
        if context.get("memory_match", 1) < 0.4:
            uncertainty += 0.15
        
        # Stress reduces metacognitive accuracy
        if context.get("stress", 0) > 60:
            uncertainty += 0.1
        
        return min(1.0, uncertainty)
    
    def should_deliberate(self, confidence: float, uncertainty: float, 
                         domain: str) -> Tuple[bool, str]:
        """
        Metacognitive control: should we use System 2 (deliberate)?
        Returns (should_deliberate, reason)
        """
        belief = self.beliefs.get(domain)
        
        # Low confidence → deliberate
        if confidence < self.confidence_threshold:
            return True, f"Low confidence ({confidence:.2f} < {self.confidence_threshold})"
        
        # High uncertainty → deliberate
        if uncertainty > self.uncertainty_threshold:
            return True, f"High uncertainty ({uncertainty:.2f} > {self.uncertainty_threshold})"
        
        # Domain-specific: if we're poorly calibrated here, deliberate
        if belief and belief.confidence_calibration < 0.4:
            return True, f"Poor calibration in {domain} ({belief.confidence_calibration:.2f})"
        
        # High stakes (from context) → deliberate
        # This would come from the decision context
        
        return False, "Sufficient confidence for System 1"
    
    # ============================================================
    # DECISION RECORDING
    # ============================================================
    
    def record_decision(self, domain: str, context: Dict, 
                       chosen_action: str, alternatives: List[str],
                       action_values: Dict[str, float],
                       confidence: float, uncertainty: float) -> str:
        """Record a decision for later outcome tracking"""
        decision_id = f"{domain}_{int(time.time()*1000)}_{random.randint(100,999)}"
        
        record = DecisionRecord(
            timestamp=time.time(),
            decision_id=decision_id,
            context=context,
            chosen_action=chosen_action,
            alternatives=alternatives,
            confidence=confidence,
            uncertainty=uncertainty,
            expected_value=action_values.get(chosen_action, 0.0),
            risk_estimate=uncertainty  # proxy
        )
        
        self.pending_decisions[decision_id] = record
        self.decisions.append(record)
        self.metrics["total_decisions"] += 1
        
        return decision_id
    
    def record_outcome(self, decision_id: str, outcome: str, 
                      outcome_value: float, correctness: bool = None):
        """Record outcome and update metacognition"""
        if decision_id not in self.pending_decisions:
            return
        
        record = self.pending_decisions.pop(decision_id)
        record.outcome = outcome
        record.outcome_value = outcome_value
        record.correctness = correctness
        
        # Post-decision confidence (often lower after errors)
        if correctness is False:
            record.confidence_post = record.confidence * 0.7
            record.error_detected = True
            self.recent_errors.append({
                "decision_id": decision_id,
                "domain": record.context.get("domain", "unknown"),
                "confidence": record.confidence,
                "timestamp": time.time()
            })
        else:
            record.confidence_post = min(1.0, record.confidence * 1.1)
        
        # Surprise = |expected - actual|
        record.surprise = abs(record.expected_value - outcome_value)
        
        # Learning signal for metacognitive beliefs
        self._update_metacognitive_beliefs(record)
        self._update_calibration(record)
        self._check_error_awareness(record)
    
    def _update_metacognitive_beliefs(self, record: DecisionRecord):
        """Update domain-specific metacognitive beliefs"""
        domain = record.context.get("domain", "general")
        belief = self.beliefs.get(domain)
        if not belief:
            belief = MetacognitiveBelief(domain=domain)
            self.beliefs[domain] = belief
        
        alpha = 0.1  # learning rate
        n = belief.evidence_count
        
        # Accuracy estimate
        if record.correctness is not None:
            belief.accuracy_estimate = (belief.accuracy_estimate * n + 
                                       (1.0 if record.correctness else 0.0)) / (n + 1)
        
        # Confidence calibration: does confidence match correctness?
        if record.correctness is not None:
            calibration = 1.0 - abs(record.confidence - (1.0 if record.correctness else 0.0))
            belief.confidence_calibration = (belief.confidence_calibration * n + calibration) / (n + 1)
        
        # Uncertainty awareness: did we express uncertainty when wrong?
        if record.correctness is False and record.uncertainty > 0.5:
            ua = 1.0
        elif record.correctness is True and record.uncertainty < 0.5:
            ua = 1.0
        else:
            ua = 0.5
        belief.uncertainty_awareness = (belief.uncertainty_awareness * n + ua) / (n + 1)
        
        # Error detection rate
        if record.error_detected:
            ed = 1.0
        elif record.correctness is False:
            ed = 0.0
        else:
            ed = 0.5  # neutral
        belief.error_detection_rate = (belief.error_detection_rate * n + ed) / (n + 1)
        
        belief.evidence_count += 1
        belief.last_updated = time.time()
    
    def _update_calibration(self, record: DecisionRecord):
        """Update global calibration tracking (for meta-d' computation)"""
        if record.correctness is None:
            return
        
        bin_idx = int(record.confidence * 10)
        bin_idx = min(9, max(0, bin_idx))
        self.confidence_bins[bin_idx].append((record.confidence, record.correctness))
        
        # Keep bins bounded
        if len(self.confidence_bins[bin_idx]) > 100:
            self.confidence_bins[bin_idx] = self.confidence_bins[bin_idx][-100:]
    
    def _check_error_awareness(self, record: DecisionRecord):
        """Detect if we became aware of error (surprise > threshold)"""
        if record.correctness is False and record.surprise > self.error_awareness_threshold:
            record.error_detected = True
            self.error_detection_latency.append(time.time() - record.timestamp)
    
    def compute_calibration_metrics(self) -> Dict[str, float]:
        """Compute calibration slope, overconfidence, resolution"""
        # Bin-wise accuracy vs confidence
        bin_centers = []
        bin_accuracies = []
        bin_confidences = []
        bin_counts = []
        
        for i, samples in self.confidence_bins.items():
            if len(samples) < 5:
                continue
            mean_conf = sum(s[0] for s in samples) / len(samples)
            accuracy = sum(1.0 for s in samples if s[1]) / len(samples)
            bin_centers.append(i / 10.0)
            bin_confidences.append(mean_conf)
            bin_accuracies.append(accuracy)
            bin_counts.append(len(samples))
        
        if len(bin_centers) < 3:
            return {"calibration_slope": 0.5, "overconfidence_bias": 0.0, "resolution": 0.0}
        
        # Calibration slope (linear fit: accuracy = a + b * confidence)
        n = len(bin_centers)
        sum_x = sum(bin_confidences)
        sum_y = sum(bin_accuracies)
        sum_xy = sum(x*y for x,y in zip(bin_confidences, bin_accuracies))
        sum_x2 = sum(x*x for x in bin_confidences)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x + 1e-8)
        intercept = (sum_y - slope * sum_x) / n
        
        # Overconfidence bias: mean(confidence - accuracy) weighted by count
        total = sum(bin_counts)
        bias = sum((c - a) * cnt for c, a, cnt in zip(bin_confidences, bin_accuracies, bin_counts)) / total
        
        # Resolution: AUC of confidence-accuracy curve (simplified)
        resolution = slope  # proxy
        
        self.metrics["calibration_slope"] = slope
        self.metrics["overconfidence_bias"] = bias
        self.metrics["resolution"] = resolution
        
        return {
            "calibration_slope": slope,
            "overconfidence_bias": bias,
            "resolution": resolution,
            "bins": len(bin_centers)
        }
    
    def compute_metacognitive_efficiency(self) -> float:
        """
        Metacognitive efficiency = meta-performance / performance
        (Fleming & Lau, 2014)
        """
        # Type 1 performance (accuracy)
        recent = [d for d in self.decisions if d.correctness is not None][-100:]
        if not recent:
            return 0.5
        
        accuracy = sum(1 for d in recent if d.correctness) / len(recent)
        
        # Type 2 performance (metacognitive sensitivity)
        # Simplified: correlation between confidence and correctness
        confidences = [d.confidence for d in recent]
        corrects = [1.0 if d.correctness else 0.0 for d in recent]
        
        if len(set(confidences)) < 2:
            return 0.5
        
        # Point-biserial correlation
        mean_conf = sum(confidences) / len(confidences)
        mean_correct = sum(corrects) / len(corrects)
        
        cov = sum((c - mean_conf) * (cr - mean_correct) 
                 for c, cr in zip(confidences, corrects)) / len(confidences)
        var_conf = sum((c - mean_conf)**2 for c in confidences) / len(confidences)
        var_correct = mean_correct * (1 - mean_correct)
        
        if var_conf * var_correct > 0:
            meta_sensitivity = cov / math.sqrt(var_conf * var_correct)
        else:
            meta_sensitivity = 0
        
        # Efficiency
        if accuracy > 0:
            efficiency = meta_sensitivity / accuracy
        else:
            efficiency = 0
        
        self.metrics["metacognitive_efficiency"] = max(0, min(2, efficiency))
        return self.metrics["metacognitive_efficiency"]
    
    def get_verbalizable_self_assessment(self, domain: str = None) -> Dict[str, str]:
        """Generate verbalizable self-report (what Kato can say about herself)"""
        if domain:
            belief = self.beliefs.get(domain)
            if not belief:
                return {"statement": "Я не знаю, насколько я хороша в этом."}
            
            # Map metrics to verbal labels
            acc_label = self._label_quality(belief.accuracy_estimate, 
                ["очень плохо", "плохо", "нормально", "хорошо", "очень хорошо"])
            cal_label = self._label_quality(belief.confidence_calibration,
                ["совсем не знаю своих сил", "часто ошибаюсь в оценках", "иногда ошибаюсь", "обычно верно оцениваю", "всегда точно знаю"])
            ua_label = self._label_quality(belief.uncertainty_awareness,
                ["не замечаю, когда не знаю", "редко замечаю", "иногда замечаю", "часто замечаю", "всегда знаю, когда не знаю"])
            
            return {
                "domain": domain,
                "statement": f"В {domain} я работаю {acc_label}. {cal_label.capitalize()}. {ua_label.capitalize()}.",
                "accuracy": belief.accuracy_estimate,
                "calibration": belief.confidence_calibration,
                "uncertainty_awareness": belief.uncertainty_awareness
            }
        
        # Global assessment
        overall_acc = sum(b.accuracy_estimate for b in self.beliefs.values()) / len(self.beliefs)
        overall_cal = sum(b.confidence_calibration for b in self.beliefs.values()) / len(self.beliefs)
        
        return {
            "statement": f"В целом я думаю, что справляюсь {self._label_quality(overall_acc, ['плохо', 'не очень', 'нормально', 'хорошо', 'отлично'])}. Уверенность в своих оценках — {self._label_quality(overall_cal, ['низкая', 'ниже средней', 'средняя', 'выше средней', 'высокая'])}.",
            "overall_accuracy": overall_acc,
            "overall_calibration": overall_cal
        }
    
    def _label_quality(self, value: float, labels: List[str]) -> str:
        idx = int(value * (len(labels) - 1))
        return labels[max(0, min(len(labels)-1, idx))]
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "beliefs": {
                k: {
                    "accuracy": v.accuracy_estimate,
                    "calibration": v.confidence_calibration,
                    "uncertainty_awareness": v.uncertainty_awareness,
                    "error_detection": v.error_detection_rate,
                    "evidence": v.evidence_count
                }
                for k, v in self.beliefs.items()
            },
            "metrics": self.metrics,
            "pending_decisions": len(self.pending_decisions),
            "recent_errors": len(self.recent_errors),
            "self_assessment": self.get_verbalizable_self_assessment()
        }


def create_metacognition_engine(agent_id: str) -> MetacognitionEngine:
    return MetacognitionEngine(agent_id)