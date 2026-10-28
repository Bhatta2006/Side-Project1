"""The harness: Socrat's engine of verified capabilities.

A language model can write, explain and ask, but it can be wrong. The harness is the part that
is not: deterministic *capabilities* (check a derivation, run code, check units, later run a
simulation or a CAD constraint) with typed inputs and outputs, run in a sandbox with a time
limit. Everything else calls them through one contract:

- the tutor and the builder agents get them as tools, so they check before they claim;
- the builder's gates call them directly, so generated content is verified by code;
- the learner-facing studios call them to grade work and write evidence.

The model behind any of those is replaceable (see ``coursegen.roles``); the capabilities are
the product. A new studio adds capabilities here, not special cases elsewhere.
"""

from socrat.harness.registry import Capability, Result, call, capabilities, register

__all__ = ["Capability", "Result", "call", "capabilities", "register"]
