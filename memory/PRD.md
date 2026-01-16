# PhotoEvent Pro - Product Requirements Document

## Overview
A full-stack photography web application for event photographers to manage photo events and allow guests to find their photos.

## Original Problem Statement
Build a photography web app with Admin Dashboard, Bulk Upload to Supabase, QR Generator for events, and Customer Page for viewing photos. Using lightweight approach (no face_recognition/dlib).

## Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: React with Tailwind CSS
- **Database**: MongoDB (app data)
- **Storage**: Supabase Storage (event-photos bucket)
- **Auth**: JWT-based authentication

## User Personas
1. **Photographer (Admin)**: Creates events, uploads photos in bulk, shares QR codes
2. **Event Guest (Customer)**: Scans QR code, browses event photos

## Core Requirements (Static)
- Photographer login/registration
- Event CRUD operations
- Bulk photo upload to Supabase
- QR code generation for events
- Customer-facing photo gallery

## What's Been Implemented (January 2026)
- ✅ JWT Authentication (register/login)
- ✅ Admin Dashboard with event management
- ✅ Create Event functionality with date picker
- ✅ Bulk photo upload to Supabase Storage
- ✅ QR Code generation with shareable links
- ✅ Customer event page (public access)
- ✅ Photo lightbox with navigation
- ✅ Modern dark theme (Netflix/Spotify style)
- ✅ Mobile-responsive design

## API Endpoints
- POST /api/auth/register - User registration
- POST /api/auth/login - User login
- GET /api/auth/me - Get current user
- POST /api/events - Create event
- GET /api/events - List user's events
- GET /api/events/{id} - Get event details
- DELETE /api/events/{id} - Delete event
- POST /api/events/{id}/photos - Upload photos
- GET /api/events/{id}/photos - Get event photos
- GET /api/public/events/{id} - Public event access
- GET /api/public/events/{id}/photos - Public photos

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- User authentication ✅
- Event management ✅
- Photo upload ✅
- QR sharing ✅

### P1 (High Priority) - Future
- AI Face Matching with OpenCV
- Selfie upload for face search
- Photo download batch option

### P2 (Medium Priority) - Future
- Event analytics/statistics
- Multiple photographer collaboration
- Watermark support

## Next Tasks
1. Implement OpenCV face matching for selfie search
2. Add selfie upload on customer page
3. Implement face embedding storage
4. Add photo download functionality
