"""NLP service for habit classification using configurable LLM providers."""

import json
from openai import OpenAI
from src.config import settings


class NLPService:
    """Service for natural language processing of habit logs."""

    def __init__(self):
        """Initialize NLPService with configured LLM client."""
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model
        
        if self.provider == "openai":
            if not settings.llm_api_key:
                raise ValueError("LLM_API_KEY is required for OpenAI provider")
            self.client = OpenAI(api_key=settings.llm_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def classify_habit_from_text(
        self,
        user_text: str,
        available_habits: list[str]
    ) -> list[str]:
        """
        Classify user text to match one or more known habits.

        Algorithm:
        1. Fetch all active habit names from Habits table
        2. Construct prompt with available habits
        3. Call OpenAI API (gpt-4 or gpt-3.5-turbo)
        4. Parse JSON response to extract matched habit(s)
        5. Return list of matched habits

        Args:
            user_text: Free text input from user
            available_habits: List of habit names to match against

        Returns:
            List of matched habit names (may be empty if no match)
        """
        prompt = self.build_classification_prompt(user_text, available_habits)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI that maps user habit logs to known habits. "
                                   "Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )

            # Extract and parse response
            content = response.choices[0].message.content.strip()

            # Try to parse as JSON
            try:
                result = json.loads(content)
                if isinstance(result, dict) and "habits" in result:
                    return result["habits"]
                elif isinstance(result, list):
                    return result
                else:
                    return []
            except json.JSONDecodeError:
                # If not valid JSON, return empty list
                return []

        except Exception as e:
            print(f"Error in LLM classification ({self.provider}/{self.model}): {e}")
            return []

    def build_classification_prompt(
        self,
        user_text: str,
        habits: list[str]
    ) -> str:
        """
        Build prompt for habit classification.

        Args:
            user_text: User's input text
            habits: List of available habit names

        Returns:
            Formatted prompt string
        """
        habits_list = "\n".join([f"- {habit}" for habit in habits])

        prompt = f"""You are an AI that maps user habit logs to known habits.

Available habits:
{habits_list}

User input: "{user_text}"

Match the user input to one or more habits from the list above.
Return your response as a JSON object with a "habits" key containing an array of matched habit names.

Example response format:
{{"habits": ["Walking", "Reading"]}}

If no habits match, return:
{{"habits": []}}

Only include habits that are clearly indicated by the user's text.
"""
        return prompt


# Global service instance
nlp_service = NLPService()
