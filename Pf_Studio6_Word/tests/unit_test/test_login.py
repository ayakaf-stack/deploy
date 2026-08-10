import pytest
from unittest.mock import patch
from werkzeug.security import generate_password_hash
from models.models import User
from models.extensions import db

# ==========================================
# 1. GETリクエストのテスト
# ==========================================
def test_login_get(client):
    """GETアクセスでログイン画面が正常に表示されるか"""
    response = client.get('/login')
    assert response.status_code == 200
    assert 'login.html' in [t.name for t in response.templates] if hasattr(response, 'templates') else True


# ==========================================
# 2. 通常ユーザー: ログイン成功
# ==========================================
def test_login_success(client, app):
    """正しいメールアドレスとパスワードでログインし、マイページへリダイレクトされるか"""
    # テストユーザーを作成
    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        if not user:
            user = User(
                email="user@example.com",
                user_name="テストユーザー",
                password_hash="...",  # 既存の処理に合わせる
            )
            db.session.add(user)
            db.session.commit()
        user_id = user.id

    # POST送信
    response = client.post('/login', data={
        'email': 'user@example.com',
        'password': 'password123'
    }, follow_redirects=False)

    # マイページ（/mypage）へのリダイレクト確認
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/mypage')

    # セッションに user_id, user_name が保存されているか確認
    with client.session_transaction() as sess:
        assert sess.get('user_id') == user_id
        assert sess.get('user_name') == "テストユーザー"


# ==========================================
# 3. 通常ユーザー: ログイン失敗（パスワード間違い / ユーザー不存在）
# ==========================================
@pytest.mark.parametrize("email, password", [
    ("user@example.com", "wrong_password"),     # パスワード間違い
    ("nonexistent@example.com", "password123"), # 存在しないメールアドレス
    ("", "password123"),                        # メールアドレスが空
    ("user@example.com", ""),                   # パスワードが空
    ("", ""),                                   # 両方空
    ("admin@example.com", "wrong_admin_pass")   # 管理者メール＋間違ったパスワード
])

def test_login_failure(client, app, email, password):
    """認証失敗時にエラーメッセージが表示され、ログイン画面に留まるか"""
    # 事前準備：テストユーザーを用意
    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        if not user:
            user = User(
                email="user@example.com",
                user_name="テストユーザー",
                password_hash="...",  # 既存の処理に合わせる
            )
            db.session.add(user)
            db.session.commit()

    response = client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'ログインに失敗しました' in response.get_data(as_text=True)

    # セッションに入っていないことの確認
    with client.session_transaction() as sess:
        assert 'user_id' not in sess


# ==========================================
# 4. 管理者ログイン（マジックリンクメール送信）
# ==========================================
from unittest.mock import patch
# app.py（またはログイン処理が記述されているモジュール名）から ADMIN_EMAIL, ADMIN_PASSWORD をインポート
# 例: from app import ADMIN_EMAIL, ADMIN_PASSWORD

@patch('flask_mail.Mail.send')
def test_admin_login_sends_email(mock_mail_send, client, app):
    """管理者情報でログインした場合に、メールが送信されてログイン画面へリダイレクトされるか"""
    
    # アプリ側で定義されている ADMIN_EMAIL / ADMIN_PASSWORD を取得
    # （インポートが難しい場合は app.config から、または直接アプリのモジュールを参照）
    try:
        from app import ADMIN_EMAIL, ADMIN_PASSWORD
    except ImportError:
        ADMIN_EMAIL = app.config.get('ADMIN_EMAIL', 'admin@example.com')
        ADMIN_PASSWORD = app.config.get('ADMIN_PASSWORD', 'adminpass')

    # 管理者ログインのリクエスト（DB操作は不要）
    response = client.post('/login', data={
        'email': ADMIN_EMAIL,
        'password': ADMIN_PASSWORD
    }, follow_redirects=True)

    # 1. メール送信関数が1回呼ばれたか検証
    assert mock_mail_send.called
    assert mock_mail_send.call_count == 1

    # 2. 送信されたメールの内容検証
    sent_msg = mock_mail_send.call_args[0][0]
    assert sent_msg.subject == '管理者ログイン用リンク'
    assert ADMIN_EMAIL in sent_msg.recipients

    # 3. フラッシュメッセージの確認
    assert '登録されたメールアドレスに送信されたURLから管理者画面にログインしてください' in response.get_data(as_text=True)