"""
FIR (First Information Report) Template
For filing police complaints
"""

from typing import Dict, Any, Optional
from .base_template import BaseTemplate
from datetime import datetime


class FIRTemplate(BaseTemplate):
    """Template for generating FIR documents"""
    
    def __init__(self):
        super().__init__()
        self.document_type = "First Information Report (FIR)"
        
        self.required_fields = [
            'complainant_name',
            'complainant_address',
            'complainant_phone',
            'incident_date',
            'incident_time',
            'incident_location',
            'incident_description',
            'accused_description',
            'offense_type'
        ]
        
        self.optional_fields = [
            'complainant_email',
            'witness_details',
            'evidence_description',
            'property_lost',
            'injuries_sustained'
        ]
    
    def get_field_prompts(self) -> Dict[str, str]:
        """Return conversational prompts for each field"""
        return {
            'complainant_name': 'What is your full name (as per official documents)?',
            'complainant_address': 'What is your complete residential address?',
            'complainant_phone': 'What is your contact phone number?',
            'complainant_email': 'What is your email address? (optional)',
            'incident_date': 'On what date did the incident occur? (format: DD/MM/YYYY)',
            'incident_time': 'At what time did the incident occur? (format: HH:MM AM/PM)',
            'incident_location': 'Where exactly did the incident take place? (be specific with landmarks)',
            'incident_description': 'Please describe the incident in detail. What happened?',
            'accused_description': 'Can you describe the accused person(s)? Include physical features, clothing, or any identifying marks.',
            'offense_type': 'What type of offense occurred? (e.g., theft, assault, fraud, etc.)',
            'witness_details': 'Were there any witnesses? If yes, please provide their names and contact details. (optional)',
            'evidence_description': 'Is there any evidence? (e.g., photos, videos, documents) (optional)',
            'property_lost': 'Was any property lost or damaged? If yes, please describe. (optional)',
            'injuries_sustained': 'Were there any injuries sustained? If yes, please describe. (optional)'
        }
    
    def validate_field(self, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """Validate field values"""
        if not value or (isinstance(value, str) and not value.strip()):
            if field_name in self.required_fields:
                return False, f"{field_name} is required and cannot be empty"
            return True, None
        
        # Specific validations
        if field_name == 'complainant_phone':
            # Check if phone number has at least 10 digits
            digits = ''.join(filter(str.isdigit, str(value)))
            if len(digits) < 10:
                return False, "Phone number must contain at least 10 digits"
        
        elif field_name == 'complainant_email' and value:
            # Basic email validation
            if '@' not in str(value) or '.' not in str(value).split('@')[-1]:
                return False, "Invalid email format"
        
        elif field_name == 'incident_date':
            # Check date format
            try:
                datetime.strptime(str(value), '%d/%m/%Y')
            except ValueError:
                return False, "Invalid date format. Please use DD/MM/YYYY"
        
        elif field_name == 'complainant_name':
            if len(str(value)) < 3:
                return False, "Name must be at least 3 characters long"
        
        elif field_name == 'incident_description':
            if len(str(value)) < 50:
                return False, "Incident description must be at least 50 characters for a valid FIR"
        
        return True, None
    
    def generate_content(self) -> str:
        """Generate FIR document content"""
        content = []
        
        content.append("TO,")
        content.append("The Station House Officer")
        content.append("Police Station: _________________")
        content.append("")
        content.append("")
        
        content.append("SUBJECT: First Information Report")
        content.append("")
        content.append("")
        
        content.append("COMPLAINANT DETAILS:")
        content.append(f"Name: {self.fields.get('complainant_name', '[NOT PROVIDED]')}")
        content.append(f"Address: {self.fields.get('complainant_address', '[NOT PROVIDED]')}")
        content.append(f"Phone: {self.fields.get('complainant_phone', '[NOT PROVIDED]')}")
        if self.fields.get('complainant_email'):
            content.append(f"Email: {self.fields.get('complainant_email')}")
        content.append("")
        content.append("")
        
        content.append("INCIDENT DETAILS:")
        content.append(f"Date of Incident: {self.fields.get('incident_date', '[NOT PROVIDED]')}")
        content.append(f"Time of Incident: {self.fields.get('incident_time', '[NOT PROVIDED]')}")
        content.append(f"Place of Incident: {self.fields.get('incident_location', '[NOT PROVIDED]')}")
        content.append(f"Type of Offense: {self.fields.get('offense_type', '[NOT PROVIDED]')}")
        content.append("")
        content.append("")
        
        content.append("DESCRIPTION OF INCIDENT:")
        content.append(self.fields.get('incident_description', '[NOT PROVIDED]'))
        content.append("")
        content.append("")
        
        content.append("ACCUSED DESCRIPTION:")
        content.append(self.fields.get('accused_description', '[NOT PROVIDED]'))
        content.append("")
        content.append("")
        
        if self.fields.get('witness_details'):
            content.append("WITNESS DETAILS:")
            content.append(self.fields.get('witness_details'))
            content.append("")
            content.append("")
        
        if self.fields.get('evidence_description'):
            content.append("EVIDENCE:")
            content.append(self.fields.get('evidence_description'))
            content.append("")
            content.append("")
        
        if self.fields.get('property_lost'):
            content.append("PROPERTY LOST/DAMAGED:")
            content.append(self.fields.get('property_lost'))
            content.append("")
            content.append("")
        
        if self.fields.get('injuries_sustained'):
            content.append("INJURIES SUSTAINED:")
            content.append(self.fields.get('injuries_sustained'))
            content.append("")
            content.append("")
        
        content.append("I hereby declare that the above information is true and correct to the best of my knowledge and belief.")
        content.append("")
        content.append("")
        content.append("")
        content.append("Signature of Complainant")
        content.append(f"Name: {self.fields.get('complainant_name', '[NOT PROVIDED]')}")
        content.append(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        
        return '\n\n'.join(content)
