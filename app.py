from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os
import base64
from PyPDF2 import PdfReader
from docx import Document
import re
import fitz 
from pypdf import PdfReader
import pypdfium2 as pdfium
from google.cloud import vision
import io
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import os 
from io import BytesIO
import zipfile
from PIL import Image
import PIL.Image

from pytesseract import image_to_string
import pytesseract

import subprocess
import shutil

def check_tesseract():
    try:
        # Check if tesseract is in the PATH
        tesseract_path = shutil.which('tesseract')
        if tesseract_path:
            print("Tesseract is installed at:", tesseract_path)
            
            # Run the tesseract command to check its version
            result = subprocess.run([tesseract_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                print("Tesseract is installed:", result.stdout.decode())
            else:
                print("Error checking Tesseract version:", result.stderr.decode())
        else:
            print("Tesseract is not installed in the PATH.")
    except Exception as e:
        print("Error checking Tesseract:", str(e))







app = Flask(__name__)
CORS(app)  # Enable CORS


# API key for Reed.co.uk
reed_api_key = 'be4976b7-4f00-4a2f-bf0e-26e36353f304'

# Route for handling job search on Reed.co.uk
@app.route('/api/jobs', methods=['POST'])
def get_jobs():
    # Call the function to check for Tesseract
    check_tesseract()
    print("Inside backend of ukjobs")
    data = request.json
    ttly = data.get('ttly')
    cty = data.get('cty')
    pageNum = data.get('pageNum')
    
    print("Data", ttly, cty, pageNum)

    target_url = f"https://www.reed.co.uk/api/1.0/search?resultsToSkip={pageNum}&resultsToTake=10&keywords={ttly}&locationName={cty}"

    headers = {
        "Authorization": "Basic " + base64.b64encode((reed_api_key + ':').encode()).decode(),
        "Content-Type": "application/json"
    }

    try:
        print("Inside ukjobs ")
        response = requests.get(target_url, headers=headers)
        return jsonify(response.json())
    except Exception as e:
        print("Error:", e)
        return "Internal Server Error", 500



# Create an 'uploads' directory if it doesn't exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')
# Set up the path to Tesseract-OCR if it's not in your PATH
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' 
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

  # Update this to your Tesseract-OCR path

# Function to extract text from a scanned PDF
def extract_text_from_pdf(file_path):
    # Convert PDF pages to images (you may need to specify poppler_path)
    # , poppler_path=r'C:\Users\FAIYAZ\Downloads\Release-24.07.0-0\poppler-24.07.0\Library\bin'
    # pages = convert_from_path(file_path, poppler_path=r'C:\Users\FAIYAZ\Downloads\Release-24.07.0-0\poppler-24.07.0\Library\bin' )  # Update poppler path if needed
    
    pages = convert_from_path(file_path )  # Update poppler path if needed
    
    full_text = ""
    
    # Iterate through the images (one per page)
    for page_num, page in enumerate(pages):
        # Save the image of the page temporarily
        image_file = f"page_{page_num + 1}.jpg"
        page.save(image_file, 'JPEG')
        
        # Use Tesseract to extract text from the image
        text = pytesseract.image_to_string(image_file, lang='eng')
        full_text += f"Page {page_num + 1}:\n{text}\n"
        
        # Remove the temporary image file
        os.remove(image_file)
    
    return full_text

# Function to extract text from DOCX
def extract_text_from_docx(file_path):
    print("docx", file_path)
    full_text = ""
    doc = Document(file_path)
    full_text = "\n".join([para.text for para in doc.paragraphs])
    return full_text



# Function to calculate resume score based on keyword matching
def calculate_resume_score(resume_text, job_keywords, file_category):
    # Check if file_category exists in job_keywords
    if file_category not in job_keywords:
        return 0.0, []  # Return 0 score and empty matched_keywords if no category

    # Get the keywords for the provided category
    keywords = job_keywords[file_category]

    # Handle empty keyword list (to avoid division by zero)
    if not keywords:
        return 0.0, []

    # Convert resume text to lowercase for easier matching
    resume_text = resume_text.lower()

    # Calculate matched keywords
    matched_keywords = [kw for kw in keywords if kw.lower() in resume_text]

    # Calculate score (prevent division by zero if there are no keywords)
    score = (len(matched_keywords) / len(keywords)) * 100 if len(keywords) > 0 else 0.0

    return score, matched_keywords

# Define the route for handling file upload and resume scoring
@app.route('/upload/file', methods=['POST'])
def upload_file_and_score():
    print("inside")
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    file_category = request.form.get('filecategory')  # Correctly accessing the file category
    print("File Category:", file_category)
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the file
    file_path = os.path.join('uploads', file.filename)
    file.save(file_path)

    # Extract text from the resume based on file extension
    if file.filename.endswith('.pdf'):
        resume_text = extract_text_from_pdf(file_path)
        print("text from extract", resume_text)
    elif file.filename.endswith('.docx'):
        resume_text = extract_text_from_docx(file_path)
        print("text from extract doc", resume_text)
    else:
        return jsonify({"error": "Unsupported file type. Please upload a PDF or DOCX file."}), 400

    # Define some job-related keywords (these should be dynamic based on the job description)
    job_keywords = {
        'software development': [
            'python', 'javascript', 'react', 'node.js', 'html', 'css', 'sql', 'aws', 
            'docker', 'api', 'devops', 'git', 'microservices', 'rest', 'graphql', 
            'agile', 'scrum', 'typescript', 'redux', 'android', 'ios', 'kotlin', 'swift', 
            'react native', 'flutter', 'xcode', 'android studio', 'mobile app development', 
            'api integration', 'firebase', 'ui/ux design', 'mobile testing', 'java', 
            'objective-c', 'mobile security', 'push notifications', 'app store optimization',
            'c#', 'c++', 'go', 'ruby', 'django', 'spring', 'express.js', 'full stack development'
        ],
        'web development': [
            'html', 'css', 'javascript', 'bootstrap', 'react', 'vue.js', 'angular', 
            'php', 'wordpress', 'seo', 'jquery', 'sass', 'tailwind css', 'webpack', 
            'node.js', 'express.js', 'api integration', 'typescript', 'redux', 'ajax', 
            'graphql', 'json', 'cms', 'ecommerce platforms', 'rest api', 'cross-browser compatibility'
        ],
        'data science': [
            'python', 'r', 'sql', 'data analysis', 'pandas', 'numpy', 'matplotlib', 
            'scikit-learn', 'machine learning', 'deep learning', 'neural networks', 
            'tensorflow', 'keras', 'nlp', 'data visualization', 'big data', 'hadoop', 
            'spark', 'data mining', 'statistical analysis', 'power bi', 'tableau', 
            'mathematical modeling', 'time series analysis', 'bayesian inference', 
            'data wrangling', 'hypothesis testing'
        ],
        'digital marketing': [
            'seo', 'sem', 'content marketing', 'google analytics', 'social media', 
            'facebook ads', 'google ads', 'email marketing', 'ppc', 'affiliate marketing', 
            'crm', 'influencer marketing', 'conversion optimization', 'keyword research', 
            'a/b testing', 'adwords', 'copywriting', 'branding', 'social media management', 
            'content creation', 'retargeting', 'funnel building', 'campaign analysis', 
            'marketing automation', 'growth hacking'
        ],
        'project management': [
            'agile', 'scrum', 'kanban', 'waterfall', 'project planning', 'risk management', 
            'stakeholder management', 'resource allocation', 'budgeting', 'jira', 'trello', 
            'microsoft project', 'asynchronous communication', 'roadmap planning', 
            'milestone tracking', 'performance tracking', 'team management', 'time tracking', 
            'resource management', 'project coordination', 'problem-solving', 'project lifecycle management', 
            'pmp', 'cost management', 'quality management'
        ],
        'cybersecurity': [
            'network security', 'penetration testing', 'vulnerability assessment', 
            'firewalls', 'intrusion detection', 'encryption', 'malware analysis', 
            'ethical hacking', 'security audits', 'incident response', 'siem', 
            'identity and access management', 'threat intelligence', 'cyber defense', 
            'risk management', 'compliance', 'vpn', 'cloud security', 'iso 27001', 
            'gdpr compliance', 'endpoint security', 'incident management', 'security information management', 
            'forensics', 'cybersecurity strategy', 'zero trust architecture'
        ],
        'devops engineer': [
            'docker', 'kubernetes', 'jenkins', 'aws', 'azure', 'terraform', 'ansible', 
            'ci/cd', 'git', 'linux', 'bash scripting', 'python', 'monitoring', 
            'prometheus', 'grafana', 'helm', 'agile', 'scripting', 'automation', 
            'cloud infrastructure', 'containerization', 'cloudformation', 'nginx', 
            'distributed systems', 'load balancing', 'troubleshooting', 'log management', 
            'infrastructure as code', 'security automation'
        ],
        'finance': [
            'financial analysis', 'accounting', 'budgeting', 'forecasting', 'taxation', 
            'excel', 'quickbooks', 'auditing', 'financial modeling', 'investment banking', 
            'financial statements', 'portfolio management', 'risk management', 'erp', 
            'financial reporting', 'payroll', 'variance analysis', 'gaap', 'sap', 
            'revenue management', 'cost control', 'profitability analysis', 'capital budgeting', 
            'fund management', 'equity research', 'investment analysis', 'internal audit'
        ],
        'human resources': [
            'recruitment', 'talent acquisition', 'performance management', 'hr analytics', 
            'employee relations', 'compensation and benefits', 'onboarding', 'offboarding', 
            'training and development', 'hr policies', 'compliance', 'workforce planning', 
            'diversity and inclusion', 'employee engagement', 'payroll', 'hr systems', 
            'labor laws', 'conflict resolution', 'retention strategies', 'employee experience', 
            'talent management', 'leadership development', 'hr branding', 'benefits administration', 
            'employee well-being', 'succession planning'
        ],
        'sales': [
            'lead generation', 'client management', 'negotiation', 'sales strategy', 'crm', 
            'b2b', 'b2c', 'cold calling', 'closing deals', 'salesforce', 'prospecting', 
            'pipeline management', 'sales presentations', 'market research', 'quota management',
            'lead nurturing', 'relationship building', 'sales funnel management', 
            'up-selling', 'cross-selling', 'territory management', 'account management', 
            'solution selling', 'customer acquisition', 'sales forecasting'
        ],
        'customer service': [
            'customer support', 'problem resolution', 'call center', 'crm', 'conflict management', 
            'client relations', 'customer satisfaction', 'ticketing systems', 'communication skills', 
            'troubleshooting', 'time management', 'escalation handling', 'active listening', 
            'product knowledge', 'multitasking', 'customer retention', 'issue resolution', 
            'customer onboarding', 'service level agreements', 'patience', 'empathetic communication', 
            'customer education', 'conflict de-escalation'
        ],
        'mobile developer': [
            'android', 'ios', 'kotlin', 'swift', 'react native', 'flutter', 'xcode', 
            'android studio', 'mobile app development', 'api integration', 'firebase', 
            'ui/ux design', 'mobile testing', 'java', 'objective-c', 'rest', 'graphql', 
            'mobile security', 'push notifications', 'app store optimization', 'augmented reality', 
            'location-based services', 'native app development', 'cross-platform app development', 
            'bluetooth integration', 'mobile performance optimization', 'cloud messaging', 
            'offline storage'
        ],
        'designer': [
            'photoshop', 'illustrator', 'indesign', 'sketch', 'figma', 'adobe xd', 
            'logo design', 'brand identity', 'ux design', 'ui design', 'wireframing', 
            'prototyping', 'graphic design', 'typography', 'color theory', 'visual hierarchy', 
            'responsive design', 'user research', 'interaction design', 'motion graphics', 
            '3d modeling', 'after effects', 'product design', 'user flows', 'accessibility design'
        ],
        'general skills': [
            'communication', 'teamwork', 'problem solving', 'adaptability', 'time management', 
            'leadership', 'critical thinking', 'creativity', 'project management', 'negotiation', 
            'decision making', 'collaboration', 'conflict resolution', 'interpersonal skills',
            'self-motivation', 'presentation skills', 'active listening', 'stress management', 
            'organization', 'work ethic', 'emotional intelligence', 'cultural awareness'
        ]
    }





    # Calculate resume score
    score, matched_keywords = calculate_resume_score(resume_text, job_keywords, file_category)
    print("Final score",score)


     # Remove the uploaded file after processing
    if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File {file.filename} has been deleted after processing.")


    
    
    # Return the score and matched keywords for other cases
    return jsonify({
            "resume_text": resume_text,
            "file_category": file_category,
            "score": score,
            "matched_keywords": matched_keywords
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

