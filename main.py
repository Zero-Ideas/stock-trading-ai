import numpy as np
import json
def analyze_sentiment(sentiment_data, extreme_threshold=0.6, variance_threshold=0.1):
    """
    Determines whether to lean toward a direction or flag volatility.
    
    Parameters:
        sentiment_data (dict): Your sentiment output containing `sentiment_scores` and `sample_articles`.
        extreme_threshold (float): Threshold for strong directional mean sentiment.
        variance_threshold (float): Threshold for high variance to indicate volatility.
        
    Returns:
        dict: Decision summary with reason.
    """
    # Extract all sentiment scores
    scores = [article['sentiment_score'] for article in sentiment_data['sample_articles'] if 'sentiment_score' in article]
    
    if not scores:
        return {"decision": "No data", "reason": "No sentiment scores found"}
    
    mean_sentiment = np.mean(scores)
    sentiment_variance = np.var(scores)
    
    # Determine direction or volatility
    if abs(mean_sentiment) >= extreme_threshold and sentiment_variance < variance_threshold:
        direction = "Positive" if mean_sentiment > 0 else "Negative"
        return {
            "decision": f"Lean {direction}",
            "mean_sentiment": mean_sentiment,
            "variance": sentiment_variance,
            "reason": f"Strong consensus (mean {mean_sentiment:.3f}) and low variance ({sentiment_variance:.3f})"
        }
    elif sentiment_variance >= variance_threshold:
        return {
            "decision": "Volatile / Mixed Sentiment",
            "mean_sentiment": mean_sentiment,
            "variance": sentiment_variance,
            "reason": f"High variance ({sentiment_variance:.3f}) despite mean sentiment ({mean_sentiment:.3f})"
        }
    else:
        return {
            "decision": "Neutral",
            "mean_sentiment": mean_sentiment,
            "variance": sentiment_variance,
            "reason": f"No strong directional signal (mean {mean_sentiment:.3f}, variance {sentiment_variance:.3f})"
        }
import json
import os

# Path to your JSON file
file_path = os.path.join('.', 'Data', 'AAPL.json')

# Open and load the JSON data
with open(file_path, 'r', encoding='utf-8') as f:
    apple_sentiment_data = json.load(f)

# Now pass it to the analyze_sentiment function
result = analyze_sentiment(apple_sentiment_data)
for item in result.items():
    print(item[0], ":", item[1])