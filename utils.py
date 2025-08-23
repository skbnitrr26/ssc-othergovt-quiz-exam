# utils.py

import os
import streamlit as st
from typing import List
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator

load_dotenv()

# -------------------------
# Pydantic Models
# -------------------------
class MCQQuestion(BaseModel):
    question: str = Field(description="The question text")
    options: List[str] = Field(description="List of 4 possible answers")
    correct_answer: str = Field(description="The correct answer from the options")

    @validator('question', pre=True)
    def clean_question(cls, v):
        if isinstance(v, dict):
            return v.get('description', str(v))
        return str(v)

class FillBlankQuestion(BaseModel):
    question: str = Field(description="The question text with '_____' for the blank")
    answer: str = Field(description="The correct word or phrase for the blank")

    @validator('question', pre=True)
    def clean_question(cls, v):
        if isinstance(v, dict):
            return v.get('description', str(v))
        return str(v)

# -------------------------
# Question Generator
# -------------------------
class QuestionGenerator:
    def __init__(self):
        try:
            groq_api_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            groq_api_key = None

        if not groq_api_key:
            groq_api_key = os.getenv("GROQ_API_KEY")

        if not groq_api_key:
            raise ValueError(
                "Groq API key not found! Add it to Streamlit secrets or .env file."
            )

        self.llm = ChatGroq(
            api_key=groq_api_key,
            model="llama-3.1-8b-instant",
            temperature=0.9
        )

    def generate_mcq(self, topic: str, difficulty: str = 'medium') -> MCQQuestion:
        mcq_parser = PydanticOutputParser(pydantic_object=MCQQuestion)
        prompt = PromptTemplate(
            template=(
                "Generate a {difficulty} multiple-choice question about {topic}.\n\n"
                "Return ONLY a JSON object with fields:\n"
                "- 'question'\n- 'options' (array of 4)\n- 'correct_answer'\n"
                "Example:\n"
                '{{"question": "What is 2+2?", "options": ["3","4","5","6"], "correct_answer":"4"}}\n'
                "Your response:"
            ),
            input_variables=["topic", "difficulty"]
        )

        for attempt in range(3):
            try:
                response = self.llm.invoke(prompt.format(topic=topic, difficulty=difficulty))
                parsed_response = mcq_parser.parse(response.content)

                if not parsed_response.question or len(parsed_response.options) != 4 or not parsed_response.correct_answer:
                    raise ValueError("Invalid question format")
                if parsed_response.correct_answer not in parsed_response.options:
                    raise ValueError("Correct answer not in options")

                return parsed_response
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f"Failed to generate valid MCQ: {str(e)}")
                continue

    def generate_fill_blank(self, topic: str, difficulty: str = 'medium') -> FillBlankQuestion:
        fill_blank_parser = PydanticOutputParser(pydantic_object=FillBlankQuestion)
        prompt = PromptTemplate(
            template=(
                "Generate a {difficulty} fill-in-the-blank question about {topic}.\n"
                "Return ONLY JSON:\n"
                "- 'question' with '_____'\n- 'answer'\n"
                "Example: {{'question':'The capital of France is _____.','answer':'Paris'}}\n"
                "Your response:"
            ),
            input_variables=["topic", "difficulty"]
        )

        for attempt in range(3):
            try:
                response = self.llm.invoke(prompt.format(topic=topic, difficulty=difficulty))
                parsed_response = fill_blank_parser.parse(response.content)

                if not parsed_response.question or not parsed_response.answer:
                    raise ValueError("Invalid question format")
                if "_____" not in parsed_response.question:
                    parsed_response.question = parsed_response.question.replace("___", "_____")
                    if "_____" not in parsed_response.question:
                        raise ValueError("Question missing blank '_____'")
                return parsed_response
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f"Failed to generate valid fill-in-the-blank: {str(e)}")
                continue
