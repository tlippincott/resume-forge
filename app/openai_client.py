import json
import time
from openai import OpenAI
from app.config import API_KEY, MODEL_NAME

client = OpenAI(api_key=API_KEY)

def call_openai_json(messages, temperature=0.0, retries=2):
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON."},
                    *messages
                ],
                temperature=temperature
            )
            if not response.choices:
                raise RuntimeError("OpenAI returned empty response")
            return json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            if attempt == retries:
                raise RuntimeError(f"JSON parse failure: {e}")
            time.sleep(1)
