import pytest
from app import app
from models.extensions import db
from models.models import Word, Text, Good_word, Good_text



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
 
 
def _get_index_json(test_client):
    response = test_client.get("/", headers={"X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    return response.get_json()
 
 
# ============================================================
# route '/' (TOP画面) のテスト
# ============================================================
 
# 1. 通常アクセス(非Ajax)でHTMLが200で返る
def test_index_returns_200_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
 
 
# 2. 通常アクセス時、レンダリングされたHTMLに単語が含まれている
def test_index_html_contains_word(client):
    response = client.get("/")
    html = response.get_data(as_text=True)
 
    with app.app_context():
        words = Word.query.all()
 
    assert any(w.word in html for w in words)
 
 
# 3. Ajaxアクセスで200・JSON構造が返る
def test_index_ajax_returns_json_with_expected_keys(client):
    response = client.get("/", headers={"X-Requested-With": "XMLHttpRequest"})
 
    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
 
    data = response.get_json()
    assert set(data.keys()) == {"word", "is_good", "good_count", "texts"}
    assert set(data["word"].keys()) == {"id", "word", "reading", "mean"}
    assert isinstance(data["texts"], list)
 
 
# 4. 返ってきた単語データが実際のDBの内容と一致する
def test_index_word_matches_db(client):
    data = _get_index_json(client)
    word_id = data["word"]["id"]
 
    with app.app_context():
        word = db.session.get(Word, word_id)
 
    assert word is not None
    assert data["word"]["word"] == word.word
    assert data["word"]["reading"] == word.reading
    assert data["word"]["mean"] == word.mean
 
 
# 5. good_count(単語のいいね数)が実際のDBの件数と一致する
def test_index_good_count_matches_db(client):
    data = _get_index_json(client)
    word_id = data["word"]["id"]
 
    expected_count = Good_word.query.filter_by(word_id=word_id).count()
    assert data["good_count"] == expected_count
 
 
# 6. 未ログイン時、is_good(単語)は必ずFalse
def test_index_is_good_false_when_not_logged_in(client):
    data = _get_index_json(client)
    assert data["is_good"] is False
 
 
# 7. ログイン時、is_good(単語)が実際のいいね登録状況と一致する
def test_index_is_good_matches_db_when_logged_in(login_client):
    data = _get_index_json(login_client)
    word_id = data["word"]["id"]
 
    with app.app_context():
        expected = Good_word.query.filter_by(word_id=word_id, user_id=14).first() is not None

    assert data["is_good"] == expected
 
 
# 8. texts配列の各要素が、必ず公開(text_status=0)の文章である
def test_index_texts_are_all_public(client):
    data = _get_index_json(client)
 
    with app.app_context():
        for item in data["texts"]:
            text = db.session.get(Text, item["id"])
            assert text is not None
            assert text.text_status == 0
 
 
# 9. texts配列の各要素の本文が、返ってきた単語を含んでいる
def test_index_texts_contain_the_word(client):
    data = _get_index_json(client)
    target_word = data["word"]["word"]
 
    for item in data["texts"]:
        assert target_word in item["main_text"]
 
 
# 10. texts配列の各要素のgood_countが実際のDBの件数と一致する
def test_index_texts_good_count_matches_db(client):
    data = _get_index_json(client)
 
    with app.app_context():
        for item in data["texts"]:
            expected_count = Good_text.query.filter_by(text_id=item["id"]).count()
            assert item["good_count"] == expected_count
 
 
# 11. ログイン時、texts配列の各要素のis_goodが実際のいいね登録状況と一致する
def test_index_texts_is_good_matches_db_when_logged_in(login_client):
    data = _get_index_json(login_client)
 
    with app.app_context():
        for item in data["texts"]:
            expected = Good_text.query.filter_by(
                text_id=item["id"], user_id=14
            ).first() is not None
            assert item["is_good"] == expected
 
 
# 12. 未ログイン時、texts配列の各要素のis_goodは必ずFalse
def test_index_texts_is_good_false_when_not_logged_in(client):
    data = _get_index_json(client)
 
    for item in data["texts"]:
        assert item["is_good"] is False
 
 
# 13. 関連する公開文章が0件の単語が選ばれた場合でもエラーにならない
#     (ランダム選択のため再現性は低く、失敗条件にはせず200が返り続けることのみ確認する)
def test_index_handles_word_with_no_texts(client):
    for _ in range(20):
        response = client.get("/", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 200
        data = response.get_json()
        if data["texts"] == []:
            break