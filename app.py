# app.py

import streamlit as st
import pandas as pd
import os
from utils import QuestionGenerator
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

class QuizManager:
    def __init__(self):
        self.questions = []
        self.user_answers = []
        self.results = []

    def generate_questions(self, generator, topic, question_type, difficulty, num_questions):
        self.questions, self.user_answers, self.results = [], [], []
        try:
            for _ in range(num_questions):
                if question_type == "Multiple Choice":
                    question = generator.generate_mcq(topic, difficulty.lower())
                    self.questions.append({
                        'type': 'MCQ',
                        'question': question.question,
                        'options': question.options,
                        'correct_answer': question.correct_answer
                    })
                else:
                    question = generator.generate_fill_blank(topic, difficulty.lower())
                    self.questions.append({
                        'type': 'Fill in the Blank',
                        'question': question.question,
                        'correct_answer': question.answer
                    })
        except Exception as e:
            st.error(f"Error generating questions: {e}")
            return False
        return True

    def attempt_quiz(self):
        st.markdown("## ✍️ Answer the Questions")
        for i, q in enumerate(self.questions):
            with st.container():
                st.markdown(f"**Q{i+1}: {q['question']}**")
                st.progress((i+1)/len(self.questions))
                st.caption(f"Question {i+1} of {len(self.questions)}")
                if q['type'] == 'MCQ':
                    user_answer = st.radio("Choose an option:", q['options'], key=f"mcq_{i}")
                else:
                    user_answer = st.text_input("Type your answer:", key=f"fill_{i}")
                self.user_answers.append(user_answer)

    def evaluate_quiz(self):
        self.results = []
        for i, (q, user_ans) in enumerate(zip(self.questions, self.user_answers)):
            result_dict = {
                'question_number': i + 1,
                'question': q['question'],
                'question_type': q['type'],
                'user_answer': user_ans,
                'correct_answer': q['correct_answer'],
                'is_correct': False
            }
            if q['type'] == 'MCQ':
                result_dict['options'] = q['options']
                result_dict['is_correct'] = user_ans == q['correct_answer']
            else:
                result_dict['options'] = []
                result_dict['is_correct'] = user_ans.strip().lower() == q['correct_answer'].strip().lower()
            self.results.append(result_dict)

    def generate_result_dataframe(self):
        return pd.DataFrame(self.results) if self.results else pd.DataFrame()

    def save_to_csv(self):
        if not self.results:
            st.warning("⚠️ No results to save.")
            return None
        df = self.generate_result_dataframe()
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("results", exist_ok=True)
        file_path = f"results/quiz_results_{timestamp}.csv"
        df.to_csv(file_path, index=False)
        return file_path

    def save_to_pdf(self):
        if not self.results:
            st.warning("⚠️ No results to save.")
            return None
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 50
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "Quiz Results")
        y -= 30
        df = self.generate_result_dataframe()
        for _, row in df.iterrows():
            c.setFont("Helvetica", 12)
            c.drawString(50, y, f"Q{row['question_number']}: {row['question']}")
            y -= 20
            c.drawString(60, y, f"Your Answer: {row['user_answer']}")
            y -= 20
            c.drawString(60, y, f"Correct Answer: {row['correct_answer']}")
            y -= 30
            if y < 100:
                c.showPage()
                y = height - 50
        c.save()
        buffer.seek(0)
        return buffer

def main():
    st.set_page_config(page_title="Exam Quiz Generator", page_icon="📝", layout="wide")

    if 'quiz_manager' not in st.session_state:
        st.session_state.quiz_manager = QuizManager()
    if 'quiz_generated' not in st.session_state:
        st.session_state.quiz_generated = False
    if 'quiz_submitted' not in st.session_state:
        st.session_state.quiz_submitted = False

    st.title("📚 SSC, PCS & Other Exam Question Generator")

    # Sidebar Settings
    st.sidebar.header("⚙️ Quiz Settings")
    api_choice = st.sidebar.selectbox("Select API", ["Groq"])
    question_type = st.sidebar.selectbox("Select Question Type", ["Multiple Choice", "Fill in the Blank"])
    topic = st.sidebar.text_input("Enter Topic", placeholder="Indian History, Geography, etc.")
    difficulty = st.sidebar.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"], index=1)
    num_questions = st.sidebar.number_input("Number of Questions", min_value=1, max_value=20, value=5)

    if st.sidebar.button("🚀 Generate Quiz & Start"):
        st.session_state.quiz_submitted = False
        generator = QuestionGenerator()
        st.session_state.quiz_generated = st.session_state.quiz_manager.generate_questions(
            generator, topic, question_type, difficulty, num_questions
        )

    # Quiz Display
    if st.session_state.quiz_generated and st.session_state.quiz_manager.questions:
        st.session_state.quiz_manager.attempt_quiz()
        if st.button("✅ Submit Quiz"):
            st.session_state.quiz_manager.evaluate_quiz()
            st.session_state.quiz_submitted = True

    # Results Display
    if st.session_state.quiz_submitted:
        st.header("📊 Quiz Results")
        results_df = st.session_state.quiz_manager.generate_result_dataframe()
        if not results_df.empty:
            correct = results_df['is_correct'].sum()
            total = len(results_df)
            score_pct = (correct / total) * 100

            # Score metric
            st.metric("Your Score", f"{correct}/{total}", f"{score_pct:.1f}%")

            # Pie chart
            fig, ax = plt.subplots()
            ax.pie(
                [correct, total - correct],
                labels=["Correct", "Incorrect"],
                autopct="%1.1f%%",
                startangle=90,
                colors=["#4CAF50", "#FF4B4B"]
            )
            st.pyplot(fig)

            # Detailed results
            for _, row in results_df.iterrows():
                with st.expander(f"Question {row['question_number']}"):
                    st.write(f"**Q: {row['question']}**")
                    if row['is_correct']:
                        st.success(f"✅ Correct! Your answer: {row['user_answer']}")
                    else:
                        st.error(f"❌ Wrong. Your answer: {row['user_answer']}")
                        st.info(f"✅ Correct Answer: {row['correct_answer']}")

            # Save + Download CSV & PDF
            col1, col2 = st.columns(2)
            with col1:
                path = st.session_state.quiz_manager.save_to_csv()
                if path:
                    with open(path, "rb") as f:
                        st.download_button("⬇️ Download CSV", f.read(), file_name=os.path.basename(path), mime="text/csv")
            with col2:
                pdf_buffer = st.session_state.quiz_manager.save_to_pdf()
                if pdf_buffer:
                    st.download_button("⬇️ Download PDF", pdf_buffer, file_name="quiz_results.pdf", mime="application/pdf")

    # Custom footer
    st.markdown(
        """
        <div style="
            position: fixed;
            left: 20px;
            bottom: 10px;
            color: ##000000;
            font-size: 14px;
        ">
            👨‍💻 Made by <a href="https://www.linkedin.com/in/sumit-kumar-476792290" target="_blank" style="text-decoration:none; color:##000000;">
            <b>सuमि𝓉</b></a>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
