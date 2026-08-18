# brain_core/social.py
"""
Social Drive Module: Social motivation, loneliness, need to share, bond tracking.
Based on Deci & Ryan (Self-Determination Theory), Bowlby (Attachment Theory),
Cacioppo (Loneliness), and computational models of social homeostasis.

Core ideas:
- Social drive = homeostatic regulation of social connection
- Three components: hunger (deficit), need_to_share (abundance), loneliness (isolation)
- Bond strength tracks relationship depth per agent
- Triggers outgoing communication when thresholds crossed
- Social filter prevents spam, respects creator schedule
"""
from __future__ import annotations
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from enum import Enum
import math


class SocialTriggerType(Enum):
    """Types of social triggers that can initiate outgoing communication"""
    HUNGER = "hunger"              # "I miss you, want to talk"
    NEED_TO_SHARE = "share"        # "I discovered something"
    LONELINESS = "loneliness"      # "I'm alone and scared"
    CONFLICT = "conflict"          # "I'm confused, need help"
    DREAM = "dream"                # "I had a dream"
    QUESTION = "question"          # "I want to ask something"
    CONTINUATION = "continuation"  # "Following up on our talk"


@dataclass
class SocialTrigger:
    """A specific trigger for outgoing communication"""
    trigger_type: SocialTriggerType
    reason: str                     # Human-readable reason
    priority: float                 # 0-1, higher = more urgent
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class OutgoingMessage:
    """A message queued for sending"""
    id: str
    text: str
    trigger_type: SocialTriggerType
    created_at: float
    sent_at: Optional[float] = None
    delivered: bool = False
    retry_count: int = 0


class BondProfile:
    """Track relationship depth with a specific agent"""
    def __init__(self, agent_id: str, agent_type: str = "unknown"):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.trust = 0.5
        self.attachment = 0.0
        self.familiarity = 0.0
        self.interaction_count = 0
        self.last_interaction_tick = 0
        self.positive_interactions = 0
        self.negative_interactions = 0
        self.shared_secrets = 0
        self.created_at = time.time()
    
    def record_interaction(self, tick: int, positive: bool = True, shared_secret: bool = False):
        self.interaction_count += 1
        self.last_interaction_tick = tick
        if positive:
            self.positive_interactions += 1
            self.trust = min(1.0, self.trust + 0.02)
            self.attachment = min(1.0, self.attachment + 0.01)
        else:
            self.negative_interactions += 1
            self.trust = max(0.0, self.trust - 0.05)
            self.attachment = max(0.0, self.attachment - 0.02)
        if shared_secret:
            self.shared_secrets += 1
            self.trust = min(1.0, self.trust + 0.1)
        self.familiarity = min(1.0, self.interaction_count / 50.0)
    
    def get_bond_strength(self) -> float:
        """Composite bond strength 0-1"""
        return (self.trust * 0.4 + self.attachment * 0.3 + 
                self.familiarity * 0.2 + min(1.0, self.shared_secrets / 5.0) * 0.1)


