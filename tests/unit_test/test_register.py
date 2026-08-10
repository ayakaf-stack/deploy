import pytest
from werkzeug.security import check_password_hash
from app import app, db, User
from random import randint

@pytest.fixture
def client():
    app.config['TESTING']=True

    with app.test_client() as client:
        with app.app_context():
            yield client


# 登録画面(GET)
def test_register_get(client):
    response = client.get("/register")

    assert response.status_code == 200
    assert "新規登録".encode("utf-8") in response.data


# 登録完了(POST) メールアドレスを変えてテストする
def test_register_success(client):

    name = f"testuser{randint(1,10000)}"
    email = f"testuser{randint(1,10000)}@test.com"

    response = client.post("/register", data={
        "user_name": name,
        "email": email,
        "password": "password123"
    })

    assert response.status_code == 302
    assert "/login" in response.location


    user = User.query.filter_by(
        email=email
    ).first()

    assert user is not None
    assert user.user_name == name

    with app.app_context():
        user = User.query.filter_by(user_name=name).first()

        db.session.delete(user)
        db.session.commit()



# ユーザー名未入力チェック
def test_register_empty_user_name(client):

    response = client.post("/register", data={
        "user_name": "",
        "email": "test@test.com",
        "password": "password123"
    }, follow_redirects=True)

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Flashメッセージ確認
    assert "全ての項目を正しく入力してください" in html


# メールアドレス未入力チェック
def test_register_empty_email(client):

    response = client.post("/register", data={
        "user_name": "test_user",
        "email": "",
        "password": "password123"
    }, follow_redirects=True)

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Flashメッセージ確認
    assert "全ての項目を正しく入力してください" in html


# パスワード未入力チェック
def test_register_empty_password(client):

    response = client.post("/register", data={
        "user_name": "test_user",
        "email": "test@test.com",
        "password": ""
    }, follow_redirects=True)

    html = response.get_data(as_text=True)

    # 未入力エラーのFlashメッセージ確認
    assert "全ての項目を正しく入力してください" in html


# ユーザー名255文字以上
def test_register_user_name_over_255(client):

    response = client.post("/register", data={
        "user_name": "a" * 256,
        "email": "test@test.com",
        "password": "password123"
    })

    # 登録画面へリダイレクト
    assert response.status_code == 302
    assert "/register" in response.location

    # フラッシュメッセージ確認
    with client.session_transaction() as session:
        assert "ユーザー名は255文字以内で入力してください" in session["_flashes"][0][1]


# 不正なメールアドレス
def test_register_invalid_email(client):
    response = client.post("/register", data={
        "user_name" : "test_user",
        "email" : "test@test",
        "password" : "password123"
    }, follow_redirects=True)

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # フラッシュメッセージ確認
    assert "既に登録済みのメールアドレスか不正なメールアドレスです" in html


# パスワード8文字未満
def test_register_password_less_than_8(client):

    response = client.post("/register", data={
        "user_name": "test_user",
        "email": "password_less8@test.com",
        "password": "1234567"  # 7文字
    }, follow_redirects=True)

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Flashメッセージ確認
    assert "パスワードは8文字以上16文字以内で入力してください" in html

# パスワード17文字以上
def test_register_password_over_16(client):

    response = client.post("/register", data={
        "user_name": "test_user",
        "email": "password_over16@test.com",
        "password": "12345678901234567"  # 17文字
    }, follow_redirects=True)

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Flashメッセージ確認
    assert "パスワードは8文字以上16文字以内で入力してください" in html


# 重複メールアドレス
def test_register_duplicate_email(client):

    name = f"testuser{randint(1,10000)}"
    email = f"testuser{randint(1,10000)}@test.com"

    response = client.post("/register", data={
        "user_name": name,
        "email": email,
        "password": "password123"
    })

    response = client.post("/register", data={
        "user_name" : name,
        "email" : email,
        "password" : "password123"
    }, follow_redirects=True)

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "既に登録済みのメールアドレスか不正なメールアドレスです" in html

    with app.app_context():
        user = User.query.filter_by(user_name=name).first()

        db.session.delete(user)
        db.session.commit()