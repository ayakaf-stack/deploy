import os,re
from random import choice,shuffle
from flask import Flask, render_template,redirect,session,flash,url_for,request,jsonify
from models.models import Word,Genre,Word_genre,User,Text,Good_word,Good_text
from models.extensions import db
from werkzeug.security import generate_password_hash,check_password_hash
from sqlalchemy import func
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Mail, Message
from dotenv import load_dotenv
from flask_migrate import Migrate

# ログインチェック用のコード
def login_check():
    if"user_id" not in session:
        flash("ログインが必要です", "warning")
        return redirect(url_for("login"))
    return None

load_dotenv()

app = Flask(__name__)

DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_USER = os.getenv('DB_USER')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
SECRET_KEY = os.getenv('SECRET_KEY')

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# app.config["SQLALCHEMY_DATABASE_URI"] = (
#     f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')

db.init_app(app)

migrate = Migrate(app, db)

app.secret_key = SECRET_KEY

# --- メール送信設定 ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# --- マジックリンク用トークン発行・検証 ---
serializer = URLSafeTimedSerializer(SECRET_KEY)

# 使用済みトークンの記録(メモリ上・サーバー再起動でリセットされる)
used_tokens = set()


# TOP画面
@app.route('/')
def index():
    words = Word.query.all()
    random_word = choice(words)

    texts = Text.query.filter(
        Text.main_text.contains(random_word.word),
        Text.text_status == 0
    ).all()

    shuffle(texts)

    is_login = 'user_id' in session

    texts_items = []
    for text in texts:
        good_count_text = len(text.goods)
        is_good_text = False
        if is_login:
            is_good_text = Good_text.query.filter_by(text_id=text.id, user_id=session['user_id']).first() is not None
        texts_items.append({
            'id': text.id,
            'title': text.title,
            'main_text': text.main_text,
            'good_count': good_count_text,
            'is_good': is_good_text
        })

    is_good = False
    if is_login:
        is_good = Good_word.query.filter_by(word_id=random_word.id, user_id=session['user_id']).first() is not None

    good_count = Good_word.query.filter_by(word_id=random_word.id).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'word': {
                'id': random_word.id,
                'word': random_word.word,
                'reading': random_word.reading,
                'mean': random_word.mean
            },
            'is_good': is_good,
            'good_count': good_count,
            'texts': texts_items,
            'is_login': is_login
        })

    texts_contents = [
        (text, item['good_count'], item['is_good']) 
        for text, item in zip(texts, texts_items)
    ]

    return render_template(
        'top.html',
        word=random_word,
        texts=texts_items,
        is_login=is_login,
        is_good=is_good,
        good_count=good_count
    )


# ログイン
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # --- 管理者判定(先に判定し、通常ユーザー処理には進まない) ---
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            token = serializer.dumps(email, salt='admin-login')
            verify_url = url_for('admin_verify', token=token, _external=True)

            msg = Message(
                subject='管理者ログイン用リンク',
                recipients=[email],
                body=f'以下のURLから管理者画面にログインしてください(有効期限15分)\n\n{verify_url}'
            )
            mail.send(msg)

            flash('登録されたメールアドレスに送信されたURLから管理者画面にログインしてください')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('ログインに失敗しました')
            return redirect(url_for('login'))
        
        session['user_id'] = user.id
        session['user_name'] = user.user_name
        return redirect(url_for('mypage'))

    return render_template('login.html')


# 管理者マジックリンク検証
@app.route('/admin/verify/<token>', methods=['GET'])
def admin_verify(token):
    if token in used_tokens:
        flash('このリンクは既に使用されています')
        return redirect(url_for('login'))

    try:
        email = serializer.loads(token, salt='admin-login', max_age=900)  # 15分
    except SignatureExpired:
        flash('リンクの有効期限が切れています')
        return redirect(url_for('login'))
    except BadSignature:
        flash('不正なリンクです')
        return redirect(url_for('login'))

    if email != ADMIN_EMAIL:
        flash('不正なリンクです')
        return redirect(url_for('login'))

    used_tokens.add(token)
    session['is_admin'] = True

    flash('管理者としてログインしました')
    return redirect(url_for('admin'))


