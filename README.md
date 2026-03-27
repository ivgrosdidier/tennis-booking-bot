# Tennis Booking Through Flask

This tool is designed to help tennis players manage their court reservations effortlessly. This app synchronizes club bookings with a dedicated Google Calendar and automates the morning "rush" for court availability.

## Features
Automated Booking: A backend engine that handles the morning booking process so you don't have to be at your computer at 8:00 AM.

Google Calendar Sync: Automatically creates and updates a dedicated "TennisBookingBot" calendar to keep your sports schedule organized and separate from your work/personal life.

Personal Dashboard: A clean web interface to manage your club credentials, toggle automation, and maintain a list of preferred playing partners.

Secure Credential Management: Uses industry-standard encryption (Fernet) to protect your club login details and OAuth 2.0 for secure Google access.

## The Tech Stack
Frontend: Flask (Python) with a responsive dashboard.
Database & Auth: Firebase (Firestore for data, Firebase Auth for user accounts).
Infrastructure: Designed for Google Cloud Run with Cloud Scheduler for automated daily triggers.
External APIs: Google Calendar API, Tennis Club Booking System.

## Privacy & Security
This application is built with privacy in mind. We do not store your personal calendar events; we only create and manage entries specifically related to your tennis bookings. All club passwords are encrypted before being stored in our database.

## Acknowledgements
Flask
Firebase
adjdunn for Flask-Firebase-Template (https://github.com/adjdunn/Flask-Firebase-Template)