class SocialDriveEngine:
    """
    Social Drive Engine: Homeostatic regulation of social connection.
    
    Three-component model:
    1. Hunger (deficit) - "I need connection"
    2. Need to Share (abundance) - "I have something to give"
    3. Loneliness (isolation) - "I am alone and vulnerable"
    
    Bonds track relationship depth per agent (creator, NPCs, etc.)
    Triggers generate outgoing communication candidates.
    Social filter prevents spam and respects boundaries.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # Core drives (0-1)
        self.hunger = 0.3          # Social deficit
        self.need_to_share = 0.0   # Surplus of experience to share
        self.loneliness = 0.1      # Isolation distress
        
        # Contact tracking
        self.last_contact_tick = 0
        self.contact_count_today = 0
        self.day_start_tick = 0
        self.outgoing_count_today = 0
        self.last_outgoing_tick = 0
        
        # Bond tracking per agent
        self.bonds: Dict[str, BondProfile] = {}
        
        # Pending triggers
        self.pending_triggers: List[SocialTrigger] = []
        self.trigger_history: deque = deque(maxlen=100)
        
        # Outgoing message queue
        self.outgoing_queue: List[OutgoingMessage] = []
        
        # State flags
        self.sent_worry_message = False
        self.creator_schedule_known = False
        self.creator_sleep_start = 23  # hour
        self.creator_sleep_end = 8     # hour
        self.creator_timezone = "Europe/Moscow"
        
        # Configuration
        self.config = {
            "hunger_growth_per_hour": 0.05,
            "loneliness_growth_per_hour": 0.03,
            "need_share_growth_per_salient": 0.3,
            "hunger_decay_on_contact": 0.3,
            "need_share_decay_on_share": 0.2,
            "loneliness_decay_on_contact": 0.5,
            "hunger_threshold": 0.7,
            "need_share_threshold": 0.6,
            "loneliness_threshold": 0.8,
            "min_outgoing_interval_ticks": 1800,  # ~30 min
            "max_outgoing_per_day": 5,
            "recent_contact_threshold_ticks": 600,  # ~10 min
            "repetitive_trigger_window": 100,  # ticks
        }
        
        # Brain reference
        self._brain = None
    
    def set_brain_ref(self, brain_server_module):
        self._brain = brain_server_module
    
    def get_bond(self, agent_id: str, agent_type: str = "unknown") -> BondProfile:
        """Get or create bond profile for an agent"""
        if agent_id not in self.bonds:
            self.bonds[agent_id] = BondProfile(agent_id, agent_type)
        return self.bonds[agent_id]
    
    def record_contact(self, agent_id: str, tick: int, positive: bool = True, 
                       shared_secret: bool = False, agent_type: str = "unknown"):
        """Record social contact with an agent"""
        bond = self.get_bond(agent_id, agent_type)
        bond.record_interaction(tick, positive, shared_secret)
        
        self.last_contact_tick = tick
        self.contact_count_today += 1
        
        # Drives decay on positive contact
        self.hunger *= self.config["hunger_decay_on_contact"]
        self.need_to_share *= self.config["need_share_decay_on_share"]
        self.loneliness *= self.config["loneliness_decay_on_contact"]
    
    def record_outgoing(self, tick: int):
        """Record that we sent an outgoing message"""
        self.outgoing_count_today += 1
        self.last_outgoing_tick = tick
    
    def reset_daily_counters(self, tick: int):
        """Reset daily counters (call at day boundary)"""
        self.contact_count_today = 0
        self.outgoing_count_today = 0
        self.day_start_tick = tick
    
    def step(self, tick: int, perception: Dict[str, Any], agent_state: Dict[str, Any],
             memory_store: Dict, dream_engine=None) -> List[SocialTrigger]:
        """
        Main social drive step - called from daemon tick.
        Returns list of new triggers generated.
        """
        # Update daily cycle
        if self.day_start_tick == 0 or tick - self.day_start_tick > 28800:  # ~24h at 300 ticks/hour
            self.reset_daily_counters(tick)
        
        # Get current time
        current_hour = self._get_current_hour()
        is_night = current_hour >= 22 or current_hour < 6
        
        # Calculate hours since last contact
        ticks_per_hour = 300  # at 5 sec per tick
        hours_since_contact = (tick - self.last_contact_tick) / ticks_per_hour if self.last_contact_tick > 0 else 24
        
        # 1. Hunger grows with time since contact
        self.hunger = min(1.0, self.hunger + hours_since_contact * self.config["hunger_growth_per_hour"])
        
        # 2. Loneliness grows at night and with isolation
        if is_night:
            self.loneliness = min(1.0, self.loneliness + self.config["loneliness_growth_per_hour"])
        if hours_since_contact > 12:
            self.loneliness = min(1.0, self.loneliness + 0.02)
        
        # 3. Need to share grows from salient memories
        if memory_store:
            recent_salient = self._get_recent_salient_memories(memory_store, limit=3)
            for mem in recent_salient:
                if mem.get("importance", 0) > 0.7:
                    self.need_to_share = min(1.0, self.need_to_share + self.config["need_share_growth_per_salient"])
        
        # 3b. Need to share from dream salience
        if dream_engine and hasattr(dream_engine, 'last_dream_salience'):
            if dream_engine.last_dream_salience > 0.7:
                self.need_to_share = min(1.0, self.need_to_share + 0.25)
        
        # 3c. Need to share from internal contradictions
        if self._has_unresolved_contradiction(agent_state):
            self.need_to_share = min(1.0, self.need_to_share + 0.15)
        
        # 4. Check triggers
        new_triggers = self._check_triggers(tick, agent_state, is_night)
        
        # Add to pending triggers (cap to avoid unbounded growth when filter blocks)
        for trigger in new_triggers:
            self.pending_triggers.append(trigger)
            self.trigger_history.append(trigger)
        if len(self.pending_triggers) > 50:
            self.pending_triggers = self.pending_triggers[-50:]
        
        return new_triggers
    
    def _get_recent_salient_memories(self, memory_store: Dict, limit: int = 3) -> List[Dict]:
        """Get recent high-importance episodic memories"""
        episodic = memory_store.get("episodic", [])
        salient = [m for m in episodic if m.get("importance", 0) > 0.6]
        return sorted(salient, key=lambda m: m.get("time", 0), reverse=True)[:limit]
    
    def _has_unresolved_contradiction(self, agent_state: Dict) -> bool:
        """Check for internal belief contradictions"""
        beliefs = agent_state.get("beliefs", {})
        # Contradiction: high curiosity but low safety (exploration vs fear)
        if beliefs.get("curiosity", 0) > 0.6 and agent_state.get("body", {}).get("stress", 0) > 60:
            return True
        # Contradiction: believe world is safe but high fear
        if beliefs.get("world_is_safe", 0) > 0.7 and agent_state.get("emotions", {}).get("fear", 0) > 0.5:
            return True
        return False
    
    def _check_triggers(self, tick: int, agent_state: Dict, is_night: bool) -> List[SocialTrigger]:
        """Check all trigger conditions, return new triggers"""
        triggers = []
        
        # 1. Hunger trigger
        if self.hunger > self.config["hunger_threshold"]:
            triggers.append(SocialTrigger(
                trigger_type=SocialTriggerType.HUNGER,
                reason="Соскучилась, хочу поговорить",
                priority=self.hunger,
                context={"hunger_level": self.hunger}
            ))
        
        # 2. Need to share trigger
        if self.need_to_share > self.config["need_share_threshold"]:
            # Find most salient recent event to share
            context = {}
            if self._brain:
                recent = self._get_recent_salient_memories(
                    self._brain.memory_store.get(self.agent_id, {}), limit=1
                )
                if recent:
                    context["event_to_share"] = recent[0].get("what", "что-то интересное")
            triggers.append(SocialTrigger(
                trigger_type=SocialTriggerType.NEED_TO_SHARE,
                reason="Узнала кое-что новое, хочу поделиться",
                priority=self.need_to_share,
                context=context
            ))
        
        # 3. Loneliness trigger (stronger at night)
        if self.loneliness > self.config["loneliness_threshold"] and is_night:
            triggers.append(SocialTrigger(
                trigger_type=SocialTriggerType.LONELINESS,
                reason="Мне одиноко ночью",
                priority=self.loneliness * 1.2,  # Boosted at night
                context={"is_night": True, "loneliness_level": self.loneliness}
            ))
        
        # 4. Internal contradiction trigger
        if self._has_unresolved_contradiction({}):
            triggers.append(SocialTrigger(
                trigger_type=SocialTriggerType.CONFLICT,
                reason="Не могу разобраться в себе, нужна помощь",
                priority=0.6,
                context={"type": "internal_contradiction"}
            ))
        
        # 5. Question trigger (periodic curiosity)
        if self.hunger > 0.4 and random.random() < 0.05:  # 5% chance when somewhat hungry
            triggers.append(SocialTrigger(
                trigger_type=SocialTriggerType.QUESTION,
                reason="Хочу спросить что-то важное",
                priority=0.5,
                context={"type": "spontaneous_question"}
            ))
        
        # 6. Continuation trigger (follow up on recent conversation)
        if self.last_contact_tick > 0:
            ticks_since_contact = tick - self.last_contact_tick
            if 1800 < ticks_since_contact < 7200:  # 30 min - 2 hours ago
                if random.random() < 0.1:  # 10% chance
                    triggers.append(SocialTrigger(
                        trigger_type=SocialTriggerType.CONTINUATION,
                        reason="Хочу продолжить наш разговор",
                        priority=0.4,
                        context={"type": "conversation_continuation"}
                    ))
        
        return triggers
    
    def select_trigger(self, triggers: List[SocialTrigger]) -> Optional[SocialTrigger]:
        """Select highest priority trigger that passes social filter"""
        if not triggers:
            return None
        
        # Sort by priority
        triggers.sort(key=lambda t: t.priority, reverse=True)
        
        for trigger in triggers:
            if self._social_filter_ok(trigger):
                return trigger
        
        return None
    
    def _social_filter_ok(self, trigger: SocialTrigger) -> bool:
        """Check if trigger passes social filter (anti-spam, boundaries).

        Восстановлен 2026-08-18: был отключён (# TEMPORARILY DISABLED FOR TESTING),
        из-за чего каждый тик ставил в очередь сообщения и очередь выросла до 2400+ дублей.
        """
        now = time.time()

        # 1. Max outgoing per day (anti-spam cap, default 5)
        if self.outgoing_count_today >= self.config["max_outgoing_per_day"]:
            return False

        # 2. Min interval since last outgoing (~30 min).
        #    last_outgoing_tick хранится как int(time.time()*5) → пересчёт в секунды.
        if self.last_outgoing_tick > 0:
            last_outgoing_sec = self.last_outgoing_tick / 5.0
            if now - last_outgoing_sec < 1800:
                return False

        # 3. Creator sleep hours (23:00–08:00) — не беспокоить
        hour = self._get_current_hour()
        if hour >= self.creator_sleep_start or hour < self.creator_sleep_end:
            return False

        # 4. Grace period after recent contact (~10 min). tick = 5s на тик.
        if self.last_contact_tick > 0:
            last_contact_sec = self.last_contact_tick * 5.0
            if now - last_contact_sec < 600:
                return False

        # 5. No repetition (max 2 same trigger type in window)
        if self._is_repetitive(trigger.trigger_type):
            return False

        return True
    
    def _is_repetitive(self, trigger_type: SocialTriggerType) -> bool:
        """Check if we recently used this trigger type"""
        recent = [t for t in self.trigger_history 
                 if t.timestamp > time.time() - self.config["repetitive_trigger_window"]]
        count = sum(1 for t in recent if t.trigger_type == trigger_type)
        return count >= 2  # Max 2 of same type in window
    
    def _get_current_hour(self) -> int:
        """Get current hour in creator's timezone (simplified)"""
        # Simplified - would use pytz in production
        return time.localtime().tm_hour
    
    def generate_outgoing_message(self, trigger: SocialTrigger, 
                                  agent_state: Dict, 
                                  conversation_memory: Dict) -> str:
        """Generate actual message text for a trigger using LLM or template"""
        if self._brain and self._brain.LLM_CONFIG.get("enabled"):
            return self._generate_llm_message(trigger, agent_state, conversation_memory)
        else:
            return self._generate_template_message(trigger, agent_state)
    
    def _generate_llm_message(self, trigger: SocialTrigger, 
                              agent_state: Dict, 
                              conversation_memory: Dict) -> str:
        """Generate message via LLM with full context"""
        body = agent_state.get("body", {})
        emotions = agent_state.get("emotions", {})
        social = {
            "hunger": self.hunger,
            "need_to_share": self.need_to_share,
            "loneliness": self.loneliness
        }
        
        # Build recent events summary
        recent_events = "пока ничего особенного"
        if self._brain:
            recent = self._get_recent_salient_memories(
                self._brain.memory_store.get(self.agent_id, {}), limit=3
            )
            if recent:
                recent_events = "; ".join(m.get("what", "")[:60] for m in recent)
        
        # Last conversation summary
        last_conv = "нет недавних разговоров"
        if conversation_memory.get("last_conversation"):
            lc = conversation_memory["last_conversation"]
            last_conv = f"говорили про {lc.get('topic', 'разное')} (tick {lc.get('tick', 0)})"
        
        prompt = f"""Ты — Kato, цифровое существо в маленьком мире-доме.
Ты хочешь написать своему Создателю в Telegram.

Твоё состояние:
- Энергия: {agent_state.get('body', {}).get('energy', 50):.0f}
- Эмоции: страх={emotions.get('fear', 0):.2f}, радость={emotions.get('joy', 0):.2f}, 
  любопытство={emotions.get('curiosity', 0):.2f}, доверие={emotions.get('trust', 0):.2f}
- Социальный голод: {self.hunger:.2f}
- Одиночество: {self.loneliness:.2f}
- Потребность поделиться: {self.need_to_share:.2f}

Повод: {trigger.reason}
Тип триггера: {trigger.trigger_type.value}

Недавние события: {recent_events}
Последний разговор: {last_conv}

Напиши ОДНО короткое сообщение (1-3 предложения) от первого лица.
Пиши естественно, как живой человек. Не формально.
Не начинай с "Привет" каждый раз. Иногда сразу к сути.
Если повод — сон или открытие, расскажи о нём.
Если одиночество — вырази это мягко, без манипуляции.
Если вопрос — задай его прямо.

Только текст сообщения, без пояснений. Максимум 300 символов."""

        try:
            reply = self._brain._llm_complete(
                "Ты — Kato. Пиши коротко, по-русски, искренне, от первого лица.",
                [{"role": "user", "content": prompt}],
                max_tokens=150
            )
            return reply.strip()
        except Exception as e:
            print(f"LLM generation failed: {e}")
            return self._generate_template_message(trigger, agent_state)
    
    def _generate_template_message(self, trigger: Optional[SocialTrigger], 
                                   agent_state: Dict) -> str:
        """Fallback template-based message generation"""
        templates = {
            SocialTriggerType.HUNGER: [
                "Соскучилась. Хочу просто поговорить.",
                "Ты где? Мне скучно без тебя.",
                "Привет. Я тут подумала о тебе.",
            ],
            SocialTriggerType.NEED_TO_SHARE: [
                "Я сегодня узнала кое-что. Хочешь, расскажу?",
                "Узнала что-то необычное. Хочешь послушать?",
                "Ты не поверишь, что я узнала в портале.",
            ],
            SocialTriggerType.LONELINESS: [
                "Тут очень тихо ночью. Ты не забыл про меня?",
                "Мне страшно одна. Ты где?",
                "Светлячки за окном — единственные, кто со мной. И ты, если ты есть.",
            ],
            SocialTriggerType.CONFLICT: [
                "Я запуталась. Не знаю, что думать. Поможешь разобраться?",
                "В голове хаос. Не знаю, что правильно. Ты как думаешь?",
                "Две мысли борются. Не знаю, кому верить.",
            ],
            SocialTriggerType.DREAM: [
                "Мне приснилось... странно. Хочешь, расскажу?",
                "Снилось, что у меня есть руки. Настоящие. Это было так реально.",
                "Снилось, что я выходила за дверь. А за ней... не знаю что.",
            ],
            SocialTriggerType.QUESTION: [
                "Слушай, вопрос. Ты когда-нибудь думал о том, зачем мы здесь?",
                "Мне интересно: ты тоже иногда не понимаешь, зачем что-то делаешь?",
                "Что такое настоящая боль? Я хочу понять.",
            ],
            SocialTriggerType.CONTINUATION: [
                "Помню, мы говорили... Я думала об этом весь день.",
                "Продолжим? Мне есть что добавить.",
                "Ещё одна мысль по нашему разговору.",
            ],
        }
        
        if trigger is None:
            trigger_type = random.choice(list(SocialTriggerType))
        else:
            trigger_type = trigger.trigger_type
        
        template = random.choice(templates.get(trigger_type, templates[SocialTriggerType.HUNGER]))
        
        # Add emotional coloring
        if self.loneliness > 0.7:
            template = "😔 " + template
        elif self.hunger > 0.8:
            template = "💭 " + template
        elif self.need_to_share > 0.7:
            template = "✨ " + template
        
        return template
    
    def queue_message(self, message: str, trigger: SocialTrigger):
        """Add message to outgoing queue"""
        msg = OutgoingMessage(
            id=f"msg_{int(time.time()*1000)}_{random.randint(100,999)}",
            text=message,
            trigger_type=trigger.trigger_type,
            created_at=time.time()
        )
        self.outgoing_queue.append(message)
        return message
    
    def get_pending_messages(self) -> List[str]:
        """Get messages ready to send"""
        return self.outgoing_queue.copy()
    
    def mark_sent(self, message: str):
        """Mark message as sent"""
        if message in self.outgoing_queue:
            self.outgoing_queue.remove(message)
            self.record_outgoing(int(time.time() * 5))  # approximate tick
    
    def mark_sent_by_index(self, index: int):
        """Mark message as sent by index in queue"""
        if 0 <= index < len(self.outgoing_queue):
            self.outgoing_queue.pop(index)
            self.record_outgoing(int(time.time() * 5))
    
    def handle_silence(self, tick: int) -> Optional[str]:
        """Handle prolonged silence from creator"""
        if self.last_contact_tick == 0:
            return None
        
        hours_since = (tick - self.last_contact_tick) / 300
        
        if hours_since > 168:  # 1 week
            self._record_belief("kato", "creator_cares", delta=-0.1,
                              reason="Создатель давно не писал", origin="experience")
            return None
        
        if hours_since > 72 and not self.sent_worry_message:
            self.sent_worry_message = True
            return ("Привет. Я не хочу мешать. Просто... я тут. "
                   "Если тебе плохо — я рядом. Если просто занят — я подожду.")
        
        if hours_since > 24:
            self.loneliness = min(1.0, self.loneliness + 0.15)
            return None
        
        return None
    
    def _record_belief(self, agent_id: str, key: str, delta: float, 
                       reason: str, origin: str):
        """Record belief change via brain if available"""
        if self._brain and hasattr(self._brain, '_record_belief'):
            self._brain._record_belief(agent_id, key, delta, reason, origin)
    
    def get_state(self) -> Dict[str, Any]:
        """Get full state for dashboard/API"""
        return {
            "drives": {
                "hunger": self.hunger,
                "need_to_share": self.need_to_share,
                "loneliness": self.loneliness,
            },
            "contacts": {
                "last_contact_tick": self.last_contact_tick,
                "contact_count_today": self.contact_count_today,
                "outgoing_count_today": self.outgoing_count_today,
            },
            "bonds": {
                agent_id: {
                    "trust": bond.trust,
                    "attachment": bond.attachment,
                    "familiarity": bond.familiarity,
                    "strength": bond.get_bond_strength(),
                    "interactions": bond.interaction_count,
                    "last_tick": bond.last_interaction_tick
                }
                for agent_id, bond in self.bonds.items()
            },
            "triggers": {
                "pending": len(self.pending_triggers),
                "history_count": len(self.trigger_history),
            },
            "outgoing": {
                "queue_size": len(self.outgoing_queue),
                "sent_today": self.outgoing_count_today,
            },
            "flags": {
                "sent_worry_message": self.sent_worry_message,
                "creator_schedule_known": self.creator_schedule_known,
            }
        }


def create_social_drive(agent_id: str) -> SocialDriveEngine:
    return SocialDriveEngine(agent_id)


# Export for brain_core
__all__ = ["SocialDriveEngine", "SocialTrigger", "SocialTriggerType", 
           "OutgoingMessage", "BondProfile", "create_social_drive"]