""" State and node defenitions """

# project root for imports 
from pathlib import Path
graph_dir = Path(__file__).parent
project_root = graph_dir.parent 

from typing import Annotated, TypedDict, List, Dict, Any
from config import system_prompts, format_user_prompt

from dotenv import load_dotenv
load_dotenv()

from src.llm import GeminiClient

from .datamodels import State, Feedback 
from .datamodels import numeirical_response_structure, response_structure_textual, solution_pathway_classification

from.datamodels import numeirical_response_structure_irrelevant, value_point_assesment
import logging
logger = logging.getLogger(__name__) 


def extractor(state:State):
    """ Extract the answers from image"""
    question = state['question']
    # if handwriten -> extract else skip 
    if question.handwritten == False:
        return {
            "student_answer_text": question.student_answer_typed,
            "success": True}
    print(f"|| Extracting Student answer ...||")
    if question.type == 'numerical_problem':
        system_prompt_extraction = system_prompts["extraction_numerical_prompt"] 
        user_prompt_extraction = format_user_prompt("extraction_numerical_prompt")
    elif question.type == 'textual_answer':
        system_prompt_extraction = system_prompts["extraction_textual_prompt"]
        user_prompt_extraction = format_user_prompt("extraction_textual_prompt")
    elif question.type == 'image_answer':
        system_prompt_extraction = system_prompts["extraction_textual_prompt_image"]
        user_prompt_extraction = format_user_prompt("extraction_textual_prompt_image")
    
    # Model Selection 
    extractor_model = GeminiClient(model = "gemini-2.0-flash") #default model for text extraction
    if question.type == 'image_answer':
        # if the question is image answer, we use the gemini pro model
        extractor_model = GeminiClient(model = "gemini-2.5-pro")

    response = extractor_model.generate(system_prompt= system_prompt_extraction, user_prompt= user_prompt_extraction,  images= question.student_answer_image_urls)

    # Handle the error cases 
    if not response.success:
        logger.error(f"Extraction failed: {response.error_message}")
        # Return error state that can be handled by the workflow
        return {
            "student_answer_text": None,
            "input_tokens": 0, 
            "output_tokens": 0,
            "cost": 0.0,
            "success": False,
            "error_message": f"Extraction failed: {response.error_message}"
        }
    
    return {"student_answer_text": response.content,
            "input_tokens": response.input_tokens, 
            "output_tokens": response.output_tokens,
            "cost": response.cost,
            "success": True}

def solution_pathway_analyzer(state:State):
    """Analyse the content from the students work, classify the solution """
    if state['success'] == False:
        # if the previous step failed, we can skip this step
        logger.error("Solution Pathway Analysis skipped due to previous step failure.")
        return {"solution_pathway": None,
            "reason_for_classification": None,}
    question = state['question']
    # if textual answer, we dont need this step 
    if question.type == 'textual_answer' or question.type == 'image_answer':
        return {"solution_pathway": "NA"}
    print(f"|| Solution pathway analysis ...||")
    system_prompt_solution_pathway_analysis = system_prompts["solution_pathway_analysis_numerical_prompt"]
    # if question contain figure 
    if question.question_contains_figure:
        question_text = f"""
        {question.question}
        Question also conatin an figure/image which can be described as follows.
        {question.image_description_for_question}"""
    else: 
        question_text = question.question
    
    # student answer contains image
    if question.handwritten:
        student_answer_text  = f"""
        Here is the extracted content from the students handwritten work,
        {state["student_answer_text"]}"""
    else:
        student_answer_text = question.student_answer_typed
    
    # format user prompt 
    user_prompt_solution_pathway_analysis = format_user_prompt(
        "solution_pathway_analysis_numerical_prompt",
        grade_level = question.grade,
        subject = question.subject,
        chapter = question.chapter,
        question = question_text,
        steps_description = question.rubrics_for_extraction,
        student_answer = student_answer_text,
    )
    solution_pathway_analysis_model = GeminiClient(model = "gemini-2.0-flash")
    response = solution_pathway_analysis_model.generate_structured_response(system_prompt= system_prompt_solution_pathway_analysis,user_prompt= user_prompt_solution_pathway_analysis, structure= solution_pathway_classification)
    
    # Handle the error cases 
    if not response.success:
        logger.error(f"Solution Pathway Analysis failed: {response.error_message}")
        # Return error state that can be handled by the workflow
        return {
            "solution_pathway": None,
            "reason_for_classification": None,
            "success": False,
            "error_message": f"Solution Pathway Analysis failed: {response.error_message}"
        }
    
    # update the cost vitals 
    input_tokens = state.get("input_tokens", 0) + response.input_tokens
    output_tokens = state.get("output_tokens", 0) + response.output_tokens
    cost = state.get("cost", 0)+ response.cost

    return {
        "solution_pathway": response.structure["solution_pathway"],
        "reason_for_classification": response.structure["reason_for_classification"],
        "input_tokens": input_tokens,  
        "output_tokens": output_tokens,
        "cost": cost,
        "success": True
    }

