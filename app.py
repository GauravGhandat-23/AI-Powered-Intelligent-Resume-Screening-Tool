import streamlit as st
from groq import Groq
import pdfplumber
import docx
import tempfile
import os
import re

# Set the Groq API Key directly in the code
GROQ_API_KEY = "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"

# Function to extract text from PDF
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or "" + "\n"
    return text

# Function to extract text from DOCX
def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# Extract resume text based on file type
def extract_resume_text(uploaded_file):
    _, extension = os.path.splitext(uploaded_file.name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
        temp_file.write(uploaded_file.read())
        temp_path = temp_file.name

    if extension.lower() == ".pdf":
        with open(temp_path, "rb") as f:
            return extract_text_from_pdf(f)
    elif extension.lower() == ".docx":
        return extract_text_from_docx(temp_path)

# Clean extracted resume text
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^A-Za-z0-9\s,.@\-]', '', text)
    return text.strip()

# Analyze resume using Groq (non-streaming to avoid partial outputs)
def analyze_resume(resume_text, job_desc):
    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
You are an expert AI HR assistant. Analyze the resume against the following job description.
Return the results strictly in this format:

1. Candidate Name        
2. Match Score (out of 100)  
3. Final Verdict: Strong Match / Moderate Match / Weak Match
4. Short Description: [One-line summary of why they match]

DO NOT include any extra text or explanation.

Resume:
{resume_text}

Job Description:
{job_desc}
"""

    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=512,
        top_p=1,
    )

    response = completion.choices[0].message.content.strip()
    return response

# Streamlit UI
st.set_page_config(page_title="AI Intelligent Resume Screener", layout="wide")
st.title("🤖 AI-Powered Intelligent Resume Screening Tool")
st.markdown("Upload multiple resumes and enter a job description for quick ATS-style analysis.")

# File uploader (supports multiple files)
uploaded_files = st.file_uploader("📄 Upload Resumes (PDF or DOCX)", type=["pdf", "docx"], accept_multiple_files=True)

# Job description input
job_desc = st.text_area("💼 Enter Job Description", height=200, placeholder="Paste the job description here...")

# Analyze button
if st.button("🔍 Analyze All Resumes") and uploaded_files and job_desc:
    with st.spinner("🧠 Analyzing all resumes... This may take a few moments."):
        results = []
        for idx, uploaded_file in enumerate(uploaded_files):
            resume_text = extract_resume_text(uploaded_file)
            cleaned_resume = clean_text(resume_text)
            analysis = analyze_resume(cleaned_resume, job_desc)
            results.append({"filename": uploaded_file.name, "analysis": analysis})

        # Show final results
        st.success("✅ Analysis completed!")
        for res in results:
            st.markdown(f"---\n### 📄 {res['filename']}\n\n{res['analysis']}")

