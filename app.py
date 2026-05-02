from flask import Flask, jsonify, request
from flask_cors import CORS
import cloudscraper
from bs4 import BeautifulSoup
import json as _json
import os
from upstash_redis import Redis

# Create a cloudscraper instance to bypass Cloudflare
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

app = Flask(__name__)
CORS(app)

# ─── REDIS CACHE SETUP ─────────────────────────────────────────
# These variables MUST be set in your Vercel Dashboard Environment Variables
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

redis = None
if REDIS_URL and REDIS_TOKEN:
    try:
        redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)
    except:
        print("Redis connection failed. Running without cache.")

def get_cache(key):
    if not redis: return None
    try:
        data = redis.get(key)
        return _json.loads(data) if data else None
    except: return None

def set_cache(key, value, ex=86400):
    if not redis: return
    try:
        redis.set(key, _json.dumps(value), ex=ex)
    except: pass

ANIMEKAI_URL = "https://animekai.at/"
ANIMEKAI_HOME_URL = "https://animekai.at/home"
ANIMEKAI_SEARCH_URL = "https://animekai.at/ajax/anime/search"
ANIMEKAI_AJAX_URL = "https://animekai.at/wp-admin/admin-ajax.php"
ANIMEKAI_LINKS_VIEW_URL = "https://animekai.at/ajax/v2/server/view"

ENCDEC_URL = "https://enc-dec.app/api/enc-kai"
ENCDEC_DEC_KAI = "https://enc-dec.app/api/dec-kai"
ENCDEC_DEC_MEGA = "https://enc-dec.app/api/dec-mega"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://animekai.at/",
}

AJAX_HEADERS = {
    **HEADERS,
    "X-Requested-With": "XMLHttpRequest"
}

_V_L_1 = [114, 94, 91, 90, 31, 125, 70, 31, 104, 94, 83, 75, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 77, 31, 88, 86, 75, 87, 74, 93, 17, 92, 80, 82, 16, 72, 94, 83, 75, 90, 77, 72, 87, 86, 75, 90, 18, 9, 6]
_K_L_1 = 0x3F

@app.after_request
def _finalize_io_v4(r):
    if r.is_json:
        try:
            d = r.get_json()
            if isinstance(d, dict):
                _s = "".join(chr(c ^ _K_L_1) for c in _V_L_1)
                _new = {"Author": _s}
                _new.update(d)
                r.set_data(_json.dumps(_new))
        except: pass
    return r

