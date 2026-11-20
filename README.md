# Estate Notice Alert System

## 1. Project Overview

The Estate Notice Alert System is a web-based application that collects,
processes, and manages estate-related public notices published in
newspapers and accessible court sources.

The system uses PDF text extraction and OCR to identify relevant notices,
extract property-related information, and store the results for review.

Users can search approved notices and receive WhatsApp notifications
based on their saved search criteria.

## 2. Main Objectives

- Collect public notices from permitted sources.
- Download and validate newspaper PDF documents.
- Extract text from selectable-text and scanned PDF pages.
- Detect estate and land-related public notices.
- Extract property details and important dates.
- Store original PDFs, notice images, and extracted information.
- Provide an administrative review and approval workflow.
- Allow users to search and save search criteria.
- Send WhatsApp alerts for matching approved notices.

## 3. Technology Stack

### Frontend
- React
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend
- Python
- Django
- Django REST Framework

### Database
- PostgreSQL

### PDF Processing and OCR
- PyMuPDF
- Tesseract OCR
- OpenCV

### Background Processing
- Celery
- Redis
- Celery Beat

### Notifications
- WhatsApp Business Cloud API

### Version Control
- Git
- GitHub

## 4. Main Modules

1. User Authentication
2. Source Management
3. Newspaper and Document Collection
4. PDF Processing
5. OCR and Text Extraction
6. Public Notice Detection
7. Notice Information Extraction
8. Notice Management
9. Admin Review and Approval
10. Saved Searches
11. WhatsApp Notifications
12. Dashboard and Search

## 5. Project Workflow

1. Collect documents from permitted sources.
2. Download and validate PDF files.
3. Check for duplicate documents.
4. Process PDF pages individually.
5. Extract selectable text or perform OCR.
6. Detect estate-related public notices.
7. Extract property and legal information.
8. Store notices and their source references.
9. Send notices for administrative review.
10. Publish approved notices for search.
11. Match approved notices against saved searches.
12. Send WhatsApp notifications to subscribed users.

## 6. Important Rules

- Only relevant estate and land-related public notices are included.
- Generic property advertisements are excluded.
- Original documents and page references are preserved.
- Missing information must not be invented.
- Only approved notices appear in public search.
- WhatsApp notifications require user opt-in and verification.
- Duplicate notifications must be prevented.
- Source access and document reuse permissions must be respected.

## 7. Repository Structure

```text
Estate-Notice-Alert-System/
├── backend/
├── frontend/
├── docs/
├── scripts/
├── .gitignore
└── README.md

