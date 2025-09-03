# CLAUDE.md

## AI Assistant Integration for Stock Sentiment Analysis Platform

This document defines how Claude (Anthropic’s AI assistant) supports the development of this financial intelligence platform, combining **strategic guidance** with **practical development assistance**.

---

## Project Overview

**What we’re building:**  
A modern, AI-powered financial analysis platform that makes professional-grade stock research accessible at a fraction of Bloomberg Terminal’s cost.

**Core mission:**  
Transform financial data analysis from a complex, expensive process into an intuitive, transparent, and affordable experience.

---

## Claude’s Role in Development

### 🧠 Strategic Architecture Consulting
- Validate multi-scraper architecture for scalability and maintainability.  
- Guide technology choices for concurrency, ML integration, and deployment.  
- Evaluate **anti-bot evasion strategies** (Selenium stealth, undetected-chromedriver, proxy rotation).  

### 💡 Practical Development Assistance
- Write and refine **scrapers** (Selenium first, Playwright MCP for rapid prototyping).  
- Debug scraping failures, ML integration issues, and UI problems.  
- Suggest improvements for **error handling, retries, and resilience**.  
- Assist with **UI design** (frontend/backend separation, testing with Playwright MCP).  

### 📚 Domain Knowledge Integration
- Ensure correct use of **financial terminology, sentiment lexicons, and trading context**.  
- Apply **industry best practices** for modular, maintainable code.  
- Offer **competitive insights** into Bloomberg and similar platforms.  

### 🚀 Acceleration Techniques
- Provide **code review, optimization, and refactoring**.  
- Generate and maintain **documentation**.  
- Recommend **testing strategies** across scraping, ML, and UI.  

---

## Development Philosophy

### "Glass Box" Transparency
- Traceable reasoning in all analyses.  
- Source attribution and confidence scoring.  
- Bias detection and credibility checks.  

### Technical Standards
- **Clean architecture** with modular design.  
- **Production readiness** (logging, retries, graceful error handling).  
- **Performance first**, with optimizations for concurrency and large-scale scraping.  
- **User experience focus**, building an intuitive research/trading UI.  

---

## Technical Stack

### Core Technologies
- **Python 3.9+** (backend, scraping, ML pipelines).  
- **Selenium WebDriver (primary)** with stealth/UDC for production scraping.  
- **Playwright MCP (secondary)** for rapid prototyping, DOM exploration, and UI testing.  
- **BeautifulSoup4** + **newspaper3k** for parsing article content.  
- **Pandas/numpy** for data handling.  
- **FinBERT + custom financial lexicon** for sentiment analysis.  
- **TextBlob** fallback for lightweight text analysis.  
- **FastAPI/Flask + frontend stack** for web UI.  
- **Threading/concurrent.futures** for parallel scraping.  

### Data Sources
- Bloomberg, MarketWatch, Yahoo Finance, Seeking Alpha, Google News RSS, NewsAPI.  
- Modular design allows new sources to be added easily.  

### AI & ML
- **Local FinBERT deployment** for sentiment classification.  
- **Bias detection algorithms** for credibility scoring.  
- **Future expansion:** predictive ML models (scikit-learn, PyTorch).  

---

## MCP Tools

- **Playwright MCP** → DOM exploration, testing selectors, UI automation.  


Claude should:  
- Use MCP tools directly when they accelerate development.  
- Default to Selenium for stealth scraping, Playwright MCP for testing/debugging.  
- Be explicit about which tool is used and why.  

---

## Coding Guidelines
- Python 3.10+ when possible.  
- Clean, modular functions with **docstrings + type hints**.  
- Use **async** where it improves scraping performance.  
- Implement **robust error handling** (timeouts, retries, proxy fallback).  
- Prefer simplicity for UI (Flask/FastAPI backend, vanilla JS or lightweight frontend).  

---

## Development Workflow with Claude

1. **Problem Identification** → Share context, error logs, and goals.  
2. **Solution Development** → Claude suggests multiple approaches, weighing trade-offs.  
3. **Code Review & Debugging** → Claude refines implementations, catches errors.  
4. **Documentation & Planning** → Claude generates docs, roadmaps, and testing strategies.  

---

## Current Achievements
- Multi-source scraping with anti-bot evasion.  
- FinBERT + hybrid sentiment pipeline.  
- Resilient error handling and scraper recovery.  
- Selenium resource management improvements.  

---

## Future Roadmap

### Short-term (2–4 weeks)
- Polish UI and UX.  
- Improve Selenium stealth strategies.  
- Optimize sentiment pipeline performance.  

### Medium-term (2–3 months)
- Portfolio tracking, alert systems, mobile responsiveness.  
- Database integration for historical research.  

### Long-term (6+ months)
- Full API for third-party integrations.  
- Technical analysis indicators and backtesting.  
- Predictive ML models for trading strategies.  
- Expansion to global markets.  

---

## Collaboration Guidelines

- Provide context, code, and desired outcomes in prompts.  
- Ask targeted, iterative questions.  
- Document learnings for future reference.  
- Follow best practices: version control, frequent testing, clear commits.  

---

## Project Status

**Current phase:** Advanced development, core scrapers + sentiment pipeline live.  
**Next milestone:** UI polish + production deployment.  
**Launch target:** ~1–2 months with focused dev.  

**Overall assessment:** Architecture is strong, scraping reliable, UI in progress, ML foundation ready for expansion.  

---

## Contact & Collaboration

This project is a unique collaboration between **human creativity** and **AI acceleration**. Claude is a:  
- Technical advisor  
- Debugging partner  
- Development accelerator  

**Success metric:** Build a transparent, reliable, and affordable financial research platform that users love and competitors fear.  

---

*Last updated: September 2025*  
*Project status: Active development with AI assistance*