def content_analyzer(state:State):
    """Analyse the content from the students work, output natural lanaguage response """
    
    if state['success'] == False:
        # if the previous step failed, we dont need to continue 
        logger.error("Content Analysis skipped due to previous step failure.")
        return {"content_analysis": None}
    question = state['question']
    print(f"|| Analysing Student answer ...||")
    if question.type == 'textual_answer' or question.type == 'image_answer':
        system_prompt_content_analysis = system_prompts["content_analysis_textual_prompt"]
    elif question.type == 'numerical_problem':
        system_prompt_content_analysis = system_prompts["content_analysis_standard_numerical_prompt"]
    # if question contain figure 
    if question.question_contains_figure:
        question_text = f"""
        {question.question}
        Question also conatin an figure/image which can be described as follows.
        {question.image_description_for_question}"""
    else: 
        question_text = question.question
    
    # student answer contains image
    if question.handwritten:
        student_answer_text  = f"""
        Here is the extracted content from the students handwritten work,
        {state["student_answer_text"]}"""
    else:
        student_answer_text = question.student_answer_typed
    
    if question.type == 'textual_answer' or question.type == 'image_answer':
        user_prompt_content_analysis = format_user_prompt(
            "content_analysis_textual_prompt",
            grade_level = question.grade,
            subject = question.subject,
            chapter = question.chapter,
            question = question_text,
            sample_solution_with_mark_breakdown = question.rubrics_for_evaluation,
            student_answer = student_answer_text
        )
    
    # if question is numerical problem, we need to classify based solution pathway
    else: 
        if state["solution_pathway"] == "standard_approach":
            user_prompt_content_analysis = format_user_prompt(
                "content_analysis_standard_numerical_prompt",
                grade_level = question.grade,
                subject = question.subject,
                chapter = question.chapter,
                question = question_text,
                steps_description = question.rubrics_for_extraction,
                sample_solution_with_steps = question.rubrics_for_evaluation,
                student_answer = student_answer_text,
                reason_for_classification = state["reason_for_classification"]
            )
        elif state["solution_pathway"] == "irrelevant_approach": 
            user_prompt_content_analysis = format_user_prompt(
                "content_analysis_irrelevant_numerical_prompt",
                grade_level = question.grade,
                subject = question.subject,
                chapter = question.chapter,
                question = question_text,
                steps_description = question.rubrics_for_extraction,
                sample_solution_with_steps = question.rubrics_for_evaluation,
                student_answer = student_answer_text,
                reason_for_classification = state["reason_for_classification"]
            )
        elif state["solution_pathway"] == "acceptable_alternative_approach": 
            user_prompt_content_analysis = format_user_prompt(
                "content_analysis_alternative_numerical_prompt",
                grade_level = question.grade,
                subject = question.subject,
                chapter = question.chapter,
                question = question_text,
                steps_description = question.rubrics_for_extraction,
                sample_solution_with_steps = question.rubrics_for_evaluation,
                student_answer = student_answer_text,
                reason_for_classification = state["reason_for_classification"]
            )
    
    # chose the model based on complexity 
    if question.complexity == "basic":
        content_analysis_model = GeminiClient(model = "gemini-2.0-flash")
    elif question.complexity == "moderate":
        content_analysis_model = GeminiClient(model = "gemini-2.5-flash")
    elif question.complexity == "advanced":
        content_analysis_model = GeminiClient(model = "gemini-2.5-pro")
    
    # upgrade the model if its acceptable_alternative_approach
    if state['solution_pathway'] == "acceptable_alternative_approach":
        content_analysis_model = GeminiClient(model = "gemini-2.5-flash")

    response = content_analysis_model.generate(system_prompt= system_prompt_content_analysis,user_prompt= user_prompt_content_analysis)
    print( f"Content analysis model: {response.model}")
    # Handle the error cases 
    if not response.success:
        logger.error(f"Content Analysis failed: {response.error_message}")
        # Return error state that can be handled by the workflow
        return {
            "content_analysis": None,
            "success": False,
            "error_message": f"Content Analysis failed: {response.error_message}"
        }
    
    # update the cost vitals 
    input_tokens = state.get("input_tokens", 0) + response.input_tokens
    output_tokens = state.get("output_tokens", 0) + response.output_tokens
    cost = state.get("cost", 0)+ response.cost

    return {
        "content_analysis": response.content,
        "input_tokens": input_tokens, 
        "output_tokens": output_tokens,
        "cost": cost,
        "success": True
    }

