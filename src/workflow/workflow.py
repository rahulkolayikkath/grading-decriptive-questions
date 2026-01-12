"""" 
Build the workflow using lang graph abstractions
"""

from typing import Annotated, TypedDict, Dict, List, Any
from .nodes import extractor, solution_pathway_analyzer ,content_analyzer, feedback_generator, value_point_analyzer
from .nodes import mark_validation, rerun_checker
from .nodes import State
from langgraph.graph import StateGraph, START, END

def build_workflow():
    # Build workflow  
    router_builder = StateGraph(State)
    # Add nodes
    router_builder.add_node("extractor", extractor)
    router_builder.add_node("solution_pathway_analyzer",solution_pathway_analyzer)
    router_builder.add_node("content_analyzer", content_analyzer)
    router_builder.add_node("feedback_generator", feedback_generator)
    router_builder.add_node("mark_validation", mark_validation)
    
    router_builder.add_node("value_point_analyzer", value_point_analyzer)
    # add edges to connect nodes
    router_builder.add_edge(START, "extractor")
    router_builder.add_edge("extractor", "solution_pathway_analyzer")
    router_builder.add_edge("solution_pathway_analyzer", "content_analyzer")
    router_builder.add_edge("content_analyzer", "feedback_generator")
    router_builder.add_edge("feedback_generator", "mark_validation")
    router_builder.add_conditional_edges(
    "mark_validation", rerun_checker,{"pass": "value_point_analyzer", "rerun": "feedback_generator"})
    router_builder.add_edge("value_point_analyzer", END)
    router_workflow = router_builder.compile()
    return router_workflow