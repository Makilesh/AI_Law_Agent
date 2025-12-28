"""
Base template class for legal document generation
Provides common structure and methods for all document types
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import json


class BaseTemplate(ABC):
    """Base class for all legal document templates"""
    
    def __init__(self):
        self.fields = {}
        self.required_fields = []
        self.optional_fields = []
        self.document_type = "Generic Legal Document"
        self.completion_status = {}
        
    @abstractmethod
    def get_field_prompts(self) -> Dict[str, str]:
        """
        Return dictionary of field names and their conversational prompts
        Example: {'complainant_name': 'What is your full name?'}
        """
        pass
    
    @abstractmethod
    def validate_field(self, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a field value
        Returns: (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def generate_content(self) -> str:
        """
        Generate the document content as plain text
        Returns formatted text content
        """
        pass
    
    def set_field(self, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """
        Set a field value after validation
        Returns: (success, error_message)
        """
        is_valid, error = self.validate_field(field_name, value)
        if is_valid:
            self.fields[field_name] = value
            self.completion_status[field_name] = True
            return True, None
        return False, error
    
    def get_field(self, field_name: str) -> Optional[Any]:
        """Get field value"""
        return self.fields.get(field_name)
    
    def get_next_required_field(self) -> Optional[str]:
        """Get next unfilled required field"""
        for field in self.required_fields:
            if field not in self.fields or not self.completion_status.get(field, False):
                return field
        return None
    
    def get_completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if not self.required_fields:
            return 100.0
        completed = sum(1 for field in self.required_fields if self.completion_status.get(field, False))
        return (completed / len(self.required_fields)) * 100
    
    def is_complete(self) -> bool:
        """Check if all required fields are filled"""
        return all(self.completion_status.get(field, False) for field in self.required_fields)
    
    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields"""
        return [field for field in self.required_fields if not self.completion_status.get(field, False)]
    
    def generate_docx(self, output_path: str) -> bool:
        """
        Generate DOCX file
        Returns: success status
        """
        try:
            doc = Document()
            
            # Set document margins
            sections = doc.sections
            for section in sections:
                section.top_margin = Inches(1)
                section.bottom_margin = Inches(1)
                section.left_margin = Inches(1)
                section.right_margin = Inches(1)
            
            # Add title
            title = doc.add_paragraph()
            title_run = title.add_run(self.document_type.upper())
            title_run.bold = True
            title_run.font.size = Pt(16)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            doc.add_paragraph()  # Blank line
            
            # Add content
            content = self.generate_content()
            paragraphs = content.split('\n\n')
            
            for para_text in paragraphs:
                if para_text.strip():
                    para = doc.add_paragraph()
                    run = para.add_run(para_text.strip())
                    run.font.size = Pt(12)
                    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # Add footer with generation date
            doc.add_paragraph()
            footer = doc.add_paragraph()
            footer_run = footer.add_run(f"\n\nGenerated on: {datetime.now().strftime('%B %d, %Y')}")
            footer_run.font.size = Pt(10)
            footer_run.italic = True
            footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            
            # Save document
            doc.save(output_path)
            return True
            
        except Exception as e:
            print(f"Error generating DOCX: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template state to dictionary"""
        return {
            'document_type': self.document_type,
            'fields': self.fields,
            'required_fields': self.required_fields,
            'optional_fields': self.optional_fields,
            'completion_status': self.completion_status,
            'completion_percentage': self.get_completion_percentage(),
            'is_complete': self.is_complete(),
            'missing_fields': self.get_missing_fields()
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Load template state from dictionary"""
        self.fields = data.get('fields', {})
        self.completion_status = data.get('completion_status', {})
    
    def get_preview(self) -> str:
        """
        Generate preview of document with current fields
        Shows placeholders for missing fields
        """
        if not self.is_complete():
            preview = f"PREVIEW - {self.document_type}\n"
            preview += "=" * 50 + "\n\n"
            preview += "This document is incomplete. Missing fields:\n"
            for field in self.get_missing_fields():
                prompts = self.get_field_prompts()
                preview += f"- {field}: {prompts.get(field, 'Not specified')}\n"
            preview += "\n" + "=" * 50 + "\n\n"
        else:
            preview = ""
        
        preview += self.generate_content()
        return preview
    
    def clear_fields(self):
        """Clear all field values"""
        self.fields = {}
        self.completion_status = {}
