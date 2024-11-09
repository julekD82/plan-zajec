document.addEventListener("DOMContentLoaded", function() {
    // Pobierz modal
    var modal = document.getElementById("scheduleModal");
    var modalText = document.getElementById("modal-text");
    var closeBtn = document.getElementsByClassName("close")[0];

    // Zidentyfikuj wszystkie zajęcia
    var scheduleEntries = document.getElementsByClassName("schedule-entry");

    // Dodaj event listener do każdego zajęcia, aby otworzyć modal
    for (var i = 0; i < scheduleEntries.length; i++) {
        scheduleEntries[i].addEventListener("click", function() {
            // Pobierz dane z klikniętego elementu i dodaj do modalu
            modalText.innerHTML = this.innerHTML; // Możesz dostosować to, co się wyświetli
            modal.style.display = "block";
        });
    }

    // Zamykanie modalu po kliknięciu przycisku zamknięcia
    closeBtn.onclick = function() {
        modal.style.display = "none";
    }

    // Zamykanie modalu po kliknięciu poza jego obszarem
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
});
