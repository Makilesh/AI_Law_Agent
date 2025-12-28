"""
Affidavit Template
For sworn statements and declarations
"""

from typing import Dict, Any, Optional
from .base_template import BaseTemplate
from datetime import datetime


class AffidavitTemplate(BaseTemplate):
    """Template for generating affidavits"""
    
    def __init__(self):
        super().__init__()
        self.document_type = "Affidavit"
        
        self.required_fields = [
            'deponent_name',
            'deponent_age',
            'deponent_address',
            'deponent_occupation',
            'affidavit_purpose',
            'facts_statements',
            'verification_statement'
        ]
        
        self.optional_fields = [
            'case_number',
            'court_name',
            'additional_documents',
            'relationship_to_case'
        ]
    
    def get_field_prompts(self) -> Dict[str, str]:
        """Return conversational prompts for each field"""
        return {
            'deponent_name': 'What is your full name (the person making this affidavit)?',
            'deponent_age': 'What is your age?',
            'deponent_address': 'What is your complete residential address?',
            'deponent_occupation': 'What is your occupation?',
            'affidavit_purpose': 'What is the purpose of this affidavit? (e.g., name change, address proof, income certificate, etc.)',
            'facts_statements': 'Please state the facts you wish to declare. Be specific and detailed.',
            'verification_statement': 'Do you solemnly affirm that the contents of this affidavit are true? (Type "I solemnly affirm" to confirm)',
            'case_number': 'If this affidavit is for a court case, what is the case number? (optional)',
            'court_name': 'If this affidavit is for a court case, which court? (optional)',
            'additional_documents': 'Are you attaching any documents with this affidavit? If yes, please list them. (optional)',
            'relationship_to_case': 'What is your relationship to the matter/case? (optional)'
        }
    
    def validate_field(self, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """Validate field values"""
        if not value or (isinstance(value, str) and not value.strip()):
            if field_name in self.required_fields:
                return False, f"{field_name} is required and cannot be empty"
            return True, None
        
        # Specific validations
        if field_name == 'deponent_age':
            try:
                age = int(value)
                if age < 18 or age > 120:
                    return False, "Age must be between 18 and 120"
            except ValueError:
                return False, "Age must be a valid number"
        
        elif field_name == 'deponent_name':
            if len(str(value)) < 3:
                return False, "Name must be at least 3 characters long"
        
        elif field_name == 'facts_statements':
            if len(str(value)) < 50:
                return False, "Facts and statements must be detailed (at least 50 characters)"
        
        elif field_name == 'verification_statement':
            if 'affirm' not in str(value).lower():
                return False, "You must affirm the truthfulness of the statements"
        
        return True, None
    
    def generate_content(self) -> str:
        """Generate affidavit content"""
        content = []
        
        content.append("AFFIDAVIT")
        content.append("")
        content.append("")
        
        if self.fields.get('court_name') and self.fields.get('case_number'):
            content.append(f"IN THE COURT OF {self.fields.get('court_name')}")
            content.append(f"Case No.: {self.fields.get('case_number')}")
            content.append("")
            content.append("")
        
        content.append("I,")
        content.append(f"{self.fields.get('deponent_name', '[NOT PROVIDED]').upper()},")
        content.append(f"aged {self.fields.get('deponent_age', '[NOT PROVIDED]')} years,")
        content.append(f"occupation: {self.fields.get('deponent_occupation', '[NOT PROVIDED]')},")
        content.append(f"resident of {self.fields.get('deponent_address', '[NOT PROVIDED]')},")
        content.append("")
        content.append("do hereby solemnly affirm and state as under:")
        content.append("")
        content.append("")
        
        content.append(f"1. PURPOSE: {self.fields.get('affidavit_purpose', '[NOT PROVIDED]')}")
        content.append("")
        
        if self.fields.get('relationship_to_case'):
            content.append(f"2. RELATIONSHIP TO MATTER: {self.fields.get('relationship_to_case')}")
            content.append("")
        
        content.append("3. FACTS AND STATEMENTS:")
        content.append("")
        # Split facts into numbered points if they contain line breaks
        facts = self.fields.get('facts_statements', '[NOT PROVIDED]')
        if '\n' in facts:
            for i, fact in enumerate(facts.split('\n'), 1):
                if fact.strip():
                    content.append(f"   {i}. {fact.strip()}")
        else:
            content.append(f"   {facts}")
        content.append("")
        content.append("")
        
        if self.fields.get('additional_documents'):
            content.append("4. DOCUMENTS ATTACHED:")
            content.append(self.fields.get('additional_documents'))
            content.append("")
            content.append("")
        
        content.append("VERIFICATION")
        content.append("")
        content.append(f"I, {self.fields.get('deponent_name', '[NOT PROVIDED]')}, the deponent above-named, do hereby verify that the contents of this affidavit are true and correct to the best of my knowledge and belief, and nothing material has been concealed therefrom.")
        content.append("")
        content.append("")
        content.append("Verified at _________________ on this _____ day of _____________, _____.")
        content.append("")
        content.append("")
        content.append("")
        content.append("_______________________")
        content.append("DEPONENT")
        content.append(f"({self.fields.get('deponent_name', '[NOT PROVIDED]')})")
        content.append("")
        content.append("")
        content.append("")
        content.append("SOLEMNLY AFFIRMED AND SIGNED")
        content.append("before me on this _____ day of _____________, _____.")
        content.append("")
        content.append("")
        content.append("")
        content.append("_______________________")
        content.append("NOTARY PUBLIC / OATH COMMISSIONER")
        content.append("Seal:")
        
        return '\n\n'.join(content)
