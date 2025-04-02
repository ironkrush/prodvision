# VideoRemind

A web application that helps you manage and remember to watch your saved videos from YouTube and Instagram.

## Features

- User authentication and account management
- Import YouTube playlists
- Import Instagram saved posts (coming soon)
- AI-powered video genre classification
- Automatic notifications for unwatched videos
- Filter and search saved videos
- Modern, responsive UI

## Tech Stack

- Frontend:
  - React with TypeScript
  - Chakra UI for components
  - React Router for navigation
  - Axios for API calls

- Backend:
  - FastAPI (Python)
  - MongoDB with Motor for async database operations
  - JWT authentication
  - Hugging Face Transformers for AI
  - YouTube Data API integration

## Prerequisites

- Node.js (v14 or later)
- Python (v3.8 or later)
- MongoDB
- YouTube API Key

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd videoremind
```

2. Frontend setup:
```bash
cd frontend
npm install
```

3. Backend setup:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory:
```
SECRET_KEY=your-secret-key
MONGODB_URL=mongodb://localhost:27017
YOUTUBE_API_KEY=your-youtube-api-key
```

5. Start MongoDB:
Make sure MongoDB is running on your system.

## Running the Application

1. Start the backend server:
```bash
cd backend
uvicorn app:app --reload
```

2. Start the frontend development server:
```bash
cd frontend
npm start
```

3. Open your browser and navigate to `http://localhost:3000`

## API Documentation

Once the backend server is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 

cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload 


cd frontend
npm install
npm start


Email: test@example.com
Password: testpassword123
