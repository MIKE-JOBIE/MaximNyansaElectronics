"""
Backup and restore admin-added content.
Usage:
    flask backup-export    → dumps all content to backup_content.json
    flask backup-import    → loads content from backup_content.json (skips existing)
"""
import json
import os
import click
from datetime import datetime
from flask.cli import with_appcontext
from .extensions import db
from .models import (User, Program, Product, Category, Resource,
                     Post, VideoTestimonial, SiteSetting, Message,
                     Donation, Order, Application)


def _serialize(obj):
    """Convert a SQLAlchemy object to a plain dict."""
    d = {}
    for col in obj.__table__.columns:
        v = getattr(obj, col.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        elif hasattr(v, "isoformat"):
            v = v.isoformat()
        elif hasattr(v, "quantize"):  # Decimal
            v = float(v)
        d[col.name] = v
    return d


def _to_dict(model, exclude_pk=True, exclude_fks=None):
    exclude_fks = exclude_fks or []
    rows = []
    for obj in model.query.all():
        d = _serialize(obj)
        if exclude_pk:
            d.pop("id", None)
        for k in exclude_fks:
            d.pop(k, None)
        # Remove password hash (never export)
        d.pop("password_hash", None)
        rows.append(d)
    return rows


def export_backup(path="backup_content.json"):
    """Dump admin-content tables to JSON."""
    data = {
        "_meta": {
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        },
        "categories":         _to_dict(Category, exclude_pk=True),
        "programs":           _to_dict(Program, exclude_pk=True),
        "products":           _to_dict(Product, exclude_pk=True, exclude_fks=["category_id"]),
        "resources":          _to_dict(Resource, exclude_pk=True),
        "posts":              _to_dict(Post, exclude_pk=True),
        "videos":             _to_dict(VideoTestimonial, exclude_pk=True, exclude_fks=["program_id"]),
        "site_settings":      _to_dict(SiteSetting, exclude_pk=True),
        # Messages, donations, orders, applications are user-generated —
        # export them too if you want a full copy
        "messages":           _to_dict(Message, exclude_pk=True),
        "applications":       _to_dict(Application, exclude_pk=True, exclude_fks=["user_id", "program_id"]),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    click.echo(f"✅ Exported to {path}")
    click.echo(f"   Categories:      {len(data['categories'])}")
    click.echo(f"   Programs:        {len(data['programs'])}")
    click.echo(f"   Products:        {len(data['products'])}")
    click.echo(f"   Resources:       {len(data['resources'])}")
    click.echo(f"   Posts:           {len(data['posts'])}")
    click.echo(f"   Videos:          {len(data['videos'])}")
    click.echo(f"   Site settings:   {len(data['site_settings'])}")
    click.echo(f"   Messages:        {len(data['messages'])}")
    click.echo(f"   Applications:    {len(data['applications'])}")


def _rehydrate(model, rows, fk_map=None, skip_if_exists_field=None):
    """Insert rows if they don't already exist."""
    added = 0
    for row in rows:
        # Skip if a natural key already exists
        if skip_if_exists_field and row.get(skip_if_exists_field):
            existing = model.query.filter(
                getattr(model, skip_if_exists_field) == row[skip_if_exists_field]
            ).first()
            if existing:
                continue
        # Remap any foreign keys
        if fk_map:
            for local_fk, (target_field, target_map) in fk_map.items():
                if local_fk in row and row[local_fk] is not None:
                    row[local_fk] = target_map.get(row[local_fk])
        # Convert ISO dates back to datetime
        for k, v in list(row.items()):
            if isinstance(v, str) and "T" in v and len(v) >= 19:
                try:
                    row[k] = datetime.fromisoformat(v)
                except Exception:
                    pass
        try:
            obj = model(**row)
            db.session.add(obj)
            added += 1
        except Exception as e:
            click.echo(f"   ⚠️  Skipped {model.__name__} row: {e}")
    db.session.commit()
    return added


def import_backup(path="backup_content.json"):
    """Load JSON into the current DB."""
    if not os.path.exists(path):
        click.echo(f"❌ File not found: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Site settings — merge by key
    for s in data.get("site_settings", []):
        existing = SiteSetting.query.filter_by(key=s["key"]).first()
        if existing:
            existing.value = s["value"]
        else:
            db.session.add(SiteSetting(key=s["key"], value=s["value"]))
    db.session.commit()
    click.echo(f"✅ Site settings: {len(data.get('site_settings', []))} processed")

    # Simple inserts
    for table, model, key in [
        ("categories", Category, "slug"),
        ("programs",   Program,  "slug"),
        ("resources",  Resource, "slug"),
        ("posts",      Post,     "slug"),
        ("messages",   Message,  None),
    ]:
        added = _rehydrate(model, data.get(table, []), skip_if_exists_field=key)
        click.echo(f"✅ {table}: {added} added")

    # Products need category remapping
    cat_map = {c.name: c.id for c in Category.query.all()}
    for p in data.get("products", []):
        # find by slug
        if Product.query.filter_by(slug=p["slug"]).first():
            continue
        prod = Product(
            name=p["name"], slug=p["slug"], description=p.get("description"),
            price=p["price"], stock=p.get("stock", 0),
            condition=p.get("condition", "new"),
            category_id=cat_map.get(p.get("category_name")) or None,
            image=p.get("image"), is_active=p.get("is_active", True),
        )
        db.session.add(prod)
    db.session.commit()
    click.echo(f"✅ products processed")

    # Videos
    added = _rehydrate(VideoTestimonial, data.get("videos", []),
                       skip_if_exists_field="title")
    click.echo(f"✅ videos: {added} added")

    click.echo("🎉 Import complete")


def register_backup_commands(app):
    @app.cli.command("backup-export")
    @with_appcontext
    def cli_export():
        """Export admin content to backup_content.json"""
        export_backup()

    @app.cli.command("backup-import")
    @with_appcontext
    def cli_import():
        """Import content from backup_content.json"""
        import_backup()