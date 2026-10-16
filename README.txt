MOVIE RATING ANALYTICS & RECOMMENDATION WEB PORTAL
==================================================

Technology:
- Python + Flask
- SQLite database
- Pandas for rating analytics
- scikit-learn TF-IDF and cosine similarity for content-based recommendations
- HTML/CSS + Chart.js for the web pages and charts

FEATURES:
1. User registration, login, logout
2. Movie catalog with title search and genre/language filters
3. User ratings from 1 to 5 stars
4. Rating analytics: highest-rated movies, genre statistics, rating distribution
5. Content-based recommendation engine
6. Admin dashboard: add/delete movies and promote users to admin
7. Recommendations are saved in the recommendations table

HOW TO RUN ON WINDOWS / VS CODE:
1. Extract this ZIP file.
2. Open the extracted folder in VS Code.
3. Open Terminal > New Terminal.
4. (Recommended) Create a virtual environment:
       py -m venv venv
       .\venv\Scripts\activate
   If `py` does not work, try `python` instead.
5. Install packages:
       python -m pip install -r requirements.txt
6. Start the project:
       python app.py
7. Open this address in your browser:
       http://127.0.0.1:5000
8. Create a user account, log in, browse movies, and rate several movies.
9. Visit “For You” to see recommendations. Rate horror movies highly to get more similar horror suggestions.

HOW TO MAKE YOUR ACCOUNT AN ADMIN:
1. First run the app and register your account.
2. Stop the server in the terminal using Ctrl+C.
3. Run:
       python make_admin.py
4. Enter the email you registered with.
5. Restart:
       python app.py
6. Log out and log back in. The Admin link will appear.

DATABASE:
The SQLite database file `movie_portal.db` is created automatically on first run.
Tables: users, movies, ratings, recommendations.
Movie descriptions and tags are included to improve similarity recommendations.

HOW THE RECOMMENDATION WORKS:
- TF-IDF converts movie titles, genres, tags, descriptions, and languages into numeric vectors.
- Cosine similarity finds movies that are similar in content.
- Movies similar to those you rated 4 or 5 stars receive a higher score.
- Similarity to movies rated 1 or 2 stars lowers the score a little.
- A small rating/popularity signal is also included.
- Already-rated movies are not recommended again.

PROJECT NOTE:
This is a student-project prototype. Before public deployment, change SECRET_KEY,
add CSRF protection, validate inputs further, and use production hosting settings.
