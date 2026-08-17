"""Kato World — brain_core package.

Modular decomposition of the brain (v0.2). Modules are pure-ish: they
import the monolith lazily inside functions to avoid circular imports.
The monolith (brain_server.py) remains the composition root / API layer.
"""
