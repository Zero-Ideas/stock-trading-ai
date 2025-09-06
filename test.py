from openai import OpenAI
import json
import os
import base64
from google import genai
from google.genai import types


os.environ["OPENAI_API_KEY"] = "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"
os.environ["GEMINI_API_KEY"] = "AIzaSyA91d_s6glh9j8de5CDoxB12lFbTziLn50"
client = OpenAI()

industry_list = [
    "Technology",
    "Semiconductor",
    "Healthcare",
    "Finance",
    "Retail",
    "Manufacturing",
    "Energy",
    "Consumer Goods",
    "Real Estate",
    "Telecommunications",
    "Utilities",
    "Transportation",
    "Hospitality",
    "Construction",
    "Education",
    "Government",
    "Agriculture",
    "Media & Entertainment",
    "Professional Services",
    "Pharmaceuticals",
    "Biotechnology",
    "Automotive",
    "Aerospace & Defense",
    "Insurance",
    "Food & Beverage",
    "Chemicals",
    "Mining & Metals",
    "Logistics & Shipping",
    "E-commerce",
    "Information Technology Services",
    "Renewable Energy",
    "Travel & Tourism",
    "Nonprofit & NGOs",
    "Sports & Recreation",
    "Fashion & Apparel",
    "Legal Services",
    "Advertising & Marketing",
    "Semiconductor Equipment",
    "Internet & Online Services",
    "Electronics",
    "Luxury Goods"
]
def generate(symbol):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash-lite"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"what industry best fits the company with the stock symbol {symbol} in out of these industries? Options: [{', '.join(industry_list)}]  Respond in this format {{'industry': <string>, 'company_name: <string>'}} without formatting."),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=0,
        ),
        # Ensure the output is treated as JSON
        response_mime_type="application/json",
    )
    response_parts = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        # 2. Add each part's text to the list
        response_parts.append(chunk.text)

    # 3. Join the parts into one complete string after the loop
    full_response = "".join(response_parts)
    print(f"Full model response received: {full_response}") # For debugging
    return json.loads(full_response.replace("'", '"'))




industry = generate("DIS")["industry"]

sentiment_labels = ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
format_string = f"""{{
    "industry": {' | '.join(industry_list)},
    "overall_sentiment": <float>,
    "sentiment_label": {' | '.join(sentiment_labels)},
    "confidence_score": <float>,
    "key_trends": [<string>],
    "reasoning": <string>,
    "sources": [<URL>]
}}"""

companySymbol = "JPM"

response = client.responses.create(
    model="gpt-5-nano",
    tools=[{"type": "web_search"}],
    input=f"Analyze the {industry} and respond in this format: {format_string} ",
)
output =json.loads(response.output_text)
output['confidence_score'] = float(output['confidence_score'])
output['overall_sentiment'] = float(output['overall_sentiment'])
#save to file
with open("output.json", "w") as f:
    json.dump(output, f, indent=4)
