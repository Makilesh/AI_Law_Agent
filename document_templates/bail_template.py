"""
Bail Application Template
For applying for bail in criminal cases
"""

from typing import Dict, Any, Optional
from .base_template import BaseTemplate
from datetime import datetime


class BailTemplate(BaseTemplate):
    """Template for generating bail applications"""
    
    def __init__(self):
        super().__init__()
        self.document_type = "Bail Application"
        
        self.required_fields = [
            'applicant_name',
            'applicant_age',
            'applicant_address',
            'case_number',
            'court_name',
            'offense_charged',
            'arrest_date',
            'grounds_for_bail',
            'surety_name',
            'surety_address'
        ]
        
        self.optional_fields = [
            'applicant_occupation',
            'family_details',
            'previous_criminal_record',
            'health_conditions',
            'employment_proof'
        ]
    
    def get_field_prompts(self) -> Dict[str, str]:
        """Return conversational prompts for each field"""
        return {
            'applicant_name': 'What is the full name of the person seeking bail?',
            'applicant_age': 'What is the age of the applicant?',
            'applicant_address': 'What is the complete residential address of the applicant?',
            'applicant_occupation': 'What is the occupation of the applicant? (optional)',
            'case_number': 'What is the case number or FIR number?',
            'court_name': 'In which court is the case registered?',
            'offense_charged': 'What offense/section has been charged against the applicant?',
            'arrest_date': 'On what date was the applicant arrested? (format: DD/MM/YYYY)',
            'grounds_for_bail': 'What are the grounds for seeking bail? (e.g., no prior criminal record, cooperative with investigation, etc.)',
            'surety_name': 'Who will stand as surety? (Full name)',
            'surety_address': 'What is the address of the surety?',
            'family_details': 'Any family members dependent on the applicant? (optional)',
            'previous_criminal_record': 'Does the applicant have any previous criminal record? If yes, please specify. (optional)',
            'health_conditions': 'Any health conditions that require attention? (optional)',
            'employment_proof': 'Details of current employment or business (optional)'
        }
    
    def validate_field(self, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """Validate field values"""
        if not value or (isinstance(value, str) and not value.strip()):
            if field_name in self.required_fields:
                return False, f"{field_name} is required and cannot be empty"
            return True, None
        
        # Specific validations
        if field_name == 'applicant_age':
            try:
                age = int(value)
                if age < 18 or age > 120:
                    return False, "Age must be between 18 and 120"
            except ValueError:
                return False, "Age must be a valid number"
        
        elif field_name == 'arrest_date':
            try:
                datetime.strptime(str(value), '%d/%m/%Y')
            except ValueError:
                return False, "Invalid date format. Please use DD/MM/YYYY"
        
        elif field_name == 'applicant_name':
            if len(str(value)) < 3:
                return False, "Name must be at least 3 characters long"
        
        elif field_name == 'grounds_for_bail':
            if len(str(value)) < 30:
                return False, "Grounds for bail must be detailed (at least 30 characters)"
        
        return True, None
    
    def generate_content(self) -> str:
        """Generate bail application content"""
        content = []
        
        content.append("IN THE COURT OF")
        content.append(f"{self.fields.get('court_name', '[NOT PROVIDED]')}")
        content.append("")
        content.append("")
        
        content.append(f"Case No.: {self.fields.get('case_number', '[NOT PROVIDED]')}")
        content.append("")
        content.append("")
        
        content.append("APPLICATION FOR BAIL")
        content.append("Under Section 437/439 of the Code of Criminal Procedure, 1973")
        content.append("")
        content.append("")
        
        content.append("IN THE MATTER OF:")
        content.append(f"{self.fields.get('applicant_name', '[NOT PROVIDED]')} ........ Applicant")
        content.append("")
        content.append("")
        
        content.append("MOST RESPECTFULLY SHOWETH:")
        content.append("")
        
        content.append(f"1. That the applicant, {self.fields.get('applicant_name', '[NOT PROVIDED]')}, "
                      f"aged {self.fields.get('applicant_age', '[NOT PROVIDED]')} years, "
                      f"resident of {self.fields.get('applicant_address', '[NOT PROVIDED]')}, "
                      "is the accused in the above-mentioned case.")
        content.append("")
        
        if self.fields.get('applicant_occupation'):
            content.append(f"2. That the applicant is {self.fields.get('applicant_occupation')} by profession.")
            content.append("")
        
        content.append(f"3. That the applicant was arrested on {self.fields.get('arrest_date', '[NOT PROVIDED]')} "
                      f"in connection with the offense under {self.fields.get('offense_charged', '[NOT PROVIDED]')}.")
        content.append("")
        
        content.append("4. That the applicant submits the following grounds for grant of bail:")
        content.append("")
        content.append(self.fields.get('grounds_for_bail', '[NOT PROVIDED]'))
        content.append("")
        
        if self.fields.get('previous_criminal_record'):
            content.append(f"5. Criminal Record: {self.fields.get('previous_criminal_record')}")
            content.append("")
        else:
            content.append("5. That the applicant has no previous criminal record and is a law-abiding citizen.")
            content.append("")
        
        if self.fields.get('family_details'):
            content.append(f"6. Family Details: {self.fields.get('family_details')}")
            content.append("")
        
        if self.fields.get('health_conditions'):
            content.append(f"7. Health Conditions: {self.fields.get('health_conditions')}")
            content.append("")
        
        content.append("8. That the applicant undertakes to appear before the court as and when required and will not tamper with evidence or influence witnesses.")
        content.append("")
        
        content.append("9. SURETY DETAILS:")
        content.append(f"Name: {self.fields.get('surety_name', '[NOT PROVIDED]')}")
        content.append(f"Address: {self.fields.get('surety_address', '[NOT PROVIDED]')}")
        content.append("")
        
        content.append("PRAYER:")
        content.append("")
        content.append("In view of the above facts and circumstances, it is most respectfully prayed that this Hon'ble Court may be pleased to:")
        content.append("")
        content.append("a) Grant bail to the applicant on such terms and conditions as this Hon'ble Court may deem fit;")
        content.append("")
        content.append("b) Pass any other order as this Hon'ble Court may deem fit in the interest of justice.")
        content.append("")
        content.append("")
        content.append("AND FOR THIS ACT OF KINDNESS, THE APPLICANT SHALL DUTY BOUND FOREVER PRAY.")
        content.append("")
        content.append("")
        content.append("")
        content.append("Applicant")
        content.append(f"Through: _________________")
        content.append("Advocate")
        content.append("")
        content.append(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        content.append(f"Place: _________________")
        
        return '\n\n'.join(content)