# 新規登録
# 田中さん担当
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_name = request.form.get('user_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not user_name or not email or not password:
            flash("全ての項目を正しく入力してください")
            return redirect(url_for('register'))
        
        if len(user_name) > 255:
            flash("ユーザー名は255文字以内で入力してください")
            return redirect(url_for('register'))
        
        if not re.fullmatch(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email):
            flash("既に登録済みのメールアドレスか不正なメールアドレスです")
            return redirect(url_for("register"))

        user = User.query.filter_by(email=email).first()
        if user:
            flash("既に登録済みのメールアドレスか不正なメールアドレスです")
            return redirect(url_for('register'))
        
        if len(password) < 8 or len(password) > 16:
            flash("パスワードは8文字以上16文字以内で入力してください")
            return redirect(url_for('register'))
        
        password_hash = generate_password_hash(password)

        user = User(
             user_name=user_name,
            email=email,
            password_hash=password_hash
         )
        
        db.session.add(user)
        db.session.commit()

        flash("新規登録が完了しました")
        return redirect(url_for('login'))

    return render_template('register.html')


# マイページ
@app.route('/mypage', methods=['GET'])
def mypage():
    result = login_check()
    if result:
        return result

    user_id = session['user_id']
    user = db.get_or_404(User, user_id)

    good_words = Good_word.query.filter_by(user_id=user_id).all()
    liked_words = []
    for gw in good_words:
        word = db.session.get(Word, gw.word_id)
        liked_words.append(word)

    good_texts = Good_text.query.filter_by(user_id=user_id).all()
    liked_texts = []
    for gt in good_texts:
        text = db.session.get(Text, gt.text_id)
        liked_texts.append(text)

    my_texts = Text.query.filter_by(user_id=user_id).all()
    my_texts_data = []
    for text in my_texts:
        good_count = len(text.goods)
        my_texts_data.append((text, good_count))

    return render_template(
        'mypage.html',
        user=user,
        liked_words=liked_words,
        liked_texts=liked_texts,
        my_texts_data=my_texts_data
    )

# ログアウト
@app.route('/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        session.clear()
        flash('ログアウトしました')
    return redirect(url_for('index'))


# 退会
@app.route('/unregister', methods=['GET', 'POST'])
def unregister():

    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
    
        my_id = session['user_id']
        user = db.session.get(User,my_id)

        password = request.form.get('password','')
        checkbox = request.form.get('checkbox')

        if not password or not checkbox:
            flash('パスワードを入力し、注意事項に同意してください')
            return redirect(url_for('unregister'))

        if not check_password_hash(user.password_hash, password):
            flash('パスワードが正しくありません')
            return redirect(url_for('unregister'))

        db.session.delete(user)
        db.session.commit()
        session.clear()
        flash("ユーザー情報が削除されました")
        return redirect(url_for('index'))

     
    user_name = session.get('user_name', '')
    return render_template('unregister.html',user_name=user_name)


# 一覧・検索
@app.route('/contents', methods=['GET'])
def contents():
    content_type = request.args.get('type','word')
    keyword = request.args.get('q','').strip()
    genre_ids = request.args.getlist('genre',type=int)
    sort = request.args.get('sort','')

    is_login = 'user_id' in session
    user_id = session.get('user_id')


    if content_type == 'text':
        query = Text.query.filter(Text.text_status == 0)

        if keyword:
            query = query.filter(
                db.or_(
                    Text.title.contains(keyword),
                    Text.main_text.contains(keyword)
                )
            )
        if sort == 'good_desc':
            texts = query.all()
            texts.sort(key=lambda t:len(t.goods),reverse=True)
        elif sort == 'date_asc':
            texts = query.order_by(Text.id.asc()).all()
        elif sort == 'date_desc':
            texts = query.order_by(Text.id.desc()).all()
        else:
            texts = query.order_by(Text.id.desc()).all()

        items = []
        for text in texts:
            good_count = len(text.goods)
            is_good = False
            if is_login:
                is_good = Good_text.query.filter_by(text_id=text.id, user_id=user_id).first() is not None
            items.append({
                'id': text.id,
                'title': text.title,
                'main_text': text.main_text,
                'good_count': good_count,
                'is_good': is_good
            })
    else:
        query = Word.query

        if keyword:
            query = query.filter(
                db.or_(
                    Word.word.contains(keyword),
                    Word.mean.contains(keyword),
                    Word.reading.contains(keyword)
                )
            )

        if genre_ids:
            query = (
                query.join(Word_genre)
                .filter(Word_genre.genre_id.in_(genre_ids))
                .group_by(Word.id)
                .having(func.count(func.distinct(Word_genre.genre_id)) == len(genre_ids))
            )
        words = query.all()

        if sort == 'aiueo_asc':
            words.sort(key=lambda w: w.reading)
        elif sort == 'aiueo_desc':
            words.sort(key=lambda w: w.reading, reverse=True)
        elif sort == 'good_desc':
            words.sort(key=lambda w: len(w.goods), reverse=True)

        items = []
        for word in words:
            good_count = len(word.goods)
            is_good = False
            if is_login:
                is_good = Good_word.query.filter_by(word_id=word.id, user_id=user_id).first() is not None
            items.append({
                'id': word.id,
                'word': word.word,
                'reading': word.reading,
                'mean': word.mean,
                'good_count': good_count,
                'is_good': is_good
            })

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'type': content_type, 'items': items})

    genres = Genre.query.all()
    return render_template('contents.html', items=items, content_type=content_type, genres=genres, is_login=is_login)


