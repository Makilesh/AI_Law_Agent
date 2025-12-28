"""
Document Templates Package
Provides templates for generating legal documents
"""

from .base_template import BaseTemplate
from .fir_template import FIRTemplate
from .bail_template import BailTemplate
from .affidavit_template import AffidavitTemplate
from .complaint_template import ComplaintTemplate
from .legal_notice_template import LegalNoticeTemplate

__all__ = [
    'BaseTemplate',
    'FIRTemplate',
    'BailTemplate',
    'AffidavitTemplate',
    'ComplaintTemplate',
    'LegalNoticeTemplate'
]
