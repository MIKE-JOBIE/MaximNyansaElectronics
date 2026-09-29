from flask import Blueprint, render_template, request, flash, redirect, url_for
from ...models import Post, Program, Message
from ...forms import ContactForm
from ...extensions import db

main_bp = Blueprint("main", __name__, template_folder="../../templates/main")

@main_bp.route("/")
def index():
    programs = Program.query.filter_by(status="open").order_by(Program.created_at.desc()).limit(3).all()
    posts = Post.query.order_by(Post.published_at.desc()).limit(3).all()
    return render_template("main/index.html", programs=programs, posts=posts)

@main_bp.route("/about")
def about(): return render_template("main/about.html")

@main_bp.route("/news")
def news(): return render_template("main/news.html", posts=Post.query.order_by(Post.published_at.desc()).all())

@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        db.session.add(Message(name=form.name.data, email=form.email.data,
                               subject=form.subject.data, body=form.message.data))
        db.session.commit()
        flash("Thanks! We'll get back to you soon.", "success")
        return redirect(url_for("main.contact"))
    return render_template("main/contact.html", form=form)