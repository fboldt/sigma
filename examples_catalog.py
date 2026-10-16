"""
example_catalog.py
------------------
Central catalog of available example modules.
Each entry maps a string key to its corresponding example implementation.
"""
from examples import echo, python_version, sum

available_examples = {
    "python_version": python_version, # exemplo sem parâmetros
    "echo": echo, # exemplo com um parâmetro 
    "sum": sum, # exemplo com dois parâmetros
}
