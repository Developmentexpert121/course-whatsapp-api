import json
import logging
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

logger = logging.getLogger(__name__)


class AIResponseInterpreter:
    """
    Interprets a user's response using OpenAI and suggests the best next step
    based on predefined possible actions.
    """

    """
    USAGE
    
    interpreter = AIResponseInterpreter(api_key="sk-...")
    
    result = interpreter.analyze_response(
    question="What is your preferred learning style?",
    response="I think I like visuals, but not too sure",
    environment_context="We are trying to customize their course path",
    possible_next_steps=["assign_video_course", "assign_text_course", "ask_more_details"]
    )

    if result["next_step"]:
        # proceed with step
        perform_next_step(result["next_step"])
    else:
        # send clarification message to user
        WhatsAppService.send_message(user.phone_number_id, user.whatsapp_id, result["user_message"])
    
    
    
    result = interpreter.extract_answer(
        question="How many years of experience do you have?",
        response="I’ve been in this field for over 5 years now",
        environment_context="User is applying for a tech mentorship program"
    )

    if result["answer"]:
        save_to_user_profile("experience_years", result["answer"])
    else:
        send_clarification_message("Could you confirm how many years exactly?")

    """

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def analyze_next_step(
        self,
        question: str,
        response: str,
        environment_context: str,
        possible_next_steps: list,
    ) -> dict:
        """
        Analyze the user's response and determine the best next step from the list provided.
        """
        system_prompt = (
            "You are a decision-making assistant for a conversational bot. "
            "Based on the user's response and question context, choose the most relevant next step. "
            'Respond strictly in JSON format like: {"next_step": "<step>", "message_to_user": "<message>"} '
            "If none of the next steps are appropriate, suggest a clarification message."
        )

        user_prompt = (
            f"Question: {question}\n"
            f"User Response: {response}\n"
            f"Context: {environment_context}\n"
            f"Possible Next Steps: {json.dumps(possible_next_steps)}"
        )

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            content = completion.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.exception("Error in analyze_next_step")
            return {"next_step": None, "message_to_user": "Something went wrong."}

    def extract_answer(
        self, question: str, response: str, environment_context: str = ""
    ) -> dict:
        """
        Extract the direct answer from the user's response in structured JSON.
        If the answer is unclear or not found, provide a user-friendly message.
        """
        system_prompt = (
            "You are an assistant that extracts specific answers from vague user responses.\n"
            "Your job is to find the most probable answer from the response.\n"
            "If you're unsure or the answer is missing, return a helpful message the system can send to the user.\n"
            "Format your response in this JSON format:\n"
            '{"answer": "<answer_if_found>", "message_to_user": "<message_to_user_if_uncertain_or_empty>"}\n'
            'If confident in the answer, leave "message_to_user" empty.\n'
            'If unsure, set "answer" to null and provide a polite clarifying message in "message_to_user".'
        )

        user_prompt = (
            f"Question: {question}\n"
            f"User Response: {response}\n"
            f"Context: {environment_context}"
        )

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            content = completion.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.exception("Error in extract_answer")
            return {
                "answer": None,
                "message_to_user": "Sorry, I couldn't understand your answer. Could you please clarify?",
            }
