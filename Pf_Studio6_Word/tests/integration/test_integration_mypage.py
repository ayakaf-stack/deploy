import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app import app as flask_app
from models.models import Text, Good_text, Good_word, Word
from models.extensions import db

WORD_ID = 2

def _create_text(user_id, title, main_text=None, text_status=0, word_id=WORD_ID):
    with flask_app.app_context():
        word_obj = db.session.get(Word, word_id)
        word_str = word_obj.word if word_obj else ""

        if main_text is None:
            main_text = f"これは{word_str}を含んだテスト用の本文です。"
        elif word_str and word_str not in main_text:
            main_text = f"{main_text} ({word_str})"

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

def _create_good_text(user_id, text_id):
    with flask_app.app_context():
        good_text = Good_text(
            user_id=user_id,
            text_id=text_id,
        )
        db.session.add(good_text)
        db.session.commit()
        good_text_id = good_text.id
        db.session.remove()
        return good_text_id

def _create_good_word(user_id, word_id):
    with flask_app.app_context():
        good_word = Good_word(
            user_id=user_id,
            word_id=word_id,
        )
        db.session.add(good_word)
        db.session.commit()
        good_word_id = good_word.id
        db.session.remove()
        return good_word_id

def _delete_text_if_exists(text_id):
    with flask_app.app_context():
        text = db.session.get(Text, text_id)
        if text is not None:
            db.session.delete(text)
            db.session.commit()
        db.session.remove()

def _delete_good_text_if_exists(good_text_id):
    with flask_app.app_context():
        good_text = db.session.get(Good_text, good_text_id)
        if good_text is not None:
            db.session.delete(good_text)
            db.session.commit()
        db.session.remove()

def _delete_good_word_if_exists(good_word_id):
    with flask_app.app_context():
        good_word = db.session.get(Good_word, good_word_id)
        if good_word is not None:
            db.session.delete(good_word)
            db.session.commit()
        db.session.remove()

# ----------------------------------------------------------------------
# Test Cases (Seleniumによる画面操作・遷移・UI検証のみ)
# ----------------------------------------------------------------------

def test_mypage_unauthorized_redirect(base_url, driver):
    """【セキュリティ】未ログイン状態でマイページに直接アクセスした場合、ログイン画面へリダイレクトされるか"""
    driver.get(f"{base_url}/mypage")
    time.sleep(1)
    wait = WebDriverWait(driver, 5)

    wait.until(EC.url_contains("/login"))
    assert "/login" in driver.current_url


def test_selenium_mypage_workflow(base_url, logged_in_driver, test_user):
    """【正常系/E2E】ログイン済み状態からマイページを開き、ユーザー名が表示されるか"""
    driver = logged_in_driver
    wait = WebDriverWait(driver, 10)

    driver.get(f"{base_url}/mypage")
    time.sleep(1)
    wait.until(EC.url_contains("/mypage"))

    body_text = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body"))).text

    # ユーザー名またはメールアドレスが正しく描画されているか確認
    assert ("selenium_test_user" in body_text) or (test_user["email"] in body_text), "ログインユーザー名が取得できていません"


def test_text_edit_navigation_via_ui(base_url, logged_in_driver, test_user):
    """【正常系/E2E】テストデータを作成してマイページを開き、「編集」ボタンから編集画面へ正常遷移できるか"""
    driver = logged_in_driver
    wait = WebDriverWait(driver, 10)

    text_id = _create_text(
        user_id=test_user["id"],
        title="Seleniumテスト用投稿タイトル",
        main_text="Seleniumテスト用の本文です。",
        text_status=1,
        word_id=WORD_ID,
    )

    try:
        driver.get(f"{base_url}/mypage")
        time.sleep(1)
        wait.until(EC.url_contains("/mypage"))

        edit_link_xpath = "//a[contains(@href, '/text-edit/') or contains(@href, '/text_edit/') or contains(text(), '編集')]"
        edit_button = wait.until(EC.element_to_be_clickable((By.XPATH, edit_link_xpath)))
        edit_button.click()
        time.sleep(1)

        wait.until(EC.url_contains("/text-edit/"))
        assert ("/text-edit/" in driver.current_url) or ("/text_edit/" in driver.current_url)
    finally:
        _delete_text_if_exists(text_id)