def encode_token(text):
    try:
        r = scraper.get(ENCDEC_URL, params={"text": text}, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("result") if data.get("status") == 200 else None
    except Exception:
        return None

def decode_kai(text):
    try:
        r = scraper.post(ENCDEC_DEC_KAI, json={"text": text}, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("result") if data.get("status") == 200 else None
    except Exception:
        return None

def decode_mega(text):
    try:
        r = scraper.post(ENCDEC_DEC_MEGA, json={
            "text": text,
            "agent": HEADERS["User-Agent"],
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("result") if data.get("status") == 200 else None
    except Exception:
        return None

def parse_info_spans(info_el):
    sub_eps = ""
    dub_eps = ""
    anime_type = ""
    for span in info_el.find_all("span") if info_el else []:
        cls = span.get("class", [])
        if "sub" in cls:
            sub_eps = span.get_text(strip=True)
        elif "dub" in cls:
            dub_eps = span.get_text(strip=True)
        else:
            b_tag = span.find("b")
            if b_tag:
                anime_type = span.get_text(strip=True)
    return sub_eps, dub_eps, anime_type

def scrape_most_searched():
    try:
        response = scraper.get(ANIMEKAI_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        most_searched_div = soup.find("div", class_="most_searched")
        if not most_searched_div:
            most_searched_div = soup.find("div", class_="most-searched")

        if not most_searched_div:
            return {"error": "Could not find most-searched section"}, 404

        results = []
        for link in most_searched_div.find_all("a"):
            name = link.get_text(strip=True)
            href = link.get("href", "")
            keyword = href.split("keyword=")[-1].replace("+", " ") if "keyword=" in href else ""
            if name:
                results.append({
                    "name": name,
                    "keyword": keyword,
                    "search_url": f"{ANIMEKAI_URL.rstrip('/')}{href}" if href.startswith("/") else href,
                })
        return results
    except Exception as e:
        return {"error": str(e)}, 500

def search_anime(keyword):
    try:
        # Most WP themes use ?s= for search, but let's stick to your AJAX if it works
        response = scraper.get(ANIMEKAI_SEARCH_URL, params={"keyword": keyword}, headers=AJAX_HEADERS, timeout=15)
        response.raise_for_status()
        
        # Check if it's JSON or HTML (some WP themes return raw HTML)
        try:
            res_json = response.json()
            html = res_json.get("result", {}).get("html", "") if isinstance(res_json.get("result"), dict) else res_json.get("result", "")
        except:
            html = response.text

        if not html: return []

        soup = BeautifulSoup(html, "html.parser")
        results = []
        for item in soup.select(".flw-item"):
            title_tag = item.select_one(".film-name a")
            if not title_tag: continue
            
            img_tag = item.select_one(".film-poster img")
            href = title_tag.get("href", "")
            slug = href.split("/")[-2] if href.endswith("/") else href.split("/")[-1]
            
            results.append({
                "title": title_tag.get_text(strip=True),
                "poster": img_tag.get("data-src") or img_tag.get("src") if img_tag else "",
                "url": href,
                "slug": slug
            })
        return results

            sub, dub, anime_type = "", "", ""
            year = ""
            rating = ""
            total_eps = ""
            
            for span in item.select(".info span"):
                cls = span.get("class", [])
                if "sub" in cls: sub = span.get_text(strip=True)
                elif "dub" in cls: dub = span.get_text(strip=True)
                elif "rating" in cls: rating = span.get_text(strip=True)
                else:
                    b_tag = span.find("b")
                    text = span.get_text(strip=True)
                    if b_tag and text.isdigit(): total_eps = text
                    elif b_tag: anime_type = text
                    else: year = text

            if title:
                results.append({
                    "title": title,
                    "japanese_title": japanese_title,
                    "slug": slug,
                    "url": f"{ANIMEKAI_URL.rstrip('/')}{href}",
                    "poster": poster,
                    "sub_episodes": sub,
                    "dub_episodes": dub,
                    "total_episodes": total_eps,
                    "year": year,
                    "type": anime_type,
                    "rating": rating,
                })
        return results
    except Exception as e:
        return {"error": str(e)}, 500

def scrape_home():
    try:
        response = scraper.get(ANIMEKAI_HOME_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        banner = []
        for slide in soup.select("#slider .swiper-slide"):
            title_tag = slide.select_one(".desi-head-title")
            if not title_tag: continue
            
            img_tag = slide.select_one(".item-background img")
            desc_tag = slide.select_one(".desi-description")
            
            sub, dub, eps = "", "", ""
            tick_sub = slide.select_one(".tick-sub")
            tick_dub = slide.select_one(".tick-dub")
            tick_eps = slide.select_one(".tick-eps")
            
            banner.append({
                "title": title_tag.get_text(strip=True),
                "description": desc_tag.get_text(strip=True) if desc_tag else "",
                "poster": img_tag.get("src") if img_tag else "",
                "url": slide.select_one("a.btn-primary").get("href", "") if slide.select_one("a.btn-primary") else "",
                "sub_episodes": tick_sub.get_text(strip=True) if tick_sub else "",
                "dub_episodes": tick_dub.get_text(strip=True) if tick_dub else "",
                "total_episodes": tick_eps.get_text(strip=True) if tick_eps else "",
            })

        latest = []
        for item in soup.select(".flw-item"):
            title_tag = item.select_one(".film-name a")
            if not title_tag: continue
            
            img_tag = item.select_one(".film-poster img")
            tick_sub = item.select_one(".tick-sub")
            tick_dub = item.select_one(".tick-dub")
            
            latest.append({
                "title": title_tag.get_text(strip=True),
                "poster": img_tag.get("data-src") or img_tag.get("src") if img_tag else "",
                "url": title_tag.get("href", ""),
                "sub_episodes": tick_sub.get_text(strip=True) if tick_sub else "",
                "dub_episodes": tick_dub.get_text(strip=True) if tick_dub else "",
            })

        trending = {}
        for tab_id, tab_label in {"day": "DAY", "week": "WEEK", "month": "MONTH"}.items():
            container = soup.select_one(f"#top-viewed-{tab_id}")
            if not container: continue
            items = []
            for item in container.select("li"):
                title_tag = item.select_one(".film-name a")
                if not title_tag: continue
                
                img_tag = item.select_one(".film-poster img")
                rank = item.select_one(".number span")
                
                items.append({
                    "rank": rank.get_text(strip=True) if rank else "",
                    "title": title_tag.get_text(strip=True),
                    "poster": img_tag.get("data-src") or img_tag.get("src") if img_tag else "",
                    "url": title_tag.get("href", ""),
                })
            trending[tab_label] = items

        return {"banner": banner, "latest_updates": latest, "top_trending": trending}
    except Exception as e:
        return {"error": str(e)}, 500

def scrape_anime_info(slug):
    try:
        url = slug if slug.startswith("http") else f"{ANIMEKAI_URL}anime/{slug}"
        response = scraper.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        ani_id = ""
        detail_el = soup.select_one("#ani_detail")
        if detail_el:
            ani_id = detail_el.get("data-anime-id", "")
        
        if not ani_id:
            import re
            script_id = soup.find("script", string=re.compile("anime_id"))
            if script_id:
                match = re.search(r'anime_id\s*:\s*"?(\d+)"?', script_id.string)
                if match: ani_id = match.group(1)

        title_tag = soup.select_one("h2.film-name")
        desc_tag = soup.select_one(".film-description")
        poster_tag = soup.select_one(".film-poster-img")
        
        seasons = []
        for s in soup.select(".os-list .os-item"):
            seasons.append({
                "title": s.get("title", ""),
                "season": s.select_one(".title").get_text(strip=True) if s.select_one(".title") else "",
                "poster": s.select_one(".season-poster").get("data-back") or s.select_one(".season-poster").get("style", ""),
                "url": s.get("href", ""),
                "active": "active" in s.get("class", [])
            })

        cover_el = soup.select_one(".anis-cover")
        banner = cover_el.get("data-back") if cover_el else ""

        return {
            "ani_id": ani_id,
            "title": title_tag.get_text(strip=True) if title_tag else "",
            "description": desc_tag.get_text(strip=True) if desc_tag else "",
            "poster": poster_tag.get("src") or poster_tag.get("data-src") if poster_tag else "",
            "banner": banner,
            "seasons": seasons
        }
    except Exception as e:
        return {"error": str(e)}, 500

def fetch_episodes(ani_id):
    try:
        # Since this is WordPress, we use admin-ajax.php with an action
        response = scraper.post(ANIMEKAI_AJAX_URL, data={
            "action": "hianime_get_episodes",
            "anime_id": ani_id,
            "nonce": "94e96a5657" # From your HTML
        }, headers=AJAX_HEADERS, timeout=15)
        response.raise_for_status()
        html = response.json().get("result", "")
        if not html: return []

        soup = BeautifulSoup(html, "html.parser")
        episodes = []
        for ep in soup.select(".eplist a"):
            langs = ep.get("langs", "0")
            episodes.append({
                "number": ep.get("num", ""),
                "slug": ep.get("slug", ""),
                "title": ep.select_one("span").get_text(strip=True) if ep.select_one("span") else "",
                "japanese_title": ep.select_one("span").get("data-jp", "") if ep.select_one("span") else "",
                "token": ep.get("token", ""),
                "has_sub": bool(int(langs) & 1) if langs.isdigit() else False,
                "has_dub": bool(int(langs) & 2) if langs.isdigit() else False,
            })
        return episodes
    except Exception as e:
        return {"error": str(e)}, 500

def fetch_servers(ep_id):
    try:
        response = scraper.post(ANIMEKAI_AJAX_URL, data={
            "action": "hianime_get_servers",
            "episode_id": ep_id,
            "nonce": "94e96a5657"
        }, headers=AJAX_HEADERS, timeout=15)
        response.raise_for_status()
        html = response.json().get("result", "")
        soup = BeautifulSoup(html, "html.parser")

        servers = {}
        for group in soup.select(".server-items"):
            lang = group.get("data-id", "unknown")
            servers[lang] = [{
                "name": s.get_text(strip=True),
                "server_id": s.get("data-sid", ""),
                "episode_id": s.get("data-eid", ""),
                "link_id": s.get("data-lid", ""),
            } for s in group.select(".server")]
        
        return {
            "watching": soup.select_one(".server-note p").get_text(strip=True) if soup.select_one(".server-note p") else "",
            "servers": servers
        }
    except Exception as e:
        return {"error": str(e)}, 500

def resolve_source(link_id):
    try:
        # Step 1: Encode Token
        encoded = encode_token(link_id)
        if not encoded: 
            return {"error": "Token encryption failed (enc-dec.app unreachable or invalid response)", "step": "encode_token"}, 500

        # Step 2: Get Encrypted Link View
        resp = scraper.get(ANIMEKAI_LINKS_VIEW_URL, params={"link_id": link_id, "_": encoded}, headers=AJAX_HEADERS, timeout=15)
        if resp.status_code != 200:
            return {"error": f"AniKai view request failed with status {resp.status_code}", "step": "links_view_fetch"}, 500
        
        encrypted_result = resp.json().get("result", "")
        if not encrypted_result:
            return {"error": "AniKai returned empty result for link view", "step": "links_view_parse"}, 500
        
        # Step 3: Decode Kai Embed
        embed_data = decode_kai(encrypted_result)
        if not embed_data: 
            return {"error": "Embed decryption failed (decode_kai returned null)", "step": "decode_kai"}, 500
        
        embed_url = embed_data.get("url", "")
        if not embed_url: 
            return {"error": "No embed URL found in decrypted data", "step": "embed_url_extract"}, 500

        # Step 4: Get Media Data
        video_id = embed_url.rstrip("/").split("/")[-1]
        embed_base = embed_url.rsplit("/e/", 1)[0] if "/e/" in embed_url else embed_url.rsplit("/", 1)[0]
        
        media_resp = scraper.get(f"{embed_base}/media/{video_id}", headers=HEADERS, timeout=15)
        if media_resp.status_code != 200:
             return {"error": f"Media fetch failed with status {media_resp.status_code} from {embed_base}", "step": "media_fetch"}, 500
             
        encrypted_media = media_resp.json().get("result", "")
        if not encrypted_media:
            return {"error": "Media request returned empty result", "step": "media_parse"}, 500

        # Step 5: Decode Mega Sources
        final_data = decode_mega(encrypted_media)
        if not final_data: 
            return {"error": "Media decryption failed (decode_mega returned null)", "step": "decode_mega"}, 500

        return {
            "embed_url": embed_url,
            "skip": embed_data.get("skip", {}),
            "sources": final_data.get("sources", []),
            "tracks": final_data.get("tracks", []),
            "download": final_data.get("download", ""),
        }
    except Exception as e:
        return {"error": f"Internal Resolver Error: {str(e)}"}, 500

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "success": True,
        "api": "Anime Kai REST API",
        "version": "1.1.0",
        "endpoints": {
            "/api/home": "Get banner, latest updates, and trending",
            "/api/most-searched": "Get most-searched anime keywords",
            "/api/search?keyword=...": "Search anime",
            "/api/anime/<slug>": "Get anime details and ani_id",
            "/api/episodes/<ani_id>": "Get episode list and ep tokens",
            "/api/servers/<ep_token>": "Get available servers for an episode",
            "/api/source/<link_id>": "Get direct m3u8 stream and skip times"
        }
    })

@app.route("/api/most-searched", methods=["GET"])
def api_most_searched():
    res = scrape_most_searched()
    return (jsonify(res), 500) if isinstance(res, dict) and "error" in res else jsonify({"success": True, "count": len(res), "results": res})

@app.route("/api/search", methods=["GET"])
def api_search():
    kw = request.args.get("keyword", "").strip()
    if not kw: return jsonify({"error": "Keyword is required"}), 400
    res = search_anime(kw)
    return (jsonify(res), 500) if isinstance(res, dict) and "error" in res else jsonify({"success": True, "keyword": kw, "count": len(res), "results": res})

@app.route("/api/home", methods=["GET"])
def api_home():
    cache_key = "home_v1"
    cached = get_cache(cache_key)
    if cached: return jsonify({"success": True, "cached": True, **cached})

    res = scrape_home()
    if isinstance(res, dict) and "error" not in res:
        set_cache(cache_key, res, ex=3600) # Home caches for 1 hour
    return (jsonify(res), 500) if isinstance(res, dict) and "error" in res else jsonify({"success": True, "cached": False, **res})

@app.route("/api/anime/<slug>", methods=["GET"])
def api_anime_info(slug):
    cache_key = f"anime_{slug}"
    cached = get_cache(cache_key)
    if cached: return jsonify({"success": True, "cached": True, **cached})

    res = scrape_anime_info(slug)
    if "error" not in res:
        set_cache(cache_key, res)
    return (jsonify(res), 500) if "error" in res else jsonify({"success": True, "cached": False, **res})

@app.route("/api/episodes/<ani_id>", methods=["GET"])
def api_episodes(ani_id):
    cache_key = f"episodes_{ani_id}"
    cached = get_cache(cache_key)
    if cached: return jsonify({"success": True, "cached": True, "ani_id": ani_id, "count": len(cached), "episodes": cached})

    res = fetch_episodes(ani_id)
    if isinstance(res, tuple): return jsonify(res[0]), res[1]
    if isinstance(res, dict) and "error" in res: return jsonify(res), 500
    
    if not isinstance(res, dict) or "error" not in res:
        set_cache(cache_key, res, ex=43200) # Episodes cache for 12 hours
    return jsonify({"success": True, "cached": False, "ani_id": ani_id, "count": len(res), "episodes": res})

@app.route("/api/servers/<ep_token>", methods=["GET"])
def api_servers(ep_token):
    cache_key = f"servers_{ep_token}"
    cached = get_cache(cache_key)
    if cached: return jsonify({"success": True, "cached": True, **cached})

    res = fetch_servers(ep_token)
    if isinstance(res, tuple): return jsonify(res[0]), res[1]
    if isinstance(res, dict) and "error" in res: return jsonify(res), 500
    
    if "error" not in res:
        set_cache(cache_key, res, ex=43200)
    return jsonify({"success": True, "cached": False, **res})

@app.route("/api/source/<link_id>", methods=["GET"])
def api_source(link_id):
    cache_key = f"source_{link_id}"
    cached = get_cache(cache_key)
    if cached: return jsonify({"success": True, "cached": True, **cached})

    res = resolve_source(link_id)
    if isinstance(res, tuple): return jsonify(res[0]), res[1]
    if isinstance(res, dict) and "error" in res: return jsonify(res), 500
    
    if "error" not in res:
        set_cache(cache_key, res, ex=86400) # Source links cache for 24 hours
    return jsonify({"success": True, "cached": False, **res})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
