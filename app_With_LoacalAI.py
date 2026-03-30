import streamlit as st
import pandas as pd
import requests
import pickle
from transformers import pipeline

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Movie Recommender", layout="wide")

# ---------------- LOAD MODEL ----------------
@st.cache_resource
def load_model():
    return pipeline(
        "text-generation",
        model="distilgpt2",
        pad_token_id=50256
    )

review_generator = load_model()

# ---------------- SESSION STATE ----------------
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []

if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

if "selected_movie_id" not in st.session_state:
    st.session_state.selected_movie_id = None

if "show_popup" not in st.session_state:
    st.session_state.show_popup = False

# ---------------- LOAD DATA ----------------
with open('movie_data.pkl', 'rb') as file:
    movies, cosine_sim = pickle.load(file)

# ---------------- FUNCTIONS ----------------
def get_recommendations(title):
    idx = movies[movies['title'] == title].index[0]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:11]
    movie_indices = [i[0] for i in sim_scores]
    return movies[['title', 'movie_id']].iloc[movie_indices]

def fetch_movie_details(movie_id):
    api_key = "7b995d3c6fd91a2284b4ad8cb390c7b8"
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    
    try:
        data = requests.get(url).json()
        return {
            "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None,
            "overview": data.get("overview"),
            "rating": data.get("vote_average")
        }
    except:
        return None

# -------- IMPROVED AI REVIEW --------
def generate_review(title, details):
    try:
        overview = details["overview"] if details and details["overview"] else ""

        prompt = f"{title} movie review:"

        result = review_generator(
            prompt,
            max_new_tokens=80,
            temperature=0.8,
            do_sample=True
        )

        text = result[0]["generated_text"]

        # remove prompt
        review = text.replace(prompt, "").strip()

        # 🔥 clean unwanted stuff
        if "Plot:" in review or len(review) < 20:
            review = f"{title} is a visually stunning and engaging film. It delivers strong performances and an immersive experience. Overall, it is definitely worth watching."

        # limit to 3 lines
        # review = ". ".join(review.split(". ")[:3]).strip()

        return review

    except:
        return f"{title} is an engaging movie with a compelling story and strong visuals. It keeps the audience interested throughout. Overall, it is worth watching."

# ---------------- UI ----------------
st.title("🎬 Movie Recommendation System")

selected_movie = st.selectbox("Choose a movie", movies['title'].values)

# -------- RECOMMEND --------
if st.button("Recommend Movies"):
    st.session_state.recommendations = get_recommendations(selected_movie)
    st.session_state.show_popup = False

# -------- SHOW MOVIES --------
if len(st.session_state.recommendations) > 0:
    st.subheader("Top Recommendations")

    recs = st.session_state.recommendations

    for i in range(0, 10, 5):
        cols = st.columns(5)

        for col, j in zip(cols, range(i, i+5)):
            if j < len(recs):
                movie_title = recs.iloc[j]['title']
                movie_id = recs.iloc[j]['movie_id']

                details = fetch_movie_details(movie_id)
                poster = details["poster"] if details and details["poster"] else "https://via.placeholder.com/500x750"

                with col:
                    st.image(poster, width="stretch")
                    st.markdown(f"<p style='text-align:center'>{movie_title}</p>", unsafe_allow_html=True)

                    if st.button("Review", key=f"{movie_title}_{j}"):
                        st.session_state.selected_movie = movie_title
                        st.session_state.selected_movie_id = movie_id
                        st.session_state.show_popup = True

# -------- POPUP --------
if st.session_state.show_popup:

    details = fetch_movie_details(st.session_state.selected_movie_id)

    with st.spinner("Generating AI review..."):
        review = generate_review(st.session_state.selected_movie, details)

    # Blur background
    st.markdown("""
    <div style="
        position:fixed;
        top:0;
        left:0;
        width:100%;
        height:100%;
        backdrop-filter: blur(8px);
        background: rgba(0,0,0,0.6);
        z-index:9998;
    "></div>
    """, unsafe_allow_html=True)

    # Popup
    st.markdown(f"""
    <div style="
        position:fixed;
        top:50%;
        left:50%;
        transform: translate(-50%, -50%);
        width:50%;
        background-color:#111827;
        padding:25px;
        border-radius:12px;
        box-shadow:0 0 25px rgba(0,0,0,0.8);
        z-index:9999;
        text-align:center;
    ">
        <h2 style='color:white'>{st.session_state.selected_movie}</h2>
        <p style='color:white'>{review}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("❌ Close Review"):
        st.session_state.show_popup = False