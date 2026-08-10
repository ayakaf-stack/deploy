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
        return text.id


def _delete_text(text_id):
    with app.app_context():
        text = db.session.get(Text, text_id)
        if text is not None:
            db.session.delete(text)
            db.session.commit()


def _get_word_string():
    with app.app_context():
        return db.session.get(Word, WORD_ID).word


# ============================================================
# GET /text-edit/<id>
# ============================================================

def test_text_edit_get_requires_login(client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集GET未ログイン{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        response = client.get(f"/text-edit/{text_id}")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]
    finally:
        _delete_text(text_id)


def test_text_edit_get_shows_form_for_owner(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集GET本人{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        response = login_client.get(f"/text-edit/{text_id}")
        assert response.status_code == 200
    finally:
        _delete_text(text_id)


def test_text_edit_get_blocks_other_users_text(login_client):
    word = _get_word_string()
    text_id = _create_text(OTHER_USER_ID, f"編集GET他人{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        response = login_client.get(f"/text-edit/{text_id}", follow_redirects=True)
        html = response.get_data(as_text=True)
        assert "他ユーザーの文章は編集できません" in html
    finally:
        _delete_text(text_id)


def test_text_edit_get_404_for_nonexistent_id(login_client):
    response = login_client.get("/text-edit/999999999")
    assert response.status_code == 404


# ============================================================
# POST /text-edit/<id> - 認可
# ============================================================

def test_text_edit_post_requires_login(client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集POST未ログイン{randint(1,100000)}",
                            f"{word}を含む本文です。")
    try:
        response = client.post(f"/text-edit/{text_id}", data={
            "title": "変更後タイトル",
            "main_text": f"{word}を含む変更後の本文です。",
            "text_status": "0",
        })
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]
    finally:
        _delete_text(text_id)


def test_text_edit_post_blocks_other_users_text(login_client):
    word = _get_word_string()
    original_title = f"編集POST他人{randint(1,100000)}"
    original_main_text = f"{word}を含む元の本文です。"
    text_id = _create_text(OTHER_USER_ID, original_title, original_main_text)
    try:
        response = login_client.post(f"/text-edit/{text_id}", data={
            "title": "書き換えようとしたタイトル",
            "main_text": f"{word}を含む書き換えようとした本文です。",
            "text_status": "0",
        }, follow_redirects=True)

        html = response.get_data(as_text=True)
        assert "他ユーザーの文章は編集できません" in html

        # 実際には書き換わっていないことを確認
        with app.app_context():
            text = db.session.get(Text, text_id)
            assert text.title == original_title
            assert text.main_text == original_main_text
    finally:
        _delete_text(text_id)


# ============================================================
# POST /text-edit/<id> - バリデーション(本人の文章、更新されないことを確認)
# ============================================================

def test_text_edit_missing_title(login_client):
    word = _get_word_string()
    original_title = f"編集バリデ元タイトル{randint(1,100000)}"
    original_main_text = f"{word}を含む元の本文です。"
    text_id = _create_text(OWNER_USER_ID, original_title, original_main_text)
    try:
        response = login_client.post(f"/text-edit/{text_id}", data={
            "title": "",
            "main_text": f"{word}を含む変更しようとした本文です。",
            "text_status": "0",
        })
        html = response.get_data(as_text=True)
        assert "タイトルを入力してください" in html

        with app.app_context():
            text = db.session.get(Text, text_id)
            assert text.title == original_title
    finally:
        _delete_text(text_id)


def test_text_edit_title_too_long(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集バリデ長{randint(1,100000)}",
                            f"{word}を含む元の本文です。")
    try:
        response = login_client.post(f"/text-edit/{text_id}", data={
            "title": "あ" * 256,
            "main_text": f"{word}を含む変更しようとした本文です。",
            "text_status": "0",
        })
        html = response.get_data(as_text=True)
        assert "タイトルは255文字以内で入力してください" in html
    finally:
        _delete_text(text_id)


def test_text_edit_missing_main_text(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集バリデ本文なし{randint(1,100000)}",
                            f"{word}を含む元の本文です。")
    try:
        response = login_client.post(f"/text-edit/{text_id}", data={
            "title": "変更後タイトル",
            "main_text": "",
            "text_status": "0",
        })
        html = response.get_data(as_text=True)
        assert "本文を入力してください" in html
    finally:
        _delete_text(text_id)


def test_text_edit_main_text_too_short(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集バリデ本文短{randint(1,100000)}",
                            f"{word}を含む元の本文です。")
    try:
        response = login_client.post(f"/text-edit/{text_id}", data={
            "title": "変更後タイトル",
            "main_text": "短い",
            "text_status": "0",
        })
        html = response.get_data(as_text=True)
        assert "本文は10文字以上・400文字以内で入力してください" in html
    finally:
        _delete_text(text_id)


def test_text_edit_main_text_missing_selected_word(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集バリデ単語なし{randint(1,100000)}",
                            f"{word}を含む元の本文です。")
    try:
        response = login_client.post(f"/text-edit/{text_id}", data={
            "title": "変更後タイトル",
            "main_text": "対象の単語を含まない変更後の本文です。",
            "text_status": "0",
        })
        html = response.get_data(as_text=True)
        assert f"本文に選択した単語（{word}）が含まれていません" in html
    finally:
        _delete_text(text_id)


# ============================================================
# POST /text-edit/<id> - 正常系
# ============================================================

def test_text_edit_success_updates_text(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集前タイトル{randint(1,100000)}",
                            f"{word}を含む編集前の本文です。")
    try:
        new_title = f"編集後タイトル{randint(1,100000)}"
        new_main_text = f"{word}を含む編集後の本文です。"

        response = login_client.post(f"/text-edit/{text_id}", data={
            "title": new_title,
            "main_text": new_main_text,
            "text_status": "0",
        }, follow_redirects=True)

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "文章を編集しました" in html

        with app.app_context():
            text = db.session.get(Text, text_id)
            assert text.title == new_title
            assert text.main_text == new_main_text
            assert text.text_status == 0
    finally:
        _delete_text(text_id)


def test_text_edit_can_set_draft_status(login_client):
    word = _get_word_string()
    text_id = _create_text(OWNER_USER_ID, f"編集下書き化{randint(1,100000)}",
                            f"{word}を含む本文です。", text_status=0)
    try:
        response = login_client.post(f"/text-edit/{text_id}", data={
            "title": f"下書きにするタイトル{randint(1,100000)}",
            "main_text": f"{word}を含む下書きにする本文です。",
            "text_status": "1",
        }, follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            text = db.session.get(Text, text_id)
            assert text.text_status == 1
    finally:
        _delete_text(text_id)


def test_text_edit_duplicate_with_another_text_becomes_draft(login_client):
    word = _get_word_string()

    # 既存の別の文章(公開)
    fixed_title = f"重複対象タイトル{randint(1,100000)}"
    fixed_main_text = f"{word}を含む重複対象の本文です。"
    other_text_id = _create_text(OWNER_USER_ID, fixed_title, fixed_main_text, text_status=0)

    # 編集対象の文章(別内容で作成)
    target_text_id = _create_text(OWNER_USER_ID, f"編集対象タイトル{randint(1,100000)}",
                                   f"{word}を含む編集対象の本文です。", text_status=0)
    try:
        # 編集対象の内容を、既存の別文章と完全に一致させる
        response = login_client.post(f"/text-edit/{target_text_id}", data={
            "title": fixed_title,
            "main_text": fixed_main_text,
            "text_status": "0",
        }, follow_redirects=True)

        html = response.get_data(as_text=True)
        assert "この文章は下書き保存されます" in html

        with app.app_context():
            edited_text = db.session.get(Text, target_text_id)
            assert edited_text.title == fixed_title
            assert edited_text.main_text == fixed_main_text
            assert edited_text.text_status == 1  # 下書きになっている
    finally:
        _delete_text(target_text_id)
        _delete_text(other_text_id)