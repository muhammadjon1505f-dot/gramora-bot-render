import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOT_TOKEN = os.getenv("UZBSTARSBUY_BOT_TOKEN", "9201777867:AAFGPMm-qx96DP8pAQH691FmUjzZvjIvg1A")

# Admin IDs (Owner + Co-owner)
ADMIN_IDS = [
    8893717129,  # Primary owner
    8191930658   # Secondary admin
]

# Paths
START_PHOTO = os.path.join(BASE_DIR, "start_photo.jpg")
AVATAR_PHOTO = os.path.join(BASE_DIR, "avatar.jpg")
DESC_PHOTO = os.path.join(BASE_DIR, "desc_photo.jpg")
WEBAPP_DIR = os.path.join(BASE_DIR, "web_app")

# Default URLs
render_base = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("APP_URL")
if render_base:
    DEFAULT_WEBAPP_URL = f"{render_base.rstrip('/')}/stars"
else:
    DEFAULT_WEBAPP_URL = "https://liquidstars.vercel.app/"
DEFAULT_VIDEO_GUIDE_URL = "https://t.me/legenda_ovoz_ishonch/5"
DEFAULT_INSTAGRAM_URL = "https://www.instagram.com/uzbstarsbu?cplk=MXJtb2lzZ3Y2Zmd3Zw=="
DEFAULT_NEWS_CHANNEL = "@UZBStarsbuy"
SUPPORT_ADMIN = "@legenda_adminn"
