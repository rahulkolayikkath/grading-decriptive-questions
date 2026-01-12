import streamlit as st
from PIL import Image
import io
import yaml
from google.cloud import storage
import datetime
import pandas as pd
import os

from src.workflow import SubmitQueryRequest, QueryRepsonse, build_workflow

# workflow code
graph  = build_workflow()
def submit_query_endpoint(request:SubmitQueryRequest) -> QueryRepsonse:
    """ invoke the graph and return reposne"""
    state = graph.invoke({"question":request})
    return QueryRepsonse(
    solution_pathway = state.get("solution_pathway", None),
    reason = state.get("feedback", None),
    value_points = state.get("value_points", None),
    mark= state.get("mark", 0.0),
    extracted_answer = state.get("student_answer_text", None),
    content_analysis = state.get("content_analysis", None),
    cost = state.get("cost", 0.0),
    input_tokens = state.get("input_tokens", 0.0), 
    output_tokens = state.get("output_tokens", 0.0),
    success = state.get("success", True),
    error_message = state.get("error_message", None)
    )

# Configure the page
st.set_page_config(page_title="Quiz App", layout="wide")

# Load questions from YAML file
@st.cache_data
def load_questions(yaml_file_path):
    """Load questions from YAML file"""
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            return data['test_questions']
    except FileNotFoundError:
        st.error(f"YAML file not found: {yaml_file_path}")
        return []
    except Exception as e:
        st.error(f"Error loading YAML file: {e}")
        return []

# Path to your YAML file - modify this path as needed
YAML_FILE_PATH = "test_questions.yaml"  # Change this to your actual file path

# Load question data
questions_data = load_questions(YAML_FILE_PATH)

# Create a simple display mapping for sidebar
QUESTIONS = {f"{q['id']}": q['question'] for q in questions_data}

# Create a lookup dictionary for full question details
QUESTION_DETAILS = {q['id']: q for q in questions_data}

# Initialize session state
if 'selected_question' not in st.session_state:
    st.session_state.selected_question = list(QUESTIONS.keys())[0] if QUESTIONS else None
if 'show_result' not in st.session_state:
    st.session_state.show_result = False
if 'current_result' not in st.session_state:
    st.session_state.current_result = None

# Check if questions loaded successfully
if not questions_data:
    st.error("No questions loaded. Please check your YAML file path.")
    st.stop()

# Sidebar navigation
st.sidebar.title("📋 Questions")
st.sidebar.markdown("---")

for q_key in QUESTIONS.keys():
    if st.sidebar.button(q_key, key=f"nav_{q_key}", use_container_width=True):
        st.session_state.selected_question = q_key
        st.session_state.show_result = False
        st.session_state.current_result = None

# Main content area
st.title("Smart grading")
st.markdown("---")

# Display selected question
current_question_id = st.session_state.selected_question
current_question_details = QUESTION_DETAILS[current_question_id]

st.header(f"{current_question_id}")
st.subheader(current_question_details['question'])

# Input section
st.markdown("### Your Answer")
text_answer = st.text_area("Enter your answer here or upload an image", height=150, key=f"text_{current_question_id}")

st.markdown("### Upload handwritten Answer")
uploaded_image = st.file_uploader("Choose an image...", type=['png', 'jpg', 'jpeg'], key=f"img_{current_question_id}")

# Display uploaded image
if uploaded_image is not None:
    image = Image.open(uploaded_image)
    st.image(image, caption="Uploaded Image", use_container_width=True)

# Evaluate button
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("🔍 Evaluate", type="primary", use_container_width=True):
        
        with st.spinner("Evaluating your answer..."):

            # Upload the image to GCP and return a signed url 
            # GCP Configuration
            service_account_path = os.environ.get("GEMINI_SERVICE_ACCOUNT_KEY")
            bucket_name = os.environ.get("GEMINI_BUCKET_NAME")

            # Upload image to GCP and generate signed URL if image exists
            if uploaded_image is not None:
                try:
                    # Create a unique filename using question_id and timestamp
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_extension = uploaded_image.name.split('.')[-1]
                    object_name = f"{current_question_id}_{timestamp}.{file_extension}"
                    
                    # Initialize GCP client and upload
                    client = storage.Client.from_service_account_json(service_account_path)
                    bucket = client.bucket(bucket_name)
                    blob = bucket.blob(object_name)
                    
                    # Upload the image
                    uploaded_image.seek(0)  # Reset file pointer
                    blob.upload_from_file(uploaded_image, content_type=uploaded_image.type)
                    
                    # Generate signed URL
                    signed_url = blob.generate_signed_url(
                        expiration=datetime.timedelta(hours=1),
                        version="v4",
                        method="GET"
                    )
                    
                    st.success(f"Image uploaded successfully!!")
                    
                except Exception as e:
                    st.error(f"Error uploading image to GCP: {e}")
                    signed_url = None
            
            # create test request
            test_request = SubmitQueryRequest(
            type =  current_question_details['type'],
            grade = current_question_details['grade'],
            max_marks = current_question_details['max_marks'],
            partial_marks_allowed = current_question_details['partial_marks_allowed'],
            subject = current_question_details['subject'],
            chapter = current_question_details['chapter'],
            question = current_question_details['question'],
            question_contains_figure = current_question_details['question_contains_figure'],
            image_description_for_question = current_question_details['image_description_for_question'],
            rubrics_for_extraction = current_question_details['rubrics_for_extraction'],
            rubrics_for_evaluation = current_question_details['rubrics_for_evaluation'],
            student_answer_typed = text_answer,
            handwritten = True,
            student_answer_image_urls = [signed_url],
            complexity = current_question_details['complexity'])

            response = submit_query_endpoint(request=test_request)

            score = response.mark  
            feedback = response.reason.criteria 
            
            # Store results
            st.session_state.current_result = {
                'score': score,
                'feedback': feedback,
                'answer': text_answer,
                'has_image': uploaded_image is not None
            }
            st.session_state.show_result = True
        st.rerun()
        

with col2:
    if st.button("🔄 Clear", use_container_width=True):
        st.session_state.show_result = False
        st.session_state.current_result = None
        st.rerun()

# Display results
if st.session_state.show_result and st.session_state.current_result:
    st.markdown("---")
    st.markdown("## 📊 Results")
    
    result = st.session_state.current_result
    
    # Score display
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Score", f"{result['score']}/{current_question_details['max_marks']}")
    
    # Feedback display
    st.markdown("### Feedback")
    # Convert to DataFrame
    df = pd.DataFrame(result['feedback'], columns=["Criteria", "Marks", "Feedback"])
    #dispaly table
    st.dataframe(df, use_container_width=True,hide_index=True)
    
    # Show submitted answer
    with st.expander("📝 View your submitted answer"):
        st.write(result['answer'])
        if result['has_image']:
            st.caption("✓ Image was uploaded with this answer")