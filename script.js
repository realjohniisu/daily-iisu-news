const MIN_DATE = new Date(2026, 8, 1);

let currentDate = new Date();
let episodes = [];
let selectedDate = null;

const monthYear = document.getElementById("month-year");
const calendarDays = document.getElementById("calendar-days");
const episodeList = document.getElementById("episode-list");
const episodeCount = document.getElementById("episode-count");
const previousMonth = document.getElementById("previous-month");
const todayButton = document.getElementById("today-button");
const nextMonth = document.getElementById("next-month");
const backgroundMusic = document.getElementById("background-music");
const siteLogo = document.querySelector(".site-logo");

const sounds = {
    move: new Audio("Move.wav"),
    scroll: new Audio("Scroll.wav"),
    social: new Audio("Social.wav"),
    link: new Audio("Link.wav")
};

sounds.move.volume = 0.5;
sounds.scroll.volume = 0.35;
sounds.social.volume = 0.5;
sounds.link.volume = 0.5;

if (currentDate < MIN_DATE) {
    currentDate = new Date(MIN_DATE);
}

currentDate = new Date(
    currentDate.getFullYear(),
    currentDate.getMonth(),
    1
);

function playSound(sound) {
    sound.currentTime = 0;
    sound.play().catch(() => {});
}

function startMusic() {
    backgroundMusic.play().catch(() => {});
}

backgroundMusic.volume = 0.25;

window.addEventListener("load", () => {
    startMusic();
});

document.addEventListener("pointerdown", () => {
    startMusic();
}, { once: true });

async function loadEpisodes() {
    try {
        const response = await fetch("episodes.json", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Failed to load episodes.json");
        }

        episodes = await response.json();

        if (!Array.isArray(episodes)) {
            throw new Error("Invalid episode data");
        }

        renderCalendar();
    } catch (error) {
        console.error(error);

        calendarDays.innerHTML = "";
        episodeList.innerHTML = `
            <div class="error">
                Unable to load episode data.
            </div>
        `;

        episodeCount.textContent = "Error";
    }
}

function getEpisodeForDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const dateString = `${year}-${month}-${day}`;

    return episodes.find(episode => episode.date === dateString);
}

function formatDate(dateString) {
    const date = new Date(`${dateString}T00:00:00`);

    return date.toLocaleDateString(undefined, {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric"
    });
}

function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    monthYear.textContent = currentDate.toLocaleDateString(undefined, {
        month: "long",
        year: "numeric"
    });

    calendarDays.innerHTML = "";

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    for (let i = 0; i < firstDay; i++) {
        const emptyDay = document.createElement("div");
        emptyDay.className = "calendar-day empty";
        calendarDays.appendChild(emptyDay);
    }

    const today = new Date();

    const todayString = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);

        const dateString = [
            year,
            String(month + 1).padStart(2, "0"),
            String(day).padStart(2, "0")
        ].join("-");

        const episode = getEpisodeForDate(date);

        const dayButton = document.createElement("button");
        dayButton.type = "button";
        dayButton.className = "calendar-day";

        if (dateString === todayString) {
            dayButton.classList.add("today");
        }

        if (selectedDate === dateString) {
            dayButton.classList.add("selected");
        }

        if (episode) {
            dayButton.classList.add("has-episode");
        }

        dayButton.innerHTML = `
            <span class="calendar-day-number">${day}</span>
            ${episode ? `<span class="calendar-day-title">${escapeHtml(episode.title)}</span>` : ""}
        `;

        dayButton.addEventListener("click", () => {
            selectedDate = dateString;
            renderCalendar();
            selectEpisode(dateString);
        });

        calendarDays.appendChild(dayButton);
    }

    previousMonth.disabled =
        year === MIN_DATE.getFullYear() &&
        month === MIN_DATE.getMonth();
}

function selectEpisode(dateString) {
    const episode = episodes.find(item => item.date === dateString);

    if (!episode) {
        showNoEpisodes(dateString);
        return;
    }

    renderEpisode(episode);
}

