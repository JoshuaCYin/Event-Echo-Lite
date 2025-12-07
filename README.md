# Event Echo

## Project Vision Statement
For university students, faculty, and staff who want to easily plan, discover, organize, and attend campus events without scheduling conflicts, EventEcho is a digital event management web application that enables easy event discovery, streamlines event planning, and uses generative artificial intelligence (AI) to increase engagement via conversational assistance. Unlike scattered emails or bulletin board flyers, our software offers a more interactive platform that simplifies logistics, improves communication, and unites the people of the Indiana Wesleyan University (IWU) community.

## Features
- **Event Discovery**: Browse and search for campus events by category, date, and location.
- **Event Planning**: Create and manage events, including venue selection and scheduling.
- **AI Assistant**: Conversational AI to help users find events and answer questions.
- **RSVP System**: Easy RSVP functionality for attendees.
- **Reviews**: Rate and review events.
- **Planning Tools**: Task management for event organizers.

## Tech Stack
- **Backend**: Python, Flask, PostgreSQL
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **AI Integration**: OpenAI / Google Gemini
- **Authentication**: JWT (JSON Web Tokens)

## Quick Start
For detailed setup instructions, please refer to [SETUP.md](./SETUP.md).

1. **Clone the repository**
2. **Set up the backend** (Virtual env, dependencies, database)
3. **Set up the frontend** (Simple HTTP server)
4. **Access the application** at `http://localhost:8080`

## Running Tests

To run the backend unit tests, navigate to the `backend` directory and run:

```bash
cd backend
python -m pytest
```

This will discover and run all tests in the `tests` directory.
