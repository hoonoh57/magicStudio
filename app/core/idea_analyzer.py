from __future__ import annotations

from typing import List

from app.core.models import IdeaAnalysis, new_id


class IdeaAnalyzer:
    """Rule-based MVP analyzer.

    Later versions can delegate to LLM providers, but the core contract must remain
    deterministic and testable.
    """

    def analyze(self, raw_text: str) -> IdeaAnalysis:
        text = raw_text.strip()
        if not text:
            raise ValueError("raw_text is required")

        lower = text.lower()
        genres = self._detect_genres(text, lower)
        audience = self._detect_audience(genres, lower)
        formats = self._detect_formats(text, lower)
        risks = self._detect_risks(text, lower)
        hook = self._extract_hook(text)

        return IdeaAnalysis(
            idea_id=new_id("idea"),
            raw_text=text,
            detected_genres=genres,
            target_audience=audience,
            format_candidates=formats,
            core_hook=hook,
            risk_flags=risks,
        )

    def _detect_genres(self, text: str, lower: str) -> List[str]:
        pairs = [
            ("modern_wuxia", ["무림", "무협", "강호", "문파", "검", "내공"]),
            ("romance", ["로맨스", "사랑", "연애", "커플"]),
            ("horror", ["공포", "귀신", "괴담", "저주", "악몽"]),
            ("education", ["교육", "강의", "설명", "배우", "학습"]),
            ("finance_shorts", ["주식", "증시", "투자", "경제", "종목"]),
            ("documentary", ["다큐", "실화", "역사", "사건", "인물"]),
            ("fantasy", ["마법", "판타지", "용", "이세계"]),
            ("cooking", ["요리", "레시피", "주방", "셰프"]),
            ("sports", ["스포츠", "축구", "야구", "농구", "격투"]),
        ]
        detected: List[str] = []
        for genre, keywords in pairs:
            for keyword in keywords:
                if keyword in text or keyword in lower:
                    detected.append(genre)
                    break
        if not detected:
            detected.append("general_story")
        return detected

    def _detect_audience(self, genres: List[str], lower: str) -> List[str]:
        audience: List[str] = []
        if "modern_wuxia" in genres:
            audience.extend(["webnovel_fans", "wuxia_fans", "shortform_viewers"])
        if "romance" in genres:
            audience.extend(["romance_readers", "shortform_viewers"])
        if "education" in genres:
            audience.extend(["learners", "youtube_viewers"])
        if "finance_shorts" in genres:
            audience.extend(["retail_investors", "finance_youtube_viewers"])
        if not audience:
            audience.extend(["general_shortform_viewers"])
        if "원작" in lower or "팬" in lower:
            audience.append("existing_fandom")
        return self._unique(audience)

    def _detect_formats(self, text: str, lower: str) -> List[str]:
        formats: List[str] = ["60sec_short", "3min_episode"]
        if "쇼츠" in text or "short" in lower:
            formats.insert(0, "30sec_short")
        if "시리즈" in text or "회차" in text:
            formats.append("serialized_video")
        if "교육" in text or "강의" in text:
            formats.append("explainer_video")
        return self._unique(formats)

    def _detect_risks(self, text: str, lower: str) -> List[str]:
        risks: List[str] = []
        if "원작" in text or "if" in lower or "팬" in text:
            risks.append("existing_ip_similarity")
        if any(word in text for word in ["대규모", "전쟁", "군중", "수천"]):
            risks.append("high_action_complexity")
        if len(text) < 20:
            risks.append("underspecified_idea")
        return risks

    def _extract_hook(self, text: str) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= 90:
            return normalized
        return normalized[:87] + "..."

    def _unique(self, values: List[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for value in values:
            if value not in seen:
                result.append(value)
                seen.add(value)
        return result
