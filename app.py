from flask import Flask, render_template, flash, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from flask_migrate import Migrate
from datetime import datetime
from webforms import LoginForm, UserForm, PostForm, SearchForm, CommentForm
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash 
from sqlalchemy.sql import func

app = Flask(__name__)
ckeditor = CKEditor(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = "samo levski"
db = SQLAlchemy(app)

class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Posts', backref='poster')
    comments = db.relationship("Comment", backref='poster')

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<Name %r>' % self.name

class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    author = db.Column(db.String(255))
    slug = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime(timezone=True), default=func.now())
    poster_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime(timezone=True), default=func.now())
    poster_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

with app.app_context():
	db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
	return Users.query.get(int(user_id))

@app.context_processor
def base():
	form = SearchForm()
	return dict(form=form)

@app.route('/search', methods=["POST"])
def search():
	form = SearchForm()
	posts = Posts.query
	if form.validate_on_submit():
		post.searched = form.searched.data
		posts = posts.filter(Posts.content.like('%' + post.searched + '%'))
		posts = posts.order_by(Posts.title).all()

		return render_template("search.html",
		 form=form,
		 searched = post.searched,
		 posts = posts)
	
@app.route('/admin')
@login_required
def admin():
	id = current_user.id
	if id == 1:
		return render_template("admin.html")
	else:
		flash("Sorry you must be the Admin to access this page")
		return redirect(url_for('dashboard'))
	

@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		user = Users.query.filter_by(username=form.username.data).first()
		if user:
			if check_password_hash(user.password_hash, form.password.data):
				login_user(user)
				flash("Login Succesfull")
				return redirect(url_for('dashboard'))
			else:
				flash("Wrong Password - Try Again")
		else:
			flash("User Not Found - Try Again")
	return render_template('login.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
	logout_user()
	flash("You Have Been Logged Out")
	return redirect(url_for('login'))

@app.route('/user/add', methods=['GET', 'POST'])
def register():
	name = None
	form = UserForm()
	if form.validate_on_submit():
		user = Users.query.filter_by(email=form.email.data).first()
		if user is None:
			hashed_pw = generate_password_hash(form.password_hash.data)
			user = Users(username=form.username.data, name=form.name.data, email=form.email.data, password_hash=hashed_pw)
			db.session.add(user)
			db.session.commit()
		name = form.name.data
		form.name.data = ''
		form.username.data = ''
		form.email.data = ''
		form.password_hash.data = ''

		flash("User Added Successfully")
	return render_template("add_user.html", 
		form=form,
		name=name)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
	form = UserForm()
	id = current_user.id
	name_to_update = Users.query.get_or_404(id)
	if request.method == "POST":
		name_to_update.name = request.form['name']
		name_to_update.email = request.form['email']
		name_to_update.username = request.form['username']
		name_to_update.about_author = request.form['about_author']
		
		return render_template("dashboard.html", 
				form=form,
				name_to_update = name_to_update,
				id = id)

	return render_template('dashboard.html')

@app.route('/posts/delete/<int:id>')
@login_required
def delete_post(id):
	post_to_delete = Posts.query.get_or_404(id)
	id = current_user.id
	if id == post_to_delete.poster.id or id == 14:
		try:
			db.session.delete(post_to_delete)
			db.session.commit()

			flash("Post Was Deleted")

			posts = Posts.query.order_by(Posts.date_posted)
			return render_template("posts.html", posts=posts)


		except:
			flash("There was a problem deleting this post - try again.")
			posts = Posts.query.order_by(Posts.date_posted)
			return render_template("posts.html", posts=posts)
	else:
		flash("You Aren't Authorized To Delete This Post")
		posts = Posts.query.order_by(Posts.date_posted)
		return render_template("posts.html", posts=posts)
	
@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
	form = UserForm()
	name_to_update = Users.query.get_or_404(id)
	if request.method == "POST":
		name_to_update.name = request.form['name']
		name_to_update.email = request.form['email']
		name_to_update.username = request.form['username']
		try:
			db.session.commit()
			flash("User Updated Successfully!")
			return render_template("update.html", 
				form=form,
				name_to_update = name_to_update, id=id)
		except:
			flash("Error. Looks like there was a problem - try again.")
			return render_template("update.html", 
				form=form,
				name_to_update = name_to_update,
				id=id)
	else:
		return render_template("update.html", 
				form=form,
				name_to_update = name_to_update,
				id = id)
	
@app.route('/delete/<int:id>')
@login_required
def delete(id):
	if id == current_user.id:
		user_to_delete = Users.query.get_or_404(id)
		name = None
		form = UserForm()

		try:
			db.session.delete(user_to_delete)
			db.session.commit()
			flash("User Deleted Successfully!!")

			our_users = Users.query.order_by(Users.date_added)
			return render_template("add_user.html", 
			form=form,
			name=name,
			our_users=our_users)

		except:
			flash("There was a problem deleting user - try again.")
			return render_template("add_user.html", 
			form=form, name=name,our_users=our_users)
	else:
		flash("Sorry, you can't delete that user! ")
		return redirect(url_for('dashboard'))

@app.route('/posts')
def posts():
	posts = Posts.query.order_by(Posts.date_posted)
	return render_template("posts.html", posts=posts)

@app.route('/posts/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Posts.query.get_or_404(id)
    comments = Comment.query.filter_by(post_id=id).order_by(Comment.date_posted.desc()).all()
    form = CommentForm()

    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author=current_user.username, post_id=id, poster_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!', 'success')
        return redirect(url_for('post', id=post.id))

    return render_template('post.html', post=post, comments=comments, form=form)

@app.route('/posts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
	post = Posts.query.get_or_404(id)
	form = PostForm()
	if form.validate_on_submit():
		post.title = form.title.data
		post.author = form.author.data
		post.slug = form.slug.data
		post.content = form.content.data
		db.session.add(post)
		db.session.commit()
		flash("Post Has Been Updated")
		return redirect(url_for('post', id=post.id))
	
	if current_user.id == post.poster_id or current_user.id == 14:
		form.title.data = post.title
		form.author.data = post.author
		form.slug.data = post.slug
		form.content.data = post.content
		return render_template('edit_post.html', form=form)
	else:
		flash("You Aren't Authorized To Edit This Post")
		posts = Posts.query.order_by(Posts.date_posted)
		return render_template("posts.html", posts=posts)

@app.route('/add-post', methods=['GET', 'POST'])
@login_required
def add_post():
	form = PostForm()

	if form.validate_on_submit():
		poster = current_user.id
		post = Posts(title=form.title.data, content=form.content.data, poster_id=poster, slug=form.slug.data)
		form.title.data = ''
		form.content.data = ''
		form.author.data = ''
		form.slug.data = ''
		db.session.add(post)
		db.session.commit()
		flash("Blog Post Submitted Successfully")

	return render_template("add_post.html", form=form)

@app.route('/')
def index():

	return render_template("index.html")

@app.route('/user/<name>')

def user(name):
	return render_template("user.html", user_name=name)

@app.errorhandler(404)
def page_not_found(e):
	return render_template("404.html"), 404

@app.errorhandler(500)
def page_not_found(e):
	return render_template("500.html"), 500

if __name__ == "__main__":
	app.run(debug=True) 