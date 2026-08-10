import os
import socket
import threading
import time
import uuid

import pytest
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

from app import app as flask_app
from models.extensions import db
from models.models import User



# 親(tests/conftest.py)のfixtureを無効化
@pytest.fixture(autouse=True)
def db_session():
    yield None


# ============================================================
# Flaskサーバーをバックグラウンドスレッドで起動
# （テストセッション全体で1回だけ起動する）
# ============================================================

def _get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ServerThread(threading.Thread):
    def __init__(self, app, host, port):
        super().__init__(daemon=True)
        self.server = make_server(host, port, app)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


@pytest.fixture(scope="session")
def live_server():
    """結合テスト全体で1回だけ、別スレッドでFlaskアプリを起動する"""
    flask_app.config.update({"TESTING": True})

    host = "127.0.0.1"
    port = _get_free_port()

    server = _ServerThread(flask_app, host, port)
    server.start()

    base_url = f"http://{host}:{port}"

    # サーバーが起動して接続できるようになるまで待つ
    for _ in range(50):
        try:
            with socket.create_connection((host, port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("テスト用Flaskサーバーの起動に失敗しました")

    yield base_url

    server.shutdown()


@pytest.fixture
def base_url(live_server):
    """各テストから使うベースURL"""
    return live_server


# ============================================================
# WebDriver
# テストごとに毎回起動・終了する（安全だが起動コストはやや高い）
# 画面表示ありがデフォルト。SELENIUM_HEADLESS=1 で headless に切替可能
# ============================================================

@pytest.fixture
def driver():
    from selenium import webdriver

    options = webdriver.ChromeOptions()

    if os.getenv("SELENIUM_HEADLESS") == "1":
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1280,900")

    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(3)

    yield drv

    drv.quit()


# ============================================================
# テスト専用ユーザー
# テストごとに使い捨てのユーザーをDBへ直接作成し、
# テスト終了後に削除する（register画面は経由しない）
# ============================================================

TEST_USER_PASSWORD = "SeleniumTest123"


def _create_test_user():
    email = f"selenium_test_{uuid.uuid4().hex}@example.com"
    with flask_app.app_context():
        user = User(
            user_name="selenium_test_user",
            email=email,
            password_hash=generate_password_hash(TEST_USER_PASSWORD),
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        db.session.expunge_all()
        db.session.remove()
    return user_id, email


def _delete_test_user_if_exists(user_id):
    with flask_app.app_context():
        user = db.session.get(User, user_id)
        if user is not None:
            db.session.delete(user)
            db.session.commit()
        db.session.remove()


@pytest.fixture
def test_user():
    """使い捨てのテストユーザーを作成し、テスト終了後に削除する"""
    user_id, email = _create_test_user()

    yield {"id": user_id, "email": email, "password": TEST_USER_PASSWORD}

    _delete_test_user_if_exists(user_id)


# ============================================================
# ログイン済み状態のdriverを作るヘルパー
#
# test_user で作成した使い捨てユーザーで、実際にログインフォームを
# 操作してログインする（ログイン処理自体の検証は test_login_flow.py
# など別ファイルで行うこと）。
# ============================================================

@pytest.fixture
def logged_in_driver(driver, base_url, test_user):
    driver.get(f"{base_url}/login")
    driver.find_element("name", "email").send_keys(test_user["email"])
    driver.find_element("name", "password").send_keys(test_user["password"])
    driver.find_element("css selector", "button[type='submit']").click()

    return driver