from selenium import webdriver
from selenium.webdriver.common.by import By
import time

# ブラウザテスト

# トップページ表示
def test_show_top_page():
    
    driver = webdriver.Chrome()
    # access url
    url = "http://127.0.0.1:5000/"
    # アクセス
    driver.get(url)
   
    # ページタイトル<title>取得
    title = driver.title

    # テスト
    assert title == "美しい日本語"
    
    # 2秒停止
    time.sleep(2)
    # 終了
    driver.quit()

# ログイン/ログアウトテスト
def test_login_to_mypage():
    
    # Web Driver
    driver = webdriver.Chrome()
    # access url
    url = "http://127.0.0.1:5000/login"
    # access
    driver.get(url)

    # 1秒停止
    time.sleep(1)

    # ログイン

    # メール入力欄を取得(#id)
    mail = driver.find_element(By.ID,"mail")
    #ユーザーメール入力
    mail.send_keys("takujiozaki@gmail.com")

    # パスワード入力欄を取得(#Password)
    password = driver.find_element(By.ID,"Password")
    # パスワード入力
    password.send_keys("abcd1234")

    # 1秒停止
    time.sleep(1)

    # submitボタン取得
    button = driver.find_element(By.TAG_NAME, "button")
    # clickする：ｗｑ！
    button.click()


    # 1秒停止
    time.sleep(1)

    # テスト(ユーザー名、マイページの表示を確認)
    h1_element = driver.find_element(By.TAG_NAME,"h1").text
    assert h1_element == "マイページ"
    h2_elements = driver.find_elements(By.TAG_NAME,"h2")
    assert h2_elements[0].text == "ログインユーザー：ozaki"

    # # ログアウト
    logout = driver.find_element(By.CLASS_NAME,"logout-btn")
    # ログアウトクリック
    logout.click()


    # 1秒停止
    time.sleep(1)

    # ログアウトメッセージ(flash)の取得
    main_element = driver.find_element(By.TAG_NAME,"main")
    flash_message = main_element.find_element(By.TAG_NAME,"p").text
    assert flash_message == "ログアウトしました"
    # 終了
    driver.quit()


# 新規登録画面表示テスト
def test_show_register_page():

    driver = webdriver.Chrome()

    url = "http://127.0.0.1:5000/register"
    driver.get(url)

    time.sleep(1)

    title = driver.find_element(By.TAG_NAME,"h1").text

    assert title == "新規登録"

    driver.quit()

# ログイン後に退会画面表示テスト
# def test_show_unregister_page():

#     driver = webdriver.Chrome()

#     # ログイン画面
#     driver.get("http://127.0.0.1:5000/login")

#     time.sleep(1)

#     # メールアドレス入力
#     mail = driver.find_element(By.ID, "mail")
#     mail.send_keys("takujiozaki@gmail.com")

#     # パスワード入力
#     password = driver.find_element(By.ID, "Password")
#     password.send_keys("abcd1234")

#     # ログイン
#     driver.find_element(By.TAG_NAME, "button").click()

#     time.sleep(1)

#     # 退会画面へ移動
#     button = driver.find_elements(By.TAG_NAME, "a")
#     assert button == "退会"

#     for button in button:
#         button.click()

#     time.sleep(1)

#     # 画面タイトル確認
#     title = driver.find_element(By.TAG_NAME, "h1").text
#     assert title == "退会画面"

#     driver.quit()

# ログイン後 マイページから退会画面表示テスト
def test_show_unregister_page():

    driver = webdriver.Chrome()

    try:
        # ログイン画面へアクセス
        driver.get(
            "http://127.0.0.1:5000/login"
        )

        time.sleep(1)

        # メール入力
        mail = driver.find_element(
            By.ID,
            "mail"
        )
        mail.send_keys(
            "takujiozaki@gmail.com"
        )

        # パスワード入力
        password = driver.find_element(
            By.ID,
            "Password"
        )
        password.send_keys(
            "abcd1234"
        )

        # ログインボタン押下
        driver.find_element(
            By.TAG_NAME,
            "button"
        ).click()

        time.sleep(1)


        # マイページ確認
        h1 = driver.find_element(
            By.TAG_NAME,
            "h1"
        ).text

        assert h1 == "マイページ"


        # 退会リンククリック
        driver.find_element(
            By.LINK_TEXT,
            "退会"
        ).click()

        time.sleep(1)


        # 退会画面確認
        h1 = driver.find_element(
            By.TAG_NAME,
            "h1"
        ).text

        assert h1 == "退会画面"

    finally:
        driver.quit()