"""SkillSearcher — 关键词搜索（Phase 2.0）

设计为可替换的搜索后端：
    KeywordSearcher   — 零依赖，TF-IDF 风格评分，现在用
    （未来）VectorSearcher — pgvector 语义检索，按需升级，接口相同
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from src.models import SkillMeta


@dataclass
class SearchResult:
    skill: SkillMeta
    score: float          # 0.0 ~ 1.0
    matched_fields: list[str]


class KeywordSearcher:
    """
    轻量级关键词搜索。

    评分逻辑：
      - 命中 id/name     +0.5
      - 命中 tags        +0.35 per tag
      - 命中 summary     +0.15（按词频加权）

    不依赖任何外部库，适合 Phase 2.0。
    """

    def search(
        self,
        query: str,
        skills: list[SkillMeta],
        top_k: int = 5,
    ) -> list[SearchResult]:
        if not query.strip():
            return [SearchResult(s, 0.0, []) for s in skills[:top_k]]

        tokens = self._tokenize(query)
        results: list[SearchResult] = []

        for skill in skills:
            score, matched = self._score(tokens, skill)
            if score > 0:
                results.append(SearchResult(skill=skill, score=score, matched_fields=matched))

        # 按分数降序，同分按 priority 降序
        results.sort(key=lambda r: (-r.score, -r.skill.priority))
        return results[:top_k]

    # ── 内部 ──────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """中英文混合分词：按空格/标点/驼峰切分，转小写"""
        # 驼峰拆分：gitWorktrees → git worktrees
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
        # 连字符/下划线视为空格
        text = text.replace("-", " ").replace("_", " ")
        tokens = re.findall(r"[a-zA-Z一-鿿]+", text.lower())
        # 中文按字符粒度切分（每个汉字独立）
        chars: set[str] = set()
        for t in tokens:
            if re.search(r"[一-鿿]", t):
                chars.update(t)  # 每个汉字
            else:
                chars.add(t)
        return chars

    def _score(self, tokens: set[str], skill: SkillMeta) -> tuple[float, list[str]]:
        score = 0.0
        matched: list[str] = []
        covered: set[str] = set()  # unique query tokens matched across all fields

        id_tokens = self._tokenize(skill.id + " " + skill.name)
        hit_name = self._match(tokens, id_tokens)
        if hit_name:
            score += 0.5 * (len(hit_name) / max(len(tokens), 1))
            matched.append("name")
            covered |= hit_name

        tag_tokens: set[str] = set()
        for tag in skill.tags:
            tag_tokens.update(self._tokenize(tag))
        hit_tags = self._match(tokens, tag_tokens)
        if hit_tags:
            score += 0.35 * (len(hit_tags) / max(len(tokens), 1))
            matched.append("tags")
            covered |= hit_tags

        if skill.summary:
            sum_tokens = self._tokenize(skill.summary)
            hit_sum = self._match(tokens, sum_tokens)
            if hit_sum:
                idf = 1 + math.log(1 + len(hit_sum))
                score += 0.15 * (idf / max(math.log(1 + len(tokens)), 1))
                matched.append("summary")
                covered |= hit_sum

        # coverage bonus: reward skills that match more unique query terms
        # prefix matches contribute 0.6 weight vs exact matches at 1.0
        if score > 0 and len(tokens) > 1:
            id_tokens = self._tokenize(skill.id + " " + skill.name)
            tag_tokens: set[str] = set()
            for tag in skill.tags:
                tag_tokens.update(self._tokenize(tag))
            sum_tokens = self._tokenize(skill.summary) if skill.summary else set()
            all_field_tokens = id_tokens | tag_tokens | sum_tokens
            weighted_covered = self._match_weighted(tokens, all_field_tokens)
            coverage = min(weighted_covered / len(tokens), 1.0)
            score *= (0.7 + 0.3 * coverage)

        return min(score, 1.0), matched

    @staticmethod
    def _match(query_tokens: set[str], field_tokens: set[str]) -> set[str]:
        """Exact match + prefix match (query token is prefix of field token, min 3 chars).

        Returns a set of matched query tokens. Prefix matches are included with a
        fractional contribution: the set contains them, but callers count them at
        full weight. To reduce their impact, prefix tokens are represented as-is
        but counted towards coverage bonus at 0.6 weight via _match_weighted().
        """
        exact = query_tokens & field_tokens
        prefix: set[str] = set()
        for qt in query_tokens - exact:
            if len(qt) >= 3:
                for ft in field_tokens:
                    if len(ft) > len(qt) and ft.startswith(qt):
                        prefix.add(qt)
                        break
        return exact | prefix

    @staticmethod
    def _match_weighted(query_tokens: set[str], field_tokens: set[str]) -> float:
        """返回加权匹配数：exact=1.0，prefix=0.6。用于覆盖率计算。"""
        exact = query_tokens & field_tokens
        weight = float(len(exact))
        for qt in query_tokens - exact:
            if len(qt) >= 3:
                for ft in field_tokens:
                    if len(ft) > len(qt) and ft.startswith(qt):
                        weight += 0.6
                        break
        return weight
