from random import randint
import pytest
from app import app
from models.extensions import db
from models.models import Text, Word, Good_text, Good_word


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

XHR_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


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


def _find_item(items, item_id):
    return next((item for item in items if item["id"] == item_id), None)


# ============================================================
# POST /contents - そもそも許可されていないメソッド
# ============================================================

def test_contents_post_not_allowed(login_client):
    response = login_client.post("/contents")
    assert response.status_code == 405


# ============================================================
# GET /contents - 基本動作
# ============================================================

def test_contents_default_type_is_word(client):
    response = client.get("/contents", headers=XHR_HEADERS)
    assert response.status_code == 200

    data = response.get_json()
    assert data["type"] == "word"


def test_contents_type_text(client):
    response = client.get("/contents", query_string={"type": "text"}, headers=XHR_HEADERS)
    assert response.status_code == 200

    data = response.get_json()
    assert data["type"] == "text"


def test_contents_html_response_without_xhr(client):
    response = client.get("/contents")
    assert response.status_code == 200
    assert "text/html" in response.content_type


# ============================================================
# GET /contents - 文章の検索・下書き除外
# ============================================================

def test_contents_text_search_finds_published_and_excludes_draft(client):
    word = _get_word_string()
    keyword = f"検索対象{randint(1,100000)}"

    published_id = _create_text(
        TEXT_OWNER_USER_ID, f"{keyword}公開", f"{word}{keyword}を含む公開文章です。", text_status=0
    )
    draft_id = _create_text(
        TEXT_OWNER_USER_ID, f"{keyword}下書き", f"{word}{keyword}を含む下書き文章です。", text_status=1
    )

    try:
        response = client.get(
            "/contents",
            query_string={"type": "text", "q": keyword},
            headers=XHR_HEADERS,
        )
        assert response.status_code == 200

        data = response.get_json()
        ids = [item["id"] for item in data["items"]]

        assert published_id in ids
        assert draft_id not in ids
    finally:
        _delete_text_if_exists(published_id)
        _delete_text_if_exists(draft_id)


# ============================================================
# GET /contents - ログイン状態によるis_goodの違い
# ============================================================

def test_contents_text_is_good_true_when_logged_in_and_liked(login_client):
    word = _get_word_string()
    keyword = f"いいね確認{randint(1,100000)}"
    text_id = _create_text(TEXT_OWNER_USER_ID, keyword, f"{word}{keyword}を含む本文です。")

    try:
        _create_good_text(LOGIN_USER_ID, text_id)

        response = login_client.get(
            "/contents",
            query_string={"type": "text", "q": keyword},
            headers=XHR_HEADERS,
        )
        data = response.get_json()
        item = _find_item(data["items"], text_id)

        assert item is not None
        assert item["is_good"] is True
    finally:
        _delete_good_text_if_exists(LOGIN_USER_ID, text_id)
        _delete_text_if_exists(text_id)


def test_contents_text_is_good_false_when_not_logged_in(client):
    word = _get_word_string()
    keyword = f"未ログインいいね{randint(1,100000)}"
    text_id = _create_text(TEXT_OWNER_USER_ID, keyword, f"{word}{keyword}を含む本文です。")

    try:
        # 他ユーザーがいいね済みでも、未ログインなら is_good は False になるはず
        _create_good_text(OTHER_USER_ID, text_id)

        response = client.get(
            "/contents",
            query_string={"type": "text", "q": keyword},
            headers=XHR_HEADERS,
        )
        data = response.get_json()
        item = _find_item(data["items"], text_id)

        assert item is not None
        assert item["is_good"] is False
    finally:
        _delete_good_text_if_exists(OTHER_USER_ID, text_id)
        _delete_text_if_exists(text_id)


def test_contents_word_is_good_true_when_logged_in_and_liked(login_client):
    try:
        _delete_good_word_if_exists(LOGIN_USER_ID, WORD_ID)
        _create_good_word(LOGIN_USER_ID, WORD_ID)

        response = login_client.get(
            "/contents",
            query_string={"type": "word"},
            headers=XHR_HEADERS,
        )
        data = response.get_json()
        item = _find_item(data["items"], WORD_ID)

        assert item is not None
        assert item["is_good"] is True
    finally:
        _delete_good_word_if_exists(LOGIN_USER_ID, WORD_ID)


def test_contents_word_is_good_false_when_not_logged_in(client):
    try:
        _delete_good_word_if_exists(OTHER_USER_ID, WORD_ID)
        _create_good_word(OTHER_USER_ID, WORD_ID)

        response = client.get(
            "/contents",
            query_string={"type": "word"},
            headers=XHR_HEADERS,
        )
        data = response.get_json()
        item = _find_item(data["items"], WORD_ID)

        assert item is not None
        assert item["is_good"] is False
    finally:
        _delete_good_word_if_exists(OTHER_USER_ID, WORD_ID)


# ============================================================
# GET /contents - 並び替え
# ============================================================

def test_contents_text_sort_date_asc_and_desc(client):
    word = _get_word_string()
    keyword = f"並び順{randint(1,100000)}"

    first_id = _create_text(TEXT_OWNER_USER_ID, f"{keyword}A", f"{word}{keyword}Aを含む本文です。")
    second_id = _create_text(TEXT_OWNER_USER_ID, f"{keyword}B", f"{word}{keyword}Bを含む本文です。")

    try:
        response_asc = client.get(
            "/contents",
            query_string={"type": "text", "q": keyword, "sort": "date_asc"},
            headers=XHR_HEADERS,
        )
        ids_asc = [item["id"] for item in response_asc.get_json()["items"]]
        assert ids_asc == [first_id, second_id]

        response_desc = client.get(
            "/contents",
            query_string={"type": "text", "q": keyword, "sort": "date_desc"},
            headers=XHR_HEADERS,
        )
        ids_desc = [item["id"] for item in response_desc.get_json()["items"]]
        assert ids_desc == [second_id, first_id]
    finally:
        _delete_text_if_exists(first_id)
        _delete_text_if_exists(second_id)


def test_contents_text_sort_good_desc(client):
    word = _get_word_string()
    keyword = f"いいね順{randint(1,100000)}"

    less_liked_id = _create_text(TEXT_OWNER_USER_ID, f"{keyword}少", f"{word}{keyword}少を含む本文です。")
    more_liked_id = _create_text(TEXT_OWNER_USER_ID, f"{keyword}多", f"{word}{keyword}多を含む本文です。")

    try:
        _create_good_text(LOGIN_USER_ID, more_liked_id)
        _create_good_text(OTHER_USER_ID, more_liked_id)

        response = client.get(
            "/contents",
            query_string={"type": "text", "q": keyword, "sort": "good_desc"},
            headers=XHR_HEADERS,
        )
        ids = [item["id"] for item in response.get_json()["items"]]
        assert ids == [more_liked_id, less_liked_id]
    finally:
        _delete_good_text_if_exists(LOGIN_USER_ID, more_liked_id)
        _delete_good_text_if_exists(OTHER_USER_ID, more_liked_id)
        _delete_text_if_exists(less_liked_id)
        _delete_text_if_exists(more_liked_id)