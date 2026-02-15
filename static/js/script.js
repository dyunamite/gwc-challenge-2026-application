document.addEventListener("DOMContentLoaded", function() {
    const screens = {
        home: document.getElementById("homeScreen"),
        art: document.getElementById("artScreen"),
        music: document.getElementById("musicScreen"),
        literature: document.getElementById("literatureScreen")
    };

    function showScreen(key) {
        Object.values(screens).forEach(s => s.style.display = "none");
        if (screens[key]) screens[key].style.display = "flex";
        if (key === 'art') {
            document.getElementById("artUploadFull").style.display = "flex";
            document.getElementById("artSelect").style.display = "none";
        }
        if (key === 'literature') {
            document.getElementById("literatureUploadFull").style.display = "flex";
            document.getElementById("literatureDownload").style.display = "none";
        }
    }

    // Navigation
    document.getElementById("homeBtn").onclick = () => showScreen("home");
    document.getElementById("artBtn").onclick = () => showScreen("art");
    document.getElementById("musicBtn").onclick = () => showScreen("music");
    document.getElementById("literatureBtn").onclick = () => showScreen("literature");

    // --- HELPER ---
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // --- ART LOGIC ---
    const uploadArtBtn = document.getElementById("uploadArtBtn");
    const artFileInput = document.getElementById("uploadArt");
    const toggles = document.querySelectorAll(".artToggle");
    let currentArtPath = "";

    uploadArtBtn.onclick = async () => {
        if (!artFileInput.files[0]) return alert("Select a file!");
        const formData = new FormData();
        formData.append("art", artFileInput.files[0]);
        uploadArtBtn.innerText = "Analyzing...";

        const resp = await fetch("/upload-art", { method: "POST", body: formData });
        const data = await resp.json();
        if (data.success) {
            document.getElementById("artUploadFull").style.display = "none";
            document.getElementById("artSelect").style.display = "flex";
            const t = Date.now();
            document.getElementById("preview1").src = data.preview1 + "?t=" + t;
            document.getElementById("preview2").src = data.preview2 + "?t=" + t;
            document.getElementById("preview3").src = data.preview3 + "?t=" + t;
            updateArtSelection(0);
        }
        uploadArtBtn.innerText = "UPLOAD";
    };

    function updateArtSelection(idx) {
        toggles.forEach((btn, i) => {
            btn.classList.toggle("active", i === idx);
            if (i === idx) currentArtPath = document.getElementById(`preview${i+1}`).src.split('?')[0];
        });
    }

    toggles.forEach(btn => btn.onclick = () => updateArtSelection(parseInt(btn.dataset.index)));
    document.getElementById("downloadArtBtn").onclick = () => {
        const a = document.createElement("a"); a.href = currentArtPath; a.download = "protected.png"; a.click();
    };
    document.getElementById("backArt").onclick = () => showScreen('art');

    // --- LITERATURE LOGIC ---
    const litInput = document.getElementById("literatureInput");
    const litOutput = document.getElementById("literatureOutput");
    const uploadLitBtn = document.getElementById("uploadLiteratureBtn");

    uploadLitBtn.onclick = async () => {
        const text = litInput.value.trim();
        if (!text) return alert("Enter text!");

        const resp = await fetch("/upload-literature", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text })
        });

        const data = await resp.json();
        if (data.success) {
            litOutput.innerText = data.result;
            const debugBox = document.getElementById("literatureDebugOutput");
            if (debugBox) debugBox.innerHTML = data.debug;
            document.getElementById("literatureUploadFull").style.display = "none";
            document.getElementById("literatureDownload").style.display = "flex";
        }
    };
    document.getElementById("literatureDownloadBtn").onclick = () => {
        navigator.clipboard.writeText(litOutput.innerText);
        alert("Copied!");
    };
    document.getElementById("backLiterature").onclick = () => showScreen('literature');

    // --- MUSIC LOGIC ---
    const uploadMusicBtn = document.getElementById("uploadMusicBtn");
    const musicFileInput = document.getElementById("uploadMusic");
    const musicPreview = document.getElementById("musicPreview");
    const musicDownloadBtn = document.getElementById("musicDownloadBtn");

    if (uploadMusicBtn) {
        uploadMusicBtn.onclick = async () => {
            const file = musicFileInput.files[0];
            if (!file) return alert("Please select an audio file first!");

            uploadMusicBtn.innerText = "PROCESSING...";
            const formData = new FormData();
            formData.append("uploadMusic", file);

            try {
                const resp = await fetch("/upload-music", { method: "POST", body: formData });
                const data = await resp.json();

                if (data.success) {
                    musicPreview.src = data.audio_url;
                    musicPreview.load();

                    alert(`Success! Poisoning static inserted at ${formatTime(data.timestamp)}.`);

                    document.getElementById("musicUploadFull").style.display = "none";
                    document.getElementById("musicDownload").style.display = "flex";

                    musicDownloadBtn.onclick = () => {
                        const a = document.createElement("a");
                        a.href = data.audio_url;
                        a.download = "protected_audio.wav";
                        a.click();
                    };
                } else {
                    alert("Error: " + data.error);
                }
            } catch (e) {
                alert("Connection error to audio server.");
            } finally {
                uploadMusicBtn.innerText = "UPLOAD";
            }
        };
    }

    document.getElementById("backMusic").onclick = () => {
        document.getElementById("musicUploadFull").style.display = "flex";
        document.getElementById("musicDownload").style.display = "none";
    };

    showScreen("home");
});