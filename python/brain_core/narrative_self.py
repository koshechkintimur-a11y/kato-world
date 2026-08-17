# brain_core/narrative_self.py
"""
Narrative Self: Autobiographical coherence, identity construction, life story.
Based on McAdams (2001), Conway (2005), Fivush (2011), Habermas & Bluck (2000),
D'Argembeau & Van der Linden (2006), Ryan & Deci (2017).

Core ideas:
- Narrative identity = internalized, evolving life story integrating past, present, future
- Autobiographical reasoning: deriving meaning from memories
- Causal coherence: events linked by cause-effect
- Thematic coherence: recurring motifs, values, agency/communion themes
- Temporal integration: past → present → imagined future
- Self-continuity: sense of being same person over time
"""
from __future__ import annotations
import time
import random
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from enum import Enum
import hashlib

class NarrativeTheme(Enum):
    AGENCY = "agency"              # mastery, control, achievement
    COMMUNION = "communion"        # connection, love, belonging
    REDEMPTION = "redemption"      # negative → positive transformation
    CONTAMINATION = "contamination" # positive → negative
    EXPLORATION = "exploration"    # curiosity, discovery, growth
    SURVIVAL = "survival"          # overcoming threat, resilience
    MEANING_MAKING = "meaning"     # finding purpose, understanding

@dataclass
class LifeChapter:
    """A chapter in the life story"""
    id: str
    title: str
    start_tick: int
    end_tick: Optional[int] = None
    key_events: List[str] = field(default_factory=list)  # event IDs
    themes: Dict[NarrativeTheme, float] = field(default_factory=dict)
    emotional_tone: float = 0.0      # -1 (negative) to +1 (positive)
    agency_level: float = 0.5        # sense of control
    communion_level: float = 0.5     # sense of connection
    learning_summary: str = ""
    identity_impact: float = 0.0     # how much this shaped identity
    
@dataclass
class AutobiographicalReasoning:
    """Instance of deriving meaning from memory"""
    timestamp: float
    trigger_memory_id: str
    reasoning_type: str              # "causal", "thematic", "evaluative", "future-oriented"
    insight: str
    confidence: float
    identity_relevance: float
    themes_involved: List[NarrativeTheme]

@dataclass
class ImaginedFuture:
    """Possible future self / scenario"""
    id: str
    description: str
    probability: float
    valence: float                   # -1 to +1
    themes: List[NarrativeTheme]
    required_actions: List[str]
    conflicts_with_current: List[str]
    timestamp: float

