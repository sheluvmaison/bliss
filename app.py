from flask import Flask, render_template, request, redirect, flash, url_for
from flask_login import login_required, current_user, LoginManager, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import re
from models import db, Post, MyUser
import uuid
app = Flask(__name__, static_url_path='/static')

app.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Путь к папке с аватарками
UPLOAD_FOLDER = 'avatars'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload_avatar/', methods=['GET', 'POST'])
def upload_avatar():
    if request.method == 'POST':
        if 'avatar' in request.files:
            avatar = request.files['avatar']

            if avatar.filename == '':
                return "Вы не выбрали файл."

            # Генерируем уникальное имя для файла
            filename = str(uuid.uuid4()) + os.path.splitext(avatar.filename)[-1]

            # Сохраняем файл в папку "avatars" с уникальным именем
            avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Теперь можно сохранить путь к выбранной аватарке в базе данных или сессии пользователя
            # Например, если вы используете сессии, вы можете сделать это так:
            # session['avatar_path'] = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            return "Аватарка успешно загружена!"

    return render_template('avatar_form.html')

# Остальной код без изменений


@login_manager.user_loader
def load_user(user_id):
    return MyUser.select().where(MyUser.id==int(user_id)).first()


@app.before_request
def before_request():
    db.connect()
    
@app.after_request
def after_request(response):
    db.close()
    return response


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        user = MyUser.select().where(MyUser.email==email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect('/login/')
        else:
            login_user(user)
            return redirect('/')
    return render_template('login.html', user=current_user)

@app.route('/logout/')
def logout():
    logout_user()
    return redirect('/login/')

@app.route('/current_profile/')
@login_required
def my_profile():
    posts = Post.select().where(Post.author==current_user)
    return render_template('profile.html', user=current_user, posts=posts)

@app.route('/profile/<int:id>/')
def profile():
    user = MyUser.select().where(MyUser.id==id).first()
    posts = Post.select().where(Post.author==current_user)
    return render_template('profile.html', user=user, posts=posts)

def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search("[a-z]", password):
        return False
    if not re.search("[A-Z]", password):
        return False
    if not re.search("[0-9]", password):
        return False
    return True

@app.route('/register/', methods=('GET', 'POST'))
def register():
    if request.method=='POST':
        email = request.form['email']
        username = request.form['username']
        age = request.form['age']
        full_name = request.form['full_name']
        password = request.form['password']
        user = MyUser.select().where(MyUser.email==email).first()
        if user:
            flash('email addres already exists')
            return redirect('/register/')
        if MyUser.select().where(MyUser.username==username).first():
            flash('username already exists')
            return redirect('/register/')
        else:
            if validate_password(password):
                MyUser.create(
                    email=email,
                    username=username,
                    age=age,
                    password=generate_password_hash(password),
                    full_name=full_name,
                )
                return redirect('/login/')
            else:
                flash('wrong password')
                return redirect('/register/')
    return render_template('register.html')


@app.route('/create/', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        Post.create(
            title=title,
            author=current_user,
            content=content
        )
        return redirect('/')
    return render_template('create.html')

@app.route('/<int:id>/')
def get_post(id):
    post = Post.select().where(Post.id==id).first()
    if post:
        return render_template('post_detail.html', post=post)
    return f'Post with id = {id} does not exists'
        

@app.route('/')
def index():
    all_posts = Post.select()
    return render_template('index.html', posts=all_posts)

@app.route('/profile_update/', methods=['GET', 'POST'])
@login_required
def profile_update():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        age = request.form['age']

        # Обработка загрузки аватарки
        if 'avatar' in request.files:
            avatar = request.files['avatar']

            # Проверяем, что пользователь выбрал файл аватарки
            if avatar.filename != '':
                # Генерируем уникальное имя файла с помощью модуля uuid
                filename = str(uuid.uuid4()) + os.path.splitext(avatar.filename)[-1]
                # Сохраняем файл в папку "avatars" с уникальным именем
                avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename)))

                # Здесь можно сохранить путь к аватарке в базе данных или сессии пользователя
                # Например, если вы используете сессии, вы можете сделать это так:
                # session['avatar_path'] = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

        # Обновляем данные профиля в базе данных
        obj = MyUser.update({
            MyUser.full_name: full_name,
            MyUser.username: username,
            MyUser.email: email,
            MyUser.age: age
        }).where(MyUser.id == current_user.id)
        obj.execute()

        return redirect('/current_profile/')

    return render_template('profile_update.html', user=current_user)

# ... (ваш текущий код Flask приложения)



@app.route('/<int:id>/update/', methods=('GET', 'POST'))
@login_required
def update(id):
    post = Post.select().where(Post.id==id).first()
    if request.method == 'POST':
        if post:
            if post.author==current_user:
                title = request.form['title']
                content = request.form['content']
                obj = Post.update({
                    Post.title: title,
                    Post.content: content
                }).where(Post.id==id)
                obj.execute()
                return redirect(f'/{id}/')
            return f'u are not author of dis post'
        return f'Post with id = {id} does not exists'
    return render_template('update.html', post=post)


@app.route('/<int:id>/delete/', methods=('GET', 'POST'))
@login_required
def delete(id):
    post = Post.select().where(Post.id==id).first()
    if request.method == 'POST':
        if post:
            if current_user==post.author:
                post.delete_instance()
                return redirect('/')
            return f'u are not author of dis post'
        return f'Post with id = {id} does not exists'
    return render_template('delete.html', post=post)


if __name__ == '__main__':
    app.run(debug=True)