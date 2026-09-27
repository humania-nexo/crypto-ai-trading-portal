"""
News & Sentiment Analysis Module for Crypto Markets.
Integrates:
- Alternative.me Fear & Greed Index
- CryptoPanic API & RSS
- CoinTelegraph & CoinDesk RSS Feeds
- Sentiment Scoring Engine (Bullish / Bearish / Neutral)
"""

import logging
import requests
import feedparser
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SentimentAgent:
    def __init__(self, cryptopanic_api_key: Optional[str] = None):
        self.cryptopanic_api_key = cryptopanic_api_key
        self.fear_greed_url = "https://api.alternative.me/fng/?limit=2"
        self.rss_sources = {
            "CoinTelegraph": "https://cointelegraph.com/rss",
            "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "CryptoPanic_Public": "https://cryptopanic.com/news/rss/"
        }
        
        # Palabras clave para análisis de sentimiento ponderado
        self.bullish_keywords = [
            "surge", "soar", "rally", "bullish", "ath", "all-time high", "breakout", 
            "adoption", "approved", "approval", "etf", "inflow", "gain", "climb", 
            "bounce", "accumulation", "partnership", "upgrade", "milestone", "pump"
        ]
        self.bearish_keywords = [
            "crash", "plunge", "dump", "bearish", "hack", "exploit", "sec lawsuit", 
            "ban", "scam", "fraud", "outflow", "liquidation", "drop", "collapse", 
            "investigation", "fud", "default", "warning", "bankrupt", "freeze"
        ]

    def get_fear_and_greed_index(self) -> Dict[str, Any]:
        """Obtiene el índice Fear & Greed actual y su valor del día anterior."""
        try:
            resp = requests.get(self.fear_greed_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("data", [{}])[0]
                yesterday = data.get("data", [{}, {}])[1] if len(data.get("data", [])) > 1 else {}
                
                score = int(current.get("value", 50))
                classification = current.get("value_classification", "Neutral")
                
                return {
                    "score": score,
                    "sentiment": classification,
                    "previous_score": int(yesterday.get("value", score)),
                    "timestamp": current.get("timestamp"),
                    "status": "success"
                }
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed: {e}")
            
        return {
            "score": 50,
            "sentiment": "Neutral",
            "previous_score": 50,
            "status": "error"
        }

    def fetch_rss_news(self, limit_per_source: int = 5) -> List[Dict[str, Any]]:
        """Descarga los últimos titulares de CoinTelegraph, CoinDesk y CryptoPanic."""
        all_news = []
        for source_name, url in self.rss_sources.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:limit_per_source]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    link = entry.get("link", "")
                    published = entry.get("published", str(datetime.utcnow()))
                    
                    sentiment = self._analyze_headline_sentiment(title + " " + summary)
                    
                    all_news.append({
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "published": published,
                        "sentiment": sentiment["label"],
                        "score": sentiment["score"],
                        "relevance_keywords": sentiment["matches"]
                    })
            except Exception as e:
                logger.warning(f"Error fetching RSS from {source_name}: {e}")
                
        return all_news

    def fetch_cryptopanic_api(self, currencies: Optional[str] = "BTC,ETH,SOL") -> List[Dict[str, Any]]:
        """Si se dispone de API Key de CryptoPanic, obtiene noticias con votos de la comunidad."""
        if not self.cryptopanic_api_key:
            return []
            
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token={self.cryptopanic_api_key}&currencies={currencies}&filter=important"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                formatted = []
                for item in results:
                    votes = item.get("votes", {})
                    bullish_votes = votes.get("bullish", 0)
                    bearish_votes = votes.get("bearish", 0)
                    
                    formatted.append({
                        "title": item.get("title"),
                        "domain": item.get("domain"),
                        "created_at": item.get("created_at"),
                        "bullish_votes": bullish_votes,
                        "bearish_votes": bearish_votes,
                        "url": item.get("url")
                    })
                return formatted
        except Exception as e:
            logger.error(f"Error fetching CryptoPanic API: {e}")
        return []

    def _analyze_headline_sentiment(self, text: str) -> Dict[str, Any]:
        """Calcula una puntuación de sentimiento (-1.0 a +1.0) para un texto."""
        text_lower = text.lower()
        bullish_matches = [w for w in self.bullish_keywords if w in text_lower]
        bearish_matches = [w for w in self.bearish_keywords if w in text_lower]
        
        score = len(bullish_matches) - len(bearish_matches)
        
        if score > 0:
            label = "BULLISH"
            normalized_score = min(1.0, score * 0.3)
        elif score < 0:
            label = "BEARISH"
            normalized_score = max(-1.0, score * 0.3)
        else:
            label = "NEUTRAL"
            normalized_score = 0.0
            
        return {
            "label": label,
            "score": normalized_score,
            "matches": bullish_matches + bearish_matches
        }

    def get_market_sentiment_summary(self) -> Dict[str, Any]:
        """Sintetiza todas las fuentes de noticias y el Fear & Greed en una métrica única consolidada."""
        fng = self.get_fear_and_greed_index()
        news = self.fetch_rss_news(limit_per_source=6)
        
        # Ponderación de sentimiento de noticias
        news_scores = [n["score"] for n in news]
        avg_news_score = sum(news_scores) / len(news_scores) if news_scores else 0.0
        
        # Conversión del Fear & Greed (0 a 100) a escala normalizada (-1.0 a +1.0)
        # 50 -> 0.0, 0 -> -1.0 (Extremo Miedo), 100 -> +1.0 (Extrema Codicia)
        fng_normalized = (fng["score"] - 50) / 50.0
        
        # Sentimiento Combinado: 50% Fear&Greed + 50% Noticias
        overall_score = (fng_normalized * 0.5) + (avg_news_score * 0.5)
        
        if overall_score >= 0.25:
            overall_sentiment = "BULLISH"
        elif overall_score <= -0.25:
            overall_sentiment = "BEARISH"
        else:
            overall_sentiment = "NEUTRAL"
            
        return {
            "overall_sentiment": overall_sentiment,
            "overall_score": round(overall_score, 2), # -1.0 (Muy Bajista) a +1.0 (Muy Alcista)
            "fear_and_greed": fng,
            "news_sample_count": len(news),
            "recent_headlines": news[:6],
            "timestamp": datetime.utcnow().isoformat()
        }
