""" Data Models"""

from pydantic import BaseModel, Field
from typing import Annotated, TypedDict, List, Dict, Any,  Optional

# class to accept input 
class SubmitQueryRequest(BaseModel):
    type : str = 'numerical_problem'
    grade : int = 12
    max_marks :float = 2
    partial_marks_allowed :bool = True
    subject : str = "Maths"
    chapter :str = "Applications of Integrals"
    question : str = "The volume of a sphere is increasing at the rate of 3 cm³/sec. Find the rate of increase of its surface area when the radius is 2 cm.\n"
    question_contains_figure: bool = False
    image_description_for_question: str = ""
    rubrics_for_extraction : str = "Step 1: Write the equation for volume, differentiate w.r.t time t, and solve for dr/dt \n Step 2: Write the equation for surface area, differentiate w.r.t time t, substitute dr/dt, and solve for ds/dt at r= 2cm"
    rubrics_for_evaluation: str = "Step 1: Write the equation for volume, differentiate w.r.t time t, and solve for dr/dt (1 mark) \n$V = \\frac{4}{3} \\pi r^3$\n$\\Rightarrow \\frac{dV}{dt} = 4\\pi r^2 \\left(\\frac{dr}{dt}\\right)$\n$\\Rightarrow \\frac{dr}{dt} = \\frac{3}{4\\pi r^2}$\nStep 2: Write the equation for surface area, differentiate w.r.t time t, substitute dr/dt, and solve for ds/dt at r= 2cm (1 mark)\n$S = 4\\pi r^2$\n$\\Rightarrow \\frac{dS}{dt} = 8\\pi r \\left(\\frac{dr}{dt}\\right)$\n$\\Rightarrow \\frac{dS}{dt} = 8\\pi r \\left(\\frac{3}{4\\pi r^2}\\right)$\n$\\Rightarrow \\left(\\frac{dS}{dt}\\right)_{r=2} = 3 \\text{ cm}^2/\\text{s}$\n"
    accepted_answer_contains_figure: bool = False 
    accepted_answer_figure_urls: list =[]
    student_answer_typed : str = ""
    handwritten: bool = True 
    student_answer_image_urls : list = ["https://smart-grading-test.s3.us-west-2.amazonaws.com/Vision_testing/259260_Incorrect+soln_Set+01.jpg"]
    complexity : str = "basic"

# class 
class Feedback(BaseModel):
    criteria: list[list[str]]

# state 
class State(TypedDict):
    question: SubmitQueryRequest
    student_answer_text: str
    solution_pathway : str
    reason_for_classification : str
    content_analysis : str
    feedback : Feedback
    value_points: dict 
    mark : float
    validation: bool = True
    retry_attempt : int = 0
    cost : float
    input_tokens : float
    output_tokens : float
    success: bool = True
    error_message: Optional[str] = None

# class to output through endpoint 
class QueryRepsonse(BaseModel):
    solution_pathway : Optional[str]
    reason : Optional[Feedback]
    value_points : Optional[dict]
    mark: Optional[float]
    extracted_answer : Optional[str]
    content_analysis : Optional[str]
    cost : float
    input_tokens: float
    output_tokens: float
    success: bool = True
    error_message: Optional[str] = None

# solution pathway analysis structure 
solution_pathway_classification = {
  "type": "object",
  "properties": {
    "solution_pathway": {
      "type": "string",
      "enum": ["standard_approach","acceptable_alternative_approach","irrelevant_approach"]
    },
    "reason_for_classification": {
        "type": "string",
        "description": "Concise reason for classification"
    }
  },
  "required": [
    "solution_pathway",
    "reason_for_classification"
  ]
}

# value point assesment structure 
value_point_assesment = {
  "type": "object",
  "properties": {
    "formulating": {
      "type": "string",
      "enum": ["Demonstrated Competence","Did Not Demonstrate Competence","Not Applicable"]
    },
    "employing": {
      "type": "string",
      "enum": ["Demonstrated Competence","Did Not Demonstrate Competence","Not Applicable"]
    },
    "interpreting_evaluating": {
      "type": "string",
      "enum": ["Demonstrated Competence","Did Not Demonstrate Competence","Not Applicable"]
    },
  },
  "required": [
    "formulating",
    "employing",
    "interpreting_evaluating"
  ]
}

# numerical response structure for (standard and alternate solution)
numeirical_response_structure= {
  "type": "object",
  "properties": {
    "criteria": {
      "type": "array",
      "description": "Contains array of steps mentioned in the content analysis",
      "items": {
        "type": "array",
        "description": "Contains deatils about grading each step[Concise Step ,Marks Given/Total Marks, ONE LINE CALLOUT of specific error if any or comment on correctness]",
        "items": {
          "type": "string"
        }
      },
      "minItems": 1,
      "maxItems": 6
    },
    "total_points": {
      "type": "array",
      "description": "Contains Total marks and concise over all feedback for the student answer [Total_Marks_Scored/Max_Marks, Overall Feedback]",
      "items": {
        "type": "string"
      },
      "minItems": 2,
      "maxItems": 2
    },
    "mark": {
      "type": "number",
      "format": "double"
    }
  },
  "required": [
    "criteria",
    "total_points",
    "mark"
  ]
}

# numerical response structre for irrlevant approach 
numeirical_response_structure_irrelevant= {
  "type": "object",
  "properties": {
    "criteria": {
      "type": "array",
      "description": "Contains array of with One or Zero Criteria mentioned in the content analysis",
      "items": {
        "type": "array",
        "description": "Contains deatils about grading for criteria [Criteria ,Partial Marks Given, ONE LINE CALL OUT against the Criteria on correctness/undertsanding ]",
        "items": {
          "type": "string"
        }
      },
      "minItems": 1,
      "maxItems": 6
    },
    "total_points": {
      "type": "array",
      "description": "Contains Total marks and concise over all feedback for the student answer [Total_Marks_Scored/Max_Marks, Overall Feedback(Reason of Incorrect solution)]",
      "items": {
        "type": "string"
      },
      "minItems": 2,
      "maxItems": 2
    },
    "mark": {
      "type": "number",
      "format": "double"
    }
  },
  "required": [
    "criteria",
    "total_points",
    "mark"
  ]
}

# response structure for textual 
response_structure_textual= {
  "type": "object",
  "properties": {
    "criteria": {
      "type": "array",
      "description": "Contains array of criteria mentioned in the GOLDEN STANDARD SOLUTION, focusing on the student's approach and understanding",
      "items": {
        "type": "array",
        "description": "Contains deatils about each criteria for grading[Criteria ,Marks Given/Total Marks, Student's Approach and Feedback]",
        "items": {
          "type": "string"
        }
      },
      "minItems": 1,
      "maxItems": 6
    },
    "total_points": {
      "type": "array",
      "description": "Contains Total marks and concise over all feedback for the student answer [Total_Marks_Scored/Max_Marks, Overall Feedback]",
      "items": {
        "type": "string"
      },
      "minItems": 2,
      "maxItems": 2
    },
    "mark": {
      "type": "number",
      "format": "double"
    }
  },
  "required": [
    "criteria",
    "total_points",
    "mark"
  ]
}