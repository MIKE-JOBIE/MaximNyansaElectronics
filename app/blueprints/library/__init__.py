from flask import Blueprint, render_template, request
from ...models import Resource

library_bp = Blueprint("library", __name__, template_folder="../../templates/library")

@library_bp.route("/")
def index():
    cat = request.args.get("cat")
    q = Resource.query
    if cat: q = q.filter_by(category=cat)
    resources = q.order_by(Resource.created_at.desc()).all()
    cats = [c[0] for c in Resource.query.with_entities(Resource.category).distinct().all() if c[0]]
    return render_template("library/index.html", resources=resources, categories=cats, current_cat=cat)

@library_bp.route("/resource/<slug>")
def resource(slug):
    r = Resource.query.filter_by(slug=slug).first_or_404()
    return render_template("library/resource.html", resource=r)

from . import video_routes  # noqa