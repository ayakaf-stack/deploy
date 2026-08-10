from random import randint
from app import app
from models.extensions import db
from models.models import Text, Word
import pytest

WORD_ID = 29  # 既存の単語ID


@pytest.fixture
def client():
    app.config['TESTING']=True

    with app.test_client() as client:
        yield client

# ログイン済みユーザー
@pytest.fixture
def login_client(client):

    with client.session_transaction() as session:
        session["user_id"] = 1 
        session["user_name"] = "aaa"

    return client


# ============================================================
# GET /text-new/<id>
# ============================================================

def test_text_new_get_requires_login(client):
    response = client.get(f"/text-new/{WORD_ID}")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_text_new_get_shows_form(login_client):
    response = login_client.get(f"/text-new/{WORD_ID}")
    assert response.status_code == 200


# ============================================================
# POST /text-new/<id> - 認可
# ============================================================

def test_text_new_post_requires_login(client):
    response = client.post(f"/text-new/{WORD_ID}", data={
        "title": "未ログインテスト",
        "main_text": "ログインなしで投稿しようとするテストです。",
    })
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ============================================================
# POST /text-new/<id> - バリデーション
# (いずれもエラー時はDBに書き込まれないため、後片付け不要)
# ============================================================

def test_text_new_missing_title(login_client):
    response = login_client.post(f"/text-new/{WORD_ID}", data={
        "title": "",
        "main_text": "タイトルなしで投稿しようとするテスト本文です。",
    })
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "タイトルを入力してください" in html


def test_text_new_title_too_long(login_client):
    response = login_client.post(f"/text-new/{WORD_ID}", data={
        "title": "あ" * 256,
        "main_text": "タイトルが長すぎる場合のテスト本文です。",
    })
    html = response.get_data(as_text=True)
    assert "タイトルは255文字以内で入力してください" in html


def test_text_new_missing_main_text(login_client):
    response = login_client.post(f"/text-new/{WORD_ID}", data={
        "title": "本文なしテスト",
        "main_text": "",
    })
    html = response.get_data(as_text=True)
    assert "本文を入力してください" in html


def test_text_new_main_text_too_short(login_client):
    response = login_client.post(f"/text-new/{WORD_ID}", data={
        "title": "本文短すぎテスト",
        "main_text": "短い",
    })
    html = response.get_data(as_text=True)
    assert "本文は10文字以上・400文字以内で入力してください" in html


def test_text_new_main_text_missing_selected_word(login_client):
    with app.app_context():
        target_word = db.session.get(Word, WORD_ID).word

    response = login_client.post(f"/text-new/{WORD_ID}", data={
        "title": "対象単語なしテスト",
        "main_text": "この本文には対象の単語がわざと含まれていません。",
    })
    html = response.get_data(as_text=True)
    assert f"本文に選択した単語（{target_word}）が含まれていません" in html


# ============================================================
# POST /text-new/<id> - 正常系
# (DBに実際に書き込まれるため、テストの最後に必ず削除する)
# ============================================================

def test_text_new_success_creates_text(login_client):
    with app.app_context():
        target_word = db.session.get(Word, WORD_ID).word

    title = f"作成テスト{randint(1, 100000)}"
    main_text = f"{target_word}に関するテスト投稿本文です{randint(1, 100)}。"

    response = login_client.post(f"/text-new/{WORD_ID}", data={
        "title": title,
        "main_text": main_text,
    }, follow_redirects=True)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "文章を作成しました" in html

    with app.app_context():
        text = Text.query.filter_by(title=title).order_by(Text.id.desc()).first()
        assert text is not None
        assert text.user_id == 1
        assert text.word == WORD_ID
        assert text.text_status == 0
        text_id = text.id

        # 後片付け
        db.session.delete(text)
        db.session.commit()


def test_text_new_duplicate_becomes_draft(login_client):
    with app.app_context():
        target_word = db.session.get(Word, WORD_ID).word

    title = f"重複テスト{randint(1, 100000)}"
    main_text = f"{target_word}を含む重複確認用の本文です{randint(1, 100)}。"
    payload = {"title": title, "main_text": main_text}

    login_client.post(f"/text-new/{WORD_ID}", data=payload, follow_redirects=True)
    response = login_client.post(f"/text-new/{WORD_ID}", data=payload, follow_redirects=True)

    html = response.get_data(as_text=True)
    assert "この文章は下書き保存されます" in html

    with app.app_context():
        texts = Text.query.filter_by(title=title).all()
        assert len(texts) == 2
        assert texts[1].text_status == 1

        # 後片付け(作成した2件とも削除)
        for t in texts:
            db.session.delete(t)
        db.session.commit()