# 新規文章作成
@app.route('/text-new/<int:id>', methods=['GET', 'POST'])
def text_new(id):
    result = login_check()
    if result:
        return result
    user_id = session["user_id"]
    
    word_id = id
    select_word = db.session.get(Word, word_id)

    if request.method == 'POST':
        title = request.form.get("title", "").strip()
        main_text = request.form.get("main_text","").strip()
        text_status_val = request.form.get("text_status", "0")
        text_status = int(text_status_val) if text_status_val.isdigit() else 0

        render_error = lambda: render_template(
            "text-new.html",
            user_id=user_id,
            title=title,
            main_text=main_text,
            text_status=text_status,
            word=word_id,
            select_word=select_word
        )

        if not title:
            flash("タイトルを入力してください", "error")
            return render_error()
        if len(title) > 255:
            flash("タイトルは255文字以内で入力してください", "error")
            return render_error()
        if not main_text:
            flash("本文を入力してください", "error")
            return render_error()
        if len(main_text) < 10 or len(main_text) > 400:
            flash("本文は10文字以上・400文字以内で入力してください", "error")
            return render_error()
        
        if select_word and (select_word.word not in main_text):
            flash(f"本文に選択した単語（{select_word.word}）が含まれていません", "error")
            return render_error()
        
        existing_text = Text.query.filter_by(title=title, main_text=main_text).first()
        if existing_text:
            text_status = 1
            flash("タイトルと本文が同一の文章が既に存在するため、この文章は下書き保存されます", "info")

        new_text = Text(
            user_id = user_id,
            title=title,
            main_text=main_text,
            text_status=text_status,
            word = word_id
            )
        db.session.add(new_text)
        db.session.commit()

        flash("文章を作成しました")
        return redirect(url_for('mypage'))

    return render_template('text-new.html',word=word_id, select_word=select_word)


# 文章編集
@app.route('/text-edit/<int:id>', methods=['GET', 'POST'])
def text_edit(id):
    text = db.get_or_404(Text, id)

    user_id = session.get('user_id')
    if not user_id:
        result = login_check()
        if result:
            return result
        user_id = session["user_id"]

    if text.user_id != user_id:
        flash("他ユーザーの文章は編集できません", "error")
        return redirect(url_for('mypage'))
    
    word_id = text.word
    select_word = db.session.get(Word, word_id) if word_id else None
    
    if request.method == 'POST':
        title = request.form.get("title", "").strip()
        main_text = request.form.get("main_text","").strip()
        text_status_val = request.form.get("text_status", "0")
        text_status = int(text_status_val) if text_status_val.isdigit() else 0

        select_word = db.session.get(Word, text.word) if text.word else None

        render_error = lambda: render_template(
            "text-edit.html",
            text=text,
            title=title,
            main_text=main_text,
            text_status=text_status,
            word=word_id,
            select_word=select_word
        )

        if not title:
            flash("タイトルを入力してください", "error")
            return render_error()
        if len(title) > 255:
            flash("タイトルは255文字以内で入力してください", "error")
            return render_error()
        if not main_text:
            flash("本文を入力してください", "error")
            return render_error()
        if len(main_text) < 10 or len(main_text) > 400:
            flash("本文は10文字以上・400文字以内で入力してください", "error")
            return render_error()
        
        if select_word and (select_word.word not in main_text):
            flash(f"本文に選択した単語（{select_word.word}）が含まれていません", "error")
            return render_error()
        
        existing_text = Text.query.filter(
            Text.id != text.id,
            Text.title == title,
            Text.main_text == main_text).first()
        if existing_text:
            text_status = 1
            flash("タイトルと本文が同一の文章が既に存在するため、この文章は下書き保存されます", "info")

        text.title = title
        text.main_text = main_text
        text.text_status = text_status
        db.session.commit()

        flash("文章を編集しました")
        return redirect(url_for('mypage'))

    return render_template('text-edit.html',text=text, word=word_id, select_word=select_word)


