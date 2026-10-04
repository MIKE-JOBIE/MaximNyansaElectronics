"""
Audit all registered routes. Run: python check_pages.py
"""
import os
os.environ.setdefault("FLASK_APP", "wsgi.py")

from app import create_app

app = create_app()

public = []
auth_required = []
admin_only = []

with app.test_request_context():
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r.rule)):
        if rule.endpoint == "static":
            continue
        methods = ",".join(sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")))
        entry = f"{methods:<12} {rule.rule:<55} → {rule.endpoint}"
        if rule.rule.startswith("/admin"):
            admin_only.append(entry)
        elif "auth" in rule.endpoint or rule.rule.startswith("/auth"):
            auth_required.append(entry)
        else:
            public.append(entry)

def show(title, items):
    print(f"\n═══ {title} ({len(items)}) ═══")
    for it in items:
        print(f"  {it}")

show("PUBLIC", public)
show("AUTH / ACCOUNT", auth_required)
show("ADMIN", admin_only)

print(f"\n✅ Total: {len(public) + len(auth_required) + len(admin_only)} routes\n")