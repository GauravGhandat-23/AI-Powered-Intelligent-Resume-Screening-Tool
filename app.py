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

# Analyze resume using Groq with better error handling
def analyze_resume(resume_text, technical_skills="", soft_skills=""):
    client = Groq(api_key=GROQ_API_KEY)

    # Build criteria string based on provided inputs
    criteria_parts = []
    if technical_skills.strip():
        criteria_parts.append(f"Technical Skills: {technical_skills}")
    if soft_skills.strip():
        criteria_parts.append(f"Soft Skills: {soft_skills}")
    
    # If no criteria provided, use a general analysis
    if not criteria_parts:
        criteria_string = "General skills and qualifications assessment"
    else:
        criteria_string = "\n".join(criteria_parts)

    prompt = f"""
You are an expert AI HR assistant. Analyze the resume against the following criteria.
Return the results strictly in this format:

1. Candidate Name: [Full Name]        
2. Match Score: [0-100]  
3. Key Skills Found: [comma-separated list]
4. Missing Skills: [comma-separated list]
5. Verdict: Strong Match / Moderate Match / Weak Match

DO NOT include any extra text or explanation. Follow this exact format.

Resume:
{resume_text}

Criteria to Match Against:
{criteria_string}
"""

    try:
        completion = client.chat.completions.create(
            model="qwen-qwq-32b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_completion_tokens=4096,
            top_p=0.95,
        )

        response = completion.choices[0].message.content.strip()
        return response
    except Exception as e:
        return f"Error in analysis: {str(e)}"

# Function to parse the analysis response
def parse_analysis_response(response):
    result = {
        "name": "Not found",
        "score": 0,
        "found_skills": "Not found",
        "missing_skills": "Not found",
        "verdict": "Not found",
        "raw_response": response
    }
    
    try:
        # Extract name
        name_match = re.search(r"1\. Candidate Name:\s*(.+)", response)
        if name_match:
            result["name"] = name_match.group(1).strip()
        
        # Extract score
        score_match = re.search(r"2\. Match Score:\s*(\d+)", response)
        if score_match:
            result["score"] = int(score_match.group(1))
        
        # Extract found skills
        found_match = re.search(r"3\. Key Skills Found:\s*(.+)", response)
        if found_match:
            result["found_skills"] = found_match.group(1).strip()
        
        # Extract missing skills
        missing_match = re.search(r"4\. Missing Skills:\s*(.+)", response)
        if missing_match:
            result["missing_skills"] = missing_match.group(1).strip()
        
        # Extract verdict
        verdict_match = re.search(r"5\. Verdict:\s*(.+)", response)
        if verdict_match:
            result["verdict"] = verdict_match.group(1).strip()
    
    except Exception as e:
        st.error(f"Error parsing response: {str(e)}")
    
    return result

# Streamlit UI
st.set_page_config(page_title="AI Resume Screener", layout="wide")
st.title("🚀 AI-Powered Resume Screening Tool")
st.markdown("""
    <style>
    .big-font { font-size:18px !important; }
    .upload-box { border: 2px dashed #ccc; padding: 20px; border-radius: 5px; }
    .match-score { font-weight: bold; font-size: 16px; }
    .strong-match { color: #2ecc71; }
    .moderate-match { color: #f39c12; }
    .weak-match { color: #e74c3c; }
    </style>
    """, unsafe_allow_html=True)

# Main content
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📁 Upload Resumes")
    with st.container(border=True):
        uploaded_files = st.file_uploader(
            "Drag & drop resumes here",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            help="You can select multiple files at once",
            label_visibility="collapsed"
        )
    st.markdown(f"<p class='big-font'>📌 {len(uploaded_files) if uploaded_files else 'No'} files selected</p>", unsafe_allow_html=True)

with col2:
    st.subheader("🔍 Screening Requirements")
    
    # Create separate input fields
    col2_1, col2_2 = st.columns(2)
    
    with col2_1:
        technical_skills = st.text_input(
            "Technical Skills",
            placeholder="e.g., Python, JavaScript, React, SQL",
            help="Enter technical skills separated by commas (optional)"
        )
    
    with col2_2:
        soft_skills = st.text_input(
            "Soft Skills",
            placeholder="e.g., Communication, Leadership, Teamwork",
            help="Enter soft skills separated by commas (optional)"
        )
    
    st.markdown("---")
    
    if st.button("🚀 Screen Resumes", use_container_width=True, type="primary"):
        if not uploaded_files:
            st.warning("Please upload at least one resume")
        else:
            # Check if at least one field has input (though all are optional)
            has_criteria = any([technical_skills.strip(), soft_skills.strip()])
            
            if not has_criteria:
                st.info("No specific criteria provided. Performing general resume analysis...")
            
            with st.spinner(f"🔍 Screening {len(uploaded_files)} resumes..."):
                results = []
                for uploaded_file in uploaded_files:
                    try:
                        resume_text = extract_resume_text(uploaded_file)
                        cleaned_resume = clean_text(resume_text)
                        analysis = analyze_resume(cleaned_resume, technical_skills, soft_skills)
                        parsed = parse_analysis_response(analysis)
                        
                        results.append({
                            "filename": uploaded_file.name,
                            "name": parsed["name"],
                            "score": parsed["score"],
                            "found_skills": parsed["found_skills"],
                            "missing_skills": parsed["missing_skills"],
                            "verdict": parsed["verdict"],
                            "raw_response": parsed["raw_response"]
                        })
                        
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                        results.append({
                            "filename": uploaded_file.name,
                            "error": str(e)
                        })
                
                # Filter out failed analyses
                successful_results = [res for res in results if "error" not in res]
                
                if successful_results:
                    # Sort results by score (high to low)
                    successful_results.sort(key=lambda x: x["score"], reverse=True)
                    
                    # Display results
                    st.success(f"✅ Screening complete! Analyzed {len(successful_results)}/{len(uploaded_files)} resumes")
                    
                    for res in successful_results:
                        # Determine verdict class for styling
                        verdict_class = ""
                        if "Strong" in res["verdict"]:
                            verdict_class = "strong-match"
                        elif "Moderate" in res["verdict"]:
                            verdict_class = "moderate-match"
                        else:
                            verdict_class = "weak-match"
                        
                        with st.expander(f"📄 {res['filename']} - {res['name']} - Score: {res['score']}/100", expanded=True):
                            st.markdown(f"""
                            **Candidate Name:** {res['name']}  
                            **Match Score:** <span class='match-score'>{res['score']}/100</span>  
                            **Verdict:** <span class='{verdict_class}'>{res['verdict']}</span>  
                            **Key Skills Found:** {res['found_skills']}  
                            **Missing Skills:** {res['missing_skills']}  
                            """, unsafe_allow_html=True)
                            
                            st.markdown("---")
                
                # Show errors if any
                error_results = [res for res in results if "error" in res]
                if error_results:
                    st.warning(f"⚠️ Could not process {len(error_results)} resumes:")
                    for err in error_results:
                        st.error(f"{err['filename']}: {err['error']}")