// DOM Elements
const moodInput = document.getElementById('mood-input');
const findMoviesBtn = document.getElementById('find-movies-btn');
const surpriseBtn = document.getElementById('surprise-btn');
const loadMoreBtn = document.getElementById('load-more-btn');
const preferenceSelect = document.getElementById('preference-select');
const limitSelect = document.getElementById('limit-select');
const loadingSection = document.getElementById('loading-section');
const resultsSection = document.getElementById('results-section');
const errorSection = document.getElementById('error-section');
const moodTitle = document.getElementById('mood-title');
const moodDescription = document.getElementById('mood-description');
const moviesGrid = document.getElementById('movies-grid');
const errorText = document.getElementById('error-text');
const emojiChips = document.querySelectorAll('.emoji-chip');

// Event Listeners
findMoviesBtn.addEventListener('click', handleFindMovies);
if (surpriseBtn) surpriseBtn.addEventListener('click', handleSurpriseMe);
if (loadMoreBtn) loadMoreBtn.addEventListener('click', handleLoadMore);
emojiChips.forEach(chip => chip.addEventListener('click', () => handleEmojiClick(chip.dataset.emoji)));
moodInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleFindMovies();
    }
});

// Client state
let lastRequest = { moodText: '', preference: 'mixed', limit: 10, emoji: '' };
let currentResults = [];

// Main function to handle movie recommendation
async function handleFindMovies() {
    const moodText = moodInput.value.trim();
    
    if (!moodText) {
        showError('Please tell us how you are feeling!');
        return;
    }
    
    // Show loading state
    showLoading();
    
    try {
        const preference = preferenceSelect ? preferenceSelect.value : 'mixed';
        const limit = limitSelect ? parseInt(limitSelect.value, 10) : 10;
        const emoji = lastRequest.emoji || '';
        lastRequest = { moodText, preference, limit, emoji };

        const response = await fetch('/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mood_text: moodText, preference, limit, emoji })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Something went wrong');
        }
        
        // Display results
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to get movie recommendations. Please try again.');
    }
}

// Show loading state
function showLoading() {
    hideAllSections();
    loadingSection.classList.remove('hidden');
    findMoviesBtn.disabled = true;
    findMoviesBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Finding Movies...';
}

