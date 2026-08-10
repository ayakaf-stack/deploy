import uuid
import pytest
from werkzeug.security import generate_password_hash
from app import db
from models.models import User


def test_unregister_get_success(client):
    """【正常系】ログインユーザーが退会ページ（GET）に正常アクセスできるか"""
    unique_suffix = str(uuid.uuid4())[:8]
    user = User(
        user_name=f'unreg_user_{unique_suffix}',
        email=f'unreg_{unique_suffix}@example.com',
        password_hash=generate_password_hash('password123')
    )
    db.session.add(user)
    db.session.commit()

    try:
        with client.session_transaction() as session:
            session['user_id'] = user.id

        response = client.get('/unregister')
        assert response.status_code == 200

    finally:
        User.query.filter_by(id=user.id).delete()
        db.session.commit()


def test_unregister_access_denied_when_not_logged_in(client):
    """【異常系】未ログイン時に退会ページにアクセスするとログイン画面へリダイレクトされるか"""
    response = client.get('/unregister')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_unregister_post_success(client):
    """【正常系】正しいパスワードとチェックボックス入力で退会処理（ユーザー削除・セッションクリア）が成功するか"""
    unique_suffix = str(uuid.uuid4())[:8]
    raw_password = 'correct_password'
    user = User(
        user_name=f'unreg_user_{unique_suffix}',
        email=f'unreg_{unique_suffix}@example.com',
        password_hash=generate_password_hash(raw_password)
    )
    db.session.add(user)
    db.session.commit()
    user_id = user.id

    try:
        with client.session_transaction() as session:
            session['user_id'] = user_id

        # POSTリクエスト実行（リダイレクトを追跡）
        response = client.post(
            '/unregister',
            data={'password': raw_password, 'checkbox': 'on'},
            follow_redirects=True
        )

        assert response.status_code == 200

        # DBからユーザーが削除されているか検証
        deleted_user = db.session.get(User, user_id)
        assert deleted_user is None

        # セッションがクリアされているか検証
        with client.session_transaction() as session:
            assert 'user_id' not in session

        # フラッシュメッセージが表示されているか検証
        html = response.get_data(as_text=True)
        assert 'ユーザー情報が削除されました' in html

    finally:
        # 万が一削除に失敗していた場合のクリーンアップ
        User.query.filter_by(id=user_id).delete()
        db.session.commit()


def test_unregister_post_missing_inputs(client):
    """【異常系】パスワード未入力またはチェックボックス未選択時にエラーメッセージが出るか"""
    unique_suffix = str(uuid.uuid4())[:8]
    raw_password = 'correct_password'
    user = User(
        user_name=f'unreg_user_{unique_suffix}',
        email=f'unreg_{unique_suffix}@example.com',
        password_hash=generate_password_hash(raw_password)
    )
    db.session.add(user)
    db.session.commit()

    try:
        with client.session_transaction() as session:
            session['user_id'] = user.id

        # チェックボックス未選択
        response = client.post(
            '/unregister',
            data={'password': raw_password},
            follow_redirects=True
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'パスワードを入力し、注意事項に同意してください' in html

        # ユーザーが削除されていないことを確認
        assert db.session.get(User, user.id) is not None

    finally:
        User.query.filter_by(id=user.id).delete()
        db.session.commit()


def test_unregister_post_invalid_password(client):
    """【異常系】間違ったパスワードを入力した場合にエラーメッセージが出るか"""
    unique_suffix = str(uuid.uuid4())[:8]
    user = User(
        user_name=f'unreg_user_{unique_suffix}',
        email=f'unreg_{unique_suffix}@example.com',
        password_hash=generate_password_hash('correct_password')
    )
    db.session.add(user)
    db.session.commit()

    try:
        with client.session_transaction() as session:
            session['user_id'] = user.id

        # 誤ったパスワードを送信
        response = client.post(
            '/unregister',
            data={'password': 'wrong_password', 'checkbox': 'on'},
            follow_redirects=True
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'パスワードが正しくありません' in html

        # ユーザーが削除されていないことを確認
        assert db.session.get(User, user.id) is not None

    finally:
        User.query.filter_by(id=user.id).delete()
        db.session.commit()