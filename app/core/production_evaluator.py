from __future__ import annotations

from app.core.models import Decision, EvaluationResult, IdeaAnalysis


class ProductionEvaluator:
    """Evaluate whether an idea can be produced by a one-person automated studio."""

    def evaluate(self, analysis: IdeaAnalysis) -> EvaluationResult:
        details = {
            "character_count_fit": self._character_count_fit(analysis),
            "location_count_fit": self._location_count_fit(analysis),
            "action_complexity_fit": self._action_complexity_fit(analysis),
            "consistency_fit": self._consistency_fit(analysis),
            "tts_fit": self._tts_fit(analysis),
            "sound_fit": self._sound_fit(analysis),
            "editing_fit": self._editing_fit(analysis),
            "automation_fit": self._automation_fit(analysis),
        }
        score = round(sum(details.values()), 2)
        decision = self._decision(score)
        reasons = self._reasons(score, analysis)
        return EvaluationResult(score=score, decision=decision, reasons=reasons, details=details)

    def _character_count_fit(self, analysis: IdeaAnalysis) -> float:
        text = analysis.raw_text
        score = 8.0
        if any(word in text for word in ["대규모", "군중", "수천", "전쟁"]):
            score -= 3.0
        if any(word in text for word in ["주인공", "조력자", "두 사람", "1인"]):
            score += 2.0
        return self._clamp(score, 0.0, 10.0)

    def _location_count_fit(self, analysis: IdeaAnalysis) -> float:
        text = analysis.raw_text
        score = 7.0
        if any(word in text for word in ["서울역", "수련실", "조사실", "방", "주방"]):
            score += 2.0
        if any(word in text for word in ["전 세계", "전장", "우주", "여러 도시"]):
            score -= 2.0
        return self._clamp(score, 0.0, 10.0)

    def _action_complexity_fit(self, analysis: IdeaAnalysis) -> float:
        score = 12.0
        if "high_action_complexity" in analysis.risk_flags:
            score -= 7.0
        if any(word in analysis.raw_text for word in ["수련", "대화", "조사", "티저", "요리", "설명"]):
            score += 2.0
        return self._clamp(score, 0.0, 15.0)

    def _consistency_fit(self, analysis: IdeaAnalysis) -> float:
        score = 10.0
        if any(word in analysis.raw_text for word in ["캐릭터", "고정", "일관", "시리즈"]):
            score += 2.0
        if len(analysis.detected_genres) >= 4:
            score -= 2.0
        return self._clamp(score, 0.0, 15.0)

    def _tts_fit(self, analysis: IdeaAnalysis) -> float:
        score = 7.0
        if any(word in analysis.raw_text for word in ["대사", "내레이션", "설명", "독백"]):
            score += 2.0
        if any(word in analysis.raw_text for word in ["합창", "군중", "노래"]):
            score -= 2.0
        return self._clamp(score, 0.0, 10.0)

    def _sound_fit(self, analysis: IdeaAnalysis) -> float:
        score = 7.0
        if any(word in analysis.raw_text for word in ["음악", "효과음", "검", "도시", "공포"]):
            score += 2.0
        return self._clamp(score, 0.0, 10.0)

    def _editing_fit(self, analysis: IdeaAnalysis) -> float:
        score = 7.0
        if any(fmt in analysis.format_candidates for fmt in ["30sec_short", "60sec_short", "3min_episode"]):
            score += 2.0
        return self._clamp(score, 0.0, 10.0)

    def _automation_fit(self, analysis: IdeaAnalysis) -> float:
        score = 12.0
        if any(word in analysis.raw_text for word in ["시나리오", "회차", "키신", "장면", "프로젝트"]):
            score += 4.0
        if "high_action_complexity" in analysis.risk_flags:
            score -= 4.0
        if "underspecified_idea" in analysis.risk_flags:
            score -= 3.0
        return self._clamp(score, 0.0, 20.0)

    def _decision(self, score: float) -> Decision:
        if score >= 80:
            return Decision.MAKE_NOW
        if score >= 65:
            return Decision.MAKE_PILOT
        if score >= 50:
            return Decision.REVISE
        return Decision.HOLD

    def _reasons(self, score: float, analysis: IdeaAnalysis) -> list[str]:
        reasons: list[str] = []
        if score >= 65:
            reasons.append("1인 자동화 제작 파이프라인에 올릴 수 있다.")
        else:
            reasons.append("장면 수, 액션 규모, 제작 복잡도를 줄여야 한다.")
        if "high_action_complexity" in analysis.risk_flags:
            reasons.append("대규모 액션은 키프레임 티저 또는 제한된 공간 액션으로 축소한다.")
        return reasons

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        if value < minimum:
            return minimum
        if value > maximum:
            return maximum
        return value