// Hide all sections
function hideAllSections() {
    loadingSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

// Display results
function displayResults(data) {
    hideAllSections();
    
    // Update mood display
    moodTitle.textContent = `You seem ${data.mood} ${data.emoji}`;
    if (data.fallback) {
        moodDescription.textContent = `Based on your input: "${data.user_input}" • Showing curated recommendations (${data.total_movies || data.movies.length} movies)`;
    } else {
        moodDescription.textContent = `Based on your input: "${data.user_input}" • Found ${data.total_movies || data.movies.length} movies from Hollywood & Bollywood`;
    }
    
    // Clear previous movies
    moviesGrid.innerHTML = '';
    
    // Display movies
    if (data.movies && data.movies.length > 0) {
        currentResults = data.movies;
        data.movies.forEach(movie => {
            const movieCard = createMovieCard(movie);
            moviesGrid.appendChild(movieCard);
        });
        if (loadMoreBtn) loadMoreBtn.classList.toggle('hidden', (data.total_movies || data.movies.length) < (lastRequest.limit || 10));
    } else {
        moviesGrid.innerHTML = '<p style="text-align: center; color: #888; grid-column: 1 / -1;">No movies found for your mood. Try a different description!</p>';
        if (loadMoreBtn) loadMoreBtn.classList.add('hidden');
    }
    
    resultsSection.classList.remove('hidden');
    resetButton();
}

// Create movie card element
function createMovieCard(movie) {
    const card = document.createElement('div');
    card.className = 'movie-card';
    
    const posterUrl = movie.poster_url && movie.poster_url !== 'null' ? movie.poster_url : 'https://via.placeholder.com/600x900/333/ffffff?text=No+Image';
    const rating = movie.rating || 0;
    const stars = generateStars(rating);
    
    card.innerHTML = `
        <img src="${posterUrl}" alt="${movie.title}" class="movie-poster" loading="lazy" referrerpolicy="no-referrer"
             onerror="this.onerror=null;this.src='https://via.placeholder.com/600x900/333/ffffff?text=No+Image'">
        <div class="movie-info">
            <h3 class="movie-title">${movie.title}</h3>
            <div class="movie-rating">
                <div class="rating-stars">${stars}</div>
                <span class="rating-value">${rating}/10</span>
            </div>
            <p class="movie-overview">${movie.overview}</p>
            <p class="movie-release">Released: ${movie.release_date}</p>
            <div class="movie-actions">
                <button class="btn tertiary details-btn">Details</button>
                <button class="btn secondary fav-btn">❤ Favorite</button>
            </div>
        </div>
    `;
    // Actions
    const detailsBtn = card.querySelector('.details-btn');
    detailsBtn.addEventListener('click', () => openDetailsModal(movie));
    const favBtn = card.querySelector('.fav-btn');
    favBtn.addEventListener('click', () => toggleFavorite(movie, favBtn));

    return card;
}

// Generate star rating display
function generateStars(rating) {
    const fullStars = Math.floor(rating / 2);
    const hasHalfStar = rating % 2 >= 1;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    let stars = '';
    
    // Full stars
    for (let i = 0; i < fullStars; i++) {
        stars += '<i class="fas fa-star"></i>';
    }
    
    // Half star
    if (hasHalfStar) {
        stars += '<i class="fas fa-star-half-alt"></i>';
    }
    
    // Empty stars
    for (let i = 0; i < emptyStars; i++) {
        stars += '<i class="far fa-star"></i>';
    }
    
    return stars;
}

// Show error message
function showError(message) {
    hideAllSections();
    errorText.textContent = message;
    errorSection.classList.remove('hidden');
    resetButton();
}

// Reset button state
function resetButton() {
    findMoviesBtn.disabled = false;
    findMoviesBtn.innerHTML = '<i class="fas fa-search"></i> Find Movies 🎥';
}

// Add some example mood suggestions
function addMoodSuggestions() {
    const suggestions = [
        "I feel happy and want to watch Bollywood comedy",
        "I'm feeling sad and need uplifting Indian movies",
        "I'm in the mood for romantic Bollywood movies",
        "I want to watch exciting action movies from India",
        "I'm feeling nostalgic and want classic Bollywood",
        "I need something to make me laugh - Bollywood comedy",
        "I want to watch thriller movies from Hollywood",
        "I'm in the mood for adventure movies from both industries"
    ];
    
    // Add clickable suggestions (optional enhancement)
    const suggestionContainer = document.createElement('div');
    suggestionContainer.className = 'mood-suggestions';
    suggestionContainer.innerHTML = `
        <p style="color: #888; margin-bottom: 1rem; font-size: 0.9rem;">💡 Try these examples:</p>
        <div class="suggestion-tags">
            ${suggestions.map(suggestion => 
                `<span class="suggestion-tag" onclick="moodInput.value='${suggestion}'">${suggestion}</span>`
            ).join('')}
        </div>
    `;
    
    // Insert after input container
    const inputContainer = document.querySelector('.input-container');
    inputContainer.appendChild(suggestionContainer);
}

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    // Add some initial styling for suggestions
    const style = document.createElement('style');
    style.textContent = `
        .mood-suggestions {
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255, 215, 0, 0.2);
        }
        
        .suggestion-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        
        .suggestion-tag {
            background: rgba(255, 215, 0, 0.1);
            border: 1px solid rgba(255, 215, 0, 0.3);
            border-radius: 20px;
            padding: 0.5rem 1rem;
            font-size: 0.8rem;
            color: #ffd700;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .suggestion-tag:hover {
            background: rgba(255, 215, 0, 0.2);
            transform: translateY(-2px);
        }
        
        @media (max-width: 768px) {
            .suggestion-tags {
                flex-direction: column;
            }
            
            .suggestion-tag {
                text-align: center;
            }
        }
    `;
    document.head.appendChild(style);
    
    // Add mood suggestions
    addMoodSuggestions();
    
    // Focus on input
    moodInput.focus();
});

// Emoji handling
const EMOJI_TO_MOOD = {
    '😊': 'happy', '😢': 'sad', '😠': 'angry', '😌': 'relaxed', '😴': 'bored',
    '🤩': 'excited', '💕': 'romantic', '😨': 'scared', '🕵️': 'mystery', '🚀': 'adventurous'
};

