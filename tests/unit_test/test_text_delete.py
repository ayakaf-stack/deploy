from random import randint
import pytest
from app import app
from models.extensions import db
from models.models import Text, Word


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
OWNER_USER_ID = 1  # login_client と同じユーザーID
OTHER_USER_ID = 2  # login_client とは別の、実在するユーザーID


# ============================================================
# テストデータ作成・削除用ヘルパー
# ============================================================

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


def _get_word_string():
    with app.app_context():
        return db.session.get(Word, WORD_ID).word


# ============================================================
# GET /text-delete/<id> - そもそも許可されていないメソッド
# ============================================================

def test_text_delete_get_not_allowed(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"削除GET不可{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        response = login_client.get(f"/text-delete/{text_id}")
        assert response.status_code == 405
    finally:
        _delete_text_if_exists(text_id)


# ============================================================
# POST /text-delete/<id> - 認可
# ============================================================

def test_text_delete_requires_login(client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"削除未ログイン{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        response = client.post(f"/text-delete/{text_id}")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

        # 削除されていないことを確認
        with app.app_context():
            assert db.session.get(Text, text_id) is not None
    finally:
        _delete_text_if_exists(text_id)


def test_text_delete_blocks_other_users_text(login_client):
    word = _get_word_string()
    text_id = _create_text(OTHER_USER_ID, f"削除他人{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        response = login_client.post(f"/text-delete/{text_id}", follow_redirects=True)
        html = response.get_data(as_text=True)
        assert "他ユーザーの文章は削除できません" in html

        # 削除されていないことを確認
        with app.app_context():
            assert db.session.get(Text, text_id) is not None
    finally:
        _delete_text_if_exists(text_id)


def test_text_delete_404_for_nonexistent_id(login_client):
    response = login_client.post("/text-delete/999999999")
    assert response.status_code == 404


# ============================================================
# POST /text-delete/<id> - 正常系
# ============================================================

def test_text_delete_success(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"削除対象{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        with app.app_context():
            db.session.remove()
        response = login_client.post(f"/text-delete/{text_id}", follow_redirects=True)

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "文章を削除しました" in html

        with app.app_context():
            assert db.session.get(Text, text_id) is None
    finally:
        _delete_text_if_exists(text_id)


def test_text_delete_does_not_affect_other_texts(login_client):
    word = _get_word_string()
    keep_id = _create_text(OWNER_USER_ID, f"削除対象外{randint(1,100000)}",
                            f"{word}を含む本文です。")
    delete_id = _create_text(OWNER_USER_ID, f"削除対象本命{randint(1,100000)}",
                              f"{word}を含む本文です。")
    try:
        login_client.post(f"/text-delete/{delete_id}", follow_redirects=True)

        with app.app_context():
            assert db.session.get(Text, delete_id) is None
            assert db.session.get(Text, keep_id) is not None
    finally:
        _delete_text_if_exists(keep_id)
        _delete_text_if_exists(delete_id)