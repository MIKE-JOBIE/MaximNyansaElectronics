import time

from flask import current_app
from .models import SiteSetting
from .extensions import db

# Site settings are read on every page. Cache them briefly per process so a busy
# site does not hit the database for them on every single request.
_CACHE = {"at": 0.0, "value": None}
_TTL_SECONDS = 60


def invalidate_cache():
    _CACHE["value"] = None

DEFAULTS = {
    "brand_name":       "Maxim Nyansa Electronics",
    "brand_phone":      "+232 31 950 662",
    "brand_email":      "michaeljobi@maximnyansa.com",
    "brand_address":    "5C BaiBureh Road, Ferry Junction, Freetown, Sierra Leone",
    "brand_tagline":    "Skills Today, Success Tomorrow",
    "announcement_active": "false",
    "announcement_banner": "",
    "impact_trained":   "13",
    "impact_practical": "90",
    "impact_kits":      "10",
    "impact_target":    "80",
    "brand_whatsapp":   "23231950662",          
    "social_facebook":  "https://www.facebook.com/share/1Dd3pZPU5b/?mibextid=wwXIfr",
    "social_linkedin":  "https://www.linkedin.com/company/maxim-nyansa-foundation/",
    "social_instagram": "https://www.instagram.com/mjobie2009?stkn=MTZzNmlha3VlNmVsaA%3D%3D&utm_source=qr",
    "social_youtube":   "",
}


def seed_default_settings():
    for k, v in DEFAULTS.items():
        if not SiteSetting.query.filter_by(key=k).first():
            db.session.add(SiteSetting(key=k, value=v))
    db.session.commit()


def get_setting(key, default=None):
    return SiteSetting.get(key, default if default is not None else DEFAULTS.get(key, ""))


def get_all_settings():
    use_cache = not current_app.testing
    now = time.monotonic()
    if use_cache and _CACHE["value"] is not None and now - _CACHE["at"] < _TTL_SECONDS:
        return dict(_CACHE["value"])
    result = dict(DEFAULTS)
    result.update(SiteSetting.all_dict())
    if use_cache:
        _CACHE.update(at=now, value=result)
    return dict(result)