def feedback_generator(state:State):
    """Grades the student and provides feedback"""
    if state.get('success', False) == False:
        # if the previous step failed, we dont need to continue 
        logger.error("Feedback Generation skipped due to previous step failure.")
        return {
            "feedback": None,
            "mark": None}
    print(f"|| Generating feedback...||")
    question = state['question']
    if question.type == "numerical_problem":
        system_prompt_feedback_generation  = system_prompts["feedback_generation_numerical_prompt"]
    elif question.type == 'textual_answer' or question.type == 'image_answer':
        system_prompt_feedback_generation  = system_prompts["feedback_generation_textual_prompt"]

    # if question contain figure 
    if question.question_contains_figure:
        question_text = f"""
        {question.question}
        Question also conatin an figure/image which can be described as follows.
        {question.image_description_for_question}"""
    else: 
        question_text = question.question 

    # if question is numerical problem, we need to classify based solution pathway
    if question.type == "numerical_problem":
        if state["solution_pathway"] =="standard_approach":
            user_prompt_feedback_generation = format_user_prompt(
                "feedback_generation_standard_numerical_prompt",
                question = question_text,
                max_marks = question.max_marks,
                grade_level = question.grade,
                subject = question.subject,
                chapter = question.chapter,
                content_analysis_output = state["content_analysis"])
            response_structure = numeirical_response_structure
        elif state["solution_pathway"] == "irrelevant_approach":
            user_prompt_feedback_generation = format_user_prompt(
                "feedback_generation_irrelevant_numerical_prompt",
                question = question_text,
                max_marks = question.max_marks,
                grade_level = question.grade,
                subject = question.subject,
                chapter = question.chapter,
                content_analysis_output = state["content_analysis"],
                reason_for_classification = state["reason_for_classification"])
            response_structure = numeirical_response_structure_irrelevant
        elif state["solution_pathway"] == "acceptable_alternative_approach":
            user_prompt_feedback_generation = format_user_prompt(
                "feedback_generation_alternative_numerical_prompt",
                question = question_text,
                max_marks = question.max_marks,
                grade_level = question.grade,
                subject = question.subject,
                chapter = question.chapter,
                content_analysis_output = state["content_analysis"])
            response_structure = numeirical_response_structure
        
    elif question.type == 'textual_answer' or question.type == 'image_answer':
        user_prompt_feedback_generation = format_user_prompt(
            "feedback_generation_textual_prompt",
            question = question_text,
            max_marks = question.max_marks,
            grade_level = question.grade,
            subject = question.subject,
            chapter = question.chapter,
            content_analysis_output = state["content_analysis"],)
        response_structure = response_structure_textual
    
    # choose the model based on complexity 
    if question.complexity == "basic":
        feedback_generation_model = GeminiClient(model = "gemini-2.0-flash")
    elif question.complexity == "moderate":
        feedback_generation_model = GeminiClient(model = "gemini-2.5-flash")
    elif question.complexity == "advanced":
        feedback_generation_model = GeminiClient(model = "gemini-2.5-pro")
    
    # upgrade the model if its acceptable_alternative_approach
    if state['solution_pathway'] == "acceptable_alternative_approach":
        feedback_generation_model = GeminiClient(model = "gemini-2.5-flash")

    response = feedback_generation_model.generate_structured_response(system_prompt= system_prompt_feedback_generation, user_prompt= user_prompt_feedback_generation, structure= response_structure)
    
    print( f"Feedback generation model: {response.model}")
    # Handle the error cases 
    if not response.success:
        logger.error(f"Feedback Generation failed: {response.error_message}")
        # Return error state that can be handled by the workflow
        return {
            "feedback": None,
            "mark": None,
            "success": False,
            "error_message": f"Feedback Generation failed: {response.error_message}"
        }
    
    # update the cost vitals 
    input_tokens = state.get("input_tokens", 0) + response.input_tokens
    output_tokens = state.get("output_tokens", 0) + response.output_tokens
    cost = state.get("cost", 0)+ response.cost

    # update the criteria list
    creterias = response.structure["criteria"]
    creterias.append(["Total"] + response.structure["total_points"])

    feedback = Feedback(
        criteria = creterias
    )
    return {
        "feedback": feedback,
        "mark": response.structure["mark"],
        "input_tokens": input_tokens, 
        "output_tokens": output_tokens,
        "success": True,
        "cost": cost
    } 

