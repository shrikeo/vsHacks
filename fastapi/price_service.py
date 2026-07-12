import re
import json
import time

from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from dotenv import load_dotenv

load_dotenv()


class PriceService:
    """Uses Gemini + Google Search grounding to fetch a rough current price."""

    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-2.5-flash"
        self.grounding_tool = types.Tool(google_search=types.GoogleSearch())

    def check_price(self, name, max_retries=3):
        prompt = (
            f'Search shopping sites for the current price of "{name}". '
            "Prefer major retailers like Amazon, Walmart, Best Buy, Target, and eBay. "
            "Give the typical current price in USD and whether now is a good time to buy "
            "(is it on sale / a good deal right now?). "
            "In the note, mention which store has the best price and its price. "
            'Reply ONLY with JSON in exactly this shape, no extra words:\n'
            '{"price": <number>, "goodDeal": <true|false>, "note": "<short note incl. best store>"}'
        )

        # Grounded calls occasionally return a transient 503; retry with backoff.
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    config={
                        "tools": [self.grounding_tool],
                        # No reasoning needed for a price lookup — skip it to cut latency.
                        "thinking_config": types.ThinkingConfig(thinking_budget=0),
                    },
                    contents=prompt,
                )
                result = self._parse(response.text)
                result["sources"] = self._extract_sources(response)
                return result
            except genai_errors.ServerError as error:
                last_error = error
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        raise last_error

    def _parse(self, text):
        # Grounded replies aren't pure JSON — pull the first {...} out of the text.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in reply: {text}")
        return json.loads(match.group(0))

    def _extract_sources(self, response):
        # Pull the web pages Gemini grounded on so the UI can link to them.
        sources = []
        try:
            chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
        except (AttributeError, IndexError, TypeError):
            return sources
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if web and getattr(web, "uri", None):
                sources.append({"title": web.title or web.uri, "url": web.uri})
        return sources


priceClient = PriceService()
