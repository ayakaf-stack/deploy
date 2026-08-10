import pytest
from app import app as main_app  # main_app という名前でインポート
from models.extensions import db

@pytest.fixture(autouse=True)
def forbid_schema_destruction(monkeypatch):
    """drop_all・create_allが誤って呼ばれても実行させない安全装置"""
    def _blocked(*args, **kwargs):
        raise RuntimeError("drop_all/create_allはテストコードで使用禁止です")

    monkeypatch.setattr(db, "drop_all", _blocked)
    monkeypatch.setattr(db, "create_all", _blocked)


@pytest.fixture
def app():
    """テスト用のFlask App"""
    main_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False
    })
    yield main_app


@pytest.fixture
def client(app):
    """テスト用のHTTPクライアント"""
    return app.test_client()


@pytest.fixture(autouse=True)
def db_session(app):
    """各テスト実行後にデータベースの変更を自動でロールバック"""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()

        yield db.session

        db.session.remove()
        transaction.rollback()
        connection.close()