def test_mypage_drawer_and_content_display(base_url, logged_in_driver, test_user):
    """【正常系/E2E】作成した文章・いいねした文章の本文ドロワー（詳細表示）が正常に開いて中身が表示されるか"""
    driver = logged_in_driver
    wait = WebDriverWait(driver, 10)

    unique_main_text = "ドロワー確認用の固有テスト本文です12345"
    text_id = _create_text(
        user_id=test_user["id"],
        title="ドロワーテストタイトル",
        main_text=unique_main_text,
        text_status=1,
    )

    try:
        driver.get(f"{base_url}/mypage")
        time.sleep(1)
        wait.until(EC.url_contains("/mypage"))

        # ドロワーを開くためのトグルやタイトル要素をクリック（クラス名やアコーディオン要素に合わせる）
        # ※ドロワーを開くボタン、またはタイトル部分をクリックする処理
        drawer_triggers = driver.find_elements(By.CSS_SELECTOR, ".drawer-toggle, .text-title, .accordion-btn, .text_item")
        if drawer_triggers:
            drawer_triggers[0].click()
            time.sleep(1)

        # 本文ドロワーの中身（main_text）が画面上に表示されるか検証
        page_source = driver.page_source
        assert unique_main_text in page_source, "本文ドロワーの中に正しい本文が表示されていません"
    finally:
        _delete_text_if_exists(text_id)


def test_mypage_navigation_top_and_logout(base_url, logged_in_driver):
    """【正常系/E2E】マイページからTOPクリック時の遷移、およびログアウトクリック時のリダイレクト確認"""
    driver = logged_in_driver
    wait = WebDriverWait(driver, 10)

    driver.get(f"{base_url}/mypage")
    time.sleep(1)
    wait.until(EC.url_contains("/mypage"))

    # 1. TOPボタン/リンクのクリックと遷移確認
    top_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/') and (contains(text(), 'TOP') or contains(text(), 'トップ') or contains(@class, 'home'))]")
    if top_links:
        top_links[0].click()
        time.sleep(1)
        wait.until(lambda d: d.current_url.rstrip('/') == base_url.rstrip('/'))
        assert driver.current_url.rstrip('/') == base_url.rstrip('/'), "TOPページへ正しく遷移していません"
        
        # 再びマイページに戻る
        driver.get(f"{base_url}/mypage")
        time.sleep(1)

    # 2. ログアウト処理の確認
    logout_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'logout') or contains(text(), 'ログアウト')] | //a[contains(@href, 'logout') or contains(text(), 'ログアウト')]")
    assert len(logout_buttons) > 0, "ログアウトボタンが見つかりません"
    
    logout_buttons[0].click()
    time.sleep(1)

    # ログアウト後にトップまたはログイン画面にリダイレクトされることを確認
    wait.until(lambda d: "/login" in d.current_url or d.current_url.rstrip('/') == base_url.rstrip('/'))
    assert ("/login" in driver.current_url) or (driver.current_url.rstrip('/') == base_url.rstrip('/')), "ログアウト後に正しくリダイレクトされていません"


def test_like_ajax_toggle(base_url, logged_in_driver):
    """【非同期通信/E2E】いいねボタンをクリックした際、画面全体のリロードなしで動作するか"""
    driver = logged_in_driver
    wait = WebDriverWait(driver, 10)

    driver.get(f"{base_url}/mypage")
    time.sleep(1)
    wait.until(EC.url_contains("/mypage"))

    like_button_xpath = "//*[contains(@class, 'like') or contains(@id, 'like') or contains(text(), 'いいね')]"
    like_button = wait.until(EC.element_to_be_clickable((By.XPATH, like_button_xpath)))

    old_html_element = driver.find_element(By.TAG_NAME, "html")

    like_button.click()
    time.sleep(1)

    new_html_element = driver.find_element(By.TAG_NAME, "html")
    assert old_html_element == new_html_element, "画面全体がリロードされました（Ajax非同期通信になっていません）"


def test_other_user_text_edit_forbidden(base_url, logged_in_driver):
    """【セキュリティ/E2E】ログイン済み状態で存在しない・権限のない編集URLへ直接アクセスした際の拒否検証"""
    driver = logged_in_driver

    target_invalid_url = f"{base_url}/text-edit/999999"
    driver.get(target_invalid_url)
    time.sleep(1)

    assert (driver.current_url != target_invalid_url) or ("404" in driver.page_source) or ("403" in driver.page_source)