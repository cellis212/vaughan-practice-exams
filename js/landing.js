// Landing page: university -> course -> professor selection.
(async function () {
  const resp = await fetch("catalog.json");
  if (!resp.ok) {
    document.querySelector("main").insertAdjacentHTML(
      "afterbegin",
      '<div class="card" style="color:#b00020">Failed to load catalog.json (' +
        resp.status + ").</div>"
    );
    return;
  }
  const catalog = await resp.json();

  const uniSel = document.getElementById("sel-university");
  const courseSel = document.getElementById("sel-course");
  const profSel = document.getElementById("sel-professor");
  const goBtn = document.getElementById("go");

  function fill(select, items) {
    select.innerHTML = "";
    for (const item of items) {
      const opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = item.name;
      select.appendChild(opt);
    }
  }

  function currentUniversity() {
    return catalog.universities.find((u) => u.id === uniSel.value);
  }

  function currentCourse() {
    return currentUniversity().courses.find((c) => c.id === courseSel.value);
  }

  fill(uniSel, catalog.universities);
  fill(courseSel, currentUniversity().courses);
  fill(profSel, currentCourse().professors);

  uniSel.addEventListener("change", () => {
    fill(courseSel, currentUniversity().courses);
    fill(profSel, currentCourse().professors);
  });
  courseSel.addEventListener("change", () => {
    fill(profSel, currentCourse().professors);
  });

  goBtn.addEventListener("click", () => {
    const params = new URLSearchParams({
      u: uniSel.value,
      c: courseSel.value,
      p: profSel.value,
    });
    window.location.href = "generator.html?" + params.toString();
  });
})();
