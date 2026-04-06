"""Evidence-grounded CV extraction pipeline.

Parallel pipeline focused on traceable extraction for resumes/CVs.
"""

from .pipeline.runner import run_cv_pipeline

__all__ = ["run_cv_pipeline"]