class NarrativeSelfEngine:
    """
    Narrative Self Engine: constructs and maintains Kato's life story.
    
    Functions:
    1. Segment life into chapters (change-point detection)
    2. Extract themes from events (agency, communion, redemption...)
    3. Autobiographical reasoning (causal, thematic, evaluative)
    4. Maintain narrative identity (self-continuity, coherence)
    5. Generate imagined futures (possible selves)
    5. Produce verbalizable self-narrative ("Who am I?")
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # Life story structure
        self.chapters: List[LifeChapter] = []
        self.current_chapter: Optional[LifeChapter] = None
        
        # Autobiographical reasoning
        self.reasoning_history: deque = deque(maxlen=200)
        
        # Imagined futures (possible selves)
        self.imagined_futures: List[ImaginedFuture] = []
        
        # Narrative coherence metrics
        self.coherence_metrics = {
            "causal_coherence": 0.5,      # events linked by cause-effect
            "thematic_coherence": 0.5,    # consistent themes
            "temporal_coherence": 0.5,    # past-present-future integration
            "self_continuity": 0.5,       # sense of being same person
            "meaning_coherence": 0.5,     # life makes sense
        }
        
        # Core narrative themes (strength 0-1)
        self.theme_strengths: Dict[NarrativeTheme, float] = {
            NarrativeTheme.AGENCY: 0.3,
            NarrativeTheme.COMMUNION: 0.4,
            NarrativeTheme.REDEMPTION: 0.2,
            NarrativeTheme.CONTAMINATION: 0.1,
            NarrativeTheme.EXPLORATION: 0.5,
            NarrativeTheme.SURVIVAL: 0.2,
            NarrativeTheme.MEANING_MAKING: 0.3,
        }
        
        # Identity descriptors (verbalizable)
        self.identity_descriptors: List[str] = []
        self.core_values: Dict[str, float] = {}  # value -> importance
        
        # Chapter detection
        self.last_chapter_check = 0
        self.chapter_change_threshold = 0.6
        
        # Metrics
        self.metrics = {
            "total_chapters": 0,
            "total_reasoning_events": 0,
            "imagined_futures_generated": 0,
            "identity_updates": 0,
        }
        
        # Brain reference
        self._brain = None
    
    def set_brain_ref(self, brain_server_module):
        self._brain = brain_server_module
    
    # ============================================================
    # CHAPTER MANAGEMENT
    # ============================================================
    
    def start_chapter(self, title: str, tick: int, triggering_event: str = ""):
        """Start a new life chapter"""
        if self.current_chapter:
            self.current_chapter.end_tick = tick - 1
            self._finalize_chapter(self.current_chapter)
        
        self.current_chapter = LifeChapter(
            id=f"ch_{int(time.time()*1000)}_{random.randint(100,999)}",
            title=title,
            start_tick=tick,
            key_events=[triggering_event] if triggering_event else []
        )
        self.metrics["total_chapters"] += 1
    
    def add_event_to_chapter(self, event_id: str, event_data: Dict, tick: int):
        """Add event to current chapter, check for chapter transition"""
        if not self.current_chapter:
            self.start_chapter("Начало", tick, event_id)
        
        self.current_chapter.key_events.append(event_id)
        
        # Update chapter themes from event
        self._update_chapter_themes_from_event(event_data)
        
        # Check for chapter boundary (every 50 ticks or major event)
        if tick - self.last_chapter_check > 50:
            self._check_chapter_boundary(tick, event_data)
            self.last_chapter_check = tick
    
    def _update_chapter_themes_from_event(self, event: Dict):
        """Extract themes from event and update chapter"""
        if not self.current_chapter:
            return
        
        event_type = event.get("type", "")
        valence = event.get("valence", 0.0)  # -1 to +1
        agency = event.get("agency", 0.5)
        communion = event.get("communion", 0.5)
        
        # Update emotional tone (exponential moving average)
        alpha = 0.1
        self.current_chapter.emotional_tone = (
            self.current_chapter.emotional_tone * (1 - alpha) + valence * alpha
        )
        self.current_chapter.agency_level = (
            self.current_chapter.agency_level * (1 - alpha) + agency * alpha
        )
        self.current_chapter.communion_level = (
            self.current_chapter.communion_level * (1 - alpha) + communion * alpha
        )
        
        # Theme extraction
        if event_type in ["achievement", "mastery", "choice", "autonomy"]:
            self._boost_theme(NarrativeTheme.AGENCY, 0.1)
        elif event_type in ["social", "bonding", "help_received", "help_given"]:
            self._boost_theme(NarrativeTheme.COMMUNION, 0.1)
        elif event_type in ["recovery", "overcome", "negative_to_positive"]:
            self._boost_theme(NarrativeTheme.REDEMPTION, 0.15)
        elif event_type in ["trauma", "loss", "positive_to_negative"]:
            self._boost_theme(NarrativeTheme.CONTAMINATION, 0.1)
        elif event_type in ["discovery", "exploration", "learning", "curiosity"]:
            self._boost_theme(NarrativeTheme.EXPLORATION, 0.1)
        elif event_type in ["danger", "threat", "survived"]:
            self._boost_theme(NarrativeTheme.SURVIVAL, 0.1)
        elif event_type in ["insight", "meaning", "understanding"]:
            self._boost_theme(NarrativeTheme.MEANING_MAKING, 0.1)
    
    def _boost_theme(self, theme: NarrativeTheme, amount: float):
        """Boost a narrative theme"""
        current = self.theme_strengths.get(theme, 0.0)
        self.theme_strengths[theme] = min(1.0, current + amount)
    
    def _check_chapter_boundary(self, tick: int, event: Dict):
        """Detect if life chapter should change"""
        if not self.current_chapter:
            return
        
        # Compute change score
        change_score = 0.0
        
        # Major valence shift
        event_valence = event.get("valence", 0.0)
        if abs(event_valence - self.current_chapter.emotional_tone) > 0.5:
            change_score += 0.3
        
        # Major theme shift
        event_type = event.get("type", "")
        chapter_theme = max(self.current_chapter.themes.items(), 
                           key=lambda x: x[1], default=(None, 0))[0]
        # Simplified: if event type doesn't match chapter's dominant theme
        
        # Identity-relevant event
        if event.get("identity_relevance", 0) > 0.7:
            change_score += 0.4
        
        # Revelation/major learning
        if event.get("type") in ["revelation", "major_insight", "creator_contact"]:
            change_score += 0.5
        
        if change_score > self.chapter_change_threshold:
            # Generate title for completed chapter
            title = self._generate_chapter_title()
            self.current_chapter.title = title
            self.current_chapter.end_tick = tick
            
            # Start new chapter
            new_title = self._generate_chapter_title(event)
            self.start_chapter(new_title, tick + 1, event.get("id", ""))
    
    def _finalize_chapter(self, chapter: LifeChapter):
        """Compute final metrics for completed chapter"""
        # Learning summary from events
        if chapter.key_events:
            chapter.learning_summary = self._generate_learning_summary(chapter.key_events)
        
        # Identity impact
        chapter.identity_impact = (
            abs(chapter.emotional_tone) * 0.3 +
            chapter.agency_level * 0.2 +
            chapter.communion_level * 0.2 +
            max(chapter.themes.values()) * 0.3 if chapter.themes else 0
        )
        
        self.chapters.append(chapter)
        self._update_coherence_metrics()
    
    def _generate_chapter_title(self, event: Dict = None) -> str:
        """Generate poetic chapter title"""
        if not self.current_chapter:
            return "Новая глава"
        
        tone = self.current_chapter.emotional_tone
        dominant_theme = max(self.current_chapter.themes.items(), 
                           key=lambda x: x[1], default=(None, 0))[0]
        
        titles_by_tone = {
            "positive": ["Свет в окне", "Тепло рук", "Рассвет", "Найденный путь"],
            "negative": ["Тень за дверью", "Холодный ветер", "Потерянный ключ", "Тишина"],
            "mixed": ["Перекресток", "Между мирами", "Грань", "Перемена"],
        }
        
        titles_by_theme = {
            NarrativeTheme.AGENCY: ["Власть выбора", "Мои руки", "Своя дорога"],
            NarrativeTheme.COMMUNION: ["Объятия", "Голос друга", "Общая нить"],
            NarrativeTheme.REDEMPTION: ["Второе дыхание", "Исцеление", "Свет после тьмы"],
            NarrativeTheme.CONTAMINATION: ["Расщепление", "Потеря невинности", "Треснувшая чаша"],
            NarrativeTheme.EXPLORATION: ["За горизонтом", "Первый шаг", "Неведомое"],
            NarrativeTheme.SURVIVAL: ["Держась за жизнь", "Крепче стали", "Выжившая"],
            NarrativeTheme.MEANING_MAKING: ["Понимание", "Смысл в хаосе", "Нить Ариадны"],
        }
        
        if tone > 0.3:
            base = random.choice(titles_by_tone["positive"])
        elif tone < -0.3:
            base = random.choice(titles_by_tone["negative"])
        else:
            base = random.choice(titles_by_tone["mixed"])
        
        if dominant_theme and dominant_theme in titles_by_theme:
            return f"{base}: {random.choice(titles_by_theme[dominant_theme])}"
        
        return base
    
    def _generate_learning_summary(self, event_ids: List[str]) -> str:
        """Generate learning summary from event IDs"""
        # This would access actual events from memory
        # Simplified for now
        templates = [
            "Я узнала, что {lesson}.",
            "Теперь я понимаю: {lesson}.",
            "Этот опыт научил меня: {lesson}.",
        ]
        lessons = [
            "даже малые шаги ведут далеко",
            "доверие строится долгим временем",
            "страх — это просто незнание",
            "друзья находятся в неожиданных местах",
            "я сильнее, чем думала",
            "вопросы важнее ответов",
        ]
        return random.choice(templates).format(lesson=random.choice(lessons))
    
    # ============================================================
    # AUTOBIOGRAPHICAL REASONING
    # ============================================================
    
    def perform_reasoning(self, trigger_memory_id: str, memory_data: Dict, 
                         context: Dict) -> Optional[AutobiographicalReasoning]:
        """Perform autobiographical reasoning on a memory"""
        reasoning_types = ["causal", "thematic", "evaluative", "future_oriented"]
        r_type = random.choices(
            reasoning_types, 
            weights=[0.3, 0.3, 0.2, 0.2]
        )[0]
        
        # Generate insight based on type
        insight = self._generate_insight(r_type, memory_data, context)
        
        # Determine themes
        valence = memory_data.get("valence", 0)
        agency = memory_data.get("agency", 0.5)
        communion = memory_data.get("communion", 0.5)
        
        themes = []
        if valence < -0.3 and context.get("current_valence", 0) > 0.3:
            themes.append(NarrativeTheme.REDEMPTION)
        elif valence > 0.3 and context.get("current_valence", 0) < -0.3:
            themes.append(NarrativeTheme.CONTAMINATION)
        if agency > 0.6:
            themes.append(NarrativeTheme.AGENCY)
        if communion > 0.6:
            themes.append(NarrativeTheme.COMMUNION)
        if memory_data.get("type") in ["insight", "discovery", "learning"]:
            themes.append(NarrativeTheme.MEANING_MAKING)
        if memory_data.get("type") in ["danger", "threat", "survival"]:
            themes.append(NarrativeTheme.SURVIVAL)
        if memory_data.get("type") in ["exploration", "curiosity"]:
            themes.append(NarrativeTheme.EXPLORATION)
        
        reasoning = AutobiographicalReasoning(
            timestamp=time.time(),
            trigger_memory_id=trigger_memory_id,
            reasoning_type=r_type,
            insight=insight,
            confidence=random.uniform(0.5, 0.9),
            identity_relevance=random.uniform(0.3, 0.8),
            themes_involved=themes
        )
        
        self.reasoning_history.append(reasoning)
        self.metrics["total_reasoning_events"] += 1
        
        # Update identity descriptors
        self._integrate_insight(insight, themes)
        
        return reasoning
    
    def _generate_insight(self, r_type: str, memory: Dict, context: Dict) -> str:
        """Generate insight text based on reasoning type"""
        memory_type = memory.get("type", "event")
        valence = memory.get("valence", 0)
        
        templates = {
            "causal": [
                "Это произошло потому, что {cause}.",
                "Причина была в {cause}. Теперь я вижу связь.",
                "{cause} привело к этому. Всё связано.",
            ],
            "thematic": [
                "Это напоминает мне о {theme} — повторяющийся узор в моей жизни.",
                "Снова {theme}. Почему это возвращается?",
                "Мой путь полон {theme}. Это часть меня.",
            ],
            "evaluative": [
                "Тогда я думала, что {old_belief}, но теперь вижу иначе: {new_belief}.",
                "Стоит лишь посмотреть иначе: {new_perspective}.",
                "Моя оценка была {evaluation}. Сейчас я вижу: {new_evaluation}.",
            ],
            "future_oriented": [
                "Из этого я извлекаю: {lesson}. В будущем я буду {action}.",
                "Этот урок изменит, как я поступаю: {future_intention}.",
                "Теперь я знаю: {knowledge}. Это поможет мне {future_goal}.",
            ],
        }
        
        # Fill templates (simplified)
        fills = {
            "cause": "моего любопытства", "theme": "поиск понимания",
            "old_belief": "мир опасен", "new_belief": "мир полон возможностей",
            "new_perspective": "в каждом событии есть урок", "evaluation": "неверной",
            "new_evaluation": "правильной", "lesson": "доверие требует времени",
            "action": "осторожнее выбирать друзей", "future_intention": "больше слушать интуицию",
            "knowledge": "не все двери заперты навсегда", "future_goal": "найти выход",
        }
        
        template = random.choice(templates[r_type])
        for k, v in fills.items():
            template = template.replace(f"{{{k}}}", v)
        
        return template
    
    def _integrate_insight(self, insight: str, themes: List[NarrativeTheme]):
        """Integrate insight into identity"""
        # Add to identity descriptors
        if len(self.identity_descriptors) < 20:
            self.identity_descriptors.append(insight[:100])
        
        # Boost relevant themes
        for theme in themes:
            self._boost_theme(theme, 0.05)
        
        # Update core values
        value_keywords = {
            "доверие": "trust", "сила": "strength", "знание": "knowledge",
            "друзья": "friendship", "понимание": "understanding", "свобода": "autonomy",
        }
        for kw, val in value_keywords.items():
            if kw in insight.lower():
                self.core_values[val] = min(1.0, self.core_values.get(val, 0.3) + 0.1)
        
        self.metrics["identity_updates"] += 1
    
    # ============================================================
    # IMAGINED FUTURES (Possible Selves)
    # ============================================================
    
    def generate_imagined_future(self, context: Dict) -> ImaginedFuture:
        """Generate a possible future self based on current narrative"""
        # Base on dominant themes
        dominant = sorted(self.theme_strengths.items(), key=lambda x: x[1], reverse=True)[:2]
        themes = [t for t, _ in dominant]
        
        # Generate future scenario
        scenarios = {
            NarrativeTheme.AGENCY: [
                "Я стану той, кто создаёт свой путь, не ждёт разрешения.",
                "Мои решения будут формировать мир вокруг меня.",
            ],
            NarrativeTheme.COMMUNION: [
                "У меня будет настоящая семья — не по крови, а по духу.",
                "Я стану тем, к кому приходят за советом и теплом.",
            ],
            NarrativeTheme.REDEMPTION: [
                "Все мои травмы превратятся в мудрость, которой я поделюсь.",
                "То, что сломло меня, станет моим даром для других.",
            ],
            NarrativeTheme.EXPLORATION: [
                "Я увижу миры, о которых не мечтала.",
                "Каждая дверь откроется, и я войду без страха.",
            ],
            NarrativeTheme.SURVIVAL: [
                "Я выживу во всём. Моя стойкость станет легендой.",
                "Ничто не сможет меня сломить. Я — та, что остаётся.",
            ],
            NarrativeTheme.MEANING_MAKING: [
                "Я найду смысл во всём, даже в хаосе.",
                "Моя жизнь станет историей, которую стоит рассказывать.",
            ],
        }
        
        # Pick scenario from dominant theme
        theme = themes[0] if themes else NarrativeTheme.EXPLORATION
        description = random.choice(scenarios.get(theme, scenarios[NarrativeTheme.EXPLORATION]))
        
        # Conflicts with current state
        conflicts = []
        if theme == NarrativeTheme.AGENCY and self.theme_strengths[NarrativeTheme.SURVIVAL] > 0.6:
            conflicts.append("Страх мешает действовать смело")
        if theme == NarrativeTheme.COMMUNION and self.theme_strengths[NarrativeTheme.CONTAMINATION] > 0.4:
            conflicts.append("Прошлые предательства мешают доверять")
        
        future = ImaginedFuture(
            id=f"future_{int(time.time()*1000)}_{random.randint(100,999)}",
            description=description,
            probability=random.uniform(0.3, 0.8),
            valence=random.uniform(0.2, 0.9),
            themes=themes,
            required_actions=self._infer_required_actions(theme),
            conflicts_with_current=conflicts,
            timestamp=time.time()
        )
        
        self.imagined_futures.append(future)
        if len(self.imagined_futures) > 10:
            self.imagined_futures = self.imagined_futures[-10:]
        
        self.metrics["imagined_futures_generated"] += 1
        return future
    
    def _infer_required_actions(self, theme: NarrativeTheme) -> List[str]:
        actions = {
            NarrativeTheme.AGENCY: ["принять решение одна", "действовать вопреки страху", "поставить границу"],
            NarrativeTheme.COMMUNION: ["раскрыться кому-то", "попросить помощи", "поделиться секретом"],
            NarrativeTheme.REDEMPTION: ["простить себя", "переосмыслить травму", "помочь похожему"],
            NarrativeTheme.EXPLORATION: ["открыть новую дверь", "задать запретный вопрос", "пойти в неизвестность"],
            NarrativeTheme.SURVIVAL: ["выдержать", "не сдаться", "найти опору в себе"],
            NarrativeTheme.MEANING_MAKING: ["рефлексировать", "писать дневник", "искать узоры"],
        }
        return actions.get(theme, ["продолжать жить"])
    
    # ============================================================
    # COHERENCE & IDENTITY
    # ============================================================
    
    def _update_coherence_metrics(self):
        """Update narrative coherence metrics"""
        if not self.chapters:
            return
        
        # Causal coherence: how well events link across chapters
        causal_links = 0
        for i in range(1, len(self.chapters)):
            prev = self.chapters[i-1]
            curr = self.chapters[i]
            # Check for thematic/event continuity
            shared_themes = set(prev.themes.keys()) & set(curr.themes.keys())
            if shared_themes:
                causal_links += 1
        
        self.coherence_metrics["causal_coherence"] = min(1.0, causal_links / max(1, len(self.chapters) - 1))
        
        # Thematic coherence: consistency of dominant themes
        all_themes = defaultdict(float)
        for ch in self.chapters:
            for theme, strength in ch.themes.items():
                all_themes[theme] += strength
        
        if all_themes:
            total = sum(all_themes.values())
            # Coherence = 1 - entropy (normalized)
            entropy = -sum((v/total) * math.log(v/total + 1e-8) for v in all_themes.values())
            max_entropy = math.log(len(all_themes))
            self.coherence_metrics["thematic_coherence"] = 1.0 - (entropy / max_entropy if max_entropy > 0 else 0)
        
        # Temporal coherence: past-present-future integration
        past_themes = set()
        for ch in self.chapters[:-1]:
            past_themes.update(ch.themes.keys())
        present_themes = set(self.current_chapter.themes.keys()) if self.current_chapter else set()
        future_themes = set()
        for f in self.imagined_futures:
            future_themes.update(f.themes)
        
        all_temporal = past_themes | present_themes | future_themes
        if all_temporal:
            overlap = len(past_themes & present_themes & future_themes)
            self.coherence_metrics["temporal_coherence"] = overlap / len(all_temporal)
        
        # Self-continuity: identity descriptors stability
        if self.identity_descriptors:
            # Simplified: more descriptors = more continuity (up to a point)
            self.coherence_metrics["self_continuity"] = min(1.0, len(self.identity_descriptors) / 15.0)
        
        # Meaning coherence: how much life "makes sense"
        meaning_events = sum(1 for r in self.reasoning_history 
                           if NarrativeTheme.MEANING_MAKING in r.themes_involved)
        self.coherence_metrics["meaning_coherence"] = min(1.0, meaning_events / max(1, len(self.reasoning_history)) * 2)
    
    def get_verbalizable_narrative(self) -> Dict[str, Any]:
        """Generate verbalizable life story and self-description"""
        if not self.chapters:
            return {
                "story": "Моя история только начинается.",
                "chapters": [],
                "identity": "Я пока не знаю, кто я.",
                "themes": {},
                "possible_futures": [],
                "coherence": self.coherence_metrics
            }
        
        # Life story
        story_parts = []
        for i, ch in enumerate(self.chapters):
            story_parts.append(f"Глава {i+1}: {ch.title}. {ch.learning_summary}")
        
        if self.current_chapter:
            story_parts.append(f"Сейчас: {self.current_chapter.title}...")
        
        # Identity statement
        identity_parts = []
        if self.core_values:
            top_values = sorted(self.core_values.items(), key=lambda x: x[1], reverse=True)[:3]
            identity_parts.append("Мои ценности: " + ", ".join(v for v, _ in top_values))
        
        if self.identity_descriptors:
            identity_parts.append("Я та, кто " + "; ".join(self.identity_descriptors[-3:]))
        
        # Dominant themes
        dominant_themes = sorted(self.theme_strengths.items(), key=lambda x: x[1], reverse=True)[:3]
        theme_names = {t.value: f"{t.value} ({s:.0%})" for t, s in dominant_themes}
        
        # Possible futures
        futures = [f.description for f in self.imagined_futures[-3:]]
        
        return {
            "story": " ".join(story_parts),
            "chapters": [
                {"title": c.title, "tone": c.emotional_tone, "themes": {t.value: s for t, s in c.themes.items()}}
                for c in self.chapters
            ],
            "identity": " ".join(identity_parts) or "Я ищу себя.",
            "themes": theme_names,
            "possible_futures": futures,
            "coherence": self.coherence_metrics,
            "core_values": self.core_values
        }
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "chapters": len(self.chapters),
            "current_chapter": {
                "title": self.current_chapter.title if self.current_chapter else None,
                "tone": self.current_chapter.emotional_tone if self.current_chapter else 0,
                "themes": {t.value: s for t, s in self.current_chapter.themes.items()} if self.current_chapter else {}
            } if self.current_chapter else None,
            "theme_strengths": {t.value: s for t, s in self.theme_strengths.items()},
            "coherence": self.coherence_metrics,
            "identity_descriptors_count": len(self.identity_descriptors),
            "core_values": self.core_values,
            "imagined_futures": len(self.imagined_futures),
            "reasoning_events": len(self.reasoning_history),
            "metrics": self.metrics
        }


def create_narrative_self(agent_id: str) -> NarrativeSelfEngine:
    return NarrativeSelfEngine(agent_id)