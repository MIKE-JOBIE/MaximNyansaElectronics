from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, SelectField, IntegerField, DecimalField, DateField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange

class RegisterForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(2, 80)])
    last_name  = StringField("Last Name", validators=[DataRequired(), Length(2, 80)])
    email      = StringField("Email", validators=[DataRequired(), Email()])
    phone      = StringField("Phone", validators=[Optional(), Length(5, 40)])
    password   = PasswordField("Password", validators=[DataRequired(), Length(6, 128)])
    confirm    = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit     = SubmitField("Create Account")

class LoginForm(FlaskForm):
    email    = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = SelectField("Remember Me", choices=[("no","No"),("yes","Yes")], default="no")
    submit   = SubmitField("Log In")

class ApplicationForm(FlaskForm):
    motivation = TextAreaField("Why do you want to join?", validators=[DataRequired(), Length(20, 3000)])
    education  = StringField("Highest education completed", validators=[DataRequired(), Length(2, 200)])
    address    = StringField("Home address", validators=[DataRequired(), Length(2, 255)])
    phone      = StringField("Phone", validators=[DataRequired(), Length(5, 40)])
    submit     = SubmitField("Submit Application")

class ContactForm(FlaskForm):
    name    = StringField("Name", validators=[DataRequired()])
    email   = StringField("Email", validators=[DataRequired(), Email()])
    subject = StringField("Subject", validators=[DataRequired(), Length(2, 200)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(10, 4000)])
    submit  = SubmitField("Send Message")

class DonationForm(FlaskForm):
    donor_name = StringField("Full Name", validators=[DataRequired()])
    email      = StringField("Email", validators=[DataRequired(), Email()])
    amount     = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=1)])
    currency   = SelectField("Currency", choices=[("USD","USD"),("SLE","SLE"),("EUR","EUR")], default="USD")
    message    = TextAreaField("Message (optional)", validators=[Optional()])
    submit     = SubmitField("Pledge Donation")

class CheckoutForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired()])
    phone     = StringField("Phone", validators=[DataRequired()])
    address   = StringField("Delivery Address", validators=[DataRequired()])
    notes     = TextAreaField("Notes", validators=[Optional()])
    submit    = SubmitField("Place Order")

class ProgramForm(FlaskForm):
    title       = StringField("Title", validators=[DataRequired()])
    summary     = StringField("Summary", validators=[DataRequired(), Length(5, 300)])
    description = TextAreaField("Description", validators=[DataRequired()])
    capacity    = IntegerField("Capacity", validators=[DataRequired(), NumberRange(min=1)], default=20)
    fee         = DecimalField("Fee", places=2, default=0)
    status      = SelectField("Status", choices=[("open","Open"),("closed","Closed"),("completed","Completed")])
    cover_image = FileField("Cover Image")
    submit      = SubmitField("Save Program")

class ProductForm(FlaskForm):
    name        = StringField("Name", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    price       = DecimalField("Price", places=2, validators=[DataRequired(), NumberRange(min=0)])
    stock       = IntegerField("Stock", validators=[DataRequired(), NumberRange(min=0)])
    condition   = SelectField("Condition", choices=[("new","New"),("refurbished","Refurbished"),("used","Used")])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    image       = FileField("Image")
    is_active   = SelectField("Active", choices=[("yes","Yes"),("no","No")], default="yes")
    submit      = SubmitField("Save Product")

class ResourceForm(FlaskForm):
    title       = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    category    = StringField("Category", validators=[DataRequired()])
    file        = FileField("File (PDF / DOC / link file)")
    file_url    = StringField("Or external URL", validators=[Optional()])
    submit      = SubmitField("Save Resource")

class ForgotPasswordForm(FlaskForm):
    email  = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired(), Length(6, 128)])
    confirm  = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit   = SubmitField("Set New Password")


class ProfileForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(2, 80)])
    last_name  = StringField("Last Name", validators=[DataRequired(), Length(2, 80)])
    phone      = StringField("Phone", validators=[Optional(), Length(5, 40)])
    address    = StringField("Address", validators=[Optional(), Length(2, 255)])
    submit     = SubmitField("Save Changes")


class ChangePasswordForm(FlaskForm):
    current  = PasswordField("Current Password", validators=[DataRequired()])
    password = PasswordField("New Password", validators=[DataRequired(), Length(6, 128)])
    confirm  = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo("password")])
    submit   = SubmitField("Change Password")

class PostForm(FlaskForm):
    title       = StringField("Title", validators=[DataRequired(), Length(3, 200)])
    body        = TextAreaField("Body (Markdown-ish)", validators=[DataRequired()])
    cover_image = FileField("Cover Image (optional)")
    submit      = SubmitField("Save Post")


class BulkEmailForm(FlaskForm):
    program_id = SelectField("Send to (Program)", coerce=int, validators=[Optional()])
    status     = SelectField("Filter by status",
                             choices=[("all","All"),("pending","Pending"),
                                      ("approved","Approved"),("enrolled","Enrolled"),
                                      ("rejected","Rejected")],
                             default="all")
    subject    = StringField("Subject", validators=[DataRequired(), Length(3, 200)])
    body       = TextAreaField("Message", validators=[DataRequired(), Length(10, 8000)])
    submit     = SubmitField("Send Bulk Email")