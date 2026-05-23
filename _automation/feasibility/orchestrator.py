"""
Entry point for the feasibility pipeline.
Reads a promising/*.md hypothesis file, classifies it via the handler registry,
dispatches to the appropriate handler, and writes the result to tested/.
"""
