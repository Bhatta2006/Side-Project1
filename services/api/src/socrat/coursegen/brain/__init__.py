"""The course brain: subject roots, request specs, and serving an existing course when one
already fits (docs/implementation/course-brain-plan.md). Off unless ``course_brain``."""

from socrat.coursegen.brain.route import Decision, attach, built, granted, joined, route

__all__ = ["Decision", "attach", "built", "granted", "joined", "route"]
