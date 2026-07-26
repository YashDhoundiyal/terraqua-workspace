// Initializes FullCalendar on any page that has a #tq-calendar container
document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById("tq-calendar");
  if (!el) return;

  const calendar = new FullCalendar.Calendar(el, {
    initialView: "dayGridMonth",
    height: "auto",
    headerToolbar: { left: "prev,next today", center: "title", right: "dayGridMonth,listMonth" },
    events: function (info, successCallback, failureCallback) {
      fetch("/api/calendar-events")
        .then((r) => r.json())
        .then((events) => successCallback(events))
        .catch((err) => failureCallback(err));
    },
    eventDidMount: function (arg) {
      if (arg.event.extendedProps && arg.event.extendedProps.description) {
        arg.el.title = arg.event.extendedProps.description;
      }
    },
  });
  calendar.render();
});