# 文章削除
@app.route('/text-delete/<int:id>', methods=['POST'])
def text_delete(id):
    text = db.get_or_404(Text, id)

    user_id = session.get('user_id')
    if not user_id:
        result = login_check()
        if result:
            return result
        user_id = session["user_id"]

    if text.user_id != user_id:
        flash("他ユーザーの文章は削除できません", "error")
        return redirect(url_for('mypage'))
    
    db.session.delete(text)
    db.session.commit()
    
    flash("文章を削除しました", "success")
    return redirect(url_for('mypage'))


# 単語いいね登録・解除
@app.route('/good/word/<int:word_id>', methods=['POST'])
def good_word(word_id):
    if 'user_id' not in session:
        return jsonify({
            "error": 'いいね機能を使うには<a href="' + url_for('login') + '">ログイン</a>してください'
        }), 401
    user_id = session['user_id']

    like = Good_word.query.filter_by(word_id=word_id, user_id=user_id).first()
    if like:
        db.session.delete(like)
        is_good = False
    else:
        new_like = Good_word(word_id=word_id,user_id=user_id)
        db.session.add(new_like)
        is_good = True
    db.session.commit()

    good_count = Good_word.query.filter_by(word_id=word_id).count()

    return jsonify({"is_good":is_good, "good_count":good_count})


# 文章いいね登録・解除
@app.route('/good/text/<int:text_id>', methods=['POST'])
def good_text(text_id):
    if 'user_id' not in session:
        return jsonify({
            "error": 'いいね機能を使うには<a href="' + url_for('login') + '">ログイン</a>してください'
        }), 401
    user_id = session['user_id']

    like = Good_text.query.filter_by(text_id=text_id,user_id=user_id).first()
    if like:
        db.session.delete(like)
        is_good = False
    else:
        new_like = Good_text(text_id=text_id,user_id=user_id)
        db.session.add(new_like)
        is_good = True
    db.session.commit()

    good_count = Good_text.query.filter_by(text_id=text_id).count()

    return jsonify({"is_good":is_good, "good_count":good_count})


# 管理者画面
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'):
        flash('管理者としてログインしてください')
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.get_json()
        word_id = data.get('word_id')
        genre_ids = set(data.get('genre_ids', []))

        if not word_id:
            return jsonify({'error': '単語を選択してください'}), 400

        existing = Word_genre.query.filter_by(word_id=word_id).all()
        existing_ids = {wg.genre_id for wg in existing}

        for wg in existing:
            if wg.genre_id not in genre_ids:
                db.session.delete(wg)

        for genre_id in genre_ids - existing_ids:
            db.session.add(Word_genre(word_id=word_id, genre_id=genre_id))

        db.session.commit()

        return jsonify({'success': True})

    genre_filter = request.args.get('genre_filter', 'all')

    words = Word.query.all()

    items = []
    for word in words:
        genre_ids = [wg.genre_id for wg in Word_genre.query.filter_by(word_id=word.id).all()]

        if genre_filter == 'has' and not genre_ids:
            continue
        if genre_filter == 'none' and genre_ids:
            continue

        items.append({
            'id': word.id,
            'word': word.word,
            'reading': word.reading,
            'mean': word.mean,
            'genre_ids': genre_ids
        })

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'items': items,
            'genres': [{'id': g.id, 'genre': g.genre} for g in Genre.query.all()]
        })

    genres = Genre.query.all()
    return render_template('admin.html', items=items, genres=genres, genre_filter=genre_filter)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)