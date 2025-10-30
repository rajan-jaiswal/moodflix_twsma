# 🎬 MoodFlix - Sentiment-Based Movie Recommender

A web-based AI application that analyzes your mood using sentiment analysis and recommends movies from both Hollywood and Bollywood using the AI Movie Recommender API that match your emotional state.

## ✨ Features

- **Sentiment Analysis**: Uses TextBlob to analyze user input and detect emotions
- **AI-Powered Recommendations**: Uses AI Movie Recommender API for intelligent movie suggestions
- **Dual Industry Support**: Recommends movies from both Hollywood and Bollywood
- **Beautiful UI**: Cinematic dark theme with responsive design
- **Real-time Results**: Dynamic movie cards with posters, ratings, and descriptions
- **Multiple Mood Support**: Handles happy, sad, excited, romantic, and more emotions

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. API Configuration

The app uses the AI Movie Recommender API via RapidAPI. The API key is already included in the code, but you can override it if needed.

Create a `.env` file in the project root (optional):

```bash
RAPIDAPI_KEY=your_rapidapi_key_here
```

### 3. Run the Application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

## 🎯 How It Works

1. **User Input**: User types how they're feeling (e.g., "I feel happy and want Bollywood comedy")
2. **Sentiment Analysis**: TextBlob analyzes the text and determines the mood
3. **Dual Query Generation**: Creates both Bollywood and Hollywood search queries
4. **AI Movie Search**: AI Movie Recommender API finds relevant movies from both industries
5. **Results Display**: Movies are displayed in beautiful cards with ratings and descriptions

## 🎭 Supported Moods

- **Happy** → "happy comedy movies bollywood"
- **Sad** → "sad drama movies indian"
- **Angry** → "action thriller movies bollywood"
- **Relaxed** → "calm relaxing movies indian"
- **Bored** → "exciting adventure movies bollywood"
- **Excited** → "action adventure movies indian"
- **Romantic** → "romantic movies bollywood"
- **Scared** → "horror thriller movies indian"
- **Nostalgic** → "classic vintage movies bollywood"
- **Adventurous** → "adventure action movies indian"

**Note**: The app searches both Hollywood and Bollywood movies for each mood to give you diverse recommendations!

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Sentiment Analysis**: TextBlob
- **Movie Data**: AI Movie Recommender API (RapidAPI)
- **Styling**: Custom CSS with cinematic dark theme

## 📁 Project Structure

```
MoodFlix/
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main HTML template
├── static/
│   ├── styles.css        # CSS styles
│   └── script.js         # JavaScript functionality
├── .env                  # Environment variables (create this)
└── README.md            # This file
```

## 🎨 UI Features

- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Theme**: Cinematic black background with gold accents
- **Loading States**: Smooth loading animations
- **Error Handling**: User-friendly error messages
- **Interactive Elements**: Hover effects and smooth transitions
- **Mood Suggestions**: Example mood inputs to help users

## 🔧 Customization

### Adding New Moods

Edit the `MOOD_QUERY_MAP` in `app.py`:

```python
MOOD_QUERY_MAP = {
    "your_mood": "your search query",  # Add new mood-query mapping
}
```

### Styling Changes

Modify `static/styles.css` to customize:
- Colors and themes
- Layout and spacing
- Animations and transitions
- Responsive breakpoints

## 🐛 Troubleshooting

### Common Issues

1. **No movies found**: Check your internet connection and API key
2. **CORS errors**: Ensure Flask is running on the correct port
3. **Missing dependencies**: Run `pip install -r requirements.txt`

### API Limits

The AI Movie Recommender API has rate limits. For production use, consider:
- Implementing caching
- Using a database to store movie data
- Adding error handling for API limits

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

**Enjoy discovering movies from Hollywood and Bollywood that match your mood with AI-powered recommendations! 🍿🎬**
