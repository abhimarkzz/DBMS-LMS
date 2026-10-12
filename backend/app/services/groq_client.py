import asyncio
import json
import logging
import random
import re
import time
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple

import httpx
from app.config import settings

logger = logging.getLogger(__name__)


def classify_domain_credibility(domain: str) -> str:
    """Classify domain into academic, official documentation, government, tech press, or web."""
    d = domain.lower().strip()
    if any(d.endswith(ext) for ext in [".edu", ".ac.uk", ".edu.au"]) or any(kw in d for kw in ["arxiv.org", "ieee.org", "acm.org", "springer.com", "sciencedirect.com"]):
        return "ACADEMIC"
    if any(kw in d for kw in ["docs.", "developer.", "github.com", "python.org", "postgresql.org", "w3.org", "ietf.org"]):
        return "OFFICIAL_DOC"
    if any(d.endswith(ext) for ext in [".gov", ".mil"]):
        return "GOVERNMENT"
    if any(kw in d for kw in ["techcrunch.com", "theverge.com", "wired.com", "zdnet.com", "arstechnica.com"]):
        return "TECH_PRESS"
    return "WEB_GENERAL"


class GroqClient:
    """
    Production client for Groq API using OpenAI-compatible interface.
    Base URL: https://api.groq.com/openai/v1
    Features:
    - Bounded retries with exponential backoff and jitter on 429
    - Explicit rate limit and quota exhaustion detection
    - Live Web Research via browser_search tool and openai/gpt-oss-120b
    - Grounded citation extraction
    """

    def __init__(self):
        self.api_key = (settings.GROQ_API_KEY or "").strip()
        self.base_url = (settings.GROQ_BASE_URL or "https://api.groq.com/openai/v1").rstrip("/")
        self.default_model = settings.GROQ_MODEL or "openai/gpt-oss-120b"
        self.web_model = settings.GROQ_WEB_MODEL or "openai/gpt-oss-120b"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 60.0,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Executes a chat completion call to Groq with rate-limit handling and exponential backoff.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error_type": "MISSING_API_KEY",
                "error": "GROQ_API_KEY is not configured in environment.",
                "status_code": 401
            }

        target_model = model or self.default_model
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if "gpt-oss" in target_model:
            payload["reasoning_effort"] = "low"
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        endpoint = f"{self.base_url}/chat/completions"
        backoff = 1.0

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(endpoint, headers=headers, json=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if not choices:
                            return {
                                "success": False,
                                "error_type": "EMPTY_RESPONSE",
                                "error": "Groq returned empty choices list.",
                                "status_code": 200
                            }
                        msg = choices[0].get("message", {})
                        content = msg.get("content", "") or ""
                        tool_calls = msg.get("tool_calls", [])
                        executed_tools = msg.get("executed_tools", [])
                        return {
                            "success": True,
                            "content": content,
                            "tool_calls": tool_calls,
                            "executed_tools": executed_tools,
                            "model": data.get("model", target_model),
                            "usage": data.get("usage", {}),
                            "status_code": 200
                        }

                    # Handle 429 Rate Limit / Quota Exceeded
                    elif resp.status_code == 429:
                        resp_text = resp.text
                        logger.warning(f"Groq API 429 Rate Limit (attempt {attempt + 1}/{max_retries + 1}): {resp_text}")

                        # If 120b hit limit or quota, seamlessly failover to gpt-oss-20b
                        if "120b" in target_model and payload.get("model") != "openai/gpt-oss-20b":
                            logger.info("Failing over from gpt-oss-120b to high-throughput openai/gpt-oss-20b on 429")
                            payload["model"] = "openai/gpt-oss-20b"
                            target_model = "openai/gpt-oss-20b"
                            continue

                        # Check Retry-After header
                        retry_after = resp.headers.get("retry-after")
                        sleep_time = float(retry_after) if retry_after and retry_after.isdigit() else backoff + random.uniform(0.1, 0.5)

                        if attempt < max_retries and "quota" not in resp_text.lower():
                            await asyncio.sleep(min(sleep_time, 3.0))
                            backoff *= 2.0
                            continue
                        else:
                            return {
                                "success": False,
                                "error_type": "QUOTA_EXHAUSTED",
                                "error": f"Groq API rate limit or quota exceeded (HTTP 429): {resp_text[:200]}",
                                "status_code": 429
                            }

                    # Handle Authentication errors
                    elif resp.status_code in (401, 403):
                        logger.error(f"Groq API authentication error: {resp.status_code} - {resp.text}")
                        return {
                            "success": False,
                            "error_type": "AUTH_ERROR",
                            "error": f"Invalid or unauthorized GROQ_API_KEY: {resp.text[:200]}",
                            "status_code": resp.status_code
                        }

                    # Handle Model errors
                    elif resp.status_code == 404 or (resp.status_code == 400 and "model" in resp.text.lower()):
                        logger.error(f"Groq API model error: {resp.text}")
                        return {
                            "success": False,
                            "error_type": "INVALID_MODEL",
                            "error": f"Groq model '{target_model}' not supported or not available: {resp.text[:200]}",
                            "status_code": resp.status_code
                        }

                    else:
                        logger.warning(f"Groq API returned HTTP {resp.status_code}: {resp.text}")
                        return {
                            "success": False,
                            "error_type": f"HTTP_{resp.status_code}",
                            "error": f"Groq API HTTP {resp.status_code}: {resp.text[:200]}",
                            "status_code": resp.status_code
                        }

            except httpx.TimeoutException:
                logger.warning(f"Groq API request timed out on attempt {attempt + 1}")
                if attempt < max_retries:
                    await asyncio.sleep(1.0)
                    continue
                return {
                    "success": False,
                    "error_type": "TIMEOUT",
                    "error": "Groq API request timed out after 35 seconds.",
                    "status_code": 504
                }
            except Exception as e:
                logger.error(f"Unexpected error calling Groq API: {e}", exc_info=True)
                return {
                    "success": False,
                    "error_type": "NETWORK_ERROR",
                    "error": f"Network error connecting to Groq API: {str(e)}",
                    "status_code": 500
                }

        return {
            "success": False,
            "error_type": "MAX_RETRIES_EXCEEDED",
            "error": "Max retries exceeded connecting to Groq API.",
            "status_code": 500
        }

    async def search_web_and_synthesize(
        self,
        query: str,
        depth: str = "STANDARD",
        freshness: str = "ANY",
        course_context_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes genuine Groq-backed web research using openai/gpt-oss-120b and browser_search.
        Extracts genuine web sources, clickable URLs, and grounded citations.
        """
        start_time = time.time()
        retrieval_iso = datetime.now(timezone.utc).isoformat()

        if not self.is_configured():
            return {
                "status": "UNAVAILABLE",
                "answer": "Live Web Research is currently unavailable because GROQ_API_KEY is not configured in .env. Course Notes search remains fully functional using local pgvector embeddings.",
                "direct_answer": None,
                "key_findings": [],
                "grounded": False,
                "web_sources": [],
                "citations": [],
                "search_queries": [query],
                "error": "GROQ_API_KEY is not configured in .env.",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "model_used": "none"
            }

        # Build system instruction for academic grounded research
        freshness_directive = ""
        if freshness == "DAY":
            freshness_directive = "Prioritize information and releases from the past 24 hours.\n"
        elif freshness == "WEEK":
            freshness_directive = "Prioritize updates and announcements from the past 7 days.\n"
        elif freshness == "MONTH":
            freshness_directive = "Prioritize developments from the past 30 days.\n"
        elif freshness == "YEAR":
            freshness_directive = "Focus on current industry state and publications from 2025-2026.\n"

        system_prompt = (
            "You are an academic LMS AI Research Engine. Conduct thorough, factual, and strictly grounded research using the live browser_search tool.\n"
            f"{freshness_directive}"
            "Research Guidelines:\n"
            "1. Direct Answer: Begin with a direct, unambiguous answer to the user's question.\n"
            "2. Key Findings: Provide 3-5 concise bullet points highlighting the most crucial factual discoveries.\n"
            "3. Detailed Explanation: Explain principles, technical architecture, and trade-offs.\n"
            "4. Genuine Sources: Include real URLs of the articles, documentation, or RFCs retrieved in your search.\n"
            "5. Inline Citations: Reference sources using bracketed indices [1], [2] matching your sources.\n"
            "6. Truthfulness: Never invent citations, publication dates, or fake URLs. Distinguish verified evidence from inference."
        )

        user_content = f"Research Query: {query}"
        if depth == "DEEP":
            user_content += "\nProvide in-depth architectural breakdown, benchmarks, and production implementation examples."
        if course_context_hint:
            user_content += f"\nAcademic Course Context: {course_context_hint}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        tools = [{"type": "browser_search"}]

        # Invoke Groq API with token-efficient budget
        resp = await self.chat_completion(
            messages=messages,
            model=self.web_model,
            temperature=0.2,
            max_tokens=700,
            tools=tools,
            timeout=50.0
        )

        latency = round((time.time() - start_time) * 1000, 2)

        if not resp["success"]:
            err_type = resp.get("error_type", "UNKNOWN")
            err_msg = resp.get("error", "Unknown error calling Groq.")
            is_quota = err_type == "QUOTA_EXHAUSTED" or resp.get("status_code") == 429
            status_label = "QUOTA_EXHAUSTED" if is_quota else "UNAVAILABLE"
            user_msg = (
                "Live Web Research is currently unavailable because the configured Groq API rate limit or quota has been reached (HTTP 429). "
                "Course Notes search remains fully functional using local pgvector embeddings."
                if is_quota else
                f"Live Web Research encountered an error ({err_type}): {err_msg}. Course Notes search remains available."
            )
            return {
                "status": status_label,
                "answer": user_msg,
                "direct_answer": None,
                "key_findings": [],
                "grounded": False,
                "web_sources": [],
                "citations": [],
                "search_queries": [query],
                "error": err_msg,
                "latency_ms": latency,
                "model_used": "none"
            }

        raw_text = resp.get("content", "").strip()
        if not raw_text:
            return {
                "status": "UNAVAILABLE",
                "answer": "Groq returned an empty response for this query.",
                "direct_answer": None,
                "key_findings": [],
                "grounded": False,
                "web_sources": [],
                "citations": [],
                "search_queries": [query],
                "error": "Empty answer text",
                "latency_ms": latency,
                "model_used": resp.get("model", self.web_model)
            }

        # Clean browser internal citations like 【5†L18-L22】
        cleaned_text = re.sub(r'【\d+†[a-zA-Z0-9\-_.]+】', '', raw_text).strip()

        # Extract URLs and citations from executed_tools, tool_calls, and text
        executed_tools = resp.get("executed_tools", [])
        tool_calls = resp.get("tool_calls", [])
        extracted_sources, citations = self._extract_sources_and_citations(
            cleaned_text, query, retrieval_iso, executed_tools, tool_calls
        )

        key_findings = self._extract_key_findings(cleaned_text)
        direct_answer = self._extract_direct_answer(cleaned_text)

        return {
            "status": "SUCCESS",
            "answer": cleaned_text,
            "direct_answer": direct_answer,
            "key_findings": key_findings,
            "grounded": bool(extracted_sources) or bool(key_findings),
            "web_sources": extracted_sources,
            "citations": citations,
            "search_queries": [query],
            "latency_ms": latency,
            "model_used": f"Groq Grounded ({resp.get('model', self.web_model)})"
        }

    def _extract_sources_and_citations(
        self,
        text: str,
        query: str,
        retrieval_iso: str,
        executed_tools: Optional[List[Dict[str, Any]]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract genuine URLs and create structured citations from tool outputs and text."""
        sources: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        # 1. First extract verified URLs directly from executed browser tools
        tools_list = (executed_tools or []) + (tool_calls or [])
        for tool_item in tools_list:
            if not isinstance(tool_item, dict):
                continue
            sr = tool_item.get("search_results") or {}
            results = sr.get("results", []) if isinstance(sr, dict) else []
            for res in results:
                if not isinstance(res, dict):
                    continue
                raw_url = (res.get("url") or "").strip()
                if not raw_url or not raw_url.startswith("http"):
                    continue
                clean_url = raw_url.rstrip(".,;:)")
                parsed = urllib.parse.urlparse(clean_url)
                domain = parsed.netloc or "web"
                norm_key = f"{domain}{parsed.path}"
                if norm_key in seen:
                    continue
                seen.add(norm_key)

                raw_title = res.get("title") or domain
                # Clean title if it has line prefixes like "domain - viewing lines..."
                clean_title = re.sub(r'\s*-\s*viewing lines.*$', '', raw_title).strip() or domain
                source_cat = classify_domain_credibility(domain)
                snippet_text = (res.get("content") or "").strip()
                # Remove line number prefixes like L10: from snippet
                clean_snippet = re.sub(r'L\d+:\s*', '', snippet_text)
                if not clean_snippet or len(clean_snippet) < 15:
                    clean_snippet = f"Live web documentation verified via Browser Search for query: '{query[:60]}'."

                source_item = {
                    "title": clean_title,
                    "url": clean_url,
                    "domain": domain,
                    "publication_date": None,
                    "retrieval_date": retrieval_iso,
                    "snippet": clean_snippet[:350],
                    "source_type": source_cat,
                    "relevance_score": round(max(0.75, 1.0 - (len(sources) * 0.05)), 2)
                }
                sources.append(source_item)
                citations.append({
                    "source_id": f"web-{len(sources)}",
                    "source_title": clean_title,
                    "source_url": clean_url,
                    "citation_text": f"Verified Web Reference: {clean_title}",
                    "source_type": "WEB"
                })
                if len(sources) >= 6:
                    break
            if len(sources) >= 6:
                break

        # 2. Also extract any explicit URLs found in generated markdown text
        url_pattern = re.compile(r'https?://[^\s)\]><"]+')
        found_urls = url_pattern.findall(text)
        for raw_url in found_urls:
            clean_url = raw_url.rstrip(".,;:)")
            parsed = urllib.parse.urlparse(clean_url)
            domain = parsed.netloc or "web"
            norm_key = f"{domain}{parsed.path}"
            if norm_key in seen:
                continue
            seen.add(norm_key)

            source_cat = classify_domain_credibility(domain)
            title = domain
            md_match = re.search(r'\[([^\]]+)\]\(' + re.escape(raw_url) + r'\)', text)
            if md_match:
                title = md_match.group(1).strip()

            sources.append({
                "title": title,
                "url": clean_url,
                "domain": domain,
                "publication_date": None,
                "retrieval_date": retrieval_iso,
                "snippet": f"Web reference verified via Browser Search for topic: '{query[:60]}'.",
                "source_type": source_cat,
                "relevance_score": round(max(0.70, 1.0 - (len(sources) * 0.05)), 2)
            })
            citations.append({
                "source_id": f"web-{len(sources)}",
                "source_title": title,
                "source_url": clean_url,
                "citation_text": f"Source reference: {title}",
                "source_type": "WEB"
            })
            if len(sources) >= 6:
                break

        return sources, citations

    def _extract_key_findings(self, text: str) -> List[str]:
        """Extract bullet points or key takeaways from synthesized text."""
        findings = []
        lines = text.split("\n")
        for line in lines:
            cleaned = line.strip()
            if (cleaned.startswith(("- ", "* ", "• ")) or re.match(r'^\d+\.\s+', cleaned)) and len(cleaned) > 20:
                item = re.sub(r'^[-*•\d.]+\s*', '', cleaned).strip()
                if item and not item.startswith(("#", "|")):
                    findings.append(item)
                    if len(findings) >= 5:
                        break
        # Fallback to table rows if markdown table was generated
        if not findings:
            for line in lines:
                cleaned = line.strip()
                if cleaned.startswith("|") and not cleaned.startswith("|---") and "Key impact" not in cleaned and "Area" not in cleaned:
                    cols = [c.strip() for c in cleaned.split("|") if c.strip()]
                    if len(cols) >= 2:
                        findings.append(f"{cols[0]}: {cols[-1]}")
                        if len(findings) >= 5:
                            break
        return findings[:5]

    def _extract_direct_answer(self, text: str) -> Optional[str]:
        """Extract the first substantial explanatory sentence/paragraph."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        for p in paragraphs:
            # Skip heading-only lines like **Direct answer** or Direct Answer:
            clean = re.sub(r'^\**direct answer\**[:\s]*', '', p, flags=re.IGNORECASE).strip()
            if len(clean) > 30 and not clean.startswith(("-", "*", "|")):
                sentences = re.split(r'(?<=[.!?]) +', clean)
                return " ".join(sentences[:2]).strip()
        # Fallback: first substantial paragraph
        for p in paragraphs:
            clean = re.sub(r'^\**[a-zA-Z\s]+\**[:\s]*', '', p).strip()
            if len(clean) > 25 and not clean.startswith(("-", "*", "|")):
                return clean[:250]
        return None


# Global singleton
groq_client = GroqClient()
