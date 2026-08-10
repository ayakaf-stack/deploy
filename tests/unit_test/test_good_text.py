from random import randint
import pytest
from app import app
from models.extensions import db
from models.models import Text, Word, Good_text


# ============================================================
# フィクスチャ
# ============================================================

@pytest.fixture
def client():
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


# ログイン済みユーザー
@pytest.fixture
def login_client(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_name"] = "aaa"

    return client

@pytest.fixture(autouse=True)
def fresh_db_connection():
    """各テストの前に、DBエンジンの接続プールを破棄して古い接続を残さないようにする"""
    with app.app_context():
        db.engine.dispose()
    yield


WORD_ID = 29  # 既存の単語ID
LOGIN_USER_ID = 1  # login_client と同じユーザーID
OTHER_USER_ID = 2  # login_client とは別の、実在するユーザーID
TEXT_OWNER_USER_ID = 1  # いいね対象の文章の作成者（いいねする側とは無関係でよい）


# ============================================================
# テストデータ作成・削除用ヘルパー
# ============================================================

def _get_word_string():
    with app.app_context():
        return db.session.get(Word, WORD_ID).word


def _create_text(user_id, title, main_text, text_status=0, word_id=WORD_ID):
    with app.app_context():
        text = Text(
            user_id=user_id,
            title=title,
            main_text=main_text,
            text_status=text_status,
            word=word_id,
        )
        db.session.add(text)
        db.session.commit()
        text_id = text.id
        db.session.remove()
        return text_id


def _delete_text_if_exists(text_id):
    with app.app_context():
        text = db.session.get(Text, text_id)
        if text is not None:
            db.session.delete(text)
            db.session.commit()
        db.session.remove()


def _create_good_text(user_id, text_id):
    with app.app_context():
        like = Good_text(user_id=user_id, text_id=text_id)
        db.session.add(like)
        db.session.commit()
        like_id = like.id
        db.session.remove()
        return like_id


def _delete_good_text_if_exists(user_id, text_id):
    with app.app_context():
        like = Good_text.query.filter_by(user_id=user_id, text_id=text_id).first()
        if like is not None:
            db.session.delete(like)
            db.session.commit()
        db.session.remove()


def _get_good_text(user_id, text_id):
    with app.app_context():
        like = Good_text.query.filter_by(user_id=user_id, text_id=text_id).first()
        db.session.remove()
        return like


def _get_good_count(text_id):
    with app.app_context():
        count = Good_text.query.filter_by(text_id=text_id).count()
        db.session.remove()
        return count


# ============================================================
# GET /good/text/<id> - そもそも許可されていないメソッド
# ============================================================

def test_good_text_get_not_allowed(login_client):
    response = login_client.get("/good/text/999999")
    assert response.status_code == 405


# ============================================================
# POST /good/text/<id> - 認可
# ============================================================

def test_good_text_requires_login(client):
    word = _get_word_string()
    text_id = _create_text(TEXT_OWNER_USER_ID, f"いいね未ログイン{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        response = client.post(f"/good/text/{text_id}")
        assert response.status_code == 401

        data = response.get_json()
        assert "ログイン" in data["error"]

        # 未ログインでは何も作成されていないことを確認
        assert _get_good_text(LOGIN_USER_ID, text_id) is None
    finally:
        _delete_text_if_exists(text_id)


# ============================================================
# POST /good/text/<id> - 正常系
# ============================================================

def test_good_text_like_on(login_client):
    word = _get_word_string()
    text_id = _create_text(TEXT_OWNER_USER_ID, f"いいねON{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        # 未いいね状態から開始することを保証
        _delete_good_text_if_exists(LOGIN_USER_ID, text_id)
        before_count = _get_good_count(text_id)

        response = login_client.post(f"/good/text/{text_id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_good"] is True
        assert data["good_count"] == before_count + 1

        assert _get_good_text(LOGIN_USER_ID, text_id) is not None
    finally:
        _delete_good_text_if_exists(LOGIN_USER_ID, text_id)
        _delete_text_if_exists(text_id)


def test_good_text_like_off(login_client):
    word = _get_word_string()
    text_id = _create_text(TEXT_OWNER_USER_ID, f"いいねOFF{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        # 既にいいね済みの状態を作ってから開始
        _delete_good_text_if_exists(LOGIN_USER_ID, text_id)
        _create_good_text(LOGIN_USER_ID, text_id)
        before_count = _get_good_count(text_id)

        response = login_client.post(f"/good/text/{text_id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_good"] is False
        assert data["good_count"] == before_count - 1

        assert _get_good_text(LOGIN_USER_ID, text_id) is None
    finally:
        _delete_good_text_if_exists(LOGIN_USER_ID, text_id)
        _delete_text_if_exists(text_id)


def test_good_text_does_not_affect_other_users_like(login_client):
    word = _get_word_string()
    text_id = _create_text(TEXT_OWNER_USER_ID, f"いいね他ユーザー{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        # 他ユーザーのいいねを先に作っておく
        _delete_good_text_if_exists(OTHER_USER_ID, text_id)
        _delete_good_text_if_exists(LOGIN_USER_ID, text_id)
        _create_good_text(OTHER_USER_ID, text_id)

        response = login_client.post(f"/good/text/{text_id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_good"] is True

        # 自分のいいねは作成されている
        assert _get_good_text(LOGIN_USER_ID, text_id) is not None
        # 他ユーザーのいいねは影響を受けていない
        assert _get_good_text(OTHER_USER_ID, text_id) is not None
    finally:
        _delete_good_text_if_exists(LOGIN_USER_ID, text_id)
        _delete_good_text_if_exists(OTHER_USER_ID, text_id)
        _delete_text_if_exists(text_id)