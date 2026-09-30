from flask import render_template, request
from . import library_bp
from ...models import VideoTestimonial


@library_bp.route("/videos")
def videos():
    vids = VideoTestimonial.query.filter_by(is_published=True)\
        .order_by(VideoTestimonial.featured.desc(),
                  VideoTestimonial.created_at.desc()).all()
    return render_template("library/videos.html", videos=vids)