def mark_validation(state:State):
    """ Validate the mark give by the feedback generator"""
    if state.get('success', False) == False:
        # if the previous step failed, we dont need to continue 
        logger.error("Feedback Generation skipped due to previous step failure.")
        return {
            "validation": True}
    question = state['question']
    print(f"|| Validating marks and checks for rerun ...||")
    if state['mark'] > question.max_marks:
        retry_attempt = state.get("retry_attempt", 0) + 1
        logger.error(f"Mark {state['mark']} exceeds the maximum allowed {question.max_marks}.")
        return {"retry_attempt": retry_attempt, "validation": False }
    return {"validation": True}

def rerun_checker(state:State):
    """ Checks if the validation failed and requires re-run"""
    # case 1 - pass with no errors
    if state['validation']== True:
        print("|| Validation passed, no re-run required ||")
        return "pass"
    # case 2 to validation failed but ran out of retries
    elif state['validation'] == False and state.get('retry_attempt', 0) == 2:
        print("|| Validation Failed, no re-run allowed ||")
        return "pass"
    # case 2 - validation failed and reattempt < allowed
    elif state['validation'] == False and state.get('retry_attempt', 0) == 1:
        print("|| Validation Failed, re-run allowed ||")
        return "rerun"

def value_point_analyzer(state:State):
    """Analyse the value point in the student's answer"""
    if state['success'] == False:
        # if the previous step failed, we dont need to continue 
        logger.error("Value Point Analysis skipped due to previous step failure.")
        return {"value_points": None}
    
    question = state['question']
    # if the question is textual answer, we dont need this step
    if question.type == 'textual_answer' or question.type == 'image_answer':
        return {"value_points": {'formulating': 'NA', 'employing': 'NA', 'interpreting_evaluating': 'NA'}}
    print(f"|| Checking for Value points...||")
    system_prompt_value_point_assesment = system_prompts["value_point_assesment_prompt"]

    # if question contain figure 
    if question.question_contains_figure:
        question_text = f"""
        {question.question}
        Question also conatin an figure/image which can be described as follows.
        {question.image_description_for_question}"""
    else: 
        question_text = question.question

    #format user_prompt
    user_prompt_value_point_assesment = format_user_prompt(
        "value_point_assesment_prompt",
        question = question_text,
        max_marks = question.max_marks,
        grade_level = question.grade,
        subject = question.subject,
        chapter = question.chapter,
        content_analysis_output = state["content_analysis"])
    
    response_structure = value_point_assesment
    value_point_assesment_model = GeminiClient(model = "gemini-2.0-flash")   

    response = value_point_assesment_model.generate_structured_response(system_prompt= system_prompt_value_point_assesment, user_prompt= user_prompt_value_point_assesment, structure= response_structure)
    # Handle the error cases 
    if not response.success:
        logger.error(f"Value point analysis failed: {response.error_message}")
        
        # Return error state that can be handled by the workflow
        return {
            "value_points": None,
            "success": False,
            "error_message": f"Value point analysis failed: {response.error_message}"
        }

    # update the cost vitals 
    input_tokens = state.get("input_tokens", 0) + response.input_tokens
    output_tokens = state.get("output_tokens", 0) + response.output_tokens
    cost = state.get("cost", 0.0)+ response.cost

    return {
        "value_points": response.structure,
        "input_tokens": input_tokens, 
        "output_tokens": output_tokens,
        "cost": cost,
        "sucess": True
    } 

    
    
