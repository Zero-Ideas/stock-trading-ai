# TODO: Sentiment Analysis System Improvements

## High Priority Fixes

### 🔧 Google News URL Resolution
- **Problem**: Currently disabled Selenium completely to avoid performance issues
- **Goal**: Implement efficient URL resolution that doesn't clog the system
- **Options**:
  - Use shared Selenium session with proper timeouts (5-10 seconds max)
  - Implement async/parallel resolution for multiple URLs
  - Add circuit breaker pattern - disable Selenium after N consecutive failures
  - Consider headless Firefox as Chrome alternative
  - Try RSS feed parsing improvements before falling back to Selenium

### 📊 Data Quality Improvements
- **Google News Content**: Currently getting ~167 char average (mostly titles)
  - Need actual article content for better sentiment analysis
  - Consider alternative Google News access methods
  - Implement fallback to other news aggregators
- **MarketWatch Access**: Getting 401 Forbidden errors
  - Update user agents and request headers
  - Implement rotating proxy support
  - Add retry mechanisms with exponential backoff

### ⚡ Performance Optimizations
- **Parallel Processing**: Implement true async article enhancement
- **Caching Layer**: Add persistent cache for resolved URLs and sentiment results
- **Batch Processing**: Process multiple articles simultaneously
- **Smart Limits**: Dynamically adjust article limits based on success rates

## Medium Priority Enhancements

### 🤖 Sentiment Analysis Accuracy
- **Neutral Classification**: Still getting 67.6% neutral articles
  - Fine-tune sentiment thresholds based on financial context
  - Implement domain-specific sentiment models
  - Add market context awareness (bull/bear market indicators)
- **Compound vs Polarity**: Ensure meaningful differentiation
  - Compound should reflect confidence/intensity
  - Polarity should be pure direction
  - Consider subjectivity weighting from TextBlob

### 📈 Source Diversification
- **New Sources**: Add reliable financial news sources
  - Reuters (fix existing implementation)
  - Financial Times
  - Wall Street Journal
  - CNBC
  - Bloomberg Terminal (if accessible)
- **Social Media**: Add Twitter/X sentiment for retail investor sentiment
- **Earnings Calls**: Parse earnings call transcripts for sentiment

### 🎯 Enhanced Analysis Features
- **Temporal Analysis**: Track sentiment changes over time periods
- **Volume-Weighted Sentiment**: Weight by article reach/source authority
- **Sector Context**: Compare sentiment relative to sector trends
- **Event Correlation**: Link sentiment spikes to news events
- **Confidence Scoring**: Rate the reliability of each sentiment reading

## Low Priority / Future Features
## These are all in the future so focus on others for now. skip these.
### 📱 User Experience
- **Real-time Updates**: Stream sentiment changes as they happen
- **Interactive Dashboard**: Web interface for sentiment visualization
- **Alert System**: Notify on significant sentiment shifts
- **Historical Analysis**: Compare current sentiment to historical patterns

### 🔍 Advanced Analytics
- **Sentiment Momentum**: Rate of sentiment change acceleration
- **Cross-Asset Correlation**: Compare sentiment across related stocks
- **Options Market Integration**: Correlate with options flow sentiment
- **Insider Trading Correlation**: Compare with insider activity

### 🛠️ Technical Debt
- **Code Organization**: Separate scrapers into individual modules
- **Error Handling**: Comprehensive error logging and recovery
- **Configuration Management**: Externalize settings to config files
- **Testing Suite**: Unit tests for all scraper components
- **Documentation**: API documentation and usage examples

## Immediate Next Steps (Tomorrow)
1. **Fix Selenium timeout implementation** - Add proper 5-10 second limits
2. **Implement URL resolution success tracking** - Disable sources with <10% success rate
3. **Add MarketWatch user agent rotation** - Fix 401 Forbidden errors
4. **Test with different stocks** - Verify improvements work across different symbols
5. **Benchmark performance** - Measure time per article and identify bottlenecks

## Success Metrics to Track
- **Resolution Success Rate**: % of Google News URLs successfully resolved
- **Content Enhancement**: Average article length after newspaper3k extraction  
- **Processing Time**: Total time from start to completion
- **Sentiment Distribution**: Aim for more realistic positive/negative ratios
- **Source Reliability**: Track which sources provide the most valuable content

---
*Generated: 2025-08-31*
*Current Status: Google News resolution disabled for reliability, system stable but content quality needs improvement*