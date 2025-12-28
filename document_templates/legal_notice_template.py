"""
Legal Notice Template
For sending formal legal notices
"""

from typing import Dict, Any, Optional
from .base_template import BaseTemplate
from datetime import datetime, timedelta


class LegalNoticeTemplate(BaseTemplate):
    """Template for generating legal notices"""
    
    def __init__(self):
        super().__init__()
        self.document_type = "Legal Notice"
        
        self.required_fields = [
            'sender_name',
            'sender_address',
            'recipient_name',
            'recipient_address',
            'notice_subject',
            'notice_details',
            'grievance_description',
            'legal_basis',
            'demand_action',
            'response_period'
        ]
        
        self.optional_fields = [
            'sender_phone',
            'sender_email',
            'reference_documents',
            'monetary_amount',
            'consequences_warning'
        ]
    
    def get_field_prompts(self) -> Dict[str, str]:
        """Return conversational prompts for each field"""
        return {
            'sender_name': 'What is your full name (person/entity sending the notice)?',
            'sender_address': 'What is your complete address?',
            'sender_phone': 'What is your contact phone number? (optional)',
            'sender_email': 'What is your email address? (optional)',
            'recipient_name': 'What is the name of the person/entity to whom you are sending this notice?',
            'recipient_address': 'What is the complete address of the recipient?',
            'notice_subject': 'What is the subject/purpose of this legal notice? (e.g., breach of contract, non-payment, defamation, etc.)',
            'notice_details': 'Briefly describe what this notice is about in one line.',
            'grievance_description': 'Describe in detail the grievance or issue. What happened and when?',
            'legal_basis': 'What is the legal basis for this notice? (e.g., breach of contract dated DD/MM/YYYY, violation of specific law/section, etc.)',
            'demand_action': 'What action do you demand from the recipient? Be specific.',
            'monetary_amount': 'If demanding payment, what is the amount? (optional)',
            'response_period': 'How many days are you giving for response? (typically 7, 15, or 30 days)',
            'reference_documents': 'Are you referencing any documents or agreements? Please list them. (optional)',
            'consequences_warning': 'What legal action will you take if demands are not met? (optional - will use default if not provided)'
        }
    
    def validate_field(self, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """Validate field values"""
        if not value or (isinstance(value, str) and not value.strip()):
            if field_name in self.required_fields:
                return False, f"{field_name} is required and cannot be empty"
            return True, None
        
        # Specific validations
        if field_name == 'sender_phone' and value:
            digits = ''.join(filter(str.isdigit, str(value)))
            if len(digits) < 10:
                return False, "Phone number must contain at least 10 digits"
        
        elif field_name == 'sender_email' and value:
            if '@' not in str(value) or '.' not in str(value).split('@')[-1]:
                return False, "Invalid email format"
        
        elif field_name in ['sender_name', 'recipient_name']:
            if len(str(value)) < 3:
                return False, "Name must be at least 3 characters long"
        
        elif field_name == 'grievance_description':
            if len(str(value)) < 50:
                return False, "Grievance description must be detailed (at least 50 characters)"
        
        elif field_name == 'demand_action':
            if len(str(value)) < 20:
                return False, "Demanded action must be clearly stated (at least 20 characters)"
        
        elif field_name == 'response_period':
            try:
                days = int(value)
                if days < 1 or days > 90:
                    return False, "Response period must be between 1 and 90 days"
            except ValueError:
                return False, "Response period must be a valid number of days"
        
        return True, None
    
    def generate_content(self) -> str:
        """Generate legal notice content"""
        content = []
        
        # Calculate deadline date
        try:
            response_days = int(self.fields.get('response_period', 15))
            deadline = datetime.now() + timedelta(days=response_days)
            deadline_str = deadline.strftime('%d/%m/%Y')
        except:
            deadline_str = "[CALCULATE BASED ON RESPONSE PERIOD]"
        
        content.append("LEGAL NOTICE")
        content.append("")
        content.append("")
        
        content.append(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        content.append("")
        content.append("")
        
        content.append("TO,")
        content.append(f"{self.fields.get('recipient_name', '[NOT PROVIDED]')}")
        content.append(f"{self.fields.get('recipient_address', '[NOT PROVIDED]')}")
        content.append("")
        content.append("")
        
        content.append(f"SUBJECT: {self.fields.get('notice_subject', '[NOT PROVIDED]')}")
        content.append("")
        content.append("")
        
        content.append("Dear Sir/Madam,")
        content.append("")
        content.append("")
        
        content.append(f"UNDER INSTRUCTIONS FROM AND ON BEHALF OF: {self.fields.get('sender_name', '[NOT PROVIDED]')}")
        content.append(f"Address: {self.fields.get('sender_address', '[NOT PROVIDED]')}")
        if self.fields.get('sender_phone'):
            content.append(f"Phone: {self.fields.get('sender_phone')}")
        if self.fields.get('sender_email'):
            content.append(f"Email: {self.fields.get('sender_email')}")
        content.append("")
        content.append("")
        
        content.append(f"RE: {self.fields.get('notice_details', '[NOT PROVIDED]')}")
        content.append("")
        content.append("")
        
        content.append("This is a legal notice being served upon you under the instructions of my client mentioned above.")
        content.append("")
        content.append("")
        
        content.append("FACTS OF THE CASE:")
        content.append("")
        # Format grievance with proper paragraphing
        grievance = self.fields.get('grievance_description', '[NOT PROVIDED]')
        if '\n' in grievance:
            for para in grievance.split('\n'):
                if para.strip():
                    content.append(para.strip())
                    content.append("")
        else:
            content.append(grievance)
            content.append("")
        content.append("")
        
        content.append("LEGAL BASIS:")
        content.append("")
        content.append(self.fields.get('legal_basis', '[NOT PROVIDED]'))
        content.append("")
        content.append("")
        
        if self.fields.get('reference_documents'):
            content.append("REFERENCE DOCUMENTS:")
            content.append(self.fields.get('reference_documents'))
            content.append("")
            content.append("")
        
        content.append("DEMAND:")
        content.append("")
        content.append("My client hereby demands that you:")
        content.append("")
        content.append(self.fields.get('demand_action', '[NOT PROVIDED]'))
        content.append("")
        if self.fields.get('monetary_amount'):
            content.append(f"Including payment of Rs. {self.fields.get('monetary_amount')}")
            content.append("")
        content.append("")
        
        content.append(f"NOTICE PERIOD: You are hereby given {self.fields.get('response_period', '[NOT PROVIDED]')} days from the date of receipt of this notice to comply with the above demands, i.e., on or before {deadline_str}.")
        content.append("")
        content.append("")
        
        content.append("CONSEQUENCES OF NON-COMPLIANCE:")
        content.append("")
        if self.fields.get('consequences_warning'):
            content.append(self.fields.get('consequences_warning'))
        else:
            content.append("Please note that if you fail to comply with the demands mentioned above within the stipulated time period, my client will be constrained to initiate appropriate legal proceedings against you for recovery of the dues/enforcement of rights, including claims for damages, interest, and costs, without any further reference to you, and you shall be fully responsible for all consequences thereof.")
        content.append("")
        content.append("")
        
        content.append("This notice is issued without prejudice to my client's rights, remedies, claims, and contentions, all of which are expressly reserved.")
        content.append("")
        content.append("")
        
        content.append("Take Notice.")
        content.append("")
        content.append("")
        content.append("")
        content.append("Yours faithfully,")
        content.append("")
        content.append("")
        content.append("")
        content.append("_______________________")
        content.append("[Advocate Name]")
        content.append("[Advocate Address]")
        content.append("[Enrolment Number]")
        content.append("")
        content.append(f"On behalf of: {self.fields.get('sender_name', '[NOT PROVIDED]')}")
        
        return '\n\n'.join(content)
