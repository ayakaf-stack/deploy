document.addEventListener("DOMContentLoaded", () => {
    let currentFilter = "all";

    const wordList = document.getElementById("word_list");
    const noResult = document.getElementById("no_result");
    const registerBtn = document.getElementById("register_btn");
    const filterBtns = document.querySelectorAll(".filter_btn");

    // 絞り込みボタン
    filterBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            currentFilter = btn.dataset.filter;

            filterBtns.forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");

            fetchAndRender();
        });
    });

    // 単語が選択されたら、その単語の登録済みジャンルにチェックを入れる
    wordList.addEventListener("change", (e) => {
        if (e.target.name !== "selected_word") return;

        const raw = e.target.dataset.genreIds;
        const registeredIds = raw ? raw.split(",").map(Number) : [];

        document.querySelectorAll('input[name="selected_genre"]').forEach(checkbox => {
            checkbox.checked = registeredIds.includes(Number(checkbox.value));
        });
    });

    // 登録ボタン
    registerBtn.addEventListener("click", async () => {
        const selectedWord = document.querySelector('input[name="selected_word"]:checked');
        const selectedGenres = Array.from(
            document.querySelectorAll('input[name="selected_genre"]:checked')
        ).map(el => Number(el.value));

        if (!selectedWord) {
            showAdminMessage("単語を選択してください");
            return;
        }

        const response = await fetch("/admin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                word_id: Number(selectedWord.value),
                genre_ids: selectedGenres
            })
        });

        const data = await response.json();

        if (!response.ok) {
            showAdminMessage(data.error);
            return;
        }

        showAdminMessage("ジャンルを更新しました");

        document.querySelectorAll('input[name="selected_genre"]').forEach(checkbox => {
            checkbox.checked = false;
        });

        fetchAndRender();
    });

    async function fetchAndRender() {
        const params = new URLSearchParams();
        params.set("genre_filter", currentFilter);

        const response = await fetch(`/admin?${params.toString()}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });
        const data = await response.json();

        renderList(data.items, data.genres);
    }

    function renderList(items, genres) {
        wordList.innerHTML = "";

        if (items.length === 0) {
            noResult.style.display = "block";
            return;
        }
        noResult.style.display = "none";

        items.forEach(item => {
            const tags = genres
                .filter(genre => item.genre_ids.includes(genre.id))
                .map(genre => `<span class="genre_tag">${genre.genre}</span>`)
                .join("");

            const li = document.createElement("li");
            li.className = "word_item";
            li.innerHTML = `
                <label>
                    <input type="radio" name="selected_word" value="${item.id}" data-genre-ids="${item.genre_ids.join(",")}">
                    単語:${item.word}(読み:${item.reading})
                </label>
                <span class="genre_tags">${tags}</span>
            `;
            wordList.appendChild(li);
        });
    }

    function showAdminMessage(message) {
        let container = document.getElementById("flash-messages");
        if (!container) {
            container = document.createElement("div");
            container.id = "flash-messages";
            document.body.prepend(container);
        }
        container.innerHTML = `<div class="flash-message">${message}</div>`;
    }
});