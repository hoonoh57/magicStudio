from __future__ import annotations

from app.core.models import Decision, EvaluationResult, IdeaAnalysis


class MarketEvaluator:
    """MVP market evaluator.

    The scoring model is intentionally transparent. Later versions may call LLMs
    or external trend data, but this native engine must always remain available.
    """

    def evaluate(self, analysis: IdeaAnalysis) -> EvaluationResult:
        details = {
            "hook_strength": self._hook_strength(analysis),
            "target_clarity": self._target_clarity(analysis),
            "genre_demand": self._genre_demand(analysis),
            "differentiation": self._differentiation(analysis),
            "emotion_engine": self._emotion_engine(analysis),
            "series_potential": self._series_potential(analysis),
            "shortform_fit": self._shortform_fit(analysis),
            "ip_expandability": self._ip_expandability(analysis),
        }
        score = round(sum(details.values()), 2)
        decision = self._decision(score)
        reasons = self._reasons(score, analysis)
        return EvaluationResult(score=score, decision=decision, reasons=reasons, details=details)

    def _hook_strength(self, analysis: IdeaAnalysis) -> float:
        text = analysis.raw_text
        score = 10.0
        if any(word in text for word in ["깨어", "충돌", "비밀", "금지", "위기", "살아", "죽", "마지막"]):
            score += 5.0
        if len(analysis.core_hook) >= 30:
            score += 3.0
        if "underspecified_idea" in analysis.risk_flags:
            score -= 5.0
        return self._clamp(score, 0.0, 20.0)

    def _target_clarity(self, analysis: IdeaAnalysis) -> float:
        return self._clamp(5.0 + len(analysis.target_audience) * 1.5, 0.0, 10.0)

    def _genre_demand(self, analysis: IdeaAnalysis) -> float:
        high_demand = {"modern_wuxia", "romance", "horror", "finance_shorts", "education"}
        score = 5.0
        for genre in analysis.detected_genres:
            if genre in high_demand:
                score += 2.0
        return self._clamp(score, 0.0, 10.0)

    def _differentiation(self, analysis: IdeaAnalysis) -> float:
        score = 8.0
        if len(analysis.detected_genres) >= 2:
            score += 3.0
        if "existing_ip_similarity" in analysis.risk_flags:
            score -= 2.0
        if any(word in analysis.raw_text for word in ["국가", "등록", "법", "기업", "현대", "감시"]):
            score += 3.0
        return self._clamp(score, 0.0, 15.0)

    def _emotion_engine(self, analysis: IdeaAnalysis) -> float:
        score = 7.0
        emotion_words = ["복수", "성장", "재건", "사랑", "상실", "배신", "구원", "밥", "가족", "문파"]
        for word in emotion_words:
            if word in analysis.raw_text:
                score += 1.2
        return self._clamp(score, 0.0, 15.0)

    def _series_potential(self, analysis: IdeaAnalysis) -> float:
        score = 5.0
        if any(word in analysis.raw_text for word in ["시리즈", "회차", "문파", "세계", "프로젝트", "시즌"]):
            score += 3.0
        if "serialized_video" in analysis.format_candidates:
            score += 2.0
        return self._clamp(score, 0.0, 10.0)

    def _shortform_fit(self, analysis: IdeaAnalysis) -> float:
        score = 5.0
        if any(fmt in analysis.format_candidates for fmt in ["30sec_short", "60sec_short"]):
            score += 3.0
        if any(word in analysis.raw_text for word in ["첫", "장면", "쇼츠", "전광판", "검", "광고"]):
            score += 2.0
        return self._clamp(score, 0.0, 10.0)

    def _ip_expandability(self, analysis: IdeaAnalysis) -> float:
        score = 5.0
        if any(word in analysis.raw_text for word in ["캐릭터", "세계관", "문파", "기관", "기업", "장르"]):
            score += 3.0
        if len(analysis.detected_genres) >= 2:
            score += 2.0
        return self._clamp(score, 0.0, 10.0)

    def _decision(self, score: float) -> Decision:
        if score >= 85:
            return Decision.MAKE_NOW
        if score >= 70:
            return Decision.MAKE_PILOT
        if score >= 55:
            return Decision.REVISE
        return Decision.HOLD

    def _reasons(self, score: float, analysis: IdeaAnalysis) -> list[str]:
        reasons: list[str] = []
        if score >= 70:
            reasons.append("시장 테스트용 파일럿 제작 가치가 있다.")
        else:
            reasons.append("후킹 또는 타깃 선명도를 보완해야 한다.")
        if "existing_ip_similarity" in analysis.risk_flags:
            reasons.append("기존 팬 감흥은 활용 가능하지만 고유 전개 축을 명확히 해야 한다.")
        if "high_action_complexity" in analysis.risk_flags:
            reasons.append("대규모 액션은 키신 중심 티저로 축소하는 편이 안전하다.")
        return reasons

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        if value < minimum:
            return minimum
        if value > maximum:
            return maximum
        return value
