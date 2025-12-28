"""
Legal Complaint Template
For filing formal complaints in civil matters
"""

from typing import Dict, Any, Optional
from .base_template import BaseTemplate
from datetime import datetime


class ComplaintTemplate(BaseTemplate):
    """Template for generating legal complaints"""
    
    def __init__(self):
        super().__init__()
        self.document_type = "Legal Complaint"
        
        self.required_fields = [
            'complainant_name',
            'complainant_address',
            'complainant_phone',
            'respondent_name',
            'respondent_address',
            'nature_of_dispute',
            'facts_of_case',
            'relief_sought',
            'jurisdiction_reason'
        ]
        
        self.optional_fields = [
            'complainant_email',
            'respondent_phone',
            'date_of_cause',
            'monetary_value',
            'previous_correspondence',
            'witness_list',
            'documents_list'
        ]
    
    def get_field_prompts(self) -> Dict[str, str]:
        """Return conversational prompts for each field"""
        return {
            'complainant_name': 'What is your full name (complainant)?',
            'complainant_address': 'What is your complete address?',
            'complainant_phone': 'What is your contact phone number?',
            'complainant_email': 'What is your email address? (optional)',
            'respondent_name': 'What is the name of the person/entity you are complaining against?',
            'respondent_address': 'What is the address of the respondent?',
            'respondent_phone': 'What is the phone number of the respondent? (optional)',
            'nature_of_dispute': 'What is the nature of the dispute? (e.g., breach of contract, property dispute, consumer complaint, etc.)',
            'date_of_cause': 'When did the cause of action arise? (format: DD/MM/YYYY) (optional)',
            'facts_of_case': 'Please describe the facts of the case in detail. What happened and when?',
            'relief_sought': 'What relief or remedy are you seeking from the court? (e.g., compensation, specific performance, injunction, etc.)',
            'monetary_value': 'If seeking monetary compensation, what is the amount? (optional)',
            'jurisdiction_reason': 'Why is this court appropriate for this matter? (e.g., location of dispute, value of claim, etc.)',
            'previous_correspondence': 'Have you sent any legal notice or attempted to resolve this matter earlier? (optional)',
            'witness_list': 'Do you have any witnesses? Please list their names. (optional)',
            'documents_list': 'What documents will you be attaching as evidence? (optional)'
        }
    
    def validate_field(self, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """Validate field values"""
        if not value or (isinstance(value, str) and not value.strip()):
            if field_name in self.required_fields:
                return False, f"{field_name} is required and cannot be empty"
            return True, None
        
        # Specific validations
        if field_name in ['complainant_phone', 'respondent_phone']:
            digits = ''.join(filter(str.isdigit, str(value)))
            if len(digits) < 10:
                return False, "Phone number must contain at least 10 digits"
        
        elif field_name == 'complainant_email' and value:
            if '@' not in str(value) or '.' not in str(value).split('@')[-1]:
                return False, "Invalid email format"
        
        elif field_name == 'date_of_cause' and value:
            try:
                datetime.strptime(str(value), '%d/%m/%Y')
            except ValueError:
                return False, "Invalid date format. Please use DD/MM/YYYY"
        
        elif field_name in ['complainant_name', 'respondent_name']:
            if len(str(value)) < 3:
                return False, "Name must be at least 3 characters long"
        
        elif field_name == 'facts_of_case':
            if len(str(value)) < 100:
                return False, "Facts of the case must be detailed (at least 100 characters)"
        
        elif field_name == 'relief_sought':
            if len(str(value)) < 20:
                return False, "Relief sought must be clearly stated (at least 20 characters)"
        
        return True, None
    
    def generate_content(self) -> str:
        """Generate complaint content"""
        content = []
        
        content.append("BEFORE THE HON'BLE COURT")
        content.append("[Court Name and Jurisdiction]")
        content.append("")
        content.append("")
        
        content.append("CIVIL COMPLAINT")
        content.append("")
        content.append("")
        
        content.append("IN THE MATTER OF:")
        content.append("")
        content.append(f"{self.fields.get('complainant_name', '[NOT PROVIDED]')}")
        content.append(f"Address: {self.fields.get('complainant_address', '[NOT PROVIDED]')}")
        content.append(f"Phone: {self.fields.get('complainant_phone', '[NOT PROVIDED]')}")
        if self.fields.get('complainant_email'):
            content.append(f"Email: {self.fields.get('complainant_email')}")
        content.append("........ COMPLAINANT")
        content.append("")
        content.append("VERSUS")
        content.append("")
        content.append(f"{self.fields.get('respondent_name', '[NOT PROVIDED]')}")
        content.append(f"Address: {self.fields.get('respondent_address', '[NOT PROVIDED]')}")
        if self.fields.get('respondent_phone'):
            content.append(f"Phone: {self.fields.get('respondent_phone')}")
        content.append("........ RESPONDENT")
        content.append("")
        content.append("")
        
        content.append("COMPLAINT UNDER [Relevant Section/Act]")
        content.append("")
        content.append("")
        
        content.append("TO,")
        content.append("The Hon'ble [Court Name]")
        content.append("")
        content.append("")
        
        content.append("THE HUMBLE COMPLAINT OF THE COMPLAINANT ABOVE-NAMED MOST RESPECTFULLY SHOWETH:")
        content.append("")
        content.append("")
        
        content.append(f"1. NATURE OF DISPUTE: {self.fields.get('nature_of_dispute', '[NOT PROVIDED]')}")
        content.append("")
        
        if self.fields.get('date_of_cause'):
            content.append(f"2. DATE OF CAUSE OF ACTION: {self.fields.get('date_of_cause')}")
            content.append("")
        
        content.append("3. FACTS OF THE CASE:")
        content.append("")
        # Format facts with proper paragraphing
        facts = self.fields.get('facts_of_case', '[NOT PROVIDED]')
        if '\n' in facts:
            for fact in facts.split('\n'):
                if fact.strip():
                    content.append(f"   {fact.strip()}")
        else:
            content.append(f"   {facts}")
        content.append("")
        content.append("")
        
        if self.fields.get('previous_correspondence'):
            content.append("4. PREVIOUS CORRESPONDENCE/ATTEMPTS AT RESOLUTION:")
            content.append(self.fields.get('previous_correspondence'))
            content.append("")
            content.append("")
        
        if self.fields.get('monetary_value'):
            content.append(f"5. MONETARY VALUE OF CLAIM: Rs. {self.fields.get('monetary_value')}")
            content.append("")
        
        content.append("6. JURISDICTION:")
        content.append(self.fields.get('jurisdiction_reason', '[NOT PROVIDED]'))
        content.append("")
        content.append("")
        
        if self.fields.get('witness_list'):
            content.append("7. LIST OF WITNESSES:")
            content.append(self.fields.get('witness_list'))
            content.append("")
            content.append("")
        
        if self.fields.get('documents_list'):
            content.append("8. LIST OF DOCUMENTS:")
            content.append(self.fields.get('documents_list'))
            content.append("")
            content.append("")
        
        content.append("PRAYER:")
        content.append("")
        content.append("In light of the facts and circumstances stated above, it is most humbly prayed that this Hon'ble Court may be pleased to:")
        content.append("")
        content.append(f"a) {self.fields.get('relief_sought', '[NOT PROVIDED]')}")
        content.append("")
        content.append("b) Award costs of this complaint to the complainant;")
        content.append("")
        content.append("c) Pass any other order or direction as this Hon'ble Court may deem fit and proper in the interest of justice.")
        content.append("")
        content.append("")
        content.append("AND FOR THIS ACT OF KINDNESS, THE COMPLAINANT SHALL DUTY BOUND FOREVER PRAY.")
        content.append("")
        content.append("")
        content.append("")
        content.append("_______________________")
        content.append("COMPLAINANT")
        content.append(f"({self.fields.get('complainant_name', '[NOT PROVIDED]')})")
        content.append("")
        content.append("")
        content.append("Through:")
        content.append("_______________________")
        content.append("Advocate")
        content.append("")
        content.append(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        content.append("Place: _________________")
        
        return '\n\n'.join(content)
