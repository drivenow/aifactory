from __future__ import annotations

from domain.codegen.agent_with_prompt import agent_factor_l3_cpp
from domain.codegen.agent_with_prompt import agent_factor_l3_py
from domain.codegen.agent_with_prompt import agent_factor_rayframe_py
from domain.codegen.agent_with_prompt import agent_semantic_check

build_l3_codegen_agent = agent_factor_l3_py.build_l3_codegen_agent
build_l3_py_user_message = agent_factor_l3_py.build_l3_py_user_message
invoke_l3_agent = agent_factor_l3_py.invoke_l3_agent

build_l3_cpp_codegen_agent = agent_factor_l3_cpp.build_l3_cpp_codegen_agent
invoke_l3_cpp_agent = agent_factor_l3_cpp.invoke_l3_cpp_agent

build_rayframe_codegen_agent = agent_factor_rayframe_py.build_rayframe_codegen_agent
build_rayframe_user_message = agent_factor_rayframe_py.build_rayframe_user_message
invoke_rayframe_agent = agent_factor_rayframe_py.invoke_rayframe_agent

build_semantic_agent = agent_semantic_check.build_semantic_agent
invoke_semantic_agent = agent_semantic_check.invoke_semantic_agent

__all__ = [
    "build_l3_codegen_agent",
    "build_l3_py_user_message",
    "invoke_l3_agent",
    "build_l3_cpp_codegen_agent",
    "invoke_l3_cpp_agent",
    "build_rayframe_codegen_agent",
    "build_rayframe_user_message",
    "invoke_rayframe_agent",
    "build_semantic_agent",
    "invoke_semantic_agent",
]
