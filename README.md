# 🚀 AnimeKAI REST API (v1.1.0)

A high-performance, Flask-based REST API for scraping and decrypting anime content from AnimeKAI. Optimized for speed and stability with Upstash Redis caching.

---

## 🌟 Features
- **Fast Scraping**: Extracts data from AnimeKAI with optimized headers.
- **Auto-Decryption**: Integrated support for resolving encrypted m3u8 streams and skip times.
- **Intelligent Caching**: Powered by Upstash Redis to prevent server overload and bypass rate limits.
- **Detailed Error Handling**: Clear, step-by-step error reporting for easier debugging.
- **CORS Enabled**: Ready for integration with any frontend or streaming platform.

---

## 🔗 Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/home` | Get banner slides, latest updates, and trending anime. |
| `GET` | `/api/search?keyword=...` | Search for anime by title or keyword. |
| `GET` | `/api/anime/<slug>` | Get full metadata, description, and `ani_id`. |
| `GET` | `/api/episodes/<ani_id>` | Get the full episode list and decryption tokens. |
| `GET` | `/api/servers/<ep_token>` | Get all available Sub/Dub/Softsub mirrors. |
| `GET` | `/api/source/<link_id>` | **The Prize**: Get direct m3u8 links, skip times, and tracks. |

---

## 🛠️ Deployment (Vercel)

1. **Fork/Upload**: Push this repository to your GitHub.
2. **Import**: Create a new project on Vercel and import the repository.
3. **Configure Environment Variables**:
   To enable caching and prevent "Overloaded" errors, you **must** set up Upstash Redis:
   - `UPSTASH_REDIS_REST_URL`: Your Upstash REST URL.
   - `UPSTASH_REDIS_REST_TOKEN`: Your Upstash REST Token.
4. **Deploy**: Vercel will automatically install dependencies from `requirements.txt`.

---

## 📦 Local Setup

1. **Clone the repo**:
   ```bash
   git clone https://github.com/your-repo/AnimeKAI-API.git
   cd AnimeKAI-API
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the server**:
   ```bash
   python app.py
   ```

---

## ⚠️ Disclaimer
This project is for **educational purposes only**. The API does not host any content but merely scrapes publicly available information. Use at your own risk.

---

**Developed for KagePlay Ecosystem** ⚡
