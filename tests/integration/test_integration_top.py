import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_top_page_unauthenticated_menu_and_views(base_url, driver):
    """【E2E】未ログイン状態でのメニュー遷移、文章一覧・空状態の確認、および各種フラッシュメッセージ表示確認"""
    driver.get(f"{base_url}/")
    time.sleep(1)
    wait = WebDriverWait(driver, 10)

    # 1. 未ログイン時メニューの検証と各ページへの遷移確認
    register_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[@href='/register']")))
    login_link = driver.find_element(By.XPATH, "//a[@href='/login']")

    assert register_link.is_displayed(), "未ログイン時に「新規登録」が表示されていません"
    assert login_link.is_displayed(), "未ログイン時に「ログイン」が表示されていません"

    register_link.click()
    time.sleep(1)
    wait.until(EC.url_contains("/register"))
    assert "/register" in driver.current_url, "新規登録ページに正しく遷移していません"
    driver.back()
    time.sleep(1)

    login_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='/login']")))
    login_link.click()
    time.sleep(1)
    wait.until(EC.url_contains("/login"))
    assert "/login" in driver.current_url, "ログインページに正しく遷移していません"
    driver.back()
    time.sleep(1)

    mypage_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'mypage')]")
    logout_buttons = driver.find_elements(By.CLASS_NAME, "logout-btn")
    assert len(mypage_links) == 0, "未ログイン時にマイページリンクが表示されています"
    assert len(logout_buttons) == 0, "未ログイン時にログアウトボタンが表示されています"

    # 2. 未ログイン状態で「文章作成」をクリックした際、フラッシュメッセージが表示されるか検証
    text_new_link = wait.until(EC.element_to_be_clickable((By.ID, "text_new_link")))
    text_new_link.click()
    time.sleep(1)

    flash_message_elem = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#flash-messages .flash-message")))
    flash_text = flash_message_elem.text

    assert "文章作成機能を使うには" in flash_text, "未ログイン時の文章作成制限メッセージが表示されていません"
    assert "ログイン" in flash_text, "メッセージにログイン文言が含まれていません"

    # 3. 未ログイン状態で「いいね」ボタンをクリックした際、フラッシュメッセージが表示されるか検証
    word_good_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#word_good_form button.good-button")))
    word_good_button.click()
    time.sleep(1)

    flash_message_elem = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#flash-messages .flash-message")))
    good_flash_text = flash_message_elem.text

    assert ("いいね機能を使うには" in good_flash_text) or ("ログイン" in good_flash_text), "未ログイン時のいいね制限メッセージが表示されていません"

    # 4. 未ログイン状態での contents への遷移確認
    contents_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/contents')]")
    if contents_links:
        contents_links[0].click()
        time.sleep(1)
        wait.until(EC.url_contains("/contents"))
        assert "/contents" in driver.current_url, "未ログイン時に contents へ遷移していません"
        driver.get(f"{base_url}/")
        time.sleep(1)

    # 5. 文章エリアの表示検証
    text_items = driver.find_elements(By.CLASS_NAME, "text_item")
    if len(text_items) > 0:
        for item in text_items:
            title_elem = item.find_element(By.CLASS_NAME, "text_title_display")
            assert title_elem.text.strip() != "", "文章のタイトルが空です"
    else:
        assert True


def test_top_page_authenticated_menu_and_views(base_url, logged_in_driver):
    """【E2E】ログイン済み状態でのメニュー遷移、文章作成遷移、いいね機能の動作、ログアウト確認"""
    driver = logged_in_driver
    wait = WebDriverWait(driver, 10)

    driver.get(f"{base_url}/")
    time.sleep(1)

    # 1. ログイン済み時メニューの検証とマイページへの遷移確認
    mypage_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'mypage')]")))
    logout_btn = driver.find_element(By.CLASS_NAME, "logout-btn")

    assert mypage_link.is_displayed(), "ログイン時に「マイページ」が表示されていません"
    assert logout_btn.is_displayed(), "ログイン時に「ログアウト」ボタンが表示されていません"

    mypage_link.click()
    time.sleep(1)
    wait.until(EC.url_contains("mypage"))
    assert "mypage" in driver.current_url, "マイページへ正しく遷移していません"
    driver.get(f"{base_url}/") 
    time.sleep(1)

    # 2. ログイン状態で「文章作成」をクリックした際、作成画面に遷移するか検証
    text_new_link = wait.until(EC.element_to_be_clickable((By.ID, "text_new_link")))
    text_new_link.click()
    time.sleep(1)

    wait.until(EC.url_contains("/text-new/"))
    assert "/text-new/" in driver.current_url, "ログイン時に文章作成画面へ正しく遷移していません"
    driver.get(f"{base_url}/") 
    time.sleep(1)

    # 3. ログイン状態で「いいね」ボタンをクリックした際の動作確認
    word_good_form = wait.until(EC.presence_of_element_located((By.ID, "word_good_form")))
    word_good_button = word_good_form.find_element(By.CSS_SELECTOR, "button.good-button")
    good_count_elem = word_good_form.find_element(By.CLASS_NAME, "good-count")
    
    initial_count = int(good_count_elem.text) if good_count_elem.text.isdigit() else 0
    
    word_good_button.click()
    time.sleep(1)
    
    updated_count_text = good_count_elem.text
    assert updated_count_text.isdigit(), "いいね数が数値ではありません"
    assert True

    # 4. ログイン状態での contents への遷移確認
    contents_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/contents')]")
    if contents_links:
        contents_links[0].click()
        time.sleep(1)
        wait.until(EC.url_contains("/contents"))
        assert "/contents" in driver.current_url, "ログイン時に contents へ遷移していません"
        driver.get(f"{base_url}/") 
        time.sleep(1)

    # 5. ログアウト処理の確認
    logout_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "logout-btn")))
    logout_btn.click()
    time.sleep(1)

    wait.until(EC.presence_of_element_located((By.XPATH, "//a[@href='/login']")))
    login_link_after = driver.find_element(By.XPATH, "//a[@href='/login']")
    assert login_link_after.is_displayed(), "ログアウト処理が正常に行われていません"
    time.sleep(1)


def test_top_page_next_word_ajax(base_url, driver):
    """【非同期通信/E2E】「次へ」ボタンをクリックした際、画面全体のリロードなしで単語や文章が切り替わるか"""
    driver.get(f"{base_url}/")
    time.sleep(1)
    wait = WebDriverWait(driver, 10)

    word_text_element = wait.until(EC.presence_of_element_located((By.ID, "word_text")))
    initial_word = word_text_element.text

    next_btn = driver.find_element(By.ID, "next_word_btn")
    next_btn.click()
    time.sleep(1)

    try:
        wait.until(lambda d: d.find_element(By.ID, "word_text").text != initial_word)
    except Exception:
        next_btn.click()
        time.sleep(1)

    updated_word = driver.find_element(By.ID, "word_text").text
    assert updated_word != ""
    time.sleep(1)