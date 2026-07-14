import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf(file_path: Path, title: str, sections: list):
    """Generates a professional multi-page PDF document using ReportLab."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        name="DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor="#1e3a8a",
        alignment=0,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor="#1e3a8a",
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        name="BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor="#334155",
        spaceAfter=10
    )
    
    story = []
    
    # Add Title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 15))
    
    # Add Sections
    for heading, text in sections:
        story.append(Paragraph(heading, heading_style))
        story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 10))
        
    doc.build(story)
    print(f"Generated PDF: {file_path}")

def main():
    base_dir = Path(__file__).resolve().parent.parent
    policies_dir = base_dir / "data" / "policies"
    
    # HR Policies
    hr_sections = [
        ("Section 1: Working Hours & Attendance", 
         "Standard working hours at Acme Corp are from 9:00 AM to 5:00 PM, Monday through Friday, totaling 40 hours per week. "
         "All employees are expected to be present and available during core business hours. Flextime schedules may be "
         "approved by direct managers, provided they do not affect department performance."),
        
        ("Section 2: Annual Leave & Paid Time Off", 
         "Employees are entitled to 25 working days of paid annual leave per calendar year. Annual leave accrues monthly "
         "at a rate of 2.08 days per month. Vacation requests must be submitted through the HR Portal at least two weeks "
         "in advance and approved by the department head. A maximum of 5 unused leave days can be carried over to the next year."),
        
        ("Section 3: Paid Parental Leave", 
         "Acme Corp provides up to 12 weeks of fully paid Parental Leave to eligible employees following the birth of a child, "
         "or the placement of a child in connection with adoption or foster care. This policy applies equally to all new parents, "
         "regardless of gender, to support family bonding. Parental leave must be taken within the first 12 months after the event."),
         
        ("Section 4: Probationary Period",
         "All new hires undergo a standard probationary period of 6 months. During this time, performance and alignment with company "
         "values are evaluated. Either party may terminate the employment contract during probation with a 1-week notice period.")
    ]
    generate_pdf(policies_dir / "HR" / "hr_policy.pdf", "Acme Corp - Human Resources Policies", hr_sections)
    
    # IT Policies
    it_sections = [
        ("Section 1: Password & Credential Security", 
         "Employees must secure all company accounts using passwords that are a minimum of 12 characters in length, "
         "containing at least one uppercase letter, one lowercase letter, one number, and one special character. "
         "Passwords must be changed every 90 days. Sharing passwords or credentials via email, messaging, or written notes is strictly prohibited."),
        
        ("Section 2: Automatic Data Backups", 
         "All corporate work documents and data must be saved to official company OneDrive repositories. Personal hard drives "
         "or local desktop folders are not backed up. Automated daily sync runs every night at 11:00 PM to backup all "
         "cloud storage folders to secure corporate servers. Lost data from local drives is not recoverable."),
        
        ("Section 3: Bring Your Own Device (BYOD) Registry", 
         "Employees wishing to access corporate email or internal networks from personal smartphones or laptops must register "
         "their device with the IT department. Devices must have mobile device management (MDM) software installed to ensure "
         "data encryption and enable remote wipe functionality in case the device is lost or stolen.")
    ]
    generate_pdf(policies_dir / "IT" / "it_policy.pdf", "Acme Corp - Information Technology Policies", it_sections)
    
    # Security Policies
    security_sections = [
        ("Section 1: Physical Access Control & ID Badges", 
         "All employees, contractors, and visitors must wear official company ID badges visibly at all times while on company premises. "
         "Employees must scan their badges at entry turnstiles. Tailgating—following another employee through a secure gate without "
         "scanning—is a serious security violation. Visitors must sign in at reception and remain escorted by a badge holder."),
        
        ("Section 2: Clean Desk Policy", 
         "To protect confidential information, employees must clear their desks of all sensitive papers, documents, notes, "
         "and physical storage devices (like USBs) at the end of each workday. Computer screens must be locked when leaving "
         "the desk for any duration (keyboard shortcut Windows + L). File cabinets containing private records must remain locked.")
    ]
    generate_pdf(policies_dir / "Security" / "security_policy.pdf", "Acme Corp - Corporate Security Policies", security_sections)

    # Travel & Expense Policies
    travel_sections = [
        ("Section 1: Flight Bookings & Travel Agency", 
         "All business travel flights must be booked through the company's designated online booking tool, Concur, or via our "
         "authorized travel agency. Domestic flights must be booked in Economy Class. Business Class bookings are only permitted "
         "for international flights exceeding 6 hours in duration and require prior written sign-off from the department Vice President."),
        
        ("Section 2: Daily Meal Allowances (Per Diem)", 
         "Acme Corp allows a maximum daily meal per diem of $75 for domestic business travel and $100 for international business travel. "
         "Employees must submit itemized receipts for all meals exceeding $25 in value. Alcohol expenses are not eligible for "
         "reimbursement unless associated with a pre-approved client entertainment event.")
    ]
    generate_pdf(policies_dir / "Travel" / "travel_policy.pdf", "Acme Corp - Travel & Expense Policies", travel_sections)

if __name__ == "__main__":
    main()
