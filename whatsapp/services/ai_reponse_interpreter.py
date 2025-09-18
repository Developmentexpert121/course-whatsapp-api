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

    def answer_user_question(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful tutor."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.exception("Error in get_ai_answer")
            return None

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

    def get_ai_answer(self, prompt: str) -> str:
        """
        Wrapper for answering user questions with AI (alias for answer_user_question).
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful tutor."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.exception("Error in get_ai_answer")
            return None

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

    def detect_conversation_intent(
        self, user_input: str, current_state: str = None
    ) -> str:
        """
        Pure AI-powered intent detection for educational WhatsApp bot.
        Returns one of:
        'greeting', 'continue', 'quiz', 'module', 'question', 'cancel', 'unknown'
        """
        try:
            lower_user_input = user_input.lower().strip()
            intent = None

            # ✅ Exact match / keyword arrays
            continues = [
                "next",
                "ready",
                "continue",
                "go ahead",
                "move on",
                "start",
                "proceed",
            ]
            assessments = [
                "assessment",
                "quiz",
                "test",
                "exam",
                "start quiz",
                "start test",
            ]
            modules = ["module", "lesson", "study", "content", "chapter", "material"]
            prevs = ["prev", "previous", "last", "back", "earlier"]
            homes = ["home", "menu", "main menu", "options", "more options"]
            intros = [
                "intro",
                "introduction",
                "course intro",
                "course-intro",
                "course introduction",
                "about course",
            ]
            progresses = [
                "progress",
                "status",
                "my journey",
                "course progress",
                "course-progress",
                "how am i doing",
            ]
            cancels = ["cancel", "stop", "exit", "quit", "end", "pause"]

            if lower_user_input in continues:
                intent = "continue"
            elif lower_user_input in assessments:
                intent = "assessment"
            elif lower_user_input in modules:
                intent = "module"
            elif lower_user_input in prevs:
                intent = "prev"
            elif lower_user_input in homes:
                intent = "home"
            elif lower_user_input in intros:
                intent = "course-intro"
            elif lower_user_input in progresses:
                intent = "course-progress"
            elif lower_user_input in cancels:
                intent = "cancel"

            if not intent:

                # 4. 'quiz' - Requests a quiz or to be tested (e.g., "quiz me", "start quiz").
                system_prompt = """You are an intent classifier for an educational WhatsApp bot.
                    Classify the user's message into exactly one of the following categories:

                    1. 'greeting' - General greetings, gratitude, or polite phrases (e.g., "hello", "thanks").
                    2. 'continue' - Signals readiness to move forward (e.g., "ready", "next", "go ahead").
                    3. 'Repeat' - Signals to send the same content again. (e.g., "repeat", "send again")
                    3. 'assessment' - Mentions assessments explicitly (e.g., "assessment", "test time").
                    5. 'module' - Requests specific learning content or lessons (e.g., "show module", "study material").
                    6. 'question' - Asks a question *about the course*, the module, the subject, or related topics (e.g., "what is this course about?", "does this cover science?").
                    7. 'cancel' - Wants to stop, pause, or cancel the interaction (e.g., "stop", "cancel", "exit").
                    8. 'unknown' - If the message doesn't clearly match any category.
                    9. 'prev' - If user ask for prev part (e.g., "prev", "last", "back").
                    10. 'home' - if user ask for home, main menu, menu, more options etc.
                    11. 'course-intro' - If user ask for course introduction (e.g., "intro").
                    12. 'course-progress' - If user ask for course progress (e.g., "progress", "my journey").

                    ONLY return one of: greeting, continue, assessment, quiz, module, question, cancel, prev, course-intro, course-progress, home, unknown.

                    Current conversation state: {current_state}
                    """

                try:
                    completion = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",  # Fast and cost-effective for this task
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt.format(
                                    current_state=current_state
                                ),
                            },
                            {"role": "user", "content": user_input},
                        ],
                        temperature=0.1,  # Low temperature for consistent results
                        max_tokens=10,
                    )

                    intent = completion.choices[0].message.content.strip().lower()

                    print("AI content:", intent)

                except Exception as e:
                    logger.exception(
                        f"AI intent detection failed for input: {user_input}"
                    )
                    return "unknown"
            valid_intents = {
                "greeting",
                "continue",
                "assessment",
                "module",
                "question",
                "cancel",
                "prev",
                "home",
                "course-intro",
                "course-progress",
                "unknown",
            }
            return intent if intent in valid_intents else "unknown"

        except Exception as e:
            logger.exception(f"AI intent detection failed for input: {user_input}")
            return "unknown"

    def _ai_evaluate_response(cls, question, options, correct_answer, user_input):
        """
        Use AI to evaluate ambiguous responses against multiple choice options.
        """
        system_prompt = f"""You are a quiz evaluation system. Analyze whether the user's response 
        matches the correct answer from the given options, considering possible variations.
        
        Question: {question}
        Options: {', '.join(options)}
        Correct answer: {correct_answer}
        
        Return JSON with:
        - is_correct (bool)
        - confidence (float 0-1)
        - explanation (brief reason)"""

        user_prompt = f"User response: {user_input}"

        try:
            response = cls.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            evaluation = json.loads(response.choices[0].message.content)

            if (
                evaluation.get("is_correct", False)
                and evaluation.get("confidence", 0) > 0.7
            ):
                return {
                    "success": True,
                    "message": f"Correct! {evaluation.get('explanation', '')}",
                    "score": 1,
                    "user_answer": user_input,
                    "correct_answer": correct_answer,
                    "is_ai_corrected": True,
                }

        except Exception as e:
            logger.error(f"AI evaluation failed: {str(e)}")

        return {
            "success": False,
            "message": f"Incorrect. The correct answer was: {correct_answer}",
            "score": 0,
            "user_answer": user_input,
            "correct_answer": correct_answer,
            "is_ai_corrected": False,
        }

    def _ai_evaluate_short_answer(
        cls, question_text, user_answer, correct_answer, threshold
    ):
        """
        Use AI to evaluate if a short answer is conceptually correct.
        """
        system_prompt = f"""You are an educational assessment system. Evaluate the student's answer compared to the reference answer.
        
        Consider:
        - Conceptual accuracy
        - Alternative phrasing
        - Partial correctness
        - Relevance and depth

        Provide a JSON response with:
        - score (float between 0.0 and 1.0): How correct the student's answer is
        - confidence (float between 0.0 and 1.0): How confident you are in your judgment
        - explanation (string): Why the answer got that score
        - suggested_feedback (string): Constructive feedback to help the student improve

        You must only respond with valid JSON.
        
        Question: {question_text}
        Reference Answer: {correct_answer}
        """

        try:
            response = cls.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Student's answer: {user_answer}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            evaluation = json.loads(response.choices[0].message.content)

            score = float(evaluation.get("score", 0))
            confidence = float(evaluation.get("confidence", 0))

            return {
                "success": confidence >= threshold,
                "message": f"{'Correct!' if confidence >= threshold else 'Partially correct or incorrect.'} {evaluation.get('explanation', '')}",
                "score": round(score, 2),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_ai_corrected": True,
                "feedback": evaluation.get("suggested_feedback", ""),
            }

        except Exception as e:
            logger.error(f"AI short answer evaluation failed: {str(e)}")

            return {
                "success": False,
                "message": f"AI evaluation failed. The correct answer was: {correct_answer}",
                "score": 0,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_ai_corrected": True,
                "feedback": "Automatic feedback unavailable. Please review the answer manually.",
            }
