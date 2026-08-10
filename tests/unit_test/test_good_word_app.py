from random import randint
import pytest
from app import app
from models.extensions import db
from models.models import Good_word


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


# ============================================================
# テストデータ作成・削除用ヘルパー
# ============================================================

def _create_good_word(user_id, word_id):
    with app.app_context():
        like = Good_word(user_id=user_id, word_id=word_id)
        db.session.add(like)
        db.session.commit()
        like_id = like.id
        db.session.remove()
        return like_id


def _delete_good_word_if_exists(user_id, word_id):
    with app.app_context():
        like = Good_word.query.filter_by(user_id=user_id, word_id=word_id).first()
        if like is not None:
            db.session.delete(like)
            db.session.commit()
        db.session.remove()


def _get_good_word(user_id, word_id):
    with app.app_context():
        like = Good_word.query.filter_by(user_id=user_id, word_id=word_id).first()
        db.session.remove()
        return like


def _get_good_count(word_id):
    with app.app_context():
        count = Good_word.query.filter_by(word_id=word_id).count()
        db.session.remove()
        return count


# ============================================================
# GET /good/word/<id> - そもそも許可されていないメソッド
# ============================================================

def test_good_word_get_not_allowed(login_client):
    response = login_client.get(f"/good/word/{WORD_ID}")
    assert response.status_code == 405


# ============================================================
# POST /good/word/<id> - 認可
# ============================================================

def test_good_word_requires_login(client):
    response = client.post(f"/good/word/{WORD_ID}")
    assert response.status_code == 401

    data = response.get_json()
    assert "ログイン" in data["error"]

    # 未ログインでは何も作成されていないことを確認
    assert _get_good_word(LOGIN_USER_ID, WORD_ID) is None


# ============================================================
# POST /good/word/<id> - 正常系
# ============================================================

def test_good_word_like_on(login_client):
    # 未いいね状態から開始することを保証
    _delete_good_word_if_exists(LOGIN_USER_ID, WORD_ID)
    before_count = _get_good_count(WORD_ID)

    try:
        response = login_client.post(f"/good/word/{WORD_ID}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_good"] is True
        assert data["good_count"] == before_count + 1

        assert _get_good_word(LOGIN_USER_ID, WORD_ID) is not None
    finally:
        _delete_good_word_if_exists(LOGIN_USER_ID, WORD_ID)


def test_good_word_like_off(login_client):
    # 既にいいね済みの状態を作ってから開始
    _delete_good_word_if_exists(LOGIN_USER_ID, WORD_ID)
    _create_good_word(LOGIN_USER_ID, WORD_ID)
    before_count = _get_good_count(WORD_ID)

    try:
        response = login_client.post(f"/good/word/{WORD_ID}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_good"] is False
        assert data["good_count"] == before_count - 1

        assert _get_good_word(LOGIN_USER_ID, WORD_ID) is None
    finally:
        _delete_good_word_if_exists(LOGIN_USER_ID, WORD_ID)


def test_good_word_does_not_affect_other_users_like(login_client):
    # 他ユーザーのいいねを先に作っておく
    _delete_good_word_if_exists(OTHER_USER_ID, WORD_ID)
    _delete_good_word_if_exists(LOGIN_USER_ID, WORD_ID)
    _create_good_word(OTHER_USER_ID, WORD_ID)

    try:
        response = login_client.post(f"/good/word/{WORD_ID}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_good"] is True

        # 自分のいいねは作成されている
        assert _get_good_word(LOGIN_USER_ID, WORD_ID) is not None
        # 他ユーザーのいいねは影響を受けていない
        assert _get_good_word(OTHER_USER_ID, WORD_ID) is not None
    finally:
        _delete_good_word_if_exists(LOGIN_USER_ID, WORD_ID)
        _delete_good_word_if_exists(OTHER_USER_ID, WORD_ID)