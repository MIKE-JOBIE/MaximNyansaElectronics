from .models import SiteSetting
from .extensions import db

DEFAULTS = {
    "brand_name":       "Maxim Nyansa Electronics",
    "brand_phone":      "+232 31 950 662",
    "brand_email":      "info@maximnyansa.com",
    "brand_address":    "5C BaiBureh Road, Ferry Junction, Freetown, Sierra Leone",
    "brand_tagline":    "Skills Today, Success Tomorrow",
    "announcement_active": "false",
    "announcement_banner": "",
    "impact_trained":   "13",
    "impact_practical": "90",
    "impact_kits":      "10",
    "impact_target":    "80",
    "social_facebook":  "",
    "social_linkedin":  "https://www.linkedin.com/company/maxim-nyansa-foundation/",
    "social_instagram": "",
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
    result = dict(DEFAULTS)
    result.update(SiteSetting.all_dict())
    return result