function handleEmojiClick(emoji) {
    lastRequest.emoji = emoji;
    const mood = EMOJI_TO_MOOD[emoji] || '';
    if (mood) {
        moodInput.value = `I feel ${mood.toLowerCase()} ${emoji}`;
    }
    handleFindMovies();
}

// Surprise Me
function handleSurpriseMe() {
    const samples = [
        'I feel happy and want Bollywood comedy',
        'I am bored and need an exciting thriller',
        'I feel romantic today',
        'I want something relaxing and calm',
        'I am angry and want action-packed movies'
    ];
    const pick = samples[Math.floor(Math.random() * samples.length)];
    moodInput.value = pick;
    handleFindMovies();
}

// Load More (re-run with higher limit)
async function handleLoadMore() {
    if (!lastRequest.moodText) return;
    limitSelect.value = String(Math.min((lastRequest.limit || 10) + 6, 20));
    await handleFindMovies();
}

// Favorites (localStorage)
function getFavorites() {
    try { return JSON.parse(localStorage.getItem('moodflix_favs') || '[]'); } catch { return []; }
}
function setFavorites(list) { localStorage.setItem('moodflix_favs', JSON.stringify(list)); }
function toggleFavorite(movie, btnEl) {
    const favs = getFavorites();
    const idx = favs.findIndex(m => (m.id || m.title) === (movie.id || movie.title));
    if (idx >= 0) {
        favs.splice(idx, 1);
        btnEl.classList.remove('active');
        btnEl.textContent = '❤ Favorite';
    } else {
        favs.push(movie);
        btnEl.classList.add('active');
        btnEl.textContent = '★ Favorited';
    }
    setFavorites(favs);
}

// Details Modal
const modal = document.getElementById('movie-modal');
const modalBody = document.getElementById('modal-body');
const modalClose = document.getElementById('modal-close');
if (modalClose) modalClose.addEventListener('click', closeModal);
if (modal) modal.addEventListener('click', (e) => { if (e.target.classList.contains('modal-backdrop')) closeModal(); });

function openDetailsModal(movie) {
    const posterUrl = movie.poster_url || 'https://via.placeholder.com/300x450/333/fff?text=No+Image';
    const googleQuery = encodeURIComponent(`${movie.title} trailer`);
    modalBody.innerHTML = `
        <div style="display:flex; gap:1rem; flex-wrap:wrap; align-items:flex-start;">
            <img src="${posterUrl}" alt="${movie.title}" style="width:220px; border-radius:12px; border:1px solid rgba(255,215,0,.25)" />
            <div style="flex:1; min-width:260px;">
                <h2 style="margin:0 0 .4rem 0; color:#ffd700;">${movie.title}</h2>
                <p style="color:#ccc; margin:.2rem 0;">Rating: <strong>${movie.rating || 'N/A'}</strong> • Released: ${movie.release_date || 'Unknown'}</p>
                <p style="color:#aaa; margin-top:.6rem; line-height:1.5;">${movie.overview || 'No overview available.'}</p>
                <div style="margin-top:1rem; display:flex; gap:.6rem; flex-wrap:wrap;">
                    <a class="btn secondary" href="https://www.youtube.com/results?search_query=${googleQuery}" target="_blank" rel="noopener">Watch Trailer</a>
                    <a class="btn tertiary" href="https://www.google.com/search?q=${encodeURIComponent(movie.title + ' movie')}" target="_blank" rel="noopener">Search on Google</a>
                </div>
                <div id="trailer-slot" style="margin-top:1rem"></div>
            </div>
        </div>
    `;
    modal.classList.remove('hidden');
    // Try to embed trailer
    fetch(`/trailer?title=${encodeURIComponent(movie.title)}&year=${encodeURIComponent((movie.release_date || '').slice(0,4))}`)
        .then(r => r.json()).then(({ videoId }) => {
            if (!videoId) return;
            const slot = document.getElementById('trailer-slot');
            slot.innerHTML = `<iframe width="100%" height="315" src="https://www.youtube.com/embed/${videoId}" frameborder="0" allowfullscreen style="border-radius:12px; border:1px solid rgba(255,255,255,.1)"></iframe>`;
        }).catch(() => {});
}
function closeModal() { modal.classList.add('hidden'); }