function renderEpisode(episode) {
    episodeCount.textContent = formatDate(episode.date);

    const thumbnail =
        episode.thumbnail ||
        `https://i.ytimg.com/vi/${episode.videoId}/hqdefault.jpg`;

    const youtubeUrl =
        episode.url ||
        `https://www.youtube.com/watch?v=${episode.videoId}`;

    episodeList.innerHTML = `
        <article class="episode-card">
            <div class="episode-content">
                <div class="episode-thumbnail">
                    <img
                        src="${escapeHtml(thumbnail)}"
                        alt="${escapeHtml(episode.title)}"
                        loading="lazy"
                    >
                </div>

                <div class="episode-info">
                    <span class="episode-number">
                        Episode ${escapeHtml(String(episode.number ?? ""))}
                    </span>

                    <h3 class="episode-title">
                        ${escapeHtml(episode.title)}
                    </h3>

                    <p class="episode-date">
                        ${escapeHtml(formatDate(episode.date))}
                    </p>

                    <div class="episode-actions">
                        <a
                            class="episode-button primary youtube-button"
                            href="${escapeHtml(youtubeUrl)}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            <svg class="youtube-icon" viewBox="0 0 24 24" aria-hidden="true">
                                <path
                                    fill="currentColor"
                                    d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31.7 31.7 0 0 0 0 12a31.7 31.7 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31.7 31.7 0 0 0 24 12a31.7 31.7 0 0 0-.5-5.8ZM9.6 15.9V8.1L16 12l-6.4 3.9Z"
                                />
                            </svg>
                            Watch on YouTube
                        </a>
                    </div>
                </div>
            </div>
        </article>
    `;
}

function showNoEpisodes(dateString) {
    episodeCount.textContent = formatDate(dateString);

    episodeList.innerHTML = `
        <div class="no-episode">
            No episode was published on this day.
        </div>
    `;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

previousMonth.addEventListener("click", () => {
    if (
        currentDate.getFullYear() === MIN_DATE.getFullYear() &&
        currentDate.getMonth() === MIN_DATE.getMonth()
    ) {
        return;
    }

    currentDate = new Date(
        currentDate.getFullYear(),
        currentDate.getMonth() - 1,
        1
    );

    if (currentDate < MIN_DATE) {
        currentDate = new Date(MIN_DATE);
    }

    selectedDate = null;

    playSound(sounds.move);
    renderCalendar();

    episodeList.innerHTML = "";
    episodeCount.textContent = "Select a day";
});

nextMonth.addEventListener("click", () => {
    currentDate = new Date(
        currentDate.getFullYear(),
        currentDate.getMonth() + 1,
        1
    );

    selectedDate = null;

    playSound(sounds.move);
    renderCalendar();

    episodeList.innerHTML = "";
    episodeCount.textContent = "Select a day";
});

todayButton.addEventListener("click", () => {
    const today = new Date();

    currentDate = new Date(
        today.getFullYear(),
        today.getMonth(),
        1
    );

    if (currentDate < MIN_DATE) {
        currentDate = new Date(MIN_DATE);
    }

    selectedDate = null;

    playSound(sounds.move);
    renderCalendar();

    episodeList.innerHTML = "";
    episodeCount.textContent = "Select a day";
});

siteLogo.addEventListener("click", () => {
    playSound(sounds.link);
});

document.addEventListener("click", event => {
    const youtubeButton = event.target.closest(".youtube-button");

    if (youtubeButton) {
        playSound(sounds.link);
    }

    const discordButton = event.target.closest(".discord-button");

    if (discordButton) {
        playSound(sounds.social);
    }
});

let lastHoveredClickable = null;

document.addEventListener("pointerover", event => {
    const clickable = event.target.closest("button, a, [role='button']");

    if (!clickable) {
        lastHoveredClickable = null;
        return;
    }

    if (clickable !== lastHoveredClickable) {
        playSound(sounds.scroll);
        lastHoveredClickable = clickable;
    }
});

document.addEventListener("pointerout", event => {
    const clickable = event.target.closest("button, a, [role='button']");

    if (!clickable) {
        return;
    }

    if (!clickable.contains(event.relatedTarget)) {
        if (clickable === lastHoveredClickable) {
            lastHoveredClickable = null;
        }
    }
});

loadEpisodes();