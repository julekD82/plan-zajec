document.addEventListener("DOMContentLoaded", function () {
    const contextMenu = document.getElementById("context-menu");

    document.addEventListener("contextmenu", function (e) {
        console.log(e)
        const target = e.target.closest(".schedule-entry");

        console.log(target);
        if (target) {
            e.preventDefault();
            contextMenu.style.top = `${e.clientY}px`;
            contextMenu.style.left = `${e.clientX}px`;
            contextMenu.style.display = "block";

            contextMenu.setAttribute("data-entry", JSON.stringify({
                title: target.getAttribute("title"),
                startTime: target.getAttribute("data-start-datetime"),
                endTime: target.getAttribute("data-end-datetime")
            }));
        } else {
            contextMenu.style.display = "none";
        }
    });

    document.addEventListener("click", function () {
        contextMenu.style.display = "none";
    });

    document.getElementById("export-outlook").addEventListener("click", function () {
        const entryData = JSON.parse(contextMenu.getAttribute("data-entry"));
        exportToICS(entryData, "Outlook");
    });

    document.getElementById("export-google").addEventListener("click", function () {
        const entryData = JSON.parse(contextMenu.getAttribute("data-entry"));
        exportToGoogle(entryData);
    });

    function exportToGoogle(entry) {
        console.log(entry);

        fetch('/update-google-event', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: entry.title,
                startTime: entry.startTime,
                endTime: entry.endTime
            })
        }).then(response => response.json())
          .then(data => {
              if (data.status === "success") {
                  alert("Wydarzenie zostało pomyślnie dodane do Google Kalendarza.");
              } else {
                  alert("Wystąpił błąd podczas dodawania wydarzenia: " + data.error);
              }
          });
    }

    function exportToICS(entry, platform) {
        const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:${entry.title}
DESCRIPTION:${entry.description}
DTSTART:${entry.date}T${entry.startTime}00
DTEND:${entry.date}T${entry.endTime}00
END:VEVENT
END:VCALENDAR;`;

        const blob = new Blob([icsContent], { type: "text/calendar" });
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = url;
        link.download = `${platform === "Outlook" ? "outlook-event" : "event"}.ics`;
        link.click();

        URL.revokeObjectURL(url);
    }
});
