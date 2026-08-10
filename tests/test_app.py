import pytest
from random import randint
from app import app
from models.models import Text
from models.extensions import db

# テストクライアントを作成
@pytest.fixture
def client():
    app.config['TESTING']=True

    with app.test_client() as client:
        yield client

# ログイン済みユーザー
@pytest.fixture
def login_client(client):

    with client.session_transaction() as session:
        session["user_id"] = 14 
        session["user_name"] = "aaa"

    return client

# 管理者ログイン済み
@pytest.fixture
def admin_client(client):
    with client.session_transaction() as session:
        session["is_admin"] = True
    return client


# トップページのテスト
def test_index(client):
    response = client.get("/")
    # StatusCode 200の確認
    assert response.status_code == 200
    # 出力文字の確認
    html = response.get_data(as_text=True)
    assert "美しい日本語" in html

# ログインのテスト
def test_login_safe(client):
    # 認証後302リダイレクトを確認
    response = client.post(
        "/login",
        data={
            "email": "aaa@aaa.com",
            "password": "testtest"
        }
    )

    assert response.status_code == 302

# ログインのテスト(失敗)
def test_login_fail(client):
    # 認証失敗からリダイレクト
    response = client.post(
        "/login",
        data={
            "email": "aaa@aaa.com",
            "password": "abcd1234"
        },
        follow_redirects=True
     )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    # フラッシュメッセージを確認
    assert "ログインに失敗しました" in html

# 新規文章登録テスト(成功)
def test_make_sentence(login_client):
    print(app.config["SQLALCHEMY_DATABASE_URI"]) 
    response = login_client.post(
            "/text-new/29",
            data={
                "title":"投稿テスト単体テスト",
                "main_text":f"山眠るに関するテスト投稿{randint(1,100)}"
            },
            follow_redirects = True
         )
      
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "文章を作成しました" in html

